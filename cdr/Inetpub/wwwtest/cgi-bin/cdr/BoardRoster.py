#----------------------------------------------------------------------
# $Id: BoardRoster.py,v 1.1 2004-05-21 20:59:37 venglisc Exp $
#
# Report to display the Board Roster with or without assistant
# information.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
boardInfo = fields and fields.getvalue("BoardInfo")      or None
repType   = fields and fields.getvalue("RepType")        or None
otherInfo = fields and fields.getvalue("ShowOtherInfo")     or 'No'
assistant = fields and fields.getvalue("ShowAssistantInfo") or 'No'
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "PDQ Board Roster Report"
instr     = "Report on PDQ Board Roster"
script    = "BoardRoster.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)
stPath    = '/Summary/SummaryTitle'
sbPath    = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
sbmPath   = '/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref'
trimPat   = re.compile("[\s;]+$")
bmPath    = '/Person/ProfessionalInformation/PDQBoardMembershipDetails/PDQ'\
            '%Board/@cdr:ref'

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
# Returns a copy of a doc title without trailing whitespace or semicolons.
#----------------------------------------------------------------------
def trim(s):
    return trimPat.sub("", s)

#----------------------------------------------------------------------
# Build a picklist for PDQ Boards.
# This function serves two purposes:
# a)  create the picklist for the selection of the board
# b)  create a dictionary in subsequent calls to select the board
#     ID based on the board selected in the first call.
#----------------------------------------------------------------------
def getBoardPicklist(boardDict):
    picklist = "<SELECT NAME='BoardInfo'>"
    selected = " SELECTED"
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
        for row in cursor.fetchall():
            semi = row[1].find(';')
            if semi != -1: boardTitle = trim(row[1][:semi])
            else:          boardTitle = trim(row[1])
            picklist += "<OPTION%s>%s</OPTION>" % (selected, boardTitle)
            selected = ""
            boardDict[boardTitle] = row[0]
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    return picklist + "</SELECT>"

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
boardList = {}
if not boardInfo:
    header   = cdrcgi.header(title, title, instr, script, ("Submit",
                                                           SUBMENU,
                                                           cdrcgi.MAINMENU))
    form     = """\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <TABLE>
       <TR>
        <TD ALIGN='right'><B>PDQ Board:&nbsp;</B></TD>
        <TD>%s</TD>
       </TR>
       <TR>
        <TD ALIGN='right'> </TD>
        <TD>
         <INPUT TYPE='checkbox' NAME='ShowOtherInfo' VALUE='Yes'>
         Show All Contact Information
        </TD>
       </TR>
       <TR>
        <TD ALIGN='right'> </TD>
        <TD>
         <INPUT TYPE='checkbox' NAME='ShowAssistantInfo' VALUE='Yes'>
         Show Assistant Information
        </TD>
       </TR>
       </TABLE>
      </FORM>
     </BODY>
    </HTML>
""" % (cdrcgi.SESSION, session, getBoardPicklist(boardList))

    cdrcgi.sendPage(cdrcgi.unicodeToLatin1(header + form))

#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y", time.localtime(time.time()))

#----------------------------------------------------------------------
# We have a board specified; extract its ID based on its doc title
# as the key of a dictionary created with getBoardPicklist().
#----------------------------------------------------------------------
getBoardPicklist(boardList)
boardId    = boardList[boardInfo]
boardName  = boardInfo
if not boardId: 
    cdrcgi.bail("Board information garbled: %s" % boardInfo)

report    = ''
html      = ''
report += """\
  </TABLE>
 </BODY>
</HTML>
"""
#    except cdrdb.Error, info:
#        cdrcgi.bail('Database query failure: %s' % info[1][0])
#    cdrcgi.sendPage(cdrcgi.unicodeToLatin1(header + report))
header    = cdrcgi.header(title, title, instr, script, buttons)
# cdrcgi.sendPage(cdrcgi.unicodeToLatin1(header + report))

#----------------------------------------------------------------------
# Show the members of the board, with associated topics.
#----------------------------------------------------------------------
instr     = '%s Roster -- %s.' % (boardName, dateString)
header    = cdrcgi.header(title, title, instr, script, buttons)
members   = {}
topics    = {}
audString = ""
report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
  <H4>%s Roster%s</H4>
