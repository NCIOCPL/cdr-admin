#----------------------------------------------------------------------
#
# $Id$
#
# Report on PDQ Board members and topics.
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2004/01/07 15:48:04  venglisc
# Modified the PDQ Board Listings user interface to being able and select
# to display the reports (Order by Topic, Order by Member) with and without
# the CDR IDs.
# The reports only show the names and board names (removed location info)
# and the board picklist doesn't display the CDR IDs of the boards anymore.
# (Bug 1006, 1007)
#
# Revision 1.6  2003/07/29 12:38:55  bkline
# Removed unnecessary test for non-breaking space in audience string.
#
# Revision 1.5  2003/06/13 21:14:12  bkline
# Added indication of audience under title.
#
# Revision 1.4  2002/06/06 12:01:26  bkline
# Added calls to cdrcgi.unicodeToLatin1().
#
# Revision 1.3  2002/02/21 15:22:03  bkline
# Added navigation buttons.
#
# Revision 1.2  2002/02/20 23:06:34  bkline
# Multiple enhancements made at users' request.
#
# Revision 1.1  2002/01/22 21:35:35  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
boardInfo = fields and fields.getvalue("BoardInfo")      or None
audience  = fields and fields.getvalue("Audience")       or None
repType   = fields and fields.getvalue("RepType")        or None
showCdrId = fields and fields.getvalue("ShowCdrId")      or None
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "PDQ Board Report"
instr     = "Report on PDQ Board Members and Topics"
script    = "PdqBoards.py"
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
# Build a picklist for Summary Audience.
#----------------------------------------------------------------------
def getAudiencePicklist():
    picklist = "<SELECT NAME='Audience'>"
    selected = " SELECTED"
    try:
        cursor.execute("""\
SELECT DISTINCT value
           FROM query_term
          WHERE path = '/Summary/SummaryMetaData/SummaryAudience'
       ORDER BY value""")
        for row in cursor.fetchall():
            if row[0]:
                picklist += "<OPTION%s>%s</OPTION>" % (selected, row[0])
            selected = ""

    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    return picklist + "</SELECT>"

#----------------------------------------------------------------------
# Build a picklist for PDQ Boards.
# This function serves two purposes:
# a)  create the picklist for the selection of the board
# b)  create a dictionary in subsequent calles to select the board
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
    form     = u"""\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <TABLE>
       <TR>
        <TD ALIGN='right'><B>PDQ Board:&nbsp;</B></TD>
        <TD>%s</TD>
       </TR>
       <TR>
        <TD ALIGN='right'><B>Summary Audience:&nbsp;</B></TD>
        <TD>%s</TD>
       </TR>
      </TABLE>
      <CENTER>
       <TABLE border='0'>
        <TR>
         <TD>
          <INPUT TYPE='radio' NAME='ShowCdrId' VALUE='Yes'>
           With CDR ID<BR>
         </TD>
         <TD>
          <INPUT TYPE='radio' NAME='RepType' VALUE='ByTopic' checked='1'>
           Order by Topic<BR>
         </TD>
        </TR>
        <TR>
         <TD>
          <INPUT TYPE='radio' NAME='ShowCdrId' VALUE='No' CHECKED>
           Without CDR ID<BR>
         </TD>
         <TD>
          <INPUT TYPE='radio' NAME='RepType' VALUE='ByMember'>
           Order by Board Member<BR>
         </TD>
        </TR>
       </TABLE>
      </CENTER>
      </FORM>
     </BODY>
    </HTML>
""" % (cdrcgi.SESSION, session, getBoardPicklist(boardList), getAudiencePicklist())

    cdrcgi.sendPage(header + form)

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

#----------------------------------------------------------------------
# Prepare for filtering on audience type, if appropriate.
#----------------------------------------------------------------------
audienceJoin = ''
if audience and len(audience) > 1:
    audienceJoin = """\
           JOIN query_term audience
             ON audience.doc_id = summary.doc_id
            AND audience.path = '/Summary/SummaryMetaData/SummaryAudience'
            AND audience.value = '%s'""" % audience

#----------------------------------------------------------------------
# Show the summaries linked to the board, with associated board members.
#----------------------------------------------------------------------
if repType == 'ByTopic':
    instr     = 'Board Report by Topics -- %s.' % dateString
    header    = cdrcgi.header(title, title, instr, script, buttons)
    audString = ""
    if audience:
        audString = "<BR>(%s)" % audience
    report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
  <H4>Topics for %s%s</H4>
""" % (cdrcgi.SESSION, session, boardName, audString)
    try:
        cursor.execute("""\
