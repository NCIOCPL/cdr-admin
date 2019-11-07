#!/usr/bin/env python

"""Prepare a document for comprehensive review.
"""

from cdrcgi import Controller, DOCID, sendPage, navigateTo
from cdr import FILTERS
from cdrapi.docs import Doc
from lxml import html

class Control(Controller):

    SUBTITLE = "QC Report"
    LOGNAME = "QCReport"
    SECTION_TITLES = dict(
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
        gtnwc="Glossary Term Name With Concept Report"
    )
    UNRECOGNIZED_TYPE = "QC Report (Unrecognized Type)"
    CURRENT_WORKING_VERSION = "Current Working Version"

    def run(self):
        """Override so we can optionally record the parameters."""

        self.logger.debug("parameters: %s", dict(self.fields))
        if self.report_type == "pp" and self.id:
            opts = dict(ReportType="pp", DocId=self.id)
            if self.doctype == "Summary":
                opts["Version"] = "cwd"
            return navigateTo("PublishPreview.py", self.session.name, **opts)
        Controller.run(self)

    def populate_form(self, page):
        """If we need more information, ask for it.

        Pass:
            page - HTMLPage on which we request values we need
        """

        # If we have a document, we're done asking for information.
        if self.doc:
            return self.show_report()

        # Remember information we already have.
        page.form.append(page.hidden_field("DocType", self.doctype))
        page.form.append(page.hidden_field("ReportType", self.report_type))
        if self.loglevel == "DEBUG":
            page.form.append(page.hidden_field("debug", True))

        # If we need a version and possibly other parameters, ask for them.
        if self.id:
            page.form.append(page.hidden_field(DOCID, self.id))
            page.form.append(self.version_fieldset)
            self.__add_markup_options(page)
            self.__add_comment_options(page)
            self.__add_section_options(page)
            self.__add_911_options(page)

        # If we have candidate documents from a fragment, let's pick one.
        elif self.matches:
            max_length = 0
            fieldset = page.fieldset("Select One Of The Matching Documents")
            for id, title in self.matches:
                if self.doctype != "GlossaryTermConcept":
                    title = f"[CDR{id:010d}] {title}"
                if len(title) > 150:
                    title = title[:150] + "..."
                max_length = max(max_length, len(title))
                opts = dict(value=id, label=title)
                fieldset.append(page.radio_button(DOCID, **opts))
            page.form.append(fieldset)
            if max_length > 55:
                page.add_css(f"fieldset {{ width: {max_length * 9}px; }}")

        # Put up the initial form asking for document identification.
        else:
            label = "Title"
            fragment = "Title Fragment"
            if self.doctype == "GlossaryTermConcept":
                fragment = "Definition Fragment"
                label = "Definition"
            fieldset = page.fieldset(f"Enter Document ID or {fragment}")
            if not self.doctype:
                fieldset.append(page.select("DocType", options=self.doctypes))
            fieldset.append(page.text_field(DOCID, label="CDR ID"))
            fieldset.append(page.text_field("fragment", label=label))
            page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src="/js/QcReport.js"))

    def show_report(self):
        """Override the base class here, as this is not a tabular report."""

        if not self.doc:
            self.show_form()
        if self.doctype == "Summary":
            self.__reroute_summary()
        result = self.doc.filter(*self.filters, parms=self.filter_parameters)
        page = str(result.result_tree)
        for placeholder in self.value_map:
            page = page.replace(placeholder, self.value_map[placeholder])
        sendPage(page)

    @property
    def doc(self):
        """`Doc` object for the report, if we have all the info we need."""

        if not self.id or self.version is None and self.version_required:
            return None
        if not hasattr(self, "_doc"):
            self._doc = Doc(self.session, id=self.id, version=self.version)
            if self._doc.doctype.name != self.doctype:
                args = self._doc.cdr_id, self._doc.doctype
                self.bail("{} is a {} document".format(*args))
        return self._doc

    @property
    def doctype(self):
        """String for the name of the CDR document type."""

        if not hasattr(self, "_doctype"):
            self._doctype = self.fields.getvalue("DocType")
            if self._doctype and ":" in self._doctype:
                self._doctype = self._doctype.split(":")[0]
            if not self._doctype and self.id:
                doc = Doc(self.session, id=self.id)
                self._doctype = doc.doctype.name
        return self._doctype

    @property
    def doctypes(self):
        """Strings for the document types for which we can make QC reports."""

        if not hasattr(self, "_doctypes"):
            doctypes = [key.split(":")[0] for key in FILTERS]
            self._doctypes = sorted(set(doctypes))
        return self._doctypes

    @property
    def filter_key(self):
        """String used to select the correct XSL/T filters."""

        if not self.doctype:
            return None
        if not hasattr(self, "_filter_key"):
            self._filter_key = self.doctype
            if self.report_type:
                self._filter_key += f":{self.report_type}"
            if "qd" in self.options:
                self._filter_key += "qd"
            if ":" not in self._filter_key:
                if self.doctype == "Media":
                    self._filter_key += ":img"
                if self.doctype == "MiscellaneousDocument":
                    self._filter_key += ":rs"
        return self._filter_key

    @property
    def filter_parameters(self):
        """Settings used to control the behavior of XSL/T processing."""

        if not hasattr(self, "_filter_parameters"):
            self._filter_parameters = FilterParameters(self).values
        return self._filter_parameters

    @property
    def filters(self):
        """Set of transformation scripts for creating the QC report."""
        return FILTERS[self.filter_key]

    @property
    def fragment(self):
        """String for matching a document title or definition fragment."""

        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("fragment", "").strip()
        return self._fragment

    @property
    def id(self):
        """Integer for the CDR ID of the document to process."""

        if not hasattr(self, "_id"):
            self._id = None
            value = self.fields.getvalue(DOCID, "").strip()
            if value:
                try:
                    self._id = Doc.extract_id(value)
                except:
                    self.bail(f"Invalid id {value}")
            elif len(self.matches) == 1:
                self._id = self.matches[0][0]
        return self._id

    @property
    def loglevel(self):
        """Let the amount of logging be controlled by the URL."""

        if self.fields.getvalue("debug"):
            environ["CDR_LOGGING_LEVEL"] = "DEBUG"
            return "DEBUG"
        return self.LOGLEVEL

    @property
    def matches(self):
        """Documents which match the user's title or definition fragment."""

        if not hasattr(self, "_matches"):
            self._matches = []
            if self.fragment:
                query = self.Query("document d", "d.id", "d.title").order(2)
                if self.doctype == "GlossaryTermConcept":
                    fragment = f"%{self.fragment}%"
                    query.join("query_term c", "c.doc_id = d.id")
                    query.where("c.path LIKE '/Gloss%Concept%DefinitionText'")
                    query.where(query.Condition("c.value", fragment, "LIKE"))
                else:
                    fragment = f"{self.fragment}%"
                    query.join("doc_type t", "t.id = d.doc_type")
                    query.where(query.Condition("t.name", self.doctype))
                    query.where(query.Condition("d.title", fragment, "LIKE"))
                rows = query.execute(self.cursor).fetchall()
                self._matches = [tuple(row) for row in rows]
                if not self._matches:
                    self.bail(f"No documents match {self.fragment}")
        return self._matches

    @property
    def method(self):
        """Make all the requests carry parameters in the URL."""
        return "get"

    @property
    def options(self):
        """Miscellaneous options (e.g., "qd")."""
        return self.fields.getlist("options")

    @property
    def params(self):
        """The parameters submitted for this job."""
        return self.fields.getvalue("paramset") or "0"

    @property
    def report_type(self):
        """Code for the variant needed for some of the QC reports."""

        if not hasattr(self, "_report_type"):
            self._report_type = self.fields.getvalue("ReportType", "")
            if not self._report_type:
                doctype = self.fields.getvalue("DocType")
                if doctype and ":" in doctype:
                    self._report_type = doctype.split(":", 1)[1]
            if not self._report_type and self.doc is not None:
                node = self.doc.root.find("SummaryMetaData/SummaryAudience")
                if node is not None and node.text == "Patients":
                    self._report_type = "pat"
        return self._report_type

    @property
    def subtitle(self):
        """String to be displayed immediately below the main banner."""

        if self.report_type:
            default = self.UNRECOGNIZED_TYPE
            return self.SECTION_TITLES.get(self.report_type, default)
        return self.SUBTITLE

    @property
    def value_map(self):
        """Replacements for placeholders in the serialized report."""

        if not hasattr(self, "_value_map"):
            substitutions = Substitutions(self)
            self._value_map = substitutions.value_map
        return self._value_map

    @property
    def version(self):
        """Version of the document to use for the report.

        None means no version has been selected. An empty string
        means the current working document has been chosen.
        """

        version = self.fields.getvalue("DocVersion")
        if version in ("-1", self.CURRENT_WORKING_VERSION):
            return ""
        return version

    @property
    def version_fieldset(self):
        """Assemble a picklist of the versions of the selected document."""

        versions = [self.CURRENT_WORKING_VERSION]
        fields = "num", "comment", "dt"
        query = self.Query("doc_version", *fields).order("num DESC")
        query.where(query.Condition("id", self.id))
        for row in query.execute(self.cursor).fetchall():
            comment = row.comment or "[No comment]"
            label = f"[V{row.num} {str(row.dt)[:10]}] {comment}"
            versions.append((row.num, label))
        fieldset = self.HTMLPage.fieldset("Select Document Version")
        opts = dict(label="Version", options=versions, default="")
        fieldset.append(self.HTMLPage.select("DocVersion", **opts))
        return fieldset

    @property
    def version_required(self):
        """Some flavors of the report need a version, some don't."""

        if self.doctype == "DrugInformationSummary":
            return True
        if self.doctype == "Summary":
            if self.report_type and self.report_type not in ("pp", "gtnwc"):
                return True
        return False

    def __add_911_options(self, page):
        """Let the user bypass checks which might cause the report to fail."""

        if self.doctype == "Summary":
            fieldset = page.fieldset("911 Options")
            opts = dict(value="qd", label="Run Quick & Dirty Report")
            fieldset.append(page.checkbox("options", **opts))
            page.form.append(fieldset)

    def __add_comment_options(self, page):
        """Determine which comments are to be displayed."""

        if self.doctype == "Summary":
            fieldset = page.fieldset("Choose Comments To Be Displayed")
            options = (
                ("internal", "Internal", "P"),
                ("external", "External", "H"),
                ("advisory", "Advisory Board", "P"),
                ("editorial", "Non-Advisory Board", "PH"),
                ("permanent", "Permanent", "H"),
                ("ephemeral", "Non-Permanent", "PH"),
                ("external-permanent", "Permanent External", ""),
                ("internal-advisory", "Internal Advisory", ""),
            )
            type_key = "P" if self.report_type.startswith("pat") else "H"
            for value, label, types in options:
                checked = type_key in types
                label = f"Include {label} Comments"
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.checkbox("comment", **opts))
            page.form.append(fieldset)

    def __add_markup_options(self, page):
        """Add checkboxes for how to display insertion/deletion markup."""

        if self.doctype == "Summary":
            if not self.report_type.startswith("pat"):
                fieldset = page.fieldset("Markup Filtering By Board")
                checked = True
                for board_type in ("editorial", "advisory"):
                    label = f"{board_type.title()} Board Markup"
                    opts = dict(value=board_type, checked=checked, label=label)
                    fieldset.append(page.checkbox("markup-board", **opts))
                    checked = False
                page.form.append(fieldset)
        types = "Summary", "DrugInformationSummary", "GlossaryTermName"
        if self.doctype in types:
            fieldset = self.HTMLPage.fieldset("Markup Filtering By Level")
            for level in ("publish", "approved", "proposed"):
                checked = level == "approved"
                label = f"{level.title()} Markup Level"
                opts = dict(value=level, checked=checked, label=label)
                fieldset.append(page.checkbox("markup-level", **opts))
            page.form.append(fieldset)

    def __add_section_options(self, page):
        """Add choices for which sections to display."""

        if self.doctype != "Summary":
            return
        common = (
            ("Glossary Terms At End of Report", "Glossaries"),
            ("Images", "Images"),
            ("Module Markup", "ModuleMarkup"),
        )
        patient = (
            ("Key Point Boxes", "Keypoints"),
            ("Reference Section", "CitationsPat"),
            ("Standard Wording With Mark-Up", "StandardWording"),
            ("To Learn More Section", "LearnMore"),
        )
        hp = (
            ("HP Reference Section", "CitationsHP"),
            ("Level of Evidence Terms", "LOEs"),
        )
        defaults = {"CitationsHP", "CitationsPat", "Keypoints", "LearnMore"}
        if self.report_type.startswith("pat"):
            sections = common + patient
        else:
            sections = common + hp
        fieldset = page.fieldset("Choose Sections To Include")
        for label, value in sorted(sections):
            checked = value in defaults
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("section", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Choose Image Versions")
        fieldset.set("class", "hidden")
        fieldset.set("id", "image-versions-fieldset")
        checked = True
        for value in ("publishable", "unpublishable"):
            label = f"Use {value.title()} Versions"
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("image-versions", **opts))
            checked = False
        page.form.append(fieldset)

    def __reroute_summary(self):
        """Make the summary usable by Microsoft Word.

        Note that the use of the name `docType` is bogus here, as we
        are instead passing the value of the key into the dictionary
        of filters.  This is regrettably caused by the need to preserve
        the behavior of legacy code which depends on this ruse.
        """

        opts = dict(
            parms=f"parmid={self.__save_parms()}",
            docId=self.doc.cdr_id,
            docType=self.filter_key,
            docVer=self.version or "",
        )
        return sendPage(None, **opts)

    def __save_parms(self):
        """Save the params in the database to work around URL limitations."""

        insert = "INSERT INTO url_parm_set (longURL) VALUES (?)"
        self.cursor.execute(insert, repr(self.filter_parameters))
        self.conn.commit()
        self.cursor.execute("SELECT @@IDENTITY")
        return self.cursor.fetchone()[0]


