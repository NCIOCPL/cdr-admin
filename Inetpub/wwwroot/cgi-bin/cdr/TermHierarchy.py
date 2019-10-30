#!/usr/bin/python

"""Navigate term hierarchy.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
from lxml.html import builder

class Control(Controller):
    """Access to the database and HTML generation classes."""

    TITLE = "CDR Terminology"
    SUBTITLE = "Terminology Hierarchy Display"
    PATHS = "/Term/PreferredName", "/Term/OtherName/OtherTermName"
    CSS = (
        "td { border: none; background: #e8e8e8; font-family: monospace; }",
        "td a { text-decoration: none; white-space: pre; }",
        "td { white-space: pre; font-size: 10pt; padding: 0; margin: 0 }",
        ".focus * { color: red; font-weight: bold; }",
        "div {",
        "  font-style: italic; border: solid 1px black; width: 300px;"
        "  margin: 25px auto; padding: 10px; font-size: .8em;",
        "}",
    )

    def populate_form(self, page):
        """If we don't have a term ID, get one.

        Pass:
            page - HTMLPage object on which to put the form field
        """

        if self.id:
            self.show_report()
        elif self.terms:
            fieldset = page.fieldset("Select Term")
            checked = True
            for id, title in self.terms:
                opts = dict(label=title, value=id, checked=checked)
                fieldset.append(page.radio_button("DocId", **opts))
                checked = False
            page.add_css("fieldset { width: 1024px; }")
        else:
            if self.name:
                fieldset = page.fieldset("Error")
                message = page.B.P(f"No matches for {self.name!r}")
                message.set("class", "error")
                fieldset.append(message)
                page.form.append(fieldset)
            fieldset = page.fieldset("Term ID or Name for Hierarchy Display")
            fieldset.append(page.text_field("DocId", label="CDR ID"))
            fieldset.append(page.text_field("TermName", label="Term Name"))
        page.form.append(fieldset)

    def show_report(self):
        """Override base class, because we're not using the Report class.

        Loop back to the cascading form for names if we don't have an id.
        """

        if not self.id:
            self.show_form()
        buttons = (
            self.HTMLPage.button(self.SUBMENU),
            self.HTMLPage.button(self.ADMINMENU),
            self.HTMLPage.button(self.LOG_OUT),
        )
        opts = dict(
            buttons=buttons,
            session=self.session,
            action=self.script,
            banner=self.title,
            footer=self.footer,
            subtitle=self.subtitle,
        )
        report = self.HTMLPage(self.title, **opts)
        instructions = builder.DIV(
            "Click term name to view formatted term document.",
            builder.BR(),
            "Click document ID to navigate tree."
        )
        report.body.append(instructions)
        for table in self.tree.tables:
            report.body.append(table)
        report.body.append(self.footer)
        report.add_css("\n".join(self.CSS))
        report.send()

    @property
    def id(self):
        """ID for term we'll use as our starting location in the hierarchy."""

        if not hasattr(self, "_id"):
            self._id = None
            value = self.fields.getvalue("DocId")
            if value:
                try:
                    self._id = Doc.extract_id(value)
                except Exception as e:
                    self.bail(f"invalid id {value!r}")
            if not self._id and self.terms:
                if len(self.terms) == 1:
                    self._id = self.terms[0][0]
        return self._id

    @property
    def name(self):
        """Term name entered by user."""

        if not hasattr(self, "_name"):
            self._name = self.fields.getvalue("TermName")
            if self._name:
                self._name = self._name.strip()
        return self._name

    @property
    def subtitle(self):
        """Override to make the subtitle dynamic."""

        if not hasattr(self, "_subtitle"):
            if self.id:
                name = self.tree.terms[self.id].name.split(";")[0]
                self._subtitle = f"Hierarchy display for {name}"
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle

    @property
    def terms(self):
        """ID/title tuples for terms matching the user's string."""

        if not hasattr(self, "_terms"):
            self._terms = None
            if self.name:
                name = f"%{self.name}%"
                fields = "d.id", "d.title"
                paths = ", ".join([f"'{path}'" for path in self.PATHS])
                query = self.Query("document d", *fields).order("d.title")
                query.join("query_term n", "n.doc_id = d.id")
                query.where(f"n.path IN ({paths})")
                query.where(query.Condition("n.value", name, "LIKE"))
                rows = query.execute(self.cursor).fetchall()
                self._terms = [tuple(row) for row in rows]
        return self._terms

    @property
    def tree(self):
        """Slice of the term hierarchy to be displayed."""

        if not hasattr(self, "_tree"):
            self._tree = Tree(self)
        return self._tree


