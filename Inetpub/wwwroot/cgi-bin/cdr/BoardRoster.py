#!/usr/bin/env python

"""Display the Board Roster with or without assistant information.
"""

from functools import cached_property
from cdrcgi import Controller, BasicWebPage
from cdrapi.docs import Doc
from datetime import date, datetime, timedelta
from lxml import html


class Control(Controller):
    """Access to the database and form/report-building tools."""

    SUBTITLE = "PDQ Board Roster Report"
    SHOW_ALL = "Show All Contact Information"
    SHOW_SUBGROUP = "Show Subgroup Information"
    SHOW_ASSISTANT = "Show Assistant Information"
    FULL_OPTIONS = SHOW_ALL, SHOW_SUBGROUP, SHOW_ASSISTANT
    MEMBERSHIP_DETAILS_PATH = "/PDQBoardMemberInfo/BoardMembershipDetails"
    BOARD_PATH = f"{MEMBERSHIP_DETAILS_PATH}/BoardName/@cdr:ref"
    CURRENT_PATH = f"{MEMBERSHIP_DETAILS_PATH}/CurrentMember"
    TERM_START_PATH = f"{MEMBERSHIP_DETAILS_PATH}/TermStartDate"
    EIC_START_PATH = f"{MEMBERSHIP_DETAILS_PATH}/EditorInChief/TermStartDate"
    EIC_FINISH_PATH = f"{MEMBERSHIP_DETAILS_PATH}/EditorInChief/TermEndDate"
    PERSON_PATH = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
    COLUMNS = (
        ("Phone", "Phone"),
        ("Fax", "Fax"),
        ("E-mail", "Email"),
        ("CDR ID", "CDR-ID"),
        ("Start Date", "Start Date"),
        ("Government Employee", "Gov. Empl."),
        ("Areas of Expertise", "Area of Exp."),
        ("Membership in Subgroups", "Member Subgrp"),
        ("Term End Date", "Term End Date"),
        ("Affiliations", "Affl. Name"),
        ("Contact Mode", "Contact Mode"),
        ("Assistant Name", "Assist Name"),
        ("Assistant E-mail", "Assist Email"),
        ("Response Date", "Resp. Date"),
    )
    DEFAULTS = "Phone", "E-mail"
    JS = (
        "function check_columns(dummy) {}",
        "function check_type(choice) {",
        "    if (choice == 'full') {",
        "        jQuery('#full-options-box').show();",
        "        jQuery('.summary-fieldset').hide();",
        "    }",
        "    else {",
        "        jQuery('#full-options-box').hide();",
        "        jQuery('.summary-fieldset').show();",
        "    }",
        "}",
        "jQuery(function() {",
        "    var choice = jQuery('input[name=\"type\"]:radio:checked').val();",
        "    check_type(choice);",
        "});",
    )
    EXTRA_HELP = (
        "The 'Extra Cols' field's value must be an integer, specifying the "
        "number of additional blank columns to be added to the report. You "
        "can optionally append a colon followed by a list of integers "
        "separated by spaces, one for each of the blank columns to be added, "
        "specifying the width of that column. Field widths for extra fields "
        "are only used when the report format is HTML."
    )
    CSS = "/stylesheets/BoardRoster.css"

    def build_tables(self):
        """Assemble the table for the summary version of the report."""

        if self.type == "full":
            return []
        caption = (
            self.board_name,
            self.started.strftime("%B %d, %Y"),
        )
        opts = dict(caption=caption, columns=self.column_headers)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask the user for the report parameters.

        Pass:
            page - HTMLPage object with which the form fields are drawn
        """

        fieldset = page.fieldset("Select Board")
        options = [("", "Pick a Board")] + self.boards
        opts = dict(label="PDQ Board", options=options)
        fieldset.append(page.select("board", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Report Type")
        fieldset.append(page.radio_button("type", value="full", checked=True))
        fieldset.append(page.radio_button("type", value="summary"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        fieldset.set("id", "full-options-box")
        for option in self.FULL_OPTIONS:
            fieldset.append(page.checkbox("option", value=option))
        page.form.append(fieldset)
        fieldset = page.fieldset("Columns to Include")
        fieldset.set("class", "summary-fieldset hidden usa-fieldset")
        for name, header in self.COLUMNS:
            checked = name in self.DEFAULTS
            opts = dict(value=name, label=name, checked=checked)
            if name == "Term End Date":
                tooltip = "calculated using the term renewal frequency"
                opts["tooltip"] = tooltip
            fieldset.append(page.checkbox("column", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Miscellaneous Summary Report Options")
        fieldset.set("class", "summary-fieldset hidden usa-fieldset")
        fieldset.append(page.B.P(self.EXTRA_HELP))
        field = page.text_field("extra", label="Extra Cols", value=0)
        field.find("input").set("type", "number")
        fieldset.append(field)
        page.form.append(fieldset)
        fieldset = page.add_output_options(default="html")
        fieldset.set("class", "summary-fieldset hidden usa-fieldset")
        page.add_script("\n".join(self.JS))

    def show_report(self):
        """Override the base class (this might not be a tabular report)."""

        if not self.board_id:
            message = "You must select a board."
            self.alerts.append(dict(message=message, type="error"))
            return self.show_form()
        if self.type == "full":
            return self.send_page(self.full_report)
        if self.format == "html" and len(self.column_headers) > 3:
            report = BasicWebPage()
            report.wrapper.append(report.B.H1(self.subtitle))
            report.wrapper.append(self.build_tables().node)
            report.wrapper.append(self.footer)
            return report.send()
        Controller.show_report(self)

    @cached_property
    def board_id(self):
        """Integer ID for the board selected from the form (if any)."""

        id = self.fields.getvalue("board", "").strip()
        if id:
            if not id.isdigit():
                self.bail()
            return int(id)
        return None

    @cached_property
    def board_manager_block(self):
        """Block for the bottom of the full report.

        TODO: Replace HTML markup deprecated by HTML5, fixing the filter
        output to match (we're using the deprecated markup here so the
        board manager block will match that of the board members when
        pulled into Microsoft Word).
        """

        paths = (
            '/Organization/PDQBoardInformation/BoardManager',
            '/Organization/PDQBoardInformation/BoardManagerEmail',
            '/Organization/PDQBoardInformation/BoardManagerPhone'
        )
        query = self.Query("query_term", "value").order("path")
        query.where(query.Condition("path", paths, "IN"))
        query.where(query.Condition("doc_id", self.board_id))
        values = [row.value for row in query.execute(self.cursor).fetchall()]
        if len(values) != 3:
            self.bail("board manager information missing")
        name, email, phone = values
        B = self.HTMLPage.B
        return B.TABLE(
            B.TR(
                B.TD(
                    B.B(B.U("Board Manager Information")), B.BR(),
                    B.B(name or "No Board Manager"), B.BR(),
                    "Office of Cancer Content", B.BR(),
                    "Office of Communications and Public Liaison", B.BR(),
                    "National Cancer Institute", B.BR(),
                    "9609 Medical Center Drive, MSC 9760", B.BR(),
                    "Rockville, MD 20850", B.BR(), B.BR(),
                    B.TABLE(
                        B.TR(
                            B.TD("Phone", width="35%"),
                            B.TD(phone or "TBD")
                        ),
                        B.TR(
                            B.TD("Fax", width="35%"),
                            B.TD("240-276-7679")
                        ),
                        B.TR(
                            B.TD("Email", width="35%"),
                            B.TD(B.A(email, href=f"mailto:{email}"))
                        ),
                        width="100%",
                        cellspacing="0",
                        cellpadding="0"
                    )
                )
            ),
            width="100%"
        )

    @cached_property
    def board_name(self):
        """String for the board name, drawn from its document title."""

        name = dict(self.boards).get(self.board_id)
        if not name:
            self.bail("No board selected")
        return name

    @cached_property
    def boards(self):
        """Boards for the picklist."""

        query = self.Query("active_doc d", "d.id", "d.title").unique()
        query.join("query_term t", "t.doc_id = d.id")
        query.where("t.path = '/Organization/OrganizationType'")
        query.where("t.value LIKE 'PDQ % Board'")
        query.order("d.title")
        boards = []
        for row in query.execute(self.cursor).fetchall():
            boards.append([row.id, row.title.split(";")[0].strip()])
        return boards

    @cached_property
    def column_headers(self):
        """Column headers for the summary table."""

        headers = [self.Reporter.Column("Name", width="250px")]
        for field, header in self.COLUMNS:
            if field in self.columns:
                headers.append(self.Reporter.Column(header, width="120px"))
        for width in self.extra_columns:
            headers.append(self.Reporter.Column(" ", width=f"{width}px"))
        return headers

    @cached_property
    def columns(self):
        """Columns selected for inclusion in the summary report."""
        return self.fields.getlist("column")

    @cached_property
    def extra_columns(self):
        """Sequence of integers for width in pixels of extra columns."""

        value = self.fields.getvalue("extra")
        if value:
            if ":" in value:
                count, widths = value.split(":", 1)
            else:
                count, widths = value, None
            try:
                count = int(count)
                if count < 0:
                    self.bail("count must be a non-negativeinteger")
                if widths:
                    widths = [int(width) for width in widths.split()]
                    if len(widths) != count:
                        self.bail("Widths much match number of extra cols")
            except Exception:
                self.logger.exception("Failure with extra of %s", value)
                self.bail("Invalid value for extra columns")
            if widths:
                return widths
            elif count:
                remaining = 750 - 100 * len(self.columns)
                width = remaining / count if remaining > 0 else 100
                return [width] * count
            return []

    @cached_property
    def full_report(self):
        """Custom report, without the standard CDR admin banner."""

        B = self.HTMLPage.B
        head = B.HEAD(
            B.META(charset="utf-8"),
            B.TITLE(f"PDQ Board Member Roster Report - {self.board_name}"),
            B.LINK(href=self.CSS, rel="stylesheet")
        )
        body = B.BODY(
            B.H1(
                self.board_name,
                B.BR(),
                B.SPAN(
                    self.started.strftime("%B %d, %Y"),
                    style="font-size: 12pt"
                )
            ),
            id="main"
        )
        for member in sorted(self.members):
            info = member.filtered_info
            info.set("class", "member")
            body.append(info)
        body.append(self.board_manager_block)
        page = B.HTML(head, body)
        opts = dict(pretty_print=True, encoding="unicode")
        return html.tostring(page, **opts)

    @cached_property
    def members(self):
        """Current members of the selected PDQ board."""

        if not self.board_id:
            return []
        if self.board_id:
            fields = (
                "m.doc_id AS member_id",
                "d.id AS person_id",
                "t.value AS term_start",
                "e.value AS eic_start",
                "f.value AS eic_finish",
            )
            query = self.Query("query_term m", *fields).unique()
            query.join("query_term p", "p.doc_id = m.doc_id")
            query.join("active_doc d", "d.id = p.int_val")
            query.join("query_term c", "c.doc_id = m.doc_id",
                       "LEFT(c.node_loc, 4) = LEFT(m.node_loc, 4)")
            query.outer("query_term t", "t.doc_id = m.doc_id",
                        "LEFT(t.node_loc, 4) = LEFT(m.node_loc, 4)",
                        f"t.path = '{self.TERM_START_PATH}'")
            query.outer("query_term e", "e.doc_id = m.doc_id",
                        "LEFT(e.node_loc, 4) = LEFT(m.node_loc, 4)",
                        f"e.path = '{self.EIC_START_PATH}'")
            query.outer("query_term f", "f.doc_id = m.doc_id",
                        "LEFT(f.node_loc, 4) = LEFT(m.node_loc, 4)",
                        f"f.path = '{self.EIC_FINISH_PATH}'")
            query.where(f"m.path = '{self.BOARD_PATH}'")
            query.where(f"p.path = '{self.PERSON_PATH}'")
            query.where(f"c.path = '{self.CURRENT_PATH}'")
            query.where("c.value = 'Yes'")
            query.where(query.Condition("m.int_val", self.board_id))
            query.log()
            rows = query.execute(self.cursor).fetchall()
            return [BoardMember(self, row) for row in rows]

    @cached_property
    def method(self):
        """Smooth the way for pulling the report into Microsoft Word."""
        return "get"

    @cached_property
    def no_results(self):
        """Suppress the warning which would otherwise be shown."""
        return None

    @cached_property
    def options(self):
        """Options selected for the full report."""
        return self.fields.getlist("option")

    @cached_property
    def rows(self):
        """Values for the summary table."""

        rows = [member.row for member in sorted(self.members)]
        if "employee" in self.columns:
            opts = dict(len(self.columns)+1, classes="footer")
            footnote = self.Reporter.Cell("* - Honoraria Declined", **opts)
            rows.append(footnote)
        return rows

    @cached_property
    def same_window(self):
        """Avoid opening lots of browser tabs."""
        return self.SUBMIT if self.request else []

    @cached_property
    def title(self):
        """Override title for Excel workbook."""

        if self.type == "full" and self.format == "excel":
            return self.board_name
        return self.TITLE

    @cached_property
    def type(self):
        """Report type (full or summary)."""
        return self.fields.getvalue("type") or "full"


class BoardMember:
    """Member of the selected PDQ board.

    Note that there are some variations in the approaches to pulling
    information out of the BoardMembershipDetails blocks. Some of the
    code is parsing values from the document, and some is getting
    values from the database query of the query_term table. Those
    approaches will come up with consistent results, as long as the
    documents only contain at most one BoardMembershipDetails block
    for a given board. According to Robin J., that should always be
    true. However, there is one document with two such blocks for
    the same board (CDR769075 for Aimee Kriemer). Robin says that's
    a data error, so the code should be OK as it is. See discussion
    in https://tracker.nci.nih.gov/browse/OCECDR-4693.
    """

    TODAY = str(date.today())
    FREQUENCY = {"Every year": 1, "Every two years": 2}
    YEAR = timedelta(365)
    SPECIFIC_CONTACT = "BoardMemberContact/SpecificBoardMemberContact"
    COMMON_FILTERS = [
        "set:Denormalization PDQBoardMemberInfo Set",
        "name:Copy XML for Person 2",
    ]
    SPECIFIC_FILTERS = dict(
        summary="name:PDQBoardMember Roster Summary",
        full="name:PDQBoardMember Roster",
    )

    def __init__(self, control, row):
        """Save the caller's values.

        Pass:
            control - access to the database and the report options
            row - values from the database query

        docId, eic_start, eic_finish, term_start, name):
        """

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Sort editors-in-chief before others, subgroup by name."""

        a = 0 if self.is_eic else 1, self.name.upper()
        b = 0 if other.is_eic else 1, other.name.upper()
        return a < b

    @cached_property
    def affiliations(self):
        """Sequence of strings for member's professional affiliations."""

        affiliations = []
        path = "Affiliations/Affiliation/AffiliationName"
        for node in self.doc.root.findall(path):
            name = Doc.get_text(node, "").strip()
            if name:
                affiliations.append(name)
        return affiliations

    @cached_property
    def areas_of_expertise(self):
        """Sequence of strings showing professional strengths."""

        areas = set()
        for membership in self.memberships:
            areas |= membership.areas_of_expertise
        return sorted(areas)

    @cached_property
    def assistant_email(self):
        """String for the email address of the board member's assistant."""

        node = self.doc.root.find("BoardMemberAssistant/AssistantEmail")
        return Doc.get_text(node, "").strip() or None

    @cached_property
    def assistant_name(self):
        """String for the name of the board member's assistant."""

        node = self.doc.root.find("BoardMemberAssistant/AssistantName")
        return Doc.get_text(node, "").strip()

    @cached_property
    def contact_mode(self):
        """String for the name of the board member's preferred contact mode."""

        node = self.doc.root.find("BoardMemberContactMode")
        return Doc.get_text(node, "").strip()

    @cached_property
    def doc(self):
        """`Doc` object for the membership info document."""
        return Doc(self.__control.session, id=self.__row.member_id)

    @cached_property
    def eic_end(self):
        """String for the date the editor-in-chief term (if any) ended."""
        return self.__row.eic_finish

    @cached_property
    def eic_start(self):
        """String for the date the editor-in-chief term (if any) started."""
        return self.__row.eic_start

    @cached_property
    def email(self):
        """Email address parsed from the filtered member information."""

        if self.filtered_info is not None:
            node = self.filtered_info.find("table/tr/td/email")
            return Doc.get_text(node, "").strip()
        return None

    @cached_property
    def emails(self):
        """Unique email addresses for the board member."""

        emails = []
        if self.email:
            emails.append(self.email)
        if self.specific_email:
            se = self.specific_email
            if not self.email or self.email.lower() != se.lower():
                emails.append(se)
        if self.__control.format == "excel":
            return emails
        span = self.__control.HTMLPage.B.SPAN()
        br = None
        for email in emails:
            a = self.__control.HTMLPage.B.A(email, href=f"mailto:{email}")
            if br is not None:
                span.append(br)
            span.append(a)
            br = self.__control.HTMLPage.B.BR()
        return self.__control.Reporter.Cell(span)

    @cached_property
    def employee_status(self):
        """String indicating whether member is a government employee."""

        node = self.doc.root.find("GovernmentEmployee")
        status = Doc.get_text(node, "").strip() or "Unknown"
        if status == "No" and node.get("HonorariaDeclined") == "Yes":
            status = "No^*"
        return status

    @cached_property
    def fax(self):
        """Fax number parsed from the filtered member information."""

        if self.filtered_info is not None:
            node = self.filtered_info.find("table/tr/td/fax")
            return Doc.get_text(node, "").strip()
        return None

    @cached_property
    def faxes(self):
        """Unique fax numbers for this board member."""

        faxes = []
        if self.fax:
            faxes.append(self.fax)
        if self.specific_fax and self.specific_fax != self.fax:
            faxes.append(self.specific_fax)
        return faxes or ""

    @cached_property
    def filtered_info(self):
        """Information pulled together for the board members using XSL/T."""

        filters = list(self.COMMON_FILTERS)
        filters.append(self.SPECIFIC_FILTERS[self.__control.type])
        result = self.doc.filter(*filters, parms=self.filter_parms)
        filtered_info = html.fromstring(str(result.result_tree))
        for node in filtered_info.findall("br"):
            if node.tail == "U.S.A.":
                filtered_info.remove(node)
        return filtered_info

    @cached_property
    def filter_parms(self):
        """Dictionary of parameter information to feed to the filters."""

        options = {}
        if self.__control.type == "full":
            options = self.__control.options
        return dict(
            eic="Yes" if self.is_eic else "No",
            subgroup="Yes" if Control.SHOW_SUBGROUP in options else "No",
            assistant="Yes" if Control.SHOW_ASSISTANT in options else "No",
            otherInfo="Yes" if Control.SHOW_ALL in options else "No",
        )

    @cached_property
    def full_name(self):
        """Name of the board member parsed from the filtered information."""

        if self.filtered_info is not None:
            node = self.filtered_info.find("b")
            return Doc.get_text(node, "").strip()
        return self.name

    @cached_property
    def is_eic(self):
        """True if this board member is the current editor-in-chief."""

        if self.eic_start and self.eic_start <= self.TODAY:
            if not self.eic_end or self.eic_end > self.TODAY:
                return True
        return False

    @cached_property
    def memberships(self):
        """Membership(s) in the selected board."""

        memberships = []
        for node in self.doc.root.findall("BoardMembershipDetails"):
            membership = self.Membership(self.__control, node)
            if membership.board_id == self.__control.board_id:
                memberships.append(membership)
        return memberships

    @cached_property
    def name(self):
        """Member's name, as pulled from the Person document title."""
        return self.person.title.split(";")[0].strip()

    @cached_property
    def person(self):
        """`Doc` object for the member's CDR Person document."""
        return Doc(self.__control.session, id=self.__row.person_id)

    @cached_property
    def phone(self):
        """Phone number parsed from the filtered member information."""

        if self.filtered_info is not None:
            node = self.filtered_info.find("table/tr/td/phone")
            return Doc.get_text(node, "").strip()
        return None

    @cached_property
    def phones(self):
        """Sequence of phone numbers."""

        phones = []
        if self.phone:
            phones.append(self.phone)
        if self.specific_phone and self.specific_phone != self.phone:
            phones.append(self.specific_phone)
        return phones

    @cached_property
    def response_dates(self):
        """Response dates added by OCECDR-4693."""

        dates = []
        for membership in self.memberships:
            dates += membership.response_dates
        return dates

    @cached_property
    def row(self):
        """Values for the summary report's table."""

        Cell = self.__control.Reporter.Cell
        row = [Cell(self.full_name, bold=True)]
        if "Phone" in self.__control.columns:
            row.append(self.phones)
        if "Fax" in self.__control.columns:
            row.append(self.faxes)
        if "E-mail" in self.__control.columns:
            row.append(self.emails)
        if "CDR ID" in self.__control.columns:
            row.append(Cell(self.doc.id, center=True))
        if "Start Date" in self.__control.columns:
            row.append(Cell(self.term_start, center=True))
        if "Government Employee" in self.__control.columns:
            row.append(self.employee_status)
        if "Areas of Expertise" in self.__control.columns:
            row.append(self.areas_of_expertise)
        if "Membership in Subgroups" in self.__control.columns:
            row.append(self.subgroups)
        if "Term End Date" in self.__control.columns:
            row.append(Cell(self.term_end, classes="emphasis center"))
        if "Affiliations" in self.__control.columns:
            row.append(self.affiliations)
        if "Contact Mode" in self.__control.columns:
            row.append(self.contact_mode)
        if "Assistant Name" in self.__control.columns:
            row.append(self.assistant_name)
        if "Assistant E-mail" in self.__control.columns:
            if self.assistant_email:
                url = f"mailto:{self.assistant_email}"
                row.append(Cell(self.assistant_email, href=url))
            else:
                row.append("")
        if "Response Date" in self.__control.columns:
            row.append(self.response_dates)
        for col in range(len(self.__control.extra_columns)):
            row.append("")
        return row

    @cached_property
    def specific_email(self):
        """String for email address used specifically for the member role."""

        path = f"{self.SPECIFIC_CONTACT}/BoardContactEmail"
        node = self.doc.root.find(path)
        return Doc.get_text(node, "").strip()

    @cached_property
    def specific_fax(self):
        """String for fax number used specifically for the member role."""

        path = f"{self.SPECIFIC_CONTACT}/BoardContactFax"
        node = self.doc.root.find(path)
        return Doc.get_text(node, "").strip()

    @cached_property
    def specific_phone(self):
        """String for phone number used specifically for the member role."""

        path = f"{self.SPECIFIC_CONTACT}/BoardContactPhone"
        node = self.doc.root.find(path)
        return Doc.get_text(node, "").strip()

    @cached_property
    def subgroups(self):
        """Sequence of strings for the names of the member's subgroups."""

        subgroups = set()
        for membership in self.memberships:
            subgroups |= membership.subgroups
        return sorted(subgroups)

    @cached_property
    def term_end(self):
        """String for the calculated end of the board member's term."""

        if not self.term_start:
            return None
        for membership in self.memberships:
            if membership.frequency:
                years = self.FREQUENCY.get(membership.frequency)
                if years is None:
                    message = "Invalid frequency {!r} for {}"
                    args = self.full_name, membership.frequency
                    self.__control.bail(message.format(*args))
                delta = self.YEAR * years
                try:
                    args = self.term_start, "%Y-%m-%d"
                    start = datetime.strptime(*args)
                    end = start + delta
                    return end.strftime("%Y-%m-%d")
                except Exception:
                    self.__control.logger.exception(self.full_name)
                    args = self.full_name, self.term_start
                    message = "Bad term date for {}: {}"
                    self.__control.bail(message.format(*args))

    @cached_property
    def term_start(self):
        """String for the date the board member's term began."""
        return self.__row.term_start

    class Membership:
        """Membership of a particular board."""

        def __init__(self, control, node):
            """Remember the caller's values.

            Pass:
                control - access to logging
                node - block of details for this membership
            """

            self.__node = node

        @cached_property
        def areas_of_expertise(self):
            """Member's expertise relevant to this board."""

            areas = set()
            for node in self.__node.findall("AreaOfExpertise"):
                area = Doc.get_text(node, "").strip()
                if area:
                    areas.add(area)
            return areas

        @cached_property
        def board_id(self):
            """Integer for the board's CDR Organization ID."""

            node = self.__node.find("BoardName")
            if node is not None:
                ref = node.get(f"{{{Doc.NS}}}ref")
                if ref:
                    try:
                        return Doc.extract_id(ref)
                    except Exception:
                        self.__control.logger.exception("board ID")
            return None

        @cached_property
        def frequency(self):
            """How long before term is up for renewal."""

            node = self.__node.find("TermRenewalFrequency")
            return Doc.get_text(node, "").strip()

        @cached_property
        def response_dates(self):
            """When the user responded to invitations for this board."""

            response_dates = []
            for node in self.__node.findall("ResponseDate"):
                response_date = Doc.get_text(node, "").strip()
                if response_date:
                    response_dates.append(response_date)
            return response_dates

        @cached_property
        def subgroups(self):
            """Sequence of strings for the names of the member's subgroups."""

            subgroups = set()
            for node in self.__node.findall("MemberOfSubgroup"):
                name = Doc.get_text(node, "").strip()
                if name:
                    subgroups.add(name)
            return subgroups


if __name__ == "__main__":
    "Let the script be loaded as a module."
    Control().run()
