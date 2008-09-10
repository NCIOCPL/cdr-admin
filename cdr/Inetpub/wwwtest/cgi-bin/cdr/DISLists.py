#----------------------------------------------------------------------
#
# $Id: DISLists.py,v 1.1 2008-09-10 17:30:49 venglisc Exp $
#
# Report on lists of drug information summaries.
#
# $Log: not supported by cvs2svn $
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
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = 'Drug Info Summaries List -- %s.'
script    = "DISLists.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)


# ---------------------------------------------------
# Functions to replace sevaral repeated HTML snippets
# ---------------------------------------------------
def drugHeader(listHeader, type):
    """Return the HTML code to display the Summary Board Header"""
    html = """\
  <SPAN class="sectionHdr">%s (%d)</SPAN>
""" % (listHeader, combiCount[type])
    return html


# ---------------------------------------------------
# 
# ---------------------------------------------------
def drugHeaderWithID(listHeader, type):
    """Return the HTML code to display the Summary Board Header with ID"""
    html = """\
  <SPAN class="sectionHdr">%s (%d)</SPAN>
""" % (listHeader, combiCount[type])
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
    form   = """\
   <input type='hidden' name='%s' value='%s'>
 
   <!-- fieldset>
    <legend>&nbsp;Select Summary Audience&nbsp;</legend>
    <input name='audience' type='radio' id="byHp"
           value='Health Professional'>
    <label for="byHp">Health Professional</label>
    <br>
    <input name='audience' type='radio' id="byPat"
           value='Patient' CHECKED>
    <label for="byPat">Patient</label>
   </fieldset -->
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
    # cdrcgi.bail('No Records Found for Selection: %s ' % drugType   + "; "
    #                                                     + audience + "; ")

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
report    = """\
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
# Display data without CDR ID
# ------------------------------------------------------------------------
singleHdDone = combiHdDone = False
singleReport = combiReport = ''
singleAll    = combiAll    = ''

if showId == 'N':
    for row in rows:
        # Display the Single Drug section
        # ----------------------------------------------------------
        if row[4] != 'Yes' and (drugType == 'All' or drugType == 'Single'):
            if not singleHdDone:
                singleHdDone = True
                singleHeader = drugHeader('Single Agent Drug', 'Single')

            singleReport += summaryRow(row[1])

        # Display the Combination Drug section
        # -------------------------------------------------------------
        elif row[4] == 'Yes' and (drugType == 'All' or drugType == 'Combi'):
            if not combiHdDone:
                combiHdDone = True
                combiHeader = drugHeader('Combination Drug', 'Combi')

            combiReport += summaryRow(row[1])

    # Put the two sections together
    # This if-block is necessary in order to create a valid HTML document
    # -------------------------------------------------------------------
    if drugType in ('All', 'Single'):
        singleAll = singleHeader + """
  <UL>
"""               + singleReport + """\
  </UL>
"""
    if drugType in ('All', 'Combi'):
        combiAll = combiHeader + """
  <UL>
"""               + combiReport + """\
  </UL>
"""

# ------------------------------------------------------------------------
# Display data including CDR ID
# ------------------------------------------------------------------------
else:
    for row in rows:
        # If we encounter a new board_type we need to create a new
        # heading
        # ----------------------------------------------------------
        if row[4] != 'Yes' and (drugType == 'All' or drugType == 'Single'):
            if not singleHdDone:
                singleHdDone = True
                singleHeader = drugHeaderWithID('Single Agent Drug', 'Single')

            singleReport += summaryRowWithID(row[0], row[1])

        # Display the Combination Drug section
        # -------------------------------------------------------------
        elif row[4] == 'Yes' and (drugType == 'All' or drugType == 'Combi'):
            if not combiHdDone:
                combiHdDone = True
                combiHeader = drugHeaderWithID('Combination Drug', 'Combi')

            combiReport += summaryRowWithID(row[0], row[1])

    # Put the two sections together
    # This if-block is necessary in order to create a valid HTML document
    # -------------------------------------------------------------------
    if drugType in ('All', 'Single'):
        singleAll = singleHeader + """
  <TABLE width = "100%">
"""               + singleReport + """\
  </TABLE>
"""
    if drugType in ('All', 'Combi'):
        combiAll = combiHeader + """
  <TABLE width = "100%">
"""               + combiReport + """\
  </TABLE>
"""

report += singleAll + combiAll

footer = """\
 </BODY>
</HTML> 
"""     

# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + report + footer)
