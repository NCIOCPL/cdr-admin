#----------------------------------------------------------------------
#
# SummaryCRD.py
# -------------
# $Id: SummaryCRD.py 9298 2009-10-21 16:58:14Z volker $
#
# BZIssue::4648
#   Report to list the Comprehensive Review Dates
# BZIssue::4987 - Problem using Comprehensive Review Date Report
# BZIssue::5273 - Identifying Modules in Summary Reports
#
#----------------------------------------------------------------------
import sys, cdr, cgi, cdrcgi, time, cdrdb, ExcelWriter

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields and fields.getvalue("Boolean")          or "AND"
audience  = fields and fields.getvalue("audience")         or None
lang      = fields and fields.getvalue("lang")             or None
showId    = fields and fields.getvalue("showId")           or "N"
showAll   = fields and fields.getvalue("showAll")          or "N"
excel     = fields and fields.getvalue("outputFormat")     or "Y"
groupsEN  = fields and fields.getvalue("grpEN")            or []
groupsES  = fields and fields.getvalue("grpES")            or []
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Summaries Comprehensive Review Dates"
script    = "SummaryCRD.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)


# -------------------------------------------------
# Select the list of all board names by language
# -------------------------------------------------
def getAllBoardNames(language, cursor):
    allBoards = []

    cursor.execute("""\
        SELECT DISTINCT board
          FROM #CRD_Info
         WHERE language = '%s'
           AND len(board) != 0""" % language)

    rows = cursor.fetchall()
    for row in rows:
        allBoards.append(row[0])

    return allBoards
    

# -------------------------------------------------
# Select the dates from the info table
# -------------------------------------------------
def getCRDDates(id, type, sort, cursor):
    query_dates = """\
        SELECT distinct cdrid, CRDdate, CRDdatetype, Comment
          FROM #CRD_Info
         WHERE cdrid = %s
           AND CRDDateType = '%s'
         ORDER BY CRDdatetype, CRDdate %s
    """ % (id, type, sort)

    cursor.execute(query_dates)
    return cursor.fetchall()


# -------------------------------------------------
# Create the table row for the table output
# -------------------------------------------------
def addHtmlTableRow(row, listCdr = 'Y', listAll = 'Y'):
    """Return the HTML code to display a row of the report"""
    cdrId = row[0]
    title = row[1]

    if listAll == 'N':
        sortOrder = 'desc'
    else:
        sortOrder = 'asc'

    # We create the report either with or without the CDR-ID column
    # -------------------------------------------------------------
    if listCdr == 'Y':
        html = """\
    <tr>
     <td>%s</td>
     <td>%s</td>
""" % (cdrId, title)
    else:
        html = """\
   <tr>
    <td>%s</td>
""" % (title)

    # Populate the Actual dates and corresponding comments
    # ----------------------------------------------------
    html += """\
    <td>"""

    crdType = 'Actual'
    rows = getCRDDates(cdrId, crdType, sortOrder, cursor)

    if rows:
        for row in rows:
            html += "%s<br>" % row[1]
            if listAll == 'N': break

        html += "</td><td>"
        for row in rows:
            html += "%s<br>" % (row[3] or '')
            if listAll == 'N': break
    # Need to add this for MB, who's still using IE6
    else:
        html += "&nbsp;<br></td><td>&nbsp;<br>"

    # Populate the Planned dates and corresponding comments
    # ----------------------------------------------------
    html += """</td>
    <td>"""

    crdType = 'Planned'
    rows = getCRDDates(cdrId, crdType, sortOrder, cursor)

    if rows:
        for row in rows:
            html += "%s<br>" % row[1]
            if listAll == 'N': break

        html += "</td><td>"
        for row in rows:
            html += "%s<br>" % (row[3] or '')
            if listAll == 'N': break
    # Need to add this for MB, who's still using IE6
    else:
        html += "&nbsp;<br></td><td>&nbsp;<br>"

    html += """</td>
   </tr>
"""
    return html


