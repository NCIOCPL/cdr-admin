#----------------------------------------------------------------------
#
# $Id: SummaryDateLastModified.py,v 1.7 2005-07-14 09:49:41 bkline Exp $
#
# Report listing specified set of Cancer Information Summaries, the date
# they were last modified as entered by a user, and the date the last
# Modify action was taken.
#
# $Log: not supported by cvs2svn $
# Revision 1.6  2005/07/13 01:28:03  bkline
# Fixed bug in test of audience for lookup of abbreviation.
#
# Revision 1.5  2005/05/27 17:21:03  bkline
# Modifications requested by Sheri (issue #1698): converted to Excel
# workbook; added three new columns for System report.
#
# Revision 1.4  2003/12/16 15:50:23  bkline
# Fixed bug in title display showing which date range user specified.
#
# Revision 1.3  2003/12/03 20:42:14  bkline
# Added designation of which date range was specified (user or system).
#
# Revision 1.2  2003/11/03 00:24:51  bkline
# Changes requested by issue #913.
#
# Revision 1.1  2003/05/08 20:26:42  bkline
# New summary reports.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time, pyXLWriter, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
summaryType = fields and fields.getvalue('SummaryType')   or None
audience    = fields and fields.getvalue('Audience')      or None
uStartDate  = fields and fields.getvalue('UserStartDate') or None
uEndDate    = fields and fields.getvalue('UserEndDate')   or None
sStartDate  = fields and fields.getvalue('SysStartDate')  or None
sEndDate    = fields and fields.getvalue('SysEndDate')    or None
SUBMENU     = "Report Menu"
buttons     = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = "SummaryDateLastModified.py"
title       = "CDR Administration"
section     = "Summary Date Last Modified"
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
if not audience or ((not uStartDate or not uEndDate) and
                    (not sStartDate or not sEndDate)):
    #now = time.time()
    #now         = time.localtime(time.time())
    #toDate      = time.strftime("%Y-%m-%d", now)
    #then        = list(now)
    #then[1]    -= 1
    #then[2]    += 1
    #then        = time.localtime(time.mktime(then))
    #fromDate    = time.strftime("%Y-%m-%d", then)
    form = """\
   <h4>Select Summary board, Audience, and Date Range by user or system
       and press Submit
   </h4>
   <input type='hidden' name='%s' value='%s' width='100%%'>
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
     <td>&nbsp;</td>
     <td>&nbsp;<br><b>Report by Date Last Modified (User):</b></td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>Start Date:&nbsp;</td>
     <td><input size='20' name='UserStartDate' value='%s'>
      &nbsp;(use YYYY-MM-DD for dates, e.g. 2003-01-01
     </td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>End Date:&nbsp;</td>
     <td><input size='20' name='UserEndDate' value='%s'></td>
    </tr>
    <tr>
     <td colspan='2'>&nbsp;<br><hr><br></td>
    </tr>
    <tr>
     <td>&nbsp;</td>
     <td><b>Report by Last Modified Date (System):</b></td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>Start Date:&nbsp;</td>
     <td><input size='20' name='SysStartDate' value='%s'></td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>End Date:&nbsp;</td>
     <td><input size='20' name='SysEndDate' value='%s'></td>
    </tr>
   </table>
""" % (cdrcgi.SESSION, session, getSummaryTypeList(cursor),
       getAudienceList(cursor), '', '', '', '')
    #fromDate, toDate, fromDate, toDate)
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

if uStartDate and uEndDate:
    sStartDate = '1853-01-01'
    sEndDate   = '9999-12-30'  # Yow!  Y10K bug! :->}
    startDate  = uStartDate
    endDate    = uEndDate
    bodyTitle  = "Summary Date Last Modified (User) Report"
    reportType = 'U'
else:
    uStartDate = '1853-01-01'
    uEndDate   = '9999-12-30'  # Don't do 9999-12-31 (avoid overflow below)
    startDate  = sStartDate
    endDate    = sEndDate
    bodyTitle  = "Summary Last Modified Date (System) Report"
    reportType = 'S'
    cmtConn    = cdrdb.connect('CdrGuest')
    cmtCursor  = cmtConn.cursor()
