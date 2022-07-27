#!/usr/bin/env python

"""Report on documents which link to a specified document.
"""

from collections import defaultdict
from cdrcgi import Controller
from cdrapi.docs import Doc, Doctype


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "Linked Documents Report"
    INSTRUCTIONS = (
        "Enter the criteria for the report. "
        "You can either enter the CDR ID for the linked document "
        "or you can provide the title of that document (and optionally "
        "a document type). "
        "If you enter a title string which matches the start of more than "
        "one document title (for that document type, if you have selected "
        "a type), you will be asked to select the document from a list of "
        "those which match. "
        "You can also specify a fragment ID to further restrict the links "
        "which are reported to those which link to one specific element of "
        "the target document. "
        "You can restrict the report to links from only a specified document "
        "type, or you can include links from any document type. "
        "Finally, you can exclude or include links from documents which "
        "have been blocked."
    )

    def build_tables(self):
        """Assemble the tables for the report."""

        if not self.target_id:
            if self.titles or not self.fragment:
                self.show_form()
            else:
                self.bail("no matching target documents found")
        else:
            return [self.target_table] + self.linking_tables

    def populate_form(self, page):
        """Put the fields for the report options on the form.

        Pass:
            page - HTMLPage object on which to place the field sets
        """

        if self.target_id:
            return self.show_report()
        elif self.titles:
            fieldset = page.fieldset("Select Linked Document For Report")
            for title in self.titles:
                opts = dict(value=title.id, label=title.display)
                if title.tooltip:
                    opts["tooltip"] = title.tooltip
                fieldset.append(page.radio_button("doc_id", **opts))
            page.form.append(fieldset)
            page.form.append(page.hidden_field("frag_id", self.fragment_id))
            value = self.linking_type
            page.form.append(page.hidden_field("linking_type", value))
            value = "Y" if self.include_blocked_documents else "N"
            page.form.append(page.hidden_field("with_blocked", value))
            page.add_css("fieldset { width: 625px; }")
        else:
            fieldset = page.fieldset("Instructions")
            fieldset.append(page.B.P(self.INSTRUCTIONS))
            page.form.append(fieldset)
            fieldset = page.fieldset("Linked Document")
            fieldset.append(page.text_field("doc_id", label="Document ID"))
            fieldset.append(page.text_field("frag_id", label="Fragment ID"))
            fieldset.append(page.text_field("doc_title", label="Doc Title"))
            opts = dict(label="Doc Type", options=[""]+self.doctypes)
            fieldset.append(page.select("linked_type", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Linking Documents")
            opts = dict(label="Doc Type", options=[("", "Any")]+self.doctypes)
            fieldset.append(page.select("linking_type", **opts))
            subset = page.fieldset("Links From Blocked Documents")
            opts = dict(label="Include", value="Y")
            subset.append(page.radio_button("with_blocked", **opts))
            opts = dict(label="Exclude", value="N", checked=True)
            subset.append(page.radio_button("with_blocked", **opts))
            fieldset.append(subset)
            page.form.append(fieldset)

    @property
    def columns(self):
        """What we show at the top of the link table columns."""

        if not hasattr(self, "_columns"):
            self._columns = (
                self.Reporter.Column("Doc ID", width="80px"),
                self.Reporter.Column("Doc Title", width="550px"),
                self.Reporter.Column("Linking Element", width="200px"),
                self.Reporter.Column("Fragment ID", width="150px"),
            )
        return self._columns

    @property
    def doc_id(self):
        """String for the CDR ID of the report's link target."""

        if not hasattr(self, "_doc_id"):
            self._doc_id = self.fields.getvalue("doc_id")
            if not self._doc_id:
                self._doc_id = self.fields.getvalue("DocId")
        return self._doc_id

    @property
    def doctypes(self):
        """Sequence of strings for the document type picklists."""

        if not hasattr(self, "_doctypes"):
            self._doctypes = Doctype.list_doc_types(self.session)
        return self._doctypes

    @property
    def fragment(self):
        """String for a summary title fragment."""
        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("doc_title")
        return self._fragment

    @property
    def fragment_id(self):
        """String for an optional ID identifying a portion of a document."""

        if not hasattr(self, "_fragment_id"):
            self._fragment_id = self.fields.getvalue("frag_id")
            if not self._fragment_id:
                self._fragment_id = self.fields.getvalue("FragId")
            if not self._fragment_id:
                if self.doc_id and "#" in self.doc_id:
                    self._fragment_id = self.doc_id.split("#")[1]
        return self._fragment_id

    @property
    def include_blocked_documents(self):
        """True if the report should include blocked documents."""
        return self.fields.getvalue("with_blocked") == "Y"

    @property
    def linked_type(self):
        """String for the document type of the report's linked document."""

        if not hasattr(self, "_linked_type"):
            self._linked_type = self.fields.getvalue("linked_type")
            if self._linked_type and self._linked_type not in self.doctypes:
                self.bail()
        return self._linked_type

    @property
    def linking_tables(self):
        """Sequence of tables for each linking document type."""

        if not self.links:
            nada = "No link to this document found."
            column = self.Reporter.Column(nada, width="500px")
            return [self.Reporter.Table([], columns=[column])]
        tables = []
        for doctype in sorted(self.links):
            rows = []
            for link in self.links[doctype]:
                cdr_id = f"CDR{link.id:d}"
                url = self.make_url("QcReport.py", DocId=cdr_id)
                row = (
                    self.Reporter.Cell(cdr_id, href=url),
                    link.title,
                    link.source_elem,
                    link.target_frag,
                )
                rows.append(row)
            caption = f"Links From {doctype} Documents"
            opts = dict(columns=self.columns, caption=caption)
            tables.append(self.Reporter.Table(rows, **opts))
        return tables

    @property
    def linking_type(self):
        """String for the document type of the report's linking documents."""

        if not hasattr(self, "_linking_type"):
            self._linking_type = self.fields.getvalue("linking_type")
            if self._linking_type and self._linking_type not in self.doctypes:
                self.bail()
        return self._linking_type

    @property
    def links(self):
        """Links to be shown on the report."""

        if not hasattr(self, "_links"):
            columns = (
                "t.name AS doc_type",
                "d.title",
                "n.source_elem",
                "n.target_frag",
                "d.id",
            )
            query = self.Query("document d", *columns).order(2, 3, 4)
            query.join("doc_type t", "t.id = d.doc_type")
            query.join("link_net n", "d.id = n.source_doc")
            query.where(query.Condition("n.target_doc", self.target_id))
            if self.linking_type:
                query.where(query.Condition("t.name", self.linking_type))
            if self.fragment_id:
                query.where(query.Condition("n.target_frag", self.fragment_id))
            if not self.include_blocked_documents:
                query.where("d.active_status = 'A'")
            self._links = defaultdict(list)
            summary_types = {}
            for row in query.execute(self.cursor).fetchall():
                doc_type = row.doc_type
                if doc_type == "Summary":
                    if row.id not in summary_types:
                        summary_types[row.id] = self.__get_summary_type(row.id)
                    doc_type = summary_types[row.id]
                self._links[doc_type].append(row)
        return self._links

    @property
    def target_id(self):
        """Integer for the CDR ID of the report's link target."""

        if not hasattr(self, "_target_id"):
            self._target_id = None
            if self.doc_id:
                try:
                    self._target_id = Doc.extract_id(self.doc_id)
                except Exception:
                    self.bail("invalid document ID format")
            elif len(self.titles) == 1:
                self._target_id = self.titles[0].id
        return self._target_id

    @property
    def target_table(self):
        doc = Doc(self.session, id=self.target_id)
        Cell = self.Reporter.Cell
        rows = (
            (Cell("Document Type", bold=True, right=True), doc.doctype.name),
            (Cell("Document Title", bold=True, right=True), doc.title),
            (Cell("Document ID", bold=True, right=True), doc.id),
        )
        opts = dict(caption="Target Document", id="target-info")
        return self.Reporter.Table(rows, **opts)

    @property
    def titles(self):
        """Sequence of `DocTitle` objects for titles matching user's string."""

        if not hasattr(self, "_titles"):
            self._titles = []
            if self.fragment:
                pattern = f"{self.fragment}%"
                query = self.Query("document d", "d.id", "d.title").order(2)
                if self.linked_type:
                    query.join("doc_type t", "t.id = d.doc_type")
                    query.where(query.Condition("t.name", self.linked_type))
                query.where(query.Condition("d.title", pattern, "LIKE"))

                class DocTitle:
                    def __init__(self, row):
                        self.id = row.id
                        self.tooltip = None
                        if len(row.title) > 60:
                            title = row.title[:57] + "..."
                            self.tooltip = row.title
                        else:
                            title = row.title
                        self.display = f"{Doc.normalize_id(row.id)}: {title}"
                for row in query.execute(self.cursor).fetchall():
                    self._titles.append(DocTitle(row))
        return self._titles

    def __get_summary_type(self, doc_id):
        """Get string showing language and audience for summary document.

        Pass:
          doc_id - integer for unique CDR document ID

        Return:
          string in the form "Summary (Language Audience)"
        """

        query = self.Query("query_term", "value")
        query.where("path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where(query.Condition("doc_id", doc_id))
        rows = query.execute(self.cursor).fetchall()
        value = rows[0][0] if rows else "Unspecified Audience"
        audience = "HP" if value.startswith("H") else "Patient"
        query = self.Query("query_term", "value")
        query.where("path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("doc_id", doc_id))
        rows = query.execute(self.cursor).fetchall()
        language = rows[0][0] if rows else "Unspecified Language"
        return f"Summary ({language} {audience})"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
