#----------------------------------------------------------------------
# Report to display the Board Roster with or without assistant
# information.
#
# BZIssue::4909 - Board Roster Report Change
# BZIssue::4979 - Error in Board Roster Report
# BZIssue::5023 - Changes to Board Roster Report
# OCECDR-3720: [Summaries] Board Roster Summary Sheet - More Options
# JIRA::OCECDR-3812 - Name change (OCPL)
# Modified July 2015 as part of security tightening.
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi
import datetime
import lxml.etree as etree
import lxml.html
import time
from cdrapi import db
from html import escape as html_escape

#----------------------------------------------------------------------
# Don't give hackers any help, and don't throw more noise at the app
# scanner than necessary.
#----------------------------------------------------------------------
cdrcgi.REVEAL_DEFAULT = False
HACKER_MSG = "CGI parameter tampering detected"

#----------------------------------------------------------------------
# Columns available for the 'summary' version of the report.
#----------------------------------------------------------------------
class Column:
    def __init__(self, name, label, form_label=None, checked=False):
        self.name = name
        self.label = label
        self.form_label = form_label or label
        self.checked = checked
COLS = (
    Column("phone", "Phone", checked=True),
    Column("fax", "Fax"),
    Column("email", "Email", "E-mail", True),
    Column("cdr-id", "CDR-ID", "CDR ID"),
    Column("start-date", "Start Date"),
    Column("employee", "Gov. Empl.", "Government Employee"),
    Column("expertise", "Area of Exp.", "Areas of Expertise"),
    Column("subgroup", "Member Subgrp", "Membership in Subgroups"),
    Column("end-date", "Term End Date",
           "Term End Date (calculated using the term renewal frequency"),
    Column("affiliation", "Affil. Name", "Affiliations"),
    Column("mode", "Contact Mode"),
    Column("assistant-name", "Assist. Name", "Assistant Name"),
    Column("assistant-email", "Assist. Email", "Assistant E-mail")
)

#----------------------------------------------------------------------
# Initial variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
TITLE      = "PDQ Board Roster Report"
subtitle   = "Full or Selected PDQ Board Roster Address Information"
action     = "BoardRoster.py"
SUBMENU    = "Report Menu"
buttons    = ["Submit", SUBMENU, cdrcgi.MAINMENU]
dateString = time.strftime("%B %d, %Y")
filterType = {'summary':'name:PDQBoardMember Roster Summary',
             'full'   :'name:PDQBoardMember Roster'}


#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)


#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = db.connect(user="CdrGuest")
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail('Database connection failure: %s' % e)


#----------------------------------------------------------------------
# Display the request form used to specify the report options.
#----------------------------------------------------------------------
def show_form():
    boards = [("", "Pick a Board")] + getActiveBoards()
    form = cdrcgi.Page(TITLE, subtitle=subtitle, buttons=buttons,
                       action=action, session=session)
    form.add("<fieldset>")
    form.add(cdrcgi.Page.B.LEGEND("Select Board"))
    form.add_select("board", "PDQ Board", boards)
    form.add("</fieldset>")
    form.add("<fieldset>")
    form.add(cdrcgi.Page.B.LEGEND("Select Report Type"))
    form.add_radio("report-type", "Full", "full", wrapper=None, checked=True)
    form.add_radio("report-type", "Summary", "summary", wrapper=None)
    form.add('<fieldset id="full-options-block">')
    form.add(cdrcgi.Page.B.LEGEND("Full Report Options"))
    form.add_checkbox("full-opts", "Show All Contact Information", "other")
    form.add_checkbox("full-opts", "Show Subgroup Information", "subgroup")
    form.add_checkbox("full-opts", "Show Assistant Information", "assistant")
    form.add("</fieldset>")
    form.add('<fieldset id="columns">')
    form.add(cdrcgi.Page.B.LEGEND("Columns to Include"))
    for c in COLS:
        form.add_checkbox("columns", c.form_label, c.name, checked=c.checked)
    form.add("</fieldset>")
    form.add("<fieldset id='misc-options'>")
    form.add(cdrcgi.Page.B.LEGEND("Miscellanous Summary Report Options"))
    form.add_text_field("blank", "Extra Cols", value="0",
                      classes="blanks")
    form.add("</fieldset>")
    form.add_output_options("html")
    form.add("</fieldset>")
    form.add_css("input.blanks { width: 60px; }\n")
    form.add_css("select:hover { background-color: #ffc; }\n")
    form.add_script("""\
function check_columns(dummy) {}
function check_report_type(choice) {
    switch (choice) {
    case 'full':
        jQuery('#full-options-block').show();
        jQuery('#columns').hide();
        jQuery('#misc-options').hide();
        jQuery('#report-format-block').hide();
        break;
    case 'summary':
        jQuery('#full-options-block').hide();
        jQuery('#columns').show();
        jQuery('#misc-options').show();
        jQuery('#report-format-block').show();
        break;
    default:
        jQuery('#full-options-block').hide();
        jQuery('#columns').hide();
        jQuery('#misc-options').hide();
        jQuery('#report-format-block').hide();
        break;
    }
}
jQuery(function() {
    check_report_type(jQuery('input[name="report-type"]:radio:checked').val());
});
""")
    form.send()


