#----------------------------------------------------------------------
#
# $Id$
#
# Report to display the Board Roster with or without assistant
# information.
#
# $Log: not supported by cvs2svn $
# Revision 1.15  2009/09/28 16:00:08  venglisc
# Adding a blank column to the summary sheet report option. (Bug 4649)
#
# Revision 1.14  2009/05/12 14:18:45  venglisc
# Modified to send Unicode string to sendPage() function. (Bug 4560)
#
# Revision 1.13  2008/09/03 18:02:17  venglisc
# Modified quoting in JavaScript call which prevented IE from running
# correctly. (Bug 4236)
#
# Revision 1.12  2008/08/22 19:24:25  venglisc
# Formatting changes to summary sheet and full report. (Bug 4236)
#
# Revision 1.11  2008/08/08 22:27:36  venglisc
# Added TermStartDate as column to summary sheet. (Bug 4236)
#
# Revision 1.10  2008/07/22 17:07:28  venglisc
# Added another option to create a summary sheet for the board managers to
# display only the name, phone, email, fax, CDR-ID. (Bug 4204)
#
# Revision 1.9  2007/08/27 20:57:52  bkline
# Change in address string at Sheri's request (#3553).
#
# Revision 1.8  2006/09/27 23:16:09  venglisc
# Changing Suite number of Board Manager address. (Bug 2530)
#
# Revision 1.7  2006/03/30 16:37:49  venglisc
# Changed address to replace CIPS with OCCM. (Bug 2031)
#
# Revision 1.6  2005/02/23 15:36:34  venglisc
# Fixed incorrect comment indicators.  This caused the style for italics to
# be ignored. (Bug 1527)
#
# Revision 1.5  2005/02/22 19:17:02  venglisc
# Modified code to add style for suppressing display of italic information.
# (Bug 1527)
#
# Revision 1.4  2005/02/19 04:08:13  bkline
# Fixed bug in determining which board members are current.  Fixed bug
# in identifying editors-in-chief.
#
# Revision 1.3  2005/02/17 22:10:22  venglisc
# Added Board Manager's contact information at end of report (Bug 1527).
#
# Revision 1.2  2005/02/10 19:17:36  bkline
# Converted from POST to GET form request; tightened up SQL query.
#
# Revision 1.1  2004/05/21 20:59:37  venglisc
# Initial Version to create the PDQ Board Member Roster report.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
boardId    = fields and fields.getvalue("board") or None
otherInfo  = fields and fields.getvalue("oinfo") or 'No'
assistant  = fields and fields.getvalue("ainfo") or 'No'
phone      = fields and fields.getvalue("pinfo") or 'No'
fax        = fields and fields.getvalue("finfo") or 'No'
cdrid      = fields and fields.getvalue("cinfo") or 'No'
email      = fields and fields.getvalue("einfo") or 'No'
startDate  = fields and fields.getvalue("dinfo") or 'No'
blankCol   = fields and fields.getvalue("blank") or 'No'
flavor     = fields and fields.getvalue("sheet") or 'full'
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
title      = "PDQ Board Roster Report"
instr      = "Report on PDQ Board Roster"
script     = "BoardRoster.py"
SUBMENU    = "Report Menu"
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

         document.getElementById('contact').checked = false;
         document.getElementById('assistant').checked = false;
         var form = document.forms[0];
         {
             form.einfo.value = form.einfo.checked ? 'Yes' : 'No';
             form.sheet.value = form.sheet.checked ? 'summary' : 'full';
             form.pinfo.value = form.pinfo.checked ? 'Yes' : 'No';
             form.cinfo.value = form.cinfo.checked ? 'Yes' : 'No';
             form.dinfo.value = form.dinfo.checked ? 'Yes' : 'No';
             form.finfo.value = form.finfo.checked ? 'Yes' : 'No';
             form.blank.value = form.blank.checked ? 'Yes' : 'No';
         }
     }
     function doFullReport() {
         document.getElementById('summary').checked = false;
         var form = document.forms[0];
         {
             form.oinfo.value = form.oinfo.checked ? 'Yes' : 'No';
             form.ainfo.value = form.ainfo.checked ? 'Yes' : 'No';
             form.sheet.value = form.sheet.checked ? 'summary' : 'full';
         }
     }
    </script>
