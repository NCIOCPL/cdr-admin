#!/usr/bin/env python

"""Show recently published media documents.

Split out from PubStatsByDate.py.
"""

from functools import cached_property
from cdrcgi import Controller
from datetime import date, timedelta


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Media Doc Publishing Report"
    AUDIENCES = "Patients", "Health_Professionals"
    LANGUAGES = "English", "Spanish"
    PATHS = (
        "/Media/MediaContent/Captions/MediaCaption/@audience",
        "/Media/MediaContent/ContentDescriptions/ContentDescription/@audience",
    )
    COLUMNS = (
        "CDR ID",
        "Media Title",
        "First Pub Date",
        "Version Date",
        "Last Version Publishable",
        "Blocked from VOL",
    )
    FIELDS = (
        "t.doc_id",
        "t.value AS title",
        "d.first_pub",
        "v.dt",
        "b.value as blocked",
        "v.publishable",
        "a.value as audience"
    )

    def build_tables(self):
        """Assemble the published media documents table."""

        start = str(self.start)[:10]
        end = str(self.end)[:10]
        caption = f"Media Documents Published Between {start} and {end}"
        opts = dict(caption=caption, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask the user for the report's parameters.

        Pass:
            page - HTMLPage object where we put the form
        """

        end = date.today()
        start = end - timedelta(7)

        fieldset = page.fieldset("Language(s)")
        for language in self.LANGUAGES:
            if language == "English":
                opts = dict(value=language, checked=True)
            else:
                opts = dict(value=language)
            fieldset.append(page.checkbox("language", **opts))
        page.form.append(fieldset)

        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)
        page.form.append(page.hidden_field("doctype", "Media"))
        page.form.append(page.hidden_field("VOL", "Y"))

        # Include instructions for the audience option since these
        # are used differently for this report.
        # --------------------------------------------------------
        instruction = ("NOTE: The audience option is working differently for "
                       "this report. Selecting both audiences will display "
                       "only those documens for which BOTH audiences exist  "
                       "rather than documents for which either one of the "
                       "audiences exists. Similarily for selecting one "
                       "audience only. In this case a document will not be "
                       "included if a caption for the other audience type "
                       "also exists")
        fieldset = page.fieldset("Audience(s)")
        para = page.B.P(instruction)
        fieldset.append(para)
        for audience in self.AUDIENCES:
            opts = dict(value=audience, checked=True)
            fieldset.append(page.checkbox("audience", **opts))
        page.form.append(fieldset)

    @cached_property
    def audience(self):
        """Audience selected from the form, if only one."""

        audiences = self.fields.getlist("audience")
        return audiences[0] if len(audiences) == 1 else None

    @cached_property
    def end(self):
        """End of the date range for the report."""

        end = self.parse_date(self.fields.getvalue("end")) or date.today()
        return f"{end} 23:59:59"

    @cached_property
    def language(self):
        """Language selected from the form, if only one."""

        languages = self.fields.getlist("language")
        return languages[0] if len(languages) == 1 else None

    @cached_property
    def rows(self):
        """Values for the report table."""

        subquery = self.Query("pub_proc_doc d", "d.doc_id").unique()
        subquery.join("pub_proc p", "p.id = d.pub_proc")
        subquery.where(subquery.Condition("p.started", self.start, ">="))
        subquery.where(subquery.Condition("p.started", self.end, "<="))
        subquery.where("p.pub_subset LIKE 'Push%'")
        subquery.where("p.status = 'Success'")
        subquery.where("d.removed = 'N'")
        last_ver = self.Query("doc_version", "MAX(num)").where("id = v.id")
        query = self.Query("query_term t", *self.FIELDS).unique()
        query.order("t.value")
        query.join("doc_version v", "t.doc_id = v.id")
        query.join("document d", "v.id = d.id")
        query.join("query_term c", "t.doc_id = c.doc_id")
        query.outer("query_term b", "t.doc_id = b.doc_id",
                    "b.path = '/Media/@BlockedFromVOL'")
        # The l.value identifies the language (see below)
        query.outer("query_term l", "t.doc_id = l.doc_id",
                    "l.path = '/Media/TranslationOf/@cdr:ref'")
        query.where("t.path = '/Media/MediaTitle'")
        query.where("c.path = '/Media/MediaContent/Categories/Category'")
        query.where("c.value NOT IN ('pronunciation', 'meeting recording')")
        query.where(query.Condition("d.id", subquery, "IN"))
        query.where(query.Condition("v.num", last_ver))

        query.join("query_term_pub a", "a.doc_id = d.id")
        query.where(query.Condition("a.path", self.PATHS, "IN"))

        # The language is determined indirectly.  If a TranslationOf
        # element exists the document is a Spanish translation,
        # otherwise the document is English.  This where-clause
        # adjusts the query accordingly.  If either both or none of
        # the languages are selected the report displays both
        # languages.
        # ---------------------------------------------------------
        if self.language == 'English':
            query.where("l.value IS NULL")  # English
        elif self.language == 'Spanish':
            query.where("l.value IS NOT NULL")  # Spanish

        #  Query for all media, including HP and Patien records
        all_rows = query.execute(self.cursor).fetchall()

        # Users want to use the audience check boxes a little differently
        # Instead of selecting all records with audience HP OR patient when
        # checking both audiences, they want to display records with
        # audience HP AND patient instead.
        # Similarily, when the Patients checkbox is selected they only want
        # to include those documents that include ONLY a patient caption,
        # not those that also include an HP caption.
        # Using sets to determine the appropriate intersections
        # -----------------------------------------------------------------
        hp = set()
        pat = set()
        selected = set()

        for row in all_rows:
            if row[6] == 'Patients':
                pat.add(row[0])
            else:
                hp.add(row[0])

        patandhp = pat & hp
        pat_only = pat - hp
        hp_only = hp - pat

        # self.audience doesn't exist if both audience checkboxes have
        # been selected
        # ------------------------------------------------------------
        audience = ''
        if self.audience:
            if self.audience == 'Patients':
                selected = pat_only
            else:
                selected = hp_only
            # audience = self.audience.replace(" ", "_")
        else:
            audience = 'both'
            selected = patandhp

        rows = []

        for row in all_rows:
            if row[0] in selected:
                url = f"GetCdrImage.py?id=CDR{row.doc_id}.jpg"
                first_pub = str(row.first_pub)[:10] if row.first_pub else ""
                version_date = str(row.dt)[:10] if row.dt else ""
                blocked = row.blocked[0] if row.blocked else ""

                # Since records for HP and Patients are listed twice in
                # the select result we're skipping one of the two
                # ----------------------------------------------------------
                if audience == 'both':
                    if row.audience == 'Health_professionals':
                        continue

                rows.append([
                    self.Reporter.Cell(row.doc_id, href=url, center=True),
                    row.title,
                    self.Reporter.Cell(first_pub, center=True),
                    self.Reporter.Cell(version_date, center=True),
                    self.Reporter.Cell(row.publishable, center=True),
                    self.Reporter.Cell(blocked, center=True),
                ])
        return rows

    @cached_property
    def start(self):
        """Beginning of the date range for the report."""
        return self.parse_date(self.fields.getvalue("start")) or "2001-01-01"

    @cached_property
    def wide_css(self):
        """Give the report table more room."""
        return self.Reporter.Table.WIDE_CSS


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
