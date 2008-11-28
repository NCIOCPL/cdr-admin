#----------------------------------------------------------------------
#
# $Id: BoardMeetingDates.py,v 1.3 2008-11-28 15:08:23 bkline Exp $
#
# Report listing the Board meetings by date or board.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2008/10/15 16:52:53  venglisc
# Added code to include WebEx attribute on the reports. (Bug 4205)
#
# Revision 1.1  2008/08/22 19:45:23  venglisc
# Initial copy of Board Meeting Dates report. (Bug 4205)
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time, ExcelWriter, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
boardPick  = fields.getlist ('boardpick') or []
flavor     = fields.getvalue('Report')    or 'ByBoard'
startDate  = fields.getvalue('StartDate') or None
endDate    = fields.getvalue('EndDate')   or None
SUBMENU    = "Report Menu"
buttons    = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script     = "BoardMeetingDates.py"
title      = "CDR Administration"
section    = "PDQ Editorial Board Meetings"
header     = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script type='text/javascript' language='JavaScript'
           src='/js/CdrCalendar.js'></script>
   <style type='text/css'>
    body          { background-color: #DFDFDF;
                    font-family: sans-serif;
                    font-size: 12pt; }
    legend        { font-weight: bold;
                    color: teal;
                    font-family: sans-serif; }
    fieldset      { width: 500px;
                    margin-left: auto;
                    margin-right: auto;
                    display: block; }
    .CdrDateField { width: 100px; }
   </style>
   <script type='text/javascript' language='JavaScript'>
    function someBoards() {
        document.getElementById('AllBoards').checked = false;
    }
    function allBoards(widget, n) {
        for (var i = 1; i <= n; ++i)
            document.getElementById('E' + i).checked = false;
    }
   </script>
