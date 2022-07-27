#!/usr/bin/env python

"""Report on management of PDQ media permissions.

JIRA::OCECDR-3704
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Media Permissions Report"
    REQUESTS = "Requests"
    APPROVALS = "Permissions"
    DENIALS = "Denials"
    SELECTION_METHODS = (
        ("global", "Global version of the report", True),
        ("specific", "Specific document selection", False),
    )
    GLOBAL_CHOICES = (
        ("en", "Permission Requested (English)", True),
        ("es", "Permission Requested (Spanish)", True),
        (
            "denied",
            "Show All Denied Permission Requested (English and Spanish)",
            False,
        ),
    )
    SPECIFIC_CHOICES = (
        ("doctype", "Choose Document Type"),
        ("summary", "Select Summary Language and Board"),
        ("docid", "Enter the CDR ID of a certain summary or glossary term"),
    )
    DOCTYPE_CHOICES = (
        ("summary", "Summaries", False),
        ("glossary", "Glossary Terms", False),
        ("both", "Both Summaries and Glossary Terms", True),
    )
    REQUEST_LEGEND = "Optional Date Range for Permission Request"
    EXPIRATION_LEGEND = "Optional Date Range for Permission Expiration"
    SCRIPT = "../../js/MediaPermissionsReport.js"
    COLUMNS = {
        REQUESTS: (
            ("Media DocTitle", 300),
            ("Permission Request Date", 100),
            ("Permission Response (Response Date)", 200),
            ("Expiration", 100),
            ("Spanish Permission Requested (Permission Response)", 200),
            ("Approved Use", 300),
            ("Comment", 150),
        ),
        APPROVALS: (
            ("Approved Use", 300),
            ("Media DocTitle", 300),
            ("Permission Request Date", 100),
            ("Permission Granted Date", 100),
            ("Expiration", 100),
            ("Spanish Permission Requested (Permission Response)", 150),
            ("Comment", 150),
        ),
        DENIALS: (
            ("Media DocTitle", 300),
            ("Permission Request Date", 100),
            ("Permission Response (Response Date)", 200),
            ("Spanish Permission Requested (Permission Response)", 200),
            ("Comment", 200),
        ),
    }
    RESPONSE_PATHS = (
        "/Media/PermissionInformation/PermissionResponse",
        "/Media/PermissionInformation/SpanishTranslationPermissionResponse",
    )
    USAGE_PATHS = dict(
        glossary="/Media/PermissionInformation/ApprovedUse/Glossary/@cdr:ref",
        summary="/Media/PermissionInformation/ApprovedUse/Summary/@cdr:ref",
    )

    def build_tables(self):
        """Assemble the report table which matches the user's selections."""

        opts = dict(
            caption=self.caption,
            columns=self.columns,
            sheet_name=self.report_type,
        )
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Add the fields to the report request form.

        Pass:
            page - HTMLPage object on which to place the fields
        """

        fieldset = page.fieldset("Selection Method")
        for value, label, checked in self.SELECTION_METHODS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("selection_method", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Global Selections", id="global-block")
        for value, label, checked in self.GLOBAL_CHOICES:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("global", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Specific Selections", id="specific-block")
        for value, label in self.SPECIFIC_CHOICES:
            opts = dict(value=value, label=label)
            fieldset.append(page.radio_button("specific", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Document Type(s)", id="doctype-block")
        for value, label, checked in self.DOCTYPE_CHOICES:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("doctype", **opts))
        page.form.append(fieldset)
        self.add_board_fieldset(page)
        self.add_language_fieldset(page)
        fieldset = page.fieldset("CDR Document ID", id="id-block")
        fieldset.append(page.text_field("docid", label="CDR ID"))
        page.form.append(fieldset)
        fieldset = page.fieldset(self.REQUEST_LEGEND)
        fieldset.append(page.date_field("req_start", label="Start Date"))
        fieldset.append(page.date_field("req_end", label="End Date"))
        page.form.append(fieldset)
        fieldset = page.fieldset(self.EXPIRATION_LEGEND)
        fieldset.append(page.date_field("exp_start", label="Start Date"))
        fieldset.append(page.date_field("exp_end", label="End Date"))
        page.form.append(fieldset)
        page.add_output_options("html")
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    @property
    def board(self):
        """PDQ board(s) selected for the report."""

        if not hasattr(self, "_board"):
            self._board = None
            if self._specific_method == "summary":
                self._board = []
                boards = self.fields.getlist("board")
                if "all" not in boards:
                    for id in boards:
                        if not id.isdigit():
                            self.bail()
                        id = int(id)
                        if id not in self.boards:
                            self.bail()
                        self._board.append(id)
        return self._board

    @property
    def boards(self):
        """Dictionary of boards used for parameter validation."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def caption(self):
        """String to be displayed at the top of the report table."""

        if not hasattr(self, "_caption"):
            if self.report_type == self.DENIALS:
                self._caption = "Media Permission Denials"
            elif self.report_type == self.REQUESTS:
                languages = dict(en="English", es="Spanish")
                languages = [languages[key] for key in self.global_selections]
                languages = " and ".join(languages)
                self._caption = f"{languages} Permission Requests"
            elif self.doc_id:
                self._caption = f"Media Approved For Use With CDR{self.doc_id}"
            elif self.doctype:
                doctype = dict(
                    both="Summaries and Glossary Terms",
                    summary="Summaries",
                    glossary="Glossary Terms",
                )[self.doctype]
                self._caption = f"Media Approved For Use With {doctype}"
            else:
                self._caption = f"Media Approved For Use With {self.language} "
                if not self.board:
                    self._caption = f"{self._caption} Summaries"
                else:
                    boards = [self.boards[id] for id in self.board]
                    if len(boards) < 3:
                        boards = " and ".join(boards)
                    else:
                        first = ", ".join(boards[:-1])
                        boards = f"{first}, and {boards[-1]}"
                    self._caption = f"{self._caption} {boards} Summaries"
        return self._caption

    @property
    def columns(self):
        """Strings for the top of the report's table columns."""

        if not hasattr(self, "_columns"):
            self._columns = []
            for label, width in self.COLUMNS[self.report_type]:
                column = self.Reporter.Column(label, width=f"{width:d}px")
                self._columns.append(column)
        return self._columns

    @property
    def denials(self):
        """Rows for the report table on permission denials."""

        if not hasattr(self, "_denials"):
            query = self.Query("query_term", "doc_id").unique()
            query.where(query.Condition("path", self.RESPONSE_PATHS, "IN"))
            query.where(query.Condition("value", "Permission Denied"))
            rows = query.execute(self.cursor).fetchall()
            docs = [Media(self, row.doc_id) for row in rows]
            self._denials = []
            for doc in sorted(docs):
                if doc.in_scope:
                    self._denials.append((
                        doc.title,
                        doc.request_date,
                        doc.english_response,
                        doc.spanish_request,
                        doc.comments,
                    ))
        return self._denials

    @property
    def doc_id(self):
        """Integer for CDR document selected for the report."""

        if not hasattr(self, "_doc_id"):
            self._doc_id = None
            if self.specific_method == "docid":
                self._doc_id = self.fields.getvalue("docid")
                if self._doc_id:
                    if not self._doc_id.isdigit():
                        self.bail()
                    self._doc_id = int(self._doc_id)
        return self._doc_id

    @property
    def doctype(self):
        """One of summary, glossary, or both."""

        if not hasattr(self, "_doctype"):
            self._doctype = None
            if self.specific_method == "doctype":
                valid = [choice[0] for choice in self.DOCTYPE_CHOICES]
                self._doctype = self.fields.getvalue("doctype", valid[0])
                if self._doctype not in valid:
                    self.bail()
        return self._doctype

    @property
    def exp_end(self):
        """End of the date range for restricting by permission expiration."""

        if not hasattr(self, "_exp_end"):
            value = self.fields.getvalue("exp_end")
            try:
                self._exp_end = self.parse_date(value)
                if self._exp_end:
                    self._exp_end = f"{self._exp_end} 23:59:59"
            except Exception:
                self.logger.exception("parsing exp_end")
                self.bail("Invalid expiration end date")
        return self._exp_end

    @property
    def exp_start(self):
        """Start of the date range for restricting by permission expiration."""

        if not hasattr(self, "_exp_start"):
            value = self.fields.getvalue("exp_start")
            try:
                self._exp_start = self.parse_date(value)
                if self._exp_start:
                    self._exp_start = str(self._exp_start)
            except Exception:
                self.logger.exception("parsing exp_start")
                self.bail("Invalid expiration start date")
        return self._exp_start

    @property
    def global_selections(self):
        """Selection(s) made for reporting on requests or denials."""

        if not hasattr(self, "_global_selections"):
            self._global_selections = None
            name = self.selection_method
            if name == "global":
                valid = [choice[0] for choice in self.GLOBAL_CHOICES]
                self._global_selections = self.fields.getlist(name) or valid[0]
                if set(self._global_selections) - set(valid):
                    self.bail()
                elif "denied" in self._global_selections:
                    if len(self._global_selections) > 1:
                        self.bail("Can't combine 'denied' with other options")
        return self._global_selections

    @property
    def language(self):
        """English or Spanish (used when selecting summaries by PDQ board."""

        if not hasattr(self, "_language"):
            self._language = None
            if self._specific_method == "summary":
                self._language = self.fields.getvalue("language", "English")
                if self._language not in self.LANGUAGES:
                    self.bail()
        return self._language

    @property
    def media_by_docid(self):
        """Sequence of IDs for media used by a one summary or glossary term."""

        if not hasattr(self, "_media_by_docid"):
            paths = list(self.USAGE_PATHS.values())
            query = self.Query("query_term", "doc_id").unique()
            query.where(query.Condition("path", paths, "IN"))
            query.where(query.Condition("int_val", self.doc_id))
            rows = query.execute(self.cursor).fetchall()
            self._media_by_docid = [row.doc_id for row in rows]
        return self._media_by_docid

    @property
    def media_by_doctype(self):
        """Sequence of IDs for media used by docs of the selected type(s)."""

        if not hasattr(self, "_media_by_doctype"):
            query = self.Query("query_term", "doc_id").unique()
            if self.doctype == "both":
                paths = list(self.USAGE_PATHS.values())
                query.where(query.Condition("path", paths, "IN"))
            else:
                path = self.USAGE_PATHS[self.doctype]
                query.where(query.Condition("path", path))
            rows = query.execute(self.cursor).fetchall()
            self._media_by_doctype = [row.doc_id for row in rows]
        return self._media_by_doctype

    @property
    def media_by_summary(self):
        """Sequence of IDs for media used by selected PDQ summaries."""

        if not hasattr(self, "_media_by_summary"):
            m_path = self.USAGE_PATHS["summary"]
            l_path = "/Summary/SummaryMetaData/SummaryLanguage"
            b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
            t_path = "/Summary/TranslationOf/@cdr:ref"
            query = self.Query("query_term m", "m.doc_id").unique()
            query.where(query.Condition("m.path", m_path))
            query.join("query_term l", "l.doc_id = m.int_val")
            query.where(query.Condition("l.path", l_path))
            query.where(query.Condition("l.value", self.language))
            if self.board:
                if self.language == "English":
                    query.join("query_term b", "b.doc_id = l.doc_id")
                else:
                    query.join("query_term t", "t.doc_id = l.doc_id")
                    query.join("query_term b", "b.doc_id = t.int_val")
                    query.where(query.Condition("t.path", t_path))
                query.where(query.Condition("b.path", b_path))
                query.where(query.Condition("b.int_val", self.board, "IN"))
            rows = query.execute(self.cursor).fetchall()
            self._media_by_summary = [row.doc_id for row in rows]
        return self._media_by_summary

    @property
    def permissions(self):
        """Rows for the report table on granted permissions."""

        if not hasattr(self, "_permissions"):
            self._permissions = []
            Cell = self.Reporter.Cell
            ids = getattr(self, f"media_by_{self.specific_method}")
            docs = [Media(self, id) for id in ids]
            values = []
            for doc in docs:
                if doc.in_scope:
                    title_key = doc.title.lower()
                    for approval in doc.approvals:
                        approval = str(approval)
                        key = approval.lower(), title_key, len(values)
                        values.append((key, approval, doc))
            for key, approval, doc in sorted(values):
                self._permissions.append((
                    approval,
                    doc.title,
                    Cell(doc.request_date, classes="nowrap"),
                    Cell(doc.english_response, classes="nowrap"),
                    Cell(doc.expiration_date, classes="nowrap"),
                    doc.spanish_request,
                    doc.comments,
                ))
        return self._permissions

    @property
    def report_type(self):
        """Denials, Requests, or Permissions."""
        if not hasattr(self, "_report_type"):
            if self.selection_method == "global":
                if "denied" in self.global_selections:
                    self._report_type = self.DENIALS
                else:
                    self._report_type = self.REQUESTS
            else:
                self._report_type = self.APPROVALS
        return self._report_type

    @property
    def req_end(self):
        """End of the date range for restricting by permission request date."""

        if not hasattr(self, "_req_end"):
            value = self.fields.getvalue("req_end")
            try:
                self._req_end = self.parse_date(value)
                if self._req_end:
                    self._req_end = f"{self._req_end} 23:59:59"
            except Exception:
                self.logger.exception("parsing req_end")
                self.bail("Invalid request end date")
        return self._req_end

    @property
    def req_start(self):
        """Start of date range for restricting by permission request date."""

        if not hasattr(self, "_req_start"):
            value = self.fields.getvalue("req_start")
            try:
                self._req_start = self.parse_date(value)
                if self._req_start:
                    self._req_start = str(self._req_start)
            except Exception:
                self.logger.exception("parsing req_start")
                self.bail("Invalid request start date")
        return self._req_start

    @property
    def requests(self):
        """Rows for the report table on permission requests."""

        if not hasattr(self, "_requests"):
            tags = dict(
                en="PermissionRequested",
                es="SpanishTranslationPermissionRequested",
            )
            paths = []
            for key in self.global_selections:
                paths.append(f"/Media/PermissionInformation/{tags[key]}")
            query = self.Query("query_term", "doc_id").unique()
            query.where(query.Condition("path", paths, "IN"))
            query.where(query.Condition("value", "Yes"))
            rows = query.execute(self.cursor).fetchall()
            docs = [Media(self, row.doc_id) for row in rows]
            self._requests = []
            for doc in sorted(docs):
                if doc.in_scope:
                    self._requests.append((
                        doc.title,
                        doc.request_date,
                        doc.english_response,
                        doc.expiration_date,
                        doc.spanish_request,
                        [str(approval) for approval in doc.approvals],
                        doc.comments,
                    ))
        return self._requests

    @property
    def rows(self):
        """Assemble the table rows for the report.

        Will use one of the `denials`, `requests` or `permissions`
        properties.
        """

        return getattr(self, self.report_type.lower())

    @property
    def selection_method(self):
        """Valid values are global and specific."""

        if not hasattr(self, "_selection_method"):
            methods = [method[0] for method in self.SELECTION_METHODS]
            name = "selection_method"
            self._selection_method = self.fields.getvalue(name, methods[0])
            if self._selection_method not in methods:
                self.bail()
        return self._selection_method

    @property
    def specific_method(self):
        """Selecting by document type, document ID, or board/language."""

        if not hasattr(self, "_specific_method"):
            self._specific_method = None
            name = self.selection_method
            if name == "specific":
                valid = [choice[0] for choice in self.SPECIFIC_CHOICES]
                self._specific_method = self.fields.getvalue(name, valid[0])
                if self._specific_method not in valid:
                    self.bail()
        return self._specific_method


