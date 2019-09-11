#----------------------------------------------------------------------
# Report to display the Board Roster with or without assistant
# information.
#
# BZIssue::4673 - Changes to PDQ Board Roster report.
# BZIssue::5060 - [Summaries] Changes to Combined Board Roster Report
#                 Adding summary sheet options to the program
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, time, operator
import sys
import lxml.html

# ---------------------------------------------------------------------
# Class to collect all of the information for a single board member
# ---------------------------------------------------------------------
class BoardMemberInfo:
    def __init__(self, person, html):
        self.boardMemberID  = person[0]
        self.boardID   = person[1]
        self.boardName = person[2]
        self.startDate = person[3]
        self.govEmpl   = person[5]
        self.phone     = ''
        self.fax       = ''
        self.email     = ''

        myHtml = lxml.html.fromstring(html)
        self.boardMemberName = myHtml.find('b').text
        table = myHtml.find('table')
        try:
            for element in table.iter():
                if element.tag == 'phone':
                    self.phone = element.text
                elif element.tag == 'fax':
                    self.fax   = element.text
                elif element.tag == 'email':
                    self.email = element.text
        except:
            pass


#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
boardType  = fields and fields.getvalue("board")  or None
sortType   = fields and fields.getvalue("sort")  or None
otherInfo  = fields and fields.getvalue("oinfo") or 'Yes'
assistant  = fields and fields.getvalue("ainfo") or 'Yes'
flavor     = fields and fields.getvalue("sheet") and 'summary' or 'full'
#if flavor == 'on':  flavor == 'summary'
boardInfo  = fields and fields.getvalue("binfo") and 'Yes' or 'No'
phoneInfo  = fields and fields.getvalue("pinfo") and 'Yes' or 'No'
faxInfo    = fields and fields.getvalue("finfo") and 'Yes' or 'No'
emailInfo  = fields and fields.getvalue("einfo") and 'Yes' or 'No'
cdrIDInfo  = fields and fields.getvalue("cinfo") and 'Yes' or 'No'
dateInfo   = fields and fields.getvalue("dinfo") and 'Yes' or 'No'
geInfo     = fields and fields.getvalue("govemp") and 'Yes' or 'No'
blank      = fields and fields.getvalue("blank") and 'Yes' or 'No'

# List to define the column headings and identify which columns to be
# displayed
# -------------------------------------------------------------------
columns = [('Board Name',boardInfo),
           ('Phone', phoneInfo), ('Fax', faxInfo),
           ('Email', emailInfo), ('CDR-ID', cdrIDInfo),
           ('Start Date', dateInfo), ('Gov. Empl', geInfo), ('Blank', blank)]

rptType    = fields and fields.getvalue("rpttype") or 'html'
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
title      = u"PDQ Board Roster Report"
instr      = u"Report on PDQ Board Roster"
script     = u"BoardRosterFull.py"
SUBMENU    = u"Report Menu"
buttons    = ("Submit", SUBMENU, cdrcgi.MAINMENU)
header     = cdrcgi.header(title, title, instr, script, buttons,
                           method = 'GET',
                           stylesheet = """
    <script type='text/javascript'>
     function doSummarySheet(box) {
         if (box == 'summary')
             {
             if (document.getElementById('summary').checked == true)
                 {
                 document.getElementById('summary').checked = true;
                 }
             else
                 {
                 document.getElementById('summary').checked = false;
                 }
             }
         else
             {
             document.getElementById('summary').checked = true;
             }

         /*
         document.getElementById('contact').checked   = false;
         document.getElementById('assistant').checked = false;
         document.getElementById('subgroup').checked  = false;
         */
         var form = document.forms[0];
         {
             form.sheet.value = form.sheet.checked ? 'summary' : 'full';
             form.binfo.value = form.binfo.checked ? 'Yes' : 'No';
             form.pinfo.value = form.pinfo.checked ? 'Yes' : 'No';
             form.finfo.value = form.finfo.checked ? 'Yes' : 'No';
             form.einfo.value = form.einfo.checked ? 'Yes' : 'No';
             form.cinfo.value = form.cinfo.checked ? 'Yes' : 'No';
             form.dinfo.value = form.dinfo.checked ? 'Yes' : 'No';
             form.blank.value = form.blank.checked ? 'Yes' : 'No';
             form.govemp.value = form.govemp.checked ? 'Yes' : 'No';
         }
     }
    </script>
    <style type="text/css">
     td       { font-size: 12pt; }
     .label   { font-weight: bold; }
     .label2  { font-size: 11pt;
                font-weight: bold; }
     .select:hover { background-color: #FFFFCC; }
     .grey    {background-color: #BEBEBE; }
     .topspace { margin-top: 24px; }

    </style>
""")

