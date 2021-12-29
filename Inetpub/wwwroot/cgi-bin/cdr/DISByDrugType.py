#!/usr/bin/env python

"""Drug Information Summary report by drug type.
"""

from cdrcgi import Controller
from cdrapi.docs import Doctype


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Drug Information Summary report by drug type."
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

    @property
    def caption(self):
        """Captions for the report's table."""

        if not hasattr(self, "_caption"):
            heading = "Drug Information Summary by Drug Type Report"
            if "all" in self.drug_type:
                drug_types = "All"
            else:
                drug_types = ", ".join(sorted(self.drug_type))
            self._caption = heading, f"Drug Type(s): {drug_types}"
        return self._caption

    @property
    def columns(self):
        """Headers for the report's table columns."""

        if not hasattr(self, "_columns"):
            self._columns = (
                self.Reporter.Column("CDR ID", width="50px"),
                self.Reporter.Column("Title of DIS", width="200px"),
                self.Reporter.Column("Drug Types", width="200px"),
                self.Reporter.Column("Publishable?", width="100px"),
            )
        return self._columns

    @property
    def drug_type(self):
        """Drug type(s) selected by user for the report."""

        if not hasattr(self, "_drug_type"):
            self._drug_type = self.fields.getlist("drug-type")
            if not self._drug_type:
                self._drug_type = "all"
        return self._drug_type

    @property
    def drug_types(self):
        """Valid values for drug type checkboxes on form."""

        if not hasattr(self, "_drug_types"):
            dis = Doctype(self.session, name="DrugInformationSummary")
            self._drug_types = dis.vv_lists.get("DrugType", [])
        return self._drug_types

    @property
    def publishable_drugs(self):
        """Set of CDR IDs for publishable DrugInformationSummary documents."""

        if not hasattr(self, "_publishable_drugs"):
            query = self.Query("doc_version v", "v.id").unique()
            query.join("doc_type t", "t.id = v.doc_type")
            query.where("t.name = 'DrugInformationSummary'")
            query.where("v.publishable = 'Y'")
            rows = query.execute(self.cursor).fetchall()
            self._publishable_drugs = {row.id for row in rows}
        return self._publishable_drugs

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
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
                self._rows.append(row)
        return self._rows


if __name__ == "__main__":
    Control().run()
