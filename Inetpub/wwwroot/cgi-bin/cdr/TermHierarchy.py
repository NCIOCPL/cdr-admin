#!/usr/bin/env python

"""Navigate term hierarchy.
"""

from functools import cached_property
from cdrcgi import Controller, BasicWebPage
from cdrapi.docs import Doc
from lxml.html import builder


class Control(Controller):
    """Access to the database and HTML generation classes."""

    TITLE = "CDR Terminology"
    SUBTITLE = "Terminology Hierarchy Display"
    PATHS = "/Term/PreferredName", "/Term/OtherName/OtherTermName"
    CSS = (
        "table { margin-bottom: 2rem; }",
        "caption { text-align: left; padding-left: 0; }",
        "td {",
        "  border: none; color: #00e; font-family: monospace;",
        "  white-space: pre; font-size: 10pt; padding: 0; margin: 0;",
        "}",
        "a { text-decoration: none; white-space: pre; color: #00e; }",
        "a:visited { color: #00e; }",
        ".focus * { color: red; font-weight: bold; }",
        "#instructions {",
        "  font-style: italic; border: solid 1px black; display: inline-block;"
        "  margin: 1rem 0; padding: 1rem; color: green;",
        "}",
    )

    def populate_form(self, page):
        """If we don't have a term ID, get one.

        Pass:
            page - HTMLPage object on which to put the form field
        """

        if self.ready:
            return self.show_report()
        if self.terms:
            page.form.append(page.hidden_field("TermName", self.name))
            fieldset = page.fieldset("Select Term")
            checked = True
            for id, title in self.terms:
                opts = dict(label=title, value=id, checked=checked)
                fieldset.append(page.radio_button("DocId", **opts))
                checked = False
        else:
            fieldset = page.fieldset("Term ID or Name for Hierarchy Display")
            opts = dict(label="CDR ID", value=self.id)
            fieldset.append(page.text_field("DocId", **opts))
            opts = dict(label="Term Name Fragment", value=self.name)
            fieldset.append(page.text_field("TermName", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Override base class, because we're not using the Report class.

        Loop back to the cascading form for names if we don't have an id.
        """

        if not self.ready:
            return self.show_form()
        report = BasicWebPage()
        instructions = report.B.DIV(
            report.B.DIV("Click term name to view formatted term document."),
            report.B.DIV("Click document ID to navigate tree."),
            id="instructions",
        )
        report.head.append(report.B.STYLE("\n".join(self.CSS)))
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        report.wrapper.append(instructions)
        for table in self.tree.tables:
            report.wrapper.append(table)
        report.wrapper.append(self.footer)
        report.send()

    @cached_property
    def id(self):
        """ID for term we'll use as our starting location in the hierarchy."""
        return self.fields.getvalue("DocId", "").strip()

    @cached_property
    def name(self):
        """Term name fragment entered by user."""
        return self.fields.getvalue("TermName", "").strip()

    @cached_property
    def ready(self):
        """True if we have everything needed for the report."""

        if not self.id and not self.name:
            if self.request:
                message = "You must enter an ID or title fragment."
                self.alerts.append(dict(message=message, type="error"))
            return False
        if self.id:
            try:
                doc = Doc(self.session, id=self.id)
                doctype = doc.doctype.name
                if doctype != "Term":
                    message = f"CDR{doc.id} is a {doctype} document."
                    self.alerts.append(dict(message=message, type="warning"))
                    return False
                self.id = doc.id
            except Exception:
                self.logger.exception("checking %s", self.id)
                message = f"Document {self.id} not found."
                self.alerts.append(dict(message=message, type="warning"))
                return False
        elif not self.terms:
            message = f"No matches for {self.name!r}."
            self.alerts.append(dict(message=message, type="warning"))
            return False
        elif len(self.terms) > 1:
            message = f"Multiple matches found for {self.name!r}."
            self.alerts.append(dict(message=message, type="info"))
            return False
        else:
            self.id = self.terms[0][0]
        if self.id not in self.tree.terms:
            message = (
                f"CDR{self.id} does not specify any relationships "
                "to any other documents."
            )
            self.alerts.append(dict(message=message, type="warning"))
            self.id = None
            return False
        return True

    @cached_property
    def same_window(self):
        """Avoid opening new browser tabs."""
        return [self.SUBMIT]

    @cached_property
    def terms(self):
        """ID/title tuples for terms matching the user's string."""

        if not self.name:
            return None
        fields = "d.id", "d.title"
        paths = ", ".join([f"'{path}'" for path in self.PATHS])
        query = self.Query("document d", *fields).order("d.title")
        query.join("query_term n", "n.doc_id = d.id")
        query.where(f"n.path IN ({paths})")
        query.where(query.Condition("n.value", f"%{self.name}%", "LIKE"))
        rows = query.execute(self.cursor).fetchall()
        return [tuple(row) for row in rows]

    @cached_property
    def tree(self):
        """Slice of the term hierarchy to be displayed."""
        return Tree(self)


class Tree:
    """Portion of the CDR term hierarchy surrounding the user's selecte term.
    """

    def __init__(self, control):
        """Save the reference to the the caller.

        Pass:
            control - access to the current session, the form, logging, etc.
        """

        self.control = control

    @cached_property
    def id(self):
        """Term ID selected by the user for the focus of the display."""
        return self.control.id

    @cached_property
    def tables(self):
        """One table for each parent-less root."""

        tables = []
        for root in self.roots:
            rows = []
            root.add_row(rows)
            caption = builder.CAPTION(f"Hierarchy from {root.name}")
            tables.append(builder.TABLE(caption, *rows))
        return tables

    @cached_property
    def roots(self):
        """Nodes at the top of the tree (no parents)."""

        roots = []
        for term in self.terms.values():
            if not term.parents:
                roots.append(term)
        return roots

    @cached_property
    def terms(self):
        """Dictionary of terms surrounding the user's pick in the tree."""

        doc = Doc(self.control.session, id=self.id)
        tree = doc.get_tree(depth=1)
        terms = {}
        for id, name in tree.names.items():
            focus = id == self.id
            terms[id] = Term(self, id, name, focus)
        for r in tree.relationships:
            terms[r.parent].children.append(terms[r.child])
            terms[r.child].parents.append(terms[r.parent])
        return terms


class Term:
    """CDR Term document, with information about its position in the tree.

    Avoid property caching for any HTML elements, as the term may need
    to be display more than once in the hierarchy.
    """

    FILTER = "Filter.py"
    FILTERS = (
        "name:Denormalization Filter (1/1): Terminology",
        "name:Terminology QC Report Filter",
    )

    def __init__(self, tree, id, name, focus):
        """Capture the caller's values.

        Pass:
            tree - hierarchy to which this term belongs
            id - CDR ID for the term document
            name - primary name string for the Term document
        """

        self.tree = tree
        self.id = id
        self.name = name
        self.parents = []
        self.children = []

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

    @cached_property
    def control(self):
        """Access to HTML and URL generation facilities."""
        return self.tree.control

    @cached_property
    def focus(self):
        """Boolean: True if this term is the one the user selected."""
        return int(self.id) == int(self.tree.id)

    @property
    def qc_link(self):
        """Let the user see full information about the term (uncached)."""
        return builder.A(self.name, href=self.qc_url, target="_blank")

    @cached_property
    def qc_url(self):
        """Used to create the link to the QC report."""

        params = dict(filter=self.FILTERS, DocId=self.id)
        return self.control.make_url(self.FILTER, **params)


if __name__ == "__main__":
    "Let the script be loaded as a module."
    Control().run()
