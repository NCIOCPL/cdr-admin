#----------------------------------------------------------------------
#
# Report on lists of summaries.
#
# BZIssue::1231 - initial version; based on SummariesLists.py
# BZIssue::3716 - unicode cleanup
# BZIssue::4207 - board name modification; UI enhancements
# BZIssue::5104 - [Summaries] Changes to Summaries TOC Lists report
# JIRA::OCECDR-4078 - reduce indentation
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, time
from cdrapi import db
from html import escape as html_escape

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields and fields.getvalue("Boolean")          or "AND"
audience  = fields and fields.getvalue("audience")         or None
lang      = fields and fields.getvalue("lang")             or None
showId    = fields and fields.getvalue("showId")           or "N"
tocLevel  = fields and fields.getvalue("tocLevel")         or "9"
groups    = fields and fields.getlist("grp")               or []
byCdrid   = fields and fields.getvalue("byCdrid")          or None
docVers   = fields and fields.getvalue("DocVersion")       or None
byTitle   = fields and fields.getvalue("byTitle")          or None
submit    = fields and fields.getvalue("SubmitButton")     or None
docType   = "Summary"
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Summaries TOC Lists"
script    = "SummariesTocReport.py"
SUBMENU   = "Report Menu"
buttons   = ("Submit", SUBMENU, cdrcgi.MAINMENU)
header   = cdrcgi.header(title, title, "Summaries TOC Report",
                         script, buttons, method = 'GET',
                         stylesheet = """
  <style type = 'text/css'>
    body            { font: 12pt "Arial"; }
    span.ip:hover     { background-color: #FFFFCC; }
    fieldset        { margin-bottom: 10px; }
    /* fieldset.docversion { width: 860px; */
    fieldset.docversion
                    { width: 75%;
                      margin-left: auto;
                      margin-right: auto;
                      margin-bottom: 0;
                      display: block; }
    fieldset.wrapper{ width: 520px;
                      margin-left: auto;
                      margin-right: auto;
                      display: block; }
    *.gogreen       { width: 95%;
                      border: 1px solid green;
                      background: #99FF66; }
    *.gg            { border: 1px solid green;
                      background: #99FF66;
                      color: #006600; }
    *.comgroup      { background: #C9C9C9;
                      margin-bottom: 8px; }
  </style>
""")

# Testing
#byCdrid = 62875
#byTitle = 'Breast'

#----------------------------------------------------------------------
# Some input validation
#----------------------------------------------------------------------
if showId not in ('Y', 'N'):
    cdrcgi.bail("Invalid showId, internal error, please inform support staff")

# Audience isn't using the exact canonical forms
if audience and audience not in ('Health Professional', 'Patient'):
    cdrcgi.bail("Invalid audience, internal error, please inform support staff")

if lang and lang not in cdr.getSummaryLanguages():
    cdrcgi.bail("Invalid language, internal error, please inform support staff")

if tocLevel and not tocLevel.isdigit():
    cdrcgi.bail("Expecting integer table of contents (TOC) level")

# Expecting '-1' or a positive integer
if docVers and not (docVers == '-1' or docVers.isdigit()):
    cdrcgi.bail("Internal error, document version is not in the select list")

# ----------------------------------------------------
# Functions to replace sevaral repeated HTML snippets
# ----------------------------------------------------
def boardHeader(header):
    """Return the HTML code to display the Summary Board Header"""
    html = """\
  <U><H4>%s</H4></U>
""" % board_type
    return html

