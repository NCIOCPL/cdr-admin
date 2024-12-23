#!/usr/bin/env python

"""Filter CDR documents.
"""

from functools import cached_property
from lxml import etree
from cdrapi.docs import Doc, FilterSet
from cdrcgi import Controller
from cdr import DEFAULT_DTD, PDQDTDPATH, expandFilterSets, getFilterSet


class Control(Controller):
    """
    Encapsulates the logic for this script. The user has three choices:
     1. Run the document through one or more filters and show the result.
     2. Filter the document, validate it, and show the warnings and errors.
     3. Show all of the filter sets which contain the specified filters.
    """

    SUBTITLE = "CDR Document Filtering"
    LOGNAME = "filter"
    FILTER = "Submit Filter Request"
    VALIDATE = "Filter and Validate"
    QCSETS = "QC Filter Sets"
    SCRIPT = "/js/filter.js"
    CSS = (
        ".action-buttons { text-wrap: nowrap; }",
        ".action-buttons .usa-button { margin-top: 0; }",
        ".usa-form a:visited { color: white; }",
    )

    def build_tables(self):
        """Return the single table used for this report."""
        return self.table

    def populate_form(self, page):
        """Replace the static CdrFilter.html with page with dynamic menus.

        Required positional argument:
          page - instance of the HTMLPage class
        """

        # Add fields for selecting the document to be filtered.
        fieldset = page.fieldset("Document")
        opts = dict(value="62902", label="Doc ID")
        fieldset.append(page.text_field("DocId", **opts))
        opts = dict(value="lastp", label="Doc Version")
        fieldset.append(page.text_field("DocVer", **opts))
        page.form.append(fieldset)

        # Let the user configure miscellaneous options for the filtering.
        fieldset = page.fieldset("Miscellaneous Options")
        opts = dict(value="pdqCG.dtd", label="DTD")
        fieldset.append(page.text_field("newdtd", **opts))
        page.form.append(fieldset)

        # Start with a single filter field, to which the user can add more.
        fieldset = page.fieldset("Filter(s)", id="filters")
        legend = fieldset.find("legend")
        add_button = page.B.SPAN(
            page.B.IMG(
                page.B.CLASS("clickable"),
                src="/images/add.gif",
                onclick="add_filter_field();",
                title="Add another filter"
            ),
            page.B.CLASS("filter-button")
        )
        legend.append(add_button)
        opts = dict(
            value="name:Passthrough Filter",
            widget_id="filter-1",
            label="",
            wrapper_classes="filter",
        )
        fieldset.append(page.text_field("filter", **opts))
        page.form.append(fieldset)

        # Control parameters implied by report type.
        fieldset = page.fieldset("Report")
        checkboxes = (
            ("ispp", "Publish Preview", False),
            ("isqc", "QC Report", True),
        )
        for id, label, checked in checkboxes:
            opts = dict(widget_id=id, label=label, checked=checked)
            fieldset.append(page.checkbox(id, value="true", **opts))
        page.form.append(fieldset)

        # Ask which type of QC report is wanted (if applicable).
        fieldset = page.fieldset("Summary Markup")
        buttons = (
            ("Y", "rsmarkup", "Redline/Strikeout, New Patient", True),
            ("N", "bu", "Bold/Underline", False),
        )
        for value, id, label, checked in buttons:
            opts = dict(
                widget_id=id,
                label=label,
                value=value,
                checked=checked,
            )
            fieldset.append(page.radio_button("rsmarkup", **opts))
        page.form.append(fieldset)

        # Which type(s) of board is the filter for (if applicable)?
        fieldset = page.fieldset("Display Markup for Board")
        checkboxes = (
            ("editorial", "Editorial", True),
            ("advisory", "Advisory", False),
        )
        for id, label, checked in checkboxes:
            opts = dict(widget_id=id, label=label, checked=checked)
            fieldset.append(page.checkbox(id, value="true", **opts))
        page.form.append(fieldset)

        # Which revision levels should be applied?
        fieldset = page.fieldset("Revision Levels")
        checkboxes = (
            ("publish", "publish", False),
            ("approved", "approved", True),
            ("proposed", "proposed", False),
        )
        for id, label, checked in checkboxes:
            opts = dict(widget_id=id, label=label, checked=checked)
            fieldset.append(page.checkbox(id, value="true", **opts))
        page.form.append(fieldset)

        # Add options applicable to glossary filtering.
        fieldset = page.fieldset("Glossary Definitions")
        checkboxes = (
            ("glosspatient", "Patient", True),
            ("glosshp", "Health Professional", True),
        )
        for id, label, checked in checkboxes:
            opts = dict(widget_id=id, label=label, checked=checked)
            fieldset.append(page.checkbox(id, value="true", **opts))
        page.form.append(fieldset)

        # Optional elements to be included.
        fieldset = page.fieldset("Miscellaneous Display Options")
        checkboxes = (
            ("images", "Images", True),
            ("glossary", "Glossary Terms", False),
            ("stdword", "Standard Wording", False),
            ("loeref", "LOE Refs", False),
        )
        for id, label, checked in checkboxes:
            opts = dict(widget_id=id, label=label, checked=checked)
            fieldset.append(page.checkbox(id, value="true", **opts))
        page.form.append(fieldset)

        # Add fields for a custom parameter (more can be added).
        fieldset = page.fieldset("Custom Parameter(s)", id="parameters")
        legend = fieldset.find("legend")
        add_button = page.B.SPAN(
            page.B.IMG(
                page.B.CLASS("clickable"),
                src="/images/add.gif",
                onclick="add_parameter_fields();",
                title="Add another parameter"
            ),
            page.B.CLASS("term-button")
        )
        legend.append(add_button)
        opts = dict(label="Name", wrapper_classes="parm-name")
        fieldset.append(page.B.DIV(
            page.text_field("parm-name-1", **opts),
            page.text_field("parm-value-1", label="Value"),
            page.B.CLASS("parameter")
        ))
        page.form.append(fieldset)
        page.add_css("\n".join([
            ".filter-button, .term-button { padding-left: 10px; }",
            "#parameters div div { display: inline-block; width: 45%; }",
            "#parameters .parm-name { margin-right: 1rem; }",
        ]))
        param_count = page.hidden_field("parm-count", "1")
        param_count.set("id", "parm-count")
        page.form.append(param_count)
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def run(self):
        """Handle the custom actions."""

        try:
            if self.table:
                self.show_report()
            elif self.filter_specs:
                self.send_page(self.filtered_xml, self.text_type)
            else:
                self.show_form()
        except Exception as e:
            self.logger.exception("Filter failure")
            self.bail(f"Filter failure: {e}")

    def show_report(self):
        """Override the base class method to add custom styling."""

        if self.filter_set_table:
            self.report.page.add_css("\n".join(self.CSS))
        self.report.send(self.format)

    def get_member_sets(self, set_name):
        """Extract the names of filter sets that are member of the named set.

        Required positional argument:
          set_name - string for unique name of filter set

        Return:
           list of filter set names up to two levels down
        """

        sub_sets = []
        for member in getFilterSet(self.session, set_name).members:
            if isinstance(member.id, int):
                sub_sets.append(member.name)
                # If we're using filter sets more than 3 levels deep we
                # need to convert this portion into a recursive call
                for member2 in getFilterSet(self.session, member.name).members:
                    if isinstance(member.id, int):
                        sub_sets.append(member2.name)
        return sub_sets

    @cached_property
    def all_filter_ids(self):
        """Set of integers for the Filter documents in the system."""
        return {id for id in self.all_filters.values()}

    @cached_property
    def all_filter_sets(self):
        """Dictionary of filter set IDs indexed by normalized title."""

        filter_sets = {}
        for id, name in FilterSet.get_filter_sets(self.session):
            filter_sets[name.upper()] = id
        return filter_sets

    @cached_property
    def all_filters(self):
        """Dictionary of filter IDs indexed by normalized title."""

        filters = {}
        for filter in FilterSet.get_filters(self.session):
            filters[filter.title.upper()] = filter.id
        return filters

    @cached_property
    def audiences(self):
        """Audience(s) selected for glossary definitions."""

        audiences = []
        for audience in ("patient", "hp"):
            if self.fields.getvalue(f"gloss{audience}") == "true":
                audiences.append(audience)
        return audiences

    @cached_property
    def boards(self):
        """Editorial and/or advisory PDQ boards."""

        boards = []
        for board in ("editorial", "advisory"):
            if self.fields.getvalue(board) == "true":
                boards.append(f"{board}-board")
        return boards

    @cached_property
    def buttons(self):
        """Custom buttons for the filtering form."""
        return (self.FILTER, self.VALIDATE, self.QCSETS)

    @cached_property
    def comments(self):
        """(I)nternal, (E)xternal, (A)ll, or (N)one."""

        comments = "N"
        if self.fields.getvalue("internal") == "true":
            comments = "I"
        if self.fields.getvalue("external") == "true":
            comments = "A" if comments == "I" else "E"
        return comments

    @cached_property
    def doc(self):
        """`Doc` object for the CDR document to be filtered."""

        id = self.fields.getvalue(self.DOCID)
        if not id:
            return None
        try:
            id = Doc.extract_id(id)
        except Exception:
            self.bail("Unrecognized document ID format")
        version = self.fields.getvalue("DocVer") or "0"

        # If no version is specified the default version is the CWD
        # which is indicated with a version=None.  Need to allow
        # "None" as a valid value.
        allowed = "None", "last", "lastp"
        if not version.isdigit() and version not in allowed:
            self.bail(f"Invalid version {version!r}.")
        return Doc(self.session, id=id, version=version)

    @cached_property
    def dtd(self):
        """Object for validating the filtered CDR document."""

        path = self.fields.getvalue("newdtd", DEFAULT_DTD)
        if "/" not in path and "\\" not in path:
            path = f"{PDQDTDPATH}/{path}"
        try:
            with open(path) as fp:
                return etree.DTD(fp)
        except Exception as e:
            self.logger.exception("Failure loading %s", path)
            self.bail(f"Failure loading {path}: {e}")

    @cached_property
    def filter_ids(self):
        """CDR document IDs for filters selected directly for this report."""
        return {s.filter_id for s in self.filter_specs if s.filter_id}

    @cached_property
    def filter_result(self):
        """Object with the result_tree, warning messages, and errors."""

        specs = [spec.identifier for spec in self.filter_specs]
        try:
            return self.doc.filter(*specs, parms=self.parms)
        except Exception as e:
            self.logger.exception("filtering %s", self.doc.cdr_id)
            self.bail(f"failure filtering {self.doc.cdr_id}: {e}")

    @cached_property
    def filter_set_table(self):
        """Table showing the filter sets relevant to this filtering job."""

        # If no filters or sets were specified, we behave as if the
        # "QC Filter Sets" button had been clicked. If there are
        # filters and/or filter sets identified, and the button was
        # not clicked, nothing to do here.
        if self.filter_specs and not self.qc_filter_sets:
            return None

        # Show the sets named by the user, as well as sets which contain
        # the users's sets.
        user_sets = [s.set_name for s in self.filter_specs if s.set_name]
        if user_sets:
            rows = []
            for resolved_set in self.resolved_filter_sets:
                for name in user_sets:
                    if name == resolved_set.name:
                        rows.append(resolved_set.row)
                    elif name in self.get_member_sets(resolved_set.name):
                        rows.append(resolved_set.row)

        # If the user didn't name any sets, show the sets which match the
        # filters the user specified.
        else:
            rows = [s.row for s in self.resolved_filter_sets if s.in_scope]

        # Assemble the table.
        if rows:
            columns = "Set Name", "Action", "Set Detail"
        else:
            if user_sets:
                columns = ["Specified filter sets not found"]
            else:
                columns = ["No filter sets include all selected filters"]
        return self.Reporter.Table(rows, columns=columns)

    @cached_property
    def filter_specs(self):
        """Filters and filter sets chosen for filtering the CDR document."""

        values = self.fields.getlist("filter") or self.fields.getlist("Filter")
        self.logger.info("filter_specs() values=%r", values)
        specs = []
        for value in values:
            if value:
                spec = FilterSpec(self, value)
                if spec.error:
                    self.bail(spec.error)
                specs.append(spec)
        self.logger.info("%d specs found", len(specs))
        return specs

    @cached_property
    def filtered_xml(self):
        """String for the document's XML, ready to be returned to the user."""

        xml = str(self.filter_result.result_tree)
        return xml.replace("@@DOCID@@", self.doc.cdr_id)

    @property
    def glossary(self):
        """True if glossary term display options are requested."""
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
        """True if level-of-evidence display options are requested."""
        return self.fields.getvalue("loeref") == "true"

    @cached_property
    def markup_levels(self):
        """Level(s) of insertion/deletion markup which should be applied."""

        levels = []
        for level in ("publish", "approved", "proposed", "rejected"):
            if self.fields.getvalue(level) == "true":
                levels.append(level)
        return levels

    @property
    def method(self):
        """Override the form method so the parameters are in the URL."""
        return "GET"

    @cached_property
    def parms(self):
        """Pack up the parameters to be fed to the CDR filter module."""

        parms = dict(
            insRevLevels="_".join(self.markup_levels),
            delRevLevels="N" if self.redline_strikeout else "Y",
            DisplayComments=self.comments,
            DisplayGlossaryTermList="Y" if self.glossary else "N",
            DisplayImages="Y" if self.display_images else "N",
            ShowStandardWording="Y" if self.standard_wording else "N",
            displayBoard="_".join(self.boards),
            displayAudience="_".join(self.audiences),
            isPP="Y" if self.is_pp else "N",
            isQC="Y" if self.is_qc else "N",
            displayLOETermList="Y" if self.loeref else "N",
        )
        if self.vendor_or_qc:
            parms["vendorOrQC"] = "QC"
        parm_count = int(self.fields.getvalue("parm-count") or "0")
        for i in range(parm_count):
            name = self.fields.getvalue(f"parm-name-{i+1}")
            if name:
                value = self.fields.getvalue(f"parm-value-{i+1}", "")
                parms[name.strip()] = value.strip()
        self.logger.info("Filter.py(parms=%r)", parms)
        return parms

    @cached_property
    def qc_filter_sets(self):
        """True if the the users asked for display of QC filter sets."""

        if self.fields.getvalue("qcFilterSets") == "Y":
            return True
        return self.request == self.QCSETS

    @property
    def redline_strikeout(self):
        """Default is True, but turned off for a bold/underline report."""
        return self.fields.getvalue("rsmarkup") not in ("N", "false")

    @cached_property
    def resolved_filter_sets(self):
        """Sequence of `ResolvedFilterSet` objects."""

        sets = expandFilterSets(self.session)
        resolved_sets = []
        for name in sorted(sets):
            filter_set = ResolvedFilterSet(self, sets[name])
            resolved_sets.append(filter_set)
        return resolved_sets

    @property
    def display_images(self):
        """True if images display option is requested."""
        return self.fields.getvalue("images") == "true"

    @cached_property
    def same_window(self):
        """Reduce generation of new browser tabs."""
        return [self.SUBMIT] if self.request else []

    @property
    def standard_wording(self):
        """True if standard wording display options are requested."""
        return self.fields.getvalue("stdword") == "true"

    @property
    def subtitle(self):
        """What we display under the main banner."""

        if not self.doc:
            return self.SUBTITLE
        cdr_id = f"{self.doc.doctype} Doc CDR{self.doc.id}"
        if self.filter_set_table:
            return f"Filter Sets for Filtering of {cdr_id}"
        return f"Validation Results for Filtered {cdr_id}"

    @property
    def table(self):
        """Pick the table requested for this report."""

        if not self.doc:
            return None
        return self.validation_table or self.filter_set_table or None

    @property
    def text_type(self):
        """String to let the browser know what type of text we're returning."""
        return "xml" if "<?xml" in self.filtered_xml else "html"

    @cached_property
    def validation_table(self):
        """Assemble the table showing the validation results."""

        if self.fields.getvalue("validate") != "Y":
            if self.request != self.VALIDATE:
                return None
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
        return self.Reporter.Table(rows, columns=columns)

    @cached_property
    def vendor_or_qc(self):
        """Are we filtering for export or for QC review?"""

        if self.fields.getvalue("QC") == "true":
            return "QC"
        return self.fields.getvalue("vendorOrQC", "")


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
        if not identifier:
            raise Exception("Missing identifier for FilterSpec")

    @property
    def control(self):
        """Access to the report's options and report-creation tools."""
        return self.__control

    @cached_property
    def error(self):
        """Optional string explaining why this filter spec is unusable."""

        error = None
        if self.set_name:
            if self.set_name.upper() not in self.control.all_filter_sets:
                args = self.set_name, self.control.session.tier
                message = "{} is not a filter set on the CDR {} server"
                error = message.format(*args)
        elif self.filter_name:
            if self.filter_name.upper() not in self.control.all_filters:
                args = self.filter_name, self.control.session.tier
                message = "{} is not a filter name on the CDR {} server"
                error = message.format(*args)
        elif self.filter_id not in self.control.all_filter_ids:
            args = self.identifier, self.control.session.tier
            message = "{} is not a filter ID on the CDR {} server"
            error = message.format(*args)
        return error

    @cached_property
    def filter_id(self):
        """Integer for the ID of a CDR Filter document."""

        filter_id = None
        if self.filter_name:
            key = self.filter_name.upper()
            filter_id = self.control.all_filters[key]
        elif not self.set_name:
            try:
                filter_id = Doc.extract_id(self.identifier)
            except Exception:
                self.control.logger.exception("FilterSpec.filter_id()")
                id = self.__identifier
                self.control.bail(f"{id!r} is not a well-formed CDR ID")
        return filter_id

    @cached_property
    def filter_name(self):
        """String for the name of a CDR filter."""

        if self.identifier.startswith("name:"):
            return self.identifier.removeprefix("name:")
        return None

    @property
    def identifier(self):
        """String identifying the filter or filter set."""
        return self.__identifier

    @cached_property
    def set_name(self):
        """String for the name of a CDR filter set."""

        if self.identifier.startswith("set:"):
            return self.identifier.removeprefix("set:")
        return None


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

    @cached_property
    def filter_ids(self):
        """Sequence of filter ID integers for this set."""
        return [Doc.extract_id(m.id) for m in self.__set.members]

    @cached_property
    def in_scope(self):
        """True if this set should be included on the report.

        If any filters are specified directly by the user, then we
        only want to include sets which contain *all* of those filters.
        Otherwise, we include all sets in the system.

        This property is only useful if a filter ID or filter name has
        been specified.  It cannot be used for filter sets.
        """

        user_ids = self.__control.filter_ids
        if not user_ids:
            return True
        return False if set(user_ids) - set(self.filter_ids) else True

    @property
    def name(self):
        """String for the set's name."""
        return self.__set.name

    @property
    def row(self):
        """Sequence of cell values for the report's table row for this set."""

        control = self.__control
        B = control.HTMLPage.B
        params = {
            control.DOCID: control.doc.cdr_id,
            "DocVer": control.doc.version,
            "filter": self.filter_ids,
        }
        if control.vendor_or_qc:
            params["vendorOrQC"] = control.vendor_or_qc
        filter_url = control.make_url(control.script, **params)
        params["validate"] = "Y"
        validate_url = control.make_url(control.script, **params)
        buttons = B.SPAN(
            B.A("Filter", B.CLASS("usa-button"), href=filter_url),
            B.A("Validate", B.CLASS("usa-button"), href=validate_url),
            B.CLASS("action-buttons"),
        )
        members = [f"{m.id}:{m.name}" for m in self.__set.members]
        return self.name, buttons, members


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
