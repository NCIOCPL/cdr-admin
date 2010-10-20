#----------------------------------------------------------------------
#
# $Id: $
#
# Report listing summaries containing specified markup.
#
# BZIssue::4671 - Summaries with Mark-up Report
# BZIssue::4922 - Enhancements to the Summaries with Markup Report
#
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, time, cdrdb, xml.dom.minidom

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
instr     = "Summaries with Mark-up"
script    = "SummariesWithMarkup.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

if type(showId) == type(""):
    showId = [showId]

# The ReportType is needed to redirect the users to the interim page for
# displaying markup QC reports
# ----------------------------------------------------------------------
if audience == 'Health Professional':
    ReportType = 'rs'
else:
    ReportType = 'pat'

# ---------------------------------------------------
# Functions to replace sevaral repeated HTML snippets
# ---------------------------------------------------
# def boardHeader(board_type):
#     """Return the HTML code to display the Summary Board Header"""
#     html = """\
#   </DL>
#   <span class="sectionHdr">%s (%d)</span>
#   <DL>
# """ % (board_type, boardCount[board_type])
#     return html
# 

# ---------------------------------------------------
# 
# ---------------------------------------------------
def boardHeaderWithID(board_type):
    """Return the HTML code to display the Summary Board Header with ID"""
    html = """\
  </TABLE>

  <span class="sectionHdr">%s</span>
  <TABLE border="1" width = "90%%">
   <tr>
    <th>ID</th>
    <th>Summary</th>
    <th>Publish</th>
    <th>Approved</th>
    <th>Proposed</th>
    <th>Rejected</th>
    <th>Advisory</th>
   </tr>
""" % (board_type)
    return html


# ------------------------------------------------
# Create the table row for the English list output
# ------------------------------------------------
# def summaryRow(summary):
#     """Return the HTML code to display a Summary row"""
#     html = """\
#    <LI class="report">%s</LI>
# """ % (row[1])
#     return html
# 

# -------------------------------------------------
# Create the table row for the English table output
# -------------------------------------------------
def summaryRowWithID(id, summary, boardCount, display, ReportType = 'rs'):
    """Return the HTML code to display a Summary row with ID"""

    # The users only want to display those summaries that do have
    # markup, so we need to suppress the once that don't by counting
    # the number of markup elements.
    # --------------------------------------------------------------
    #cdrcgi.bail(display)
    num = 0
    for list in display:
        num += boardCount[list]

    if num == 0: return ""

    # Create the table row display
    # If a markup type hasn't been checked the table cell will be
    # displayed with the class="nodisplay" style otherwise the 
    # count of the markup type is being displayed.
    # ------------------------------------------------------
    html = """\
   <TR>
    <TD class="report cdrid" width = "7%%">
     <a href="/cgi-bin/cdr/QcReport.py?DocId=CDR%s&DocType=Summary&ReportType=%s&Session=guest">%s</a>
    </TD>
    <TD class="report">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
   </TR>
""" % (id, ReportType, id, summary, 
           'publish' in display and 'display' or 'nodisplay',
           ('publish' not in display or boardCount['publish']  == 0) 
                           and '&nbsp;' or boardCount['publish'], 
           'approved' in display and 'display' or 'nodisplay',
           ('approved' not in display or boardCount['approved'] == 0) 
                           and '&nbsp;' or boardCount['approved'],
           'proposed' in display and 'display' or 'nodisplay',
           ('proposed' not in display or boardCount['proposed'] == 0) 
                           and '&nbsp;' or boardCount['proposed'], 
           'rejected' in display and 'display' or 'nodisplay',
           ('rejected' not in display or boardCount['rejected'] == 0) 
                           and '&nbsp;' or boardCount['rejected'],
           'advisory' in display and 'display' or 'nodisplay',
           ('advisory' not in display or boardCount['advisory'] == 0) 
                           and '&nbsp;' or boardCount['advisory'])
    return html


