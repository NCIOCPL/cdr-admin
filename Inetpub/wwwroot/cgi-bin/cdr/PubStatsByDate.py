#----------------------------------------------------------------------
#
# $Id$
#
# Report to list updated document count by document type.
#
# Added an option to the script (VOL=Y) to allow to pull out the 
# media documents and create a list suitable for Visuals Online to be
# updated.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2007/11/03 14:15:07  bkline
# Unicode encoding cleanup (issue #3716).
#
# Revision 1.1  2007/01/05 23:27:33  venglisc
# Initial copy of publishing report by date.  (Bug 2111)
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
vol       = fields and fields.getvalue("VOL")              or ""

# Setting the dates to prepopulate Start/End Date fields
# ------------------------------------------------------
now       = time.localtime(time.time())
then      = list(now)
then[2]  -= 7
then      = time.localtime(time.mktime(then))

if not dateFrom:
    dateFrom = time.strftime("%Y-%m-%d", then)

if not dateTo:
    dateTo   = time.strftime("%Y-%m-%d", now)

request   = cdrcgi.getRequest(fields)

title     = "CDR Administration"

if not vol:
    instr = "Publishing Job Statistics by Date"
else:
    instr = "Media Doc Publishing Report"

script    = "PubStatsByDate.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

# ---------------------------------------------------
# Function to get the document types from the CDR
# ---------------------------------------------------
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

# ------------------------------------------------------------------
# Function to get the Media information to be displayed in the table
# from the CDR
# We're selecting the information for the latest version of the doc.
# ------------------------------------------------------------------
def getMediaInfo(ids):
    if not ids:
        return []

    query = """
         SELECT m.doc_id, m.value, d.first_pub, dv.dt, dv.updated_dt, v.value,
                dv.num, dv.publishable
           FROM query_term m
LEFT OUTER JOIN query_term v
             ON m.doc_id = v.doc_id
            AND v.path = '/Media/@BlockedFromVOL'
           JOIN doc_version dv
             ON m.doc_id = dv.id
           JOIN document d
             ON dv.id = d.id
          WHERE m.path = '/Media/MediaTitle'
            AND m.doc_id in (%s)
            AND dv.num = (
                          SELECT max(num)
                            FROM doc_version x
                           WHERE x.id = dv.id
                         )
          ORDER BY m.value
""" % ', '.join(["%s" % x for x in ids])

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving Media info: %s' %
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

# ***** First Pass *****
#----------------------------------------------------------------------
# If we don't have a request, put up the form.
# For the Media Doc report, however, we only need the Start/End date
# fields to put up.
#----------------------------------------------------------------------
if not docType:
    header = cdrcgi.header(title, title, instr, script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1,
                           stylesheet = """
   <script language='JavaScript' type='text/javascript'>
       function clearAll() {
           document.getElementById('all').checked = false;
       }
       function clearOthers(widget, n) {
           for (var i = 1; i<=n; ++i)
               document.getElementById('D' + i).checked = false;
       }
   </script>
""")
    form   = """\
   <input type='hidden' name='%s' value='%s'>
   <!-- Table containing the Date -->
   <table border='0' width='25%%'>
    <tr>
     <td colspan='3'>
      %s<br><br>
     </td>
    </tr>
   </table>
 
   <!-- Table to enter the time frame -->
   <table border='0' >
    <tr>
     <td>
      <table border='0'cellpadding="3">
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
     <td valign="middle" align="left">(format YYYY-MM-DD)</td>
    </tr>
   </table>

   <!-- table to display a horizontal ruler -->
   <table border='0' width='25%%'>
    <tr>
     <td width="320">
      <hr width="50%%">
     </td>
    </tr>
   </table>
""" % (cdrcgi.SESSION, session, dateString, dateFrom, dateTo)

    # For the Media Doc report the default docType is 'Media'
    # -------------------------------------------------------
    if vol:
        html = """
   <input type='hidden' name='doctype' value='Media'>
   <input type='hidden' name='VOL'     value='Y'>"""
    # For the Pub Job Statistic report we need to select the docType
    # --------------------------------------------------------------
    else:
        docTypes = getDocType()
    
        html = """
   <table border='0'>
    <tr>
     <td>
      <input type='checkbox' name='doctype' value='All' CHECKED
             onclick="javascript:clearOthers(this, %d)" id="all">
      <b>All Document Types</b><br>
     </td>
    </tr>
    <tr>
     <td>&nbsp;... or ...</td>
    </tr>""" % (len(docTypes))

        i = 0
        for docType in docTypes:
            i += 1
            html += """
    <tr>
     <td>
      <input type='checkbox' name='doctype' value='%s'
             onclick="javascript:clearAll()" id=D%d>
      <b>%s</b>
     </td>
    </tr>""" % (docType[0], i, docType[0]) 
        html += """
   </table>"""

    html += """
  </form>
 </body>
</html>"""
        
    cdrcgi.sendPage(header + form + html)

