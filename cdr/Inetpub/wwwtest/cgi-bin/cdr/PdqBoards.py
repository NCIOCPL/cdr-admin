#----------------------------------------------------------------------
#
# $Id: PdqBoards.py,v 1.2 2002-02-20 23:06:34 bkline Exp $
#
# Report on PDQ Board members and topics.
#
# $Log: not supported by cvs2svn $
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
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "PDQ Board Report"
instr     = "Report on PDQ Board Members and Topics"
script    = "PdqBoards.py"
buttons   = ()
stPath    = '/Summary/SummaryTitle'
sbPath    = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
sbmPath   = '/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref'
trimPat   = re.compile("[\s;]+$")
bmPath    = '/Person/ProfessionalInformation/PDQBoardMembershipDetails/PDQ'\
            '%Board/@cdr:ref'

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
    picklist = "<SELECT NAME='Audience'><OPTION SELECTED>&nbsp;</OPTION>"
    try:
        cursor.execute("""\
SELECT DISTINCT value
           FROM query_term
          WHERE path = '/Summary/SummaryMetaData/SummaryAudience'
       ORDER BY value""")
        for row in cursor.fetchall():
            if row[0]:
                picklist += "<OPTION>%s</OPTION>" % row[0]
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    return picklist + "</SELECT>"

#----------------------------------------------------------------------
# Build a picklist for PDQ Boards.
#----------------------------------------------------------------------
def getBoardPicklist():
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
            picklist += "<OPTION%s>[CDR%010d] %s</OPTION>" % (selected,
                                                              row[0],
                                                              boardTitle)
            selected = ""
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    return picklist + "</SELECT>"

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not boardInfo:
    header   = cdrcgi.header(title, title, instr, script, ("Submit",))
    form     = """\
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
       <TABLE>
        <TR>
         <TD>
          <INPUT TYPE='radio' NAME='RepType' VALUE='ByTopic' checked='1'>
           Order by Topic<BR>
         </TD>
        </TR>
        <TR>
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
""" % (getBoardPicklist(), getAudiencePicklist())
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y", time.localtime(time.time()))

#----------------------------------------------------------------------
# We have a board specified; extract its ID and doc title.
#----------------------------------------------------------------------
pattern   = re.compile(r"\[CDR0*(\d+)\] (.+)")
match     = pattern.match(boardInfo)
if not match: cdrcgi.bail("Board information garbled: %s" % boardInfo)
boardId   = int(match.group(1))
boardName = trim(match.group(2))

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
    instr     = 'Board report by topics -- %s.' % dateString
    header    = cdrcgi.header(title, title, instr, script, buttons)
    report    = """\
  </FORM>
  <H4>Topics for %s</H4>
""" % boardName
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
            if row[2] != prevSummaryId:
                if prevSummaryId:
                    report += """\
  </UL>
"""
                report += """\
  <H4><FONT SIZE='-0'>%s [CDR%010d]</FONT></H4>
  <UL>
""" % (re.sub(";", "--", trim(row[3])), row[2])
                prevSummaryId = row[2]

            report += """\
   <LI><FONT SIZE='-0'>%s [CDR%010d]</FONT></LI>
""" % (re.sub(";", ", ", trim(row[1]), 1), row[0])
        if prevSummaryId:
            report += """\
  </UL>
"""
        report += """\
 </BODY>
</HTML>
"""
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    cdrcgi.sendPage(header + report)

#----------------------------------------------------------------------
# Show the members of the board, with associated topics.
#----------------------------------------------------------------------
instr     = 'Board report by members -- %s.' % dateString
header    = cdrcgi.header(title, title, instr, script, buttons)
members   = {}
topics    = {}
report    = """\
  </FORM>
  <H4>Topics for %s</H4>
""" % boardName

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
            members[row[0]] = Member(row[0], re.sub(";", ", ", trim(row[1])))
        members[row[0]].topics.append(Topic(row[2], 
                    re.sub(";", "--", trim(row[3]))))

except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

keys = members.keys()
keys.sort(lambda a, b: cmp(members[a].name, members[b].name))
for key in keys:
    member = members[key]
    report += """\
  <H4><FONT SIZE='-0'>%s [CDR%010d]</FONT></H4>
""" % (member.name, member.id)
    if member.topics:
        report += """\
  <UL>
"""
        member.topics.sort(lambda a, b: cmp(a.name, b.name))
        for topic in member.topics:
            report += """\
   <LI><FONT SIZE='-0'>%s [CDR%010d]</FONT></LI>
""" % (topic.name, topic.id)
        report += """\
  </UL>
"""
    report += """\
 </BODY>
</HTML>
"""
cdrcgi.sendPage(header + report)
