#----------------------------------------------------------------------
#
# $Id: SummaryDateLastModified.py,v 1.10 2007-11-05 15:08:42 bkline Exp $
#
# Report listing specified set of Cancer Information Summaries, the date
# they were last modified as entered by a user, and the date the last
# Modify action was taken.
#
# $Log: not supported by cvs2svn $
# Revision 1.9  2007/11/03 14:15:07  bkline
# Unicode encoding cleanup (issue #3716).
#
# Revision 1.8  2007/10/31 17:41:52  bkline
# Extensively rewritten for request #3635.
#
# Revision 1.7  2005/07/14 09:49:41  bkline
# Changed to ignore UNLOCK rows in the audit table.
#
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
import cdr, cdrdb, cdrcgi, cgi, re, time, ExcelWriter, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
est         = fields.getlist ('est')           or []
sst         = fields.getlist ('sst')           or []
audience    = fields.getvalue('Audience')      or None
uStartDate  = fields.getvalue('UserStartDate') or None
uEndDate    = fields.getvalue('UserEndDate')   or None
sStartDate  = fields.getvalue('SysStartDate')  or None
sEndDate    = fields.getvalue('SysEndDate')    or None
SUBMENU     = "Report Menu"
buttons     = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = "SummaryDateLastModified.py"
title       = "CDR Administration"
section     = "Summary Date Last Modified"
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script language='JavaScript' src='/js/CdrCalendar.js'></script>
   <style type='text/css'>
    body { background-color: #f8f8f8; font-family: sans-serif;
           font-size: 11pt; }
    legend  { font-weight: bold; color: teal; font-family: sans-serif; }
    fieldset { width: 500px; margin-left: auto; margin-right: auto;
               display: block; }
    .CdrDateField { width: 80px; }
   </style>
   <script language='JavaScript'>
    function clearSysDates() {
        document.getElementById('sstart').value = '';
        document.getElementById('send').value = '';
    }
    function clearUserDates() {
        document.getElementById('ustart').value = '';
        document.getElementById('uend').value = '';
    }
    function someEnglish() {
        document.getElementById('AllEnglish').checked = false;
    }
    function someSpanish() {
        document.getElementById('AllSpanish').checked = false;
    }
    function allEnglish(widget, n) {
        for (var i = 1; i <= n; ++i)
            document.getElementById('E' + i).checked = false;
    }
    function allSpanish(widget, n) {
        for (var i = 1; i <= n; ++i)
            document.getElementById('S' + i).checked = false;
    }
   </script>
""")

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
def getAudienceChoices(cursor):
    html = []
    try:
        cursor.execute("""\
SELECT DISTINCT value
           FROM query_term
          WHERE path = '/Summary/SummaryMetaData/SummaryAudience'
       ORDER BY value""")
        for row in cursor.fetchall():
            value = row[0].strip()
            if value:
                html.append(u"""\
    &nbsp;
    <input name='Audience' type='radio' value='%s' class='choice'/> %s <br />
""" % (value, value))
    except Exception:
        cdrcgi.bail("Failure retrieving audience choices: %s" % e)
    html.append(u"""\
    &nbsp;
    <input name='Audience' type='radio' checked='1' value='all'
           class='choice' /> All <br />
""")
    return u"".join(html)

#----------------------------------------------------------------------
# Generate picklist for Summary type.
#----------------------------------------------------------------------
def getSummaryTypeOptions(cursor):
    cursor.execute("CREATE TABLE #board (doc_id INTEGER, title NVARCHAR(512))")
    cursor.execute("CREATE TABLE #english (summary INTEGER, board INTEGER)")
    cursor.execute("CREATE TABLE #spanish (summary INTEGER, english INTEGER)")
    cursor.execute("""\
        INSERT INTO #board
    SELECT DISTINCT board.id, board.title
               FROM document board
               JOIN query_term org_type
                 ON org_type.doc_id = board.id
               JOIN active_doc a
                 ON a.id = board.id
              WHERE org_type.path = '/Organization/OrganizationType'
                AND org_type.value = 'PDQ Editorial Board'""", timeout = 600)
    cursor.execute("""\
        INSERT INTO #english
    SELECT DISTINCT s.doc_id AS summary, s.int_val as board
               FROM query_term s
               JOIN query_term l
                 ON l.doc_id = s.doc_id
               JOIN active_doc a
                 ON a.id = s.doc_id
              WHERE s.path = '/Summary/SummaryMetaData/PDQBoard'
                           + '/Board/@cdr:ref'
                AND l.path = '/Summary/SummaryMetaData'
                           + '/SummaryLanguage'
                AND l.value = 'English'""", timeout = 600)
    cursor.execute("""\
        INSERT INTO #spanish
    SELECT DISTINCT s.doc_id summary, s.int_val as english
               FROM query_term s
               JOIN active_doc a
                 ON a.id = s.doc_id
               JOIN query_term l
                 ON l.doc_id = s.doc_id
              WHERE s.path = '/Summary/TranslationOf/@cdr:ref'
                AND l.path = '/Summary/SummaryMetaData'
                           + '/SummaryLanguage'
                AND l.value = 'Spanish'""", timeout = 600)
    cursor.execute("""\
        SELECT DISTINCT b.doc_id, b.title
                   FROM #board b
                   JOIN #english e
                     ON e.board = b.doc_id""", timeout = 600)
    rows = cursor.fetchall()
    html = [u"""\
    <fieldset>
     <legend>English</legend>
     &nbsp;
     <input name='est' type='checkbox' checked='1' id='AllEnglish'
            class='choice'
            onclick='javascript:allEnglish(this, %d)'
            value='all' /> All <br />
