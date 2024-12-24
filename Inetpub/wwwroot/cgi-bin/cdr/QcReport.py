#!/usr/bin/env python
"""Prepare a document for comprehensive reivew.
"""

from functools import cached_property
from json import dumps
from os import environ
from types import SimpleNamespace
from lxml import html
from cdr import FILTERS
from cdrapi.docs import Doc
from cdrcgi import Controller, HTMLPage


class Control(Controller):
    """Top-level logic for the report."""

    SUBTITLE = "QC Report"
    LOGNAME = "qc-report"
    METHOD = "GET"
    TITLES_BY_REPORT_TYPE = dict(
        bu="HP Bold/Underline QC Report",
        but="HP Bold/Underline QC Report (Test)",
        rs="HP Redline/Strikeout QC Report",
        rst="HP Redline/Strikeout QC Report (Test)",
        nm="QC Report (No Markup)",
        pat="PT Redline/Strikeout QC Report",
        patrs="PT Redline/Strikeout QC Report",
        patbu="PT Bold/Underline QC Report",
        pp="Publish Preview Report",
        img="Media QC Report",
        gtnwc="Glossary Term Name With Concept Report",
    )
    TITLES_BY_DOCTYPE = dict(
        GlossaryTermName="Glossary Term Name QC Report",
        GlossaryTermConcept="Glossary Term Concept QC Report",
        PDQBoardMemberInfo="PDQ Board Member Information QC Report",
        DrugInformationSummary="Drug Information Summary QC Report",
        Media="Media Document QC Report",
        Summary="Summary QC Report",
        MiscellaneousDocument="Miscellaneous Document QC Report",
    )
    UNRECOGNIZED_TYPE = "QC Report (Unrecognized Type)"
    GTC = "GlossaryTermConcept"
    GTC_DEFINITION_PATHS = f"/{GTC}/%TermDefinition/DefinitionText"
    TITLE_LABELS = dict(
        PDQBoardMemberInfo="Board Member Name",
        GlossaryTermConcept="Glossary Definition",
    )
    MARKUP_INSTRUCTIONS = (
        "Select Insertion/Deletion Markup to be displayed (one or more)."
    )
    MARKUP_BOARD_OPTIONS = (
        ("markup-editorial", "Editorial board markup"),
        ("markup-advisory", "Advisory board markup"),
    )
    MARKUP_LEVEL_OPTIONS = (
        ("markup-publish", "With publish attribute"),
        ("markup-approved", "With approved attribute"),
        ("markup-proposed", "With proposed attribute"),
    )
    MISCELLANEOUS_OPTIONS = (
        ("glossary", "Display glossary terms at end of report"),
        ("hp-reference", "Display HP Reference section"),
        ("images", "Display images"),
        ("publishable-images", "Use publishable images"),
        ("keypoints", "Display Key Point boxes"),
        ("std-wording", "Display standard wording with mark-up"),
        ("pat-cites", "Display Reference section"),
        ("more", "Display To Learn More section"),
        ("loes", "Display Level of Evidence terms"),
        ("shade-modules", "Display Modules Shaded"),
        ("qc-only-mods", "Display QC-only Modules (Board Members QC Report)"),
        ("section-meta", "Display Section Meta Data"),
        ("summary-refs", "Display Summary Ref and Fragment Ref Links"),
    )
    COMMENT_OPTIONS = (
        (
            ("com-int", "Internal Comments (excluding permanent comments)"),
            ("com-perm", "Permanent Comments (internal & external)"),
        ),
        (
            ("com-ext", "External Comments"),
            ("com-adv", "Advisory Board Comments (internal & external)"),
        ),
        (
            ("com-all", "All Comments"),
            ("com-none", "No Comments"),
        ),
    )
    DETAILED_COMMENT_OPTIONS = (
        (
            "Audience (txt color)",
            (
                ("com-aud-int", "Internal"),
                ("com-aud-ext", "External"),
            ),
            dict(YY="A", YN="I", NY="E", NN="N"),
        ),
        (
            "Source (txt spacing)",
            (
                ("com-src-ed", "Not Advisory"),
                ("com-src-adv", "Advisory"),
            ),
            dict(YY="A", YN="E", NY="V", NN="N"),
        ),
        (
            "Duration (background)",
            (
                ("com-dur-perm", "Permanent"),
                ("com-dur-temp", "Non-permanent"),
            ),
            dict(YY="A", YN="P", NY="R", NN="N"),
        ),
    )
    GLOSSARY_DEFINITION_OPTIONS = (
        ("glossary-definitions-hp", "Health Professional"),
        ("glossary-definitions-patient", "Patient"),
    )
    DEFAULT_OPTIONS = {
        "com-aud-int",
        "com-aud-ext",
        "com-dur-perm",
        "com-dur-temp",
        "com-int",
        "com-ext",
        "com-src-adv",
        "com-src-ed",
        "glossary-definitions-hp",
        "glossary-definitions-patient",
        "hp-reference",
        "keypoints",
        "markup-approved",
        "markup-editorial",
        "more",
        "pat-cites",
        "publishable-images",
    }
    HP_ONLY_OPTIONS = {"hp-reference", "loes"}
    HP_ONLY_DEFAULTS = {"com-ext", "com-adv", "com-aud-ext", "com-dur-perm"}
    PATIENT_ONLY_OPTIONS = {"keypoints", "std-wording", "pat-cites", "more"}
    PATIENT_ONLY_DEFAULTS = {"com-int", "com-aud-int", "com-src-adv"}
    HIDDEN_OPTIONS = {"publishable-images"}
    HIDDEN_FOR_PATIENT = {"com-adv"}
    IMAGE_VERSIONS = "pub", "unpub"

    def populate_form(self, page: HTMLPage):
        """Create cascading forms as needed.

        Required positional argument:
          page - instance of the cdrcgi.HTMLPage class
        """

        # Skip the form if we already have everything we need.
        if self.ready:
            return self.show_report()

        # Separate out the work to draw the complex "version" form.
        if self.version_needed:
            page.form.append(page.hidden_field("DocId", self.doc.id))
            self.show_version_form(page)

        # Ask the user to choose from multiple title fragment matches.
        elif self.titles:
            fieldset = page.fieldset("Choose Document")
            for id, title in self.titles:
                opts = dict(label=title, value=id)
                fieldset.append(page.radio_button("DocId", **opts))
            page.form.append(fieldset)

        # Otherwise, ask for an ID or a title fragment.
        else:
            fieldset = page.fieldset("Title or Document ID")
            opts = dict(
                label=self.TITLE_LABELS.get(self.doctype, "Document Title"),
                value=self.fragment,
                tooltip="Use % as wildcard.",
            )
            fieldset.append(page.text_field("DocTitle", **opts))
            label = "Document CDR ID"
            if self.doctype == "PDQBoardMemberInfo":
                label = "Board Member CDR ID"
            opts = dict(label=label, value=self.id)
            fieldset.append(page.text_field("DocId", **opts))
            page.form.append(fieldset)

        # Carry forward information we've gathered along the way.
        if self.report_type:
            page.form.append(page.hidden_field("ReportType", self.report_type))
        if self.doctype:
            page.form.append(page.hidden_field("DocType", self.doctype))
        if self.loglevel == "DEBUG":
            page.form.append(page.hidden_field("debug", True))

    def show_report(self):
        """Custom reporting handled by the filters."""

        if not self.ready:
            return self.show_form()
        args = self.doc.id, self.doc.version, self.doctype, self.parameters
        self.logger.info("QC for %s version %s type %s with parms %s", *args)
        if self.report_type == "pp":
            params = dict(ReportType="pp", DocId=self.doc.id)
            if self.doctype == "Summary":
                params["Version"] = "cwd"
            return self.redirect("PublishPreview.py", **params)
        if self.doctype == "Summary":
            self.logger.info("packing params")
            params = dict(
                DocId=self.doc.id,
                DocType=self.doctype,
                parmstring="yes",
                parmid=self.parameter_set_id,
            )
            if self.report_type:
                params["ReportType"] = self.report_type
            if self.version_integer:
                params["DocVersion"] = self.version_integer
            self.logger.info("packed params=%s", params)
            return self.redirect("QCforWord.py", **params)
        self.send_page(self.html_page)

    def show_version_form(self, page: HTMLPage):
        """Ask the user to choose a version and some report options.

        Required positional argument:
          page - instance of the HTMLPage class
        """

        # Ask the user to pick a version.
        legend = f"Select Document Version For CDR{self.doc.id}"
        fieldset = page.fieldset(legend)
        opts = dict(label="", options=self.versions, default="0")
        fieldset.append(page.select("DocVersion", **opts))
        page.form.append(fieldset)

        # Adjust available options and defaults appropriately.
        defaults = set(self.DEFAULT_OPTIONS)
        if self.patient:
            defaults -= self.HP_ONLY_DEFAULTS
            skip = self.HP_ONLY_OPTIONS
        else:
            defaults -= self.PATIENT_ONLY_DEFAULTS
            skip = self.PATIENT_ONLY_OPTIONS
        self.logger.debug("option defaults=%s", defaults)

        # Ask about board markup for HP Summaries.
        instructions = page.B.P(page.B.EM(self.MARKUP_INSTRUCTIONS))
        if self.fields.getvalue("accordions"):
            accordion = page.accordion("markup-options")
            accordion.payload.append(instructions)
            page.form.append(accordion.wrapper)
        else:
            page.form.append(instructions)
        if self.doc.doctype.name == "Summary" and not self.patient:
            fieldset = page.fieldset("Board Markup")
            for value, label in self.MARKUP_BOARD_OPTIONS:
                checked = value in defaults
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.checkbox("options", **opts))
            if self.fields.getvalue("accordions"):
                accordion.payload.append(fieldset)
            else:
                page.form.append(fieldset)

        # Ask about markup levels to be included.
        fieldset = page.fieldset("Revision-level Markup")
        for value, label in self.MARKUP_LEVEL_OPTIONS:
            checked = value in defaults
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("options", **opts))
        if self.fields.getvalue("accordions"):
            accordion.payload.append(fieldset)
        else:
            page.form.append(fieldset)

        # Options specific to GlossaryTermName documents come next.
        # XXX Commented out, because unless I'm misreading the original
        #     code, there was no logical path which results in display
        #     of the "version" form for GTN documents.
        # if self.doc.doctype.name == "GlossaryTermName":
        #     fieldset = page.fieldset("Display Audience Definition")
        #     for value, label in self.GLOSSARY_DEFINITION_OPTIONS:
        #         checked = value in defaults
        #         opts = dict(value=value, label=label, checked=checked)
        #         fieldset.append(page.checkbox("options", **opts))
        #     page.form.append(fieldset)

        # Show the miscellaneous options here for patient summaries.
        if self.doc.doctype.name == "Summary" and self.patient:
            self.show_miscellaneous_options(page, defaults, skip)

        # Let the user choose which comment types should be displayed.
        if self.doc.doctype.name == "Summary":
            fieldset = page.fieldset("Select Comment Types to be displayed")
            for subset in self.COMMENT_OPTIONS:
                div = page.B.DIV(page.B.CLASS("comgroup"))
                for value, label in subset:
                    if self.patient and value in self.HIDDEN_FOR_PATIENT:
                        continue
                    if value not in skip:
                        if not self.patient and value == "com-ext":
                            label = f"{label} (excluding advisory comments)"
                        checked = value in defaults
                        opts = dict(value=value, label=label, checked=checked)
                        div.append(page.checkbox("options", **opts))
                fieldset.append(div)
            fieldset.append(
                page.B.BUTTON(
                    "Show Individual Options",
                    page.B.CLASS("usa-button"),
                    id="show-options",
                    onclick="toggle_alternate_comment_options()",
                    type="button",
                )
            )
            if self.fields.getvalue("accordions"):
                accordion = page.accordion("comment-options")
                accordion.payload.append(fieldset)
                page.form.append(accordion.wrapper)
            else:
                page.form.append(fieldset)

            # Show another set showing the same (sometimes conflicting) info.
            fieldset = page.fieldset("Display Comments and Responses")
            fieldset.set("id", "alternate-comment-options")
            fieldset.set("class", "usa-fieldset hidden")
            fieldset.append(page.B.P("Mark comment types to be displayed."))
            wrapper = page.B.DIV(page.B.CLASS("grid-row grid-gap"))
            for header, options, _ in self.DETAILED_COMMENT_OPTIONS:
                column = page.B.DIV(
                    page.B.DIV(
                        header,
                        page.B.CLASS("subheading")
                    )
                )
                for value, label in options:
                    checked = value in defaults
                    opts = dict(value=value, label=label, checked=checked)
                    column.append(page.checkbox("options", **opts))
                wrapper.append(column)
            fieldset.append(wrapper)
            if self.fields.getvalue("accordions"):
                accordion.payload.append(fieldset)
            else:
                page.form.append(fieldset)

        # Show the miscellaneous options here for HP summaries.
        if self.doc.doctype.name == "Summary" and not self.patient:
            self.show_miscellaneous_options(page, defaults, skip)

        # Add some extra styling and scripting.
        opts = dict(href="/stylesheets/QCReport.css", rel="stylesheet")
        page.head.append(page.B.LINK(**opts))
        page.head.append(page.B.SCRIPT(src="/js/QCReport.js"))
        if self.fields.getvalue("accordions"):
            page.add_css("#submit-button-submit { margin-top: 2.5rem; }")

    def show_miscellaneous_options(self, page, defaults, skip):
        """Ask which parts of the document should be shown.

        This is hoisted out because of a requirement that this block
        of options be shown on a different part of the form depending
        on whether the document is a patient or HP summary. No idea
        why this odd requirement exists, but we handle it.

        Required positional argument:
          page - instance of the HTMLPage class
          defaults - which options are selected by default
          skip - values which should not be included
        """

        fieldset = page.fieldset("Miscellaneous Print Options")
        for value, label in self.MISCELLANEOUS_OPTIONS:
            self.logger.debug("value=%s label=%s", value, label)
            if value not in skip:
                checked = value in defaults
                opts = dict(value=value, label=label, checked=checked)
                self.logger.debug("opts=%s", opts)
                checkbox = page.checkbox("options", **opts)
                if value in self.HIDDEN_OPTIONS:
                    checkbox.set("class", "hidden")
                    checkbox.set("id", "pub-images")
                fieldset.append(checkbox)
        if self.fields.getvalue("accordions"):
            accordion = page.accordion("print-options")
            accordion.payload.append(fieldset)
            page.form.append(accordion.wrapper)
        else:
            page.form.append(fieldset)

        # Let the user choose a version which is less likely to fail.
        fieldset = page.fieldset("911 Options", id="qc-option-fieldset")
        opts = dict(value="qd", label="Run Quick & Dirty report")
        fieldset.append(page.checkbox("options", **opts))
        if self.fields.getvalue("accordions"):
            accordion.payload.append(fieldset)
        else:
            page.form.append(fieldset)

    @cached_property
    def comment_options(self):
        """Filter paramaters controlling comment display."""

        comment_options = SimpleNamespace()
        for label, options, values in self.DETAILED_COMMENT_OPTIONS:
            name = label.split()[0].lower()
            key = ""
            for option in options:
                key += "Y" if option[0] in self.options else "N"
            setattr(comment_options, name, values[key])
        if "com-int" in self.options and "com-perm" in self.options:
            comment_options.external_permanent = "Y"
        else:
            comment_options.external_permanent = "N"
        if "com-ext" in self.options and "com-adv" in self.options:
            comment_options.internal_advisory = "Y"
        else:
            comment_options.internal_advisory = "N"
        return comment_options

    @cached_property
    def doc(self):
        """The document selected for the report.

        As a side effect, alerts are registered here to show the user
        useful information.
        """

        id = self.id
        if not id:
            if not self.fragment:
                if self.request:
                    message = "CDR ID or title is required."
                    self.alerts.append(dict(message=message, type="error"))
                return None
            elif not self.titles:
                message = f"No matches found for {self.fragment!r}."
                self.alerts.append(dict(message=message, type="warning"))
                return None
            elif len(self.titles) > 1:
                message = f"Multiple matches found for {self.fragment!r}."
                self.alerts.append(dict(message=message, type="info"))
                return None
            id = self.titles[0][0]
        opts = dict(id=id)
        if self.version_integer:
            opts["version"] = self.version_integer
        doc = Doc(self.session, **opts)
        doc_id = f"CDR{doc.id}"
        if self.version_integer:
            doc_id = f"{doc_id}V{doc.version}"
        try:
            doctype = doc.doctype.name
            if self.doctype and doctype != self.doctype:
                message = f"CDR{doc.id} is a {doctype} document."
                self.alerts.append(dict(message=message, type="warning"))
                return None
            if doctype != "Media" and doctype not in FILTERS:
                message = f"{doctype} documents are unsupported."
                self.alerts.append(dict(message=message, type="warning"))
                return None
        except Exception:
            message = f"Document {id} not found."
            self.logger.exception(message)
            self.alerts.append(dict(message=message, type="error"))
            return None
        self.logger.info("Loaded %s document %s", doctype, doc_id)
        return doc

    @cached_property
    def doctype(self):
        """Acceptable document types optionally supplied by the user."""
        return self.fields.getvalue("DocType")

    @cached_property
    def filters(self):
        """XSL/T filter used to transform our document."""

        key = self.doc.doctype.name
        self.logger.info("filters(): self.report_type=%r", self.report_type)
        if self.report_type:
            key = f"{key}:{self.report_type}"
            if "qd" in self.options:
                key += "qd"
        self.logger.info("Using %s filters", key)
        return FILTERS.get(key)

    @cached_property
    def fragment(self):
        """Portion of a title used for selecting the report's document."""
        return self.fields.getvalue("DocTitle")

    @cached_property
    def html_page(self):
        """Transformed document for the report."""

        parms = dict(self.parameters)
        try:
            result = self.doc.filter(*self.filters, parms=parms)
        except Exception as e:
            self.logger.exception("Filtering failure")
            return self.bail(f"Filtering failure: {e}")
        page = str(result.result_tree).replace("@@DOCID@@", self.doc.cdr_id)
        for placeholder in self.value_map:
            page = page.replace(placeholder, self.value_map[placeholder])
        return page

    @cached_property
    def id(self):
        """CDR document ID provided by the user."""
        return self.fields.getvalue("DocId")

    @cached_property
    def loglevel(self):
        """If requested, crank up the logging."""

        debug = True if self.fields.getvalue("debug") else False
        if debug:
            environ["CDR_LOGGING_LEVEL"] = "DEBUG"
            return "DEBUG"
        return self.LOGLEVEL

    @cached_property
    def markup_options(self):
        """Filter parameter for which levels of revision markup to apply."""

        markup_options = SimpleNamespace()
        names = [option[0] for option in self.MARKUP_LEVEL_OPTIONS]
        levels = [n.split("-")[1] for n in names if n in self.options]
        markup_options.levels = "|".join(levels)
        names = [option[0] for option in self.MARKUP_BOARD_OPTIONS]
        board_types = []
        for name in names:
            if name in self.options:
                board_type = name.split("-")[1] + "-board"
                board_types.append(board_type)
        if self.patient and not board_types:
            board_types = ["editorial-board"]
        markup_options.boards = "_".join(board_types)
        return markup_options

    @cached_property
    def options(self):
        """Names of options which have been selected by the user."""
        return set(self.fields.getlist("options"))

    @cached_property
    def parameters(self):
        """Parameters passed to the XSL/T filters."""

        parms = [
            ["DisplayGlossaryTermList", self.yn_flags.glossary],
            ["DisplayImages", self.yn_flags.images],
            ["DisplaySummaryRefList", self.yn_flags.summary_refs],
            ["DisplayCitations", self.yn_flags.citations],
            ["DisplayLOETermList", self.yn_flags.loes],
        ]
        if "images" in self.options:
            parms.append([
                "DisplayPubImages",
                self.yn_flags.publishable_images
            ])
        if self.patient:
            parms += [
                ["ShowStandardWording", self.yn_flags.std_wording],
                ["ShowKPBox", self.yn_flags.keypoints],
                ["ShowLearnMoreSection", self.yn_flags.more],
            ]
        if self.markup_options.levels:
            parms.append(["insRevLevels", self.markup_options.levels])
        if self.doctype in ("DrugInformationSummary", "Media"):
            parms.append(["isQC", "Y"])
        if self.doctype == "DrugInformationSummary":
            parms.append(["DisplayComments", "A"])
        if self.doctype == "Summary":
            parms += [
                ["isQC", "Y"],
                ["DisplayComments", self.comment_options.audience],
                ["DurationComments", self.comment_options.duration],
                ["SourceComments", self.comment_options.source],
                ["IncludeExtPerm", self.comment_options.external_permanent],
                ["IncludeIntAdv", self.comment_options.internal_advisory],
                ["DisplayModuleMarkup", self.yn_flags.shade_modules],
                ["DisplaySectMetaData", self.yn_flags.section_metadata],
                ["DisplayQcOnlyMod", self.yn_flags.qc_only],
                ["displayBoard", self.markup_options.boards],
            ]
        if self.doctype and self.doctype.startswith("GlossaryTerm"):
            parms += [
                ["isQC", "Y"],
                ["DisplayComments", self.comment_options.audience],
                ["displayBoard", "editorial-board_"],
                # XXX Unused, as far as I can tall.
                # ["displayAudience", display_audience],
            ]
        if self.doctype == "MiscellaneousDocument":
            parms += [
                ["isQC", "Y"],
                ["insRevLevels", "approved|"],
                ["displayBoard", "editorial-board_"],
            ]
        if self.report_type in ("bu", "but"):
            parms.append(["delRevLevels", "Y"])
        return parms

    @cached_property
    def parameter_set_id(self):
        """Primary key for the row in the url_parm_set table."""

        query = "INSERT INTO url_parm_set (longURL) VALUES (?)"
        self.logger.info("dumping")
        parms = dumps(sorted(self.parameters))
        self.logger.info("dumped")
        self.logger.info("filter parms=%s", parms)
        path = f"dumped-filter-parms-{self.timestamp}.json"
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(parms)
        self.cursor.execute(query, parms)
        self.conn.commit()
        self.cursor.execute("SELECT @@IDENTITY AS id")
        return self.cursor.fetchall()[0].id

    @cached_property
    def patient(self):
        """True if we're handling one of the patient report types."""
        return self.report_type and self.report_type.startswith("pat")

    @cached_property
    def ready(self):
        """True if we have everything we need for the report."""

        self.logger.info("QcReport.py called with %s", self.fields)
        if self.alerts:
            return False
        return True if self.doc and not self.version_needed else False

    @cached_property
    def report_type(self):
        """Optional variant of the QC report.

        The original report only defaulted the report type for patient
        summaries when the user didn't pass the DocType=Summary
        parameter in the URL. That inconsistency seems wrong.
        """

        report_type = self.fields.getvalue("ReportType")
        if report_type:
            return report_type
        doctype = self.doctype or self.doc and self.doc.doctype.name or None
        if not doctype:
            return None
        match doctype:
            case "Media":
                return "img"
            case "MiscellaneousDocument":
                return "rs"
            case "Summary":
                if self.doc:
                    path = "SummaryMetaData/SummaryAudience"
                    if Doc.get_text(self.doc.root.find(path)) == "Patients":
                        return "pat"
        return None

    @cached_property
    def subtitle(self):
        """Title for the form (not used in the report output)."""

        if self.report_type:
            title = self.TITLES_BY_REPORT_TYPE.get(self.report_type)
            return title or self.UNRECOGNIZED_TYPE
        title = self.TITLES_BY_DOCTYPE.get(self.doctype)
        return title or "QC Report"

    @cached_property
    def titles(self):
        """Sequence of (id, title) tuples matching the user's fragment."""

        if not self.fragment:
            return None
        fragment = f"{self.fragment}%"
        query = self.Query("document d", "d.id", "d.title").order("d.title")
        if self.doctype == "GlossaryTermConcept":
            query.join("query_term q", "q.doc_id = d.id")
            query.where(f"q.path LIKE '{self.GTC_DEFINITION_PATHS}'")
            query.where(query.Condition("q.value", fragment, "LIKE"))
        elif self.doctype:
            query.join("doc_type t", "t.id = d.doc_type")
            query.where(query.Condition("t.name", self.doctype))
        if self.doctype != "GlossaryTermConcept":
            query.where(query.Condition("d.title", fragment, "LIKE"))
        query.log()
        return query.execute(self.cursor).fetchall()

    @cached_property
    def value_map(self):
        """Replacements for placeholders in the serialized report."""
        return Substitutions(self).value_map

    @cached_property
    def version(self):
        """Version of the document to use for the report."""

        version = self.fields.getvalue("DocVersion", "").strip()
        if version:
            try:
                version_int = int(version)
                if version_int < 0:
                    self.logger.warning("Version %s (deprecated)")
                return version
            except Exception:
                message = f"Invalid version {version} discarded."
                self.alerts.append(dict(message=message, type="warning"))
                return None

    @cached_property
    def version_integer(self):
        """Integer for the version if integer > 0 else None."""

        if not self.version:
            return None
        version = int(self.version)
        return version if version > 0 else None

    @cached_property
    def version_needed(self):
        """True if we need a version but don't have it yet."""

        if not self.doc or self.version is not None:
            return False
        if self.doctype == "DrugInformationSummary":
            return True
        if self.doctype != "Summary":
            return False
        return self.report_type not in ("pp", "gtnwc")

    @cached_property
    def versions(self):
        """Values for the picklist on the version form."""

        versions = [("0", "Current Working Version")]
        for version in self.doc.list_versions():
            saved = str(version.saved)
            comment = (version.comment or "").strip() or "[No comment]"
            label = f"[V{version.number} {saved[:10]}] {comment[:120]}"
            versions.append((version.number, label))
        return versions

    @cached_property
    def yn_flags(self):
        """Convert Boolean options to "Y" or "N" strings."""

        class Flags:
            def __init__(self, options):
                self.options = options

            def __getattr__(self, name):
                if name == "citations":
                    if "hp-reference" in self.options:
                        return "Y"
                    return "Y" if "pat-cites" in self.options else "N"
                if name not in self.options:
                    name = name.replace("_", "-")
                return "Y" if name in self.options else "N"

        return Flags(self.options)


