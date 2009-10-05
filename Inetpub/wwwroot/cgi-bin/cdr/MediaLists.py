#----------------------------------------------------------------------
#
# $Id: MediaLists.py,v 1.1 2008-12-29 21:25:32 venglisc Exp $
#
# Report to list Media documents modified between a certain time 
# interval.  The user can select to filter by a category and/or
# diagnosis.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, time, cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
showId    = fields and fields.getvalue("showId")           or "N"
#submit    = fields and fields.getvalue("SubmitButton")     or None
diagnoses = fields and fields.getvalue("Diagnosis")        or []
categories= fields and fields.getvalue("Category")         or []
request   = cdrcgi.getRequest(fields)
title     = "CDR Media List"
instr     = "Media Lists"
script    = "MediaLists.py"
SUBMENU   = "Report Menu"


# ------------------------------------------------
# Create the table row for the report
# ------------------------------------------------
def summaryRow(summary):
    """Return the HTML code to display a Summary row"""
    html = """\
   <LI class="report">%s</LI>
""" % (row[1])
    return html


# -------------------------------------------------
# Create the table row with CDR-ID for the report
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

# ---------------------------------------------------------------------
# Select all the existing categories in the data to be displayed in 
# the selection window
# ---------------------------------------------------------------------
def getCategories():
    query = """
       SELECT DISTINCT value
         FROM query_term
        WHERE path = '/Media/MediaContent/Categories/Category'"""
    try:
        cursor.execute(query)
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving categories: %s' %
                info[1][0])
    return cursor.fetchall()

# ---------------------------------------------------------------------
# Select all the existing diagnoses names in the data to be displayed
# on the final report
# ---------------------------------------------------------------------
def getDiagnosesNames(cdrIds):
    if not cdrIds:
        return

    query = """
       SELECT value
         FROM query_term
        WHERE path = '/Term/PreferredName'
          AND doc_id in (%s)
        ORDER BY value""" % cdrIds
    try:
        cursor.execute(query)
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving diagnosis names: %s' %
                info[1][0])
    rows = cursor.fetchall()
    return ', '.join(['%s' % row[0] for row in rows])


# ---------------------------------------------------------------------
# Select all the existing diagnoses IDs in the data to be displayed in 
# the selection box.
# ---------------------------------------------------------------------
def getDiagnoses():
    query = """
       SELECT DISTINCT t.doc_id, t.value
         FROM query_term t
         JOIN query_term m
           ON t.doc_id = m.int_val
          AND m.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'
        WHERE t.path = '/Term/PreferredName'
        ORDER BY t.value"""
    try:
        cursor.execute(query)
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving diagnosis: %s' %
                info[1][0])
    return cursor.fetchall()

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not categories:
    header = cdrcgi.header(title, title, instr + ' - ' + dateString, 
                           script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1,
                           stylesheet = """
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script language='JavaScript' src='/js/CdrCalendar.js'></script>

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
    <legend>&nbsp;Display CDR-ID?&nbsp;</legend>
    <input name='showId' type='radio' id="idNo"
           value='N' CHECKED>
    <label for="idNo">Without CDR-ID</label>
    <br>
    <input name='showId' type='radio' id="idYes"
           value='Y'>
    <label for="idYes">With CDR-ID</label>
   </fieldset>
""" % (cdrcgi.SESSION, session)

    # Build the option list for the categories
    # -----------------------------------------
    form  += """\
   <fieldset>
    <legend>&nbsp;Select Categories&nbsp;</legend>
    <select name='Category' multiple='1' size='7'>
     <option value='any' selected='1'>All Categories</option>
"""
    for category in getCategories():
        form += "     <option value='%s'>%s</option>\n" % (category[0], 
                                                           category[0])
    form += """    </select>
   </fieldset>
"""

    # Build the option list for the diagnoses
    # -----------------------------------------
    form  += """\
   <fieldset>
    <legend>&nbsp;Select Diagnoses&nbsp;</legend>
    <select name='Diagnosis' multiple='1' size='7'>
     <option value='any' selected='1'>All Diagnoses</option>
"""
    for cdrId, diagnosis in getDiagnoses():
        form += "     <option value='%s'>%s</option>\n" % (cdrId, 
                                                           diagnosis)
    form += """    </select>
   </fieldset>
"""

    form  += """\
  </form>
 </body>
</html>
"""
    cdrcgi.sendPage(header + form)

# Build the string for the categories to be passed to the IN statement
# --------------------------------------------------------------------
if type(categories) == type([]):
    filterCat = ", ".join(["'%s'" % x for x in categories])
elif type(categories) == type('') and categories == 'any':
    filterCat = ''
else:
    filterCat = "'%s'" % categories

# Build the string for the diagnoses to be passed to the IN statement
# --------------------------------------------------------------------
if type(diagnoses) == type([]):
    filterDiag = ", ".join(["%s" % x for x in diagnoses])
elif type(diagnoses) == type('') and diagnoses == 'any':
    filterDiag = ''
else:
    filterDiag = diagnoses

# We need the names for the diagnoses to display on the report.
# -------------------------------------------------------------
textDiag = getDiagnosesNames(filterDiag)

#----------------------------------------------------------------------
# Selections have been made, build the SQL query
# If categories and diagnoses are selected they are combined with AND
#----------------------------------------------------------------------
if filterCat:
    cat_join = """\
  JOIN query_term c
    ON c.doc_id = m.doc_id
   AND c.path = '/Media/MediaContent/Categories/Category'"""
    cat_where = "   AND c.value in (%s)" % filterCat
else:
    cat_join = ''
    cat_where = ''

if filterDiag:
    diag_join = """\
   JOIN query_term d
     ON d.doc_id = m.doc_id
    AND d.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'"""
    diag_where = "   AND d.int_val in (%s)" % filterDiag
else:
    diag_join = ''
    diag_where = ''

# Put all the pieces together for the SELECT statement
# -------------------------------------------------------------
query = """\
SELECT DISTINCT m.doc_id, m.value
  FROM query_term m
%s
%s
 WHERE m.path = '/Media/MediaTitle'
%s
%s
 ORDER BY m.value
""" % (cat_join, diag_join, cat_where, diag_where)

if not query:
    cdrcgi.bail('No query criteria specified')   

# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor.execute(query)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Media documents: %s' %
                info[1][0])
     
if not rows:
    cdrcgi.bail('No Records Found for Selection: (%s) and (%s)' % (
                 str(categories), str(textDiag)))

# Counting the number of summaries per board
# ------------------------------------------
recordCount = len(rows)

# Create the results page.
#----------------------------------------------------------------------
instr     = 'Media List -- %s.' % (dateString)
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
                     font-weight: bold; }
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
report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
  <H3>PDQ Media Documents (%d)<br>
  <span class="date">%s</span>
  </H3>
""" % (cdrcgi.SESSION, session, recordCount, dateString)

report += """\
  <span class="sectionHdr">Category: %s</span><br>
  <span class="sectionHdr">Diagnosis: %s</span>
""" % (filterCat.replace("'", "") or 'All', textDiag or 'All')

# -------------------------------------------------------------------
# Decision if the CDR IDs are displayed along with the Media names
# - The report without CDR ID is displayed as a list.
# - The report with    CDR ID is displayed in a table format.
# -------------------------------------------------------------------
if showId == 'N':
    report += """\
  <DL>
"""
    for row in rows:
        report += summaryRow(row[1])
else:
    report += """\
  <TABLE width = "100%%">
"""

    for row in rows:
        report += summaryRowWithID(row[0], row[1])

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