class Media:
    """Media document proposed for inclusion on the report."""

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report options
            doc_id - integer for this document's CDR ID
        """

        self.__control = control
        self.__doc_id = doc_id

    def __lt__(self, other):
        """Sort by normalized title."""
        return self.sort_key < other.sort_key

    @property
    def approvals(self):
        """Sequence of information from ApprovedUse nodes."""

        if not hasattr(self, "_approvals"):
            self._approvals = []
            path = "PermissionInformation/ApprovedUse"
            for node in self.doc.root.findall(path):
                for child in node:
                    ref = child.get(f"{{{Doc.NS}}}ref")
                    if ref:
                        try:
                            approval = self.Approval(self, ref)
                            if approval.title:
                                self._approvals.append(approval)
                        except Exception:
                            self.control.exception("parsing %r", ref)
        return self._approvals

    @property
    def comments(self):
        """Sequence of comment strings for permission to use the media."""

        if not hasattr(self, "_comments"):
            self._comments = []
            for node in self.doc.root.findall("PermissionInformation/Comment"):
                comment = Doc.get_text(node, "").strip()
                if comment:
                    self._comments.append(comment)
        return self._comments

    @property
    def control(self):
        """Access to the database and to the report options."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for this CDR Media document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.__doc_id)
        return self._doc

    @property
    def english_request(self):
        """Request for use of English media content."""

        if not hasattr(self, "_english_request"):
            path = "PermissionInformation/PermissionRequested"
            self._english_request = Doc.get_text(self.doc.root.find(path))
        return self._english_request

    @property
    def english_response(self):
        """Response to request to use English media content."""

        if not hasattr(self, "_english_response"):
            path = "PermissionInformation/PermissionResponse"
            self._english_response = Doc.get_text(self.doc.root.find(path))
            if self.response_date:
                self._english_response += f" ({self.response_date})"
        return self._english_response

    @property
    def expiration_date(self):
        """Date on which the permission expires."""

        if not hasattr(self, "_expiration_date"):
            path = "PermissionInformation/PermissionExpirationDate"
            self._expiration_date = Doc.get_text(self.doc.root.find(path))
        return self._expiration_date

    @property
    def in_scope(self):
        """True if the document should be included on the report."""

        if self.control.exp_start or self.control.exp_end:
            if not self.expiration_date:
                return False
            if self.control.exp_start:
                if self.control.exp_start > self.expiration_date:
                    return False
            if self.control.exp_end:
                if self.control.exp_end < self.expiration_date:
                    return False
        if self.control.req_start or self.control.req_end:
            if not self.request_date:
                return False
            if self.control.req_start:
                if self.control.req_start > self.request_date:
                    return False
            if self.control.req_end:
                if self.control.req_end < self.request_date:
                    return False
        return True

    @property
    def request_date(self):
        """Date the request was submitted."""

        if not hasattr(self, "_request_date"):
            path = "PermissionInformation/PermissionRequestDate"
            self._request_date = Doc.get_text(self.doc.root.find(path))
        return self._request_date

    @property
    def response_date(self):
        """Date the response to the request was received."""

        if not hasattr(self, "_response_date"):
            path = "PermissionInformation/PermissionResponseDate"
            self._response_date = Doc.get_text(self.doc.root.find(path))
        return self._response_date

    @property
    def spanish_request(self):
        """Request for use of Spanish media content."""

        path = "PermissionInformation/SpanishTranslationPermissionRequested"
        if not hasattr(self, "_spanish_request"):
            self._spanish_request = Doc.get_text(self.doc.root.find(path))
            if self.spanish_response:
                self._spanish_request += f" ({self.spanish_response})"
        return self._spanish_request

    @property
    def spanish_response(self):
        """Response to request to use Spanish media content."""

        path = "PermissionInformation/SpanishTranslationPermissionResponse"
        if not hasattr(self, "_spanish_response"):
            self._spanish_response = Doc.get_text(self.doc.root.find(path))
        return self._spanish_response

    @property
    def title(self):
        """Brief title for the Media document."""

        if not hasattr(self, "_title"):
            try:
                title = self.doc.title.split(";")[0].strip()
                self._title = f"{title} (CDR{self.doc.id})"
            except Exception:
                self.control.exception("parsing document %r", self.__doc_id)
                self.control.bail(f"Cannot find document {self.__doc_id!r}")
        return self._title

    @property
    def sort_key(self):
        """Sort by normalized title."""

        if not hasattr(self, "_sort_key"):
            self._sort_key = self.title.lower()
        return self._sort_key

    class Approval:
        """Identification of a document for which use is authorized."""

        def __init__(self, media, ref):
            """Remember the caller's values

            Pass:
                media - document for the media needing permissions
                ref - ID of the using document
            """

            self.__media = media
            self.__ref = ref

        def __str__(self):
            """Format the approval for display in the report's table."""
            return f"{self.title} (CDR{self.doc_id:d})"

        @property
        def doc_id(self):
            """Integer parsed from the cdr:ref attribute."""

            if not hasattr(self, "_doc_id"):
                self._doc_id = Doc.extract_id(self.__ref)
            return self._doc_id

        @property
        def title(self):
            """String for the using document's title."""

            if not hasattr(self, "_title"):
                doc = Doc(self.__media.control.session, id=self.doc_id)
                self._title = doc.title.split(";")[0].strip()
            return self._title


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