#----------------------------------------------------------------------
# Look up title of a board, given its ID.
#----------------------------------------------------------------------
def getBoardName(id):
    try:
        cursor.execute("SELECT title FROM document WHERE id = ?", id)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail(HACKER_MSG)
        return cleanTitle(rows[0][0])
    except Exception:
        cdrcgi.bail("Database failure looking up PDQ board name")


#----------------------------------------------------------------------
# Remove cruft from a document title.
#----------------------------------------------------------------------
def cleanTitle(title):
    return title.split(";")[0].strip()


#----------------------------------------------------------------------
# Build a drop-down menu list for PDQ Boards.
#----------------------------------------------------------------------
def getActiveBoards():
    try:
        cursor.execute("""\
SELECT DISTINCT board.id, board.title
           FROM active_doc board
           JOIN query_term org_type
             ON org_type.doc_id = board.id
          WHERE org_type.path = '/Organization/OrganizationType'
            AND org_type.value IN ('PDQ Editorial Board',
                                   'PDQ Advisory Board')
       ORDER BY board.title""")
        return [(row[0], cleanTitle(row[1])) for row in cursor.fetchall()]
    except Exception as e:
        cdrcgi.bail('Database query failure: %s' % e)


#----------------------------------------------------------------------
# Get the information for the Board Manager
#----------------------------------------------------------------------
def getBoardManagerInfo(orgId):
    paths = (
        '/Organization/PDQBoardInformation/BoardManager',
        '/Organization/PDQBoardInformation/BoardManagerEmail',
        '/Organization/PDQBoardInformation/BoardManagerPhone'
    )
    query = db.Query("query_term", "path", "value").order("path")
    query.where(query.Condition("path", paths, "IN"))
    query.where(query.Condition("doc_id", orgId))
    try:
        rows = query.execute(cursor).fetchall()
        if len(rows) != 3:
            cdrcgi.bail("board manager information missing")
        return rows
    except Exception as e:
        cdrcgi.bail('Database query failure for BoardManager: %s' % e)


#----------------------------------------------------------------------
# This function creates the columns/column headings for the table.
# We're including all headings in a list to ensure a given sort order.
#----------------------------------------------------------------------
def makeColumns(cols, blankCols):
    nameWidth = 250
    colWidth  = 100
    columns = [cdrcgi.Report.Column('Name', width='%dpx' % nameWidth)]
    pageWidth = 1000
    for col in COLS:
        if col.name in cols:
            columns.append(cdrcgi.Report.Column(col.label))

    # Adding blank columns and adjusting the width to the number of
    # already existing columns
    # -------------------------------------------------------------
    if blankCols.count > 0:
        remainingWidth = pageWidth - nameWidth - (len(columns) - 1) * colWidth
        if remainingWidth > 0:
            blankWidth = remainingWidth / blankCols.count
        else:
            blankWidth = colWidth
        for col in range(blankCols.count):
            width = blankWidth
            if blankCols.widths:
                width = blankCols.widths[col]
            columns.append(cdrcgi.Report.Column(" ", width="%dpx" % width))

    return columns


# ----------------------------------------------------------------------
# Table post Process
# Add additional CSS
# ----------------------------------------------------------------------
def post(table, page):
    page.add_css("td.footer { background-color: white; font-weight: bold; }")
    page.add_css("table.report { border-collapse: collapse;}\n")
    page.add_css(".report td, .report th { border: 1px black solid; }\n")
    page.add_css(".report td.footer { border: none; }\n")