""" % len(rows)]
    i = 1
    for docId, docTitle in rows:
        if docTitle.startswith('PDQ '):
            docTitle = docTitle[4:]
        edBoard = docTitle.find(' Editorial Board;')
        if edBoard != -1:
            docTitle = docTitle[:edBoard]
        html.append(u"""\
     &nbsp;
     <input name='est' type='checkbox' value='%d' class='choice'
            onclick='javascript:someEnglish()' id='E%d' /> %s <br />
""" % (docId, i, cgi.escape(docTitle)))
        i += 1
    cursor.execute("""\
        SELECT DISTINCT b.doc_id, b.title
                   FROM #spanish s
                   JOIN #english e
                     ON s.english = e.summary
                   JOIN #board b
                     ON e.board = b.doc_id""", timeout = 600)
    rows = cursor.fetchall()
    html.append(u"""\
    </fieldset>
    <fieldset>
     <legend>Spanish</legend>
     &nbsp;
     <input name='sst' type='checkbox' id='AllSpanish' class='choice'
            onclick='javascript:allSpanish(this, %d)'
            value='all' /> All <br />
""" % len(rows))
    i = 1
    for docId, docTitle in rows:
        if docTitle.startswith('PDQ '):
            docTitle = docTitle[4:]
        edBoard = docTitle.find(' Editorial Board;')
        if edBoard != -1:
            docTitle = docTitle[:edBoard]
        html.append(u"""\
     &nbsp;
     <input name='sst' type='checkbox' value='%d' class='choice'
            onclick='javascript:someSpanish()' id='S%d' /> %s <br />
""" % (docId, i, cgi.escape(docTitle)))
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
def genDateValues():
    import time
    yr, mo, da, ho, mi, se, wd, yd, ds = time.localtime()
    if wd == 4:
        # Today is Friday; have we reached 6:00 p.m.?
        if (ho, mi, se) >= (18, 0, 0):
            daysToBackUp = 0
        else:
            daysToBackUp = 7
    elif wd < 4:
        daysToBackUp = wd + 3
    else:
        daysToBackUp = wd - 4
    friday = normalizeDate(yr, mo, da - daysToBackUp)
    saturday = normalizeDate(friday[0], friday[1], friday[2] - 6)
    return (time.strftime("%Y-%m-%d", saturday),
            time.strftime("%Y-%m-%d", friday))

#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not audience or not (est or sst) or ((not uStartDate or not uEndDate) and
                                        (not sStartDate or not sEndDate)):
    startDate, endDate = genDateValues()
    form = """\
   <input type='hidden' name='%s' value='%s' width='100%%' />
   <fieldset>
    <legend>Audience</legend>
%s
   </fieldset>
%s
   <fieldset class='dates'>
    <legend>Report by Date Last Modified (User)</legend>
    <label for='ustart'>Start Date:</label>
    <input name='UserStartDate' value='%s' class='CdrDateField'
           id='ustart' onchange='javascript:clearSysDates()' /> &nbsp;
    <label for='uend'>End Date:</label>
    <input name='UserEndDate' value='%s' class='CdrDateField'
           id='uend' onchange='javascript:clearSysDates()' />
   </fieldset>
   <fieldset class='dates'>
    <legend>Report by Date Last Modified (System)</legend>
    <label for='sstart'>Start Date:</label>
    <input name='SysStartDate' class='CdrDateField'
           id='sstart' onchange='javascript:clearUserDates()' /> &nbsp;
    <label for='send'>End Date:</label>
    <input name='SysEndDate' class='CdrDateField'
           id='send' onchange='javascript:clearUserDates()' />
   </fieldset>
  </form>
