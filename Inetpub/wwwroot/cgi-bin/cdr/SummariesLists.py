#----------------------------------------------------------------------
#
# $Id: SummariesLists.py,v 1.7 2008-08-19 18:45:30 venglisc Exp $
#
# Report on lists of summaries.
#
# $Log: not supported by cvs2svn $
# Revision 1.6  2007/11/03 14:15:07  bkline
# Unicode encoding cleanup (issue #3716).
#
# Revision 1.5  2007/05/01 23:56:23  venglisc
# Added a count of summaries per board and corrected the display of the
# newish CAM Advisory Board. (Bug 3204)
#
# Revision 1.4  2004/03/30 23:09:24  venglisc
# Fixed a problem that dropped the first summary of every summary type.
#
# Revision 1.3  2004/01/13 23:51:18  venglisc
# Added comments to the code.  Removed query_s since it is now handled with
# one query for both, English and Spanish requests.
#
# Revision 1.2  2004/01/13 23:23:40  venglisc
# Creating new summaries list reports per request (Bug 1010/1011).
#
# Revision 1.1  2003/12/19 18:30:00  bkline
# New report for CDR requests #1010/1011.
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
groups    = fields and fields.getvalue("grp")              or []
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Summaries Lists"
script    = "SummariesLists.py"
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


# If the user only picked one summary group, put it into a list so we
# can deal with the same data structure whether one or more were
# selected.
#----------------------------------------------------------------------
if type(groups) in (type(""), type(u"")):
    groups = [groups]

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
      <input type='checkbox' name='grp' value='All English' 
             onclick="javascript:allEnglish(this, 6)" id="allEn" CHECKED>
       <label id="allEn">All English</label><br>
      <input type='checkbox' name='grp' value='Adult Treatment'
             onclick="javascript:someEnglish()" id="E1">
       <label id="E1">Adult Treatment</label><br>
      <input type='checkbox' name='grp' value='Genetics'
             onclick="javascript:someEnglish()" id="E2">
       <label id="E2">Cancer Genetics</label><br>
      <input type='checkbox' name='grp'
             value='Complementary and Alternative Medicine'
                    onclick="javascript:someEnglish()" id="E3">
       <label id="E3">Complementary and Alternative Medicine</b><br>
      <input type='checkbox' name='grp' value='Pediatric Treatment'
             onclick="javascript:someEnglish()" id="E4">
       <label id="E4">Pediatric Treatment</label><br>
      <input type='checkbox' name='grp' value='Screening and Prevention'
             onclick="javascript:someEnglish()" id="E5">
       <label id="E5">Screening and Prevention</label><br>
      <input type='checkbox' name='grp' value='Supportive Care'
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
      <input type='checkbox' name='grp' value='All Spanish' 
             onclick="javascript:allSpanish(this, 3)" id="allEs" CHECKED>
       <label id="allEs">All Spanish</label><br>
      <input type='checkbox' name='grp' value='Spanish Adult Treatment'
             onclick="javascript:someSpanish()" id="S1" >
       <label id="S1">Adult Treatment</label><br>
      <input type='checkbox' name='grp' value='Spanish Pediatric Treatment'
             onclick="javascript:someSpanish()" id="S2" >
       <label id="S2">Pediatric Treatment</label><br>
      <input type='checkbox' name='grp' value='Spanish Supportive Care'
             onclick="javascript:someSpanish()" id="S3" >
       <label id="S3">Supportive and Palliative Care</label><br>
     </td>
    </tr>
   </table>
   </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Language variable has been selected