# ----------------------------------------------------------------------
# Callback function to format multiple email addresses in one cell
# for the HTML output
# ----------------------------------------------------------------------
def email_format(cell, fmt):
    if fmt != "html":
        return None
    B = cdrcgi.Page.B
    td = B.TD()
    br = None
    for address in cell.values():
        a = B.A(address, href="mailto:%s" % address)
        if br is not None:
            td.append(br)
        td.append(a)
        br = B.BR()
    return td

#----------------------------------------------------------------------
# Control over optional blank columns to be added to the report.
# See help message in bail() method for details.
#----------------------------------------------------------------------
class BlankCols:
    def __init__(self, fields, report_format):
        self.count = 0
        self.widths = None
        blank = fields.getvalue("blank")
        if blank:
            pieces = blank.split(":")
            if len(pieces) > 2:
                self.bail()
            elif len(pieces) == 2:
                count, widths = pieces
            elif len(pieces) == 1:
                count, widths = pieces[0], ""
            if count:
                if not count.isdigit():
                    self.bail()
                self.count = int(count)
            if widths and report_format == "html":
                widths = widths.split()
                if len(widths) != self.count:
                    self.bail()
                self.widths = []
                for width in widths:
                    if not width.isdigit():
                        self.bail()
                    self.widths.append(int(width))
    def bail(self):
        cdrcgi.bail("""\
The 'Extra Cols' field's value must be an integer, specifying the number
of additional blank column to be added to the report. You can also append
a colon followed by a list of integers separated by spaces, one for
each of the blank columns to be added, specifying the width of that
column. Field widths for extra fields are only used when the report
format is HTML.""")

# *********************************************************************
# Main program starts here
# *********************************************************************

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
boardId = fields.getvalue("board")
if not boardId:
    show_form()
if not boardId.isdigit():
    cdrcgi.bail(HACKER_MSG)

#----------------------------------------------------------------------
# Get the rest of request variables.
#----------------------------------------------------------------------
boardId    = int(boardId)
flavor     = fields.getvalue("report-type") or "full"
full_opts  = set(fields.getlist("full-opts"))
cols       = set(fields.getlist("columns"))
report_fmt = fields.getvalue("format") or "html"
blankCols  = BlankCols(fields, report_fmt)
otherInfo  = "other" in full_opts and "Yes" or "No"
assistant  = "assistant" in full_opts and "Yes" or "No"
subgroup   = "subgroup" in full_opts and "Yes" or "No"

#----------------------------------------------------------------------
# Check for tampering.
#----------------------------------------------------------------------
cdrcgi.valParmVal(flavor, val_list=("full", "summary"), msg=HACKER_MSG)
cdrcgi.valParmVal(full_opts, val_list=("other", "subgroup", "assistant"),
                  msg=HACKER_MSG, empty_ok=True)
cdrcgi.valParmVal(cols, val_list=[c.name for c in COLS], msg=HACKER_MSG)
cdrcgi.valParmVal(report_fmt, val_list=("html", "excel"), msg=HACKER_MSG)

#----------------------------------------------------------------------
# Get the board's name from its ID.
#----------------------------------------------------------------------
boardName = getBoardName(boardId)

