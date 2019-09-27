#----------------------------------------------------------------------
# Report listing specified set of Cancer Information Summaries, the date
# they were last modified as entered by a user, and the date the last
# Modify action was taken.
#
# BZIssue::913 - user-requested changes
# BZIssue::1698 - add new columns and switch to Excel report
# BZIssue::3635 - extensive rewrite
# BZIssue::3716 - unicode encoding cleanup
# BZIssue::4209 - add date to report
# BZIssue::4214 - use the document's own DateLastModified value
# BZIssue::4924 - modify Summary Date Last Modified Report
# JIRA::OCECDR-4285 - add filtering by summary document state
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
import datetime
import sys
from cdrapi import db
from html import escape as html_escape

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
also        = fields.getlist ('also')          or []
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
today       = str(datetime.date.today())
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script language='JavaScript' src='/js/CdrCalendar.js'></script>
   <style type='text/css'>
    .CdrDateField { width: 100px; }
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
    conn   = db.connect(user='CdrGuest', timeout=600)
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail('Database connection failure: %s' % e)

#----------------------------------------------------------------------
# Validate parameters
#----------------------------------------------------------------------
if request:    cdrcgi.valParmVal(request, valList=buttons)
if est:
    if est != ['all']:
               cdrcgi.valParmVal(est, regex=r'^\d+$')
if sst:
    if sst != ['all']:
               cdrcgi.valParmVal(sst, regex=r'^\d+$')
