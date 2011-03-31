#----------------------------------------------------------------------
#
# $Id: $
#
# Report to display the Board Roster with or without assistant
# information.
#
# BZIssue::4673 - Changes to PDQ Board Roster report.
# 
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, time, operator
import sys, ExcelWriter

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
boardType  = fields and fields.getvalue("board")  or None
# boardId    = fields and fields.getvalue("board") or None
otherInfo  = fields and fields.getvalue("oinfo") or 'Yes'
assistant  = fields and fields.getvalue("ainfo") or 'Yes'
flavor     = fields and fields.getvalue("sheet") or 'full'
rptType    = fields and fields.getvalue("rpttype") or 'html'
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
title      = u"PDQ Board Roster Report"
instr      = u"Report on PDQ Board Roster"
script     = u"BoardRosterFull.py"
SUBMENU    = u"Report Menu"
buttons    = ("Submit", SUBMENU, cdrcgi.MAINMENU)
header     = cdrcgi.header(title, title, instr, script, buttons, 
                           method = 'GET')

dateString = time.strftime(u"%B %d, %Y")

filterType= {'summary':'name:PDQBoardMember Roster Summary',
             'excel'  :'name:PDQBoardMember Roster Excel',
             'full'   :'name:PDQBoardMember Roster'}
allRows   = []

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
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    return allBoards


# -------------------------------------------------
# Create the table row for the table output
# -------------------------------------------------
def addExcelTableRow(person):
    """Return the Excel code to display a row of the report"""

    exRow.addCell( 1, person[1])
    exRow.addCell( 2, person[2])
    exRow.addCell( 3, person[3])
    exRow.addCell( 4, person[4])
    exRow.addCell( 5, person[5])
    exRow.addCell( 6, person[6])
    exRow.addCell( 7, person[7])
    exRow.addCell( 8, person[8])
    exRow.addCell( 9, person[9])
    exRow.addCell(10, person[10])
    exRow.addCell(11, person[11])
    exRow.addCell(12, person[12])
    exRow.addCell(13, person[13])

    return


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
                 term_start.value, person_doc.title
            FROM query_term member
            JOIN query_term curmemb
              ON curmemb.doc_id = member.doc_id
             AND LEFT(curmemb.node_loc, 4) = LEFT(member.node_loc, 4)
            JOIN query_term person
              ON person.doc_id = member.doc_id
            JOIN document person_doc
              ON person_doc.id = person.doc_id
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
    boardMembers = []

    for docId, boardId, term_start, name in rows:
        boardName = getBoardName(boardId)
        boardMembers.append([docId, boardId, boardName, term_start, name])

except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

# Sorting the list alphabetically by board member
# -----------------------------------------------
getcount = operator.itemgetter(4)
sortedMembers = sorted(boardMembers, key=getcount)

