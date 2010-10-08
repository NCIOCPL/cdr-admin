#--------------------------------------------------------------
# Report information to a user about documents for which the CWD
# was replaced with an earlier version.
#
# Filters and displays information from the CWDReplacements.log file
# created by ReplaceCWDwithVersion.py
#
#--------------------------------------------------------------
import time, cgi, cdr, cdrcgi, cdrdb

TITLE    = "Report CWD Replacements"
SCRIPT   = "ReplaceCWDReport.py"
SRC_FILE = "%s/%s" % (cdr.DEFAULT_LOGDIR, "CWDReplacements.log")

# Parse form variables
fields = cgi.FieldStorage()
if not fields:
    cdrcgi.bail("Unable to load form fields - should not happen!")

# Establish user session and authorization
# No special authorization required, it's just a report
session = cdrcgi.getSession(fields)
if not session:
    cdrcgi.bail("Unknown or expired CDR session.")

# Load fields from form
firstDate = fields.getvalue("firstDate", None)
userId    = fields.getvalue("userId", None)
docType   = fields.getvalue("docType", None)
docId     = fields.getvalue("docId", None)
action    = cdrcgi.getRequest(fields)

# Normalize case for later comparisons
if userId:  userId  = userId.lower()
if docType: docType = docType.lower()

# Navigate away?
if action and action == "Admin Menu":
    cdrcgi.navigateTo ("Admin.py", session)

# Has user seen the form yet?
if fields.getvalue("formSeen", None) is None:

    buttons = ('Submit', 'Admin Menu')
    html = cdrcgi.header(TITLE, TITLE, "Enter report parameters",
                         script=SCRIPT, buttons=buttons, stylesheet="""
""")

    html += """
<h2>Enter report parameters</h2>
<p>Retrieve information on documents for which someone has replaced
the current working document (CWD) with an older version.</p>
<p>Fill in the form to select only those replacements meeting the criteria
given in the parameter values.  All parameters are optional.  If all are
blank, all replacements will be reported for which we have logged
information.</p>

<p>Click "Submit" when done.</p>

<table border='0'>
<tr>
  <td align='right'>Earliest date to examine (YYYY-MM-DD): </td>
  <td><input type='text' name='firstDate' size='10' /></td>
</tr>
<tr>
  <td align='right'>User id of person replacing documents: </td>
  <td><input type='text' name='userId' size='10' /></td>
</tr>
<tr>
  <td align='right'>Document type replaced: </td>
  <td><input type='text' name='docType' size='30' /></td>
</tr>
<tr>
  <td align='right'>CDR ID (to only see one document: </td>
  <td><input type='text' name='docId' size='20' /></td>
</tr>
</table>

<input type='hidden' name='formSeen' value='True'>
<input type='hidden' name='%s' value='%s'>
</form>
</body>
</html>""" % (cdrcgi.SESSION, session)

    cdrcgi.sendPage(html)


# If we got here, the user has already seen and submitted the form

if firstDate:
    # Validate format
    okay = True
    try:
        year  = int(firstDate[0:4])
        month = int(firstDate[5:7])
        day   = int(firstDate[8:10])
    except ValueError:
        okay = False
    else:
        if (year < 2000 or year > 2100 or
            month < 1 or month > 12 or
            day < 1 or day > 31):
           okay = False
    if not okay:
        cdrcgi.bail("Y=%d  M=%d  D=%d" % (year, month, day))
        cdrcgi.bail("Please enter date in YYYY-MM-DD format, e.g., 2010-10-01")

if docId:
    # Validate doc ID format
    try:
        result = cdr.exNormalize(docId.upper())
    except cdr.Exception, info:
        cdrcgi.bail('Doc ID "%s" is not a recognized CDR ID format' % docId)
    else:
        docId = str(result[1])

# Construct page and report headers
buttons = ('New Report', 'Admin Menu')
prolog = cdrcgi.header(TITLE, TITLE, "Enter report parameters",
                     script=SCRIPT, buttons=buttons, stylesheet="""
  <style type='text/css'>
   P  { text-indent: 3em; font-size: 120% }
   TABLE.legend TH { text-indent: 3em; font-size: 100%; text-align: right }
   TABLE.data   TH { font-size: 100%; text-align: center }
  </style>
""")

prolog += """
<p>Column header abbreviations:</p>
<table class='legend' border='0'>
<tr>
  <th>Date/time: </th><td>YYYY-MM-DD HH:MM:SS of CWD replacement</td>
</tr>
<tr>
  <th>DocID: </th><td>Affected document</td>
</tr>
<tr>
  <th>DocType: </th><td>Document type of document</td>
</tr>
<tr>
  <th>User: </th><td>Short user ID of person promoting the version</td>
</tr>
<tr>
  <th>LV: </th><td>Version number of last version at time of promotion</td>
</tr>
<tr>
  <th>PV: </th><td>Version number of last publishable version at that time, -1 = None</td>
</tr>
<tr>
  <th>Chg: </th><td>'Y' = CWD was different from last version, else 'N'</td>
</tr>
<tr>
  <th>V#: </th><td>Version number promoted to become CWD</td>
</tr>
<tr>
  <th>V: </th><td>New CWD was also versioned</td>
</tr>
<tr>
  <th>P: </th><td>New CWD was also versioned as publishable</td>
</tr>
<tr>
  <th>Comment: </th><td>System generated comment ':' user entered comment</td>
</tr>

<table class='data' border='1'>
<tr>
  <th>Date/time</th>
  <th>DocID</th>
  <th>Doc type</th>
  <th>User</th>
  <th>LV</th>
  <th>PV</th>
  <th>Chg</th>
  <th>V#</th>
  <th>V</th>
  <th>P</th>
  <th>Comment</th>
</tr>
<br />
"""


# Open the file
try:
    fp = open(SRC_FILE, "r")
except IOError, info:
    cdrcgi.bail("Unable to open log file: %s" % info)

reportRows = []
errMsg     = ""
while True:
    # Read each line
    line = fp.readline()
    if not line:
        break

    # Skip lines prior to our first date
    if firstDate and line[0:10] < firstDate:
        continue
    # cdrcgi.bail("firstDate=%s,  firstDate[0:10]=%s" % (firstDate,
    #            firstDate[0:10]))

    # Parse on tabs
    data = line.split('\t')

    # This is a text file, it could get corrupted, ignore corrupt lines
    if len(data) != 11:
        errMsg = "Note: One or more lines of the log file have invalid data." \
                 " Please inform system staff."
        continue

    # Filters
    if docId and data[1] != docId:
        continue
    if docType and data[2].lower() != docType:
        continue
    if userId and data[3].lower() != userId:
        continue

    # Format
    row = "<tr> "
    for item in data:
        row += "<td>%s</td> " % item
    row += " </tr>\n"
    reportRows.append(row)

# End stuff
suffix = """
</table>
<p>Number of replacements in report: %d.</p>
<p>%s</p>
<input type='hidden' name='%s' value='%s'>
</form>
</body>
</html>
""" % (len(reportRows), errMsg, cdrcgi.SESSION, session)

# Assemble the full report
html = prolog + "".join(reportRows) + suffix

# Display
cdrcgi.sendPage(html)
