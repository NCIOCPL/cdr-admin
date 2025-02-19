#!/usr/bin/env python

"""Report on PDQ content counts.

See JIRA ticket OCECDR-5105 for requirements.
"""

from functools import cached_property
from io import BytesIO
from openpyxl import load_workbook
from requests import get
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "PDQ Content Counts"
    SUMMARIES = [
        ("PDQ English HP summaries", "English", "Health professionals", False),
        ("PDQ Spanish HP summaries", "Spanish", "Health professionals", False),
        ("PDQ English patient summaries", "English", "Patients", False),
        ("PDQ Spanish patient summaries", "Spanish", "Patients", False),
        ("English SVPC summaries", "English", None, True),
        ("Spanish SVPC summaries", "Spanish", None, True),
    ]
    CONCEPT_PATH = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
    COLUMNS = "Documents", "Count"
    URL = "https://cdr.cancer.gov/cgi-bin/cdr/PDQContentCounts.py?format=excel"
    INSTRUCTIONS = (
        "This report pulls together counts of published PDQ content "
        "of various types for inclusion in more widely disseminated "
        "communications. Use the form below for specifying the format "
        "in which the report should be generated."
    )

    def populate_form(self, page):
        """Ask the user which flavor or report to generate."""

        if not self.fields.getvalue("prompt"):
            self.show_report()
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        page.add_output_options()

    def build_tables(self):
        """Wrap the table in a sequence."""
        return [self.table]

    @cached_property
    def table(self):
        """Used for both HTML and Excel reports."""

        rows = []
        caption = None
        for title, count in self.rows:
            rows.append([title, self.Reporter.Cell(count, right=True)])
        if self.format == "excel":
            columns = (
                self.Reporter.Column("Documents", width="250px"),
                self.Reporter.Column("Count", width="50px"),
            )
            caption = "Counts"
        else:
            columns = (
                self.Reporter.Column("Documents"),
                self.Reporter.Column("Count", classes="text-right"),
            )
        return self.Reporter.Table(rows, caption=caption, columns=columns)

    @cached_property
    def rows(self):
        """Get the data from the production server."""

        # If this isn't the production server, hand off the work to it.
        if self.session.tier.name != "PROD":
            response = get(self.URL)
            if not response.ok:
                self.bail(f"Report failed: {response.reason}")
            book = load_workbook(BytesIO(response.content))
            rows = [row for row in book.active]
            return [(row[0].value, row[1].value) for row in rows[3:]]

        # Start by counting the cancer information summaries.
        rows = []
        cursor = self.cursor

        # Change in requirements: don't include "module-only" summaries.
        subquery = self.Query("query_term", "doc_id")
        subquery.where("path = '/Summary/@ModuleOnly'")
        subquery.where("value = 'Yes'")
        for title, language, audience, svpc in self.SUMMARIES:
            query = self.Query("query_term_pub l", "COUNT(*) AS n")
            query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
            query.where(f"l.value = '{language}'")
            query.join("active_doc d", "d.id = l.doc_id")
            query.where(query.Condition("d.id", subquery, "NOT IN"))
            if audience:
                query.join("query_term_pub a", "a.doc_id = l.doc_id")
                query.where(
                    "a.path = '/Summary/SummaryMetaData/SummaryAudience'"
                )
                query.where(f"a.value = '{audience}'")
            if svpc:
                query.join("query_term_pub s", "s.doc_id = l.doc_id")
                query.where("s.path = '/Summary/@SVPC'")
                query.where("s.value = 'Yes'")
            else:
                query.outer("query_term_pub s", "s.doc_id = l.doc_id",
                            "s.path = '/Summary/@SVPC'")
                query.where("s.value IS NULL")
            count = query.execute(cursor).fetchone().n
            rows.append([title, count])

        # Next we count the drug information summaries
        query = self.Query("query_term_pub t", "COUNT(*) AS n")
        query.where("t.path = '/DrugInformationSummary/Title'")
        query.join("active_doc d", "d.id = t.doc_id")
        count = query.execute(cursor).fetchone().n
        title = "Drug information summaries"
        rows.append([title, count])

        # Now get the counts for the dictionaries.
        for dictionary in ("Cancer", "Genetics"):
            d_value = dictionary
            if d_value == "Cancer":
                d_value = "Cancer.gov"
            for language in ("English", "Spanish"):
                title = f"NCI Dictionary of {dictionary} Terms in {language}"
                name_path = "TermName"
                definition_path = "TermDefinition"
                if language == "Spanish":
                    name_path = "TranslatedName"
                    definition_path = "TranslatedTermDefinition"
                n_path = f"/GlossaryTermName/{name_path}/TermNameString"
                d_path = f"/GlossaryTermConcept/{definition_path}/Dictionary"
                query = self.Query("query_term_pub n",
                                   "COUNT(DISTINCT n.doc_id) AS n")
                query.join("active_doc a", "a.id = n.doc_id")
                query.join("query_term_pub c", "c.doc_id = n.doc_id")
                query.join("query_term_pub d", "d.doc_id = c.int_val")
                query.where(f"n.path = '{n_path}'")
                query.where(f"c.path = '{self.CONCEPT_PATH}'")
                query.where(f"d.path = '{d_path}'")
                query.where(f"d.value = '{d_value}'")
                count = query.execute(cursor).fetchone().n
                rows.append([title, count])
        query = self.Query("query_term_pub d", "COUNT(DISTINCT d.doc_id) AS n")
        query.join("active_doc a", "a.id = d.doc_id")
        query.where("d.path = '/Term/Definition/DefinitionType'")
        query.join("query_term_pub t", "t.doc_id = d.doc_id")
        query.join("query_term_pub s", "s.doc_id = t.int_val")
        query.where("t.path = '/Term/SemanticType/@cdr:ref'")
        query.where("s.path = '/Term/PreferredName'")
        query.where("s.value = 'Drug/agent'")
        count = query.execute(cursor).fetchone().n
        title = "NCI Drug Dictionary Terms"
        rows.append([title, count])

        # For media, exclude images which we are reusing from journals, etc.
        image_encoding_path = "/Media/PhysicalMedia/ImageData/ImageEncoding"
        video_encoding_path = "/Media/PhysicalMedia/VideoData/VideoEncoding"
        query = self.Query("query_term_pub", "doc_id").unique()
        query.where("path LIKE '/Media/PermissionInformation%'")
        reused = {row.doc_id for row in query.execute(cursor).fetchall()}
        query = self.Query("query_term_pub", "doc_id").unique()
        query.where("path = '/Media/TranslationOf/@cdr:ref'")
        spanish = {row.doc_id for row in query.execute(cursor).fetchall()}
        query = self.Query("query_term_pub e", "e.doc_id").unique()
        query.join("active_doc a", "a.id = e.doc_id")
        query.where(f"e.path = '{image_encoding_path}'")
        query.where("e.path = '/Media/PhysicalMedia/ImageData/ImageEncoding'")
        images = {row.doc_id for row in query.execute(cursor).fetchall()}
        query = self.Query("query_term_pub e", "e.doc_id").unique()
        query.join("active_doc a", "a.id = e.doc_id")
        query.where(f"e.path = '{video_encoding_path}'")
        video = {row.doc_id for row in query.execute(cursor).fetchall()}
        title = "English Biomedical Images and Animations"
        count = len(((images - reused) | video) ^ spanish)
        rows.append([title, count])
        title = "Spanish Biomedical Images and Animations"
        count = len(((images - reused) | video) & spanish)
        rows.append([title, count])
        return rows


if __name__ == "__main__":
    Control().run()
