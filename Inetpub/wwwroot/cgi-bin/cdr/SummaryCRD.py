#----------------------------------------------------------------------
#
# SummaryCRD.py
# -------------
# $Id$
#
# BZIssue::4648
#   Report to list the Comprehensive Review Dates
#
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, time, cdrdb

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
groupsEN  = fields and fields.getvalue("grpEN")            or []
groupsES  = fields and fields.getvalue("grpES")            or []
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Summaries Comprehensive Review Dates"
script    = "SummaryCRD.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)


# ---------------------------------------------------
# Functions to replace sevaral repeated HTML snippets
# ---------------------------------------------------
def boardHeader(board_type):
    """Return the HTML code to display the Summary Board Header"""
    html = """\
  </DL>
  <span class="sectionHdr">%s (%d)</span>
  <DL>
""" % (board_type, boardCount[board_type])
    return html


# ---------------------------------------------------
# 
# ---------------------------------------------------
def boardHeaderWithID(board_type):
    """Return the HTML code to display the Summary Board Header with ID"""
    html = """\
  </TABLE>

  <span class="sectionHdr">%s (%d)</span>
  <TABLE width = "100%%"> 
""" % (board_type, boardCount[board_type])
    return html


# ------------------------------------------------
# Create the table row for the English list output
# ------------------------------------------------
def summaryRow(summary):
    """Return the HTML code to display a Summary row"""
    html = """\
   <LI class="report">%s</LI>
""" % (row[1])
    return html


# -------------------------------------------------
# Create the table row for the English table output
# -------------------------------------------------
def summaryRowWithID(id, summary):
    """Return the HTML code to display a Summary row with ID"""
    html = """\
   <TR>
    <TD class="report cdrid" width = "8%%">%s</TD>
    <TD class="report">%s</TD>
   </TR>
""" % (id, summary)
    return html


# ------------------------------------------------
# Create the table row for the Spanish list output
# ------------------------------------------------
def summaryRowES(summary, translation):
    """Return the HTML code to display a Spanish Summary"""
    html = """\
   <LI class="report">%s</LI>
   <LI class="report">&nbsp;&nbsp;&nbsp;(%s)<div class="es"> </div></LI>
""" % (row[1], row[4])
    return html


# -------------------------------------------------
# Create the table row for the Spanish table output
# -------------------------------------------------
def summaryRowESWithID(id, summary, translation):
    """Return the HTML code to display a Spanish Summary row with ID"""
    html = """\
   <TR>
    <TD class="report cdrid" width = "8%%">%s</TD>
    <TD class="report">%s<BR/>
     (%s)
    </TD>
   </TR>
""" % (id, summary, translation)
    return html


# -------------------------------------------------
# Create the table row for the Spanish table output
# -------------------------------------------------
def addTableRow(row, listCdr = 'Y', listAll = 'Y'):
    """Return the HTML code to display a row of the report"""
    cdrId = row[0]
    title = row[1]

    if listAll == 'N':
        sortOrder = 'desc'
    else:
        sortOrder = 'asc'

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

    query_dates = """\
        SELECT distinct cdrid, CRDdate, CRDdatetype
          FROM #CRD_Info
         WHERE cdrid = %s
         ORDER BY CRDdate %s
    """ % (cdrId, sortOrder)

    cursor.execute(query_dates)
    rows = cursor.fetchall()

    html += """\
    <td>"""
    for row in rows:
        if row[2] and row[2] == 'Actual':
            html += "%s<br>" % row[1]
            if listAll == 'N': break

    html += """</td>
    <td>"""
    for row in rows:
        if row[2] and row[2] == 'Planned':
            html += "%s<br>" % row[1]
            if listAll == 'N': break

    html += """</td>
   </tr>
"""
    return html


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
           value='Y' CHECKED>
    <label for="idAll">Show all CR Dates</label>
    <br>
    <input name='showAll' type='radio' id="idOne"
           value='N'>
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
       <label id="E3">Complementary and Alternative Medicine</b><br>
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
      <input type='checkbox' name='grpES' value='All Spanish' 
             onclick="javascript:allSpanish(this, 4)" id="allEs" CHECKED>
       <label id="allEs">All Spanish</label><br>
      <input type='checkbox' name='grpES' 
             value='Adult Treatment Board'
             onclick="javascript:someSpanish()" id="S1" >
       <label id="S1">Adult Treatment</label><br>
      <input type='checkbox' name='grpES'
             value='Complementary and Alternative Medicine Board'
             onclick="javascript:someSpanish()" id="S2">
       <label id="S2">Complementary and Alternative Medicine</b><br>
      <input type='checkbox' name='grpES' 
             value='Pediatric Treatment Board'
             onclick="javascript:someSpanish()" id="S3" >
       <label id="S3">Pediatric Treatment</label><br>
      <input type='checkbox' name='grpES' 
             value='Supportive and Palliative Care Board'
             onclick="javascript:someSpanish()" id="S4" >
       <label id="S4">Supportive and Palliative Care</label><br>
     </td>
    </tr>
   </table>
   </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