def addHtmlTableRow2(row, listCdr = 'Y', listAll = 'Y'):
    """Return the HTML code to display a row of the report.
       If multiple comments exist display each comment on
       a line separately."""
    cdrId = row[0]
    title = '%s%s' % (row[1], row[4] and ' (Module)' or '')

    if listAll == 'N':
        sortOrder = 'desc'
    else:
        sortOrder = 'asc'

    crdType = 'Actual'
    aRows = getCRDDates(cdrId, crdType, sortOrder, cursor)
    crdType = 'Planned'
    pRows = getCRDDates(cdrId, crdType, sortOrder, cursor)
    numRows = max(len(aRows), len(pRows))
    #cdrcgi.bail(pRows)

    # We create the report either with or without the CDR-ID column
    # -------------------------------------------------------------
    if listCdr == 'Y':
        html = """\
    <tr>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
    </tr>
""" % (cdrId, title, 
       aRows and aRows[0][1] or '&nbsp;', aRows and aRows[0][3] or '&nbsp;', 
       pRows and pRows[0][1] or '&nbsp;', pRows and pRows[0][3] or '&nbsp;')
    else:
        html = """\
    <tr>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
    </tr>
""" % (title, 
       aRows and aRows[0][1] or '&nbsp;', aRows and aRows[0][3] or '&nbsp;', 
       pRows and pRows[0][1] or '&nbsp;', pRows and pRows[0][3] or '&nbsp;')

    # If more then one date exists and we want to display them all
    # print the other lines, too.
    # ------------------------------------------------------------
    if listAll == 'Y':
        for i in range(1, numRows):
            html += """
    <tr>
     %s
     <td>&nbsp;<br></td>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
    </tr>
""" % (listCdr == 'Y' and '<td>&nbsp;<br></td>' or '&nbsp;',
       aRows and i < len(aRows) and aRows[i][1] or '&nbsp;', 
       aRows and i < len(aRows) and aRows[i][3] or '&nbsp;', 
       pRows and i < len(pRows) and pRows[i][1] or '&nbsp;', 
       pRows and i < len(pRows) and pRows[i][3] or '&nbsp;')

    return html



# -------------------------------------------------
# Create the table row for the table output
# -------------------------------------------------
def addExcelTableRow(row, listCdr = 'Y', listAll = 'Y'):
    """Return the Excel code to display a row of the report"""
    cdrId = row[0]
    title = row[1]

    if listAll == 'N':
        sortOrder = 'desc'
    else:
        sortOrder = 'asc'

    if listCdr == 'Y':
        exRow.addCell(1, cdrId)
        exRow.addCell(2, title)
    else:
        exRow.addCell(2, title)

    crdType = 'Actual'
    rows = getCRDDates(cdrId, crdType, sortOrder, cursor)

    if rows:
        for row in rows:
            exRow.addCell(3, row[1])
            exRow.addCell(4, row[3])
            if listAll == 'N': break

    crdType = 'Planned'
    rows = getCRDDates(cdrId, crdType, sortOrder, cursor)

    if rows:
        for row in rows:
            exRow.addCell(5, row[1])
            exRow.addCell(6, row[3])
            if listAll == 'N': break

    return


# If the user only picked one summary group, put it into a list so we
# can deal with the same data structure whether one or more were
# selected.
#----------------------------------------------------------------------
if type(groupsEN) in (type(""), type(u"")):
    groupsEN = [groupsEN]
