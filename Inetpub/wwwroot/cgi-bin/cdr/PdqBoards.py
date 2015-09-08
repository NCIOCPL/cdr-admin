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
import cgi, cdrcgi, re, cdrdb, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
boardInfo = fields and fields.getvalue("BoardInfo")      or None
audience  = fields and fields.getvalue("Audience")       or None
repType   = fields and fields.getvalue("RepType")        or None
showCdrId = fields and fields.getvalue("ShowCdrId")      or None
pubOnly   = fields and fields.getvalue("pubOnly")        or None
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

# CSS styling for both types of report
listStyle = """
  <style type='text/css'>
   *.group   { font-family: Arial; font-size: 12pt; font-weight: bold }
   *.content { font-family: Arial; font-size: 12pt; font-weight: normal }
   ul        { list-style-type: none; }
  </style>
"""

#----------------------------------------------------------------------
# If the user requests published Summaries only, we need query_term_pub
#  for any selection of the Summary documents themselves.
# All other query_term selections use the current working document to
#  get the latest values for board members, orgs, picklists, etc.
#----------------------------------------------------------------------
if pubOnly == 'Yes':
    qTermTbl = 'query_term_pub'
else:
    qTermTbl = 'query_term'

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

def getAudiences():
    """
    Return a list of audiences as derived in this function.

    See also cdr.getSummaryAudiences() for a different approach.

    Return:
        List of strings, e.g., ['Health professionals', 'Patients'].
    """
    audiences = []
    try:
        cursor.execute("""\
SELECT DISTINCT value
           FROM query_term
          WHERE path = '/Summary/SummaryMetaData/SummaryAudience'
       ORDER BY value""")
        for row in cursor.fetchall():
            if row[0]:
                audiences.append(row[0])
    except cdrdb.Error as e:
        cdrcgi.bail('Database failure - Audiences: %s' % str(e))

    return audiences

#----------------------------------------------------------------------
# Build a picklist for Summary Audience.
#----------------------------------------------------------------------
def getAudiencePicklist():
    picklist = "<SELECT NAME='Audience'>"
    selected = " SELECTED"
    audiences = getAudiences()
    for audience in audiences:
        picklist += "<OPTION%s>%s</OPTION>" % (selected, audience)
        selected = ""

    return picklist + "</SELECT>"

def getBoardIdNames(includeIds):
    """
    Get a list of board names and, optionally, board CDR IDs

    Used by getBoardPicklist to construct a picklist, and by parameter
    validation to ensure that the value passed back from the form is really
    from the list and not a hacker introduced value.

    Pass:
        includeIds - True = get the Board Organization document CDR IDs as
                     well as the names.  Format = list of tuples of
                     (boardId, name).
                     False = get names only.  Format = list of strings.
    Return:
        List of board names and optional IDs matching the query, ordered
        alphabetically by board name.
        Board names only contain the name, i.e. the part of the document
        title up to but not including the semicolon.
    """
    global cursor

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
    except cdrdb.Error, info:
        cdrcgi.bail('Database failure - Board names: %s' % info[1][0])

    boards = []
    for row in cursor.fetchall():
        # Extract name part of the board
        semi = row[1].find(';')
        if semi != -1: boardTitle = trim(row[1][:semi])
        else:          boardTitle = trim(row[1])

        # Save id,name or just name
        if includeIds:
            boards.append((row[0], boardTitle))
        else:
            boards.append(boardTitle)

    return boards

#----------------------------------------------------------------------
# Build a picklist for PDQ Boards.
#----------------------------------------------------------------------
def getBoardPicklist(boardDict):
    """
    Create a board picklist.

    Also populate a passed dictionary with name = CDR Organization doc ID.

    Pass:
        boardDict - Reference to a dictionary to update with name => ID.

    Return:
        HTML format picklist, boardDict is also updated.
    """
    picklist = "<SELECT NAME='BoardInfo'>"
    selected = " SELECTED"

    idNames = getBoardIdNames(True)

    for docId, boardName in idNames:
        # Top One is selected by default
        picklist += "<OPTION%s>%s</OPTION>" % (selected, boardName)
        selected = ""
        boardDict[boardName] = docId

    return picklist + "</SELECT>"

