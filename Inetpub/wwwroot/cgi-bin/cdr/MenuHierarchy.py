#!/usr/bin/env

"""Review the entire menu hierarchy for a given menu type.

In order to sort the children of a term based on the SortOrder attribute
value the sortString was introduced.  The sortString is equal to the
TermName if the SortOrder attribute does not exist, otherwise it is the
SortOrder value itself.  Sort the children of a term by the sortString but
display the term name.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
from cdrapi.reports import Report


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "Menu Hierarchy Report"
    RULES = (
        "#menu-type { text-align: center; }",
        "#wrapper { width: 700px; margin: 5px auto; }",
        "ul { list-style: none; }",
        "li li { font-weight: bold; }",
        "li li li { font-weight: normal; }",
        "li li li ul { display: none; }",
    )

    def populate_form(self, page):
        """Ask the user to pick a menu type.

        Pass:
            page - HTMLPage object used to build the form
        """

        fieldset = page.fieldset("Select Menu Type For Report")
        checked = True
        for menu_type in self.menu_types:
            opts = dict(value=menu_type, checked=checked)
            fieldset.append(page.radio_button("type", **opts))
            checked = False
        page.form.append(fieldset)

    def show_report(self):
        """Override base class method, as this isn't a tabular report."""

        h2 = self.HTMLPage.B.H2(self.menu_type)
        h2.set("id", "menu-type")
        self.report.page.form.append(h2)
        ul = self.HTMLPage.B.UL()
        ul.set("id", "wrapper")
        for name in self.orphans:
            ul.append(name.node)
        self.report.page.form.append(ul)
        self.report.page.add_css("\n".join(self.RULES))
        self.report.send()

    @property
    def menu_type(self):
        """Menu type selected from the form."""
        return self.fields.getvalue("type")

    @property
    def menu_types(self):
        """Options for the form's field."""

        query = self.Query("query_term", "value").unique().order("value")
        query.where("path = '/Term/MenuInformation/MenuItem/MenuType'")
        return [row.value for row in query.execute(self.cursor).fetchall()]

    @property
    def names(self):
        """Dictionary of unique ID/name/sortkey combinations."""

        if not hasattr(self, "_names"):
            self._names = {}
            parms = dict(MenuType=self.menu_type)
            root = Report(self.session, "Menu Term Tree", **parms).run()
            for node in root.findall("MenuItem"):
                name = Name(self, node)
                parent = name.parent
                if name.key in self._names:
                    name = self._names[name.key]
                else:
                    self._names[name.key] = name
                if parent:
                    name.add_parent(parent)
        return self._names

    @property
    def no_results(self):
        """Suppress the message we'd normally get with no tables."""
        return None

    @property
    def orphans(self):
        """Ordered sequence of `Name` objects without parents."""

        if not hasattr(self, "_orphans"):
            orphans = [n for n in self.names.values() if not n.parents]
            self._orphans = sorted(orphans)
        return self._orphans

    @property
    def parents(self):
        """Dictionary of children lists, indexed by parent Term ID."""

        if not hasattr(self, "_parents"):
            self._parents = {}
            for name in self.names.values():
                for id in name.parents:
                    self._parents.setdefault(id, []).append(name)
            for id, children in self._parents.items():
                self._parents[id] = sorted(children)
        return self._parents


class Name:
    """Unique ID/name/sortkey combination for the report's menu type."""

    def __init__(self, control, node):
        """Save the caller's value and create empty lists.

        Pass:
           control - access to report-building tools and the terms dictionary
           node - parsed XML block with the values for this menu item
        """

        self.__control = control
        self.__node = node
        self.__parents = []

    def add_parent(self, parent):
        """Add to the private array of parents."""
        self.__parents.append(parent)

    def __lt__(self, other):
        """Support sorting of the menu items."""
        return self.sort_key < other.sort_key

    @property
    def children(self):
        """Sequence of child menu items under this item."""

        if not hasattr(self, "_children"):
            self._children = self.__control.parents.get(self.id, [])
        return self._children

    @property
    def display_name(self):
        """String to override the name to be displayed in the menus."""

        if not hasattr(self, "_display_name"):
            self._display_name = Doc.get_text(self.__node.find("DisplayName"))
        return self._display_name

    @property
    def id(self):
        """CDR ID for the menu item's document."""

        if not hasattr(self, "_id"):
            self._id = int(self.__node.find("TermId").text)
        return self._id

    @property
    def key(self):
        """Index into the dictionary of menu items."""

        if not hasattr(self, "_key"):
            self._key = self.id, self.name.lower(), self.sort_key
        return self._key

    @property
    def name(self):
        """Use the display name if we have one, else the term name."""
        return self.display_name or self.term_name

    @property
    def node(self):
        """HTML list item for the report (possibly with children)."""

        B = self.__control.HTMLPage.B
        node = B.LI(self.name)
        if self.children:
            node.append(B.UL(*[child.node for child in self.children]))
        return node

    @property
    def parent(self):
        """ID from this node."""

        if not hasattr(self, "_parent_id"):
            self._parent = None
            node = self.__node.find("ParentId")
            if node is not None and node.text is not None:
                self._parent = int(node.text)
        return self._parent

    @property
    def parents(self):
        """Sequence of parents of this menu item."""
        return self.__parents

    @property
    def sort_key(self):
        """Use custom sort string if provided, else display or term name."""

        if not hasattr(self, "_sort_key"):
            if self.parents:
                self._sort_key = (self.sort_string or self.name).lower()
            else:
                self._sort_key = self.name.lower()
        return self._sort_key

    @property
    def sort_string(self):
        """String used for sorting menus on the web site."""

        if not hasattr(self, "_sort_string"):
            self._sort_string = Doc.get_text(self.__node.find("SortString"))
        return self._sort_string

    @property
    def term_name(self):
        """Preferred name for the term."""

        if not hasattr(self, "_term_name"):
            self._term_name = Doc.get_text(self.__node.find("TermName"))
        return self._term_name


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
