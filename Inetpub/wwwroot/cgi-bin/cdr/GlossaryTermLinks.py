#!/usr/bin/env python

"""Report of documents linking to a specified glossary term.
"""

from cdrcgi import Controller, Reporter
from cdrapi.docs import Doc

class Control(Controller):
    """Report logic."""

    SUBTITLE = "Glossary Term Links QC Report"
    NAME_PATH = "/GlossaryTermName/TermName/TermNameString"
    SOURCE_PATH = "/GlossaryTermName/TermName/TermNameSource"
    COLUMNS = (
        Reporter.Column("Doc ID", classes="doc-id"),
        Reporter.Column("Doc Title", classes="doc-title"),
        Reporter.Column("Element Name", classes="element-name"),
        Reporter.Column("Fragment ID", classes="frag-id"),
    )

    def populate_form(self, page):
        """Add the two fields to the form for selecting a term name."""

        fieldset = page.fieldset("Select a Glossary Term by Name or ID")
        fieldset.append(page.text_field("id", label="CDR ID"))
        fieldset.append(page.text_field("name", label="Term Name"))
        page.form.append(fieldset)

    def build_tables(self):
        """Assemble the report tables, one for each linking document type."""

        tables = []
        for doctype in sorted(self.types):
            rows = []
            for linker in self.types[doctype]:
                rows += linker.rows
            opts = dict(cols=self.COLUMNS, caption=doctype, classes="linkers")
            tables.append(self.Reporter.Table(rows, **opts))
        return tables

    def show_report(self):
        """Override the base class version to add a top table and css."""

        css = (
            "#name-and-source tr * { padding: 2px 5px; }",
            "#name-and-source { width: auto; }",
            "#name-and-source th { text-align: right; }",
            ".doc-id { width: 125px; }",
            ".doc-title { width: auto; }",
            ".element-name {width: 150px; }",
            ".frag-id { width: 100px; }",
            "table { width: auto; margin-top: 50px; }",
            "table.linkers { width: 90%; }",
        )
        page = self.report.page
        h2 = page.B.H2("Documents Linked To Glossary Term Names Report")
        h2.set("class", "center")
        page.body.insert(1, h2)
        table = page.B.TABLE(
            page.B.CAPTION("Glossary Term"),
            page.B.TR(page.B.TH("Name"), page.B.TD(self.name)),
            page.B.TR(page.B.TH("Source"), page.B.TD(self.source))
        )
        table.set("id", "name-and-source")
        page.body.insert(2, table)
        h4 = page.B.H4("Documents Linked to Term Name")
        h4.set("class", "center emphasis")
        page.body.insert(3, h4)
        self.report.page.add_css("\n".join(css))
        self.report.send()

    @property
    def types(self):
        """Dictionary of linking document lists, indexed by document type."""

        if not hasattr(self, "_types"):
            fields = "d.id", "t.name"
            query = self.Query("document d", *fields).unique().order("d.id")
            query.join("doc_type t", "t.id = d.doc_type")
            query.join("query_term l", "l.doc_id = d.id")
            query.where(query.Condition("l.int_val", self.id))
            self._types = {}
            for row in query.execute(self.cursor).fetchall():
                doc = LinkingDoc(self, row.id)
                if row.name not in self._types:
                    self._types[row.name] = [doc]
                else:
                    self._types[row.name].append(doc)
        return self._types

    @property
    def cdr_id(self):
        """String version if the glossary term's CDR ID."""

        if not hasattr(self, "_cdr_id"):
            self._cdr_id = f"CDR{self.id:010d}"
        return self._cdr_id

    @property
    def id(self):
        """Integer for the glossary term name document ID."""

        if not hasattr(self, "_id"):
            id = self.fields.getvalue("id")
            if id:
                try:
                    self._id = Doc.extract_id(id)
                except:
                    self.bail(f"Invalid id: {id!r}")
            else:
                name = self.fields.getvalue("name")
                if not name:
                    self.show_form()
                query = self.Query("query_term", "doc_id").unique()
                query.where(f"path = '{self.NAME_PATH}'")
                query.where(query.Condition("value", name))
                rows = query.execute(self.cursor).fetchall()
                if len(rows) > 1:
                    self.bail(f"Ambiguous term name: {name!r}")
                elif not rows:
                    self.bail(f"Unknown term {name!r}")
                self._id = rows[0].doc_id
        return self._id

    @property
    def name(self):
        """String for the glossary term name."""

        if not hasattr(self, "_name"):
            query = self.Query("query_term", "value")
            query.where(f"path = '{self.NAME_PATH}'")
            query.where(query.Condition("doc_id", self.id))
            rows = query.execute(self.cursor).fetchall()
            self._name = rows[0].value
        return self._name

    @property
    def source(self):
        """Source for the term name, if any."""

        if not hasattr(self, "_source"):
            query = self.Query("query_term", "value")
            query.where(f"path = '{self.SOURCE_PATH}'")
            query.where(query.Condition("doc_id", self.id))
            rows = query.execute(self.cursor).fetchall()
            self._source = rows[0].value if rows else None
        return self._source

    @property
    def cdr_id(self):
        """Display version of the term name document ID."""

        if not hasattr(self, "_cdr_id"):
            self._cdr_id = f"CDR{self.id:010d}"
        return self._cdr_id

    @property
    def xpath(self):
        """Search path for finding links to this document."""

        if not hasattr(self, "_xpath"):
            tests = (
                f"@cdr:ref='{self.cdr_id}'",
                f"@cdr:href='{self.cdr_id}'",
            )
            self._xpath = f"//*[{' or '.join(tests)}]"
        return self._xpath


class LinkingDoc:
    """Document linking to our glossary term name."""

    XPATH_OPTS = dict(namespaces=Doc.NSMAP)
    CDR_ID = f"{{{Doc.NS}}}id"

    def __init__(self, control, id):
        """Capture the caller's values."""

        self.__control = control
        self.__id = id

    @property
    def id(self):
        """CDR ID for the linking document."""
        return self.__id

    @property
    def control(self):
        """Access to information about the linked glossary term name."""
        return self.__control

    @property
    def doc(self):
        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id)
        return self._doc

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            rows = []
            root = self.doc.root
            for node in root.xpath(self.control.xpath, **self.XPATH_OPTS):
                parent = node.getparent()
                tag = parent.tag
                node_id = str(parent.get(self.CDR_ID))
                row = (
                    Reporter.Cell(self.doc.cdr_id, center=True),
                    self.doc.title,
                    tag,
                    Reporter.Cell(node_id, center=True),
                )
                rows.append(row)
            self._rows = rows
        return self._rows


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
