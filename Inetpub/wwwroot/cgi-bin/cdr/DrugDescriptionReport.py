#!/usr/bin/env python

"""Display DrugInfoSummary document.
"""

from datetime import date, timedelta
from json import dumps, loads
from lxml import html
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """
    If the user has asked for a report:
        collect the report options from the individual CGI parameters
        and show the report.
    Otherwise, if the user asked to refine an existing request:
        unpack the remembered options and show the form again with them.
    Otherwise, put up the request form with the default choices.
    """

    SUBTITLE = "Drug Description Report"
    CSS = "../../stylesheets/DrugDescriptionReport.css"
    SCRIPT = "../../js/DrugDescriptionReport.js"
    REFTYPE_PATH = "/DrugInformationSummary/DrugReference/DrugReferenceType"
    METADATA = "/DrugInformationSummary/DrugInfoMetaData"
    COMBO_PATH = f"{METADATA}/DrugInfoType/@Combination"
    ACCEL_PATH = f"{METADATA}/FDAApproved/@Accelerated"
    KIDS_PATH = f"{METADATA}/FDAApproved/@ApprovedInChildren"
    TYPE_PATH = f"{METADATA}/DrugType"
    REFTYPES = "NCI", "FDA", "NLM"
    METHODS = (
        ("By Drug Name", "name"),
        ("By Date of Last Publishable Version", "date"),
        ("By Drug Reference Type", "type"),
        ("By FDA Approval Information", "fda"),
    )
    ACCELERATED_APPROVAL = "Accelerated approval"
    APPROVED_IN_CHILDREN = "Approved in children"
    FDA_APPROVAL_STATUSES = ACCELERATED_APPROVAL, APPROVED_IN_CHILDREN
    FDA_PATHS = {
        ACCELERATED_APPROVAL: ACCEL_PATH,
        APPROVED_IN_CHILDREN: KIDS_PATH,
    }
    ALL_DRUGS = "all-drugs"
    SINGLE_AGENT_DRUGS = "all-single-agent-drugs"
    DRUG_COMBOS = "all-drug-combinations"
    DRUG_GROUP_OPTIONS = ALL_DRUGS, SINGLE_AGENT_DRUGS, DRUG_COMBOS
    DRUG_GROUP_LABELS = {
        ALL_DRUGS: "All Drugs",
        SINGLE_AGENT_DRUGS: "All Single-Agent Drugs",
        DRUG_COMBOS: "All Drug Combinations",
    }

    def populate_form(self, page):
        """Add the fields for a DIS report request to the page's form.

        Pass:
            page - HTMLPage object where the fields go
        """

        # How will the drugs be selected?
        fieldset = page.fieldset("Filter Method")
        for label, value in self.METHODS:
            checked = value == self.selection_method
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("method", **opts))
        page.form.append(fieldset)

        # Picklist for selecting drugs by name or group.
        fieldset = page.fieldset("Select Drugs For Report", id="name-block")
        if self.selection_method != "name":
            fieldset.set("class", "hidden usa-fieldset")
        opts = dict(
            label="Drug(s)",
            multiple=True,
            default=self.selected_drugs,
            options=self.drug_picklist_options,
            tooltip="Control-click to select multiple\nShift-click for range.",
        )
        fieldset.append(page.select("drugs", **opts))
        page.form.append(fieldset)

        # Fields for selecting drugs by date range of last pub version.
        fieldset = page.fieldset("Date Range of Last Published Version")
        fieldset.set("id", "date-block")
        if self.selection_method != "date":
            fieldset.set("class", "hidden usa-fieldset")
        opts = dict(label="Start Date", value=self.start)
        fieldset.append(page.date_field("start", **opts))
        opts = dict(label="End Date", value=self.end)
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)

        # Radio buttons for selecting drugs by reference type.
        fieldset = page.fieldset("Select Drug Reference Type", id="type-block")
        if self.selection_method != "type":
            fieldset.set("class", "hidden usa-fieldset")
        for value in self.REFTYPES:
            checked = value == self.reftype
            opts = dict(value=value, label=value, checked=checked)
            fieldset.append(page.radio_button("reftype", **opts))
        page.form.append(fieldset)

        # Extra choices for the "FDA approval" selection method.
        fieldset = page.fieldset("By FDA Approval Information", id="fda-block")
        if self.selection_method != "fda":
            fieldset.set("class", "hidden usa-fieldset")
        for value in self.FDA_APPROVAL_STATUSES:
            opts = dict(value=value, label=value, checked=True)
            fieldset.append(page.checkbox("fda-approval-status", **opts))
        page.form.append(fieldset)

        # Optionally narrow by drug type.
        fieldset = page.fieldset("Select Drug Type(s) For Report")
        opts = dict(options=self.drug_types, multiple=True)
        fieldset.append(page.select("drug-type", **opts))
        page.form.append(fieldset)

        # Magic to make field sets appear and disappear, based on method.
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))
        page.add_css("#drugs { height: 175px; }")

    def show_report(self):
        """Override base table because this report doesn't fit the mold."""

        opts = dict(
            action=self.script,
            subtitle=self.subtitle,
            session=self.session,
            body_classes="report",
        )
        page = self.HTMLPage(self.PAGE_TITLE, **opts)
        page.form.append(page.hidden_field("vals", self.current_values))
        now = str(self.started)[:self.DATETIMELEN]
        count = f"{len(self.summaries):d} documents found"
        if self.criteria:
            count = f"{count} {self.criteria}"
        title = page.B.H2(
            self.subtitle,
            page.B.BR(),
            page.B.SPAN(now, page.B.CLASS("report-date")),
            page.B.BR(),
            page.B.SPAN(count, page.B.CLASS("report-count")),
            page.B.CLASS("center"),
        )
        page.form.append(title)
        for summary in sorted(self.summaries):
            page.form.append(summary.table)
            page.form.append(page.B.HR())
        page.form.append(self.footer)
        page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))
        page.send()

    @property
    def criteria(self):
        """String describing how the drug documents were selected."""

        if not hasattr(self, "_criteria"):
            self._criteria = None
            if self.selection_method == "name":
                if self.ALL_DRUGS not in self.selected_drugs:
                    self._criteria = ""
                if self.SINGLE_AGENT_DRUGS in self.selected_drugs:
                    self._criteria = "for single-agent drugs"
                elif self.DRUG_COMBOS in self.selected_drugs:
                    self._criteria = "for drug combinations"
                else:
                    self._criteria = "by name"
            elif self.selection_method == "type":
                self._criteria = f"with reference type {self.reftype}"
            elif self.selection_method == "date":
                self._criteria = "with last publishable versions created "
                self._criteria += f"{self.start}--{self.end} (inclusive)"
            elif self.selection_method == "fda":
                approvals = " and ".join(self.fda_approval_status)
                self._criteria = f"with {approvals}"
        return self._criteria

    @property
    def current_values(self):
        """Pack up the user's selections so she can return to them."""

        vals = dict(
            method=self.selection_method,
            start=str(self.start),
            end=str(self.end),
            drugs=self.selected_drugs,
            reftype=self.reftype,
            fda=self.fda_approval_status,
            types=self.drug_type,
        )
        return dumps(vals)

    @property
    def drug_picklist_options(self):
        """The sequence presented in the picklist for selecting drugs."""

        if not hasattr(self, "_drug_picklist_options"):
            options = []
            for option in self.DRUG_GROUP_OPTIONS:
                options.append((option, self.DRUG_GROUP_LABELS[option]))
            for drug in self.drugs:
                options.append((drug.id, drug.name))
            self._drug_picklist_options = options
        return self._drug_picklist_options

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
    def drugs(self):
        "Find all of the DIS docs which have at least one version."

        if not hasattr(self, "_drugs"):
            query = self.Query("document d", "d.id", "d.title").order(2, 1)
            query.join("doc_type t", "t.id = d.doc_type")
            query.join("doc_version v", "v.id = d.id")
            query.where("t.name = 'DrugInformationSummary'")
            rows = query.unique().execute(self.cursor).fetchall()

            class VersionedDrugDoc:
                """Information needed for the drug picklist."""
                def __init__(self, row):
                    self.id = row.id
                    self.name = row.title.split(";")[0].strip()
                    if not self.name:
                        self.name = f"[Unnamed drug CDR{row.id}]"
            self._drugs = [VersionedDrugDoc(row) for row in rows]
        return self._drugs

    @property
    def end(self):
        """The `datetime.date` object for end of report's date range."""

        if not hasattr(self, "_end"):
            end = self.saved_values.get("end")
            if not end:
                end = self.fields.getvalue("end")
            try:
                self._end = self.parse_date(end)
            except Exception:
                self.bail("Invalid end date")
            if not self._end:
                self._end = date.today()
        return self._end

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
    def selection_method(self):
        """How should drugs be selected (see self.METHODS)?"""

        if not hasattr(self, "_selection_method"):
            methods = [method[1] for method in self.METHODS]
            method = self.saved_values.get("method")
            if not method:
                method = self.fields.getvalue("method", methods[0])
            if method not in methods:
                self.bail()
            self._selection_method = method
        return self._selection_method

    @property
    def reftype(self):
        """Drug reference type (NCI, FDA, or NLM)."""

        if not hasattr(self, "_reftype"):
            self._reftype = self.saved_values.get("reftype")
            if not self._reftype:
                default = self.REFTYPES[0]
                self._reftype = self.fields.getvalue("reftype", default)
            if self._reftype not in self.REFTYPES:
                self.bail()
        return self._reftype

    @property
    def saved_values(self):
        """User's selections from the last request."""

        if not hasattr(self, "_saved_values"):
            vals = self.fields.getvalue("vals", "{}")
            try:
                self._saved_values = loads(vals)
            except Exception:
                self.bail()
        return self._saved_values

    @property
    def selected_drugs(self):
        """Which drugs has the user chosen for the report?"""

        if not hasattr(self, "_selected_drugs"):
            drugs = self.saved_values.get("drugs")
            if not drugs:
                drugs = self.fields.getlist("drugs")
            if not drugs or self.ALL_DRUGS in drugs:
                self._selected_drugs = [self.ALL_DRUGS]
            elif self.SINGLE_AGENT_DRUGS in drugs:
                self._selected_drugs = [self.SINGLE_AGENT_DRUGS]
            elif self.DRUG_COMBOS in drugs:
                self._selected_drugs = [self.DRUG_COMBOS]
            else:
                try:
                    self._selected_drugs = [int(d) for d in drugs]
                except Exception:
                    self.bail()
                if set(self._selected_drugs) - {d.id for d in self.drugs}:
                    self.bail()
        return self._selected_drugs

    @property
    def start(self):
        """The `datetime.date` object for start of report's date range."""

        if not hasattr(self, "_start"):
            start = self.saved_values.get("start")
            if not start:
                start = self.fields.getvalue("start")
            try:
                self._start = self.parse_date(start)
            except Exception:
                self.bail("Invalid start date")
            if not self._start:
                self._start = self.end - timedelta(30)
            elif self._start > self.end:
                self.bail("Invalid date range")
        return self._start

    @property
    def summaries(self):
        """Sequence of `DrugInformationSummary` docs selected for report."""

        if not hasattr(self, "_summaries"):
            if self.selection_method == "date":
                end = f"{self.end} 23:59:59"
                cols = "p.id", "MAX(p.num) AS num"
                subquery = self.Query("publishable_version p", *cols)
                subquery.join("doc_type t", "t.id = p.doc_type")
                subquery.join("document d", "d.id = p.id")
                subquery.where("t.name = 'DrugInformationSummary'")
                subquery.group("p.id")
                subquery.alias("lastp")
                query = self.Query("doc_version v", "v.id", "v.num")
                query.join(subquery, "lastp.id = v.id", "lastp.num = v.num")
                query.where(query.Condition("v.dt", self.start, ">="))
                query.where(query.Condition("v.dt", end, "<="))
            else:
                cols = "v.id", "MAX(v.num) AS num"
                query = self.Query("doc_version v", *cols)
                query.group("v.id")
            if self.drug_type:
                query.join("query_term t", "t.doc_id = v.id")
                query.where(f"t.path = '{self.TYPE_PATH}'")
                query.where(query.Condition("t.value", self.drug_type, "IN"))
            if self.selection_method == "name":
                self.logger.info("selected drugs: %s", self.selected_drugs)
                if self.ALL_DRUGS in self.selected_drugs:
                    if not self.drug_type:
                        query.join("doc_type t", "t.id = v.doc_type")
                        query.join("document d", "d.id = v.id")
                        query.where("t.name = 'DrugInformationSummary'")
                elif self.SINGLE_AGENT_DRUGS in self.selected_drugs:
                    if not self.drug_type:
                        query.join("doc_type t", "t.id = v.doc_type")
                        query.join("document d", "d.id = v.id")
                        query.where("t.name = 'DrugInformationSummary'")
                    subquery = self.Query("query_term", "doc_id")
                    subquery.where(f"path = '{self.COMBO_PATH}'")
                    subquery.where("value = 'Yes'")
                    query.where(query.Condition("v.id", subquery, "NOT IN"))
                elif self.DRUG_COMBOS in self.selected_drugs:
                    query.join("query_term c", "c.doc_id = v.id")
                    query.where(f"c.path = '{self.COMBO_PATH}'")
                    query.where("c.value = 'Yes'")
                else:
                    doc_ids = self.selected_drugs
                    query.where(query.Condition("v.id", doc_ids, "IN"))
            elif self.selection_method == "type":
                subquery = self.Query("query_term", "doc_id")
                subquery.where(query.Condition("path", self.REFTYPE_PATH))
                subquery.where(query.Condition("value", self.reftype))
                query.where(query.Condition("v.id", subquery, "IN"))
            elif self.selection_method == "fda":
                if not self.fda_approval_status:
                    self.bail("No FDA approval options selected")
                paths = []
                for key in self.fda_approval_status:
                    if key in self.FDA_PATHS:
                        paths.append(self.FDA_PATHS[key])
                    else:
                        self.bail()
                query.join("query_term f", "f.doc_id = v.id")
                query.where(query.Condition("f.path", paths, "IN"))
                query.where("f.value = 'Yes'")
            query.log(label="huh?")
            try:
                rows = query.execute(timeout=300).fetchall()
            except Exception:
                query.log(label="drug summaries")
                self.logger.exception("drug summaries")
                self.bail("database query failure finding drug summaries")
            self._summaries = [DrugInfoSummary(self, row) for row in rows]
        return self._summaries


