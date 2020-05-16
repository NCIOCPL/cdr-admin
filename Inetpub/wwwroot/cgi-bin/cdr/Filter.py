#!/usr/bin/env python

"""Filter CDR documents.
"""

from lxml import etree
from cdrapi.docs import Doc, FilterSet
from cdrcgi import Controller, DOCID
from cdr import DEFAULT_DTD, PDQDTDPATH, expandFilterSets


class Control(Controller):
    """
    Encapsulates the logic for this script. The user has three choices:
     1. Run the document through one or more filters and show the result.
     2. Filter the document, validate it, and show the warnings and errors.
     3. Show all of the filter sets which contain the specified filters.
    """

    LOGNAME = "filter"
    FILTER = "Submit Filter Request"
    VALIDATE = "Filter and Validate"
    QCSETS = "QC Filter Sets"
    TITLE = "CDR Filtering"
    CSS = ".action-buttons a { padding-left: 2px; padding-right: 2px; }"

    def build_tables(self):
        """Return the single table used for this report."""
        return self.table

    def run(self):
        """Override the base class version: the form is static HTML."""

        if self.table:
            self.show_report()
        elif self.filter_specs:
            self.send_page(self.filtered_xml, self.text_type)
        else:
            self.bail("No filters specified")

    def show_report(self):
        """Override the base class method to add custom styling."""

        if self.filter_set_table:
            self.report.page.add_css(self.CSS)
        self.report.send(self.format)

    @property
    def all_filter_ids(self):
        """Set of integers for the Filter documents in the system."""

        if not hasattr(self, "_all_filter_ids"):
            self._all_filter_ids = {id for id in self.all_filters.values()}
        return self._all_filter_ids

    @property
    def all_filter_sets(self):
        """Dictionary of filter set IDs indexed by normalized title."""

        if not hasattr(self, "_all_filter_sets"):
            self._all_filter_sets = {}
            for id, name in FilterSet.get_filter_sets(self.session):
                self._all_filter_sets[name.upper()] = id
        return self._all_filter_sets

    @property
    def all_filters(self):
        """Dictionary of filter IDs indexed by normalized title."""

        if not hasattr(self, "_all_filters"):
            self._all_filters = {}
            for filter in FilterSet.get_filters(self.session):
                self._all_filters[filter.title.upper()] = filter.id
        return self._all_filters

    @property
    def audiences(self):
        """Audience(s) selected for glossary definitions."""

        if not hasattr(self, "_audiences"):
            self._audiences = []
            for audience in ("patient", "hp"):
                if self.fields.getvalue(f"gloss{audience}") == "true":
                    self._audiences.append(audience)
        return self._audiences

    @property
    def boards(self):
        """Editorial and/or advisory PDQ boards."""

        if not hasattr(self, "_boards"):
            self._boards = []
            for board in ("editorial", "advisory"):
                if self.fields.getvalue(board) == "true":
                    self._boards.append(f"{board}-board")
        return self._boards

    @property
    def comments(self):
        """(I)nternal, (E)xternal, (A)ll, or (N)one."""

        if not hasattr(self, "_comments"):
            self._comments = "N"
            if self.fields.getvalue("internal") == "true":
                self._comments = "I"
            if self.fields.getvalue("external") == "true":
                self._comments = "A" if self.comments == "I" else "E"
        return self._comments

    @property
    def doc(self):
        """`Doc` object for the CDR document to be filtered."""

        if not hasattr(self, "_doc"):
            id = self.fields.getvalue(DOCID)
            if not id:
                self.bail("No Document", self.TITLE)
            try:
                id = Doc.extract_id(id)
            except Exception:
                self.bail("Unrecognized document ID format")
            version = self.fields.getvalue("DocVer", "0")
            if not version.isdigit() and version not in ("last", "lastp"):
                self.bail(f"Invalid version {version!r}")
            self._doc = Doc(self.session, id=id, version=version)
        return self._doc

    @property
    def dtd(self):
        """Object for validating the filtered CDR document."""

        if not hasattr(self, "_dtd"):
            path = self.fields.getvalue("newdtd", DEFAULT_DTD)
            if "/" not in path and "\\" not in path:
                path = f"{PDQDTDPATH}/{path}"
            try:
                with open(path) as fp:
                    self._dtd = etree.DTD(fp)
            except Exception as e:
                self.logger.exception("Failure loading %s", path)
                self.bail("Failure loading {path}: {e}")
        return self._dtd

    @property
    def filter_ids(self):
        """CDR document IDs for filters selected directly for this report."""

        if not hasattr(self, "_filter_ids"):
            specs = self.filter_specs
            self._filter_ids = {s.filter_id for s in specs if s.filter_id}
        return self._filter_ids

    @property
    def filter_result(self):
        """Object with the result_tree, warning messages, and errors."""

        if not hasattr(self, "_filter_result"):
            specs = [spec.identifier for spec in self.filter_specs]
            try:
                self._filter_result = self.doc.filter(*specs, parms=self.parms)
            except Exception as e:
                self.logger.exception("filtering %s", self.doc.cdr_id)
                self.bail(f"failure filtering {self.doc.cdr_id}: {e}")
        return self._filter_result

    @property
    def filter_set_table(self):
        """Table showing the filter sets relevant to this filtering job.

        Show the user the filter sets that contain the selected
        filter(s). Skip over named sets specified by the user.
        """

        if not hasattr(self, "_filter_set_table"):
            table_requested = self.fields.getvalue("qcFilterSets") == "Y"
            if table_requested or not self.filter_ids:
                columns = "Set Name", "Action", "Set Detail"
                rows = []
                for filter_set in self.resolved_filter_sets:
                    if filter_set.in_scope:
                        rows.append(filter_set.row)
                if not rows:
                    columns = ["No filter sets include all selected filters"]
                opts = dict(columns=columns)
                self._filter_set_table = self.Reporter.Table(rows, **opts)
            else:
                self._filter_set_table = None
        return self._filter_set_table

    @property
    def resolved_filter_sets(self):
        """Sequence of `ResolvedFilterSet` objects."""

        if not hasattr(self, "_resolved_filter_sets"):
            filter_sets = expandFilterSets(self.session)
            self._resolved_filter_sets = []
            for name in sorted(filter_sets):
                filter_set = ResolvedFilterSet(self, filter_sets[name])
                self._resolved_filter_sets.append(filter_set)
        return self._resolved_filter_sets

    @property
    def filter_specs(self):
        """Filters and filter sets chosen for filtering the CDR document."""

        if not hasattr(self, "_filter_specs"):
            values = self.fields.getlist("filter")
            if not values:
                values = self.fields.getlist("Filter")
            self._filter_specs = []
            for value in values:
                spec = FilterSpec(self, value)
                if spec.error:
                    self.bail(spec.error)
                self._filter_specs.append(spec)
        return self._filter_specs

    @property
    def filtered_xml(self):
        """String for the document's XML, ready to be returned to the user."""

        if not hasattr(self, "_filtered_xml"):
            xml = str(self.filter_result.result_tree)
            self._filtered_xml = xml.replace("@@DOCID@@", self.doc.cdr_id)
        return self._filtered_xml

    @property
    def glossary(self):
        """True if glossary term print options are requested."""
        return self.fields.getvalue("glossary") == "true"

    @property
    def is_pp(self):
        """True if we're preparing a publish preview report."""
        return self.fields.getvalue("ispp") == "true"

    @property
    def is_qc(self):
        """True if we're preparing a QC report."""
        return self.fields.getvalue("isqc") == "true"

    @property
    def loeref(self):
        """True if level-of-evidence print options are requested."""
        return self.fields.getvalue("loeref") == "true"

    @property
    def markup_levels(self):
        """Level(s) of insertion/deletion markup which should be applied."""

        if not hasattr(self, "_markup_levels"):
            self._markup_levels = []
            for level in  ("publish", "approved", "proposed", "rejected"):
                if self.fields.getvalue(level) == "true":
                    self._markup_levels.append(level)
        return self._markup_levels

    @property
    def parms(self):
        """Pack up the parameters to be fed to the CDR filter module."""

        if not hasattr(self, "_parms"):
            self._parms = dict(
                insRevLevels="_".join(self.markup_levels),
                delRevLevels="N" if self.redline_strikeout else "Y",
                DisplayComments=self.comments,
                DisplayGlossaryTermList="Y" if self.glossary else "N",
                ShowStandardWording="Y" if self.standard_wording else "N",
                displayBoard="_".join(self.boards),
                displayAudience="_".join(self.audiences),
                isPP="Y" if self.is_pp else "N",
                isQC="Y" if self.is_qc else "N",
                displayLOETermList="Y" if self.loeref else "N",
            )
            if self.vendor_or_qc:
                self._parms["vendorOrQC"] = "QC"
            self.logger.info("Filter.py(parms=%r)", self._parms)
        return self._parms

    @property
    def redline_strikeout(self):
        """Default is True, but turned off for a bold/underline report."""
        return self.fields.getvalue("rsmarkup") != "false"

    @property
    def standard_wording(self):
        """True if standard wording print options are requested."""
        return self.fields.getvalue("stdword") == "true"

    @property
    def subtitle(self):
        """What we display under the main banner."""

        cdr_id = f"{self.doc.doctype} Document {self.doc.cdr_id}"
        if self.filter_set_table:
            return f"QC Filter Sets for CDR XSL/T Filtering of {cdr_id}"
        return f"Validation Results for Filtered {cdr_id}"

    @property
    def table(self):
        """Pick the table requested for this report."""
        return self.validation_table or self.filter_set_table or None

    @property
    def text_type(self):
        """String to let the browser know what type of text we're returning."""
        return "xml" if "<?xml" in self.filtered_xml else "html"

    @property
    def validation_table(self):
        """Assemble the table showing the validation results."""

        if not hasattr(self, "_validation_table"):
            if self.fields.getvalue("validate") == "Y":
                self.dtd.validate(self.filter_result.result_tree)
                errors = self.dtd.error_log.filter_from_errors()
                rows = []
                for message in self.filter_result.messages:
                    rows.append(("Warning", self.doc.cdr_id, "N/A", message))
                for error in errors:
                    rows.append([
                        error.level_name,
                        self.doc.cdr_id,
                        error.line,
                        error.message,
                    ])
                columns = "Type", "Document", "Line", "Message"
                if not rows:
                    columns = ["Document is valid"]
                opts = dict(columns=columns)
                self._validation_table = self.Reporter.Table(rows, **opts)
            else:
                self._validation_table = None
        return self._validation_table

    @property
    def vendor_or_qc(self):
        """Are we filtering for export or for QC review?"""

        if not hasattr(self, "_vendor_or_qc"):
            if self.fields.getvalue("QC") == "true":
                self._vendor_or_qc = "QC"
            else:
                self._vendor_or_qc = self.fields.getvalue("vendorOrQC", "")
        return self._vendor_or_qc


