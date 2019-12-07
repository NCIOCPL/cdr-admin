#!/usr/bin/env python

"""Report on lists of drug information summaries.
"""

import datetime
from cdrcgi import Controller, Reporter
from cdrapi import db

class Control(Controller):
    """Top-level logic for the report."""

    SUBTITLE = f"Drug Info Summaries List -- {datetime.date.today()}"
    SINGLE_AGENT = "single_agent"
    COMBINATION = "combination"
    TYPES = {
        SINGLE_AGENT: "Single Agent Drug",
        COMBINATION: "Combination Drug",
    }
    OPTIONS = (
        ("include_id", "Include CDR ID", True),
        ("headers", "Include Column Headers", True),
        ("gridlines", "Show Grid Lines", True),
        ("extra", "Include Extra Column", False),
    )
    META_DATA = "/DrugInformationSummary/DrugInfoMetaData"
    COMBO_PATH = f"{META_DATA}/DrugInfoType/@Combination"

    def build_tables(self):
        """Create the report tables the user requested.

        If none were requested, fall back to the form.
        """

        tables = []
        for drug_type in self.drug_types:
            query = self.create_query(drug_type)
            rows = []
            for doc_id, title in query.execute(self.cursor).fetchall():
                row = []
                if self.include_id:
                    row = [Reporter.Cell(doc_id, center=True)]
                row.append(title)
                if self.include_blank_column:
                    row.append("")
                rows.append(row)
            caption = f"{self.TYPES[drug_type]} ({len(rows)})"
            table = Reporter.Table(rows, columns=self.cols, caption=caption)
            if not self.show_gridlines:
                table.node.set("class", "no-gridlines")
            tables.append(table)
        if tables:
            return tables
        else:
            self.show_form()

    def create_query(self, drug_type):
        """Create a customized database query depending on the agent type.

        Pass:
            drug_type: one of `SINGLE_AGENT` or `COMBINATION`

        Return:
            `cdrapi.db.Query` object
        """

        fields = "d.id", "t.value"
        query = db.Query("active_doc d", "d.id", "t.value").unique().order(2)
        query.join("query_term_pub t", "t.doc_id = d.id")
        query.where("t.path = '/DrugInformationSummary/Title'")
        query.outer("query_term_pub c", "c.doc_id = d.id",
                    f"c.path = '{self.COMBO_PATH}'")
        if drug_type == self.SINGLE_AGENT:
            query.where("c.value IS NULL")
        else:
            query.where("c.value = 'Yes'")
        return query

    def populate_form(self, page):
        """Add the fields for the report.

        Add client-side script to turn off the extra column flag
        if grid lines are suppressed.

        Pass:
            `HTMLPage` object to which the fields are added.
        """

        fieldset = page.fieldset("Select Agent Type(s)")
        for drug_type, display in reversed(sorted(self.TYPES.items())):
            opts = dict(value=drug_type, label=display, checked=True)
            fieldset.append(page.checkbox("type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        for value, label, checked in self.OPTIONS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)
        page.add_script("""\
function check_options(value) {
    if (!jQuery("#options-gridlines").prop("checked"))
        jQuery("#options-extra").prop("checked", false);
}""")

    @property
    def cols(self):
        """Column headers selected to match the report options."""

        if not hasattr(self, "_cols"):
            if self.include_headers:
                self._cols = []
                if self.include_id:
                    self._cols = ["CDR ID"]
                self._cols.append("Title")
                if self.include_blank_column:
                    self._cols.append(Reporter.Column("", width="300px"))
            else:
                self._cols = None
        return self._cols

    @property
    def include_headers(self):
        """Boolean indicating whether to show table column headers."""
        return True if "headers" in self.options else False

    @property
    def include_blank_column(self):
        """Boolean indicating whether to tack on a blank column."""
        return True if "extra" in self.options else False

    @property
    def include_id(self):
        """Boolean indicating whether we should include a column for the ID."""
        return True if "include_id" in self.options else False

    @property
    def options(self):
        """Settings of the option checkboxes."""
        return self.fields.getlist("options")

    @property
    def show_gridlines(self):
        """Boolean indicating whether we should have visible cell borders."""
        return True if "gridlines" in self.options else False

    @property
    def drug_types(self):
        """Sequence of drug agent types to be included in the report.

        Reverse the order so that single agent drugs come first.
        """

        if not hasattr(self, "_drug_types"):
            self._drug_types = reversed(sorted(self.fields.getlist("type")))
        return self._drug_types

if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
