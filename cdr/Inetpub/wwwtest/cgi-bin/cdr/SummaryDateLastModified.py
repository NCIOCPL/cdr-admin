#----------------------------------------------------------------------
#
# $Id: SummaryDateLastModified.py,v 1.1 2003-05-08 20:26:42 bkline Exp $
#
# Report listing specified set of Cancer Information Summaries, the date
# they were last modified as entered by a user, and the date the last
# Modify action was taken.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
summaryType = fields and fields.getvalue('SummaryType') or None
audience    = fields and fields.getvalue('Audience')    or None
startDate   = fields and fields.getvalue('StartDate')   or None
endDate     = fields and fields.getvalue('EndDate')     or None
SUBMENU     = "Report Menu"
buttons     = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = "SummaryDateLastModified.py"
title       = "CDR Administration"
section     = "Pre-Mailer Protocol Check"
header      = cdrcgi.header(title, title, section, script, buttons)

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
# Build a picklist for Summary Audience.
#----------------------------------------------------------------------
def getAudienceList(cursor):
    sel = " selected='1'"
    picklist = "<select name='Audience'>"
    try:
        cursor.execute("""\
SELECT DISTINCT value
           FROM query_term
          WHERE path = '/Summary/SummaryMetaData/SummaryAudience'
       ORDER BY value""")
        for row in cursor.fetchall():
            if row[0]:
                picklist += "<option%s>%s</option>" % (sel, row[0])
                sel = ""
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving audience choices: %s' % info[1][0])
    return picklist + "</select>"

#----------------------------------------------------------------------
# Generate picklist for Summary type.
#----------------------------------------------------------------------
def getSummaryTypeList(cursor):
    picklist = """\
  <select name='SummaryType'>
   <option value='' selected>All Boards</option>
"""
    try:
        cursor.execute("""\
SELECT DISTINCT board.id, board.title
           FROM document board
           JOIN query_term org_type
             ON org_type.doc_id = board.id
          WHERE org_type.path = '/Organization/OrganizationType'
            AND org_type.value = 'PDQ Editorial Board'
--                                   'PDQ Advisory Board')
--            AND board.title LIKE '%Editorial Board%'
       ORDER BY board.title""")
        for row in cursor.fetchall():
            semi = row[1].find(';')
            if semi != -1: boardTitle = trim(row[1][:semi])
            else:          boardTitle = trim(row[1])
            picklist += """\
   <option value='%d'>%s</option>
""" % (row[0], boardTitle)
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving summary board choices: %s' %
                    info[1][0])
    return picklist + """\
  </select>
"""

#----------------------------------------------------------------------
# Returns a copy of a doc title without trailing whitespace or semicolons.
#----------------------------------------------------------------------
trimPat = re.compile("[\s;]+$")
def trim(s):
    return trimPat.sub("", s)

#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not audience or not startDate or not endDate:
    now = time.time()
    now         = time.localtime(time.time())
    toDate      = time.strftime("%Y-%m-%d", now)
    then        = list(now)
    then[1]    -= 1
    then[2]    += 1
    then        = time.localtime(time.mktime(then))
    fromDate    = time.strftime("%Y-%m-%d", then)
    form = """\
   <h4>Select Summary board, audience, and date range for report
       and press Submit
   </h4>
   <input type='hidden' name='%s' value='%s'>
   <table border='0'>
    <tr>
     <td align='right' nowrap='1'>PDQ Board:&nbsp;</td>
     <td>%s</td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>Summary Audience:&nbsp;</td>
     <td>%s</td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>Date Last Modified:&nbsp;</td>
     <td><input size='20' name='StartDate' value='%s'></td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>&nbsp;</td>
     <td><input size='20' name='EndDate' value='%s'></td>
    </tr>
   </table>
""" % (cdrcgi.SESSION, session, getSummaryTypeList(cursor),
       getAudienceList(cursor), fromDate, toDate)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")

#----------------------------------------------------------------------
# Find the summaries that belong in the report.
#----------------------------------------------------------------------
boardFilter = "AND bn.value LIKE '%Editorial Board'"
if summaryType:
    boardFilter = "AND bn.doc_id = %s" % summaryType
try:
    cursor.execute("""\
        SELECT DISTINCT st.doc_id,
                        st.value AS summary_title,
                        bn.value AS board_name,
                        au.value AS audience,
                        lm.value AS last_mod,
                        MAX(audit_trail.dt) AS audit_date
                   FROM query_term st
                   JOIN query_term sb
                     ON sb.doc_id = st.doc_id
                   JOIN query_term au
                     ON au.doc_id = sb.doc_id
                   JOIN query_term lm
                     ON lm.doc_id = au.doc_id
                   JOIN query_term bn
                     ON bn.doc_id = sb.int_val
                   JOIN audit_trail
                     ON audit_trail.document = st.doc_id
                  WHERE st.path = '/Summary/SummaryTitle'
                    AND sb.path = '/Summary/SummaryMetaData/PDQBoard'
                                + '/Board/@cdr:ref'
                    AND au.path = '/Summary/SummaryMetaData/SummaryAudience'
                    AND lm.path = '/Summary/DateLastModified'
                    AND bn.path = '/Organization/OrganizationNameInformation'
                                + '/OfficialName/Name'
                    AND au.value = ?
                    AND lm.value BETWEEN ? AND DATEADD(s, -1, DATEADD(d, 1, ?))
                    %s
               GROUP BY bn.value,
                        au.value,
                        st.value,
                        st.doc_id,
                        lm.value
               ORDER BY bn.value,
                        au.value,
                        st.value""" % boardFilter, (audience,
                                                    startDate,
                                                    endDate), timeout = 300)
    row = cursor.fetchone()
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving report information: %s' % info[1][0])
if not row:
    cdrcgi.bail("No summaries match report criteria")

#----------------------------------------------------------------------
# Start the HTML page.
#----------------------------------------------------------------------
if not summaryType:
    title = "All Boards/%s" % audience
else:
    title = "%s/%s" % (row[2], audience)
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   body { font-family: sans-serif }
   span.title { font-size: 20; font-weight: bold; text-align: center; }
   span.subtitle { font-size: 18; text-align: center; }
   th { font-size: 16; font-weight: bold; vertical-align: top; }
   td { font-family: sans-serif; font-size: 16; }
   span.audience { font-size: 16; font-weight: bold; }
   span.board    { font-size: 18; font-weight: bold; }
  </style>
 </head>
 <body>
  <center>
   <span class='title'>Summary Date Last Modified Report</span><br>
   <span class='subtitle'>%s to %s</span>
  </center>
  <br><br>
""" % (title, startDate, endDate)

#----------------------------------------------------------------------
# Walk through the rows.
#----------------------------------------------------------------------
lastBoard = None
while row:
    docId, title, board, audience, lastMod, auditDate = row
    if lastBoard != board:
        if lastBoard:
            html += """\
  </table>
  <br><br>
"""
        html += """\
  <span class='board'>%s</span><br>
  <span class='audience'>%s</span>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th width='500'>Summary Title</th>
    <th width='150'>DocID</th>
    <th width='120'>Date Last Modified (User)</th>
    <th width='120'>Last Modify Action Date (System)</th>
   </tr>
""" % (board, audience)
        lastBoard = board
    html += """\
   <tr>
    <td>%s</td>
    <td valign='top'>CDR%010d</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (cgi.escape(title), docId, lastMod,
       auditDate and auditDate[:10] or "&nbsp;")
    try:
        row = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail('Failure fetching report information: %s' % info[1][0])

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