# ***** Second Pass *****
# If the option 'All' has been selected in addition to individual
# doctypes we're assuming that all doc types should be displayed
# ---------------------------------------------------------------
if docType[0] == 'All':
    docType = ['All']

#----------------------------------------------------------------------
# Creating temporary tables
# The SQL queries for both reports Media Doc and Job Statistics are 
# slightly different, in the first we're selecting document IDs in the 
# other one we're selecting counts.
#----------------------------------------------------------------------
if vol:
    q_select = "SELECT rbp.doc_id"
    q_select2= "SELECT DISTINCT ppd.doc_id"
    q_and    = "   AND dt.name = 'Media'"
    q_group  = ""
else:
    q_select = "SELECT dt.name, count(*)"
    q_select2= "SELECT dt.name, count(distinct ppd.doc_id)"
    q_and    = ""
    q_group  = " GROUP BY dt.name"

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
     
# Select information from removed table (count or doc-ID)
# -------------------------------------------------------
query = """\
 %s
  from #removed rbp
  JOIN document d
    ON d.id = rbp.doc_id
  JOIN doc_type dt
    ON d.doc_type = dt.id
 WHERE started between '%s' and dateadd(DAY, 1, '%s')
 %s
 %s""" % (q_select, dateFrom, dateTo, q_and, q_group)

try:
    cursor = conn.cursor()
    cursor.execute(query)
    removes = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting removed documents: %s' %
                info[1][0])
     
# Select information of brandnew table (count or doc_ID)
# ------------------------------------------------------
query = """
%s
  from #brandnew rbp
  JOIN document d
    ON d.id = rbp.doc_id
  JOIN doc_type dt
    ON d.doc_type = dt.id
 WHERE started between '%s' and dateadd(DAY, 1, '%s')
 %s
 %s""" % (q_select, dateFrom, dateTo, q_and, q_group)

try:
    cursor = conn.cursor()
    cursor.execute(query)
    brandnews = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting brand new documents: %s' %
                info[1][0])
     
# Select information of re-published new table (count or doc-id)
# --------------------------------------------------------------
query = """
%s
  FROM #phoenix rbp
  JOIN document d
    ON d.id = rbp.doc_id
  JOIN doc_type dt
    ON d.doc_type = dt.id
 WHERE started between '%s' and dateadd(DAY, 1, '%s')
 %s
 %s""" % (q_select, dateFrom, dateTo, q_and, q_group)

try:
    cursor = conn.cursor()
    cursor.execute(query)
    renews = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting old new documents: %s' %
                info[1][0])
     
# Select information of updated table (count or doc-id)
# -----------------------------------------------------
query = """
%s
  FROM pub_proc_doc ppd
  JOIN pub_proc pp
    ON pp.id = ppd.pub_proc
  JOIN document d
    ON d.id = ppd.doc_id
  JOIN doc_type dt
    ON d.doc_type = dt.id
 WHERE pp.started between '%s' and dateadd(DAY, 1, '%s')
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
 %s
 %s""" % (q_select2, dateFrom, dateTo, dateFrom, dateTo, 
                     dateFrom, dateTo, q_and, q_group)

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