try:
    cursor.execute("""\
        SELECT DISTINCT st.doc_id,
                        st.value AS summary_title,
                        bn.value AS board_name,
                        au.value AS audience,
                        lm.value AS last_mod,
                        ty.value AS summary_type,
                        MAX(audit_trail.dt) AS audit_date
                   FROM query_term st
                   JOIN query_term ty
                     ON ty.doc_id = st.doc_id
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
                   JOIN action
                     ON action.id = audit_trail.action
                  WHERE st.path = '/Summary/SummaryTitle'
                    AND ty.path = '/Summary/SummaryMetaData/SummaryType'
                    AND sb.path = '/Summary/SummaryMetaData/PDQBoard'
                                + '/Board/@cdr:ref'
                    AND au.path = '/Summary/SummaryMetaData/SummaryAudience'
                    AND lm.path = '/Summary/DateLastModified'
                    AND bn.path = '/Organization/OrganizationNameInformation'
                                + '/OfficialName/Name'
                    AND action.name <> 'UNLOCK'
                    AND au.value = ?
                    
                    /*
                     * Have to convert second date back to VARCHAR(40)
                     * using style 20 (YYYY-MM-DD ...) to avoid blowing
                     * up in the face of invalid date strings in the
                     * documents.
                     */
                    AND lm.value BETWEEN '%s'
                                 AND CONVERT(VARCHAR(40),
                                             DATEADD(s, -1,
                                                     DATEADD(d, 1, '%s')), 20)
                    %s
               GROUP BY bn.value,
                        au.value,
                        st.value,
                        st.doc_id,
                        lm.value,
                        ty.value
                 HAVING MAX(audit_trail.dt) BETWEEN '%s' AND
                                            DATEADD(s, -1, DATEADD(d, 1, '%s'))
               ORDER BY bn.value,
                        au.value,
                        st.value""" % (uStartDate,
                                       uEndDate,
                                       boardFilter,
                                       sStartDate,
                                       sEndDate), (audience,), timeout = 300)
    row = cursor.fetchone()
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving report information: %s' % info[1][0])
if not row:
    cdrcgi.bail("No summaries match report criteria")

#----------------------------------------------------------------------
# Get the comment from the last version of the document.
#----------------------------------------------------------------------
def getComment(docId, cursor):
    cursor.execute("""\
       SELECT comment
         FROM doc_version
        WHERE id = %s
          AND num = (SELECT MAX(num)
                       FROM doc_version
                      WHERE id = %s)""" % (docId, docId))
    rows = cursor.fetchall()
    return rows and rows[0][0] or None

#----------------------------------------------------------------------
# Prepare string for insertion into worksheet cell.
#----------------------------------------------------------------------
def fix(s):
    if not s:
        return ""
    if type(s) == unicode:
        return s.replace(u"\u2019", "'").encode('latin-1', 'replace')
    return str(s)

#----------------------------------------------------------------------
# Map board name to abbreviation.
#----------------------------------------------------------------------
def getBoardAbbreviation(board):
    if board.upper().find('PEDIATRIC') != -1:
        return 'PTEB'
    if board.upper().find('ADULT TREATMENT') != -1:
        return 'ATEB'
    if board.upper().find('COMPLEMENTARY AND ALT') != -1:
        return 'CAM'
    if board.upper().find('SCREENING & PREVENTION') != -1:
        return 'SPEB'
    if board.upper().find('SUPPORTIVE CARE') != -1:
        return 'SCEB'
    if board.upper().find('CANCER GENETICS') != -1:
        return 'CGEB'
    return fix(board)

#----------------------------------------------------------------------
# Map audience name to abbreviation.
#----------------------------------------------------------------------
def getTypeAbbreviation(audience):
    if audience.upper().find('PROFESSIONAL') != -1:
        return 'HP'
    return 'PAT'

#----------------------------------------------------------------------
# Add column headers for a new board/audience combo.
#----------------------------------------------------------------------
def addColHeaders(sheet, rowNum, repType, format):
    colNum = 0
    sheet.write_string([rowNum, colNum], "DocID", format)
    colNum += 1
    sheet.write_string([rowNum, colNum], "Summary Title", format)
    colNum += 1
    if repType == 'S':
        sheet.write_string([rowNum, colNum], "Board", format)
        colNum += 1
        sheet.write_string([rowNum, colNum], "Type", format)
        colNum += 1
        sheet.write_string([rowNum, colNum], "Last Comment", format)
        colNum += 1
    sheet.write_string([rowNum, colNum], "Date Last Modified", format)
    colNum += 1
    sheet.write_string([rowNum, colNum], "Last Modify Action Date (System)",
                       format)
    colNum += 1
    sheet.write_string([rowNum, colNum], "LastV Publish?", format)

