#!/usr/bin/env python

"""Report on CDR filter sets.
"""

from copy import deepcopy
from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Filter as APIFilter, FilterSet as APIFilterSet


class Control(Controller):
    """Logic for the report."""

    FILTER_SETS = "Filter Sets"
    EDIT_FILTER_SETS = "EditFilterSets.py"
    DEEP = "Deep Report"
    SHALLOW = "Shallow Report"

    def run(self):
        """Provide routing to our custom commands."""

        if self.request == self.DEEP:
            self.navigate_to(self.script, self.session.name)
        elif self.request == self.SHALLOW:
            self.navigate_to(self.script, self.session.name, depth="shallow")
        elif self.request == self.FILTER_SETS:
            self.navigate_to(self.EDIT_FILTER_SETS, self.session.name)
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Bypass the form, go straight to the report output.

        Pass:
            page - HTMLPage object to be filled in
        """

        if self.depth == "shallow":
            self.show_shallow_report(page)
        else:
            self.show_deep_report(page)
        page.add_css("""\
.set     { color: purple; }
.filter  { color: blue; }
.include { color: green; }
.error   { color: red; }
.error { color: red; }
li.filter a, li.include a { text-decoration: underline; }
li.filter a:hover, li.include a:hover { cursor: pointer; }""")

    def show_deep_report(self, page):
        """Create the recursive version of the report.

        Pass:
            page - HTMLPage object to be filled in
        """

        fieldset = page.fieldset("Filter Sets")
        ul = page.B.UL()
        for filter_set in self.filter_sets:
            ul.append(filter_set.node)
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_script("""\
function show(id) {
    var url  = "ShowRawXml.py?id=" + id;
    var name = "raw" + id
    var wind = window.open(url, name);
}""")
        page.add_css("fieldset { width: 750px; }")

    def show_shallow_report(self, page):
        """Create the non-recursive version of the report.

        Pass:
            page - HTMLPage object to be filled in
        """

        fieldset = page.fieldset("Filter Sets")
        dl = page.B.DL()
        for id, name in APIFilterSet.get_filter_sets(self.session):
            dl.append(page.B.DT(name, page.B.CLASS("set")))
            filter_set = APIFilterSet(self.session, id=id)
            for member in filter_set.members:
                if isinstance(member, APIFilterSet):
                    dd = page.B.DD(f"[S] {member.name}")
                    dd.set("class", "set")
                else:
                    dd = page.B.DD(f"[F] {member.title}")
                    dd.set("class", "filter")
                dl.append(dd)
        fieldset.append(dl)
        page.form.append(fieldset)
        page.add_css("dt { font-weight: bold; }\nfieldset { width: 600px; }")

    @cached_property
    def buttons(self):
        """Customize supported actions, including toggle between versions."""

        other = self.DEEP if self.depth == "shallow" else self.SHALLOW
        return (other, self.FILTER_SETS)

    @cached_property
    def depth(self):
        """If shallow, we don't recurse."""
        return self.fields.getvalue("depth")

    @cached_property
    def filter_sets(self):
        """Sequence of FilterSet` objects used by the deep report."""

        # Load and index the filters first.
        for doc in APIFilterSet.get_filters(self.session):
            Filter(doc)

        # Now it's safe to load up the filter sets.
        sets = []
        for id, name in APIFilterSet.get_filter_sets(self.session):
            api_filter_set = APIFilterSet(self.session, id=id, name=name)
            sets.append(FilterSet(api_filter_set))
        return sets

    @cached_property
    def same_window(self):
        """Don't open new browser tabs."""
        return self.buttons

    @cached_property
    def subtitle(self):
        """Identify which report this is."""

        if self.depth == "shallow":
            return "CDR Filter Sets -- Shallow Report"
        return "CDR Filter Sets -- Deep Report"