SELECT DISTINCT board_member.id, board_member.title,
                summary.doc_id, summary.value
           FROM document board_member
           JOIN query_term summary_board_member
             ON summary_board_member.int_val = board_member.id
            AND summary_board_member.path = '%s'
           JOIN query_term summary_board
             ON summary_board.doc_id = summary_board_member.doc_id
            AND summary_board.path = '%s'
            AND LEFT(summary_board.node_loc, 8) = 
                LEFT(summary_board_member.node_loc, 8)
           JOIN query_term summary
             ON summary.doc_id = summary_board.doc_id
            AND summary.path = '%s'
             %s
          WHERE summary_board.int_val = ?
       ORDER BY summary.value, board_member.title""" % (sbmPath, sbPath,
                                                        stPath, audienceJoin), 
                boardId)

        prevSummaryId = 0
        for row in cursor.fetchall():

# Decision if the report will be printed with or without CDR ID
# =============================================================
            if showCdrId == 'Yes':
                if row[2] != prevSummaryId:
#                    if prevSummaryId:
#                        report += """\
#"""
                     report += """\
  </TABLE>
  <TABLE width='100%%' border='0'>
   <TR>
    <TD width='10%%' align='right'>
     <BR/>
     <FONT SIZE='4'>%10d</FONT>
    </TD>
    <TD>
     <BR/>
     <FONT SIZE='4'>%s</FONT>
    </TD>
   </TR>
""" % (row[2], re.sub(";", "--", trim(row[3])))
                     prevSummaryId = row[2]

                report += """\
   <TR>
    <TD width='10%%'> </TD>
    <TD>
     <FONT SIZE='3'>%s</FONT>
    </TD>
   </TR>
""" % (trim(row[1][:row[1].index(';')]))
                if prevSummaryId:
                    report += """\
"""
### Code for report without CDR ID
### ==============================
#                    if prevSummaryId:
#                        report += """\
#"""
            else:
                if row[2] != prevSummaryId:
                     report += """\
  </TABLE>
  <TABLE width='100%%' border='0'>
   <TR>
    <TD colspan='2'>
     <BR/>
     <FONT SIZE='4'>%s</FONT>
    </TD>
    <TD width='5%%' align='right'>
     <BR/>
     <FONT SIZE='4'></FONT>
    </TD>
   </TR>
""" % (re.sub(";", "--", trim(row[3])))
                     prevSummaryId = row[2]

                report += """\
   <TR>
    <TD width='5%%'> </TD>
    <TD>
     <FONT SIZE='3'>%s</FONT>
    </TD>
   </TR>
""" % (trim(row[1][:row[1].index(';')]))
                if prevSummaryId:
                    report += """\
"""
# =======================================
        report += """\
  </TABLE>
 </BODY>
</HTML>
"""
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    cdrcgi.sendPage(header + report)

#----------------------------------------------------------------------
# Show the members of the board, with associated topics.
#----------------------------------------------------------------------
instr     = 'Board Report by Members -- %s.' % dateString
header    = cdrcgi.header(title, title, instr, script, buttons)
members   = {}
topics    = {}
audString = ""
if audience:
    audString = "<BR>(%s)" % audience
report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
  <H4>Reviewers for %s%s</H4>
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
    cursor.execute("""\
SELECT DISTINCT board_member.id, board_member.title
           FROM document board_member
           JOIN query_term board_membership
             ON board_membership.doc_id = board_member.id
          WHERE board_membership.path = '%s'
            AND board_membership.int_val = ?""" % bmPath, boardId)
    for row in cursor.fetchall():
        members[row[0]] = Member(row[0], re.sub(";", ", ", trim(row[1])))

    cursor.execute("""\
SELECT DISTINCT board_member.id, board_member.title,
                summary.doc_id, summary.value
           FROM document board_member
           JOIN query_term summary_board_member
             ON summary_board_member.int_val = board_member.id
            AND summary_board_member.path = '%s'
           JOIN query_term summary_board
             ON summary_board.doc_id = summary_board_member.doc_id
            AND summary_board.path = '%s'
            AND LEFT(summary_board.node_loc, 8) = 
                LEFT(summary_board_member.node_loc, 8)
           JOIN query_term summary
             ON summary.doc_id = summary_board.doc_id
            AND summary.path = '%s'
             %s
          WHERE summary_board.int_val = ?""" % (sbmPath, sbPath, stPath,
                                                audienceJoin), 
            boardId)
    for row in cursor.fetchall():
        if not members.has_key(row[0]):
            members[row[0]] = Member(row[0], trim(row[1][:row[1].index(';')]))
        members[row[0]].topics.append(Topic(row[2], 
                    re.sub(";", "--", trim(row[3]))))

except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

keys = members.keys()
keys.sort(lambda a, b: cmp(members[a].name, members[b].name))
for key in keys:
    member = members[key]
    try:
        report += """\
  <FONT SIZE='4'>%s</FONT>
  <TABLE width='100%%' border='0'>
   <TR>
""" % (member.name)
    except:
        cdrcgi.bail("member.name = " + member.name)
        raise
    if member.topics:
        report += """\
"""
        member.topics.sort(lambda a, b: cmp(a.name, b.name))
        for topic in member.topics:

# Decision if the report will be printed with or without CDR ID
# ============================================================
            if showCdrId == 'Yes':
               report += """\
    <TD width='10%%' align='right'><FONT SIZE='-0'>%10d</FONT></TD>
    <TD width='2%%'></TD>
    <TD><FONT SIZE='-0'>%s</FONT></TD>
   </TR>
""" % (topic.id, topic.name)
            else:
               report += """\
    <TD width='5%%'></TD>
    <TD><FONT SIZE='-0'>%s</FONT></TD>
   </TR>
""" % (topic.name)

        report += """\
  </TABLE>
  <BR/>
"""
    report += """\
 </BODY>
</HTML>
"""
cdrcgi.sendPage(header + report)
