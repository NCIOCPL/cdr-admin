#----------------------------------------------------------------------
#
# $Id$
#
# Report on lists of drug information summaries.
#
# BZIssue::5198 - Adding a Table Option to Drug Summaries Lists Report
#
# Revision 1.1  2008/09/10 17:30:49  venglisc
# Initial version of DrugInformationSummaries List report (Bug 4250).
#
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, time, cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
# audience  = fields and fields.getvalue("audience")         or "Patient"
drugType  = fields and fields.getvalue("type")             or None
showId    = fields and fields.getvalue("showId")           or "N"
showTable = fields and fields.getvalue("showTable")        or "N"
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = 'Drug Info Summaries List -- %s.'
script    = "DISLists.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)


# -------------------------------------------------
# Create the table row for the English table output
# -------------------------------------------------
def summaryTableRow(id, summary, addCdrID='Y', addBlank='N'):
    """Return the HTML code to display a Summary row with ID"""

    # Start the table row
    # -------------------
    html = """\
   <TR>"""

    # Setting the class and column headers for table display
    # ------------------------------------------------------
    if addBlank == 'Y': 
        showGrid = 'blankCol'
    else:
        showGrid = ''


    # Add an extra cell for the CDR-ID
    # --------------------------------
    if addCdrID == 'Y':
        html += """
    <TD class="report cdrid %s" width="8%%">%s</TD>""" % (showGrid, id)

    # Display the Summary title
    # -------------------------
    html += """
    <TD class="report %s">%s""" % (showGrid, summary)

    # End the summaries cell
    # ----------------------
    html += """
    </TD>"""

    # Add and extra blank column
    # --------------------------
    if addBlank == 'Y':
        html += """
    <TD class="report %s" width="50%%">&nbsp;</TD>""" % showGrid

    # End the table row
    # -----------------
    html += """
   </TR>
"""
    return html



# ---------------------------------------------------
# Functions to replace sevaral repeated HTML snippets
# ---------------------------------------------------
def disHeader(listHeader, disCount):
    """Return the HTML code to display the Summary Board Header"""
    html = u"""\
  <SPAN class="sectionHdr">%s (%d)</SPAN>
  <TABLE width = "100%%">
""" % (listHeader, disCount)
    return html


## ---------------------------------------------------
## 
## ---------------------------------------------------
#def drugHeaderWithID(listHeader, type):
#    """Return the HTML code to display the Summary Board Header with ID"""
#    html = u"""\
#  <SPAN class="sectionHdr">%s (%d)</SPAN>
#""" % (listHeader, combiCount[type])
#    return html
#
#
## ------------------------------------------------
## Create the table row for the English list output
## ------------------------------------------------
#def summaryRow(summary):
#    """Return the HTML code to display a Summary row"""
#    html = u"""\
#   <LI class="report">%s</LI>
#""" % (row[1])
#    return html
#
##
## -------------------------------------------------
## Create the table row for the English table output
## -------------------------------------------------
#def summaryRowWithID(id, summary):
#    """Return the HTML code to display a Summary row with ID"""
#    html = u"""\
#   <TR>
#    <TD class="report cdrid" width = "8%%">%s</TD>
#    <TD class="report">%s</TD>
#   </TR>
#""" % (id, summary)
#    return html
#

# =====================================================================
# Main starts here
# =====================================================================
# Handle navigation requests.
#----------------------------
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
instr = instr % dateString