# Building individual Queries
# - English, HP, with CDR ID
# - English, HP, without CDR ID
# - English, Patient, with CDR ID ...
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Create the selection criteria based on the groups picked by the user
# But the decision will be based on the content of the board instead
# of the SummaryType.
# Based on the SummaryType selected on the form the boardPick list is
# being created including the Editorial and Advisory board for each
# type.  These board IDs can then be decoded into the proper 
# heading to be used for each selected summary type.
# --------------------------------------------------------------------
boardPick = ''
for i in range(len(groups)):
  # if i+1 == len(groups):
  if groups[i] == 'Adult Treatment' and lang == 'English':
      boardPick += """'CDR0000028327', 'CDR0000035049', """
  elif groups[i] == 'Spanish Adult Treatment' and lang == 'Spanish':
      boardPick += """'CDR0000028327', 'CDR0000035049', """
  elif groups[i] == 'Complementary and Alternative Medicine':
      boardPick += """'CDR0000256158', 'CDR0000423294', """
  elif groups[i] == 'Genetics':
      boardPick += """'CDR0000032120', 'CDR0000257061', """
  elif groups[i] == 'Screening and Prevention':
      boardPick += """'CDR0000028536', 'CDR0000028537', """
  elif groups[i] == 'Pediatric Treatment' and lang == 'English':
      boardPick += """'CDR0000028557', 'CDR0000028558', """
  elif groups[i] == 'Spanish Pediatric Treatment' and lang == 'Spanish':
      boardPick += """'CDR0000028557', 'CDR0000028558', """
  elif groups[i] == 'Supportive Care' and lang == 'English':
      boardPick += """'CDR0000028579', 'CDR0000029837', """
  elif groups[i] == 'Spanish Supportive Care' and lang == 'Spanish':
      boardPick += """'CDR0000028579', 'CDR0000029837', """
  else:
      boardPick += """'""" + groups[i] + """', """

# Define the Headings under which the summaries should be listed
# --------------------------------------------------------------
q_case = """\
       CASE WHEN board.value = 'CDR0000028327'  
                 THEN 'Adult Treatment'
            WHEN board.value = 'CDR0000035049'  
                 THEN 'Adult Treatment'
            WHEN board.value = 'CDR0000032120'  
                 THEN 'Cancer Genetics'
            WHEN board.value = 'CDR0000257061'  
                 THEN 'Cancer Genetics'
            WHEN board.value = 'CDR0000256158'  
                 THEN 'Complementary and Alternative Medicine'
            WHEN board.value = 'CDR0000423294'  
                 THEN 'Complementary and Alternative Medicine'
            WHEN board.value = 'CDR0000028557'  
                 THEN 'Pediatric Treatment'
            WHEN board.value = 'CDR0000028558'  
                 THEN 'Pediatric Treatment'
            WHEN board.value = 'CDR0000028536'  
                 THEN 'Screening and Prevention'
            WHEN board.value = 'CDR0000028537'  
                 THEN 'Screening and Prevention'
            WHEN board.value = 'CDR0000028579'  
                 THEN 'Supportive and Palliative Care'
            WHEN board.value = 'CDR0000029837'  
                 THEN 'Supportive and Palliative Care'
            ELSE board.value END
"""

# Create the selection criteria for the summary language (English/Spanish)
# ------------------------------------------------------------------------
q_lang = """\
AND    lang.path = '/Summary/SummaryMetaData/SummaryLanguage'
AND    lang.value = '%s'
""" % lang

# Define the selection criteria parts that are different for English or
# Spanish documents:
# q_fields:  Fields to be selected, i.e. the Spanish version needs to 
#            display the English translation
# q_join:    The Spanish version has to evaluate the board and language
#            elements differently
# q_board:   Don't restrict on selected boards if All English/Spanish
#            has been selected as well
# --------------------------------------------------------------------
if lang == 'English': 
    q_fields = """
                'dummy1', 'dummy2', title.value EnglTitle, 
"""
    q_join = """
JOIN  query_term board
ON    qt.doc_id = board.doc_id
JOIN  query_term lang
ON    qt.doc_id    = lang.doc_id
"""
    q_trans = ''
    if groups.count('All English'):
        q_board = ''
    else:
        q_board = """\
AND    board.value in (%s)
""" % boardPick[:-2]
else:
    q_fields = """
                qt.value CDRID, qt.int_val ID, translation.value EnglTitle, 
"""
    q_join = """
JOIN  query_term board
ON    qt.int_val = board.doc_id
JOIN  query_term translation
ON    qt.int_val = translation.doc_id
JOIN  query_term lang
ON    qt.doc_id    = lang.doc_id
"""
    q_trans = """
AND   translation.path = '/Summary/SummaryTitle'
AND   qt.path          = '/Summary/TranslationOf/@cdr:ref'
"""
    if groups.count('All Spanish'):
        q_board = ''
    else:
        q_board = """\
AND    board.value in (%s)
""" % boardPick[:-2]