class DrugInfoSummary:
    """Drug document to be represented on the report."""

    FILTER = "name:Format DIS SummarySection"
    PARMS = {"suppress-nbsp": "true"}
    PARSER = html.HTMLParser()
    URL = "QcReport.py?Session=guest&DocId={}&DocVersion=-1"
    FDA_PATH = "DrugInfoMetaData/FDAApproved"
    DRUG_TYPE_PATH = "DrugInfoMetaData/DrugType"

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to the current login session and report tools
        """

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Use lowercase names for sorting."""
        return self.key < other.key

    @property
    def accelerated_approval(self):
        """True if this drug has been given accelerated approval."""

        if not hasattr(self, "_accelerated_approval"):
            self._accelerated_approval = False
            if self.fda_approved_node is not None:
                if self.fda_approved_node.get("Accelerated") == "Yes":
                    self._accelerated_approval = True
        return self._accelerated_approval

    @property
    def approved_in_children(self):
        """True if this drug has been approved for pediatric applications."""

        if not hasattr(self, "_approved_in_children"):
            self._approved_in_children = False
            if self.fda_approved_node is not None:
                if self.fda_approved_node.get("ApprovedInChildren") == "Yes":
                    self._approved_in_children = True
        return self._approved_in_children

    @property
    def control(self):
        """Access to the current login session and report creation tools."""
        return self.__control

    @property
    def description(self):
        """String description of the drug summary page."""

        if not hasattr(self, "_description"):
            for node in self.doc.root.iter("Description"):
                self._description = "".join(self.fetch_text(node)).strip()
        return self._description

    @property
    def doc(self):
        """`Doc` object for this version of the drug summary document."""

        if not hasattr(self, "_doc"):
            opts = dict(id=self.__row.id, version=self.__row.num)
            self._doc = Doc(self.control.session, **opts)
        return self._doc

    @property
    def drug_types(self):
        """Sequence of strings for drug type names used for this drug."""

        if not hasattr(self, "_drug_types"):
            self._drug_types = []
            for node in self.doc.root.findall(self.DRUG_TYPE_PATH):
                value = Doc.get_text(node, "").strip()
                if value:
                    self._drug_types.append(value)
        return self._drug_types

    @property
    def fda_approved_node(self):
        """Required node for FDA approval information."""

        if not hasattr(self, "_fda_approved_node"):
            self._fda_approved_node = self.doc.root.find(self.FDA_PATH)
        return self._fda_approved_node

    @property
    def key(self):
        """Use lowercase names for sorting."""

        if not hasattr(self, "_key"):
            self._key = self.name.lower()
        return self._key

    @property
    def link(self):
        """Link to the document's QC report."""

        if not hasattr(self, "_link"):
            B = self.control.HTMLPage.B
            url = self.URL.format(self.doc.id)
            self._link = B.A(str(self.doc.id), href=url)
        return self._link

    @property
    def name(self):
        """Drug name, extracted from the document's title."""

        if not hasattr(self, "_name"):
            self._name = self.doc.title.split(";")[0].strip()
        return self._name

    @property
    def summary(self):
        """Body of document, filtered to extract content for table cell."""

        if not hasattr(self, "_summary"):
            try:
                response = self.doc.filter(self.FILTER, parms=self.PARMS)
                td = f"<td>{response.result_tree}</td>"
            except Exception:
                self.control.logger.exception("filtering %s", self.doc.cdr_id)
                td = '<td><span class="error">UNAVAILABLE</span>'
            self._summary = html.fromstring(td, parser=self.PARSER)
        return self._summary

    @property
    def table(self):
        """Assemble the report table for this drug summary."""

        if not hasattr(self, "_table"):
            B = self.control.HTMLPage.B
            ok_for_kids = "Yes" if self.approved_in_children else "No"
            accelerated = "Yes" if self.accelerated_approval else "No"
            types = ", ".join(self.drug_types)
            self._table = B.TABLE(
                B.TR(B.TH("CDR ID"), B.TD(self.link)),
                B.TR(B.TH("Drug Name"), B.TD(self.name)),
                B.TR(B.TH("Drug Type(s)"), B.TD(types)),
                B.TR(B.TH("Accelerated Approval"), B.TD(accelerated)),
                B.TR(B.TH("Approved in Children"), B.TD(ok_for_kids)),
                B.TR(B.TH("Description"), B.TD(self.description)),
                B.TR(B.TH("Summary"), self.summary),
                B.CLASS("dis"),
            )
        return self._table

    @staticmethod
    def fetch_text(node):
        """Recurse through nodes to get text, skipping Deletion elements."""

        if node is None:
            return []
        text = []
        if node.text is not None:
            text.append(node.text)
        for child in node:
            if child.tag != "Deletion":
                text += DrugInfoSummary.fetch_text(child)
        if node.tail is not None:
            text.append(node.tail)
        return text


if __name__ == "__main__":
    "Allow documentation and lint tools to load script without side effects"
    Control().run()