#----------------------------------------------------------------------
# Create an HTML block listing a summary with its board members
#----------------------------------------------------------------------
def makeSummaryDisplay(summaryId, members, cdrId='No'):
    """
    Create display for a single summary, and within that, board members
    linked to that Summary

    Pass:
        summaryId - CDR ID as an integer.
        members   - array of:
                        board member CDR ID
                        board member title
                        summary CDR ID from board member document
                        summary title
                        module only specifier, or None
    Return:
        Block of html for one Summary.
    """

    # Begin a paragraph
    html = "<p>"

    # Create a summary header row if and only if there are any people linked
    #  to this summary.
    # Walking through the members, we create the header row if and when we
    #  find the first member actually linked in his own record.
    headrow = False
    for member in members:

        if member[2] == summaryId:
            if not headrow:
                # Prepare a CDR ID if requested
                cdrId = ""
                if showCdrId == "Yes":
                    cdrId = " (%d)" % summaryId

                # Same for module indicator
                module = ""
                if member[4]:
                    module = " (Module)"

                # Prepare Summary topic line
                # css affects browser display, <b> affects Word display
                html += "<span class='group'><b>%s%s%s</b></span>\n" % (
                                trim(member[3]), module, cdrId)

                # Start the unordered list of members
                html += " <ul>\n"

                # Don't print the summary name again
                headrow = True

            # Print the data rows (the board member name)
            html += "   <li><span class='content'>%s</span></li>\n" % \
                        trim(member[1][:member[1].index(';')])

        # DEBUG
        # else:
        #     cdr.logwrite("no summaryId match for member: %s" % str(member))

    # Close the list and paragraph
    html += "  </ul>\n </p>\n"

    return html

#----------------------------------------------------------------------
# Validate inputs
#----------------------------------------------------------------------
if request:  cdrcgi.valParmVal(request,
                               valList=('Submit', SUBMENU, cdrcgi.MAINMENU))
if boardInfo: cdrcgi.valParmVal(boardInfo,
                               valList=getBoardIdNames(False))
if audience: cdrcgi.valParmVal(audience,
                               valList=getAudiences())
if repType: cdrcgi.valParmVal(repType,
                               valList=('ByTopic', 'ByMember'))
if showCdrId: cdrcgi.valParmVal(showCdrId,
                               valList=('Yes', 'No'))