dateString = time.strftime(u"%B %d, %Y")

filterType= {'summary':'name:PDQBoardMember Roster Summary',
             'excel'  :'name:PDQBoardMember Roster Excel',
             'full'   :'name:PDQBoardMember Roster'}
#allRows   = []

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
except cdrdb.Error as info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

# ---------------------------------------------------------------------
# Counting how many columns are to be printed. We need to know this
# value for the colspan attribute of the table to be created.
# ---------------------------------------------------------------------
def countCols(cols):
    k = 0
    for header, display in cols:
        if display == 'Yes': k += 1
    return k


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
    except Exception as e:
        cdrcgi.bail('Looking up board title: %s' % str(e))

#----------------------------------------------------------------------
# Remove cruft from a document title.
#----------------------------------------------------------------------
def cleanTitle(title):
    semicolon = title.find(';')
    if semicolon != -1:
        title = title[:semicolon]
    return title.strip()

#----------------------------------------------------------------------
# Build a picklist for PDQ Boards.
# This function serves two purposes:
# a)  create the picklist for the selection of the board
# b)  create a dictionary in subsequent calls to select the board
#     ID based on the board selected in the first call.
#----------------------------------------------------------------------
def getBoardPicklist(boardType):
    try:
        cursor.execute("""\
SELECT DISTINCT board.id, board.title
           FROM document board
           JOIN query_term org_type
             ON org_type.doc_id = board.id
          WHERE org_type.path = '/Organization/OrganizationType'
            AND org_type.value IN ('PDQ %s Board')
       ORDER BY board.title""" % boardType)
        rows = cursor.fetchall()
        allBoards = {}
        for id, title in rows:
            if id != 256088:
                allBoards[id] = cleanTitle(title)
    except cdrdb.Error as info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    return allBoards


# -------------------------------------------------
# Create the table row for a specific person
# -------------------------------------------------
def addTableRow(person, columns):
    tableRows = {}
    for colHeader, colDisplay in columns:
        if colHeader == 'Board Name':
            tableRows[colHeader] = person.boardName
        elif colHeader == 'Phone':
            tableRows[colHeader] = person.phone
        elif colHeader == 'Fax':
            tableRows[colHeader] = person.fax
        elif colHeader == 'Email':
            tableRows[colHeader] = person.email
        elif colHeader == 'CDR-ID':
            tableRows[colHeader] = person.boardMemberID
        elif colHeader == 'Start Date':
            tableRows[colHeader] = person.startDate
        elif colHeader == 'Gov. Empl':
            tableRows[colHeader] = person.govEmpl
        elif colHeader == 'Blank':
            tableRows[colHeader] = ''

    htmlRow = u"""\
       <tr>
        <td>%s</td>""" % person.boardMemberName

    for colHeader, colDisplay in columns:
        if colDisplay == 'Yes' and colHeader == 'Email':
            htmlRow += u"""
        <td class="email">
         <a href="mailto:%s">%s</a>
        </td>""" % (tableRows[colHeader], tableRows[colHeader])
        elif colDisplay == 'Yes' and colHeader == 'Blank':
            htmlRow += u"""
        <td class="blank">&nbsp;</td>"""
        elif colDisplay == 'Yes':
            htmlRow += u"""
        <td>%s</td>""" % tableRows[colHeader]

    htmlRow += u"""
       </tr>"""
    return htmlRow