#----------------------------------------------------------------------
# More than one matching title; let the user choose one.
#----------------------------------------------------------------------
def showTitleChoices(choices):
    form = """\
   <H3>More than one matching document found; please choose one.</H3>
"""
    i = 0
    for choice in choices:
        i += 1
        form += """\
   <span class="ip">
    <INPUT TYPE='radio' NAME='byCdrid' VALUE='CDR%010d' id='byCdrid%d'>
    <label for='byCdrid%d'>%s (CDR%06d)</label><br>
   </span>
""" % (choice[0], i, i, html_escape(choice[1]), choice[0])
    cdrcgi.sendPage(header + form + """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='showId' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='tocLevel' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, docType, 'TOC', showId, tocLevel))

# ----------------------------------------------------
#
# ----------------------------------------------------
def summaryRow(id, summary, toc, docVersion = None):
    """Return the HTML code to display a Summary row"""
    response = cdr.filterDoc('guest',
                     ['name:Denormalization Filter: Summary Module',
                      'name:Wrap nodes with Insertion or Deletion',
                      'name:Clean up Insertion and Deletion',
                      'name:Summaries TOC Report'],
                     id, parm = filterParm, docVer = docVersion)
    html = response[0]
    html += """\
"""
    return html

#----------------------------------------------------------------------
# If the user only picked one summary group, put it into a list so we
# can deal with the same data structure whether one or more were
# selected.
#----------------------------------------------------------------------
if isinstance(groups, str):
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
    conn = db.connect(user="CdrGuest")
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail('Database connection failure: %s' % e)

#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y")

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not lang and (not byCdrid and not byTitle):
                           #("Submit",
                           # SUBMENU,
                           # cdrcgi.MAINMENU),
    header = cdrcgi.header(title, title, instr + ' - ' + dateString,
                           script, buttons,
                           numBreaks = 1,
                           stylesheet = """
   <STYLE type="text/css">
    TD      { font-size:  12pt; }
    LI.none { list-style-type: none }
    DL      { margin-left: 0; padding-left: 0 }
    *.singletoc, *.multitoc, *.alltoc
            { width: 50%;
              font: 12pt "Arial";
              border: 2px solid white;
              margin-top: 20px;
              margin-bottom: 20px;
              margin-left: auto;
              margin-right:auto;
              padding: 5px;
              background: #CCCCCC; }
    *.alltoc
            { background: #CCDDCC; }

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
   <input type='hidden' name='singletoc' value='N'>

   <div class='singletoc'>
   <b>Single Summary</b>
   <fieldset>
    <legend>&nbsp;Document Title or CDR-ID&nbsp;</legend>
    <label for="byCdrid">CDR-ID</label>
    <input name='byCdrid' size='15' id="byCdrid">
    <br>
    <label for="byTitle">Title</label>
    <input name='byTitle' size='40' id='byTitle'>
   </fieldset>
   </div>

   <div class='alltoc'>
   <b>Shared Options (Single Summary, All Summaries)</b>
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
   </div>

   <div class='multitoc'>
   <b>All Summaries</b>
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
             value='Integrative, Alternative, and Complementary Therapies'
                    onclick="javascript:someEnglish()" id="E3">
       <label id="E3">Integrative, Alternative, and Complementary Therapies</label><br>
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
             onclick="javascript:allSpanish(this, 5)" id="allEs" CHECKED>
         <label id="allEs">All Spanish</label><br>
      <input type='checkbox' name='grp' value='Spanish Adult Treatment'
             onclick="javascript:someSpanish()" id="S1">
         <label id="S1">Adult Treatment</label><br>
      <input type='checkbox' name='grp'
           value='Spanish Integrative, Alternative, and Complementary Therapies'
                    onclick="javascript:someSpanish()" id="S2">
         <label id="S2">Integrative, Alternative, and Complementary Therapies</label><br>
      <input type='checkbox' name='grp' value='Spanish Pediatric Treatment'
             onclick="javascript:someSpanish()" id="S3" >
         <label id="S3">Pediatric Treatment</label><br>
      <input type='checkbox' name='grp' value='Spanish Screening and Prevention'
             onclick="javascript:someSpanish()" id="S4">
         <label id="S4">Screening and Prevention</label><br>
      <input type='checkbox' name='grp' value='Spanish Supportive Care'
             onclick="javascript:someSpanish()" id="S5" >
         <label id="S5">Supportive and Palliative Care</label><br>
     </td>
    </tr>
   </table>
   </fieldset>
   </div>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# If we have a document title but not a document ID, find the ID.
#----------------------------------------------------------------------
#if not lang and not docId:
if byTitle and byCdrid:
    byTitle = None

if byTitle:
    lookingFor = 'title'
    try:
        cursor.execute("""\
            SELECT d.id, d.title
              FROM document d
              JOIN doc_type dt
                on dt.id = d.doc_type
             WHERE title LIKE ?
               AND dt.name = '%s'
             ORDER BY d.title""" % docType, '%' + byTitle + '%')
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find document with %s '%s'" % (lookingFor,
                                                                   byTitle))
        if len(rows) > 1:
            showTitleChoices(rows)
        intId = rows[0][0]
        docId = "CDR%010d" % intId
    except Exception as e:
        cdrcgi.bail('Failure looking up document %s: %s' % (lookingFor, e))

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
  if groups[i] == 'Adult Treatment'            and lang == 'English':
      boardPick += """'CDR0000028327', 'CDR0000035049', """
  elif groups[i] == 'Spanish Adult Treatment'  and lang == 'Spanish':
      boardPick += """'CDR0000028327', 'CDR0000035049', """
  elif groups[i] == 'Integrative, Alternative, and Complementary Therapies' \
                                               and lang == 'English':
      boardPick += """'CDR0000256158', 'CDR0000423294', """
  elif groups[i] == 'Spanish Integrative, Alternative, and Complementary Therapies' \
                                               and lang == 'Spanish':
      boardPick += """'CDR0000256158', 'CDR0000423294', """
  elif groups[i] == 'Genetics':
      boardPick += """'CDR0000032120', 'CDR0000257061', """
  elif groups[i] == 'Screening and Prevention' and lang == 'English':
      boardPick += """'CDR0000028536', 'CDR0000028537', """
  elif groups[i] == 'Spanish Screening and Prevention' and lang == 'Spanish':
      boardPick += """'CDR0000028536', 'CDR0000028537', """   ### XXX
  elif groups[i] == 'Pediatric Treatment'      and lang == 'English':
      boardPick += """'CDR0000028557', 'CDR0000028558', """
  elif groups[i] == 'Spanish Pediatric Treatment' and lang == 'Spanish':
      boardPick += """'CDR0000028557', 'CDR0000028558', """
  elif groups[i] == 'Supportive Care'          and lang == 'English':
      boardPick += """'CDR0000028579', 'CDR0000029837', """
  elif groups[i] == 'Spanish Supportive Care'  and lang == 'Spanish':
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
            WHEN board.value = 'CDR0000256158'  THEN 'Integrative, Alternative, and Complementary Therapies'
            WHEN board.value = 'CDR0000423294'  THEN 'Integrative, Alternative, and Complementary Therapies'
            WHEN board.value = 'CDR0000028557'  THEN 'Pediatric Treatment'
            WHEN board.value = 'CDR0000028558'  THEN 'Pediatric Treatment'
            WHEN board.value = 'CDR0000028536'  THEN 'Screening and Prevention'
            WHEN board.value = 'CDR0000028537'  THEN 'Screening and Prevention'
            WHEN board.value = 'CDR0000028579'  THEN 'Supportive and Palliative Care'
            WHEN board.value = 'CDR0000029837'  THEN 'Supportive and Palliative Care'
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
# If we are running the report for a single summary but we don't have
# a version number yet, display the intermediary screen to select the
# version.
#----------------------------------------------------------------------
vrows = []
cursor = conn.cursor()
letUserPickVersion = True
if byCdrid:
    byCdrid = cdr.exNormalize(byCdrid)[1]
    if not docVers:
        try:
            cursor.execute("""\
                SELECT num,
                       comment,
                       dt
                  FROM doc_version
                 WHERE id = ?
              ORDER BY num DESC""", byCdrid)
            vrows = cursor.fetchall()
        except Exception as e:
            cdrcgi.bail('Failure retrieving document versions: %s' % e)
        form = """\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>
      <INPUT TYPE='hidden' NAME='byCdrid' VALUE='CDR%010d'>
      <INPUT TYPE='hidden' NAME='showId' VALUE='%s'>
      <INPUT TYPE='hidden' NAME='tocLevel' VALUE='%s'>
    """ % (cdrcgi.SESSION, session, docType, byCdrid, showId, tocLevel)

        form += """\
      <fieldset class='docversion'>
       <legend>&nbsp;Select document version&nbsp;</legend>
      <div style="width: 100%; text-align: center;">
      <div style="margin: 0 auto;">
      <SELECT NAME='DocVersion'>
       <OPTION VALUE='-1' SELECTED='1'>Current Working Version</OPTION>
    """

        # Limit display of version comment to 120 chars (if exists)
        # ---------------------------------------------------------
        for row in vrows:
            form += """\
       <OPTION VALUE='%d'>[V%d %s] %s</OPTION>
    """ % (row[0], row[0], str(row[2])[:10],
           not row[1] and "[No comment]" or row[1][:120])
            selected = ""
        form += "</SELECT></div></div>"
        form += """
      </fieldset>
    """
        cdrcgi.sendPage(header + form)

    else:
        if docVers == "-1": docVers = None

    # We need the summary title to display on the report
    # --------------------------------------------------
    try:
        query = """\
    SELECT DISTINCT qt.doc_id, title.value DocTitle,
                    'dummy1', 'dummy2', title.value EnglTitle, ' '
      FROM query_term qt
      JOIN query_term title
        ON qt.doc_id = title.doc_id
     WHERE title.path = '/Summary/SummaryTitle'
       AND qt.doc_id = %s""" % byCdrid

        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except Exception as e:
        cdrcgi.bail('Failure retrieving single Summary document: %s' % e)
else:
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except Exception as e:
        cdrcgi.bail('Failure retrieving Summary documents: %s' % e)

if not rows and not vrows:
    cdrcgi.bail('No Records Found for Selection: %s ' % lang+"; "+audience+"; "+groups[0] )

#cdrcgi.bail("Result: [%s]" % rows)
#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
instr     = 'Section Titles for %s Summaries -- %s.' % (lang, dateString)
header    = cdrcgi.rptHeader(title, instr,
                          stylesheet = """\
   <STYLE type="text/css">
    UL             { margin: 0pt; margin-left: 25px; padding-left: 5px; }
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
    *.Insertion    { color: red; }
    *.Deletion     { color: red;
                     text-decoration: line-through; }
   </STYLE>
""")

# -------------------------
# Display the Report Titles
# -------------------------
# Single Summary TOC Report
if byCdrid:
    report    = """\
       <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      </FORM>
      <div class="ehdr">Single Summary TOC Report<br>
      <span class="hdrDate">%s</span>
      </div>
    """ % (cdrcgi.SESSION, session, dateString)
# Multi-Summary TOC Report
else:
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

board_type = rows[0][5] or None

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
       report += summaryRow(row[0], row[1], toc = tocLevel,
                                               docVersion = docVers)
       #if lang == 'English':
       #   report += summaryRow(row[0], row[1], toc = tocLevel,
       #                                        docVersion = docVers)
       #else:
       #   report += summaryRow(row[0], row[1], toc = tocLevel,
       #                                        docVersion = docVers)

    # For the Treatment Summary Type we need to check if this is an
    # adult or pediatric summary
    # -------------------------------------------------------------
    else:
       board_type = row[5]
       report += boardHeader(board_type)
       report += summaryRow(row[0], row[1], toc = tocLevel,
                                               docVersion = docVers)
       #if lang == 'English':
       #   report += summaryRow(row[0], row[1], toc = tocLevel,
       #                                        docVersion = docVers)
       #else:
       #   report += summaryRow(row[0], row[1], toc = tocLevel,
       #                                        docVersion = docVers)
footer = """\
 </BODY>
</HTML>
"""

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + report + footer)