# -------------------------------------------------
# Create the table row for the Spanish table output
# -------------------------------------------------
def summaryRowESWithID(id, summary, translation, boardCount, display, 
                       ReportType = 'rs'):
    """Return the HTML code to display a Spanish Summary row with ID"""
    # The users only want to display those summaries that do have
    # markup, so we need to suppress the once that don't by counting
    # the number of markup elements.
    # --------------------------------------------------------------
    #cdrcgi.bail(display)
    num = 0
    for list in display:
        num += boardCount[list]

    if num == 0: return ""

    # Create the table row display
    # If a markup type hasn't been checked the table cell will be
    # displayed with the class="nodisplay" style otherwise the 
    # count of the markup type is being displayed.
    # ------------------------------------------------------
    html = """\
   <TR>
    <TD class="report cdrid" width = "7%%">
     <a href="/cgi-bin/cdr/QcReport.py?DocId=CDR%s&DocType=Summary&ReportType=%s&Session=guest">%s</a>
    </TD>
    <TD class="report">%s<BR/>
     (%s)
    </TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
   </TR>
""" % (id, ReportType, id, summary, translation,
           'publish' in display and 'display' or 'nodisplay',
           ('publish' not in display or boardCount['publish']  == 0) 
                           and '&nbsp;' or boardCount['publish'], 
           'approved' in display and 'display' or 'nodisplay',
           ('approved' not in display or boardCount['approved'] == 0) 
                           and '&nbsp;' or boardCount['approved'],
           'proposed' in display and 'display' or 'nodisplay',
           ('proposed' not in display or boardCount['proposed'] == 0) 
                           and '&nbsp;' or boardCount['proposed'], 
           'rejected' in display and 'display' or 'nodisplay',
           ('rejected' not in display or boardCount['rejected'] == 0) 
                           and '&nbsp;' or boardCount['rejected'],
           'advisory' in display and 'display' or 'nodisplay',
           ('advisory' not in display or boardCount['advisory'] == 0) 
                           and '&nbsp;' or boardCount['advisory'])
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
    label   { font: 12pt "Arial"; }
    LI.none { list-style-type: none }
    DL      { margin-left: 0; padding-left: 0 }
   </STYLE>
