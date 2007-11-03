#----------------------------------------------------------------------
#
# $Id: PubStatsByDate.py,v 1.2 2007-11-03 14:15:07 bkline Exp $
#
# Report to list updated document by document type.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2007/01/05 23:27:33  venglisc
# Initial copy of publishing report by date.  (Bug 2111)
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
docTypes  = []
docType   = fields and fields.getvalue("doctype")          or []
submit    = fields and fields.getvalue("SubmitButton")     or None
dateFrom  = fields and fields.getvalue("datefrom")         or ""
dateTo    = fields and fields.getvalue("dateto")           or ""
if not dateFrom:
    dateFrom = time.strftime("%Y-%m-%d")

if not dateTo:
    dateTo = time.strftime("%Y-%m-%d")

request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Publishing Job Statistics by Date"
script    = "PubStatsByDate.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

# Functions to replace sevaral repeated HTML snippets
# ===================================================
def getDocType():
    """Select all published document types"""
    query = """
        SELECT DISTINCT dt.name, d.doc_type
          FROM document d
          JOIN pub_proc_cg cg
            ON cg.id = d.id
          JOIN doc_type dt
            ON d.doc_type = dt.id
         ORDER BY dt.name"""

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving document types: %s' %
                    info[1][0])

    return rows

#----------------------------------------------------------------------
# If the user only picked one document type, put it into a list so we
# can deal with the same data structure whether one or more were
# selected.
#----------------------------------------------------------------------
if type(docType) in (type(""), type(u"")):
    docType = [docType]

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
if not docType:
    header = cdrcgi.header(title, title, instr, script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1)
    form   = """\
   <input type='hidden' name='%s' value='%s'>
   <!-- Table containing the Date -->
   <table border='0' width='35%%'>
    <tr>
     <td colspan='3'>
      %s<br><br>
     </td>
    </tr>
   </table>
 
   <!-- Table to enter the time frame -->
   <table border='0' width='35%%'>
    <tr>
     <td>
      <table border='0' width='100%%'>
       <tr>
        <td><b>Start Date:&nbsp;</b></td>
        <td><input name='datefrom' value='%s' size='10'></td>
       </tr>
       <tr>
        <td><b>End Date:&nbsp;</b></td>
        <td><input name='dateto' value='%s' size='10'></td>
       </tr>
      </table>
     </td>
     <td valign="center" align="left">(format YYYY-MM-DD)</td>
    </tr>
   </table>

   <!-- table to display a horizontal ruler -->
   <table border='0' width='35%%'>
    <tr>
     <td width="320">
      <hr width="50%%"/>
     </td>
    </tr>
   </table>

""" % (cdrcgi.SESSION, session, dateString, dateFrom, dateTo)

    docTypes = getDocType()
    
    html = """<table border='0'>
      <tr>
       <td>
        <input type='checkbox' name='doctype' value='All' CHECKED>
        <b>All Document Types</b><br>
       </td>
      </tr>
      <tr><td>&nbsp;... or ...</td></tr>"""

    for docType in docTypes:
        html += """
              <tr>
               <td>
                <input type='checkbox' name='doctype' value='%s'>
                <b>%s</b>
               </td>
              </tr> """ % (docType[0], docType[0]) 
    html += """
                  </td>
                </tr>
              </table>
  </form>
 </body>
</html>"""
        
    cdrcgi.sendPage(header + form + html)

# If the option 'All' has been selected in addition to individual
# doctypes we're assuming that all doc types should be displayed
# ---------------------------------------------------------------
if docType[0] == 'All':
    docType = ['All']

#----------------------------------------------------------------------
# Creating temporary tables
#----------------------------------------------------------------------
# Create #removed table
# ---------------------
query = """SELECT doc_id, MAX(started) AS started 
  INTO #removed
  FROM pub_proc_doc ppd
  JOIN pub_proc pp
    ON pp.id = ppd.pub_proc
 WHERE started < dateadd(DAY, 1, '%s')
   AND pub_subset like 'Push_%%'
   AND status      = 'Success'
   AND ppd.removed = 'Y'
 GROUP BY doc_id""" % dateTo

try:
    cursor = conn.cursor()
    cursor.execute(query)
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure creating temp table #removed: %s' %
                info[1][0])
     