""")
rptStyle = """\
  <style type='text/css'>
   *.board       { font-weight: bold;
                   text-decoration: underline;
                   font-size: 12pt; }
   .dates        { font-size: 11pt; }
   .title        { font-size: 16pt;
                   font-weight: bold;
                   text-align: center; }
   .subtitle     { font-size: 12pt; }
   .blank        { background-color: #FFFFFF; }
  </style>"""
rptHeader  = cdrcgi.rptHeader(title, bkgd = 'FFFFFF', stylesheet = rptStyle)
footer     = """\
 </body>
</html>"""

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])


#----------------------------------------------------------------------
# Build a sequence of Board objects, which holds all the information
# needed for the two reports.  Sequence is sorted by board name.
#----------------------------------------------------------------------
class Board:
    def __init__(self, cdrId, name):
        self.cdrId = cdrId
        self.name = name.replace(' Editorial Board', '')
        self.meetings = []
        if self.name.startswith('PDQ '):
            self.name = self.name[4:]
    def __cmp__(self, other):
        diff = cmp(self.name, other.name)
        if diff:
            return diff
        return cmp(self.cdrId, other.cdrId)
class Meeting:
    def __init__(self, meetingDate, meetingTime, board, webEx = False):
        self.date = meetingDate
        self.time = meetingTime
        self.board = board
        self.webEx = webEx
        try:
            y, m, d = [int(piece) for piece in meetingDate.split('-')]
            normalizedDate = normalizeDate(y, m, d)
            self.englishDate = time.strftime("%B %d, %Y", normalizedDate)
            self.dayOfWeek = time.strftime("%A", normalizedDate)
        except Exception, e:
            # cdrcgi.bail("%s: %s" % (date, e))
            self.prettyDate = self.dayOfWeek = "???"
    def __cmp__(self, other):
        diff = cmp(self.date, other.date)
        if diff:
            return diff
        return cmp(self.board.name, other.board.name)
def collectBoardMeetingInfo(cursor):
    cursor.execute("""\
SELECT DISTINCT a.id, n.value, d.value, t.value, w.value
           FROM active_doc a
           JOIN query_term n
             ON n.doc_id = a.id
           JOIN query_term o
             ON o.doc_id = a.id
           JOIN query_term d
             ON d.doc_id = a.id
           JOIN query_term t
             ON t.doc_id = d.doc_id
            AND LEFT(t.node_loc, 12) = LEFT(d.node_loc, 12)
LEFT OUTER JOIN query_term w
             ON w.doc_id = d.doc_id
            AND LEFT(w.node_loc, 12) = LEFT(d.node_loc, 12)
            AND w.path = '/Organization/PDQBoardInformation/BoardMeetings' +
                         '/BoardMeeting/MeetingDate/@WebEx'
          WHERE o.value IN ('PDQ Advisory Board', 'PDQ Editorial Board')
            AND o.path = '/Organization/OrganizationType'
            AND n.path = '/Organization/OrganizationNameInformation' +
                         '/OfficialName/Name'
            AND d.path = '/Organization/PDQBoardInformation/BoardMeetings' +
                         '/BoardMeeting/MeetingDate'
            AND t.path = '/Organization/PDQBoardInformation/BoardMeetings' +
                         '/BoardMeeting/MeetingTime'""", timeout = 600)
    boards = {}
    for cdrId, boardName, meetingDate, meetingTime, webEx in cursor.fetchall():
        board = boards.get(cdrId)
        if not board:
            board = Board(cdrId, boardName)
            boards[cdrId] = board
        board.meetings.append(Meeting(meetingDate, meetingTime, board, webEx))
    boards = boards.values()
    boards.sort()
    return boards

#----------------------------------------------------------------------
# Generate fields for selecting which boards should be included in the
# report.
#----------------------------------------------------------------------
def makeBoardSelectionFields(boards):
    html = [u"""\
    <fieldset>
     <legend> Select Board Names </legend>
     &nbsp;
     <input name='boardpick' type='checkbox' CHECKED id='AllBoards'
            class='choice'
            onclick='javascript:allBoards(this, %d)'
            value='all'> All <br>
""" % len(boards)]
    i = 1
    for board in boards:
        html.append(u"""\
     &nbsp;
     <input name='boardpick' type='checkbox' value='%d' class='choice'
            onclick='javascript:someBoards()' id='E%d'> %s <br>
""" % (board.cdrId, i, cgi.escape(board.name)))
        i += 1
    html.append(u"""\
    </fieldset>
""")
    return u"".join(html)

#----------------------------------------------------------------------
# Normalize a year, month, day tuple into a standard date-time value.
#----------------------------------------------------------------------
def normalizeDate(y, m, d):
    return time.localtime(time.mktime((y, m, d, 0, 0, 0, 0, 0, -1)))

#----------------------------------------------------------------------
# Generate a pair of dates suitable for seeding the user date fields.
#----------------------------------------------------------------------
def getDefaultDates():
    import time
    yr, mo, da, ho, mi, se, wd, yd, ds = time.localtime()
    startYear = normalizeDate(yr, 1, 1)
    endYear   = normalizeDate(yr, 12, 31)
    return (time.strftime("%Y-%m-%d", startYear),
            time.strftime("%Y-%m-%d", endYear))

# ---------------------------------------------------------------------
# *** Main starts here ***
# ---------------------------------------------------------------------
boards = collectBoardMeetingInfo(cursor)

#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not (boardPick and startDate and endDate):
    startDate, endDate = getDefaultDates()
    form = """\
   <input type='hidden' name='%s' value='%s'>
   <fieldset class='rtype'>
    <legend>&nbsp;Select Report Type&nbsp;</legend>
    <input type='radio' name='Report' value='ByBoard' id='byboard' CHECKED>
    <label for='byboard'>Display by Board</label>
    <br>
    <input type='radio' name='Report' value='ByDate' id='bydate'>
    <label for='bydate'>Display by Date</label>
   </fieldset>
   <p></p>
%s
   <p></p>
   <fieldset class='dates'>
    <legend>&nbsp;Report for this time frame&nbsp;</legend>
    <label for='ustart'>Start Date:</label>
    <input name='StartDate' value='%s' class='CdrDateField'
           id='ustart'> &nbsp;
    <label for='uend'>End Date:</label>
    <input name='EndDate' value='%s' class='CdrDateField'
           id='uend'>
   </fieldset>
  </form>
""" % (cdrcgi.SESSION, session,
       makeBoardSelectionFields(boards), startDate, endDate)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")


# Create the report and display dates by Board
# --------------------------------------------
if flavor == 'ByBoard':
    html = ["""\
 <table>
  <tr>
   <td class="title">
    PDQ Editorial Board Meetings<br>
    <span class="subtitle">(between %s and %s)</span>
   </td>
  </tr>
 </table>
 <p></p>
""" % (startDate, endDate)]

    # Display data by board
    # ---------------------
    for board in boards:
         if str(board.cdrId) in boardPick or boardPick[0] == 'all':
             html.append("""
 <table>
  <tr>
   <td class="board">%s</td>
  </tr>
""" % cgi.escape(board.name))
             board.meetings.sort()
             for meeting in board.meetings:
                 if meeting.date >= startDate and meeting.date <= endDate:
                     html.append("""\
  <tr>
   <td class="dates">%s %s %s</td>
  </tr>
""" % (meeting.date, meeting.time or "", meeting.webEx and ' (WebEx)' or ''))

             html.append("""\
 </table>
 <p></p>
""")
    html = "".join(html)

# Show the meeting information arranged by meeting dates.
# -------------------------------------------------------
else:
    # First we're displaying the title and create the table layout
    # ------------------------------------------------------------
    html = ["""\
 <body>
  <table width="850px">
   <tr>
    <td class="title">
     PDQ Editorial Board Meetings<br>
     <span class="subtitle">(between %s and %s)</span>
    </td>
   </tr>
  </table>
  <p></p>
  <table>
   <tr>
    <th>Date</th>
    <th>Day</th>
    <th>Time</th>
    <th>WebEx</th>
    <th>Board</th>
   </tr>""" % (startDate, endDate)]

    # Reshuffle the boardInfo list so we can sort by date accross
    # all boards
    # -----------------------------------------------------------
    meetings = []
    for board in boards:
        meetings += board.meetings
    meetings.sort()
    # mtgsByDate = getMeetingsByDate(boardInfo)
    # cdrcgi.bail(mtgsByDate)
    lastDate = startDate # prettyDate(startDate)[1][:3]
    monthBlocks = 0

    # Display Data by Date
    # --------------------
    #for date, boardName, boardId, mtgTime, isWebEx in mtgsByDate:
    for meeting in meetings:
        if meeting.date >= startDate and meeting.date <= endDate:
            if str(meeting.board.cdrId) in boardPick or boardPick[0] == 'all':
                # We want to add a space between each month
                # Checking if we're still in the same month as the last row
                # ---------------------------------------------------------
                if lastDate[:7] != meeting.date[:7]:
                    # cdrcgi.bail("%s vs. %s" % (lastDate, meeting.date))
                    monthBlocks += 1
                    html.append("""
   <tr class="blank">
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
   </tr>""")
                # Display the records in a table row format
                # -----------------------------------------
                bg = monthBlocks % 2 == 0 and 'even' or 'odd'
                html.append("""
   <tr class="%s">
    <td width="150px" class="dates" align='center'>%s</td>
    <td width="70px" class="dates" align='center'>%s</td>
    <td width="200px" class="dates" align='center'>%s</td>
    <td width="60px" class="dates" align='center'>%s</td>
    <td width="330px" class="dates">%s</td>
   </tr>""" % (bg, meeting.date, meeting.dayOfWeek, meeting.time,
               meeting.webEx and 'Yes' or '', cgi.escape(meeting.board.name)))

            lastDate = meeting.date

    html.append("""
  </table>
""")
    html = u"".join(html)

# We have everything we need.  Show it to the user
# ------------------------------------------------
cdrcgi.sendPage(rptHeader + html + footer)