""" )

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
    <legend>&nbsp;Type of mark-up&nbsp;</legend>
    <input name='showId' type='checkbox' id="pub"
           value='publish' CHECKED>
    <label for="pub">Publish</label>
    <br>
    <input name='showId' type='checkbox' id="app"
           value='approved' CHECKED>
    <label for="app">Approved</label>
    <br>
    <input name='showId' type='checkbox' id="pro"
           value='proposed' CHECKED>
    <label for="pro">Proposed</label>
    <br>
    <input name='showId' type='checkbox' id="rej"
           value='rejected' CHECKED>
    <label for="rej">Rejected</label>
    <br>
    <hr width="25%%">
    <input name='showId' type='checkbox' id="adv"
           value='advisory' CHECKED>
    <label for="adv">Advisory Board mark-up</label>
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
       <input type='checkbox' name='grp' 
              value='Adult Treatment' id="E1">
       <label for="E1">Adult Treatment</label>
       <br>
       <input type='checkbox' name='grp' 
              value='Genetics' id="E2">
       <label for="E2">Cancer Genetics</label>
       <br>
       <input type='checkbox' name='grp'
              value='Complementary and Alternative Medicine' id="E3">
       <label for="E3">Complementary and Alternative Medicine</label>
       <br>
       <input type='checkbox' name='grp' 
              value='Pediatric Treatment' id="E4">
       <label for="E4">Pediatric Treatment</label>
       <br>
       <input type='checkbox' name='grp' 
              value='Screening and Prevention' id="E5">
       <label for="E5">Screening and Prevention</label>
       <br>
       <input type='checkbox' name='grp' 
              value='Supportive Care' id="E6">
       <label for="E6">Supportive and Palliative Care</label>
       <br><br>
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
      <input type='checkbox' name='grp' 
             value='Spanish Adult Treatment' id="S1" >
       <label for="S1">Adult Treatment</label><br>
      <input type='checkbox' name='grp' 
             value='Spanish Pediatric Treatment' id="S2" >
       <label for="S2">Pediatric Treatment</label><br>
      <input type='checkbox' name='grp' 
             value='Spanish Supportive Care' id="S3" >
       <label for="S3">Supportive and Palliative Care</label><br>
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
    doc = cdr.getDoc('guest', board[0], getObject = 1)

    #if doc.xml.startswith("<Errors"):
    #    continue
    
    dom = xml.dom.minidom.parseString(doc.xml)
    boardCount[board[0]] = {'publish':0, 
                            'approved':0,
                            'proposed':0,
                            'rejected':0,
                            'advisory':0}
    
    insertionElements = dom.getElementsByTagName('Insertion')  
    for obj in insertionElements:
        boardCount[board[0]][obj.getAttribute('RevisionLevel')] += 1
        advLevel = obj.getAttribute('Source')
        if advLevel == 'advisory-board':
            boardCount[board[0]]['advisory'] += 1

    deletionElements  = dom.getElementsByTagName('Deletion')
    for obj in deletionElements:
        boardCount[board[0]][obj.getAttribute('RevisionLevel')] += 1
        advLevel = obj.getAttribute('Source')
        if advLevel == 'advisory-board':
            boardCount[board[0]]['advisory'] += 1

#cdrcgi.bail(boardCount)


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

    .date          { font-size: 12pt; }
    .sectionHdr    { font-size: 12pt;
                     font-weight: bold;
                     text-decoration: underline; }
    td.report      { font-size: 11pt;
                     padding-right: 15px; 
                     vertical-align: top; }
    td.nodisplay   { background-color: grey; }
    td.display     { background-color: white; 
                     font-weight: bold;
                     text-align: center; }
    .cdrid         { text-align: right; 
                     text-decoration: underline; 
                     text-color: blue; }
    LI             { list-style-type: none; }
    li.report      { font-size: 11pt;
                     font-weight: normal; }
    div.es         { height: 10px; }
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

board_type = rows[0][5]

# ------------------------------------------------------------------------
# Display data including CDR ID
# English and Spanish data to be displayed identically except that the 
# English translation of the summary titles is displayed under the title
# ------------------------------------------------------------------------
#cdrcgi.bail(showId)
# if showId == 'N':
#     cdrcgi.bail(board_type)
#     report += """\
#   <span class="sectionHdr">%s</span>
#   <DL>
# """ % (board_type)
# 
#     for row in rows:
#         # If we encounter a new board_type we need to create a new
#         # heading
#         # ----------------------------------------------------------
#         if row[5] == board_type:
#             if lang == 'English':
#                 report += summaryRow(row[1], boardCount[row[0]])
#             else:
#                 report += summaryRowES(row[1], row[4])
# 
#         # For the Treatment Summary Type we need to check if this is an 
#         # adult or pediatric summary
#         # -------------------------------------------------------------
#         else:
#             board_type = row[5]
#             report += boardHeader(board_type)
#             if lang == 'English':
#                 report += summaryRow(row[1])
#             else:
#                 report += summaryRowES(row[1], row[4])
# ------------------------------------------------------------------------
# Display data including CDR ID
# English and Spanish data to be displayed identically except that the 
# English translation of the summary titles is displayed under the title
# ------------------------------------------------------------------------
# else:
#cdrcgi.bail(board_type)
report += """\
  <span class="sectionHdr">%s</span>
  <TABLE border="1" width = "90%%">
   <tr>
    <th>ID</th>
    <th>Summary</th>
    <th>Publish</th>
    <th>Approved</th>
    <th>Proposed</th>
    <th>Rejected</th>
    <th>Advisory</th>
   </tr>
""" % (board_type)

for row in rows:
    # If we encounter a new board_type we need to create a new
    # heading
    # ----------------------------------------------------------
    if row[5] == board_type:
        if lang == 'English':
            report += summaryRowWithID(row[0], row[1],
                                       boardCount[row[0]],
                                       showId, ReportType)
        else:
            report += summaryRowESWithID(row[0], row[1], row[4],
                                         boardCount[row[0]],
                                         showId, ReportType)
    else:
        board_type = row[5]
        report += boardHeaderWithID(board_type)
        if lang == 'English':
            report += summaryRowWithID(row[0], row[1],
                                         boardCount[row[0]],
                                         showId, ReportType)
        else:
            report += summaryRowESWithID(row[0], row[1], row[4],
                                         boardCount[row[0]],
                                         showId, ReportType)

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