if pubOnly: cdrcgi.valParmVal(pubOnly, valList='Yes')

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
boardList = {}
if not boardInfo:
    header   = cdrcgi.header(title, title, instr, script, ("Submit",
                                                           SUBMENU,
                                                           cdrcgi.MAINMENU))
    form     = u"""\
  <style type='text/css'>
   *         { font-family: Arial; }
  </style>
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <fieldset>
       <legend>&nbsp;Select Board and Audience&nbsp;</legend>
        <B>PDQ Board:&nbsp;</B>
        <br>%s
        <br>
        <B>Summary Audience:&nbsp;</B>
        <br>%s
      </fieldset>
      <br>
      <fieldset>
         <div style="float:left; width:120px;">
         <b>Display Cdr-Id:</b>
         </div>
         <div style="float:left; width:70px;">
          <INPUT TYPE='radio' NAME='ShowCdrId' VALUE='Yes' id='y1'>
          <label for='y1'>Yes</label>
         </div>
         <div style="float:left; width:120px;">
          <INPUT TYPE='radio' NAME='ShowCdrId' VALUE='No' id='n1' checked='1'>
          <label for='n1'>No</label>
         </div>
          <br>

         <div style="float:left; clear:left; width:120px;">
         <b>Order by:</b>
         </div>
         <div style="float:left; width:70px;">
          <INPUT TYPE='radio' NAME='RepType' VALUE='ByTopic' id='y2'
                                                          checked='1'>
          <label for='y2'>Topic</label>
         </div>
         <div style="float:left; width:150px;">
          <INPUT TYPE='radio' NAME='RepType' VALUE='ByMember' id='n2'>
          <label for='n2'>Board Member</label>
         </div>

      </fieldset>
      <br>
      <fieldset>
         <label><b>Only published Summaries:</b>
         <INPUT TYPE='checkbox' NAME='pubOnly' VALUE='Yes' checked='1' id='n3' /></label>
      </fieldset>
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
    header    = cdrcgi.header(title, title, instr, script, buttons,
                              stylesheet=listStyle)
    audString = ""
    if audience:
        audString = "<BR>(%s)" % audience
    report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
  <H4>Topics for %s%s</H4>
""" % (cdrcgi.SESSION, session, boardName, audString)
    try:
        query = """\
SELECT DISTINCT board_member.id, board_member.title,
                summary.doc_id, summary.value, mod.value
           FROM document board_member
           JOIN query_term summary_board_member
             ON summary_board_member.int_val = board_member.id
            AND summary_board_member.path = '%s'
           JOIN query_term summary_board
             ON summary_board.doc_id = summary_board_member.doc_id
            AND summary_board.path = '%s'
            AND LEFT(summary_board.node_loc, 8) =
                LEFT(summary_board_member.node_loc, 8)
           JOIN %s summary
             ON summary.doc_id = summary_board.doc_id
            AND summary.path = '%s'
             %s
           LEFT OUTER JOIN query_term mod
             ON mod.doc_id = summary.doc_id
            AND mod.path = '/Summary/@ModuleOnly'
           JOIN document d
             ON d.id = summary.doc_id
            AND d.active_status = 'A'
          WHERE summary_board.int_val = ?
       ORDER BY summary.value, board_member.title""" % (
                    sbmPath, sbPath, qTermTbl, stPath, audienceJoin)

        cursor.execute(query, boardId)
        prevSummaryId = 0
        rows = cursor.fetchall()

    except cdrdb.Error, info:
        cdrcgi.bail('Database failure - Board members: %s' % info[1][0])

    # Create a dictionary of summaries and IDs and sort
    # -------------------------------------------------
    summaries  = [i[3] for i in rows]
    sumDict = dict.fromkeys(summaries)
    summaryInfo  = [[i[3], i[2]] for i in rows]

    # Create the dictionary from a list
    for name, id in summaryInfo:
        sumDict[name] = id

    # Display the information sorted by summary names
    sumSort = sumDict.keys()
    sumSort.sort()

    # Create a HTML table for each topic and list the board members
    # -------------------------------------------------------------
    for summary in sumSort:
        report += makeSummaryDisplay(sumDict[summary], rows, showCdrId)

    # Finish up the report output
    # ===========================
    report += """\
  </TABLE>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(header + report)

#----------------------------------------------------------------------
# Show the members of the board, with associated topics.
#----------------------------------------------------------------------
instr     = 'Board Report by Members -- %s.' % dateString
header    = cdrcgi.header(title, title, instr, script, buttons,
                          stylesheet=listStyle)
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
# Construct a report with major headings for board member followed by a list
# of Summaries linked to that board member.
#
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
                summary.doc_id, summary.value, mod.value
           FROM document board_member
           JOIN query_term summary_board_member
             ON summary_board_member.int_val = board_member.id
            AND summary_board_member.path = '%s'
           JOIN query_term summary_board
             ON summary_board.doc_id = summary_board_member.doc_id
            AND summary_board.path = '%s'
            AND LEFT(summary_board.node_loc, 8) =
                LEFT(summary_board_member.node_loc, 8)
           JOIN %s summary
             ON summary.doc_id = summary_board.doc_id
            AND summary.path = '%s'
             %s
           LEFT OUTER JOIN query_term mod
             ON mod.doc_id = summary.doc_id
            AND mod.path = '/Summary/@ModuleOnly'
           JOIN document d
             ON d.id = summary.doc_id
            AND d.active_status = 'A'
          WHERE summary_board.int_val = ?""" % (
                    sbmPath, sbPath, qTermTbl, stPath, audienceJoin), boardId)
    for row in cursor.fetchall():
        if not members.has_key(row[0]):
            members[row[0]] = Member(row[0], trim(row[1][:row[1].index(';')]))
        members[row[0]].topics.append(Topic(row[2],
                    re.sub(";", "--", trim(row[3]))))

except cdrdb.Error, info:
    cdrcgi.bail('Database failure - Board members 2: %s' % info[1][0])

keys = members.keys()
keys.sort(lambda a, b: cmp(members[a].name, members[b].name))
for key in keys:
    member = members[key]
    try:
        report += "<p><span class='group'><b>%s</b></span></p>\n <ul>\n" \
                   % member.name
    except:
        cdrcgi.bail("member.name = " + member.name)
        raise
    if member.topics:
        member.topics.sort(lambda a, b: cmp(a.name, b.name))
        for topic in member.topics:

            # Prepare a CDR ID if requested
            cdrId = ""
            if showCdrId == "Yes":
                cdrId = " (%d)" % topic.id

            # Create the line for the topic
            report += " <li><span class='content'>%s%s</span></li>\n" \
                        % (topic.name, cdrId)
        report += " </ul>\n</p>\n"

report += """\
 </BODY>
</HTML>
"""
cdrcgi.sendPage(header + report)
