#!/usr/bin/env python
"""Report on lists of drug information summaries.

This script actually generates four different reports (with one of those
having two options), based on the parameters chosen at run time.
"""

from cdrcgi import Controller, Reporter, bail
from cdrapi import db


class Control(Controller):

    SUBTITLE = "Drug Indications"
    TYPES = (
        ("drug", "Indications and Drug Names Only"),
        ("brand", "Indications and Drug Names (With Brand Name(s))"),
        ("plain", "Indications Only"),
    )
    GROUPINGS = (
        ("indication", "Display Drug(s) for each Indication"),
        ("drug", "Display Indication(s) for each Drug"),
    )

    def build_tables(self):
        """Create the correct table format depending on the report type.

        For the report listing approved indications with the drugs
        associated with each, we don't have any table at all.
        """

        if self.type == "plain":
            return self.plain_table
        elif self.grouping == "drug":
            return self.drug_table
        elif self.type == "brand":
            return self.indication_table
        else:
            return []

    def populate_form(self, page):
        """Put the fields on the form.

        Add client-side scripting to hide irrelevant fields depending
        on the state of other fields.

        Pass:
            page - `HTMLPage` object
        """

        fieldset = page.fieldset("Select Data To Be Displayed")
        opts = dict(checked=True)
        for value, label in self.TYPES:
            opts["value"] = value
            opts["label"] = label
            fieldset.append(page.radio_button("type", **opts))
            opts["checked"] = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Report Grouping")
        fieldset.set("class", "hideable")
        opts["checked"] = True
        for value, label in self.GROUPINGS:
            opts["value"] = value
            opts["label"] = label
            fieldset.append(page.radio_button("grouping", **opts))
            opts = dict(checked=False)
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Approved Indication(s)")
        fieldset.set("class", "hideable")
        options = [("all", "All indications")] + self.all_indications
        opts = dict(
            default="all",
            multiple=True,
            options=options,
            label="Indications",
            size=10,
        )
        fieldset.append(page.select("indication", **opts))
        page.form.append(fieldset)
        page.add_script("""\
function check_type(value) {
    if (value == "plain")
        jQuery("fieldset.hideable").hide();
    else
        jQuery("fieldset.hideable").show();
}h
jQuery(function() {
    var value = jQuery("input[name='type']:checked").val();
    check_type(value);
});""")

    def show_indicators_with_drugs(self):
        """Show the drugs associated with each approved indicator.

        The HTML 5 dl element is used for this version of the report.
        https://www.w3.org/TR/2011/WD-html5-author-20110809/the-dl-element.html
        makes it clear that this element is no longer exclusively used
        for dictionary definitions.
        """

        B = self.report.page.B
        div = B.DIV(style="margin: 10px auto; width: 600px")
        self.report.page.body.append(div)
        div.append(B.H3(self.caption))
        dl = B.DL(style="margin: 5px auto; width: 1000px")
        div.append(dl)
        for indication in sorted(self.indications, key=str.lower):
            dl.append(B.DT(indication))
            for drug in sorted(self.indications[indication]):
                link = Reporter.Table.B.A(drug.cdr_id, href=drug.url)
                span = Reporter.Table.B.SPAN(f"{drug.name} (", link, ")")
                dl.append(B.DD(span))

    def show_report(self):
        """Override the base class method.

        We do this so that we can handle the report which doesn't use tables.
        """

        if not self.report.tables:
            self.show_indicators_with_drugs()
        self.report.send()

    @property
    def all_indications(self):
        """Sequence of all the approval indications used by any drug."""
        if not hasattr(self, "_all_indications"):
            self._all_indications = Drug.all_indications(self)
        return self._all_indications

    @property
    def caption(self):
        """What we display at the top of the tables."""
        return "Approved Indications for Drug Information Summaries"

    @property
    def drug_table(self):
        """Report grouping the information by drug."""

        if self.include_brands:
            cols = "CDR ID", "Drug Name (Brand Name)", "Approved Indication(s)"
        else:
            cols = "CDR ID", "Drug Name", "Approved Indication(s)"
        rows = []
        for drug in self.drugs:
            if self.include_brands and drug.brands:
                name = Reporter.Table.B.SPAN(drug.name, drug.brand_span)
            else:
                name = drug.name
            row = drug.link, name, drug.indications
            rows.append(row)
        return Reporter.Table(rows, columns=cols, caption=self.caption)

    @property
    def drugs(self):
        """Sequence of all the drugs in scope for this report's options."""
        if not hasattr(self, "_drugs"):
            self._drugs = Drug.get_drugs(self)
        return self._drugs

    @property
    def grouping(self):
        """Whether the grouping should be by drug or by approval."""
        if not hasattr(self, "_grouping"):
            self._grouping = self.fields.getvalue("grouping")
            if self._grouping not in [g[0] for g in self.GROUPINGS]:
                bail()
        return self._grouping

    @property
    def include_brands(self):
        """Boolean indicating whether the users has asked for brand names."""
        return self.type == "brand"

    @property
    def indication(self):
        """Which approved indication(s) the report should show."""
        if not hasattr(self, "_indication"):
            self._indication = self.fields.getlist("indication")
            for indication in self._indication:
                if indication != "all":
                    if indication not in self.all_indications:
                        bail()
        return self._indication

    @property
    def indication_table(self):
        """Group the report by approval indication."""
        cols = "Approved Indication", "Drug Name", "Brand Name(s)"
        rows = []
        for indication in sorted(self.indications, key=str.lower):
            drugs = sorted(self.indications[indication])
            if len(drugs) > 1:
                name = Reporter.Cell(indication, rowspan=len(drugs))
            else:
                name = indication
            for drug in drugs:
                link = Reporter.Table.B.A(drug.cdr_id, href=drug.url)
                span = Reporter.Table.B.SPAN(f"{drug.name} (", link, ")")
                if name:
                    row = name, span, drug.brands or ""
                else:
                    row = span, drug.brands or ""
                rows.append(row)
                name = None
        return Reporter.Table(rows, columns=cols, caption=self.caption)

    @property
    def indications(self):
        """Dictionary of drugs used by each approval indication."""

        if not hasattr(self, "_indications"):
            self._indications = {}
            for drug in self.drugs:
                for indication in drug.indications:
                    if indication not in self._indications:
                        self._indications[indication] = [drug]
                    else:
                        self._indications[indication].append(drug)
        return self._indications

    @property
    def plain_table(self):
        """Simplest report, showing all of the approval indications."""
        if not hasattr(self, "_plain_table"):
            rows = [[indication] for indication in self.all_indications]
            cols = ["Full List of Drug Indications"]
            self._plain_table = Reporter.Table(rows, columns=cols)
        return self._plain_table

    @property
    def type(self):
        """The basic option for which type of report to generate.

        Validate the data to ensure that it hasn't been tampered
        with. In the event of hacking, we provide an error message
        which is as uninformative as possible.
        """
        if not hasattr(self, "_type"):
            self._type = self.fields.getvalue("type")
            if self._type not in [t[0] for t in self.TYPES]:
                bail()
        return self._type