#----------------------------------------------------------------------
# Object for one PDQ board member.
#----------------------------------------------------------------------
class BoardMember:
    today = str(datetime.date.today())
    def __init__(self, docId, eic_start, eic_finish, term_start, name):
        """
        Seed the object with a few initial values

        Create the remaining members needed for the summary flavor or
        the report.
        """
        self.id = docId
        self.name = cleanTitle(name)
        self.isEic = (eic_start and eic_start <= BoardMember.today and
                      (not eic_finish or eic_finish > BoardMember.today))
        self.eicSdate = eic_start
        self.eicEdate = eic_finish
        self.termSdate = term_start

        # Get these values later, with finish_object().
        self.fullName = self.phone = self.fax = self.email = None
        self.governmentEmployee = self.honorariaDeclined = None
        self.specificPhone = self.specificFax = self.specificEmail = None
        self.termEndDate = None
        self.contactMode = self.assistantName = self.assistantEmail = None
        self.affiliations = []
        self.subgroups = []
        self.expertises = []
        self.finished = False

    def get_phones(self):
        """
        Assemble a de-duplcated list of email addresses
        """
        phones = []
        if self.phone:
            phones.append(self.phone)
        if self.specificPhone and self.specificPhone != self.phone:
            phones.append(self.specificPhone)
        return phones or ""

    def get_faxes(self):
        """
        Assemble a de-duplicated list of fax addresses
        """
        faxes = []
        if self.fax:
            faxes.append(self.fax)
        if self.specificFax and self.specificFax != self.fax:
            faxes.append(self.specificFax)
        return faxes or ""

    def get_emails(self):
        """
        Assemble the cell to show the email addresses

        De-duplicate and register a callback so we can render
        multiple addresses with hyperlink markup.
        """
        emails = []
        if self.email:
            emails.append(self.email)
        if self.specificEmail:
            se = self.specificEmail
            if not self.email or self.email.lower() != se.lower():
                emails.append(se)
        if not emails:
            return ""
        return cdrcgi.Report.Cell(emails, callback=email_format)

    def get_employee_status(self):
        """
        Format the cell indicating whether the member is a fed

        Add a footnote for non-employees who have declined the
        honariariam to which they are entitled.
        """
        status = self.governmentEmployee or "Unknown"
        if status == "No" and self.honorariaDeclined == "Yes":
            return "No^*"
        return status

    def make_row(self, cols, blankCols):
        """
        Assemble an array of cells, based on which columns are requested
        """
        self.finish_object()
        row = [cdrcgi.Report.Cell(self.fullName, bold=True)]
        if "phone" in cols:
            row.append(self.get_phones())
        if "fax" in cols:
            row.append(self.get_faxes())
        if "email" in cols:
            row.append(self.get_emails())
        if "cdr-id" in cols:
            row.append(self.id)
        if "start-date" in cols:
            row.append(self.termSdate)
        if "employee" in cols:
            row.append(self.get_employee_status())
        if "expertise" in cols:
            row.append(self.expertises or "")
        if "subgroup" in cols:
            row.append(self.subgroups or "")
        if "end-date" in cols:
            row.append(cdrcgi.Report.Cell(self.termEndDate or "",
                       classes=("emphasis", "center")))
        if "affiliation" in cols:
            row.append(self.affiliations or "")
        if "mode" in cols:
            row.append(self.contactMode or "")
        if "assistant-name" in cols:
            row.append(self.assistantName or "")
        if "assistant-email" in cols:
            if self.assistantEmail:
                url = "mailto:%s" % self.assistantEmail
                row.append(cdrcgi.Report.Cell(self.assistantEmail, href=url))
            else:
                row.append("")
        for col in range(blankCols.count):
            row.append("")
        return row

    def parse(self, fragments):
        """
        Extract name and contact info from HTML fragments
        """
        nodes = lxml.html.fragments_fromstring(fragments)
        for node in nodes:
            try:
                if node.tag == "b":
                    self.fullName = node.text
                elif node.tag == "table":
                    for child in node.findall("tr/td/phone"):
                        self.phone = child.text
                    for child in node.findall("tr/td/fax"):
                        self.fax = child.text
                    for child in node.findall("tr/td/email"):
                        self.email = child.text
            except:
                # Ignore non-element nodes (e.g., "Inactive - ")
                pass

    def finish_object(self):
        """
        Find the rest of the information needed for the summary report
        """
        if self.finished:
            return
        cursor.execute("SELECT xml FROM document WHERE id = ?", self.id)
        root = etree.XML(cursor.fetchall()[0][0].encode("utf-8"))
        aoe = sgrp = termEndDate = aName = cMode = asName = asEmail = None
        for node in root:
            if node.tag == "BoardMembershipDetails":
                for child in node:
                    if child.tag == "AreaOfExpertise":
                        self.expertises.append(child.text)
                    elif child.tag == "MemberOfSubgroup":
                        self.subgroups.append(child.text)
                    elif child.tag == "TermRenewalFrequency":
                        # Need to calculate the term end date from the
                        # start date and renewal frequency
                        # --------------------------------------------
                        termRenewal = child.text
                        frequency = {'Every year':1,
                                     'Every two years':2}
                        year = datetime.timedelta(365)

                        try:
                            if self.termSdate:
                                termStart = datetime.datetime.strptime(
                                                 self.termSdate, '%Y-%m-%d')
                                termEnd = (termStart +
                                             frequency[termRenewal] * year)
                                self.termEndDate = termEnd.strftime('%Y-%m-%d')
                        except:
                            cdrcgi.bail('Invalid date format on ' +
                                        'TermStartDate for: %s - %s' % (
                                         self.fullName, self.termSdate))
            elif node.tag == "Affiliations":
                for child in node.findall("Affiliation/AffiliationName"):
                    self.affiliations.append(child.text)
            elif node.tag == "BoardMemberContactMode":
                self.contactMode = node.text
            elif node.tag == "BoardMemberAssistant":
                for child in node:
                    if child.tag == "AssistantName":
                        self.assistantName = child.text
                    elif child.tag == "AssistantEmail":
                        self.assistantEmail = child.text
            elif node.tag == "GovernmentEmployee":
                self.governmentEmployee = node.text
                self.honorariaDeclined = node.get("HonorariaDeclined")
            elif node.tag == "BoardMemberContact":
                for child in node.findall("SpecificBoardMemberContact/*"):
                    if child.tag == "BoardContactFax":
                        self.specificFax = child.text
                    if child.tag == "BoardContactEmail":
                        self.specificEmail = child.text
                    if child.tag == "BoardContactPhone":
                        self.specificPhone = child.text
        self.finished = True
    def __lt__(self, other):
        """
        Sort editors-in-chief before others, subgroup by name
        """
        a = True if self.isEic else False, self.name.upper()
        b = True if other.isEic else False, other.name.upper()
        return a < b