# Create #brandnew table
# ----------------------
query = """SELECT ppd.doc_id, min(pp.started) AS started
  INTO #brandnew 
  FROM pub_proc_doc ppd
  JOIN pub_proc pp
    ON pp.id = ppd.pub_proc
 WHERE pp.started between '%s' and dateadd(DAY, 1, '%s')
   AND pp.pub_subset LIKE 'Push_%%'
   AND pp.status = 'Success'
   AND NOT EXISTS (SELECT 'x'
                     FROM pub_proc_doc a
                     JOIN pub_proc b
                       ON b.id = a.pub_proc
                    WHERE started < '%s'
                      AND pub_subset LIKE 'Push_%%'
                      AND status = 'Success'
                      AND a.doc_id = ppd.doc_id
                  )
GROUP BY ppd.doc_id
ORDER BY ppd.doc_id""" % (dateFrom, dateTo, dateFrom)

try:
    cursor = conn.cursor()
    cursor.execute(query)
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure creating temp table #brandnew: %s' %
                info[1][0])
     
# Create #phoenix table
# ---------------------
query = """SELECT ppd.doc_id, min(pp.started) as started 
  INTO #phoenix
  FROM pub_proc_doc ppd
  JOIN pub_proc pp
    ON pp.id = ppd.pub_proc
  JOIN #removed r
    ON r.doc_id = ppd.doc_id
 WHERE pp.started > r.started
   AND pub_subset LIKE 'Push_%%'
   AND status = 'Success'
   AND ppd.removed = 'N'
 GROUP BY ppd.doc_id
 ORDER BY ppd.doc_id"""

try:
    cursor = conn.cursor()
    cursor.execute(query)
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure creating temp table #phoenix: %s' %
                info[1][0])
     
# Select count of removed documents
# ---------------------------------
query = """select dt.name, count(*) 
  from #removed r
  JOIN document d
    ON d.id = r.doc_id
  JOIN doc_type dt
    ON d.doc_type = dt.id
 WHERE started between '%s' and dateadd(DAY, 1, '%s')
 GROUP BY dt.name""" % (dateFrom, dateTo)

try:
    cursor = conn.cursor()
    cursor.execute(query)
    removes = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting removed documents: %s' %
                info[1][0])
     
# Select count of brand new documents
# -----------------------------------
query = """select dt.name, count(*) 
  from #brandnew b
  JOIN document d
    ON d.id = b.doc_id
  JOIN doc_type dt
    ON d.doc_type = dt.id
 WHERE started between '%s' and dateadd(DAY, 1, '%s')
 GROUP BY dt.name""" % (dateFrom, dateTo)

try:
    cursor = conn.cursor()
    cursor.execute(query)
    brandnews = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting brand new documents: %s' %
                info[1][0])
     
# Select count of re-published new documents
# ------------------------------------------
query = """SELECT dt.name, count(*) 
  FROM #phoenix p
  JOIN document d
    ON d.id = p.doc_id
  JOIN doc_type dt
    ON d.doc_type = dt.id
 WHERE started between '%s' and dateadd(DAY, 1, '%s')
 GROUP BY dt.name""" % (dateFrom, dateTo)

try:
    cursor = conn.cursor()
    cursor.execute(query)
    renews = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting old new documents: %s' %
                info[1][0])
     
# Select count of updated documents
# ---------------------------------
query = """select dt.name, count(distinct ppd.doc_id) 
  from pub_proc_doc ppd
  join pub_proc pp
    on pp.id = ppd.pub_proc
  join document d
    on d.id = ppd.doc_id
  join doc_type dt
    on d.doc_type = dt.id
 where pp.started between '%s' and dateadd(DAY, 1, '%s')
   AND pub_subset LIKE 'Push_%%'
   AND pp.status = 'Success'
   AND ppd.removed = 'N'
   AND NOT EXISTS (SELECT 'x'
                     FROM #phoenix i
                    WHERE started between '%s' and dateadd(DAY, 1, '%s')
                      AND ppd.doc_id = i.doc_id
                  )
   AND NOT EXISTS (SELECT 'x'
                     FROM #brandnew b
                    WHERE started between '%s' and dateadd(DAY, 1, '%s')
                      AND ppd.doc_id = b.doc_id
                  )
 group by dt.name""" % (dateFrom, dateTo, dateFrom, dateTo, dateFrom, dateTo)

try:
    cursor = conn.cursor()
    cursor.execute(query)
    updates = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting updated documents: %s' %
                info[1][0])
 
# Create a dictionary out of the update list
# (It's easier to select the results later on)
# --------------------------------------------
countUpdate   = {}
countRemove   = {}
countRenew    = {}
countBrandnew = {}