if type(groupsES) in (type(""), type(u"")):
    groupsES = [groupsES]

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
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y")

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not lang:
    header = cdrcgi.header(title, title, instr + ' - ' + dateString, 
                           script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1,
                           stylesheet = """
   <STYLE type="text/css">
    TD      { font-size:  12pt; }
    LI.none { list-style-type: none }
    DL      { margin-left: 0; padding-left: 0 }
   </STYLE>
   <script language='JavaScript'>
    function someEnglish() {
        document.getElementById('allEn').checked = false;
    }
    function someSpanish() {
        document.getElementById('allEs').checked = false;
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

"""                           )
    form   = """\
   <input type='hidden' name='%s' value='%s'>
 
   <fieldset>
    <legend>&nbsp;Select Summary Audience&nbsp;</legend>
    <input name='audience' type='radio' id="byHp"
           value='Health Professional' CHECKED>
    <label for="byHp">Health Professional</label>
    <br>
    <input name='audience' type='radio' id="byPat"
           value='Patient'>
    <label for="byPat">Patient</label>
   </fieldset>
   <fieldset>
    <legend>&nbsp;Display CR Dates&nbsp;</legend>
    <input name='showAll' type='radio' id="idAll"
           value='Y'>
    <label for="idAll">Show all CR Dates</label>
    <br>
    <input name='showAll' type='radio' id="idOne"
           value='N' CHECKED>
    <label for="idOne">Show last CR Date only</label>
   </fieldset>

   <fieldset>
    <legend>&nbsp;Display CDR-ID?&nbsp;</legend>
    <input name='showId' type='radio' id="idNo"
           value='N' CHECKED>
    <label for="idNo">Without CDR-ID</label>
    <br>
    <input name='showId' type='radio' id="idYes"
           value='Y'>
    <label for="idYes">With CDR-ID</label>
   </fieldset>

   <fieldset>
    <legend>&nbsp;Select Summary Language and Summary Type&nbsp;</legend>
   <table border = '0'>
    <tr>
     <td width=100>
      <input name='lang' type='radio' id="en" value='English' CHECKED>
      <label for="en">English</label>
     </td>
     <td valign='top'>
      Select PDQ Summaries: (one or more)
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <input type='checkbox' name='grpEN' value='All English' 
             onclick="javascript:allEnglish(this, 6)" id="allEn" CHECKED>
       <label id="allEn">All English</label><br>
      <input type='checkbox' name='grpEN' value='Adult Treatment Board'
             onclick="javascript:someEnglish()" id="E1">
       <label id="E1">Adult Treatment</label><br>
      <input type='checkbox' name='grpEN' value='Cancer Genetics Board'
             onclick="javascript:someEnglish()" id="E2">
       <label id="E2">Cancer Genetics</label><br>
      <input type='checkbox' name='grpEN'
             value='Cancer Complementary and Alternative Medicine Board'
             onclick="javascript:someEnglish()" id="E3">
       <label id="E3">Complementary and Alternative Medicine</label><br>
      <input type='checkbox' name='grpEN' value='Pediatric Treatment Board'
             onclick="javascript:someEnglish()" id="E4">
       <label id="E4">Pediatric Treatment</label><br>
      <input type='checkbox' name='grpEN' value='Screening and Prevention Board'
             onclick="javascript:someEnglish()" id="E5">
       <label id="E5">Screening and Prevention</label><br>
      <input type='checkbox' name='grpEN' 
             value='Supportive and Palliative Care Board'
             onclick="javascript:someEnglish()" id="E6">
       <label id="E6">Supportive and Palliative Care</label><br><br>
     </td>
    </tr>
    <tr>
     <td width=100>
      <input name='lang' type='radio' id="es" value='Spanish'>
      <label for="es">Spanish</label>
     </td>
     <td valign='top'>
      Select PDQ Summaries: (one or more)
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <input type='checkbox' name='grpES' 
             value='All Spanish' 
             onclick="javascript:allSpanish(this, 5)" id="allEs" CHECKED>
       <label id="allEs">All Spanish</label><br>
      <input type='checkbox' name='grpES' 
             value='Adult Treatment Board'
             onclick="javascript:someSpanish()" id="S1">
       <label id="S1">Adult Treatment</label><br>
      <input type='checkbox' name='grpES'
             value='Cancer Complementary and Alternative Medicine Board'
             onclick="javascript:someSpanish()" id="S2">
       <label id="S2">Complementary and Alternative Medicine</label><br>
      <input type='checkbox' name='grpES' 
             value='Pediatric Treatment Board'
             onclick="javascript:someSpanish()" id="S3">
       <label id="S3">Pediatric Treatment</label><br>
      <input type='checkbox' name='grpES' 
             value='Screening and Prevention Board'
             onclick="javascript:someSpanish()" id="S4">
       <label id="S4">Screening and Prevention</label><br>
      <input type='checkbox' name='grpES' 
             value='Supportive and Palliative Care Board'
             onclick="javascript:someSpanish()" id="S5">
       <label id="S5">Supportive and Palliative Care</label><br>
     </td>
    </tr>
   </table>
   </fieldset>

   <fieldset>
    <legend>&nbsp;Output Format?&nbsp;</legend>
    <input name='outputFormat' type='radio' id="idNo"
           value='N' CHECKED>
    <label for="idNo">HTML Report</label>
    <br>
    <input name='outputFormat' type='radio' id="idYes"
           value='Y'>
    <label for="idYes">Excel Report (for testing only)</label>
   </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

# Create a table for summaries with CR Dates
# ------------------------------------------
query_crd = """\
    SELECT dt.doc_id AS CdrId, dt.value AS CRDDate, 
           t.value AS CRDDateType , left(dt.node_loc, 4) AS node_loc
      INTO #CRD_Dates
      FROM query_term dt
      JOIN  query_term t
        ON dt.doc_id = t.doc_id
       AND t.path = '/Summary/ComprehensiveReview/' +
                    'ComprehensiveReviewDate/@DateType'
       AND LEFT(t.node_loc, 4) = LEFT(dt.node_loc, 4)
     WHERE dt.path = '/Summary/ComprehensiveReview/ComprehensiveReviewDate' 
     ORDER BY dt.doc_id, dt.value
