#!/usr/bin/env python

"""Show Media documents, optionally filtered by category and/or diagnosis.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Media Lists"
    LOGNAME = "MediaLists"
    DIAGNOSIS_PATH = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
    CATEGORY_PATH = "/Media/MediaContent/Categories/Category"
    MEDIA_TYPES = "Any", "Image", "Sound", "Video"

    def build_tables(self):
        """Assemble the report and return it."""

        tables = []

        # Getting total records by category
        totals = self.category_count

        # Only display the table with counts by category if at least
        # one category has been selected.
        # Add a final row with the total (total of rows displayed)
        # ----------------------------------------------------------
        if self.category:
            cat_columns = "Category", "Count"
            cat_rows = []

            for cat in self.category:
                cat_rows.append([cat, totals[cat]])
            cat_rows.append(['Total  ========>', len(self.rows)])

            caption = "Count for Conditions"
            cat_opts = dict(columns=cat_columns, caption=caption)
            cat_opts["id"] = "totals-table"
            tables.append(self.Reporter.Table(cat_rows, **cat_opts))

        opts = dict(caption=self.caption, columns=self.columns)
        tables.append(self.Reporter.Table(self.rows, **opts))
        return tables

    @cached_property
    def report_css(self):
        return """\
.report .usa-table { width: auto; }
#totals-table th:last-child, #totals-table td:last-child {
  text-align: right;
}"""
    def populate_form(self, page):
        """Ask the user for the report's parameters.

        Pass:
            page - HTMLPage object on which the form is drawn
        """

        fieldset = page.fieldset("Report Filtering")
        opts = dict(options=["all"]+self.diagnoses, multiple=True)
        fieldset.append(page.select("diagnosis", **opts))
        opts["options"] = ["all"] + self.categories
        fieldset.append(page.select("category", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        opts = dict(label="Include CDR ID", value="show_id")
        fieldset.append(page.checkbox("options", **opts))
        opts = dict(label="Exclude blocked documents", value="active")
        fieldset.append(page.checkbox("options", **opts))
        opts = dict(label="Exclude non-publishable documents", value="pub")
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Language")
        fieldset.append(page.checkbox("language", label="English", value="en"))
        fieldset.append(page.checkbox("language", label="Spanish", value="es"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Media Type")
        checked = True
        for t in self.MEDIA_TYPES:
            opts = dict(label=t, value=t, checked=checked)
            checked = False
            fieldset.append(page.radio_button("type", **opts))
        page.form.append(fieldset)

    @cached_property
    def caption(self):
        """Strings to be displayed immediately above the report table."""

        s = "" if len(self.rows) == 1 else "s"
        caption = [
            f"{len(self.rows)} Media Document{s}",
            "Report Filtering",
            f"Diagnosis: {self.diagnosis_names}",
            f"Condition: {self.category_names}",
            f"Media Type: {self.type}",
        ]
        if "active" in self.options:
            caption.append("Excluding blocked documents")
        if "pub" in self.options:
            caption.append("Excluding non-publishable documents")
        if len(self.languages) == 1:
            lang = "English" if "en" in self.languages else "Spanish"
            caption.append(f"Language: {lang}")
        return caption

    @cached_property
    def categories(self):
        """ID/name tuples of the category terms for the form picklist."""

        query = self.Query("query_term", "value").order("value").unique()
        query.where("path = '/Media/MediaContent/Categories/Category'")
        query.where("value <> '' AND value <> 'meeting recording'")
        return [row.value for row in query.execute(self.cursor).fetchall()]

    @cached_property
    def category(self):
        """Categories selected by the user for filtering the report."""

        categories = self.fields.getlist("category")
        categories = [] if "all" in categories else categories
        self.logger.info("categories selected: %s", categories)
        return categories

    @cached_property
    def category_count(self):
        """Count by category for the count table."""

        category_count = {}
        table = "query_term_pub" if "pub" in self.options else "query_term"
        fields = ["m.doc_id", "m.value"] if self.show_id else ["m.value"]
        for category in self.category:
            query = self.Query(f"{table} m", *fields).unique()
            query.order("m.value")
            query.where("m.path = '/Media/MediaTitle'")
            if "active" in self.options:
                query.join("active_doc a", "a.id = m.doc_id")
            if self.category:
                query.join(f"{table} c", "c.doc_id = m.doc_id")
                query.where(query.Condition("c.path", self.CATEGORY_PATH))
                query.where(query.Condition("c.value", category, "IN"))
            if self.diagnosis:
                query.join(f"{table} d", "d.doc_id = m.doc_id")
                query.where(query.Condition("d.path", self.DIAGNOSIS_PATH))
                query.where(query.Condition("d.int_val", self.diagnosis,
                                            "IN"))
            if len(self.languages) == 1:
                if "en" in self.languages:
                    query.outer(f"{table} t", "t.doc_id = m.doc_id",
                                "t.path = '/Media/TranslationOf/@cdr:ref'")
                    query.where("t.doc_id IS NULL")
                else:
                    query.join(f"{table} t", "t.doc_id = m.doc_id")
                    query.where("t.path = '/Media/TranslationOf/@cdr:ref'")
            if self.type != "Any":
                pt = self.type
                path = f"/Media/PhysicalMedia/{pt}Data/{pt}Encoding"
                query.join(f"{table} p", "p.doc_id = m.doc_id")
                query.where(f"p.path = '{path}'")
            rows = query.execute(self.cursor).fetchall()
            self.logger.info(f"{len(rows)} rows for {category} found")
            category_count[category] = len(rows)
        return category_count

    @cached_property
    def category_names(self):
        """Display the category filtering selected for the report."""

        if not self.category:
            return "All Categories"
        return ", ".join(sorted(self.category))

    @cached_property
    def columns(self):
        """Column header(s) for the report table (might be only one)."""

        columns = []
        if self.show_id:
            columns = [self.Reporter.Column("Doc ID", width="80px")]
        columns.append(self.Reporter.Column("Doc Title", width="800px"))
        return columns

    @cached_property
    def diagnoses(self):
        """ID/name tuples of the diagnosis terms for the form picklist."""

        query = self.Query("query_term t", "t.doc_id", "t.value").unique()
        query.order("t.value")
        query.join("query_term m", "m.int_val = t.doc_id")
        query.where("t.path = '/Term/PreferredName'")
        query.where(query.Condition("m.path", self.DIAGNOSIS_PATH))
        return [tuple(row) for row in query.execute(self.cursor).fetchall()]

    @cached_property
    def diagnosis(self):
        """Diagnoses selected by the user for filtering the report."""

        diagnoses = []
        values = self.fields.getlist("diagnosis")
        if "all" not in values:
            try:
                for value in values:
                    diagnoses.append(int(value))
            except Exception:
                self.bail()
        self.logger.info("diagnoses selected: %s", diagnoses)
        return diagnoses

    @cached_property
    def diagnosis_names(self):
        """Display the diagnosis filtering selected for the report."""

        if not self.diagnosis:
            return "All Diagnoses"
        names = []
        diagnoses = dict(self.diagnoses)
        try:
            for id in self.diagnosis:
                names.append(diagnoses[id])
        except Exception:
            self.bail()
        return ", ".join(sorted(names))

    @cached_property
    def languages(self):
        """Optional language(s) for filtering."""
        return self.fields.getlist("language")

    @cached_property
    def options(self):
        """Miscellaneous options selected by the user."""
        return self.fields.getlist("options")

    @cached_property
    def rows(self):
        """Values for the report table."""

        table = "query_term_pub" if "pub" in self.options else "query_term"
        fields = ["TRIM(m.value) AS title"]
        if self.show_id:
            fields.append("m.doc_id AS id")
        query = self.Query(f"{table} m", *fields).unique()
        query.order(1)
        query.where("m.path = '/Media/MediaTitle'")
        if "active" in self.options:
            query.join("active_doc a", "a.id = m.doc_id")
        if self.category:
            query.join(f"{table} c", "c.doc_id = m.doc_id")
            query.where(query.Condition("c.path", self.CATEGORY_PATH))
            query.where(query.Condition("c.value", self.category, "IN"))
        else:
            subquery = self.Query("query_term", "doc_id").unique()
            subquery.where(query.Condition("path", self.CATEGORY_PATH))
            subquery.where("value = 'meeting recording'")
            query.where(query.Condition("m.doc_id", subquery, "NOT IN"))
        if self.diagnosis:
            query.join(f"{table} d", "d.doc_id = m.doc_id")
            query.where(query.Condition("d.path", self.DIAGNOSIS_PATH))
            query.where(query.Condition("d.int_val", self.diagnosis, "IN"))
        if len(self.languages) == 1:
            if "en" in self.languages:
                query.outer(f"{table} t", "t.doc_id = m.doc_id",
                            "t.path = '/Media/TranslationOf/@cdr:ref'")
                query.where("t.doc_id IS NULL")
            else:
                query.join(f"{table} t", "t.doc_id = m.doc_id")
                query.where("t.path = '/Media/TranslationOf/@cdr:ref'")
        if self.type != "Any":
            pt = self.type
            path = f"/Media/PhysicalMedia/{pt}Data/{pt}Encoding"
            query.join(f"{table} p", "p.doc_id = m.doc_id")
            query.where(f"p.path = '{path}'")
        query.log()
        rows = []
        for row in query.execute(self.cursor).fetchall():
            title = row.title or "[Missing title]"
            if self.show_id:
                rows.append((row.id, title))
            else:
                rows.append((title,))
        self.logger.info("%d rows found", len(rows))
        return rows

    @cached_property
    def show_id(self):
        """True if we should include another column for the document IDs."""
        return "show_id" in self.options

    @cached_property
    def type(self):
        """Type of media to show on the report."""
        return self.fields.getvalue("type")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