class FilterSpec:
    """Identification of a filter or a set of filters."""

    def __init__(self, control, identifier):
        """Remember the caller's values.

        Pass:
            control - access to the report's options and report-creation tools
            identifier - string identifying the filter or filter set
        """

        self.__control = control
        self.__identifier = identifier

    @property
    def control(self):
        """Access to the report's options and report-creation tools."""
        return self.__control

    @property
    def error(self):
        """Optional string explaining why this filter spec is unusable."""

        if not hasattr(self, "_error"):
            self._error = None
            if self.set_name:
                if self.set_name.upper() not in self.control.all_filter_sets:
                    args = self.set_name, self.control.tier
                    message = "{} not found on the CDR {} server"
                    self._error = message.format(*args)
            elif self.filter_name:
                if self.filter_name.upper() not in self.control.all_filters:
                    args = self.filter_name, self.control.tier
                    message = "{} is not a filter on the CDR {} server"
                    self._error = message.format(*args)
            elif self.filter_id not in self.control.all_filter_ids:
                args = self.identifier, self.control.tier
                message = "{} is not a filter on the CDR {} server"
                self._error = message.format(*args)
        return self._error

    @property
    def filter_id(self):
        """Integer for the ID of a CDR Filter document."""

        if not hasattr(self, "_filter_id"):
            self._filter_id = None
            if self.filter_name:
                key = self.filter_name.upper()
                self._filter_id = self.control.all_filters[key]
            elif not self.set_name:
                try:
                    self._filter_id = Doc.extract_id(self.identifier)
                except Exception:
                    id = self.identifier
                    self.control.bail(f"{id!r} is not a well-formed CDR ID")
        return self._filter_id

    @property
    def filter_name(self):
        """String for the name of a CDR filter."""

        if not hasattr(self, "_filter_name"):
            self._filter_name = None
            if self.identifier.startswith("name:"):
                self._filter_name = self.identifier[5:]
        return self._filter_name

    @property
    def identifier(self):
        """String identifying the filter or filter set."""
        return self.__identifier

    @property
    def set_name(self):
        """String for the name of a CDR filter set."""

        if not hasattr(self, "_set_name"):
            self._set_name = None
            if self.identifier.startswith("set:"):
                self._set_name = self.identifier[4:]
        return self._set_name