#----------------------------------------------------------------------
# Create the workbook.
#----------------------------------------------------------------------
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
if not summaryType:
    title = "All Boards/%s" % audience
else:
    title = "%s/%s" % (row[2], audience)
stamp     = time.strftime("%Y%m%d%H%M%S")
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=sdlm-%s.xls" % stamp
print
book      = pyXLWriter.Writer(sys.stdout)
sheet     = book.add_worksheet("Summary Date Last Modified")
rowNum    = 1
format1   = book.add_format()
format2   = book.add_format()
format3   = book.add_format()
format4   = book.add_format()
format5   = book.add_format()
format1.set_bold();
format1.set_size(12)
format1.set_align('center')
format1.set_merge(1)
format2.set_bold();
format2.set_size(12)
format2.set_merge(0)
format2.set_align('left')
format3.set_bold();
format3.set_size(12)
format3.set_merge(0)
format3.set_align('center')
format3.set_text_wrap(1)
format4.set_align('center')
format5.set_align('center')
format5.set_color('blue')
format5.set_underline(1)

sheet.write_string([0, 0], fix(bodyTitle), format1)
colNum = 0
sheet.set_column(colNum, 12)
colNum += 1
sheet.set_column(colNum, 50)
sheet.write_blank([0, colNum], format1)
colNum += 1
if reportType == 'S':
    sheet.set_column(colNum, 14)
    sheet.write_blank([0, colNum], format1)
    colNum += 1
    sheet.set_column(colNum, 7)
    sheet.write_blank([0, colNum], format1)
    colNum += 1
    sheet.set_column(colNum, 50)
    sheet.write_blank([0, colNum], format1)
    colNum += 1
sheet.set_column(colNum, 15)
sheet.write_blank([0, colNum], format1)
colNum += 1
sheet.set_column(colNum, 15)
sheet.write_blank([0, colNum], format1)
colNum += 1
sheet.set_column(colNum, 10)
sheet.write_blank([0, colNum], format1)

#----------------------------------------------------------------------
# Walk through the rows.
#----------------------------------------------------------------------
lastBoard = None
while row:
    intId, title, board, audience, lastMod, summaryType, auditDate = row
    docId = "CDR%d" % intId
    if summaryType == 'Complementary and alternative medicine':
        summaryType = 'CAM'
    lastVersions = cdr.lastVersions('guest', docId)
    if type(lastVersions) in (type(""), type(u"")):
        lastVFlag = lastVersions
    else:
        lastAny, lastPub, isChanged = lastVersions
        if lastAny == -1:
            lastVFlag = 'N/A'
        elif lastAny == lastPub:
            lastVFlag = 'Y'
        else:
            lastVFlag = 'N'
    if lastBoard != board:
        sheet.write_string([rowNum + 1, 0], fix(board), format2)
        sheet.write_string([rowNum + 2, 0], fix(audience), format2)
        addColHeaders(sheet, rowNum + 3, reportType, format3)
        rowNum += 4
        lastBoard = board
    colNum = 0
    sheet.write_string([rowNum, colNum], docId)
    colNum += 1
    sheet.write_string([rowNum, colNum], fix(title))
    colNum += 1
    if reportType == 'S':
        sheet.write_string([rowNum, colNum], fix(summaryType))
        colNum += 1
        sheet.write_string([rowNum, colNum], getTypeAbbreviation(audience))
        colNum += 1
        comment = getComment(intId, cmtCursor)
        if comment:
            sheet.write_string([rowNum, colNum], fix(comment))
        colNum += 1
    sheet.write_string([rowNum, colNum], fix(lastMod), format4)
    colNum += 1
    if auditDate:
        if reportType == 'S':
            url = ("http://%s/cgi-bin/cdr/AuditTrail.py?id=%s" %
                   (cdrcgi.WEBSERVER, docId))
            sheet.write_url([rowNum, colNum], url, fix(auditDate[:10]),
                            format5)
        else:
            sheet.write_string([rowNum, colNum], fix(auditDate[:10]), format4)
    colNum += 1
    sheet.write_string([rowNum, colNum], lastVFlag, format4)
    row = cursor.fetchone()
    rowNum += 1
book.close()
