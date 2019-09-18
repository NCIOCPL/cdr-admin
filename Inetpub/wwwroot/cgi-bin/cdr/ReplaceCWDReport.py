#--------------------------------------------------------------
# Report information to a user about documents for which the CWD
# was replaced with an earlier version.
#
# Filters and displays information from the CWDReplacements.log file
# created by ReplaceCWDwithVersion.py
#
# JIRA::OCECDR-3800 - Address security vulnerabilities
#--------------------------------------------------------------
import cgi
import cdr
import cdrcgi

TITLE    = "Report CWD Replacements"
SCRIPT   = "ReplaceCWDReport.py"
SRC_FILE = "%s/%s" % (cdr.DEFAULT_LOGDIR, "CWDReplacements.log")

# Parse form variables
fields = cgi.FieldStorage()

# Establish user session and authorization
# No special authorization required, it's just a report
session = cdrcgi.getSession(fields) or cdrcgi.bail("Please log in")

# Load fields from form
firstDate = fields.getvalue("firstDate")
userId    = fields.getvalue("userId")
docType   = fields.getvalue("docType")
docId     = fields.getvalue("docId")
action    = cdrcgi.getRequest(fields)

# Normalize case for later comparisons
if userId:  userId  = userId.lower()
if docType: docType = docType.lower()

# Navigate away?
if action and action == "Admin Menu":
    cdrcgi.navigateTo ("Admin.py", session)

# Has user seen the form yet?
if fields.getvalue("formSeen") is None:
    buttons = ('Submit', 'Admin Menu')
    page = cdrcgi.Page("CDR Administration", subtitle=TITLE, action=SCRIPT,
                       buttons=buttons, session=session)
    instructions = """\
Retrieve information on documents for which someone has replaced
the current working document (CWD) with an older version.
Fill in the form to select only those replacements meeting the criteria
given in the parameter values.  All parameters are optional.  If all are
blank, all replacements will be reported for which we have logged
information."""
    page.add(page.B.FIELDSET(page.B.P(instructions)))
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Enter Report Parameters"))
    page.add_date_field("firstDate", "Earliest Date")
    page.add_text_field("userId", "User ID")
    page.add_text_field("docType", "Doc Type")
    page.add_text_field("docId", "CDR ID")
    page.add("</fieldset>")
    page.add(page.B.INPUT(type="hidden", name="formSeen", value="True"))
    page.send()

# If we got here, the user has already seen and submitted the form
if firstDate and not cdrcgi.is_date(firstDate):
    cdrcgi.bail("Invalid start date")
if docId:
    # Validate doc ID format
    try:
        result = cdr.exNormalize(docId.upper())
    except Exception:
        cdrcgi.bail('Doc ID "%s" is not a recognized CDR ID format' % docId)
    else:
        docId = str(result[1])

# Construct page and report headers
help = (
    "When did the replacement occur?",
    "CDR ID of the affected document",
    "Document type for the affected document",
    "User ID of the user promoting the version",
    "Version number of last version at time of promotion",
    "Version number of last publishable version at that time, -1 = None",
    "'Y' = CWD was different from last version, else 'N'",
    "Version number promoted to become CWD",
    "Was new CWD also versioned? (Y/N)",
    "Was new CWD also versioned as publishable? (Y/N)",
    "System generated comment ':' user entered comment",
)
headings = ("Date/time", "DocID", "Doc type", "User", "LV", "PV", "Chg",
            "V#", "V", "P", "Comment")
columns = []
for i, h in enumerate(headings):
    columns.append(cdrcgi.Report.Column(h, title=help[i]))

# Open the file
try:
    fp = open(SRC_FILE, "r")
except IOError as info:
    cdrcgi.bail("Unable to open log file: %s" % info)

rows = []
while True:
    # Read each line
    line = fp.readline()
    if not line:
        break

    # Skip lines prior to our first date
    if firstDate and line[0:10] < firstDate:
        continue

    # Parse on tabs
    data = line.split('\t')

    # This is a text file, it could get corrupted, ignore corrupt lines
    if len(data) != 11:
        continue

    # Filters
    if docId and data[1] != docId:
        continue
    if docType and data[2].lower() != docType:
        continue
    if userId and data[3].lower() != userId:
        continue

    # Include the row if we got here.
    row = []
    for i, d in enumerate(data):
        row.append(cdrcgi.Report.Cell(d.strip(), title=help[i]))
    rows.append(row)

# Assemble and send the report.
caption = "Replaced Documents (%d)" % len(rows)
title = "CWD Replacement Report"
table = cdrcgi.Report.Table(columns, rows, caption=caption)
report = cdrcgi.Report(title, [table], banner=title)
report.send()
