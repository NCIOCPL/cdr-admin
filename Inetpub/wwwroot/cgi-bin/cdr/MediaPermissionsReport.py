#!/usr/bin/env python

"""Report on management of PDQ media permissions.

JIRA::OCECDR-3704
"""

from functools import cached_property
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

    @cached_property
    def board(self):
        """PDQ board(s) selected for the report."""

        if self.specific_method != "summary":
            return None
        boards = []
        values = self.fields.getlist("board")
        if "all" in values:
            return []
        for id in values:
            if not id.isdigit():
                self.bail()
            id = int(id)
            if id not in self.boards:
                self.bail()
            boards.append(id)
        return boards

    @cached_property
    def boards(self):
        """Dictionary of boards used for parameter validation."""
        return self.get_boards()

    @cached_property
    def caption(self):
        """String to be displayed at the top of the report table."""

        if self.report_type == self.DENIALS:
            return "Media Permission Denials"
        if self.report_type == self.REQUESTS:
            languages = dict(en="English", es="Spanish")
            languages = [languages[key] for key in self.global_selections]
            languages = " and ".join(languages)
            return f"{languages} Permission Requests"
        if self.doc_id:
            return f"Media Approved For Use With CDR{self.doc_id}"
        elif self.doctype:
            doctype = dict(
                both="Summaries and Glossary Terms",
                summary="Summaries",
                glossary="Glossary Terms",
            )[self.doctype]
            return f"Media Approved For Use With {doctype}"
        caption = f"Media Approved For Use With {self.language} "
        if not self.board:
            return f"{caption} Summaries"
        boards = [self.boards[id] for id in self.board]
        if len(boards) < 3:
            boards = " and ".join(boards)
        else:
            first = ", ".join(boards[:-1])
            boards = f"{first}, and {boards[-1]}"
        return f"{caption} {boards} Summaries"

    @cached_property
    def columns(self):
        """Strings for the top of the report's table columns."""

        columns = []
        for label, width in self.COLUMNS[self.report_type]:
            column = self.Reporter.Column(label, width=f"{width:d}px")
            columns.append(column)
        return columns

    @cached_property
    def denials(self):
        """Rows for the report table on permission denials."""

        query = self.Query("query_term", "doc_id").unique()
        query.where(query.Condition("path", self.RESPONSE_PATHS, "IN"))
        query.where(query.Condition("value", "Permission Denied"))
        rows = query.execute(self.cursor).fetchall()
        docs = [Media(self, row.doc_id) for row in rows]
        denials = []
        for doc in sorted(docs):
            if doc.in_scope:
                denials.append((
                    doc.title,
                    doc.request_date,
                    doc.english_response,
                    doc.spanish_request,
                    doc.comments,
                ))
        return denials

    @cached_property
    def doc_id(self):
        """Integer for CDR document selected for the report."""

        if self.specific_method != "docid":
            return None
        doc_id = self.fields.getvalue("docid")
        if doc_id:
            if not doc_id.isdigit():
                self.bail()
        return int(doc_id)

    @cached_property
    def doctype(self):
        """One of summary, glossary, or both."""

        if self.specific_method != "doctype":
            return None
        valid = [choice[0] for choice in self.DOCTYPE_CHOICES]
        doctype = self.fields.getvalue("doctype", valid[0])
        if doctype not in valid:
            self.bail()
        return doctype

    @cached_property
    def exp_end(self):
        """End of the date range for restricting by permission expiration."""

        value = self.fields.getvalue("exp_end")
        try:
            end = self.parse_date(value)
            return f"{end} 23:59:59" if end else None
        except Exception:
            self.logger.exception("parsing exp_end")
            self.bail("Invalid expiration end date")

    @cached_property
    def exp_start(self):
        """Start of the date range for restricting by permission expiration."""

        value = self.fields.getvalue("exp_start")
        try:
            start = self.parse_date(value)
            return str(start) if start else None
        except Exception:
            self.logger.exception("parsing exp_start")
            self.bail("Invalid expiration start date")

    @cached_property
    def global_selections(self):
        """Selection(s) made for reporting on requests or denials."""

        if self.selection_method != "global":
            return None
        valid = [choice[0] for choice in self.GLOBAL_CHOICES]
        values = self.fields.getlist("global") or [valid[0]]
        if set(values) - set(valid):
            self.bail()
        if "denied" in values and len(values) > 1:
            self.bail("Can't combine 'denied' with other options")
        return values

    @cached_property
    def language(self):
        """English or Spanish (used when selecting summaries by PDQ board."""

        if self.specific_method != "summary":
            return None
        language = self.fields.getvalue("language", "English")
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def media_by_docid(self):
        """Sequence of IDs for media used by a one summary or glossary term."""

        paths = list(self.USAGE_PATHS.values())
        query = self.Query("query_term", "doc_id").unique()
        query.where(query.Condition("path", paths, "IN"))
        query.where(query.Condition("int_val", self.doc_id))
        rows = query.execute(self.cursor).fetchall()
        return [row.doc_id for row in rows]

    @cached_property
    def media_by_doctype(self):
        """Sequence of IDs for media used by docs of the selected type(s)."""

        query = self.Query("query_term", "doc_id").unique()
        if self.doctype == "both":
            paths = list(self.USAGE_PATHS.values())
            query.where(query.Condition("path", paths, "IN"))
        else:
            path = self.USAGE_PATHS[self.doctype]
            query.where(query.Condition("path", path))
        rows = query.execute(self.cursor).fetchall()
        return [row.doc_id for row in rows]

    @cached_property
    def media_by_summary(self):
        """Sequence of IDs for media used by selected PDQ summaries."""

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
        return [row.doc_id for row in rows]

    @cached_property
    def permissions(self):
        """Rows for the report table on granted permissions."""

        permissions = []
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
            permissions.append((
                approval,
                doc.title,
                Cell(doc.request_date, classes="nowrap"),
                Cell(doc.english_response, classes="nowrap"),
                Cell(doc.expiration_date, classes="nowrap"),
                doc.spanish_request,
                doc.comments,
            ))
        return permissions

    @cached_property
    def report_type(self):
        """Denials, Requests, or Permissions."""

        if self.selection_method == "global":
            if "denied" in self.global_selections:
                return self.DENIALS
            else:
                return self.REQUESTS
        else:
            return self.APPROVALS

    @cached_property
    def req_end(self):
        """End of the date range for restricting by permission request date."""

        value = self.fields.getvalue("req_end")
        try:
            end = self.parse_date(value)
            if end:
                return f"{end} 23:59:59" if end else None
        except Exception:
            self.logger.exception("parsing req_end")
            self.bail("Invalid request end date")

    @cached_property
    def req_start(self):
        """Start of date range for restricting by permission request date."""

        value = self.fields.getvalue("req_start")
        try:
            start = self.parse_date(value)
            return str(start) if start else None
        except Exception:
            self.logger.exception("parsing req_start")
            self.bail("Invalid request start date")

    @cached_property
    def requests(self):
        """Rows for the report table on permission requests."""

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
        requests = []
        for doc in sorted(docs):
            if doc.in_scope:
                requests.append((
                    doc.title,
                    doc.request_date,
                    doc.english_response,
                    doc.expiration_date,
                    doc.spanish_request,
                    [str(approval) for approval in doc.approvals],
                    doc.comments,
                ))
        return requests

    @cached_property
    def rows(self):
        """Assemble the table rows for the report.

        Will use one of the `denials`, `requests` or `permissions`
        properties.
        """

        return getattr(self, self.report_type.lower())

    @cached_property
    def selection_method(self):
        """Valid values are global and specific."""

        methods = [method[0] for method in self.SELECTION_METHODS]
        method = self.fields.getvalue("selection_method", methods[0])
        if method not in methods:
            self.bail()
        return method

    @cached_property
    def specific_method(self):
        """Selecting by document type, document ID, or board/language."""

        if self.selection_method != "specific":
            return None
        valid = [choice[0] for choice in self.SPECIFIC_CHOICES]
        method = self.fields.getvalue("specific", valid[0])
        if method not in valid:
            self.bail()
        return method

    @cached_property
    def use_basic_web_page(self):
        """Use the sinpler layout for the report."""
        return True