"""

try:
    cursor = conn.cursor()
    cursor.execute(query_crd)
    #rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure Creating CRD temp table CRD_Dates: %s' %
                info[1][0])
     

# Create a table holding all information needed for all summaries
# This still leaves the Spanish summaries without board and needs
# to be modified in the next step.
# ---------------------------------------------------------------
query_info = """\
    SELECT DISTINCT t.doc_id AS CDRID, t.value AS Title, a.value AS Audience, 
           CASE 
               WHEN b.value = 'PDQ Adult Treatment Editorial Advisory Board' 
                    OR
                    b.value = 'PDQ Adult Treatment Editorial Board'
                    OR
                    b.value = 'PDQ Adult Treatment Advisory Board'
               THEN 'Adult Treatment Board'
               WHEN b.value = 'PDQ Cancer Genetics Editorial Advisory Board' 
                    OR
                    b.value = 'PDQ Cancer Genetics Editorial Board'
               THEN 'Cancer Genetics Board'
               WHEN b.value = 'PDQ Pediatric Treatment Editorial Advisory Board'
                    OR
                    b.value = 'PDQ Pediatric Editorial Treatment Advisory Board'
                    OR
                    b.value = 'PDQ Pediatric Treatment Editorial Board'
               THEN 'Pediatric Treatment Board'
               WHEN b.value = 'PDQ Supportive and Palliative Care '       +
                              'Editorial Advisory Board'
                    OR
                    b.value = 'PDQ Supportive and Palliative Care '       +
                              'Editorial Board'
               THEN 'Supportive and Palliative Care Board'
               WHEN b.value = 'PDQ Screening and Prevention Editorial '   +
                              'Advisory Board' 
                    OR
                    b.value = 'PDQ Screening and Prevention Editorial '   +
                              'Board'
               THEN 'Screening and Prevention Board'
               WHEN b.value = 'PDQ Cancer Complementary and Alternative ' +
                              'Medicine Editorial Advisory Board'
                    OR
                    b.value = 'PDQ Cancer Complementary and Alternative ' +
                              'Medicine Editorial Board'
               THEN 'Cancer Complementary and Alternative Medicine Board'
               ELSE b.value 
           END AS Board, 
           s.int_val AS TranslationOf,
           l.value AS Language, dt.CRDdate, dt.CRDdatetype,
           c.value AS Comment
      INTO #CRD_Info
      FROM query_term t
      JOIN document d
        ON d.id = t.doc_id
       AND d.active_status = 'A'
      JOIN query_term b
        ON t.doc_id = b.doc_id
       AND b.path = '/Summary/SummaryMetaData/PDQBoard/Board'
      JOIN query_term a
        ON t.doc_id = a.doc_id
       AND a.path = '/Summary/SummaryMetaData/SummaryAudience'
      JOIN query_term l
        ON t.doc_id = l.doc_id
       AND l.path = '/Summary/SummaryMetaData/SummaryLanguage'
 LEFT JOIN #CRD_Dates dt
        ON dt.cdrid = t.doc_id
 LEFT JOIN query_term c
        ON c.doc_id = t.doc_id
       AND c.path = '/Summary/ComprehensiveReview/Comment'
       AND left(c.node_loc, 4) = dt.node_loc
 LEFT JOIN query_term s
        ON s.doc_id = t.doc_id
       AND s.path = '/Summary/TranslationOf/@cdr:ref'
     WHERE t.path = '/Summary/SummaryTitle'
       AND len(t.value) > 0  -- exclude empty title rows
     ORDER BY t.doc_id
