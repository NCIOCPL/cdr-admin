#!/usr/bin/env python

"""Drug Information Summary report by drug type.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doctype


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Drug Report By Drug Type"
    LOGNAME = "DISByDrugType"
    DRUG_TYPE_PATH = "/DrugInformationSummary/DrugInfoMetaData/DrugType"
    TITLE_PATH = "/DrugInformationSummary/Title"

    def build_tables(self):
        """Assemble the report and return it."""

        opts = dict(columns=self.columns, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask the user for the report's parameters.

        Pass:
            page - HTMLPage object on which the form is drawn
        """

        fieldset = page.fieldset("Drug Type(s)")
        opts = dict(label="All", value="all")
        fieldset.append(page.checkbox("drug-type", **opts))
        for drug_type in self.drug_types:
            opts = dict(label=drug_type, value=drug_type)
            fieldset.append(page.checkbox("drug-type", **opts))
        page.form.append(fieldset)
        page.add_output_options()

    @cached_property
    def caption(self):
        """Captions for the report's table."""

        heading = "Drug Information Summary by Drug Type Report"
        if "all" in self.drug_type:
            drug_types = "All"
        else:
            drug_types = ", ".join(sorted(self.drug_type))
        return heading, f"Drug Type(s): {drug_types}"

    @cached_property
    def columns(self):
        """Headers for the report's table columns."""

        return (
            self.Reporter.Column("CDR ID", width="50px"),
            self.Reporter.Column("Title of DIS", width="200px"),
            self.Reporter.Column("Drug Types", width="200px"),
            self.Reporter.Column("Publishable?", width="100px"),
        )

    @cached_property
    def drug_type(self):
        """Drug type(s) selected by user for the report."""
        return self.fields.getlist("drug-type") or "all"

    @cached_property
    def drug_types(self):
        """Valid values for drug type checkboxes on form."""

        dis = Doctype(self.session, name="DrugInformationSummary")
        return dis.vv_lists.get("DrugType", [])

    @cached_property
    def publishable_drugs(self):
        """Set of CDR IDs for publishable DrugInformationSummary documents."""

        query = self.Query("doc_version v", "v.id").unique()
        query.join("doc_type t", "t.id = v.doc_type")
        query.where("t.name = 'DrugInformationSummary'")
        query.where("v.publishable = 'Y'")
        rows = query.execute(self.cursor).fetchall()
        return {row.id for row in rows}

    @cached_property
    def rows(self):
        """Table rows for the report."""

        report_rows = []
        fields = "t.doc_id", "t.value", "d.value"
        query = self.Query("query_term t", *fields)
        query.join("query_term d", "d.doc_id = t.doc_id")
        query.where(f"t.path = '{self.TITLE_PATH}'")
        query.where(f"d.path = '{self.DRUG_TYPE_PATH}'")
        query.order("t.value")
        query.order("d.value")
        if self.drug_type and "all" not in self.drug_type:
            query.where(query.Condition("d.value", self.drug_type, "IN"))
        rows = query.execute(self.cursor).fetchall()
        counts = {}
        for doc_id, title, drug_type in rows:
            counts[doc_id] = counts.get(doc_id, 0) + 1
        for doc_id, title, drug_type in rows:
            opts = dict(bold=counts[doc_id] > 1)
            publishable = doc_id in self.publishable_drugs
            row = [
                self.Reporter.Cell(doc_id, **opts),
                self.Reporter.Cell(title, **opts),
                self.Reporter.Cell(drug_type, **opts),
                self.Reporter.Cell("Yes" if publishable else "No", **opts),
            ]
            report_rows.append(row)
        return report_rows


if __name__ == "__main__":
    Control().run()
