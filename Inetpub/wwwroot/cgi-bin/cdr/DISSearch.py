#!/usr/bin/env python

"""Search for CDR DrugInformationSummary documents.
"""

from cdrcgi import AdvancedSearch


class DrugInformationSummarySearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "DrugInformationSummary"
    SUBTITLE = "Drug Information Summary"
    FILTER = "set:QC DrugInfoSummary Set"
    PATHS = dict(
        title=f"/{DOCTYPE}/Title",
        fda_appr=f"/{DOCTYPE}/DrugInfoMetaData/FDAApproved",
        appr_ind=f"/{DOCTYPE}/DrugInfoMetaData/ApprovedIndication/@cdr:ref",
        drug_ref=f"/{DOCTYPE}/DrugReference/DrugReferenceType",
        last_mod=f"/{DOCTYPE}/DateLastModified",
    )

    def __init__(self):
        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        fda_appr_vals = self.valid_values["FDAApproved"]
        drug_ref_vals = self.valid_values["DrugReferenceType"]
        appr_ind_vals = self.approved_indication_terms
        if self.fda_appr and self.fda_appr not in fda_appr_vals:
            raise Exception("Tampering with form values")
        fda_appr_vals = [""] + fda_appr_vals
        if self.drug_ref and self.drug_ref not in drug_ref_vals:
            raise Exception("Tampering with form values")
        drug_ref_vals = [""] + drug_ref_vals
        if self.appr_ind:
            if self.appr_ind not in [v[0] for v in appr_ind_vals]:
                raise Exception("Tampering with form values")
        appr_ind_vals = [""] + appr_ind_vals
        self.search_fields = (
            self.text_field("title"),
            self.select("fda_appr", label="FDA Appr", options=fda_appr_vals),
            self.text_field("last_mod", label="Last Mod"),
            self.select("appr_ind", label="Appr Ind", options=appr_ind_vals),
            self.select("drug_ref", label="Drug Ref", options=drug_ref_vals),
        )
        self.query_fields = []
        for name, path in self.PATHS.items():
            field = self.QueryField(getattr(self, name), [path])
            self.query_fields.append(field)

    @property
    def approved_indication_terms(self):
        query = self.DBQuery("query_term t", "t.doc_id", "t.value").unique()
        query.join("query_term a", "a.int_val = t.doc_id")
        query.where(query.Condition("a.path", self.PATHS["appr_ind"]))
        query.where("t.path = '/Term/PreferredName'")
        query.order("t.value")
        rows = query.execute(self.session.cursor).fetchall()
        return [(f"CDR{row.doc_id:010d}", row.value) for row in rows]


if __name__ == "__main__":
    DrugInformationSummarySearch().run()