""")
boardId    = boardId and int(boardId) or None
dateString = time.strftime("%B %d, %Y")

filterType= {'summary':'name:PDQBoardMember Roster Summary',
             'full'   :'name:PDQBoardMember Roster'}
allRows   = []

# We can only run one report at a time: Full or Summary
# -----------------------------------------------------
if flavor == 'summary' and (otherInfo == 'Yes' or assistant == 'Yes'):
    cdrcgi.bail("Please uncheck 'Create Summary Sheet' to run 'Full' report")

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
def getBoardPicklist():
    picklist = "<SELECT NAME='board' onchange='javascript:doSummarySheet(\"summary\")'>\n"
    sel      = " SELECTED"
    try:
        cursor.execute("""\
SELECT DISTINCT board.id, board.title
           FROM document board
           JOIN query_term org_type
             ON org_type.doc_id = board.id
          WHERE org_type.path = '/Organization/OrganizationType'
            AND org_type.value IN ('PDQ Editorial Board',
                                   'PDQ Advisory Board')
       ORDER BY board.title""")
        for id, title in cursor.fetchall():
            title = cleanTitle(title)
            picklist += "<OPTION%s value='%d'>%s</OPTION>\n" % (sel, id, title)
            sel = ""
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    return picklist + "</SELECT>\n"

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

    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure for BoardManager: %s' % info[1][0])
    return cursor.fetchall()

#----------------------------------------------------------------------
# Extract the relevant information from the HTML snippet (which is
# created using the filter modules)
# The phone, fax, email information has been wrapped with the 
# respective elements in the filter for the summary sheet flavor
#----------------------------------------------------------------------
def extractSheetInfo(boardInfo):
    #cdrcgi.bail(boardInfo)
    myName  = boardInfo.split('<b>')[1].split('</b>')[0]
    #myTitle = boardInfo.split('<br>')[1]
    if boardInfo.find('<Phone>') > -1:
        try:
            myPhone = boardInfo.split('<Phone>')[1].split('</Phone>')[0]
        except:
            cdrcgi.bail(boardInfo)
    else:
        myPhone = ''

    if boardInfo.find('<Email>') > -1:
        try:
            myEmail = boardInfo.split('<Email>')[1].split('</Email>')[0]
        except:
            cdrcgi.bail(boardInfo)
    else:
        myEmail = ''

    if boardInfo.find('<Fax>') > -1:
        try:
            myFax   = boardInfo.split('<Fax>')[1].split('</Fax>')[0]
        except:
            cdrcgi.bail(boardInfo)
    else:
        myFax   = ''
    
    return [myName, myPhone, myFax, myEmail]


#----------------------------------------------------------------------
# Add the specific information to the boardInfo records
#----------------------------------------------------------------------
def addSpecificContactInfo(boardIds, boardInfo):
    newBoardInfo = []
    try:
        cursor.execute("""\
SELECT q.doc_id, q.value as SpPhone, f.value as SpFax, e.value as SpEmail
  FROM query_term q
LEFT OUTER JOIN query_term f
    ON q.doc_id = f.doc_id
   AND f.path = '/PDQBoardMemberInfo/BoardMemberContact' +
                '/SpecificBoardMemberContact/BoardContactFax'