#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not boardType:
    form   = u"""\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <TABLE border='0'>
       <TR>
        <TD ALIGN='right'><B>PDQ Boards included:&nbsp;</B></TD>
        <TD>
        <SELECT NAME='board'>
        <OPTION SELECTED value='Editorial'>PDQ Editorial Boards</OPTION>
        <OPTION value='Advisory'>PDQ Editorial Advisory Boards</OPTION>
        </SELECT>
        </TD>
       </TR>
       <TR>
        <TD ALIGN='right'><B>Sort report by:&nbsp;</B></TD>
        <TD>
        <SELECT NAME='sort'>
        <OPTION SELECTED value='Member'>Member Name</OPTION>
        <OPTION value='Board'>Member Name (group by Board)</OPTION>
        </SELECT>
        </TD>
       </TR>

   <tr>
    <td colspan="2">
     <div style="height: 10px"> </div>
    </td>
   </tr>
   <tr>
    <td> </td>
    <td class="grey">
     <div style="height: 10px"> </div>
     <input TYPE='checkbox' NAME='sheet' id='summary'
            onclick='javascript:doSummarySheet("summary")'>
      <label for="summary" class="select">
       <strong>Create Summary Sheet</strong>
      </label>
     <table>
      <tr>
       <th><span style="margin-left: 20px"> </span></th>
       <th class="label2">Include Columns</th>
      <tr>
       <td><span style="margin-left: 20px"> </span></td>
       <td class="select">
        <input type='checkbox' name='binfo'
               onclick='javascript:doSummarySheet()' id='E1' CHECKED>
        <label for="E1">Board Name</label>
       </td>
      </tr>
      <tr>
       <td><span style="margin-left: 20px"> </span></td>
       <td class="select">
        <input type='checkbox' name='pinfo'
               onclick='javascript:doSummarySheet()' id='E2'>
        <label for="E2">Phone</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='finfo'
               onclick='javascript:doSummarySheet()' id='E3'>
        <label for="E3">Fax</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='einfo'
               onclick='javascript:doSummarySheet()' id='E4'>
        <label for="E4">Email</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='cinfo'
               onclick='javascript:doSummarySheet()' id='E5'>
        <label for="E5">CDR-ID</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='dinfo'
               onclick='javascript:doSummarySheet()' id='E6'>
        <label for="E6">Start Date</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='govemp'
               onclick='javascript:doSummarySheet()' id='E7'>
        <label for="E7">Government Employee</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='blank'
               onclick='javascript:doSummarySheet()' id='E8'>
        <label for="E8">Blank Column</label>
       </td>
      </tr>

       </TABLE>
      </FORM>
     </BODY>
    </HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Get the board's name from its ID.
#----------------------------------------------------------------------
allBoards = getBoardPicklist(boardType)
boardIds  = allBoards.keys()

#----------------------------------------------------------------------
# Main SELECT query
#----------------------------------------------------------------------
try:
    cursor.execute("""\
 SELECT DISTINCT member.doc_id, member.int_val,
                 term_start.value, person_doc.title, ge.value
            FROM query_term member
            JOIN query_term curmemb
              ON curmemb.doc_id = member.doc_id
             AND LEFT(curmemb.node_loc, 4) = LEFT(member.node_loc, 4)
            JOIN query_term person
              ON person.doc_id = member.doc_id
            JOIN document person_doc
              ON person_doc.id = person.doc_id
            JOIN query_term ge
              ON ge.doc_id = person_doc.id
             AND ge.path = '/PDQBoardMemberInfo/GovernmentEmployee'
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
             AND member.int_val in (%s)
           ORDER BY member.int_val""" %
                      ", ".join(["%s" % x for x in boardIds]), timeout = 300)
    rows = cursor.fetchall()
    cursor.close()
    boardMembers = []

    for docId, boardId, term_start, name, ge in rows:
        boardName = getBoardName(boardId)
        boardMembers.append([docId, boardId, boardName, term_start, name, ge])

except cdrdb.Error as info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

# Sorting the list alphabetically by board member
# or by board member grouped by board name
# -----------------------------------------------
if sortType == 'Member':
    getcount = operator.itemgetter(4)
    sortedMembers = sorted(boardMembers, key=getcount)
else:
    sortedMembers = sorted(boardMembers, key=operator.itemgetter(2, 4))

# We're creating two flavors of the report here: excel and html
# (but users decided later not to use the Excel report anymore)
# -------------------------------------------------------------
if rptType == 'html':
    # ---------------------------------------------------------------
    # Create the HTML Output Page
    # ---------------------------------------------------------------
    html = u"""\
    <!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
                          'http://www.w3.org/TR/html4/loose.dtd'>
    <HTML>
     <HEAD>
      <TITLE>PDQ Board Member Roster Report - %s</title>
      <META http-equiv='Content-Type' content='text/html; charset=UTF-8'>
      <STYLE type='text/css'>
       H1       { font-family: Arial, sans-serif;
                  font-size: 16pt;
                  text-align: center;
                  font-weight: bold; }
       H2       { font-family: Arial, sans-serif;
                  font-size: 14pt;
                  text-align: center;
                  font-weight: bold; }
       P        { font-family: Arial, sans-serif;
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
       SPAN.SectionRef { text-decoration: underline; font-weight: bold; }

       .theader { background-color: #CFCFCF; }
       .name    { font-weight: bold;
                  vertical-align: top; }
       .phone, .email, .fax, .cdrid
                { vertical-align: top; }
       .blank   { width: 100px; }
       .bheader { font-family: Arial, sans-serif;
                  font-size: 14pt;
                  font-weight: bold; }
       #main    { font-family: Arial, Helvetica, sans-serif;
                  font-size: 12pt; }
      </STYLE>
     </HEAD>
     <BODY id="main">
       <H1>All %s Boards<br>
    """ % (boardType, boardType)

    # Adjusting the report title depending on the input values
    # --------------------------------------------------------
    if sortType == 'Member':
        html += u"""
       <span style="font-size: 12pt">by Member</span><br>
    """
    else:
        html += u"""
       <span style="font-size: 12pt">by Board and Member</span><br>
    """
    html += u"""
       <span style="font-size: 12pt">%s</span></H1>
    """ % (dateString)

    boardTitle = None
    lastBoardTitle = None

    # Need to create the table wrapper for the summary sheet
    # We always print at least the board member name as a column
    # -----------------------------------------------------------
    if flavor == 'summary':
        html += u"""
      <table id="summary" cellspacing="0" cellpadding="5">
       <tr class="theader">
        <th class="thcell">Name</th>"""

        # Add column headings
        # -------------------
        for colHeader, colDisplay in columns:
            if colDisplay == 'Yes':
                html += u"""
        <th class="thcell">%s</th>""" % colHeader
        html += """
       </tr>
"""

    # Loop through the list of sorted members to get the address info
    # ---------------------------------------------------------------
    for boardMember in sortedMembers:
        boardTitle = boardMember[2]
        response = cdr.filterDoc('guest',
                                 ['set:Denormalization PDQBoardMemberInfo Set',
                                  'name:Copy XML for Person 2',
                                  filterType[flavor]],
                                  boardMember[0],
                                  parm = [['otherInfo', otherInfo],
                                          ['assistant', assistant]])
        if type(response) in (str, unicode):
            cdrcgi.bail("%s: %s" % (boardMember[0], response))

        # For the report we're just attaching the resulting HTML
        # snippets to the previous output.
        #
        # We need to wrap each person in a table in order to prevent
        # page breaks within address blocks after the convertion to
        # MS-Word.
        # -----------------------------------------------------------
        if flavor == 'full':
            # If we're grouping by board we need to display the board name
            # as a title.
            # ------------------------------------------------------------
            if not sortType == 'Member' and not lastBoardTitle == boardTitle:
                html += u"""
            <br>
            <span class="bheader">%s</span>
            <br>
            """ % (boardTitle)

            # If we're not grouping by board we need to print the board for
            # each board member
            # -------------------------------------------------------------
            if sortType == 'Member':
                html += u"""
                <table width='100%%'>
                 <tr>
                  <td>%s<span style="font-style: italic">%s</span><br><br><td>
                 </tr>
                </table>""" % (unicode(response[0], 'utf-8'), boardMember[2])
            else:
                html += u"""
                <table width='100%%'>
                 <tr>
                  <td>%s<br><td>
                 </tr>
                </table>""" % (unicode(response[0], 'utf-8'))
            lastBoardTitle = boardTitle

        # Creating the Summary sheet output
        # ---------------------------------
        else:
            memberInfo = BoardMemberInfo(boardMember, response[0])

            # If we're grouping by board we need to display the board name
            # as an individuel row in the table
            # ------------------------------------------------------------
            if not sortType == 'Member' and not lastBoardTitle == boardTitle:
                html += u"""
            <tr>
             <td class="theader" colspan="%d">
              <b>%s</b>
             </td>
            </tr>
            """ % (countCols(columns) + 1, boardTitle)
            #if sortType == 'Member':
            html += u"""%s
            """ % (addTableRow(memberInfo, columns))
            #else:
            #    html += u"""%s
            #""" % (addTableRow(memberInfo, columns))

            lastBoardTitle = boardTitle

    # Need to end the table wrapper for the summary sheet
    # ------------------------------------------------------
    if not flavor == 'full':
        html += u"""      </table>"""

    html += u"""
      <br>
     </BODY>
    </HTML>
    """

    # The users don't want to display the country if it's the US.
    # Since the address is build by a common address module we're
    # better off removing it in the final HTML output
    # ------------------------------------------------------------
    cdrcgi.sendPage(html.replace(u'U.S.A.<br>', u''))

else:
    cdrcgi.bail("Sorry, don't know report type: %s" % rptType)
