#----------------------------------------------------------------------
#
# $Id$
#
# Report to list updated document by document type.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2008/02/08 21:51:10  venglisc
# Inintial copy of report listing documents (and protocols) published
# in the latest export job. (Bug 3812)
#
# Revision 1.1  2007/01/05 23:27:33  venglisc
# Initial copy of publishing report by date.  (Bug 2111)
#
#
# BZIssue::5237: Report for publication document counts fails on 
#                non-production server
#
#----------------------------------------------------------------------
#import xml.dom.minidom
import cgi, cdr, cdrcgi, re, string, cdrdb, time, sys
import lxml.etree as etree

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
OUTPUTBASE= cdr.BASEDIR + "/Output"

fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
docTypes  = []
submit    = fields and fields.getvalue("SubmitButton")     or None
dateFrom  = fields and fields.getvalue("datefrom")         or ""
dateTo    = fields and fields.getvalue("dateto")           or ""
if not dateFrom:
    dateFrom = time.strftime("%Y-%m-%d")

if not dateTo:
    dateTo = time.strftime("%Y-%m-%d")

t0 = time.time()

request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Publishing Job Statistics by Date"
script    = "PubStatsByDate.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

protQuery = """
    SELECT doc_id, doc_version 
      FROM pub_proc_doc ppd
      JOIN active_doc d
        ON d.id = ppd.doc_id
      JOIN doc_type dt
        ON d.doc_type = dt.id
     WHERE pub_proc = %s
       AND dt.name = '%s'
"""

# -------------------------------------------------------------------
# Retrieve the XML from the database
# Returns the protocol object
# -------------------------------------------------------------------
def getProtocol(docId, num, cursor):
    query = """
        SELECT xml 
          FROM doc_version 
         WHERE id = %s
           AND num = %s 
""" % (docId, num)

    try:
        cursor.execute(query)
        row = cursor.fetchone()

    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving XML: %s' % info[1][0])

    return etree.XML(row[0].encode('utf-8'))


# -------------------------------------------------------------------
# Count the InScopeProtocols by status
# This version retrieves the documents from the database
# -------------------------------------------------------------------
def getInScopeCount(jobID = 4867):
    """
    Function to collect the InScopeProtocols from the last
    export job (given by the JobID) and counting the number
    of documents per CurrentStatus.
    """
    query = protQuery % (jobID, 'InScopeProtocol')

    try:
        # Selecting all protocol documents
        # --------------------------------
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        inScopeCount = {}

        # Inspecting and counting by status value
        # ---------------------------------------
        for (docID, version) in rows:
            xml = getProtocol(docID, version, cursor)
            curStatus = xml.find('./ProtocolAdminInfo/CurrentProtocolStatus')
            status = curStatus.text

            if inScopeCount.has_key(status):
                inScopeCount[status] += 1
            else:
                inScopeCount[status]  = 1

    except Exception as e:
        cdrcgi.bail("Error collecting InScope filenames: %s" % e)

    return(inScopeCount)

# -------------------------------------------------------------------
# Count the CTGovProtocols by status
# This version retrieves the documents from the database
# -------------------------------------------------------------------
def getCTGovCount(jobID = 4867):
    """
    Function to collect the CTGovProtocols from the last
    export job (given by the JobID) and counting the number
    of documents per CurrentStatus.
    """
    query = protQuery % (jobID, 'CTGovProtocol')

    try:
        # Selecting all protocol documents
        # --------------------------------
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        ctgovCount = {}

        # Inspecting and counting by status value
        # ---------------------------------------
        for (docID, version) in rows:
            xml = getProtocol(docID, version, cursor)
            curStatus = xml.find('./OverallStatus')

            if curStatus is not None:
                status = curStatus.text

            if ctgovCount.has_key(status):
                ctgovCount[status] += 1
            else:
                ctgovCount[status]  = 1

    except Exception as e:
        cdrcgi.bail("Error collecting CTGov filenames: %s" % e)
    
    return(ctgovCount)


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
# Select the Job ID of the last Export job
# ----------------------------------------
query = """SELECT MAX(id) 
             FROM pub_proc 
            WHERE pub_system = 178
              AND pub_subset = 'Export'
              AND status = 'Success'"""
try:
    cursor = conn.cursor()
    cursor.execute(query)
    jobID = cursor.fetchone()

    jobID = [9768]
    print jobID

    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting last Export JobId: %s' % info[1][0])
     
t1 = time.time() - t0
print "Get Export job: %s sec" % t1

# Counting the documents by document type
# ---------------------------------------
query = """select dt.name, count(*)
             from pub_proc_doc ppd
             join document d
               on d.id = ppd.doc_id
             join doc_type dt
               on dt.id = d.doc_type
            where pub_proc = %s
              and failure is null
            group by dt.name
            order by dt.name""" % (jobID[0])
try:
    cursor = conn.cursor()
    cursor.execute(query)
    docTypesCount = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting published document count: %s' %
                info[1][0])
     
