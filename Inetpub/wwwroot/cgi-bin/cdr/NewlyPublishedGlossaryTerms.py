#!/usr/bin/env python

"""Show published Glossary Term Name documents.

"We need a New Published Glossary Terms Report which will serve as a
QC report to verify which new Glossary Term Name documents have been
published within the given time frame.  We would like a new Mailer
report so we can track responses easier."
"""

import datetime
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-building facilities."""

    SUBTITLE = "New Published Glossary Terms"
    COLUMNS = (
        ("CDR ID", "75px"),
        ("Term Name (English)", "300px"),
        ("Term Name (Spanish)", "300px"),
        ("Date First Published", "100px"),
    )

    def build_tables(self):
        """Assemble and return the report's table."""

        opts = dict(caption=self.caption, columns=self.columns)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask the user for the report parameters.

        Pass:
            page - HTMLPage object on which to place the form fields
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset = page.fieldset("Report Parameters")
        opts = dict(label="Start Date", value=start)
        fieldset.append(page.date_field("start", **opts))
        opts = dict(label="End Date", value=end)
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Audience")
        for audience in self.AUDIENCES:
            opts = dict(label=audience, value=audience)
            fieldset.append(page.checkbox("audience", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Language")
        for language in self.LANGUAGES:
            opts = dict(label=language, value=language)
            fieldset.append(page.checkbox("language", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Dictionary")
        for dictionary in self.dictionaries:
            opts = dict(label=dictionary, value=dictionary)
            fieldset.append(page.checkbox("dictionary", **opts))
        page.form.append(fieldset)

    @property
    def audiences(self):
        """Which audiences have been selected for the report?"""

        if not hasattr(self, "_audiences"):
            self._audiences = self.fields.getlist("audience")
            if set(self._audiences) - set(self.AUDIENCES):
                self.bail()
        return self._audiences

    @property
    def caption(self):
        """What we display at the top of the report's table."""
        return f"{len(self.rows)} Newly Published Glossary Term Documents"

    @property
    def columns(self):
        """Column headers displayed at the top of the report table."""

        cols = []
        for label, width in self.COLUMNS:
            cols.append(self.Reporter.Column(label, width=width))
        return cols

    @property
    def definition_path(self):
        """How we find concept filtering values depending on language."""

        if not hasattr(self, "_definition_path"):
            if len(self.languages) == 1:
                if self.languages[0] == "English":
                    tag = "TermDefinition"
                else:
                    tag = "TranslatedTermDefinition"
            else:
                tag = "%TermDefinition"
            self._definition_path = f"/GlossaryTermConcept/{tag}"
        return self._definition_path

    @property
    def dictionaries(self):
        """Dictionary values for the checkboxes."""

        if not hasattr(self, "_dictionaries"):
            query = self.Query("query_term", "value").unique().order("value")
            query.where("path LIKE '/GlossaryTermConcept/%nition/Dictionary'")
            rows = query.execute(self.cursor).fetchall()
            self._dictionaries = [row.value for row in rows]
        return self._dictionaries

    @property
    def dictionary(self):
        """Which dictionary(ies) has/have been selected for the report?"""

        if not hasattr(self, "_dictionary"):
            self._dictionary = self.fields.getlist("dictionary")
            if set(self._dictionary) - set(self.dictionaries):
                self.bail
        return self._dictionary

    @property
    def end(self):
        return self.fields.getvalue("end")

    @property
    def format(self):
        """Override the default report format so we get an Excel workbook."""
        return "excel"

    @property
    def languages(self):
        """Which languages have been selected for the report?"""

        if not hasattr(self, "_languages"):
            self._languages = self.fields.getlist("language")
            if set(self._languages) - set(self.LANGUAGES):
                self.bail()
        return self._languages

    @property
    def rows(self):
        """Values for the report table."""

        if not hasattr(self, "_rows"):
            self._rows = [term.row for term in self.terms]
        return self._rows

    @property
    def start(self):
        return self.fields.getvalue("start")

    @property
    def terms(self):
        """Values for the report table."""

        query = self.Query("document d", "d.id", "d.first_pub").order("d.id")
        query.where("d.first_pub IS NOT NULL")
        query.where("d.active_status = 'A'")
        if self.start:
            query.where(query.Condition("d.first_pub", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59"
            query.where(query.Condition("d.first_pub", end, "<="))
        if self.audiences or self.dictionary or self.languages:
            query.unique()
            path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
            query.join("query_term c", "c.doc_id = d.id")
            query.where(f"c.path = '{path}'")
            path_op = "LIKE" if "%" in self.definition_path else "="
        else:
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'GlossaryTermName'")
        if self.audiences:
            query.join("query_term a", "a.doc_id = c.int_val")
            query.where(f"a.path {path_op} '{self.definition_path}/Audience'")
            query.where(query.Condition("a.value", self.audiences, "IN"))
        if self.dictionary:
            path = f"{self.definition_path}/Dictionary"
            query.join("query_term y", "y.doc_id = c.int_val")
            query.where(f"y.path {path_op} '{path}'")
            query.where(query.Condition("y.value", self.dictionary, "IN"))
        if self.languages and not self.audiences and not self.dictionary:
            path = f"{self.definition_path}/DefinitionText"
            query.join("query_term l", "l.doc_id = c.int_val")
            query.where(f"l.path {path_op} '{path}'")
            query.where("l.value IS NOT NULL AND l.value <> ''")
        rows = query.execute(self.cursor).fetchall()
        return [TermName(self, row) for row in rows]


class TermName:
    """GlossaryTermName document published in the report's date range."""

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-generation tools
            row - resultset row from the database query
        """

        self.__control = control
        self.__row = row

    @property
    def english_name(self):
        """The primary English name for the glossary term."""

        query = self.__control.Query("query_term", "value")
        query.where("path = '/GlossaryTermName/TermName/TermNameString'")
        query.where(query.Condition("doc_id", self.id))
        return query.execute(self.__control.cursor).fetchall()[0].value

    @property
    def first_pub(self):
        """Date the document was first published."""
        return str(self.__row.first_pub)[:10]

    @property
    def id(self):
        """Primary key from the all_docs table for the document."""
        return self.__row.id

    @property
    def row(self):
        """Values for the report's table."""
        return (
            self.__control.Reporter.Cell(self.id, center=True),
            self.english_name,
            self.spanish_names,
            self.__control.Reporter.Cell(self.first_pub, center=True),
        )

    @property
    def spanish_names(self):
        """Concatenated list of all the Spanish names for this term."""

        query = self.__control.Query("query_term", "value")
        query.where("path = '/GlossaryTermName/TranslatedName/TermNameString'")
        query.where(query.Condition("doc_id", self.id))
        rows = query.execute(self.__control.cursor).fetchall()
        return "; ".join([row.value for row in rows])


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
