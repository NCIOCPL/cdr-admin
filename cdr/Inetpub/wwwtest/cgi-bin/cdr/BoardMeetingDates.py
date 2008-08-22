#----------------------------------------------------------------------
#
# $Id: BoardMeetingDates.py,v 1.1 2008-08-22 19:45:23 venglisc Exp $
#
# Report listing the Board meetings by date or board.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time, ExcelWriter, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
boardPick  = fields.getlist ('boardpick')           or []
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
# Create list of boards with all meeting dates
# Returns a dictionary of the format
#    {CDR-ID:[BoardName, [Date1, Date2, Date3, ...], Time]}
# which holds all information necessary for the two reports.
#----------------------------------------------------------------------
def getScheduleInformation(cursor):
    cursor.execute("""\
SELECT distinct d.id, 
       n.value  AS BoardName,
       t.value  AS BoardType, 
       y.value  AS myYear, 
       dd.value AS myDate, 
       tt.value AS myTime
  FROM query_term n
  JOIN query_term t
    ON t.doc_id = n.doc_id
  JOIN document d
    ON n.doc_id = d.id
  JOIN query_term y
    ON y.doc_id = d.id
  JOIN query_term dd
    ON dd.doc_id = d.id
  JOIN query_term tt
    ON tt.doc_id = d.id
 WHERE t.value in ('PDQ Advisory Board', 'PDQ Editorial Board')
   AND t.path  = '/Organization/OrganizationType'
   AND n.path  = '/Organization/OrganizationNameInformation/OfficialName/Name'
   AND y.path  = '/Organization/PDQBoardInformation/BoardMeetingDate/Year'
   AND dd.path = '/Organization/PDQBoardInformation/BoardMeetingDate/Date'
   AND tt.path = '/Organization/PDQBoardInformation/BoardMeetingDate/DayTime'
   AND SUBSTRING(dd.node_loc, 1, 8) = SUBSTRING(y.node_loc, 1, 8) 
   AND SUBSTRING(tt.node_loc, 1, 8) = SUBSTRING(y.node_loc, 1, 8) 
   AND d.doc_type = 22
   AND active_status = 'A'
 ORDER BY n.value
                   """, timeout = 600)
    rows = cursor.fetchall()
    boardInfo = {}
    for cdrId, boardName, boardType, myYear, myDate, myTime in rows:
        if not boardInfo.has_key(cdrId):
             boardInfo[cdrId] = [boardName]
             boardInfo[cdrId].append([])
             boardInfo[cdrId].append(myTime)
        
        boardInfo[cdrId][1].append(myDate)

    return boardInfo


#----------------------------------------------------------------------
# Create list of all board names with all meeting dates
#----------------------------------------------------------------------
def getBoardNames(boardInfo):
    boardNames = []

    # Store the values are [Name, CDR-id] so we can easily
    # sort the list alphabetically
    # -----------------------------------------------------
    for cdrId in boardInfo.keys():
        if boardInfo[cdrId][0].startswith('PDQ '):
            boardInfo[cdrId][0] = boardInfo[cdrId][0][4:]
        boardNames.append([boardInfo[cdrId][0], cdrId, boardInfo[cdrId][2]])

    return boardNames


#----------------------------------------------------------------------
# Generate picklist for Summary type.
#----------------------------------------------------------------------
def displayBoardPicklist(allBoards):
    html = [u"""\
    <fieldset>
     <legend> Select Board Names </legend>
     &nbsp;
     <input name='boardpick' type='checkbox' CHECKED id='AllBoards'
            class='choice'
            onclick='javascript:allBoards(this, %d)'
            value='all'> All <br>
""" % len(allBoards)]
    i = 1
    #for docId, docTitle, bType, bYear, bDate, bTime in rows:
    for docTitle, docId, time in allBoards:
        if docTitle.startswith('PDQ '):
            docTitle = docTitle[4:]
        edBoard = docTitle.find(' Editorial Board;')
        if edBoard != -1:
            docTitle = docTitle[:edBoard]
        html.append(u"""\
     &nbsp;
     <input name='boardpick' type='checkbox' value='%d' class='choice'
            onclick='javascript:someBoards()' id='E%d'> %s <br>
""" % (docId, i, cgi.escape(docTitle)))
        i += 1
    html.append(u"""\
    </fieldset>
""")
    return u"".join(html)


#----------------------------------------------------------------------
# Generate picklist for Summary type.
#----------------------------------------------------------------------
def getMeetingsByDate(boardInfo):
    newList = []
    for boardId in boardInfo.keys():
        #cdrcgi.bail(boardInfo[boardId])
        for date in boardInfo[boardId][1]:
            newList.append([date, boardInfo[boardId][0], 
                            boardId, boardInfo[boardId][2]])
    newList.sort()
    #cdrcgi.bail(newList)
    return newList