#----------------------------------------------------------------------
# Select the list of board members associated to a board (passed in
# by the selection of the user) along with start/end dates.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
 SELECT DISTINCT member.doc_id, eic_start.value, eic_finish.value,
                 term_start.value, person_doc.title
            FROM query_term member
            JOIN query_term curmemb
              ON curmemb.doc_id = member.doc_id
             AND LEFT(curmemb.node_loc, 4) = LEFT(member.node_loc, 4)
            JOIN query_term person
              ON person.doc_id = member.doc_id
            JOIN document person_doc
              ON person_doc.id = person.doc_id
 LEFT OUTER JOIN query_term eic_start
              ON eic_start.doc_id = member.doc_id
             AND LEFT(eic_start.node_loc, 4) = LEFT(member.node_loc, 4)
             AND eic_start.path   = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/EditorInChief/TermStartDate'
 LEFT OUTER JOIN query_term eic_finish
              ON eic_finish.doc_id = member.doc_id
             AND LEFT(eic_finish.node_loc, 4) = LEFT(member.node_loc, 4)
             AND eic_finish.path  = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/EditorInChief/TermEndDate'
 LEFT OUTER JOIN query_term term_start
              ON term_start.doc_id = member.doc_id
             AND LEFT(term_start.node_loc, 4) = LEFT(member.node_loc, 4)
             AND term_start.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/TermStartDate'
           WHERE member.path  = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/BoardName/@cdr:ref'
             AND curmemb.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/CurrentMember'
             AND person.path  = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'
             AND curmemb.value = 'Yes'
             AND person_doc.active_status = 'A'
             AND member.int_val = ?
""", boardId)
    rows = cursor.fetchall()
    boardMembers = []
    boardIds     = []
    for docId, eic_start, eic_finish, term_start, name in rows:
        boardMembers.append(BoardMember(docId, eic_start, eic_finish,
                                        term_start, name))
        boardIds.append(docId)
    boardMembers.sort()

except Exception as e:
    cdrcgi.bail('Database query failure: %s' % e)


if flavor == 'full':
    # ---------------------------------------------------------------
    # Create the HTML Output Page
    # ---------------------------------------------------------------
    html = """\
<!DOCTYPE html>
<html>
 <head>
  <title>PDQ Board Member Roster Report - %s</title>
  <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>
  <style type='text/css'>
   h1       { font-family: Arial, sans-serif;
              font-size: 16pt;
              text-align: center;
              font-weight: bold; }
   h2       { font-family: Arial, sans-serif;
              font-size: 14pt;
              text-align: center;
              font-weight: bold; }
   p        { font-family: Arial, sans-serif;
              font-size: 12pt; }
   #summary td, #summary th
            { border: 1px solid black; }
   #hdg     { font-family: Arial, sans-serif;
              font-size: 16pt;
              font-weight: bold;
              text-align: center;
              padding-bottom: 20px;
              border: 0px; }
   #summary { border: 0px; }

   /* The Board Member Roster information is created via a global */
   /* template for Persons.  The italic display used for the QC   */
   /* report does therefore need to be suppressed here.           */
   /* ----------------------------------------------------------- */
   I        { font-family: Arial, sans-serif; font-size: 12pt;
              font-style: normal; }
   span.SectionRef { text-decoration: underline; font-weight: bold; }

   .theader { background-color: #CFCFCF; }
   .name    { font-weight: bold;
              vertical-align: top; }
   .phone, .email, .fax, .cdrid
            { vertical-align: top; }
   .blank   { width: 100px; }
   #main    { font-family: Arial, Helvetica, sans-serif;
              font-size: 12pt; }
  </style>
 </head>
 <body id="main">