class Tree:
    """Portion of the CDR term hierarchy surrounding the user's selecte term.
    """

    def __init__(self, control):
        """Save the reference to the the caller.

        Pass:
            control - access to the current session, the form, logging, etc.
        """

        self.__control = control

    @property
    def control(self):
        """Access to the current session and the form selection."""
        return self.__control

    @property
    def id(self):
        """Term ID selected by the user for the focus of the display."""
        return self.control.id

    @property
    def tables(self):
        """One table for each parent-less root."""

        if not hasattr(self, "_tables"):
            self._tables = []
            for root in self.roots:
                rows = []
                root.add_row(rows)
                caption = builder.CAPTION(f"Hierarchy from {root.name}")
                self._tables.append(builder.TABLE(caption, *rows))
        return self._tables

    @property
    def roots(self):
        if not hasattr(self, "_roots"):
            self._roots = []
            for term in self.terms.values():
                if not term.parents:
                    self._roots.append(term)
        return self._roots
    @property
    def terms(self):
        """Dictionary of terms surrounding the user's pick in the tree."""

        if not hasattr(self, "_terms"):
            doc = Doc(self.control.session, id=self.id)
            tree = doc.get_tree(depth=1)
            self._terms = {}
            for id, name in tree.names.items():
                focus = id == self.id
                self._terms[id] = Term(self, id, name, focus)
            for r in tree.relationships:
                self._terms[r.parent].add_child(self._terms[r.child])
                self._terms[r.child].add_parent(self._terms[r.parent])
        return self._terms

class Term:
    """CDR Term document, with information about its position in the tree.

    Avoid property caching for any HTML elements, as the term may need
    to be display more than once in the hierarchy.
    """

    FILTER = "Filter.py"
    FILTER_PARAMS = dict(
        Filter="name:Denormalization Filter (1/1): Terminology",
        Filter1="name:Terminology QC Report Filter",
    )

    def __init__(self, tree, id, name, focus):
        """Capture the caller's values.

        Pass:
            tree - hierarchy to which this term belongs
            id - CDR ID for the term document
            name - primary name string for the Term document
        """

        self.__tree = tree
        self.__id = id
        self.__name = name
        self.__parents = []
        self.__children = []

    @property
    def control(self):
        """Access to HTML and URL generation facilities."""
        return self.tree.control

    @property
    def tree(self):
        """Hierarchy to which this term belongs."""
        return self.__tree

    @property
    def id(self):
        """CDR ID for the Term document."""
        return self.__id

    @property
    def name(self):
        """Primary name string for the Term document."""
        return self.__name

    @property
    def focus(self):
        """Boolean: True if this term is the one the user selected."""
        return self.id == self.tree.id

    @property
    def parents(self):
        """Sequence of references to parent Terms."""
        return list(self.__parents)

    @property
    def children(self):
        """Sequence of references to child Terms."""
        return list(self.__children)

    @property
    def qc_link(self):
        """Provide navigation through the hierarchy."""
        return builder.A(self.name, href=self.qc_url)

    @property
    def cdr_id(self):
        """String version of the term's CDR document ID.

        Will be wrapped in a link unless this is the term the user picked
        (in which case, the user is already on the page we'd be linking to).
        Don't cache, in case the term appears more than once in the tree.
        """

        cdr_id = f"CDR{self.id:010d}"
        if self.focus:
            return cdr_id
        else:
            params = dict(DocId=self.id)
            url = self.control.make_url(self.control.script, **params)
            return builder.A(cdr_id, href=url)

    @property
    def qc_url(self):
        """Let the user see full information about the term."""

        params = dict(self.FILTER_PARAMS)
        params["DocId"] = str(self.id)
        return self.control.make_url(self.FILTER, **params)

    def add_child(self, child):
        """Append a child Term object to our sequence."""
        self.__children.append(child)

    def add_parent(self, parent):
        """Append a parent object to our sequence."""
        self.__parents.append(parent)

    def __lt__(self, other):
        """Make the terms sortable by name string, case insensitive."""
        return self.name.lower() < other.name.lower()

    def add_row(self, rows, level=0):
        """Create an HTML node to show this term and recurse for children.

        Pass:
            rows - sequence of rows to which we add new rows
            level - level of indent in the hierarchy

        Return:
            node object ready for insertion into an HTML tree
        """

        args = [" " * (level - 1) * 2 + "+-"] if level else []
        args += self.qc_link, " (", self.cdr_id, ")"
        row = builder.TR(builder.TD(*args))
        if self.focus:
            row.set("class", "focus")
        rows.append(row)
        for child in self.children:
            child.add_row(rows, level+1)


if __name__ == "__main__":
    "Let the script be loaded as a module."
    Control().run()