# Create selection criteria for HP or Patient version
# ---------------------------------------------------
if audience == 'Patient':
    q_audience = """\
AND audience.value = 'Patients'
"""
else:
    q_audience = """\
AND audience.value = 'Health professionals'
"""

# Put all the pieces together for the SELECT statement
# -------------------------------------------------------------
query = """\
SELECT DISTINCT qt.doc_id, title.value DocTitle, 
%s
%s
FROM  query_term qt
%s
JOIN  query_term title
ON    qt.doc_id    = title.doc_id
JOIN  query_term audience
ON    qt.doc_id    = audience.doc_id
WHERE title.path   = '/Summary/SummaryTitle'
%s
AND   board.path   = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
%s
AND   audience.path = '/Summary/SummaryMetaData/SummaryAudience'
%s
%s
AND EXISTS (SELECT 'x' FROM doc_version v
            WHERE  v.id = qt.doc_id
            AND    v.val_status = 'V'
            AND    v.publishable = 'Y')
AND qt.doc_id not in (select doc_id 
                       from doc_info 
                       where doc_status = 'I' 
                       and doc_type = 'Summary')
ORDER BY 6, 2
""" % (q_fields, q_case, q_join, q_trans, q_board, q_audience, q_lang)

if not query:
    cdrcgi.bail('No query criteria specified')   

# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Summary documents: %s' %
                info[1][0])
     
if not rows:
    cdrcgi.bail('No Records Found for Selection: %s ' % lang+"; "+audience+"; "+groups[0] )

#cdrcgi.bail("Result: %s" % rows[75])
# Counting the number of summaries per board
# ------------------------------------------
boardCount = {}
for board in rows:
    if boardCount.has_key(board[5]):
        boardCount[board[5]] += 1
    else:
        boardCount[board[5]]  = 1

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
#else:
#    report    = """\
#   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
#  </FORM>
#  <H3>PDQ %s %s Summaries</H3>
#""" % (cdrcgi.SESSION, session, lang, audience)

board_type = rows[0][5]

# -------------------------------------------------------------------
# Decision if the CDR IDs are displayed along with the summary titles
# - The report without CDR ID is displayed as a bulleted list.
# - The report with    CDR ID is displayed in a table format.
# -------------------------------------------------------------------
# ------------------------------------------------------------------------
# Display data including CDR ID
# English and Spanish data to be displayed identically except that the 
# English translation of the summary titles is displayed under the title
# ------------------------------------------------------------------------
if showId == 'N':
    report += """\
  <span class="sectionHdr">%s (%d)</span>
  <DL>
""" % (board_type, boardCount[board_type])

    for row in rows:
        # If we encounter a new board_type we need to create a new
        # heading
        # ----------------------------------------------------------
        if row[5] == board_type:
            if lang == 'English':
                report += summaryRow(row[1])
            else:
                report += summaryRowES(row[1], row[4])

        # For the Treatment Summary Type we need to check if this is an 
        # adult or pediatric summary
        # -------------------------------------------------------------
        else:
            board_type = row[5]
            report += boardHeader(board_type)
            if lang == 'English':
                report += summaryRow(row[1])
            else:
                report += summaryRowES(row[1], row[4])
# ------------------------------------------------------------------------
# Display data including CDR ID
# English and Spanish data to be displayed identically except that the 
# English translation of the summary titles is displayed under the title
# ------------------------------------------------------------------------
else:
    report += """\
  <span class="sectionHdr">%s (%d)</span>
  <TABLE width = "100%%">
""" % (board_type, boardCount[board_type])

    for row in rows:
        # If we encounter a new board_type we need to create a new
        # heading
        # ----------------------------------------------------------
        if row[5] == board_type:
            if lang == 'English':
                report += summaryRowWithID(row[0], row[1])
            else:
                report += summaryRowESWithID(row[0], row[1], row[4])
        else:
            board_type = row[5]
            report += boardHeaderWithID(board_type)
            if lang == 'English':
                report += summaryRowWithID(row[0], row[1])
            else:
                report += summaryRowESWithID(row[0], row[1], row[4])

    report += """
  </TABLE>
"""

footer = """\
 </BODY>
</HTML> 
"""     

# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + report + footer)