LEFT OUTER JOIN query_term e
    ON q.doc_id = e.doc_id
   AND e.path = '/PDQBoardMemberInfo/BoardMemberContact/' +
                'SpecificBoardMemberContact/BoardContactEmail'
 WHERE q.doc_id IN (%s)
   AND q.path = '/PDQBoardMemberInfo/BoardMemberContact' +
                '/SpecificBoardMemberContact/BoardContactPhone'
 ORDER BY q.path""" % ','.join(["'%d'" % id for id in boardIds]))
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure for SpecificInfo: %s' % info[1][0]+
                    '<br>Board has No Board Members')

    rows = cursor.fetchall()

    # Add the specific info to the boardInfo records
    # ----------------------------------------------
    for member in boardInfo:
        memCount = len(member)
        for cdrId, phone, fax, email in rows:
            if member[4] == cdrId:
                member = member + [phone or None, fax or None, email or None]
        if memCount == len(member):
            member = member + [None, None, None]
        newBoardInfo.append(member)
    return newBoardInfo


#----------------------------------------------------------------------
# Once the information for all board members has been collected create
# the HTML table to be displayed
#----------------------------------------------------------------------
def makeSheet(rows):
    # Create the table and table headings
    # ===================================
    rowCount = 0
    html = """
        <tr class="theader">"""
    for k, v in [('Name','Yes'), ('Phone',phone), ('Fax',fax), 
              ('Email',email), ('CDR-ID',cdrid), 
              ('Start Date', startDate), ('&nbsp;', blankCol)]:
        if v == 'Yes':
            rowCount += 1
            html += """
         <th class="thcell">%s</th>""" % k

    html += """
        </tr>"""

    # Populate the table with data rows
    # =================================
    #for row in name, phone, fax, email, cdrid, termStardDate, spPhone, ...
    for row in rows:
       html += """
        <tr>
         <td class="name">%s</td>""" % row[0]
       if phone == 'Yes':
           html += """
         <td class="phone">%s""" % row[1]
           if row[1] and row[6]:
               html += "<br>%s</td>" % row[6]
           elif not row[1] and row[6]:
               html += "%s</td>" % row[6]
           else:
               html += "</td>"

       if fax   == 'Yes':
           html += """
         <td class="fax">%s""" % row[2]
           if row[2] and row[7]:
               html += "<br>%s</td>" % row[7]
           elif not row[2] and row[7]:
               html += "%s</td>" % row[7]
           else:
               html += "</td>"

       if email == 'Yes':
           html += """
         <td class="email">
          <a href="mailto:%s">%s</a>
         """ % (row[3], row[3])
           if row[3] and row[8]:
               html += """<br>
          <a href="mailto:%s">%s</a>
         """ % (row[8], row[8])
           elif not row[3] and row[8]:
               html += """
          <a href="mailto:%s">%s</a>
         </td>""" % (row[8], row[8])
           else:
               html += "</td>"

       if cdrid == 'Yes':
           html += """
         <td class="cdrid">%s</td>""" % row[4]
       if startDate == 'Yes':
           html += """
         <td class="cdrid">%s</td>""" % row[5]
       if blankCol == 'Yes':
           html += """
         <td class="blank">&nbsp;</td>"""
       html += """
        </tr>"""

    return (html, rowCount)

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not boardId:
    form   = """\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <TABLE border='0'>
       <TR>
        <TD ALIGN='right'><B>PDQ Board:&nbsp;</B></TD>
        <TD>%s</TD>
       </TR>
       <TR>
        <TD ALIGN='right'> </TD>
        <TD>
         <INPUT TYPE='checkbox' NAME='oinfo' id='contact'
                onclick='jacascript:doFullReport()'>
         Show All Contact Information
        </TD>
       </TR>
       <TR>
        <TD ALIGN='right'> </TD>
        <TD>
         <INPUT TYPE='checkbox' NAME='ainfo' id='assistant'
                onclick='javascript:doFullReport()'>
         Show Assistant Information
         <div style="height: 10px"> </div>
        </TD>
       </TR>
       <TR style="margin-top: 24px">
        <TD ALIGN='right'> </TD>
        <TD style="background-color: #BEBEBE">
         <div style="height: 10px"> </div>
         <INPUT TYPE='checkbox' NAME='sheet' id='summary'
                onclick='javascript:doSummarySheet("summary")'>
          <strong >Create Summary Sheet</strong>
         <table>
          <tr>
           <th><span style="margin-left: 20px"> </span></th>
           <th style="font-size: 10pt">Include Columns
          <tr>
           <td><span style="margin-left: 20px"> </span></td>
           <td>
            <input type='checkbox' name='pinfo' 
                   onclick='javascript:doSummarySheet()' id='E1' CHECKED>
            Phone
           </td>
          </tr>
          <tr>
           <td> </td>
           <td>
            <input type='checkbox' name='finfo' 
                   onclick='javascript:doSummarySheet()' id='E2'>
            Fax
           </td>
          </tr>
          <tr>
           <td> </td>
           <td>
            <input type='checkbox' name='einfo' 
                   onclick='javascript:doSummarySheet()' id='E3'>
            Email
           </td>
          </tr>
          <tr>
           <td> </td>
           <td>
            <input type='checkbox' name='cinfo' 
                   onclick='javascript:doSummarySheet()' id='E4'>
            CDR-ID
           </td>
          </tr>
          <tr>
           <td> </td>
           <td>
            <input type='checkbox' name='dinfo' 
                   onclick='javascript:doSummarySheet()' id='E5'>
            Start Date
           </td>
          </tr>
          <tr>
           <td> </td>
           <td>
            <input type='checkbox' name='blank' 
                   onclick='javascript:doSummarySheet()' id='E6'>
            Blank Column
           </td>
          </tr>
         </table>
        </TD>
       </TR>
       </TABLE>
      </FORM>
     </BODY>
    </HTML>