t2 = time.time() - t0
print "Count Doc type: %s sec" % (t2 - t1)

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
    TR.head       { background-color: #B2B2B2; }
    *.center      { text-align: center; }
    *.footer      { font-size: 11pt;
                    background-color: #B2B2B2; 
                    font-weight: bold; 
                    border-top: 2px solid black; 
                    border-bottom: 2px solid black; }
   </STYLE>
""")

# -------------------------
# Display the Report Title
# -------------------------
report    = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
""" % (cdrcgi.SESSION, session)

report += u"""\
  <div class="center">
    <H3>Published Documents</H3>
     <b>Documents Listed from Last Weekly Export: Job%s</b>
     <br>
     <br>
  </div>
""" % jobID[0]

# Display the header row of the first table
# ------------------------------------------
report += u"""
   <table width="25%" align="center" border="0">
    <tr class="head">
     <td class="header" align="center" width="70%">Doc Type</td>
     <td class="header" align="center" width="30%">Count</td>
    </tr>"""

# Displaying the records for the document type counts
# ------------------------------------------------------------
count = 0
total = 0
for docTypeCount in docTypesCount:
    total += docTypeCount[1]
    count += 1

    # Display the rows with different background color
    # ------------------------------------------------
    if count % 2 == 0:
        report += u"""
    <tr class="even">"""
    else:
        report += u"""
    <tr class="odd">"""
    report += u"""
     <td><b>%s</b></td>
     <td><b>%s</b></td>""" % (docTypeCount[0], docTypeCount[1])

    report += u"""
    </tr>"""

report += u"""
    <tr class="footer">
     <td class="footer">Total</td>
     <td class="footer">%s</td>
    </tr>
   </table>""" % total

# List an additional table for the breakdown of InScopeProtocols 
# by status
# -----------------------------------------------------------------
inScopeCount = getInScopeCount(jobID[0])
t3 = time.time() - t0
print "Count InScope: %s sec" % (t3 - t2)

inScopeKeys = inScopeCount.keys()
inScopeKeys.sort()
#print ""

report += u"""
   <div class="center">
    <br>
     <b>InScopeProtocol by Status</b>
    <br>
   </div>
   <table width="35%" align="center" border="0">
    <tr class="head">
     <td class="header" align="center" width="50%">Status</td>
     <td class="header" align="center" width="20%">Count</td>
    </tr>"""

# We want to display a summary line of total active/closed protocols
# ------------------------------------------------------------------
scount = 0
acount = 0
ccount = 0

for status in inScopeKeys:
    # Counting total of active and closed protocols
    # ------------------------------------------------------
    if status in ('Active', 'Approved-not yet active'):
        acount += inScopeCount[status]
    else:
        ccount += inScopeCount[status]

    # Display the records for the status values
    # -----------------------------------------
    scount += 1
    if scount % 2 == 0:
        report += u"""
    <tr class="even">"""
    else:
        report += u"""
    <tr class="odd">"""
    report += u"""
     <td><b>%s</b></td>
     <td><b>%s</b></td>""" % (status, inScopeCount[status])

    report += u"""
    </tr>"""

# Display the summary for active/closed protocols
# -----------------------------------------------
report += u"""
    <tr class="footer">
     <td class="footer">Total-active</td>
     <td class="footer">%s</td>
    </tr>
    <tr class="footer">
     <td class="footer">Total-closed</td>
     <td class="footer">%s</td>
    </tr>
   </table>""" % (acount, ccount)

# Repeat the same for the CTGovProtocols
# --------------------------------------
ctgovCount = getCTGovCount(jobID[0])
t4 = time.time() - t0
print "Count CTGov: %s sec" % (t4 - t3)

ctgovKeys = ctgovCount.keys()
ctgovKeys.sort()

report += u"""
   <div class="center">
    <br>
     <b>CTGovProtocol by Status</b>
    <br>
   </div>
   <table width="35%" align="center" border="0">
    <tr class="head">
     <td class="header" align="center" width="50%">Status</td>
     <td class="header" align="center" width="20%">Count</td>
    </tr>"""

# We want to display a summary line of total active/closed protocols
# ------------------------------------------------------------------
scount = 0
acount = 0
ccount = 0

for status in ctgovKeys:
    # Counting total of active and closed CTGovProtocols
    # --------------------------------------------------
    if status in ('Active', 'Approved-not yet active'):
         acount += ctgovCount[status]
    else:
         ccount += ctgovCount[status]

    # Display the records for the status values
    # -----------------------------------------
    scount += 1
    if scount % 2 == 0:
        report += u"""
    <tr class="even">"""
    else:
        report += u"""
    <tr class="odd">"""
    report += u"""
     <td><b>%s</b></td>
     <td><b>%s</b></td>""" % (status, ctgovCount[status])

    report += u"""
    </tr>"""


# Display the summary for active/closed protocols
# -----------------------------------------------
report += """
    <tr class="footer">
     <td class="footer">Total-active</td>
     <td class="footer">%s</td>
    </tr>
    <tr class="footer">
     <td class="footer">Total-closed</td>
     <td class="footer">%s</td>
    </tr>
   </table>""" % (acount, ccount)

footer = u"""\
 </BODY>
</HTML> 
"""     

sys.exit(1)
#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(cdrcgi.unicodeToLatin1(header + report + footer))