class Drug:
    """DrugInformationSummary CDR document."""

    META_DATA = "/DrugInformationSummary/DrugInfoMetaData"
    TERM_LINK = f"{META_DATA}/TerminologyLink/@cdr:ref"
    APPROVED = "/DrugInformationSummary/DrugInfoMetaData/ApprovedIndication"
    TITLE = "/DrugInformationSummary/Title"
    PARMS = "Session={}&DocType=DrugInformationSummary&DocVersion=-1&DocId={}"

    def __init__(self, control, id, name):
        """Capture the caller's information.

        Properties do the heavy lifting as needed.
        """

        self.id = id
        self.name = name
        self.control = control

    def __lt__(self, other):
        """Make the drugs sortable by name."""
        return (self.name.lower(), self.id) < (other.name.lower(), other.id)

    @property
    def brand_span(self):
        """HTML span element wrapping this drug's brand names."""

        if not hasattr(self, "_brand_span"):
            brands = ", ".join(self.brands)
            self._brand_span = Reporter.Table.B.SPAN(f"({brands})")
            self._brand_span.set("class", "emphasis")
        return self._brand_span

    @property
    def brands(self):
        """All of the brand names used for this drug."""

        if not hasattr(self, "_brands"):
            query = db.Query("query_term_pub b", "b.value").unique()
            query.join("query_term_pub t", "t.doc_id = b.doc_id",
                       "LEFT(t.node_loc, 4) = LEFT(b.node_loc, 4)")
            query.join("query_term_pub d", "d.int_val = b.doc_id")
            query.where(query.Condition("d.doc_id", self.id))
            query.where(f"d.path = '{self.TERM_LINK}'")
            query.where("b.path = '/Term/OtherName/OtherTermName'")
            query.where("t.path = '/Term/OtherName/OtherNameType'")
            query.where("t.value = 'US brand name'")
            rows = query.execute(self.control.cursor).fetchall()
            self._brands = [row.value for row in rows]
        return self._brands

    @property
    def cdr_id(self):
        """Formatted CDR ID for this drug."""
        return f"CDR{self.id:d}"

    @property
    def indications(self):
        """Approved indications for this drug."""
        if not hasattr(self, "_indications"):
            query = db.Query("query_term_pub", "value").unique()
            query.where(query.Condition("doc_id", self.id))
            query.where(f"path = '{self.APPROVED}'")
            rows = query.execute(self.control.cursor)
            self._indications = [row.value for row in rows]
        return self._indications

    @property
    def link(self):
        """Table cell for a link to this drug's QC report."""
        if not hasattr(self, "_link"):
            self._link = Reporter.Cell(self.cdr_id, href=self.url, center=True)
        return self._link

    @property
    def url(self):
        """Address for this drug's CDR QC report."""
        if not hasattr(self, "_url"):
            parms = self.PARMS.format(self.control.session, self.cdr_id)
            self._url = f"QcReport.py?{parms}"
        return self._url

    @classmethod
    def all_indications(cls, control):
        """All the approval indications used by any CDR drug document."""
        query = db.Query("query_term_pub", "value").unique().order("value")
        query.where(query.Condition("path", cls.APPROVED))
        rows = query.execute(control.cursor).fetchall()
        return [row.value for row in rows]

    @classmethod
    def get_drugs(cls, control):
        """Find all of the drugs which are in scope for this report.

        Pass:
            control - object with report parameters and database access

        Return:
            sequence of `Drug` objects
        """

        fields = "d.doc_id", "d.value"
        query = db.Query("query_term_pub d", *fields).unique().order("d.value")
        query.join("query_term_pub a", "a.doc_id = d.doc_id")
        query.where(f"d.path = '{cls.TITLE}'")
        query.where(f"a.path = '{cls.APPROVED}'")
        if control.indication and "all" not in control.indication:
            query.where(query.Condition("a.value", control.indication, "IN"))
        rows = query.execute(control.cursor).fetchall()
        return [cls(control, row.doc_id, row.value) for row in rows]


if __name__ == "__main__":
    Control().run()
