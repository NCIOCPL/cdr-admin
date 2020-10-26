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
    AGENT_TYPES = {
        SINGLE_AGENT: "Single Agent Drug",
        COMBINATION: "Combination Drug",
    }
    ACCELERATED_APPROVAL = "Accelerated approval"
    APPROVED_IN_CHILDREN = "Approved in children"
    FDA_APPROVAL_STATUSES = ACCELERATED_APPROVAL, APPROVED_IN_CHILDREN
    OPTIONS = (
        ("include_id", "Include CDR ID", True),
        ("headers", "Include Column Headers", True),
        ("gridlines", "Show Grid Lines", True),
        ("include_approvals", "Include FDA Approval Information", False),
        ("extra", "Include Extra Column", False),
    )
    META_DATA = "/DrugInformationSummary/DrugInfoMetaData"
    COMBO_PATH = f"{META_DATA}/DrugInfoType/@Combination"
    ACCEL_PATH = f"{META_DATA}/FDAApproved/@Accelerated"
    KIDS_PATH = f"{META_DATA}/FDAApproved/@ApprovedInChildren"
    TYPE_PATH = f"{META_DATA}/DrugType"

    def build_tables(self):
        """Create the report tables the user requested.

        If none were requested, fall back to the form.
        """

        tables = []
        for agent_type in self.agent_types:
            query = self.create_query(agent_type)
            rows = []
            for row in query.execute(self.cursor).fetchall():
                query = self.Query("query_term_pub", "value")
                query.where(f"path = '{self.TYPE_PATH}'")
                query.where(query.Condition("doc_id", row.id))
                types = query.execute(self.cursor).fetchall()
                types = ", ".join([t.value for t in types])
                cells = []
                if self.include_id:
                    cells = [Reporter.Cell(row.id, center=True)]
                cells.append(row.title)
                cells.append(types)
                if self.include_fda_approval:
                    cells.append("Yes" if row.accelerated else "")
                    cells.append("Yes" if row.approved_in_children else "")
                if self.include_blank_column:
                    cells.append("")
                rows.append(cells)
            caption = f"{self.AGENT_TYPES[agent_type]} ({len(rows)})"
            table = Reporter.Table(rows, columns=self.cols, caption=caption)
            if not self.show_gridlines:
                table.node.set("class", "no-gridlines")
            tables.append(table)
        if tables:
            return tables
        else:
            self.show_form()

    def create_query(self, agent_type):
        """Create a customized database query depending on the agent type.

        Pass:
            agent_type: one of `SINGLE_AGENT` or `COMBINATION`

        Return:
            `cdrapi.db.Query` object
        """

        fields = ["d.id", "t.value AS title"]
        if self.include_fda_approval:
            fields.append("a.value AS accelerated")
            fields.append("k.value AS approved_in_children")
        query = db.Query("active_doc d", *fields).unique().order(2, 1)
        query.join("query_term_pub t", "t.doc_id = d.id")
        query.where("t.path = '/DrugInformationSummary/Title'")
        if self.drug_type:
            query.join("query_term_pub r", "r.doc_id = d.id")
            query.where(f"r.path = '{self.TYPE_PATH}'")
            query.where(query.Condition("r.value", self.drug_type, "IN"))
        if self.ACCELERATED_APPROVAL in self.fda_approval_status:
            if self.APPROVED_IN_CHILDREN in self.fda_approval_status:
                query.outer("query_term_pub a", "a.doc_id = d.id",
                            "a.value = 'Yes'", f"a.path = '{self.ACCEL_PATH}'")
                query.outer("query_term_pub k","k.doc_id = d.id",
                            "k.value = 'Yes'", f"k.path = '{self.KIDS_PATH}'")
                query.where("(a.doc_id IS NOT NULL OR k.doc_id IS NOT NULL)")
            else:
                query.join("query_term_pub a", "a.doc_id = d.id")
                query.where(f"a.path = '{self.ACCEL_PATH}'")
                query.where("a.value = 'Yes'")
                if self.include_fda_approval:
                    query.outer("query_term_pub k","k.doc_id = d.id",
                                "k.value = 'Yes'",
                                f"k.path = '{self.KIDS_PATH}'")
        elif self.APPROVED_IN_CHILDREN in self.fda_approval_status:
            query.join("query_term_pub k", "k.doc_id = d.id")
            query.where(f"k.path = '{self.KIDS_PATH}'")
            query.where("k.value = 'Yes'")
            if self.include_fda_approval:
                query.outer("query_term_pub a", "a.doc_id = d.id",
                            "a.value = 'Yes'", f"a.path = '{self.ACCEL_PATH}'")
        elif self.include_fda_approval:
            query.outer("query_term_pub a", "a.doc_id = d.id",
                        "a.value = 'Yes'", f"a.path = '{self.ACCEL_PATH}'")
            query.outer("query_term_pub k","k.doc_id = d.id",
                        "k.value = 'Yes'", f"k.path = '{self.KIDS_PATH}'")
        query.outer("query_term_pub c", "c.doc_id = d.id",
                    f"c.path = '{self.COMBO_PATH}'")
        if agent_type == self.SINGLE_AGENT:
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
        for agent_type, display in reversed(sorted(self.AGENT_TYPES.items())):
            opts = dict(value=agent_type, label=display, checked=True)
            fieldset.append(page.checkbox("agent-type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Select FDA Approval Status")
        for status in self.FDA_APPROVAL_STATUSES:
            fieldset.append(page.checkbox("fda-approval-status", value=status))
        page.form.append(fieldset)
        fieldset = page.fieldset("Drug Type")
        opts = dict(options=self.drug_types, multiple=True)
        fieldset.append(page.select("drug-type", **opts))
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
    def agent_types(self):
        """Sequence of drug agent types to be included in the report.

        Reverse the order so that single agent drugs come first.
        """

        if not hasattr(self, "_agent_types"):
            types = self.fields.getlist("agent-type")
            self._agent_types = reversed(sorted(types))
        return self._agent_types

    @property
    def cols(self):
        """Column headers selected to match the report options."""

        if not hasattr(self, "_cols"):
            if self.include_headers:
                self._cols = []
                if self.include_id:
                    self._cols = ["CDR ID"]
                self._cols.append("Title")
                self._cols.append("Drug Type")
                if self.include_fda_approval:
                    self._cols.append("Accelerated")
                    self._cols.append("Approved in Children")
                if self.include_blank_column:
                    self._cols.append(Reporter.Column("", width="300px"))
            else:
                self._cols = None
        return self._cols

    @property
    def drug_type(self):
        """Narrow report to these drug types if any selected."""

        if not hasattr(self, "_drug_type"):
            self._drug_type = self.fields.getlist("drug-type")
        return self._drug_type

    @property
    def drug_types(self):
        """Valid values for the drug type picklist."""

        if not hasattr(self, "_drug_types"):
            query = self.Query("query_term_pub", "value").unique().order(1)
            query.where(f"path = '{self.TYPE_PATH}'")
            rows = query.execute(self.cursor)
            self._drug_types = [row.value for row in rows]
        return self._drug_types

    @property
    def fda_approval_status(self):
        """Which approval status filters (if any) have been chosen."""

        if not hasattr(self, "_fda_approval_status"):
            statuses = self.fields.getlist("fda-approval-status")
            for status in statuses:
                if status not in self.FDA_APPROVAL_STATUSES:
                    self.bail()
            self._fda_approval_status = statuses
        return self._fda_approval_status

    @property
    def include_headers(self):
        """Boolean indicating whether to show table column headers."""
        return True if "headers" in self.options else False

    @property
    def include_blank_column(self):
        """Boolean indicating whether to tack on a blank column."""
        return True if "extra" in self.options else False

    @property
    def include_fda_approval(self):
        """Boolean indicating whether to add columns for FDA approvals."""
        return True if "include_approvals" in self.options else False

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


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