class Media:
    """Media document proposed for inclusion on the report."""

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report options
            doc_id - integer for this document's CDR ID
        """

        self.control = control
        self.doc_id = doc_id

    def __lt__(self, other):
        """Sort by normalized title."""
        return self.sort_key < other.sort_key

    @cached_property
    def approvals(self):
        """Sequence of information from ApprovedUse nodes."""

        approvals = []
        for node in self.doc.root.findall("PermissionInformation/ApprovedUse"):
            for child in node:
                ref = child.get(f"{{{Doc.NS}}}ref")
                if ref:
                    try:
                        approval = self.Approval(self, ref)
                        if approval.title:
                            approvals.append(approval)
                    except Exception:
                        self.control.exception("parsing %r", ref)
        return approvals

    @cached_property
    def comments(self):
        """Sequence of comment strings for permission to use the media."""

        comments = []
        for node in self.doc.root.findall("PermissionInformation/Comment"):
            comment = Doc.get_text(node, "").strip()
            if comment:
                comments.append(comment)
        return comments

    @cached_property
    def doc(self):
        """`Doc` object for this CDR Media document."""
        return Doc(self.control.session, id=self.doc_id)

    @cached_property
    def english_request(self):
        """Request for use of English media content."""

        path = "PermissionInformation/PermissionRequested"
        return Doc.get_text(self.doc.root.find(path))

    @cached_property
    def english_response(self):
        """Response to request to use English media content."""

        path = "PermissionInformation/PermissionResponse"
        response = Doc.get_text(self.doc.root.find(path))
        if self.response_date:
            response += f" ({self.response_date})"
        return response

    @cached_property
    def expiration_date(self):
        """Date on which the permission expires."""

        path = "PermissionInformation/PermissionExpirationDate"
        return Doc.get_text(self.doc.root.find(path))

    @cached_property
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

    @cached_property
    def request_date(self):
        """Date the request was submitted."""

        path = "PermissionInformation/PermissionRequestDate"
        return Doc.get_text(self.doc.root.find(path))

    @cached_property
    def response_date(self):
        """Date the response to the request was received."""

        path = "PermissionInformation/PermissionResponseDate"
        return Doc.get_text(self.doc.root.find(path))

    @cached_property
    def spanish_request(self):
        """Request for use of Spanish media content."""

        path = "PermissionInformation/SpanishTranslationPermissionRequested"
        request = Doc.get_text(self.doc.root.find(path))
        if self.spanish_response:
            request += f" ({self.spanish_response})"
        return request

    @cached_property
    def spanish_response(self):
        """Response to request to use Spanish media content."""

        path = "PermissionInformation/SpanishTranslationPermissionResponse"
        return Doc.get_text(self.doc.root.find(path))

    @cached_property
    def title(self):
        """Brief title for the Media document."""

        try:
            title = self.doc.title.split(";")[0].strip()
            return f"{title} (CDR{self.doc.id})"
        except Exception:
            self.control.exception("parsing document %r", self.doc_id)
            self.control.bail(f"Cannot find document {self.doc_id!r}")

    @cached_property
    def sort_key(self):
        """Sort by normalized title."""
        return self.title.lower()

    class Approval:
        """Identification of a document for which use is authorized."""

        def __init__(self, media, ref):
            """Remember the caller's values

            Pass:
                media - document for the media needing permissions
                ref - ID of the using document
            """

            self.media = media
            self.ref = ref

        def __str__(self):
            """Format the approval for display in the report's table."""
            return f"{self.title} (CDR{self.doc_id:d})"

        @cached_property
        def doc_id(self):
            """Integer parsed from the cdr:ref attribute."""
            return Doc.extract_id(self.ref)

        @cached_property
        def title(self):
            """String for the using document's title."""

            doc = Doc(self.media.control.session, id=self.doc_id)
            return doc.title.split(";")[0].strip()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
