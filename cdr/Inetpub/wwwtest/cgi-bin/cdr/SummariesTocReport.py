#----------------------------------------------------------------------
#
# $Id: SummariesTocReport.py,v 1.5 2008-09-29 17:48:21 venglisc Exp $
#
# Report on lists of summaries.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2008/09/29 17:46:41  venglisc
# Modified Supportive Care board name. (Bug 4207)
# Also modified user interface to use fieldsets.
#
# Revision 1.3  2007/11/03 14:15:07  bkline
# Unicode encoding cleanup (issue #3716).
#
# Revision 1.2  2004/08/16 20:03:24  venglisc
# Added CSS to display the TOC levels indented.  Added help message.
# (Bug 1231)
#
# Revision 1.1  2004/07/13 20:11:36  venglisc
# Initial version of program to display a list of Summary Section Titles by
# summary board (Bug 1231).
# The user interface has been "borrowed" from SummariesLists.py.
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields and fields.getvalue("Boolean")          or "AND"
audience  = fields and fields.getvalue("audience")         or None
lang      = fields and fields.getvalue("lang")             or None
showId    = fields and fields.getvalue("showId")           or "N"
tocLevel  = fields and fields.getvalue("tocLevel")         or "3"
groups    = fields and fields.getvalue("grp")              or []
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Summaries TOC Lists"
script    = "SummariesTocReport.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

# Functions to replace sevaral repeated HTML snippets
# ===================================================
def boardHeader(header):
    """Return the HTML code to display the Summary Board Header"""
    html = """\
  <U><H4>%s</H4></U>
""" % board_type
    return html

def summaryRow(id, summary, toc):
    """Return the HTML code to display a Summary row"""
    response = cdr.filterDoc('guest', ['name:Summaries TOC Report'], id, 
                             parm = filterParm)
    html = unicode(response[0], "utf-8")
    html += """\
"""
    return html

#----------------------------------------------------------------------
# If the user only picked one summary group, put it into a list so we
# can deal with the same data structure whether one or more were
# selected.
#----------------------------------------------------------------------
if type(groups) in (type(""), type(u"")):
    groups = [groups]

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
    <legend>&nbsp;TOC Levels?&nbsp;</legend>
    <input name='tocLevel' type='text' size='1' value='3' CHECKED>
    (QC Report uses "3" - leave blank to see all levels)
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
      boardPick += """'CDR0000256158', """
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

# --------------------------------------------------------------
# Define the Headings under which the summaries should be listed
# --------------------------------------------------------------
q_case = """\
       CASE WHEN board.value = 'CDR0000028327'  THEN 'Adult Treatment'
            WHEN board.value = 'CDR0000035049'  THEN 'Adult Treatment'
            WHEN board.value = 'CDR0000032120'  THEN 'Cancer Genetics'
            WHEN board.value = 'CDR0000257061'  THEN 'Cancer Genetics'
            WHEN board.value = 'CDR0000256158'  THEN 'Complementary and Alternative Medicine'
            WHEN board.value = 'CDR0000028557'  THEN 'Pediatric Treatment'
            WHEN board.value = 'CDR0000028558'  THEN 'Pediatric Treatment'
            WHEN board.value = 'CDR0000028536'  THEN 'Screening and Prevention'
            WHEN board.value = 'CDR0000028537'  THEN 'Screening and Prevention'
            WHEN board.value = 'CDR0000028579'  THEN 'Supportive Care'
            WHEN board.value = 'CDR0000029837'  THEN 'Supportive Care'
            ELSE board.value END
"""

# ------------------------------------------------------------------------
# Create the selection criteria for the summary language (English/Spanish)
# ------------------------------------------------------------------------
q_lang = """\
AND    lang.path = '/Summary/SummaryMetaData/SummaryLanguage'
AND    lang.value = '%s'
""" % lang

# ---------------------------------------------------------------------
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

# ---------------------------------------------------
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

# -------------------------------------------------------------
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

#----------------------------------------------------------------------
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

#cdrcgi.bail("Result: [%s]" % rows)
#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
instr     = 'Section Titles for %s Summaries -- %s.' % (lang, dateString)
header    = cdrcgi.rptHeader(title, instr,
                          stylesheet = """\
   <STYLE type="text/css">
    UL             { margin: 0pt; }
    UL UL          { margin-left: 30pt; }
    UL UL UL       { margin-left: 30pt; }
    UL UL UL UL    { margin-left: 30pt; }
    UL UL UL UL UL { margin-left: 30pt; }
    LI             { font-style: normal;
                     font-family: Arial;
                     font-weight: normal; 
                     font-size: 12pt;
                     list-style-type: none; }
    H5             { font-weight: bold;
                     font-family: Arial;
                     font-size: 13pt; 
                     margin: 0pt; }
    *.ehdr         { font-size: 18pt;
                     font-weight: bold;
                     text-align: center; 
                     width: 420px; }
    *.shdr         { font-size: 18pt;
                     font-weight: bold;
                     text-align: center; 
                     width: 540px; }
    *.hdrDate      { font-size: 12pt;
                     font-weight: bold; }
   </STYLE>
""")

# -------------------------
# Display the Report Title
# -------------------------
if lang == 'English':
    report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
  <div class="ehdr">PDQ %s Summaries<br>
  <span class="hdrDate">%s</span>
  </div>
""" % (cdrcgi.SESSION, session, audience, dateString)
else:
    report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
  <div class="shdr">PDQ %s %s Summaries<br>
  <span class="hdrDate">%s</span>
  </div>
""" % (cdrcgi.SESSION, session, lang, audience, dateString)

board_type = rows[0][5]

# -------------------------------------------------------------------
# Decision if the CDR IDs are displayed along with the summary titles
# - The report without CDR ID is displayed as a bulleted list.
# - The report with    CDR ID is displayed in a table format.
# -------------------------------------------------------------------
# ------------------------------------------------------------------------
# Display Summary Title including CDR ID
# ------------------------------------------------------------------------
filterParm = []
filterParm = [['showLevel', tocLevel], ['showId', showId ]]
report += """\
  <U><H4>%s</H4></U>
""" % board_type

for row in rows:
    # If we encounter a new board_type we need to create a new
    # heading
    # ----------------------------------------------------------
    if row[5] == board_type:
       if lang == 'English':
          report += summaryRow(row[0], row[1], toc = tocLevel)
       else:
          report += summaryRow(row[0], row[1], toc = tocLevel)

    # For the Treatment Summary Type we need to check if this is an 
    # adult or pediatric summary
    # -------------------------------------------------------------
    else:
       board_type = row[5]
       report += boardHeader(board_type)
       if lang == 'English':
          report += summaryRow(row[0], row[1], toc = tocLevel)
       else:
          report += summaryRow(row[0], row[1], toc = tocLevel)
footer = """\
 </BODY>
</HTML> 
"""     

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + report + footer)