"""
try:
    cursor.execute(query_info)
    #rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure Creating CRD temp table CRD_Info: %s' %
                info[1][0])
     

# Removing all English Summaries for which the board element
# doesn't exist (is empty).  This is a not null field in #CRD_Info.
# ---------------------------------------------------------------
query_en_delete = """\
    DELETE FROM #CRD_Info
     WHERE language = 'English'
       AND len(Board) = 0
"""
try:
    cursor.execute(query_en_delete)
    #rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure deleting EN summaries without BoardName: %s' %
                info[1][0])
     

# Removing all Spanish Summaries without a TranslationOf element
# since we're unable to update the Board appropriately.
# ---------------------------------------------------------------
query_es_delete = """\
    DELETE FROM #CRD_Info
     WHERE language = 'Spanish' 
       AND TranslationOf IS NULL
"""
try:
    cursor.execute(query_es_delete)
    #rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure deleting ES summaries without TranslationOf: %s' %
                info[1][0])
     

# Updating the Spanish board names
# ---------------------------------------------------------------
query_upd = """\
    UPDATE #CRD_Info
       SET Board = (SELECT DISTINCT e.Board
                      FROM #CRD_Info e
                      JOIN #CRD_Info s
                        ON e.cdrid = s.TranslationOf
                     WHERE s.cdrid = #CRD_Info.cdrid
                       AND e.language = 'English'
                       AND e.board not like '%Advisory%'
                   )
     WHERE TranslationOf IS NOT NULL
       AND language = 'Spanish'  -- to protect against data entry errors
"""

try:
    cursor.execute(query_upd)
except cdrdb.Error, info:
    cdrcgi.bail('Failure Updating Spanish board names: %s' %
                info[1][0])

# Create selection criteria for HP or Patient version
# ---------------------------------------------------
if audience == 'Patient':
    q_audience = """\
    audience = 'Patients'
"""
else:
    q_audience = """\
    audience = 'Health professionals'