# Create a table for summaries with CR Dates
# ------------------------------------------
query_crd = """\
    SELECT dt.doc_id AS CdrId, dt.value AS CRDDate, t.value AS CRDDateType 
      INTO #CRD_Dates
      FROM query_term_pub dt
      JOIN  query_term_pub t
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
               WHEN b.value = 'PDQ Adult Treatment Editorial Advisory Board' OR
                    b.value = 'PDQ Adult Treatment Editorial Board'
               THEN 'Adult Treatment Board'
               WHEN b.value = 'PDQ Cancer Genetics Editorial Advisory Board' OR
                    b.value = 'PDQ Cancer Genetics Editorial Board'
               THEN 'Cancer Genetics Board'
               WHEN b.value = 'PDQ Pediatric Editorial Treatment Advisory Board' OR
                    b.value = 'PDQ Pediatric Treatment Editorial Board'
               THEN 'Pediatric Treatment Board'
               WHEN b.value = 'PDQ Supportive and Palliative Care Editorial Advisory Board' OR
                    b.value = 'PDQ Supportive and Palliative Care Editorial Board'
               THEN 'Supportive and Palliative Care Board'
               WHEN b.value = 'PDQ Screening and Prevention Editorial Advisory Board' OR
                    b.value = 'PDQ Screening and Prevention Editorial Board'
               THEN 'Screening and Prevention Board'
               WHEN b.value = 'PDQ Cancer Complementary and Alternative Medicine Editorial Advisory Board' OR
                    b.value = 'PDQ Cancer Complementary and Alternative Medicine Editorial Board'
               THEN 'Complementary and Alternative Medicine Board'
               ELSE b.value 
           END AS Board, 
           s.int_val AS TranslationOf,
           l.value AS Language, dt.CRDdate, dt.CRDdatetype
      INTO #CRD_Info
      FROM query_term_pub t
      JOIN document d
        ON d.id = t.doc_id
       AND d.active_status = 'A'
      JOIN query_term_pub b
        ON t.doc_id = b.doc_id
       AND b.path = '/Summary/SummaryMetaData/PDQBoard/Board'
      JOIN query_term_pub a
        ON t.doc_id = a.doc_id
       AND a.path = '/Summary/SummaryMetaData/SummaryAudience'
      JOIN query_term_pub l
        ON t.doc_id = l.doc_id
       AND l.path = '/Summary/SummaryMetaData/SummaryLanguage'
 LEFT JOIN query_term_pub s
        ON s.doc_id = t.doc_id
       AND s.path = '/Summary/TranslationOf/@cdr:ref'
 LEFT JOIN #CRD_Dates dt
        ON dt.cdrid = t.doc_id
     WHERE t.path = '/Summary/SummaryTitle'
     ORDER BY t.doc_id
"""
try:
    cursor.execute(query_info)
    #rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure Creating CRD temp table CRD_info: %s' %
                info[1][0])
     