""" % (cdrcgi.SESSION, session, getAudienceChoices(cursor),
       getSummaryTypeOptions(cursor), startDate, endDate)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")

#----------------------------------------------------------------------
# Collection information we'll need for each summary document.
#----------------------------------------------------------------------
class Summary:
    summaries = {}
    def __init__(self, row, lang, reportType, cursor):
        self.docId       = row[0]
        self.title       = row[1]
        self.board       = row[2]
        self.audience    = row[3]
        self.language    = row[4]
        self.lastMod     = row[5]
        self.summaryType = row[6]
        self.lastSave    = row[7]
        self.comment     = None
        if self.board not in Summary.summaries:
            Summary.summaries[self.board] = {}
        board = Summary.summaries[self.board]
        if self.language not in board:
            board[self.language] = {}
        language = board[self.language]
        if self.audience not in language:
            language[self.audience] = [self]
        else:
            language[self.audience].append(self)
        if reportType == 'S':
            self.comment = Summary.__getComment(self.docId, cursor)
        lastVersions = cdr.lastVersions('guest', "CDR%010d" % self.docId)
        if type(lastVersions) in (type(""), type(u"")):
            self.lastVFlag = lastVersions
        else:
            lastAny, lastPub, isChanged = lastVersions
            if lastAny == -1:
                self.lastVFlag = 'N/A'
            elif lastAny == lastPub:
                self.lastVFlag = 'Y'
            else:
                self.lastVFlag = 'N'
    def __cmp__(self, other):
        result = cmp(self.title, other.title)
        if result:
            return result
        return cmp(self.docId, other.docId)
    @staticmethod
    def __getComment(docId, cursor):
        " Get the comment from the last version of the document."
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
# Find the summaries that belong in the report.
#----------------------------------------------------------------------
sqlSelect = """\
    SELECT DISTINCT su.doc_id         AS doc_id,
                    su.value          AS summary_title,
                    bn.value          AS board_name,
                    au.value          AS audience,
                    la.value          AS language,
                    lm.value          AS last_mod_date,
                    st.value          AS summary_type,
                    ls.last_save_date AS last_save_date
"""
sqlFrom = """\
               FROM query_term su
"""
sqlJoin = """\
               JOIN query_term st
                 ON st.doc_id = su.doc_id
               JOIN query_term bn
                 ON bn.doc_id = sb.int_val
               JOIN query_term au
                 ON au.doc_id = sb.doc_id
               JOIN doc_last_save ls
                 ON ls.doc_id = su.doc_id
               JOIN query_term la
                 ON la.doc_id = su.doc_id
    LEFT OUTER JOIN query_term lm
                 ON lm.doc_id = au.doc_id
"""
sqlWhere = """\
              WHERE su.path = '/Summary/SummaryTitle'
                AND st.path = '/Summary/SummaryMetaData/SummaryType'
                AND sb.path = '/Summary/SummaryMetaData/PDQBoard'
                            + '/Board/@cdr:ref'
                AND au.path = '/Summary/SummaryMetaData/SummaryAudience'
                AND lm.path = '/Summary/DateLastModified'
                AND la.path = '/Summary/SummaryMetaData/SummaryLanguage'
                AND bn.path = '/Organization/OrganizationNameInformation'
                            + '/OfficialName/Name'
"""

#----------------------------------------------------------------------
# Filter on dates, depending on which flavor of the report was requested.
# We have to convert second date back to VARCHAR(40) using style 20
# (YYYY-MM-DD ...) to avoid blowing up in the face of invalid date
# strings in the documents.
#----------------------------------------------------------------------
if uStartDate and uEndDate:
    bodyTitle  = "Summary Date Last Modified (User) Report"
    subtitle   = u"%s - %s" % (uStartDate, uEndDate)
    reportType = 'U'
    dateFilter = """\
                AND lm.value BETWEEN '%s'
                             AND CONVERT(VARCHAR(40),
                                         DATEADD(s, -1,
                                                 DATEADD(d, 1, '%s')), 20)
