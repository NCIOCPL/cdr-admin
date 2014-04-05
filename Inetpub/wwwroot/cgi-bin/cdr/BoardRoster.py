#----------------------------------------------------------------------
#
# $Id$
#
# Report to display the Board Roster with or without assistant
# information.
#
# BZIssue::4909 - Board Roster Report Change
# BZIssue::4979 - Error in Board Roster Report
# BZIssue::5023 - Changes to Board Roster Report
# OCECDR-3720: [Summaries] Board Roster Summary Sheet - More Options 
# 
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, time, lxml.etree as etree
import datetime, lxml.html

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
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])


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
    form.add('<fieldset id="full-options-block" class="hidden">')
    form.add(cdrcgi.Page.B.LEGEND("Full Report Options"))
    form.add_checkbox("full-opts", "Show All Contact Information", "other")
    form.add_checkbox("full-opts", "Show Subgroup Information", "subgroup")
    form.add_checkbox("full-opts", "Show Assistant Information", "assistant")
    form.add("</fieldset>")
    form.add('<fieldset id="columns" class="hidden">')
    form.add(cdrcgi.Page.B.LEGEND("Columns to Include"))
    form.add_checkbox("columns", "Phone", "phone", checked=True)
    form.add_checkbox("columns", "Fax", "fax")
    form.add_checkbox("columns", "E-mail", "email", checked=True)
    form.add_checkbox("columns", "CDR ID", "cdr-id")
    form.add_checkbox("columns", "Start Date", "start-date")
    form.add_checkbox("columns", "Government Employee", "employee")
    form.add_checkbox("columns", "Areas of Expertise", "expertise")
    form.add_checkbox("columns", "Membership in Subgroups", "subgroup")
    termEnd = "Term End Date (calculated using the term renewal frequency)"
    form.add_checkbox("columns", "%s" % termEnd, "end-date")
    form.add_checkbox("columns", "Affiliations", "affiliation")
    form.add_checkbox("columns", "Contact Mode", "mode")
    form.add_checkbox("columns", "Assistant Name", "assistant-name")
    form.add_checkbox("columns", "Assistant E-mail", "assistant-email")
    form.add("</fieldset>")
    form.add("<fieldset id='misc-options' class='hidden'>")
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
            cdrcgi.bail('Failure looking up title for CDR%s' % id)
        return cleanTitle(rows[0][0])
    except Exception, e:
        cdrcgi.bail('Looking up board title: %s' % str(e))


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
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])


#----------------------------------------------------------------------
# Get the information for the Board Manager
#----------------------------------------------------------------------
def getBoardManagerInfo(orgId):
    try:
        cursor.execute("""\
SELECT path, value
 FROM query_term
 WHERE path like '/Organization/PDQBoardInformation/BoardManager%%'
 AND   doc_id = ?
 ORDER BY path""", orgId)

        return cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure for BoardManager: %s' % info[1][0])


#----------------------------------------------------------------------
# This function creates the columns/column headings for the table.
# We're including all headings in a list to ensure a given sort order.
#----------------------------------------------------------------------
def makeColumns(cols):
    nameWidth = 250
    colWidth  = 100
    columns = [cdrcgi.Report.Column('Name', width='%dpx' % nameWidth)]
    pageWidth = 1000
    for label, field in (
        ("Phone", "phone"), 
        ("Fax", "fax"), 
        ("Email", "email"), 
        ("CDR-ID", "cdr-id"), 
        ("Start Date", "start-date"), 
        ("Gov. Empl.", "employee"),
        ("Area of Exp.", "expertise"), 
        ("Member Subgrp", "subgroup"),
        ("Term End Date", "end-date"),
        ("Affil. Name", "affiliation"),
        ("Contact Mode", "mode"),
        ("Assist. Name", "assistant-name"),
        ("Assist. Email", "assistant-email")
    ):
        if field in cols:
            columns.append(cdrcgi.Report.Column(label))
    
    # Adding blank columns and adjusting the width to the number of
    # already existing columns
    # -------------------------------------------------------------
    if extra > 0:
        remainWidth = pageWidth - nameWidth - (len(columns) - 1) * colWidth
        if remainWidth > 0:
            blankWidth = remainWidth / extra
        else:
            blankWidth = colWidth
        for col in range(extra):
            width = colWidths and int(colWidths[col]) or blankWidth
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