class ResolvedFilterSet:
    """Filter set with members in a single sequence.

    Members of nested sets have been hoisted up into a single list.
    Used for the QC Filter Sets option of the report.
    """

    def __init__(self, control, filter_set):
        """Remember the caller's values.

        Pass:
            control - access to the report's options
            filter_set - `cdr.FilterSet` object
        """

        self.__control = control
        self.__set = filter_set

    @property
    def filter_ids(self):
        """Sequence of filter ID integers for this set."""

        if not hasattr(self, "_filter_ids"):
            members = self.__set.members
            self._filter_ids = [Doc.extract_id(m.id) for m in members]
        return self._filter_ids

    @property
    def in_scope(self):
        """True if this set should be included on the report.

        If any filters are specified directly by the user, then we
        only want to include sets which contain *all* of those filters.
        Otherwise, we include all sets in the system.
        """

        user_ids = self.__control.filter_ids
        if not user_ids:
            return True
        return False if set(user_ids) - set(self.filter_ids) else True

    @property
    def row(self):
        """Sequence of cell values for the report's table row for this set."""

        control = self.__control
        B = control.HTMLPage.B
        params = {
            DOCID: control.doc.cdr_id,
            "DocVer": control.doc.version,
            "filter": self.filter_ids,
        }
        if control.vendor_or_qc:
            params["vendorOrQC"] = control.vendor_or_qc
        filter_url = control.make_url(control.script, **params)
        params["validate"] = "Y"
        validate_url = control.make_url(control.script, **params)
        buttons = B.SPAN(
            B.A(B.BUTTON("Filter"), href=filter_url),
            B.A(B.BUTTON("Validate"), href=validate_url),
            B.CLASS("action-buttons"),
        )
        members = [f"{m.id}:{m.name}" for m in self.__set.members]
        return self.__set.name, buttons, members


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