for update in updates:
    countUpdate[update[0]] = update[1]

for remove in removes:
    countRemove[remove[0]] = remove[1]

for brandnew in brandnews:
    countBrandnew[brandnew[0]] = brandnew[1]

for renew in renews:
    countRenew[renew[0]] = renew[1]

#cdrcgi.bail("Result: [%s]" % rows)
#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
instr     = 'Published Documents on Cancer.gov -- %s.' % (dateString)
header    = cdrcgi.header(title, title, instr, script, buttons, 
                          stylesheet = """\
   <STYLE type="text/css">
    H5            { font-weight: bold;
	                font-family: Arial;
                    font-size: 13pt; 
	                margin: 0pt; }
    TD.header     { font-weight: bold; 
                    align: center; }
    TR.odd        { background-color: #F7F7F7; }
    TR.even       { background-color: #FFFFFF; }
    TR.head       { background-color: #E2E2E2; }
   </STYLE>
""")

# -------------------------
# Display the Report Title
# -------------------------
report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
""" % (cdrcgi.SESSION, session)

# -------------------------------------------------------------------
# Decision if the CDR IDs are displayed along with the summary titles
# - The report without CDR ID is displayed as a bulleted list.
# - The report with    CDR ID is displayed in a table format.
# -------------------------------------------------------------------
# ------------------------------------------------------------------------
# Display Summary Title including CDR ID
# ------------------------------------------------------------------------
report += """\
  <center>
    <H3>Published Documents</H3>
     Report includes publishing jobs started between <br/>
     <b>%s</b> and <b>%s</b> <br/>
     <br/>
  </center>
""" % (dateFrom, dateTo)

# Display the header row
# ----------------------
report += """
   <table width="50%%" align="center" border="0">
    <tr class="head">
     <td class="header" align="center" width="25%%">Doc Type</td>
     <td class="header" align="center" width="15%%">Added-Old</td>
     <td class="header" align="center" width="15%%">Added-New</td>
     <td class="header" align="center" width="15%%">Updated</td>
     <td class="header" align="center" width="15%%">Removed</td>
     <td class="header" align="center" width="15%%">Total</td>
    </tr>"""


# Selecting the document types to be displayed
# User can select to display all document types or select individual
# document types by selecting a check box.
# ------------------------------------------------------------------
if docType[0] == 'All':
    allDocTypes = getDocType()
    for type in allDocTypes:
        docTypes.append(type[0])
else:
    docTypes = docType

# Display the columns of the display table
# (Creating a column should probably be handled in a function)
# ------------------------------------------------------------
count = 0
for docType in docTypes:
    total = 0
    count += 1

    # Display first column (list of document types selected)
    # ------------------------------------------------------
    if count % 2 == 0:
        report += """
    <tr class="even">"""
    else:
        report += """
    <tr class="odd">"""
    report += """
     <td><b>%s</b></td>""" % docType

    # Display second column (documents added again after being deleted)
    # -----------------------------------------------------------------
    if countRenew.has_key(docType):
        total += countRenew[docType]
        report += """
     <td align="right">
      <b>%s</b>
     </td>""" % countRenew[docType]
    else:
        report += """
     <td align="right">0</td>"""

    # Display third column (documents being added for the first time)
    # ---------------------------------------------------------------
    if countBrandnew.has_key(docType):
        total += countBrandnew[docType]
        report += """
     <td align="right">
      <b>%s<b/>
     </td>""" % countBrandnew[docType]
    else:
        report += """
     <td align="right">0</td>"""

    # Display fourth column (updated documents)
    # -----------------------------------------
    if countUpdate.has_key(docType):
        total += countUpdate[docType]
        report += """
     <td align="right">
      <b>%s</b>
     </td>""" % countUpdate[docType]
    else:
        report += """
     <td align="right">0</td>"""

    # Display fifth column (documents being deleted)
    # ----------------------------------------------
    if countRemove.has_key(docType):
        total += countRemove[docType]
        report += """
     <td align="right">
      <b>%s</b>
     </td>""" % countRemove[docType]
    else:
        report += """
     <td align="right">0</td>"""

    # Display total column (a total of all previous columns)
    # ------------------------------------------------------
    if total:
        report += """
     <td align="right">
      <b>%s</b>
     </td>""" % total
    else:
        report += """
     <td align="right">
      <b>0</b>
     </td>"""

    report += """
    </tr>"""

report += """
   </table>"""

footer = """\
 </BODY>
</HTML> 
"""     

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + report + footer)