class Substitutions:
    """Replacements for placeholders added by the filters."""

    MEMBER_PATH = "/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref"
    AUDIENCE_PATH = "/Summary/SummaryMetaData/SummaryAudience"

    def __init__(self, control):
        """Save the caller's argument.

        Pass:
            control - access to the report information and the database
        """

        self.__control = control

    @cached_property
    def board_member_person_id(self):
        """ID of Person document linked with a PDQBoardMemberInfo doc."""

        if not hasattr(self, "_board_member_person_id"):
            self._board_member_person_id = None
            if self.doctype == "PDQBoardMemberInfo":
                path = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
                query = self.control.Query("query_term", "int_val")
                query.where(f"path = '{path}'")
                query.where(query.Condition("doc_id", self.doc.id))
                rows = query.execute(self.control.cursor).fetchall()
                if not rows:
                    self.control.bail("Person document not found")
                self._board_member_person_id = rows[0][0]
        return self._board_member_person_id

    @cached_property
    def control(self):
        """Access to the report information and the database."""
        return self.__control

    @cached_property
    def doc(self):
        """Subject of the QC report."""
        return self.control.doc

    @cached_property
    def doctype(self):
        """String for the document type's name."""
        return self.doc.doctype.name

    @cached_property
    def hp_summaries(self):
        """Are there health professional summaries linking to this document?"""

        if self.doctype not in ("Person", "Organization"):
            return ""
        audience = "Health Professionals"
        return "Yes" if self.links_from_summaries(audience) else "No"

    def links_from_summaries(self, audience):
        """How many summaries for this audience link to our document?

        Pass:
            audience - "Patients" or "Health Professionals"

        Return:
            integer for the number of linking summaries
        """

        query = self.control.Query("query_term p", "COUNT(*) n")
        query.join("query_term a", "a.doc_id = p.doc_id")
        query.where(f"p.path = '{self.MEMBER_PATH}'")
        query.where(f"a.path = '{self.AUDIENCE_PATH}'")
        query.where(query.Condition("p.int_val", self.doc.id))
        query.where(query.Condition("a.value", audience))
        return query.execute(self.control.cursor).fetchall()[0].n

    @cached_property
    def mailer_info(self):
        """Information about the last mailer sent to a person."""

        class MailerInfo:
            def __init__(self):
                self.resp_received = self.change = "N/A"
                self.sent = "No mailers sent for this document"

        info = MailerInfo()
        if self.doctype == "Person":
            query = self.control.Query("query_term", "MAX(doc_id) id")
            query.where("path = '/Mailer/Document/@cdr:ref'")
            query.where(query.Condition("int_val", self.doc.id))
            row = query.execute(self.control.cursor).fetchone()
            query.log()
            if row and row.id:
                mailer_id = row.id
                fields = "s.value s", "r.value r", "c.value c"
                query = self.control.Query("query_term s", *fields)
                query.outer("query_term r", "r.doc_id = s.doc_id",
                            "r.path = '/Mailer/Response/Received'")
                query.outer("query_term c", "c.doc_id = s.doc_id")
                query.where("s.path = '/Mailer/Sent'")
                query.where(query.Condition("s.doc_id", mailer_id))
                rows = query.execute(self.control.cursor).fetchall()
                if rows:
                    row = rows[0]
                    info.sent = row.s
                    if row.r:
                        info.resp_received = row.r
                        if row.c:
                            info.change = row.c
                        else:
                            info.change = "Unable to retrieve change type"
                    else:
                        info.resp_received = "Response not yet received"
                else:
                    info.sent = "Unable to retrieve date mailer was sent"
        return info

    @cached_property
    def org_doc_links(self):
        """Do organization document link to this one?"""

        if self.doctype != "Organization":
            return ""
        query = self.control.Query("query_term", "COUNT(*) AS n")
        query.where("path LIKE '/Organization/%/@cdr:ref'""")
        query.where(query.Condition("int_val", self.doc.id))
        count = query.execute(self.control.cursor).fetchone().n
        return "Yes" if count else "No"

    @cached_property
    def patient_summaries(self):
        """Are there patient summaries linking to this document?"""

        if self.doctype not in ("Person", "Organization"):
            return ""
        return "Yes" if self.links_from_summaries("Patients") else "No"

    @cached_property
    def person_doc_links(self):
        """Do person document link to this one?"""

        if self.doctype != "Organization":
            return ""
        query = self.control.Query("query_term", "COUNT(*) AS n")
        query.where("path LIKE '/Person/%/@cdr:ref'""")
        query.where(query.Condition("int_val", self.doc.id))
        count = query.execute(self.control.cursor).fetchone().n
        return "Yes" if count else "No"

    @cached_property
    def summaries_reviewed(self):
        """List of the summaries reviewed by a PDQ board member."""

        if not self.board_member_person_id:
            return "None"
        fields = "t.value AS title", "a.value AS audience"
        query = self.control.Query("query_term t", *fields).unique()
        query.order("t.value", "a.value")
        query.join("query_term a", "a.doc_id = t.doc_id")
        query.join("query_term m", "m.doc_id = t.doc_id")
        query.join("active_doc d", "d.id = t.doc_id")
        query.join("pub_proc_doc ppd", "ppd.doc_id = t.doc_id")
        query.join("pub_proc p", "p.id = ppd.pub_proc")
        query.where("t.path = '/Summary/SummaryTitle'")
        query.where(f"a.path = '{self.AUDIENCE_PATH}'")
        query.where(f"m.path = '{self.MEMBER_PATH}'")
        query.where(query.Condition("m.int_val", self.board_member_person_id))
        query.where("p.status = 'Success'")
        query.where("p.pub_subset = 'Summary-PDQ Editorial Board'")
        rows = query.execute(self.control.cursor).fetchall()
        if not rows:
            return "None"
        dl = self.control.HTMLPage.B.DL()
        for row in rows:
            summary = f"{row.title}; {row.audience}"
            dl.append(self.control.HTMLPage.B.LI(summary))
        return html.tostring(dl, encoding="unicode", pretty_print=True)

    @cached_property
    def summary_date_sent(self):
        """Date of the last summary mailer for a PDQ board member."""

        if not self.summary_job_id:
            return ""
        query = self.control.Query("pub_proc", "completed")
        query.where(query.Condition("id", self.summary_job_id))
        completed = query.execute(self.control.cursor).fetchone().completed
        return str(completed)[:10]

    @cached_property
    def summary_job_id(self):
        """Last summary mailer job for a PDQ board member."""

        if self.board_member_person_id:
            person_id = self.board_member_person_id
            query = self.control.Query("pub_proc p", "MAX(p.id) AS id")
            query.join("query_term j", "j.int_val = p.id")
            query.join("query_term t", "t.doc_id = j.doc_id")
            query.join("query_term r", "r.doc_id = j.doc_id")
            query.where("j.path = '/Mailer/JobId'")
            query.where("t.path = '/Mailer/Type'")
            query.where("r.path = '/Mailer/Recipient/@cdr:ref'")
            query.where("t.value = 'Summary-PDQ Editorial Board'")
            query.where("p.status = 'Success'")
            query.where(query.Condition("r.int_val", person_id))
            row = query.execute(self.control.cursor).fetchone()
            if row and row.id:
                return str(row.id)
        return ""

    @cached_property
    def summary_mailer_sent(self):
        """Rows for summaries in a board member's last mailer batch."""

        if not self.summary_job_id:
            return ""
        person_id = self.board_member_person_id
        fields = "t.value AS title", "r.value as response"
        query = self.control.Query("query_term t", *fields).order("t.value")
        query.join("query_term d", "d.int_val = t.doc_id")
        query.join("query_term j", "j.doc_id = d.doc_id")
        query.join("query_term p", "p.doc_id = d.doc_id")
        query.outer("query_term r", "r.doc_id = d.doc_id",
                    "r.path = '/Mailer/Response/Received'")
        query.where("t.path = '/Summary/SummaryTitle'")
        query.where("d.path = '/Mailer/Document/@cdr:ref'")
        query.where("j.path = '/Mailer/JobId'")
        query.where("p.path = '/Mailer/Recipient/@cdr:ref'")
        query.where(query.Condition("p.int_val", person_id))
        query.where(query.Condition("j.int_val", self.summary_job_id))
        rows = query.execute(self.control.cursor).fetchall()
        segments = []
        B = self.control.HTMLPage.B
        for row in rows:
            tr = B.TR(B.TD(B.B("Summary")), B.TD(row.title))
            segments.append(html.tostring(tr, encoding="unicode"))
            value = row.response or "Not Received"
            tr = B.TR(B.TD(B.B("Date Response Received")), B.TD(value))
            segments.append(html.tostring(tr, encoding="unicode"))
        return "\n".join(segments)

    @cached_property
    def value_map(self):
        """Everything which needs to be replaced in the document."""

        return {
            "@@ACTIVE_APPR0VED_TEMPORARILY_CLOSED_PROTOCOLS@@": "No",
            "@@CLOSED_COMPLETED_PROTOCOLS@@": "No",
            "@@CTGOV_PROTOCOLS@@": "No",
            "@@HEALTH_PROFESSIONAL_SUMMARIES@@": self.hp_summaries,
            "@@IN_EXTERNAL_MAP_TABLE@@": "No",
            "@@MAILER_DATE_SENT@@": self.mailer_info.sent,
            "@@MAILER_RESPONSE_RECEIVED@@": self.mailer_info.resp_received,
            "@@MAILER_TYPE_OF_CHANGE@@": self.mailer_info.change,
            "@@ORG_DOC_LINKS@@": self.org_doc_links,
            "@@PATIENT_SUMMARIES@@": self.patient_summaries,
            "@@PERSON_DOC_LINKS@@": self.person_doc_links,
            "@@SESSION@@": self.control.session.name,
            "@@SUMMARIES_REVIEWED@@": self.summaries_reviewed,
            "@@SUMMARY_DATE_SENT@@": self.summary_date_sent or "N/A",
            "@@SUMMARY_JOB_ID@@": self.summary_job_id or "N/A",
            "@@SUMMARY_MAILER_SENT@@": self.summary_mailer_sent,
        }


if __name__ == "__main__":
    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("Failed")
        control.bail(e)
