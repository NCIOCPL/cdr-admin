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
audience  = 'Patients'  # Leaving audience here for future use
markUp    = fields and fields.getvalue("markUp")           or None
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Drug Summaries with Markup"
script    = "DISWithMarkup.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

if type(markUp) == type(""):
    markUp = [markUp]

# ---------------------------------------------------
# 
# ---------------------------------------------------
def reportHeader(disTitle = 'Drug Information Summary Markup'):
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
   </tr>
""" % (disTitle)
    return html


# -------------------------------------------------
# Create the table row for the English table output
# -------------------------------------------------
def summaryRow(id, summary, markupCount, display):
    """Return the HTML code to display a Summary row with ID"""

    # The users only want to display those summaries that do have
    # markup, so we need to suppress the once that don't by counting
    # the number of markup elements.
    # --------------------------------------------------------------
    #cdrcgi.bail(display)
    num = 0
    for list in display:
        num += markupCount[list]

    if num == 0: return ""

    # Create the table row display
    # If a markup type hasn't been checked the table cell will be
    # displayed with the class="nodisplay" style otherwise the 
    # count of the markup type is being displayed.
    # ------------------------------------------------------
    html = """\
   <TR>
    <TD class="report cdrid" width = "7%%">
     <a href="/cgi-bin/cdr/QcReport.py?DocId=CDR%s&Session=guest">%s</a>
    </TD>
    <TD class="report">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
    <TD class="%s" width="7%%">%s</TD>
   </TR>
""" % (id, id, summary, 
           'publish' in display and 'display' or 'nodisplay',
           ('publish' not in display or markupCount['publish']  == 0) 
                           and '&nbsp;' or markupCount['publish'], 
           'approved' in display and 'display' or 'nodisplay',
           ('approved' not in display or markupCount['approved'] == 0) 
                           and '&nbsp;' or markupCount['approved'],
           'proposed' in display and 'display' or 'nodisplay',
           ('proposed' not in display or markupCount['proposed'] == 0) 
                           and '&nbsp;' or markupCount['proposed'], 
           'rejected' in display and 'display' or 'nodisplay',
           ('rejected' not in display or markupCount['rejected'] == 0) 
                           and '&nbsp;' or markupCount['rejected'])
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

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not markUp:
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
    <legend>&nbsp;Type of mark-up to Include&nbsp;</legend>
    <input name='markUp' type='checkbox' id="pub"
           value='publish' CHECKED>
    <label for="pub">Publish</label>
    <br>
    <input name='markUp' type='checkbox' id="app"
           value='approved' CHECKED>
    <label for="app">Approved</label>
    <br>
    <input name='markUp' type='checkbox' id="pro"
           value='proposed' CHECKED>
    <label for="pro">Proposed</label>
    <br>
    <input name='markUp' type='checkbox' id="rej"
           value='rejected' CHECKED>
    <label for="rej">Rejected</label>
    <br>
   </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

# Setup the SQL query to be submitted to select all DIS
# -----------------------------------------------------
query = """\
        SELECT DISTINCT qt.doc_id, t.value DocTitle
          FROM query_term qt
          JOIN query_term t
            ON qt.doc_id = t.doc_id
          JOIN query_term a
            ON qt.doc_id = a.doc_id
         WHERE t.path  = '/DrugInformationSummary/Title'
           AND a.path = '/DrugInformationSummary' +
                        '/DrugInfoMetaData'       +
                        '/Audience'
           AND a.value = 'Patients'
         ORDER BY t.value
"""

if not query:
    cdrcgi.bail('No query criteria specified')   

# Submit the query to the database.
#----------------------------------
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
    cdrcgi.bail('No Records Found for Selection: %s ' % audience+"; ")

# Counting the number of drug info summaries
# ------------------------------------------
markupCount = {}
for dis in rows:
    doc = cdr.getDoc('guest', dis[0], getObject = 1)

    #if doc.xml.startswith("<Errors"):
    #    continue
    
    dom = xml.dom.minidom.parseString(doc.xml)
    markupCount[dis[0]] = {'publish':0, 
                            'approved':0,
                            'proposed':0,
                            'rejected':0}
    
    insertionElements = dom.getElementsByTagName('Insertion')  
    for obj in insertionElements:
        markupCount[dis[0]][obj.getAttribute('RevisionLevel')] += 1

    deletionElements  = dom.getElementsByTagName('Deletion')
    for obj in deletionElements:
        markupCount[dis[0]][obj.getAttribute('RevisionLevel')] += 1

#cdrcgi.bail(dis)


# Create the results page.
#----------------------------------------------------------------------
instr     = 'Summaries List -- %s.' % (dateString)
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
report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
  <H3>PDQ Drug Information Summaries - %s<br>
  <span class="date">(%s)</span>
  </H3>
""" % (cdrcgi.SESSION, session, audience, dateString)

dis_hdr = 'Count of Revision Level Markup'
report += reportHeader(dis_hdr)

# Create the HTML snippet for each row
# ------------------------------------
for row in rows:
    report += summaryRow(row[0], row[1], markupCount[row[0]], markUp)

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