""" % (cdrcgi.SESSION, session, boardName, audString)

#----------------------------------------------------------------------
# Type for storing board member information.
#----------------------------------------------------------------------
class Member:
    def __init__(self, id, name):
        self.id     = id
        self.name   = name
        self.topics = []

#----------------------------------------------------------------------
# Type for storing summary topic information.
#----------------------------------------------------------------------
class Topic:
    def __init__(self, id, name):
        self.id   = id
        self.name = name

#----------------------------------------------------------------------
# This is trickier than the other form of the report, because we must
# deal with two possible conditions:
#   1. A board member is linked to a board, but to none of that board's
#      summaries.
#   2. A summary lists a board member whose own document does not
#      reflect that membership.
#----------------------------------------------------------------------
try:
    query = """\
SELECT bp.int_val person_id, title person_name, b.doc_id boardmemberdoc_id, 
       b.int_val board_id, bn.value board_name, d.doc_type, d.val_status,
       CASE WHEN eds.value < getdate() THEN 'Active'
            ELSE 'Inactive'
       END EICS,
       CASE WHEN ede.value IS NULL     THEN 'Active'
            WHEN ede.value > getdate() THEN 'Active'
            ELSE 'Inactive'
       END EICE
  FROM query_term b
  JOIN document d  
    ON d.id = b.doc_id
  JOIN query_term bp
                              -- get the board member person ID
    ON b.doc_id = bp.doc_id
  JOIN query_term bn                 
                              -- get the board name
    ON bn.doc_id = b.int_val
  JOIN query_term curr               
                              -- get the info if board member is active
    ON b.doc_id = curr.doc_id
   AND LEFT(b.node_loc, 4) = LEFT(curr.node_loc, 4)
LEFT OUTER JOIN query_term eds       
                              -- Find TermStartDate to find out 
                              -- if EditorInChief
    ON b.doc_id = eds.doc_id
   AND left(b.node_loc, 4) = left(eds.node_loc, 4)
   AND eds.path   = 
      '/PDQBoardMemberInfo/BoardMembershipDetails/EditorInChief/TermStartDate'
LEFT OUTER JOIN query_term ede
                              -- Find TermEndDate to find out if still 
                              -- active EditorInChief
    ON b.doc_id = ede.doc_id  
   AND left(b.node_loc, 4) = left(ede.node_loc, 4)
   AND ede.path   = 
          '/PDQBoardMemberInfo/BoardMembershipDetails/EditorInChief/TermEndDate'
 WHERE b.path     = 
                 '/PDQBoardMemberInfo/BoardMembershipDetails/BoardName/@cdr:ref'
                              -- get the records with the board id
   AND b.int_val  = %d
                              -- value if the board id
   AND bp.path    = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'
                              -- get the person ID from the board document
   AND bn.path   = '/Organization/OrganizationNameInformation/OfficialName/Name'
                              -- get the official board name
   AND active_status = 'A' 
                              -- document can not be blocked
   AND curr.path  = '/PDQBoardMemberInfo/BoardMembershipDetails/CurrentMember'
                              -- Board member must be current
   AND curr.value = 'Yes'
 ORDER BY 8, title""" % (boardId) 
    cursor.execute(query)
    boardmember = []
    for row in cursor.fetchall():
        eic = ''
        if row[7] == 'Active' and row[8] == 'Active':
            eic = 'Yes'
        boardmember.append([row[0], row[2], eic])
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
   SPAN.SectionRef { text-decoration: underline; font-weight: bold; }
  </STYLE>
 </HEAD>  
 <BASEFONT FACE="Arial, Helvetica, sans-serif">
  <BODY>   
  <CENTER>
   <H1>%s</H1>
  </CENTER>
""" % (boardInfo, boardInfo)   

for i in boardmember:
    response = cdr.filterDoc('guest', ['set:Denormalization PDQBoardMemberInfo Set',
                                       'name:Copy XML for Person 2',
                                       'name:PDQBoardMember Roster'], i[1],
                                       parm = [['otherInfo',otherInfo],
                                               ['assistant', assistant],
                                               ['eic', i[2]]])
                                               #['eic', i[2] ]) 
    html += response[0]

html += """
 </BODY>   
</HTML>    
"""

cdrcgi.sendPage(html)