# *********************************************************************
# Main program starts here
# *********************************************************************

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
boardId = fields.getvalue("board")
if not boardId:
    show_form()

#----------------------------------------------------------------------
# Get the rest of request variables.
#----------------------------------------------------------------------
boardId    = int(boardId)
flavor     = fields.getvalue("report-type") or "full"
full_opts  = set(fields.getlist("full-opts"))
cols       = set(fields.getlist("columns"))
blankInfo  = fields.getvalue("blank")  or '0'
otherInfo  = "other" in full_opts and "Yes" or "No"
assistant  = "assistant" in full_opts and "Yes" or "No"
subgroup   = "subgroup" in full_opts and "Yes" or "No"

# If blank columns are specified with a width specifier extract 
# the width and make sure we have enough values for each column
# The width would be specified in pixels with values separated
# by spaces, for example  '3:20 40 60' will add 3 columns with 
# a width of 20px, 40px, and 60px respectively.
# -------------------------------------------------------------
blankCol = blankInfo.split(':')[0]
extra = int(blankCol)
colWidths = None

# This test only makes sense for non-Excel output of the summary sheet
# --------------------------------------------------------------------
if flavor == 'summary' and len(blankInfo.split(':')) == 2 \
                       and fields.getvalue("format") == 'html':
    colWidths = blankInfo.split(':')[1].split()
    if len(colWidths) < extra:
        cdrcgi.bail('Not enough values for column widths specified!')

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

    def make_row(self, cols, extra):
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
        for col in range(extra):
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
    def __cmp__(self, other):
        """
        Sort editors-in-chief before others, subgroup by name
        """
        if self.isEic == other.isEic:
            return cmp(self.name.upper(), other.name.upper())
        elif self.isEic:
            return -1
        return 1
    
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
""", boardId, timeout = 300)
    rows = cursor.fetchall()
    boardMembers = []
    boardIds     = []
    for docId, eic_start, eic_finish, term_start, name in rows:
        boardMembers.append(BoardMember(docId, eic_start, eic_finish, 
                                               term_start, name))
        boardIds.append(docId)
    boardMembers.sort()

except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])


if flavor == 'full':
    # ---------------------------------------------------------------
    # Create the HTML Output Page
    # ---------------------------------------------------------------
    html = """\
<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
                      'http://www.w3.org/TR/html4/loose.dtd'>
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
""" % boardName

    html += """
   <h1>%s<br><span style="font-size: 12pt">%s</span></h1>
""" % (boardName, dateString)   
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
    if type(response) in (str, unicode):
        cdrcgi.bail("%s: %s" % (boardMember.id, response))

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
        html += u"""
        <table width='100%%'>
         <tr>
          <td>%s<td>
         </tr>
        </table>""" % unicode(response[0], 'utf-8')
    else:
        boardMember.parse(response[0])
 
# Create the HTML table for the summary sheet
# -------------------------------------------
if flavor == 'summary':
    rows = [member.make_row(cols, extra) for member in boardMembers]
    if "employee" in cols:
        rows.append([cdrcgi.Report.Cell("* - Honoraria Declined", 
                                        colspan=len(cols) + 1,
                                        classes="footer")])
    caption = [boardName, dateString]
    columns = makeColumns(cols)
    table = cdrcgi.Report.Table(columns, rows, caption=caption,
                                html_callback_post=post)
    report = cdrcgi.Report('%s - %s' % (boardName, dateString), [table])
    report.send(fields.getvalue("format"))


# At the end collect the information for the board manager
# --------------------------------------------------------
if flavor == 'full':
    boardManagerInfo = getBoardManagerInfo(boardId)

    html += u"""
      <br>
      <table width='100%%'>
       <tr>
        <td>
         <b><u>Board Manager Information</u></b><br>
         <b>%s</b><br>
         Office of Cancer Content Management (OCCM)<br>
         Office of Communications and Education<br>
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