"""

# The report should be displayed as an Excel Spreadsheet 
# Since I already finished the report as HTML output I'll leave that option
# in here as another option for the users to choose.
# -------------------------------------------------------------------------
if excel == 'Y':
    # Create the spreadsheet and define default style, etc.
    # -----------------------------------------------------
    wsTitle = u'SummaryCRD'
    wb      = ExcelWriter.Workbook()
    b       = ExcelWriter.Border()
    borders = ExcelWriter.Borders(b, b, b, b)
    font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
    align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
    alignS  = ExcelWriter.Alignment('Left', 'Top', wrap = False)
    style1  = wb.addStyle(alignment = align, font = font)
    urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
    style4  = wb.addStyle(alignment = align, font = urlFont)
    style2  = wb.addStyle(alignment = align, font = font, 
                             numFormat = 'YYYY-mm-dd')
    alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
    alignT  = ExcelWriter.Alignment('Left', 'Bottom', wrap = False)
    headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                size = 12)
    titleFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                size = 14)
    boldFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                size = 11)
    styleH  = wb.addStyle(alignment = alignH, font = headFont)
    styleT  = wb.addStyle(alignment = alignT, font = titleFont)
    style1b = wb.addStyle(alignment = align,  font = boldFont)
    styleS  = wb.addStyle(alignment = alignS, font = boldFont)
    styleR  = wb.addStyle(alignment = alignS, font = font)

    ws      = wb.addWorksheet(wsTitle, style1, 45, 1)
    
    # CIAT wants a title row
    # ----------------------------------------------------------
    titleTime = time.strftime("%Y-%m-%d %H:%M:%S")
    rowCount = 0
    rowNum = 1
    exRow = ws.addRow(rowNum, styleT)

    rowNum = 1
    exRow = ws.addRow(rowNum, styleS)
    exRow.addCell(1,  'Report created: %s' % titleTime)

    # Set the column width
    # --------------------
    if showId == 'Y':
        ws.addCol( 1, 60)
    ws.addCol( 2, 500)
    ws.addCol( 3,  60)
    ws.addCol( 4, 200)
    ws.addCol( 5,  60)
    ws.addCol( 6, 200)

    # Create selection criteria for English/Spanish
    # and the boards
    # ---------------------------------------------
    boards = []
    iboard = 0
    if lang == 'English':
        if groupsEN.count('All English'):
            boards = getAllBoardNames('English', cursor)
        else:
            for group in groupsEN:
                boards.append(group)
    else:
        if groupsES.count('All Spanish'):
            boards = getAllBoardNames('Spanish', cursor)
        else:
            for group in groupsES:
                boards.append(group)

    for board in boards:
        rowNum += 2
        exRow = ws.addRow(rowNum, styleT)
        exRow.addCell(2, '%s - %s, %s' % (board, audience, lang))
        rowNum += 1

        exRow = ws.addRow(rowNum, styleH)
        if showId == 'Y':
            exRow.addCell(1, 'CDR-ID')
        exRow.addCell(2, 'Summary Title')
        exRow.addCell(3, 'CRD (Actual)')
        exRow.addCell(4, 'Actual Date Comment')
        exRow.addCell(5, 'CRD (Planned)')
        exRow.addCell(6, 'Planned Date Comment')

        # Submit the query to the database.
        #---------------------------------------------------
        q_language = """\
        and language = '%s'
""" % lang
        query = """\
            SELECT distinct CdrId, Title, Audience, Language
              FROM #CRD_Info
             WHERE %s
             %s
               AND board = '%s' 
             ORDER BY title