# Collect all doc-ids in one list and get the information for the 
# report for each of the documents from the database
# ---------------------------------------------------------------
if vol:
    mediaIds = []
    for set in (updates, removes, brandnews, renews):
        for x in set:
            mediaIds.append(x[0])

    mediaRecords = getMediaInfo(mediaIds)

# Store the row counts in a dictionary to be accessed later
# ---------------------------------------------------------
else:
    for update in updates:
        countUpdate[update[0]] = update[1]

    for remove in removes:
        countRemove[remove[0]] = remove[1]

    for brandnew in brandnews:
        countBrandnew[brandnew[0]] = brandnew[1]

    for renew in renews:
        countRenew[renew[0]] = renew[1]

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
instr     = 'Published %s Documents on Cancer.gov -- %s.' % (
                                      vol and 'Media' or '', dateString)
header    = cdrcgi.header(title, title, instr, script, buttons, 
                          stylesheet = """\
   <STYLE type="text/css">
    H3            { font-weight: bold;
	                font-family: Arial;
                    font-size: 16pt; 
	                margin: 8pt; }
    TABLE.output  { margin-left: auto;
                    margin-right: auto; }
    TABLE.output  TD
                  { padding: 3px; }
    TD.header     { font-weight: bold; 
                    text-align: center; }
    TR.odd        { background-color: #E7E7E7; }
    TR.even       { background-color: #FFFFFF; }
    TR.head       { background-color: #D2D2D2; }
    .link         { color: blue; 
                    text-decoration: underline; }
   </STYLE>
""")

# -------------------------
# Display the Report Title
# -------------------------
report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
""" % (cdrcgi.SESSION, session)

# ------------------------------------------------------------------------
# Display Summary Title including CDR ID
# ------------------------------------------------------------------------
report += """\
  <center>
    <H3>Published %s Documents</H3>
     Report includes publishing jobs started between<br/>
     <b>%s</b> and <b>%s</b><br/>
     <br/>
  </center>
""" % (vol and 'Media' or '', dateFrom, dateTo)

# ***** Main part for Media Doc Published report *****
# ----------------------------------------------------
if vol:
    report += """
  <table class="output" border="1">
   <tr class="head">
    <td class="header">CDR-ID</td>
    <td class="header">Media Title</td>
    <td class="header">First Pub Date</td>
    <td class="header">Version Date</td>
    <td class="header">Last Version<br/>Publishable</td>
    <td class="header">Blocked from<br/>VOL</td>
   </tr>
"""
    count = 0
    for id, title, first, verDt, audDt, volFlag, ver, \
        publishable in mediaRecords:
        count += 1
        if count % 2 == 0:
            report += '   <tr class="even">'
        else:
            report += '   <tr class="odd">'

        report += """
    <td class="link">
     <a href="/cgi-bin/cdr/GetCdrImage.py?id=CDR%s.jpg">%s</a>
    </td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td align="center">%s</td>
    <td align="center">%s</td>
   </tr>
""" % (id, id, title, first[:10], verDt[:16], publishable, volFlag and volFlag[:1] or "")


    footer = """\
  </table>
 </BODY>
</HTML> 
"""     
    cdrcgi.sendPage(header + report + footer)


# ***** Main section for Job Statistics report display *****
# ----------------------------------------------------------
# Display the header row
# ----------------------
report += """
   <table class="output" width="45%%" border="0">
    <tr class="head">
     <td class="header" width="25%%">Doc Type</td>
     <td class="header" width="15%%">Added-Old</td>
     <td class="header" width="15%%">Added-New</td>
     <td class="header" width="15%%">Updated</td>
     <td class="header" width="15%%">Removed</td>
     <td class="header" width="15%%">Total</td>
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