### Testing
#drugType = 'All'
### Testing
#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not drugType:
    header = cdrcgi.header(title, title, instr, 
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
""")
    form   = u"""\
   <input type='hidden' name='%s' value='%s'>
 
   <fieldset>
    <legend>&nbsp;Display CDR-ID?&nbsp;</legend>
    <input name='showId' type='radio' id="idNo"
           value='N'>
    <label for="idNo">Without CDR-ID</label>
    <br>
    <input name='showId' type='radio' id="idYes"
           value='Y' CHECKED>
    <label for="idYes">With CDR-ID</label>
   </fieldset>

   <fieldset>
    <legend>&nbsp;Select Agent Type&nbsp;</legend>
    <input name='type' type='radio' id="single" value='Single'>
    <label for="single">Single Agent</label>
    <br>
    <input name='type' type='radio' id="combi" value='Combi'>
    <label for="combi">Combination</label>
    <br>
    <input name='type' type='radio' id="both" value='All' CHECKED>
    <label for="both">Both</label>
   </fieldset>

   <fieldset>
    <legend>&nbsp;Display in Table Format?&nbsp;</legend>
    <input name='showTable' type='radio' id="tableNo"
           value='N' CHECKED>
    <label for="tableNo">Standard</label>
    <br>
    <input name='showTable' type='radio' id="tableYes"
           value='Y'>
    <label for="tableYes">Table format with blank column</label>
   </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

# Put all the pieces together for the SELECT statement
# -------------------------------------------------------------
query = """\
         SELECT d.id, q.value, active_status, val_status, s.value
           FROM query_term_pub q
           JOIN document d
             ON d.id = q.doc_id
           JOIN doc_type dt
             ON d.doc_type = dt.id
LEFT OUTER JOIN query_term s
             ON s.doc_id = q.doc_id
            AND s.path  = '/DrugInformationSummary/DrugInfoMetaData' +
                          '/DrugInfoType/@Combination'
          WHERE dt.name = 'DrugInformationSummary'
            AND q.path  = '/DrugInformationSummary/Title'
            AND d.active_status = 'A'
          ORDER BY s.value, q.value
"""

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
    cdrcgi.bail('Failure retrieving DIS documents: %s' %
                info[1][0])
     
if not rows:
    cdrcgi.bail('No Records Found for Selection: %s ' % drugType   + "; ")

# Counting the number of summaries per board
# ------------------------------------------
combiCount = {'All'   :len(rows), 
              'Combi' :0, 
              'Single':0}
for row in rows:
    if row[4] == 'Yes':
        combiCount['Combi']  += 1
    else:
        combiCount['Single'] += 1

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
header    = cdrcgi.rptHeader(title, stylesheet = """\
   <STYLE type="text/css">
    UL             { margin-left:    0; 
                     padding-left:   0;
                     margin-top:    10px;
                     margin-bottom: 30px; }
    TABLE          { border-collapse:collapse;
                     margin-top:    10px; 
                     margin-bottom: 30px; } 

    *.date         { font-size: 12pt; }
    *.sectionHdr   { font-size: 12pt;
                     font-weight: bold;
                     text-decoration: underline; }
    *.report       { font-size: 11pt;
                     padding-right: 15px; 
                     vertical-align: top; }
    *.blankCol     { empty-cells: show;
                     border: 1px solid black; }
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
report    = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <H3>Drug Information Summaries<br>
  <span class="date">(%s)</span>
  </H3>
""" % (cdrcgi.SESSION, session, dateString)

# -------------------------------------------------------------------
# Decision if the CDR IDs are displayed along with the summary titles
# - The report without CDR ID is displayed as a none-bulleted list.
# - The report with    CDR ID is displayed in a table format.
# -------------------------------------------------------------------

# ------------------------------------------------------------------------
# Display the data
# ------------------------------------------------------------------------
reportS = disHeader('Single Agent Drug', combiCount['Single'])
reportD = disHeader('Combination Drug', combiCount['Combi'])

if showTable == 'Y': 
    if showId == 'Y':
        showHeader = """\
   <TR>
    <TH class="report blankCol">CDR-ID</TH>
    <TH class="report blankCol">Title</TH>
    <TH class="report blankCol"> </TH>
   </TR>
"""
    else:
        showHeader = """\
   <TR>
    <TH class="report blankCol">Title</TH>
    <TH class="report blankCol"> </TH>
   </TR>
"""
    reportS += showHeader
    reportD += showHeader

# Creating the individual rows
# ----------------------------------------
for row in rows:
    # The rows list all Drug Summary records sorted by DIS/Combo.
    # If only one type needs to be printed then skip the other
    # otherwise we'll need to print a second heading for the second
    # type.
    # ----------------------------------------------------------
    if row[4] != 'Yes':
        reportS += summaryTableRow(row[0], row[1], addCdrID=showId, 
                                   addBlank=showTable)
    if row[4] == 'Yes':
        reportD += summaryTableRow(row[0], row[1], addCdrID=showId, 
                                  addBlank=showTable)
reportS += """
  </TABLE>
"""
reportD += """
  </TABLE>
"""

# Decide which of the two individual reports should be printed
# ------------------------------------------------------------
if drugType == 'All' or drugType == 'Single':
    report += reportS
if drugType == 'All' or drugType == 'Combi':
    report += reportD

footer = u"""\
 </BODY>
</HTML> 
"""     

# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + report + footer)