""" % (uStartDate, uEndDate)
else:
    bodyTitle  = "Summary Last Modified Date (System) Report"
    subtitle   = u"%s - %s" % (sStartDate, sEndDate)
    reportType = 'S'
    dateFilter = """\
                AND ls.last_save_date BETWEEN '%s' AND
                                      DATEADD(s, -1, DATEADD(d, 1, '%s'))
""" % (sStartDate, sEndDate)

#----------------------------------------------------------------------
# Filter on audience unless the user want everything.
#----------------------------------------------------------------------
if audience and audience != 'all':
    audienceFilter = """\
                AND au.value = '%s'
""" % audience
else:
    audienceFilter = ""

#----------------------------------------------------------------------
# Collect summaries which meet the criteria.
#----------------------------------------------------------------------
def collectSummaries(sqlSelect, sqlFrom, sqlJoin, sqlWhere,
                     audienceFilter, dateFilter,
                     cursor, language, boards, reportType):
    if boards:
        langFilter = """\
                AND la.value = '%s'
""" % language
        if len(boards) == 1 and boards[0] == 'all':
            boardFilter = """\
                AND bn.value LIKE '%Editorial Board'
"""
        else:
            boardFilter = """\
                AND bn.doc_id IN (%s)
""" % ", ".join(boards)
        if language == 'English':
            boardJoin = """\
               JOIN query_term sb
                 ON sb.doc_id = su.doc_id
"""
        else:
            boardFilter += """\
                AND en.path = '/Summary/TranslationOf/@cdr:ref'
"""
            boardJoin = """\
               JOIN query_term en
                 ON en.doc_id = su.doc_id
               JOIN query_term sb
                 ON sb.doc_id = en.int_val