if uStartDate: cdrcgi.valParmDate(uStartDate)
if uEndDate:   cdrcgi.valParmDate(uEndDate)
if sStartDate: cdrcgi.valParmDate(sStartDate)
if sEndDate:   cdrcgi.valParmDate(sEndDate)
if audience:
    if audience != 'all':
        # Note: I'm using the cdr. version here, not refactoring the code
        #       that generated audiences in this script
        cdrcgi.valParmVal(audience, valList=cdr.getSummaryAudiences())

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
                html.append("""\
    &nbsp;
    <input name='Audience' type='radio' value='%s' class='choice'/> %s <br />
""" % (value, value))
    except Exception as e:
        cdrcgi.bail("Failure retrieving audience choices: %s" % e)
    html.append("""\
    &nbsp;
    <input name='Audience' type='radio' checked='1' value='all'
           class='choice' /> All <br />
""")
    return "".join(html)

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
                AND org_type.value = 'PDQ Editorial Board'""")
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
                AND l.value = 'English'""")
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
                AND l.value = 'Spanish'""")
    cursor.execute("""\
        SELECT DISTINCT b.doc_id, b.title
                   FROM #board b
                   JOIN #english e
                     ON e.board = b.doc_id""")
    rows = cursor.fetchall()
    html = ["""\
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
        html.append("""\
     &nbsp;
     <input name='est' type='checkbox' value='%d' class='choice'
            onclick='javascript:someEnglish()' id='E%d' /> %s <br />
""" % (docId, i, html_escape(docTitle)))
        i += 1
    cursor.execute("""\
        SELECT DISTINCT b.doc_id, b.title
                   FROM #spanish s
                   JOIN #english e
                     ON s.english = e.summary
                   JOIN #board b
                     ON e.board = b.doc_id""")
    rows = cursor.fetchall()
    html.append("""\
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
        html.append("""\
     &nbsp;
     <input name='sst' type='checkbox' value='%d' class='choice'
            onclick='javascript:someSpanish()' id='S%d' /> %s <br />
""" % (docId, i, html_escape(docTitle)))
        i += 1
    html.append("""\
    </fieldset>
""")
    return "".join(html)

#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not audience or not (est or sst) or ((not uStartDate or not uEndDate) and
                                        (not sStartDate or not sEndDate)):
    endDate = datetime.date.today()
    startDate = endDate - datetime.timedelta(6)
    form = """\
   <input type='hidden' name='%s' value='%s' width='100%%' />
   <fieldset>
    <legend>Audience</legend>
%s
   </fieldset>
%s
   <fieldset>
    <legend>Include</legend>
    &nbsp;
     <input name='also' type='checkbox' id='AlsoMod' class='choice'
            value='modules' /> Modules <br />
    &nbsp;
     <input name='also' type='checkbox' id='AlsoBlocked' class='choice'
            value='blocked' /> Blocked Documents <br />
    &nbsp;
     <input name='also' type='checkbox' id='AlsoUnpub' class='choice'
            value='unpub' /> Other Unpublished Documents <br />
   </fieldset>
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
        self.module      = row[8]
        self.lastSaveUsr = Summary.__getSaveUsr(self.docId, cursor)
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
        if isinstance(lastVersions, (str, bytes)):
            self.lastVFlag = lastVersions
        else:
            lastAny, lastPub, isChanged = lastVersions
            if lastAny == -1:
                self.lastVFlag = 'N/A'
            elif lastAny == lastPub:
                self.lastVFlag = 'Y'
            else:
                self.lastVFlag = 'N'

    def __lt__(self, other):
        return (self.title, self.docId) < (other.title, other.docId)

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

    @staticmethod
    def __getSaveUsr(docId, cursor):
        "Get the user from the last version of the document."
        cursor.execute("""\
       SELECT fullname
         FROM doc_last_save dls
         JOIN doc_save_action dsa
           ON dsa.doc_id = dls.doc_id
          AND dls.last_save_date = dsa.save_date
         JOIN usr u
           ON u.id = dsa.save_user
        WHERE dls.doc_id = %s""" % docId)
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
                    ls.last_save_date AS last_save_date,
                    mo.value          AS module
"""
sqlFrom = """\
               FROM query_term su
"""
sqlJoin = """\
               JOIN document d
                 ON d.id = su.doc_id
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
    LEFT OUTER JOIN pub_proc_cg cg
                 ON cg.id = su.doc_id
    LEFT OUTER JOIN query_term lm
                 ON lm.doc_id = su.doc_id
    LEFT OUTER JOIN query_term mo
                 ON mo.doc_id = su.doc_id
                AND mo.path = '/Summary/@AvailableAsModule'
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
# OCECDR-4285: add filtering of summary document states. By default,
# only summaries which have been published to Cancer.gov are included
# in the report (which would exclude all blocked documents, summaries
# which are marked 'available as module' and summaries which are new
# and in progress). Checkboxes are provided to lift some or all of
# those restrictions.
#----------------------------------------------------------------------
if "unpub" in also:
    if "blocked" not in also:
        sqlWhere += """\
                AND d.active_status = 'A'
"""
else:
    also_where = ["cg.id IS NOT NULL"]
    if "blocked" in also:
        also_where.append("d.active_status = 'I'")
    if "modules" in also:
        also_where.append("mo.doc_id IS NOT NULL")
    sqlWhere += """\
                AND (%s)
""" % " OR ".join(also_where)
if "modules" not in also:
    sqlWhere += """\
                AND mo.doc_id IS NULL
"""

#----------------------------------------------------------------------
# Filter on dates, depending on which flavor of the report was requested.
# We have to convert second date back to VARCHAR(40) using style 20
# (YYYY-MM-DD ...) to avoid blowing up in the face of invalid date
# strings in the documents.
#----------------------------------------------------------------------
if uStartDate and uEndDate:
    bodyTitle  = "Summary Date Last Modified (User) Report"
    subtitle   = "%s - %s" % (uStartDate, uEndDate)
    reportType = 'U'
    dateFilter = """\
                AND lm.value BETWEEN '%s'
                             AND CONVERT(VARCHAR(40),
                                         DATEADD(s, -1,
                                                 DATEADD(d, 1, '%s')), 20)
""" % (uStartDate, uEndDate)
else:
    bodyTitle  = "Summary Last Modified Date (System) Report"
    subtitle   = "%s - %s" % (sStartDate, sEndDate)
    reportType = 'S'
    dateFilter = """\
                AND ls.last_save_date BETWEEN '%s' AND
                                      DATEADD(s, -1, DATEADD(d, 1, '%s'))
""" % (sStartDate, sEndDate)

#----------------------------------------------------------------------
# Filter on audience unless the user wants everything.
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
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                Summary(row, language, reportType, cursor)
        except Exception as e:
            cdrcgi.bail('Failure retrieving report information: %s' % e)
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
# Create the workbook.
#----------------------------------------------------------------------
styles = cdrcgi.ExcelStyles()
styles.header = styles.style("align: wrap true, horz center; font: bold true")
styles.url = styles.style(styles.HYPERLINK, styles.CENTER_TOP)
styles.sect = styles.style(styles.LEFT, styles.bold_font(11))
sheet = styles.add_sheet("DLM Report")
report_date = "Report Date: %s" % today
sheet.col(0).width = styles.chars_to_width(12)
sheet.col(1).width = styles.chars_to_width(50)
extraCols = 0
if reportType == 'S':
    sheet.col(2).width = styles.chars_to_width(15)
    sheet.col(3).width = styles.chars_to_width(7)
    sheet.col(4).width = styles.chars_to_width(50)
    extraCols = 3
sheet.col(extraCols + 2).width = styles.chars_to_width(15)
sheet.col(extraCols + 3).width = styles.chars_to_width(15)
sheet.col(extraCols + 4).width = styles.chars_to_width(10)
sheet.col(extraCols + 5).width = styles.chars_to_width(15)
sheet.write_merge(0, 0, 0, extraCols + 5, bodyTitle, styles.banner)
sheet.write_merge(1, 1, 0, extraCols + 5, subtitle, styles.banner)
sheet.write_merge(2, 2, 0, extraCols + 5, report_date, styles.bold)
rowNum = 3

#----------------------------------------------------------------------
# Add rows for one section of the report.
#----------------------------------------------------------------------
def addSection(sheet, summaries, board, language, audience, reportType,
               styles, row):
    audienceAndLanguage = "%s (%s)" % (audience, language)
    lastCol = reportType == 'S' and 8 or 5
    sheet.write_merge(row, row, 0, lastCol, "")
    row += 1
    sheet.write_merge(row, row, 0, lastCol, board, styles.sect)
    row += 1
    sheet.write_merge(row, row, 0, lastCol, audienceAndLanguage, styles.sect)
    row += 1
    sheet.write(row, 0, "DocID", styles.header)
    sheet.write(row, 1, "Summary Title", styles.header)
    extraCols = 0
    if reportType == 'S':
        sheet.write(row, 2, "Board", styles.header)
        sheet.write(row, 3, "Type", styles.header)
        sheet.write(row, 4, "Last Comment", styles.header)
        extraCols = 3
        audienceAbbreviation = getAudienceAbbreviation(audience)
    sheet.write(row, extraCols + 2, "Date Last Modified", styles.header)
    sheet.write(row, extraCols + 3, "Last Modify Action Date (System)",
                styles.header)
    sheet.write(row, extraCols + 4, "LastV Publish?", styles.header)
    sheet.write(row, extraCols + 5, "User", styles.header)
    row += 1
    for summary in sorted(summaries):
        summaryType = summary.summaryType
        if summaryType == 'Complementary and alternative medicine':
            summaryType = 'CAM'
        lastSave = ("%s" % summary.lastSave)[:10]
        url = ("http://%s" % cdrcgi.WEBSERVER +
               "/cgi-bin/cdr/DocVersionHistory.py?" +
               "Session=guest&DocId=%s" % summary.docId)
        link = styles.link(url, "CDR%d" % summary.docId)
        sheet.write(row, 0, link, styles.url)
        title = summary.title
        if summary.module:
            title += " [module]"
        sheet.write(row, 1, title, styles.left)
        if extraCols:
            sheet.write(row, 2, summaryType, styles.left)
            sheet.write(row, 3, audienceAbbreviation, styles.left)
            sheet.write(row, 4, summary.comment, styles.left)
        sheet.write(row, extraCols + 2, summary.lastMod, styles.center)
        if reportType == 'S':
            url = ("http://%s/cgi-bin/cdr/AuditTrail.py?id=%s" %
                   (cdrcgi.WEBSERVER, summary.docId))
            link = styles.link(url, lastSave)
            sheet.write(row, extraCols + 3, link, styles.url)
        else:
            sheet.write(row, extraCols + 3, lastSave, styles.center)
        sheet.write(row, extraCols + 4, summary.lastVFlag, styles.center)
        sheet.write(row, extraCols + 5, summary.lastSaveUsr, styles.center)
        row += 1
    return row

#----------------------------------------------------------------------
# Walk through the sections.
#----------------------------------------------------------------------
for boardName in sorted(Summary.summaries):
    board = Summary.summaries[boardName]
    for languageName in sorted(board):
        language = board[languageName]
        for audienceName in sorted(language):
            summaries = language[audienceName]
            rowNum = addSection(sheet, summaries, boardName, languageName,
                                audienceName, reportType, styles, rowNum)

stamp = cdr.make_timestamp()
sys.stdout.buffer.write(f"""\
Content-type: application/vnd.ms-excel
Content-Disposition: attachment; filename=sdlm-{stamp}.xls

""".encode("utf-8"))
styles.book.save(sys.stdout.buffer)