""" % (cdrcgi.SESSION, session, getBoardPicklist())
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Get the board's name from its ID.
#----------------------------------------------------------------------
boardName = getBoardName(boardId)

#----------------------------------------------------------------------
# Object for one PDQ board member.
#----------------------------------------------------------------------
class BoardMember:
    now = time.strftime("%Y-%m-%d")
    def __init__(self, docId, eic_start, eic_finish, term_start, name):
        self.id        = docId
        self.name      = cleanTitle(name)
        self.isEic     = (eic_start and eic_start <= BoardMember.now and
                          (not eic_finish or eic_finish > BoardMember.now))
        self.eicSdate  = eic_start
        self.eicEdate  = eic_finish
        self.termSdate = term_start
    def __cmp__(self, other):
        if self.isEic == other.isEic:
            return cmp(self.name.upper(), other.name.upper())
        elif self.isEic:
            return -1
        return 1
    
#----------------------------------------------------------------------
# This is trickier than the other form of the report, because we must
# deal with two possible conditions:
#   1. A board member is linked to a board, but to none of that board's
#      summaries.
#   2. A summary lists a board member whose own document does not
#      reflect that membership.
#
# XXX Note: Comment not reflected in code.  RMK 2005-02-10
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
             AND member.int_val = ?""", boardId, timeout = 300)
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

# ---------------------------------------------------------------
# Create the HTML Output Page
# ---------------------------------------------------------------
html = """\
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
""" % boardName

if flavor == 'full':
    html += """
   <H1>%s<br><span style="font-size: 12pt">%s</span></H1>
""" % (boardName, dateString)   

count = 0
for boardMember in boardMembers:
    response = cdr.filterDoc('guest',
                             ['set:Denormalization PDQBoardMemberInfo Set',
                              'name:Copy XML for Person 2',
                              filterType[flavor]],
                             boardMember.id,
                             parm = [['otherInfo', otherInfo],
                                     ['assistant', assistant],
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
    # page breaks within address blocks after the convertion to 
    # MS-Word.
    # -----------------------------------------------------------
    if flavor == 'full':
        html += """
        <table width='100%%'>
         <tr>
          <td>%s<td>
         </tr>
        </table>""" % response[0]
    else:
        row = extractSheetInfo(response[0])
        row = row + [boardMember.id] + [boardMember.termSdate]
        allRows.append(row)
 
# Create the HTML table for the summary sheet
# -------------------------------------------
if flavor == 'summary':
    allRows = addSpecificContactInfo(boardIds, allRows)
    out  = makeSheet(allRows)
    html += """\
       <table id="summary" cellspacing="0" cellpadding="5">
        <tr>
         <td id="hdg" colspan="%d">%s<br>
           <span style="font-size: 12pt">%s</span>
         </td>
        </tr>
        %s
       </table>
""" % (out[1], boardName, dateString, out[0])   

boardManagerInfo = getBoardManagerInfo(boardId)

html += """
  <br>
  <table width='100%%'>
   <tr>
    <td>
     <b><u>Board Manager Information</u></b><br>
     <b>%s</b><br>
     Office of Cancer Content Management (OCCM)<br>
     Office of Communications and Education<br>
     National Cancer Institute<br>
     MSC-8321, Suite 300A<br>
     6116 Executive Blvd.<br>
     Bethesda, MD 20892-8321<br><br>
     <table border="0" width="100%%" cellspacing="0" cellpadding="0">
      <tr>
       <td width="35%%">Phone</td>
       <td width="65%%">%s</td>
      </tr>
      <tr>
       <td>Fax</td>
       <td>301-480-8105</td>
      </tr>
      <tr>
       <td>Email</td>
       <td><a href="mailto:%s">%s</a></td>
      </tr>
     </table>
       </td>
   </tr>
  </table>
 </BODY>   
</HTML>    
""" % (boardManagerInfo and boardManagerInfo[0][1] or 'No Board Manager', 
       boardManagerInfo and boardManagerInfo[2][1] or 'TBD',
       boardManagerInfo and boardManagerInfo[1][1] or 'TBD', 
       boardManagerInfo and boardManagerInfo[1][1] or 'TBD')

# The users don't want to display the country if it's the US.
# Since the address is build by a common address module we're
# better off removing it in the final HTML output
# ------------------------------------------------------------
cdrcgi.sendPage(html.replace('U.S.A.<br>', ''))