"""
        try:
            sql = (sqlSelect + sqlFrom + boardJoin + sqlJoin + sqlWhere +
                   audienceFilter + boardFilter + langFilter + dateFilter)
            stamp = time.time()
            fp = open('d:/tmp/dlm-%s-%s.sql' % (language, stamp), 'w')
            fp.write(sql)
            fp.close()
            cursor.execute(sql, timeout = 300)
            rows = cursor.fetchall()
            for row in rows:
                Summary(row, language, reportType, cursor)
        except cdrdb.Error, info:
            cdrcgi.bail('Failure retrieving report information: %s' %
                        info[1][0])
        return sql

collectSummaries(sqlSelect, sqlFrom, sqlJoin, sqlWhere,
                 audienceFilter, dateFilter,
                 cursor, 'English', est, reportType)
collectSummaries(sqlSelect, sqlFrom, sqlJoin, sqlWhere,
                 audienceFilter, dateFilter,
                 cursor, 'Spanish', sst, reportType)
if not Summary.summaries:
    cdrcgi.bail("No summaries match report criteria")

#----------------------------------------------------------------------
# Map audience name to abbreviation.
#----------------------------------------------------------------------
def getAudienceAbbreviation(audience):
    return 'PROFESSIONAL' in audience.upper() and 'HP' or 'PAT'

#----------------------------------------------------------------------
# Create the styles for the workbook.
#----------------------------------------------------------------------
class Styles:
    def __init__(self, wb):

        # Create the style for the title of a sheet.
        font        = ExcelWriter.Font(name = 'Arial', size = 12, bold = True)
        align       = ExcelWriter.Alignment('Center', 'Center')
        self.title  = wb.addStyle(alignment = align, font = font)

        # Create the style for the section titles.
        font        = ExcelWriter.Font(name = 'Arial', size = 11, bold = True)
        align       = ExcelWriter.Alignment('Left', 'Center', True)
        self.sect   = wb.addStyle(alignment = align, font = font)

        # Create the style for the column headers.
        font        = ExcelWriter.Font(name = 'Arial', size = 10, bold = True)
        align       = ExcelWriter.Alignment('Center', 'Bottom', True)
        self.header = wb.addStyle(alignment = align, font = font)

        # Create the style for the left-aligned cells.
        align       = ExcelWriter.Alignment('Left', 'Top', True)
        font        = ExcelWriter.Font(name = 'Arial', size = 10)
        self.left   = wb.addStyle(alignment = align, font = font)
        
        # Create the style for the centered cells.
        align       = ExcelWriter.Alignment('Center', 'Top', True)
        self.center = wb.addStyle(alignment = align, font = font)
        
        # Create the style for the linking cells.
        font        = ExcelWriter.Font('blue', 'Single', 'Arial', size = 10)
        #align       = ExcelWriter.Alignment('Center', 'Top', True)
        self.url    = wb.addStyle(alignment = align, font = font)

#----------------------------------------------------------------------
# Create the workbook.
#----------------------------------------------------------------------
#format1   = makeFormat(book, True, 12, merge = 1)
#format2   = makeFormat(book, True, 12, align = 'left', merge = 1)
#format3   = makeFormat(book, True, 12, textWrap = True)
#format4   = makeFormat(book)
#format5   = makeFormat(book, underscore = True, color = 'blue')
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
book = ExcelWriter.Workbook()
styles = Styles(book)
sheet = book.addWorksheet("CCB Report")
rowNum    = 1
sheet.addCol(1, 66.75)
sheet.addCol(2, 266.25)
extraCols = 0
if reportType == 'S':
    sheet.addCol(3, 77.25)
    sheet.addCol(4, 40.5)
    sheet.addCol(5, 266.25)
    extraCols = 3
sheet.addCol(extraCols + 3, 82.5)
sheet.addCol(extraCols + 4, 82.5)
sheet.addCol(extraCols + 5, 56.25)
row = sheet.addRow(1, styles.title)#, 15.75)
row.addCell(1, bodyTitle, mergeAcross = 4 + extraCols)
row = sheet.addRow(2, styles.title)#, 15.75)
row.addCell(1, subtitle, mergeAcross = 4 + extraCols)
rowNum = 4

#----------------------------------------------------------------------
# Add rows for one section of the report.
#----------------------------------------------------------------------
def addSection(sheet, summaries, board, language, audience, reportType,
               styles, rowNum):
    audienceAndLanguage = "%s (%s)" % (audience, language)
    mergeCells = reportType == 'S' and 8 or 5
    row = sheet.addRow(rowNum, styles.sect)#, 15.75)
    row.addCell(1, board, mergeAcross = mergeCells)
    rowNum += 1
    row = sheet.addRow(rowNum, styles.sect)#, 15.75)
    row.addCell(1, audienceAndLanguage, mergeAcross = mergeCells)
    rowNum += 1
    row = sheet.addRow(rowNum, styles.header)#, 47.25)
    row.addCell(1, 'DocID')
    row.addCell(2, 'Summary Title')
    extraCols = 0
    url = None
    urlStyle = styles.center
    if reportType == 'S':
        row.addCell(3, 'Board')
        row.addCell(4, 'Type')
        row.addCell(5, 'Last Comment')
        extraCols = 3
        audienceAbbreviation = getAudienceAbbreviation(audience)
        urlStyle = styles.url
    row.addCell(3 + extraCols, 'Date Last Modified')
    row.addCell(4 + extraCols, 'Last Modify Action Date (System)')
    row.addCell(5 + extraCols, 'LastV Publish?')
    rowNum += 1
    summaries.sort()
    for summary in summaries:
        row = sheet.addRow(rowNum)
        summaryType = summary.summaryType
        if summaryType == 'Complementary and alternative medicine':
            summaryType = 'CAM'
        lastSave = ("%s" % summary.lastSave)[:10]
        row.addCell(1, u"CDR%d" % summary.docId, style = styles.left)
        row.addCell(2, summary.title, style = styles.left)
        if reportType == 'S':
            row.addCell(3, summaryType, style = styles.left)
            row.addCell(4, audienceAbbreviation, style = styles.left)
            row.addCell(5, summary.comment, style = styles.left)
            url = ("http://%s/cgi-bin/cdr/AuditTrail.py?id=%s" %
                   (cdrcgi.WEBSERVER, summary.docId))
        row.addCell(3 + extraCols, summary.lastMod, style = styles.center)
        row.addCell(4 + extraCols, lastSave, style = urlStyle,
                    href = url)
        row.addCell(5 + extraCols, summary.lastVFlag, style = styles.center)
        rowNum += 1
    return rowNum + 1

#----------------------------------------------------------------------
# Walk through the sections.
#----------------------------------------------------------------------
boards = Summary.summaries.keys()
boards.sort()
for boardName in boards:
    board = Summary.summaries[boardName]
    languages = board.keys()
    languages.sort()
    for languageName in languages:
        language = board[languageName]
        audiences = language.keys()
        audiences.sort()
        for audienceName in audiences:
            summaries = language[audienceName]
            rowNum = addSection(sheet, summaries, boardName, languageName,
                                audienceName, reportType, styles, rowNum)

stamp = time.strftime("%Y%m%d%H%M%S")
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=sdlm-%s.xls" % stamp
print
book.write(sys.stdout, True)
