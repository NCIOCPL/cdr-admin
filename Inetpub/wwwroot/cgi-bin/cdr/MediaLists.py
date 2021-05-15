#!/usr/bin/env python

"""Show Media documents, optionally filtered by category and/or diagnosis.
"""

from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Media Lists"
    LOGNAME = "MediaLists"
    DIAGNOSIS_PATH = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
    CATEGORY_PATH = "/Media/MediaContent/Categories/Category"

    def build_tables(self):
        """Assemble the report and return it."""

        opts = dict(caption=self.caption, columns=self.columns)
        return self.Reporter.Table(self.rows, **opts)

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

    @property
    def caption(self):
        """Strings to be displayed immediately above the report table."""

        if not hasattr(self, "_caption"):
            self._caption = [
                "Report Filtering",
                f"Diagnosis: {self.diagnosis_names}",
                f"Condition: {self.category_names}",
            ]
            if "active" in self.options:
                self._caption.append("Excluding blocked documents")
            if "pub" in self.options:
                self._caption.append("Excluding non-publishable documents")
            if len(self.languages) == 1:
                lang = "English" if "en" in self.languages else "Spanish"
                self._caption.append(f"Language: {lang}")
        return self._caption

    @property
    def categories(self):
        """ID/name tuples of the category terms for the form picklist."""

        query = self.Query("query_term", "value").order("value").unique()
        query.where("path = '/Media/MediaContent/Categories/Category'")
        query.where("value <> ''")
        return [row.value for row in query.execute(self.cursor).fetchall()]

    @property
    def category(self):
        """Categories selected by the user for filtering the report."""

        if not hasattr(self, "_category"):
            self._category = self.fields.getlist("category")
            if "all" in self._category:
                self._category = []
            self.logger.info("categories selected: %s", self._category)
        return self._category

    @property
    def category_names(self):
        """Display the category filtering selected for the report."""

        if not self.category:
            return "All Categories"
        return ", ".join(sorted(self.category))

    @property
    def columns(self):
        """Column header(s) for the report table (might be only one)."""

        columns = []
        if self.show_id:
            columns = [self.Reporter.Column("Doc ID", width="80px")]
        columns.append(self.Reporter.Column("Doc Title", width="800px"))
        return columns

    @property
    def diagnoses(self):
        """ID/name tuples of the diagnosis terms for the form picklist."""

        query = self.Query("query_term t", "t.doc_id", "t.value").unique()
        query.order("t.value")
        query.join("query_term m", "m.int_val = t.doc_id")
        query.where("t.path = '/Term/PreferredName'")
        query.where(query.Condition("m.path", self.DIAGNOSIS_PATH))
        return [tuple(row) for row in query.execute(self.cursor).fetchall()]

    @property
    def diagnosis(self):
        """Diagnoses selected by the user for filtering the report."""

        if not hasattr(self, "_diagnosis"):
            self._diagnosis = []
            diagnoses = self.fields.getlist("diagnosis")
            if "all" not in diagnoses:
                try:
                    for diagnosis in diagnoses:
                        self._diagnosis.append(int(diagnosis))
                except:
                    self.bail()
            self.logger.info("diagnoses selected: %s", self._diagnosis)
        return self._diagnosis

    @property
    def diagnosis_names(self):
        """Display the diagnosis filtering selected for the report."""

        if not self.diagnosis:
            return "All Diagnoses"
        names = []
        diagnoses = dict(self.diagnoses)
        try:
            for id in self.diagnosis:
                names.append(diagnoses[id])
        except:
            self.bail()
        return ", ".join(sorted(names))

    @property
    def languages(self):
        """Optional language(s) for filtering."""

        if not hasattr(self, "_language"):
            self._languages = self.fields.getlist("language")
        return self._languages

    @property
    def options(self):
        """Miscellaneous options selected by the user."""

        if not hasattr(self, "_options"):
            self._options = self.fields.getlist("options")
        return self._options

    @property
    def rows(self):
        """Values for the report table."""

        if not hasattr(self, "_rows"):
            table = "query_term_pub" if "pub" in self.options else "query_term"
            fields = ["m.doc_id", "m.value"] if self.show_id else ["m.value"]
            query = self.Query(f"{table} m", *fields).unique()
            query.order("m.value")
            query.where("m.path = '/Media/MediaTitle'")
            if "active" in self.options:
                query.join("active_doc a", "a.id = m.doc_id")
            if self.category:
                query.join(f"{table} c", "c.doc_id = m.doc_id")
                query.where(query.Condition("c.path", self.CATEGORY_PATH))
                query.where(query.Condition("c.value", self.category, "IN"))
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
            rows = query.execute(self.cursor).fetchall()
            self._rows = [tuple(row) for row in rows]
            self.logger.info("%d rows found", len(self._rows))
        return self._rows

    @property
    def show_id(self):
        """True if we should include another column for the document IDs."""
        return "show_id" in self.options


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