class FilterParameters:
    """Settings used to control the behavior of XSL/T processing."""

    def __init__(self, control):
        """Save a the caller's values.

        Pass:
            control - access to the form's field values
        """

        self.__control = control

    @property
    def audience(self):
        """Which audience(s) to use for glossary term name reports."""
        return "_".join(self.fields.getlist("audience"))

    @property
    def citations(self):
        """Should the references be displayed?"""
        for value in ("CitationsHP", "CitationsPat"):
            if value in self.section_options:
                return "Y"
        return "N"

    @property
    def comment_audience(self):
        """Code indicating which audience comments are to be displayed."""

        if "internal" in self.comment_options:
            if "external" in self.comment_options:
                return "A"
            return "I"
        elif "external" in self.comment_options:
            return "E"
        return "N"

    @property
    def comment_duration(self):
        """Selection of permanent/ephemeral comments."""

        if "permanent" in self.comment_options:
            if "ephemeral" in self.comment_options:
                return "A"
            return "P"
        elif "ephemeral" in self.comment_options:
            return "R"
        return "N"

    @property
    def comment_external_permanent(self):
        """Custom combination option for comment selection."""
        return "Y" if "external-permanent" in self.comment_options else "N"

    @property
    def comment_internal_advisory(self):
        """Custom combination option for comment selection."""
        return "Y" if "internal-advisory" in self.comment_options else "N"

    @property
    def comment_options(self):
        """Options selected from the form for which comments to include."""

        if not hasattr(self, "_comment_options"):
            self._comment_options = self.fields.getlist("comment")
        return self._comment_options

    @property
    def comment_source(self):
        """Selection of comments by source."""

        if "advisory" in self.comment_options:
            if "editorial" in self.comment_options:
                return "A"
            return "V"
        if "editorial" in self.comment_options:
            return "E"
        return "N"

    @property
    def doctype(self):
        """String for the name of the CDR document type."""
        return self.__control.doctype

    @property
    def fields(self):
        """The values selected for the report at run time."""
        return self.__control.fields

    @property
    def glossary(self):
        """Include glossary terms in summary QC report?"""
        return "Y" if "Glossaries" in self.section_options else "N"

    @property
    def images(self):
        """Include images terms in summary QC report?"""
        return "Y" if "Images" in self.section_options else "N"

    @property
    def images_publishable(self):
        """'Y' if publishable versions of images are required, else 'N'."""

        image_versions = self.fields.getvalue("image-versions")
        return "N" if image_versions == "unpublishable" else "Y"

    @property
    def key_points(self):
        """Whether to include key points."""
        return "Y" if "Keypoints" in self.section_options else "N"

    @property
    def learn_more(self):
        """Whether to include the 'Learn more about ...' section."""
        return "Y" if "LearnMore" in self.section_options else "N"

    @property
    def loe(self):
        """Should the levels of evidence be displayed?"""
        return "Y" if "LOEs" in self.section_options else "N"

    @property
    def markup_boards(self):
        """Markup control by board type."""

        boards = set()
        board_types = self.fields.getlist("markup-board")
        for board_type in ("editorial", "advisory"):
            if board_type in board_types:
                boards.add(f"{board_type}-board")
        if self.doctype == "Summary" and self.report_type.startswith("pat"):
            boards.add("editorial-board")
        return "_".join(boards)

    @property
    def markup_levels(self):
        """Which Insertion/Deletion levels to include."""

        if not hasattr(self, "_markup_levels"):
            levels = self.fields.getvalue("insRevLevels")
            if levels:
                markup_levels = set(levels.strip("|").split("|"))
            else:
                markup_levels = set(self.fields.getlist("markup-level"))
            if self.doctype == "MiscellaneousDocument":
                markup_levels.add("approved")
            self._markup_levels = "|".join(markup_levels)
        return self._markup_levels

    @property
    def markup_module(self):
        """Whether to include markup in modules."""
        return "Y" if "ModuleMarkup" in self.section_options else "N"

    @property
    def report_type(self):
        """Code for the variant needed for some of the QC reports."""
        return self.__control.report_type

    @property
    def section_options(self):
        """Options selected from the form for which sections to include."""

        if not hasattr(self, "_section_options"):
            self._section_options = self.fields.getlist("section")
        return self._section_options

    @property
    def standard_wording(self):
        """Whether to include the standard wording section."""
        return "Y" if "StandardWording" in self.section_options else "N"

    @property
    def values(self):
        parms = {}
        if self.markup_levels:
            parms["insRevLevels"] = self.markup_levels
        if self.doctype in ("DrugInformationSummary", "Media"):
            parms["isQC"] = "Y"
        if self.doctype == "DrugInformationSummary":
            parms["DisplayComments"] = "A"
        if self.doctype == "Summary":
            parms["DisplayComments"] = self.comment_audience
            parms["DurationComments"] = self.comment_duration
            parms["SourceComments"] = self.comment_source
            parms["IncludeExtPerm"] = self.comment_external_permanent
            parms["IncludeIntAdv"] = self.comment_internal_advisory
            parms["DisplayModuleMarkup"] = self.markup_module
            parms["displayBoard"] = self.markup_boards
        if self.doctype == "GlossaryTermName":
            parms["DisplayComments"] = self.comment_audience
            parms["displayBoard"] = "editorial-board"
            parms["displayAudience"] = self.audience
        if self.doctype == "MiscellaneousDocument":
            parms["insRevLevels"] = "approved"
            parms["displayBoard"] = "editorial_board"
        if self.report_type in ("bu", "but"):
            parms["delRevLevels"] = "Y"
        parms["DisplayGlossaryTermList"] = self.glossary
        parms["DisplayImages"] = self.images
        if self.images == "Y":
            parms["DisplayPubImages"] = self.images_publishable
        parms["DisplayCitations"] = self.citations
        parms["DisplayLOETermList"] = self.loe
        if self.report_type.startswith("pat"):
            parms["ShowStandardWording"] = self.standard_wording
            parms["ShowKPBox"] = self.key_points
            parms["ShowLearnMoreSection"] = self.learn_more
        return parms


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

    @property
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

    @property
    def control(self):
        """Access to the report information and the database."""
        return self.__control

    @property
    def doc(self):
        """Subject of the QC report."""
        return self.control.doc

    @property
    def doctype(self):
        """String for the document type's name."""
        return self.doc.doctype.name

    @property
    def hp_summaries(self):
        "Are there health professional summaries linking to this document?"""

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

    @property
    def mailer_info(self):
        """Information about the last mailer sent to a person."""

        if not hasattr(self, "_mailer_info"):
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
                    row = query.execute(self.control.cursor).fetchall()
                    if row:
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
            self._mailer_info = info
        return self._mailer_info

    @property
    def org_doc_links(self):
        """Do organization document link to this one?"""

        if self.doctype != "Organization":
            return ""
        query = self.control.Query("query_term", "COUNT(*) AS n")
        query.where("path LIKE '/Organization/%/@cdr:ref'""")
        query.where(query.Condition("int_val", self.doc.id))
        count = query.execute(self.control.cursor).fetchone().n
        return "Yes" if count else "No"

    @property
    def patient_summaries(self):
        "Are there patient summaries linking to this document?"""

        if self.doctype not in ("Person", "Organization"):
            return ""
        return "Yes" if self.links_from_summaries("Patients") else "No"

    @property
    def person_doc_links(self):
        """Do person document link to this one?"""

        if self.doctype != "Organization":
            return ""
        query = self.control.Query("query_term", "COUNT(*) AS n")
        query.where("path LIKE '/Person/%/@cdr:ref'""")
        query.where(query.Condition("int_val", self.doc.id))
        count = query.execute(self.control.cursor).fetchone().n
        return "Yes" if count else "No"

    @property
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

    @property
    def summary_date_sent(self):
        """Date of the last summary mailer for a PDQ board member."""

        if not self.summary_job_id:
            return ""
        query = self.control.Query("pub_proc", "completed")
        query.where(query.Condition("id", self.summary_job_id))
        completed = query.execute(self.control.cursor).fetchone().completed
        return str(completed)[:10]

    @property
    def summary_job_id(self):
        """Last summary mailer job for a PDQ board member."""

        if not hasattr(self, "_summary_job_id"):
            self._summary_job_id = ""
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
                    self._summary_job_id = str(row.id)
        return self._summary_job_id

    @property
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

    @property
    def value_map(self):
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
    """Don't run the script if loaded as a module."""
    Control().run()