# Updating the Spanish board names
# ---------------------------------------------------------------
query_upd = """\
    UPDATE #CRD_info
       SET Board = (SELECT DISTINCT e.Board
                      FROM #CRD_info e
                      JOIN #CRD_info s
                        ON e.cdrid = s.TranslationOf
                     WHERE s.cdrid = #CRD_info.cdrid
                       AND e.language = 'English'
                   )
     WHERE TranslationOf IS NOT NULL
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

# Create the results page.
#----------------------------------------------------------------------
instr     = '%s Summaries List -- %s.' % (lang, dateString)
header    = cdrcgi.rptHeader(title, instr, 
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
    LI             { list-style-type: none }
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
if showId == 'N':
    # Create selection criteria for English/Spanish
    # and the boards
    # ---------------------------------------------
    boards = []
    iboard = 0
    if lang == 'English':
        q_language = """\
        and language = 'English'
"""
        if groupsEN.count('All English'):
            # Collect all board names
            # -----------------------
            cursor.execute("""\
                SELECT DISTINCT board
                  FROM #CRD_info
                 WHERE language = 'English'""")
            rows = cursor.fetchall()
            for row in rows:
                boards.append(row[0])
        else:
            for group in groupsEN:
                boards.append(group)
    else:
        q_language = """\
        and language = 'Spanish'
"""
        if groupsES.count('All Spanish'):
            cursor.execute("""\
                SELECT DISTINCT board
                  FROM #CRD_info
                 WHERE language = 'Spanish'""")
            rows = cursor.fetchall()
            for row in rows:
                boards.append(row[0])
        else:
            for group in groupsES:
                boards.append(group)

    for board in boards:
        report += """\
  <h2>%s - %s, %s</h2>
  <table width = "80%%" border="1">
   <tr>
    <th>Summary Title</td>
    <th>CRD (Actual)</td>
    <th>CRD (Projected)</td>
   </tr>
""" % (board, audience, lang)

        # Submit the query to the database.
        #----------------------------------------------------------------------
        query = """\
            SELECT distinct CdrId, Title, Audience, Language
             FROM #CRD_Info
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
            report += addTableRow(row, listCdr = showId, listAll = showAll)
        report += """\
  </table>
"""

# ------------------------------------------------------------------------
# Display data including CDR ID
# English and Spanish data to be displayed identically except that the 
# English translation of the summary titles is displayed under the title
# ------------------------------------------------------------------------
else:
    # Create selection criteria for English/Spanish
    # and the boards
    # ---------------------------------------------
    boards = []
    iboard = 0
    if lang == 'English':
        q_language = """\
        and language = 'English'
"""
        if groupsEN.count('All English'):
            # Collect all board names
            # -----------------------
            cursor.execute("""\
                SELECT DISTINCT board
                  FROM #CRD_info
                 WHERE language = 'English'""")
            rows = cursor.fetchall()
            for row in rows:
                boards.append(row[0])
        else:
            for group in groupsEN:
                boards.append(group)
    else:
        q_language = """\
        and language = 'Spanish'
"""
        if groupsES.count('All Spanish'):
            cursor.execute("""\
                SELECT DISTINCT board
                  FROM #CRD_info
                 WHERE language = 'Spanish'""")
            rows = cursor.fetchall()
            for row in rows:
                boards.append(row[0])
        else:
            for group in groupsES:
                boards.append(group)

    for board in boards:
        report += """\
  <h2>%s - %s, %s</h2>
  <table width = "80%%" border="1">
   <tr>
    <th>CDR-ID</td>
    <th>Summary Title</td>
    <th>CRD (Actual)</td>
    <th>CRD (Projected)</td>
   </tr>
""" % (board, audience, lang)

        # Submit the query to the database.
        #----------------------------------------------------------------------
        query = """\
            SELECT distinct CdrId, Title, Audience, Language
             FROM #CRD_Info
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
            report += addTableRow(row, listCdr = showId, listAll = showAll)

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