# We're creating two flavors of the report here: excel and html
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
       #main    { font-family: Arial, Helvetica, sans-serif;
                  font-size: 12pt; }
      </STYLE>
     </HEAD>  
     <BODY id="main">
       <H1>All %s Boards<br>
       <span style="font-size: 12pt">%s</span></H1>
    """ % (boardType, boardType, dateString)   

    for boardMember in sortedMembers:
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
            html += u"""
            <table width='100%%'>
             <tr>
              <td>%s<span style="font-style: italic">%s</span><br><br><td>
             </tr>
            </table>""" % (unicode(response[0], 'utf-8'), boardMember[2])

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

# ----------------------------------------------------------------
# The users decided not to have the Excel option implemented.  This
# is working except for the proper display of the address block but
# is not accessible.  To run this option submit the URL with the 
# parameter '&rptType=excel' 
# ----------------------------------------------------------------
elif rptType == 'excel':
    # Create the spreadsheet and define default style, etc.
    # -----------------------------------------------------
    wsTitle = u'BoardRosterFull'
    wb      = ExcelWriter.Workbook()
    b       = ExcelWriter.Border()
    borders = ExcelWriter.Borders(b, b, b, b)
    font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
    align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
    alignS  = ExcelWriter.Alignment('Left', 'Top', wrap = False)
    style1  = wb.addStyle(alignment = align, font = font)
    urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
    style4  = wb.addStyle(alignment = align, font = urlFont)
    style2  = wb.addStyle(alignment = align, font = font,
                             numFormat = 'YYYY-mm-dd')
    alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
    alignT  = ExcelWriter.Alignment('Left', 'Bottom', wrap = False)
    headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman',
                                                                size = 12)
    titleFont= ExcelWriter.Font(bold=True, name = 'Times New Roman',
                                                                size = 14)
    boldFont= ExcelWriter.Font(bold=True, name = 'Times New Roman',
                                                                size = 11)
    styleH  = wb.addStyle(alignment = alignH, font = headFont)
    styleT  = wb.addStyle(alignment = alignT, font = titleFont)
    style1b = wb.addStyle(alignment = align,  font = boldFont)
    styleS  = wb.addStyle(alignment = alignS, font = boldFont)
    styleR  = wb.addStyle(alignment = alignS, font = font)

    ws      = wb.addWorksheet(wsTitle, style1, 45, 1)

    # CIAT wants a title row
    # ----------------------------------------------------------
    titleTime = time.strftime("%Y-%m-%d %H:%M:%S")
    rowCount = 0
    rowNum = 1
    exRow = ws.addRow(rowNum, styleT)

    rowNum = 1
    exRow = ws.addRow(rowNum, styleS)
    exRow.addCell(1,  'Report created: %s' % titleTime)

    # Set the column width
    # --------------------
    ws.addCol( 1, 100)
    ws.addCol( 2, 100)
    ws.addCol( 3, 100)
    ws.addCol( 4, 100)
    ws.addCol( 5, 100)
    ws.addCol( 6, 100)

    # Create selection criteria for English/Spanish
    # and the boards
    # ---------------------------------------------
    boards = []
    iboard = 0

    rowNum += 2
    exRow = ws.addRow(rowNum, styleT)
    exRow.addCell(2, '%s' % ('All Boards'))
    rowNum += 1

    exRow = ws.addRow(rowNum, styleH)
    exRow.addCell( 1, 'Name')
    exRow.addCell( 2, 'Title')
    exRow.addCell( 3, 'Organization')
    exRow.addCell( 4, 'Address')
    exRow.addCell( 5, 'Phone')
    exRow.addCell( 6, 'Fax')
    exRow.addCell( 7, 'Email')
    exRow.addCell( 8, 'Specific Info')
    exRow.addCell( 9, 'Assistant')
    exRow.addCell(10, 'Assistant Phone')
    exRow.addCell(11, 'Assistant Fax')
    exRow.addCell(12, 'Assistant Email')
    exRow.addCell(13, 'SendBy')

    for boardMember in sortedMembers:
        response = cdr.filterDoc('guest',
                                 ['set:Denormalization PDQBoardMemberInfo Set',
                                  'name:Copy XML for Person 2',
                                  filterType[rptType]],
                                 boardMember[0],
                                 parm = [['otherInfo', otherInfo],
                                         ['assistant', assistant],
                                         ['eic', 'No']])
        if type(response) in (str, unicode):
            cdrcgi.bail("%s: %s" % (boardMember[0], response))

        #cdrcgi.bail(response[0].split(':'))
        boardRecord = response[0].split(':')
        rowCount += 1
        rowNum += 1
        exRow = ws.addRow(rowNum, styleR)
        addExcelTableRow(boardRecord)


    rowNum += 1
    exRow = ws.addRow(rowNum, style1b)
    exRow.addCell(1, 'Count: %d' % rowCount)

    t = time.strftime("%Y%m%d%H%M%S")

    # Save the report.
    # ----------------
    name = '/BoardRosterFullReport-%s.xls' % t
    REPORTS_BASE = 'd:/cdr/reports'
    f = open(REPORTS_BASE + name, 'wb')
    wb.write(f, True)
    f.close()

    if sys.platform == "win32":
        import os, msvcrt
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=%s" % name
    print
    wb.write(sys.stdout, True)

else:
    cdrcgi.bail("Sorry, don't know report type: %s" % rptType)