""" % (q_audience, q_language, board)

        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except cdrdb.Error, info:
            cdrcgi.bail('Failure retrieving Summary documents: %s' %
                        info[1][0])
             
        if not rows:
            rows = []

        for row in rows:
            rowCount += 1
            rowNum += 1
            exRow = ws.addRow(rowNum, styleR)
            addExcelTableRow(row, listCdr = showId, listAll = showAll)


    rowNum += 1
    exRow = ws.addRow(rowNum, style1b)
    exRow.addCell(1, 'Count: %d' % rowCount)

    t = time.strftime("%Y%m%d%H%M%S")                                               
    # Save the report.
    # ----------------
    name = '/SummaryCRDReport-%s.xls' % t
    REPORTS_BASE = 'd:/cdr/reports'
    f = open(REPORTS_BASE + name, 'wb')
    wb.write(f, True)
    f.close()

    if sys.platform == "win32":
        import os, msvcrt
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=%s" % name
    print
    wb.write(sys.stdout, True)

# Section to create HTML output
# -----------------------------
else:
    # Create the results page (in HTML format).
    #----------------------------------------------------------------------
    header    = cdrcgi.rptHeader(title, 
                              stylesheet = """\
       <STYLE type="text/css">
        DL             { margin-left:    0; 
                         padding-left:   0;
                         margin-top:    10px;
                         margin-bottom: 30px; }
        TABLE          { margin-top:    10px; 
                         margin-bottom: 30px; } 

        *.date         { font-size: 12pt; }
        *.sectionHdr   { font-size: 12pt;
                         font-weight: bold;
                         text-decoration: underline; }
        td.report      { font-size: 11pt;
                         padding-right: 15px; 
                         vertical-align: top; }
        *.cdrid        { text-align: right }
        LI             { list-style-type: bullet; 
                         font-weight: normal;
                         font-size: 10pt; }
        li.report      { font-size: 11pt;
                         font-weight: normal; }
        div.es          { height: 10px; }
        td             { vertical-align: top; }
       </STYLE>
    """)

    # -------------------------
    # Display the Report Title
    # -------------------------
    if lang == 'English':
        hdrLang = ''
    else:
        hdrLang = lang

    report    = """\
       <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      </FORM>
      <H3>PDQ %s %s Summaries<br>
      <span class="date">(%s)</span>
      </H3>
    """ % (cdrcgi.SESSION, session, hdrLang, audience, dateString)

    # -------------------------------------------------------------------
    # Decision if the CDR IDs are displayed along with the summary titles
    # - The report with    CDR ID is displayed in a table format.
    # -------------------------------------------------------------------
    # Create selection criteria for English/Spanish
    # and the boards
    # ---------------------------------------------
    boards = []
    iboard = 0
    if lang == 'English':
        if groupsEN.count('All English'):
            boards = getAllBoardNames('English', cursor)
        else:
            for group in groupsEN:
                boards.append(group)
    else:
        if groupsES.count('All Spanish'):
            boards = getAllBoardNames('Spanish', cursor)
        else:
            for group in groupsES:
                boards.append(group)

    for board in boards:
        report += """\
  <h2>%s - %s, %s</h2>
  <table width = "80%%" border="1">
   <tr>
""" % (board, audience, lang)

        if showId == 'Y':
            report += """\
    <th>CDR-ID</th>
"""
        report += """\
    <th>Summary Title</th>
    <th>CRD (Actual)</th>
    <th>Actual Date Comment</th>
    <th>CRD (Projected)</th>
    <th>Projected Date Comment</th>
   </tr>
"""
        # Submit the query to the database.
        #---------------------------------------------------
        q_language = """\
        and language = '%s'
""" % lang
        query = """\
            SELECT distinct CdrId, Title, Audience, Language, mod.value
             FROM #CRD_Info
        LEFT OUTER JOIN query_term mod
                     ON mod.doc_id = CdrId
                    AND mod.path = '/Summary/@ModuleOnly'
             WHERE %s
             %s
             and board = '%s' 
             ORDER BY title
""" % (q_audience, q_language, board)

        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except cdrdb.Error, info:
            cdrcgi.bail('Failure retrieving Summary documents: %s' %
                        info[1][0])
             
        if not rows:
            rows = []

        for row in rows:
            report += addHtmlTableRow2(row, listCdr = showId, 
                                           listAll = showAll)
        report += """\
  </table>
"""


    footer = """\
     </BODY>
    </HTML> 
    """     

    # Send the page back to the browser.
    #----------------------------------------------------------------------
    cdrcgi.sendPage(header + report + footer)
