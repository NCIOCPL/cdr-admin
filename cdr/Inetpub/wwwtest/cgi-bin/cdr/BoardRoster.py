#----------------------------------------------------------------------
#
# $Id: BoardRoster.py,v 1.6 2005-02-23 15:36:34 venglisc Exp $
#
# Report to display the Board Roster with or without assistant
# information.
#
# $Log: not supported by cvs2svn $
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
import cgi, cdr, cdrcgi, cdrdb, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
boardId   = fields and fields.getvalue("board") or None
otherInfo = fields and fields.getvalue("oinfo") or 'No'
assistant = fields and fields.getvalue("ainfo") or 'No'
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "PDQ Board Roster Report"
instr     = "Report on PDQ Board Roster"
script    = "BoardRoster.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)
header    = cdrcgi.header(title, title, instr, script, buttons)
boardId   = boardId and int(boardId) or None

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
    picklist = "<SELECT NAME='board'>\n"
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
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not boardId:
    form   = """\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <TABLE>
       <TR>
        <TD ALIGN='right'><B>PDQ Board:&nbsp;</B></TD>
        <TD>%s</TD>
       </TR>
       <TR>
        <TD ALIGN='right'> </TD>
        <TD>
         <INPUT TYPE='checkbox' NAME='oinfo'>
         Show All Contact Information
        </TD>
       </TR>
       <TR>
        <TD ALIGN='right'> </TD>
        <TD>
         <INPUT TYPE='checkbox' NAME='ainfo'>
         Show Assistant Information
        </TD>
       </TR>
       </TABLE>
       <SCRIPT language='JavaScript'>
        <!--
         function report() {
             var form = document.forms[0];
             if (!form.board.value) {
                 alert('Select a board first!');
             }
             else {
                 form.oinfo.value = form.oinfo.checked ? 'Yes' : 'No';
                 form.ainfo.value = form.ainfo.checked ? 'Yes' : 'No';
                 form.method      = 'GET';
                 form.submit();
             }
         }
        // -->
       </SCRIPT>
       <BR>
       <INPUT type='button' onclick='javascript:report()' value='Report'>
      </FORM>
     </BODY>
    </HTML>
""" % (cdrcgi.SESSION, session, getBoardPicklist())
    cdrcgi.sendPage(cdrcgi.unicodeToLatin1(header + form))

#----------------------------------------------------------------------
# Get the board's name from its ID.
#----------------------------------------------------------------------
boardName = getBoardName(boardId)

#----------------------------------------------------------------------
# Object for one PDQ board member.
#----------------------------------------------------------------------
class BoardMember:
    now = time.strftime("%Y-%m-%d")
    def __init__(self, docId, start, finish, name):
        self.id    = docId
        self.name  = cleanTitle(name)
        self.isEic = (start and start <= BoardMember.now and
                      (not finish or finish > BoardMember.now))
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
 SELECT DISTINCT member.doc_id, start.value, finish.value, person_doc.title
            FROM query_term member
            JOIN query_term curmemb
              ON curmemb.doc_id = member.doc_id
             AND LEFT(curmemb.node_loc, 4) = LEFT(member.node_loc, 4)
            JOIN query_term person
              ON person.doc_id = member.doc_id
            JOIN document person_doc
              ON person_doc.id = person.doc_id
 LEFT OUTER JOIN query_term start
              ON start.doc_id = member.doc_id
             AND LEFT(start.node_loc, 4) = LEFT(member.node_loc, 4)
             AND start.path   = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/EditorInChief/TermStartDate'
 LEFT OUTER JOIN query_term finish
              ON finish.doc_id = member.doc_id  
             AND LEFT(finish.node_loc, 4) = LEFT(member.node_loc, 4)
             AND finish.path  = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/EditorInChief/TermEndDate'
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
    for docId, start, finish, name in rows:
        boardMembers.append(BoardMember(docId, start, finish, name))
    boardMembers.sort()

except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

# ---------------------------------------------------------------
# Create the HTML Output Page
# ---------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>PDQ Board Member Roster Report - %s</title>
  <STYLE type='text/css'>
   H1       { font-family: Arial, sans-serif; font-size: 16pt;
              text-align: center; font-weight: bold; }
   H2       { font-family: Arial, sans-serif; font-size: 14pt;
              text-align: center; font-weight: bold; }
   TD.hdg   { font-family: Arial, sans-serif; font-size: 16pt;
              font-weight: bold; }
   P        { font-family: Arial, sans-serif; font-size: 12pt; }

   /* The Board Member Roster information is created via a global */
   /* template for Persons.  The italic display used for the QC   */
   /* report does therefore need to be suppressed here.           */
   /* ----------------------------------------------------------- */
   I        { font-family: Arial, sans-serif; font-size: 12pt; 
              font-style: normal; }
   SPAN.SectionRef { text-decoration: underline; font-weight: bold; }
  </STYLE>
 </HEAD>  
 <BASEFONT FACE="Arial, Helvetica, sans-serif">
  <BODY>   
  <CENTER>
   <H1>%s</H1>
  </CENTER>
""" % (boardName, boardName)   

for boardMember in boardMembers:
    response = cdr.filterDoc('guest',
                             ['set:Denormalization PDQBoardMemberInfo Set',
                              'name:Copy XML for Person 2',
                              'name:PDQBoardMember Roster'],
                             boardMember.id,
                             parm = [['otherInfo', otherInfo],
                                     ['assistant', assistant],
                                     ['eic',
                                      boardMember.isEic and 'Yes' or 'No']])
    if type(response) in (str, unicode):
        cdrcgi.bail("%s: %s" % (boardMember.id, response))
    html += response[0]

boardManagerInfo = getBoardManagerInfo(boardId)

html += """
  <hr width="50%%"><br>
  <b><u>Board Manager Information</u></b><br>
  <b>%s</b><br>
  Cancer Information Products and Systems (CIPS)<br>
  Office of Communications<br>
  National Cancer Institute<br>
  MSC-8321, Suite 3002B<br>
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
 </BODY>   
</HTML>    
""" % (boardManagerInfo[0][1], boardManagerInfo[2][1],
       boardManagerInfo[1][1], boardManagerInfo[1][1])

cdrcgi.sendPage(html)