""" % html_escape(boardName)

    html += """
   <h1>%s<br><span style="font-size: 12pt">%s</span></h1>
""" % (html_escape(boardName), dateString)
else:
    otherInfo = assistant = "No"

# ------------------------------------------------------------------------
# Collect all of the data for the board members
# ------------------------------------------------------------------------
for boardMember in boardMembers:
    response = cdr.filterDoc('guest',
                             ['set:Denormalization PDQBoardMemberInfo Set',
                              'name:Copy XML for Person 2',
                              filterType[flavor]],
                             boardMember.id,
                             parm = [['otherInfo', otherInfo],
                                     ['assistant', assistant],
                                     ['subgroup',  subgroup],
                                     ['eic',
                                      boardMember.isEic and 'Yes' or 'No']])
    if isinstance(response, (str, bytes)):
        cdrcgi.bail("%s: %r" % (boardMember.id, response))

    # If we run the full report we just attach the resulting HTML
    # snippets to the previous output.
    # For the summary sheet we still need to extract the relevant
    # information from the HTML snippet
    #
    # We need to wrap each person in a table in order to prevent
    # page breaks within address blocks after the conversion to
    # MS-Word.
    # -----------------------------------------------------------
    if flavor == 'full':
        cell_value = response[0]
        html += """
        <table width='100%%'>
         <tr>
          <td>%s<td>
         </tr>
        </table>""" % cell_value
    else:
        boardMember.parse(response[0])

# Create the HTML table for the summary sheet
# -------------------------------------------
if flavor == 'summary':
    rows = [member.make_row(cols, blankCols) for member in boardMembers]
    if "employee" in cols:
        rows.append([cdrcgi.Report.Cell("* - Honoraria Declined",
                                        colspan=len(cols) + 1,
                                        classes="footer")])
    caption = [boardName, dateString]
    columns = makeColumns(cols, blankCols)
    table = cdrcgi.Report.Table(columns, rows, caption=caption,
                                html_callback_post=post)
    report = cdrcgi.Report('%s - %s' % (boardName, dateString), [table])
    report.send(fields.getvalue("format"))


# At the end collect the information for the board manager
# --------------------------------------------------------
if flavor == 'full':
    boardManagerInfo = getBoardManagerInfo(boardId)

    html += """
      <br>
      <table width='100%%'>
       <tr>
        <td>
         <b><u>Board Manager Information</u></b><br>
         <b>%s</b><br>
         Office of Cancer Content<br>
         Office of Communications and Public Liaison<br>
         National Cancer Institute<br>
         9609 Medical Center Drive, MSC 9760<br>
         Rockville, MD 20850<br><br>
         <table border="0" width="100%%" cellspacing="0" cellpadding="0">
          <tr>
           <td width="35%%">Phone</td>
           <td width="65%%">%s</td>
          </tr>
          <tr>
           <td>Fax</td>
           <td>240-276-7679</td>
          </tr>
          <tr>
           <td>Email</td>
           <td><a href="mailto:%s">%s</a></td>
          </tr>
         </table>
           </td>
       </tr>
      </table>
     </body>
    </html>
    """ % (boardManagerInfo and boardManagerInfo[0][1] or 'No Board Manager',
           boardManagerInfo and boardManagerInfo[2][1] or 'TBD',
           boardManagerInfo and boardManagerInfo[1][1] or 'TBD',
           boardManagerInfo and boardManagerInfo[1][1] or 'TBD')

    # The users don't want to display the country if it's the US.
    # Since the address is build by a common address module we're
    # better off removing it in the final HTML output
    # ------------------------------------------------------------
    cdrcgi.sendPage(html.replace('U.S.A.<br>', ''))