class FilterSet:
    """Wrapper around API's `FilterSet` class.

    Adds functionality needed to render HTML for the report recursively.
    Uses inclusion instead of inheritance. Notice that the `node`
    properties cache the work of building up the node, returning the
    cached node when first built, but on subsequent invocations we use
    the `copy` module's `deepcopy()` function to ensure that lxml does
    not move the node form its first location on the second and subsequent
    occurrences.
    """

    def __init__(self, api_filter_set):
        """Save API `FilterSet` object, giving us access to all we need."""
        self.__api_filter_set = api_filter_set

    @property
    def name(self):
        """The string for the filter set's name."""
        return self.__api_filter_set.name

    @cached_property
    def members(self):
        """Sequence of members using our own object types."""

        members = []
        for member in self.__api_filter_set.members:
            if isinstance(member, APIFilterSet):
                members.append(FilterSet(member))
            else:
                members.append(Filter(member))
        return members

    @property
    def node(self):
        """HTML li node for the recursive report."""

        if not hasattr(self, "_node"):
            self._node = Filter.B.LI(self.name, Filter.B.CLASS("set"))
            members = [member.node for member in self.members]
            if members:
                self._node.append(Filter.B.UL(*members))
            return self._node
        return deepcopy(self._node)


class Filter:
    """Filter document with info on included modules."""

    from lxml.html import builder as B
    NS = APIFilter.NS
    XSL_INCLUDE = f"{{{NS}}}include"
    XSL_IMPORT = f"{{{NS}}}import"
    TITLES = {}
    IDS = {}

    def __init__(self, doc):
        """Store the document object for the filter and index it."""

        self.__doc = doc
        Filter.IDS[doc.id] = self
        Filter.TITLES[doc.title.strip().lower()] = self

    @property
    def doc(self):
        """Access to the `Document` object for the filter."""
        return self.__doc

    @property
    def id(self):
        """For creating links to the filter document."""
        return self.doc.id

    @property
    def error(self):
        """Parsing failure explanation if errors happened, else None."""
        return self._error if hasattr(self, "_error") else None

    @property
    def includes(self):
        """Modules included by the filter."""

        if not hasattr(self, "_includes"):
            self._includes = None
            filters = []
            try:
                for child in self.doc.root:
                    if child.tag in (self.XSL_INCLUDE, self.XSL_IMPORT):
                        tag = child.tag.replace(f"{{{self.NS}}}", "xsl:")
                        href = child.get("href")
                        filters.append(self.Include(tag, href))
                if filters:
                    self._includes = self.B.UL()
                    for included in filters:
                        self._includes.append(included.node)
                return self._includes
            except Exception as e:
                print(e)
                self._error = f"Failure parsing filter: {e}"
        return deepcopy(self._includes)

    @property
    def node(self):
        if not hasattr(self, "_node"):
            link = self.B.A(str(self.doc.id), onclick=f"show({self.doc.id})")
            self._node = self.B.LI(self.doc.title, " (", link, ")")
            self._node.set("class", "filter")
            if self.error:
                self._node.append(self.B.SPAN(self.error))
            elif self.includes is not None:
                self._node.append(self.includes)
            return self._node
        return deepcopy(self._node)

    class Include:
        """An included (or imported) filter."""

        def __init__(self, elem, href):
            """Capture the caller's values."""

            self.elem = elem
            self.href = href

        @cached_property
        def name(self):
            """Used for display and for constructing lookup key."""

            if self.href.startswith("cdr:"):
                return self.href[4:]
            return self.href

        @cached_property
        def key(self):
            """Index into Filter.TITLES dictionary."""
            return self.name[5:].lower().strip()

        @property
        def node(self):
            if not hasattr(self, "_node"):
                label = f"{self.elem} {self.name}"
                filter_doc = Filter.TITLES.get(self.key)
                if filter_doc:
                    doc_id = str(filter_doc.id)
                    link = Filter.B.A(doc_id, onclick=f"show({doc_id})")
                    self._node = Filter.B.LI(label, " (", link, ")")
                    self._node.set("class", "include")
                    if filter_doc.includes is not None:
                        self._node.append(filter_doc.includes)
                else:
                    print(self.key)
                    print(sorted(Filter.TITLES))
                    label = f"{label} *** NO SUCH FILTER ***"
                    self._node = Filter.B.LI(label)
                    self._node.set("class", "error")
                return self._node
            return deepcopy(self._node)


if __name__ == "__main__":
    Control().run()