#----------------------------------------------------------------------
# Normalize a year, month, day tuple into a standard date-time value.
#----------------------------------------------------------------------
def normalizeDate(y, m, d):
    return time.localtime(time.mktime((y, m, d, 0, 0, 0, 0, 0, -1)))


#----------------------------------------------------------------------
# Convert an ISO date 'YYYY-mm-dd' into a date of the format
# weekday, Month Day Year
#----------------------------------------------------------------------
def prettyDate(date):
    newDate = time.strptime(date, "%Y-%m-%d")
    fullDate = time.strftime("%A, %B %d, %Y", newDate)
    weekDay = time.strftime("%B %d, %Y", newDate)
    calDay = time.strftime("%A", newDate)

    return (fullDate, weekDay, calDay)


#----------------------------------------------------------------------
# Generate a pair of dates suitable for seeding the user date fields.
#----------------------------------------------------------------------
def genDateValues():
    import time
    yr, mo, da, ho, mi, se, wd, yd, ds = time.localtime()
    startYear = normalizeDate(yr, 1, 1)
    endYear   = normalizeDate(yr, 12, 31)
    return (time.strftime("%Y-%m-%d", startYear),
            time.strftime("%Y-%m-%d", endYear))

# ---------------------------------------------------------------------
# *** Main starts here ***
# ---------------------------------------------------------------------
boardInfo  = getScheduleInformation(cursor)
boardNames = getBoardNames(boardInfo)
boardNames.sort()

#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not boardPick or (not startDate or not endDate):
    startDate, endDate = genDateValues()
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
       displayBoardPicklist(boardNames), startDate, endDate)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")


# Create the report and display dates by Board
# --------------------------------------------
if flavor == 'ByBoard':
    html = """\
 <table>
  <tr>
   <td class="title">
    PDQ Editorial Board Meetings (By Board)<br>
    <span class="subtitle">(between %s and %s)</span>
   </td>
  </tr>
 </table>
 <p></p>
""" % (startDate, endDate)

    # Display data by board
    # ---------------------
    for boardName, boardId, boardTime in boardNames:
         #cdrcgi.bail(boardName)
         if str(boardId) in boardPick or boardPick[0] == 'all':
             html += """
 <table>
  <tr>
   <td class="board">%s (%s)</td>
  </tr>
""" % (boardName, boardTime)
             boardInfo[boardId][1].sort()
             for date in boardInfo[boardId][1]:
                 if date >= startDate and date <= endDate:
                     html += """\
  <tr>
   <td class="dates">%s</td>
  </tr>
""" % prettyDate(date)[0]

             html += """\
 </table>
 <p></p>
"""
# Create the report and display dates by Board
# --------------------------------------------
else:
    # First we're displaying the title and create the table layout
    # ------------------------------------------------------------
    html = """\
 <body>
  <table width="850px">
   <tr>
    <td class="title">
     PDQ Editorial Board Meetings (By Board)<br>
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
    <th>Board</th>
   </tr>""" % (startDate, endDate)

    # Reshuffle the boardInfo list so we can sort by date accross
    # all boards
    # -----------------------------------------------------------
    mtgsByDate = getMeetingsByDate(boardInfo)
    lastDate = prettyDate(startDate)[1][:3]
    rowCount = 0

    # Display Data by Date
    # --------------------
    for date, boardName, boardId, mtgTime in mtgsByDate:
        if date >= startDate and date <= endDate:
            if str(boardId) in boardPick or boardPick[0] == 'all':
                # We want to add a space between each month
                # Checking if we're still in the same month as the last row
                # ---------------------------------------------------------
                if not prettyDate(date)[1].startswith(lastDate):
                    rowCount += 1
                    html += """
   <tr class="blank">
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
   </tr>"""
                # Display the records in a table row format
                # -----------------------------------------
                if rowCount % 2 == 0: bg = 'even'
                else:                 bg = 'odd'
                html += """
   <tr class="%s">
    <td width="180px" class="dates">%s</td>
    <td width="100px" class="dates">%s</td>
    <td width="200px" class="dates">%s</td>
    <td width="400px" class="dates">%s</td>
   </tr>""" % (bg, prettyDate(date)[1], prettyDate(date)[2], 
               mtgTime, boardName)

            lastDate = prettyDate(date)[1][:3]

    html += """
  </table>
"""

# We have everything we need.  Show it to the user
# ------------------------------------------------
cdrcgi.sendPage(rptHeader + html + footer)
