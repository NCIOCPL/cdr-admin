#----------------------------------------------------------------------
# $Id$
#
# Produce an Excel spreadsheet showing significant fields from user
# selected Media documents.
#
# Users enter date, diagnosis, category, and language selection criteria.
# The program selects those documents and outputs the requested fields,
# one document per row.
#
# BZIssue::4717 (add audience selection criterion)
# BZIssue::4931 Media Caption and Content Report: Bug in Date Selections
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------

import cdr
import cdrcgi
import cdrdb
import cgi
import copy
import datetime
import ExcelWriter
import os
import sys
import xml.sax
import xml.sax.handler

#----------------------------------------------------------------------
# CGI form variables
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
action     = cdrcgi.getRequest(fields)
session    = cdrcgi.getSession(fields) or cdrcgi.bail("Please login")
diagnosis  = fields.getlist("diagnosis") or ["any"]
category   = fields.getlist("category") or ["any"]
language   = fields.getvalue("language") or "all"
audience   = fields.getvalue("audience") or "all"
start_date = fields.getvalue("start_date")
end_date   = fields.getvalue("end_date")

#----------------------------------------------------------------------
# Form buttons
#----------------------------------------------------------------------
BT_SUBMIT  = "Submit"
BT_ADMIN   = cdrcgi.MAINMENU
BT_REPORTS = "Reports Menu"
BT_LOGOUT  = "Logout"
buttons = (BT_SUBMIT, BT_REPORTS, BT_ADMIN, BT_LOGOUT)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == BT_REPORTS:
    cdrcgi.navigateTo("Reports.py", session)
if action == BT_ADMIN:
    cdrcgi.navigateTo("Admin.py", session)
if action == BT_LOGOUT:
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Connection to database
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except Exception, e:
    cdrcgi.bail("Unable to connect to database", extra=[str(e)])

#----------------------------------------------------------------------
# Assemble the lists of valid values.
#----------------------------------------------------------------------
query = cdrdb.Query("query_term t", "t.doc_id", "t.value")
query.join("query_term m", "m.int_val = t.doc_id")
query.where("t.path = '/Term/PreferredName'")
query.where("m.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'")
results = query.unique().order(2).execute(cursor).fetchall()
diagnoses = [("any", "Any Diagnosis")] + results
query = cdrdb.Query("query_term", "value", "value")
query.where("path = '/Media/MediaContent/Categories/Category'")
query.where("value <> ''")
results = query.unique().order(1).execute(cursor).fetchall()
categories = [("any", "Any Category")] + results
languages = (("all", "All Languages"), ("en", "English"), ("es", "Spanish"))
audiences = (
    ("all", "All Audiences"),
    ("Health_professionals", "HP"),
    ("Patients", "Patient"),
)

#----------------------------------------------------------------------
# Validate the form values. The expectation is that any bogus values
# will come from someone tampering with the form, so no need to provide
# the hacker with any useful diagnostic information. Dates will be
# scrubbed in the test below.
#----------------------------------------------------------------------
for value, values in ((diagnosis, diagnoses), (audience, audiences),
                      (language, languages), (category, categories)):
    if isinstance(value, basestring):
        value = [value]
    values = [str(v[0]).lower() for v in values]
    for val in value:
        if val.lower() not in values:
            cdrcgi.bail("Corrupted form value")

#----------------------------------------------------------------------
# Show the form if we don't have a request yet.
#----------------------------------------------------------------------
if not cdrcgi.is_date(start_date) or not cdrcgi.is_date(end_date):
    end = datetime.date.today()
    start = end - datetime.timedelta(30)
    title = "Administrative Subsystem"
    subtitle = "Media Caption and Content Report"
    script = "MediaCaptionContent.py"
    page = cdrcgi.Page(title, subtitle=subtitle, action=script,
                       buttons=buttons, session=session)
    instructions = (
        "To prepare an Excel format report of Media Caption and Content "
        "information, enter starting and ending dates (inclusive) for the "
        "last versions of the Media documents to be retrieved.  You may also "
        "select documents with specific diagnoses, categories, language, or "
        "audience of the content description.  Relevant fields from the Media "
        "documents that meet the selection criteria will be displayed in an "
        "Excel spreadsheet."
    )
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Instructions"))
    page.add(page.B.P(instructions))
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Time Frame"))
    page.add_date_field("start_date", "Start Date", value=start)
    page.add_date_field("end_date", "End Date", value=end)
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Include Specific Content"))
    page.add_select("diagnosis", "Diagnosis", diagnoses, "any", multiple=True)
    page.add_select("category", "Category", categories, "any", multiple=True)
    page.add_select("language", "Language", languages, "all")
    page.add_select("audience", "Audience", audiences, "all")
    page.add("</fieldset>")
    page.send()

######################################################################
#                        SAX Parser for doc                          #
######################################################################
class DocHandler(xml.sax.handler.ContentHandler):

    def __init__(self, wantFields, language, audience):
        """
        Initialize parsing.

        Pass:
            wantFields - Dictionary of full pathnames to elements of interest.
                         Key   = full path to element.
                         Value = Empty list = []
            language   - "en", "es", or None for any language
            audience   - "Health_professionals", "Patients", or None (for any)
        """
        self.wantFields = wantFields

        # Start with dictionary of desired fields, empty of text
        self.fldText  = copy.deepcopy(wantFields)
        self.language = language
        self.audience = audience

        # Full path to where we are
        self.fullPath = ""

        # Name of a field we want, when we encounter it
        self.getText = None

        # Cumulate text here for that field
        self.gotText = ""

    def startElement(self, name, attrs):
        # Push this onto the full path
        self.fullPath += '/' + name

        # Is it one we're supposed to collect?
        if self.fullPath in self.wantFields:

            # Do we need to filter by language or audience?
            keep = True
            if self.language:
                language = attrs.get('language')
                if language and language != self.language:
                    keep = False
            if keep and self.audience:
                audience = attrs.get('audience')
                if audience and audience != self.audience:
                    keep = False
            if keep:
                self.getText = self.fullPath

    def characters(self, content):
        # Are we in a field we're collecting from?
        if self.getText:
            self.gotText += content

    def endElement(self, name):
        # Are we wrapping up a field we were collecting data from
        if self.getText == self.fullPath:
            # Make the text available
            self.fldText[self.fullPath].append(self.gotText)

            # No longer collecting
            self.getText = None
            self.gotText = ""

        # Pop element name from full path
        self.fullPath = self.fullPath[:self.fullPath.rindex('/')]

    def getResults(self):
        """
        Retrieve the results of the parse.

        Return:
            Dictionary containing:
                Keys   = Full paths
                Values = Sequence of 0 or more values for that path in the doc
        """
        return self.fldText

######################################################################
#                    Retrieve data for the report                    #
######################################################################

# Path strings for where clauses.
content_path = "/Media/MediaContent"
diagnosis_path = content_path + "/Diagnoses/Diagnosis/@cdr:ref"
category_path = content_path + "/Categories/Category"
caption_path = content_path + "/Captions/MediaCaption"
language_path = caption_path + "/@language"
audience_path = caption_path + "/@audience"

# Create base query for the documents
query = cdrdb.Query("document d", "d.id", "d.title").unique().order(2)
query.join("doc_type t", "t.id = d.doc_type")
query.join("doc_version v", "d.id = v.id")
query.where("t.name = 'Media'")
query.where(query.Condition("v.dt", start_date, ">="))
query.where(query.Condition("v.dt", "%s 23:59:59" % end_date, "<="))

# If optional criteria entered, add the requisite joins
# One or more diagnoses
if diagnosis and "any" not in diagnosis:
    query.join("query_term q1", "q1.doc_id = d.id")
    query.where(query.Condition("q1.path", diagnosis_path))
    query.where(query.Condition("q1.int_val", diagnosis, "IN"))

# One or more categories
if category and "any" not in category:
    query.join("query_term q2", "q2.doc_id = d.id")
    query.where(query.Condition("q2.path", category_path))
    query.where(query.Condition("q2.value", category, "IN"))

# Only one language can be specified
if language and language != "all":
    query.join("query_term q3", "q3.doc_id = d.id")
    query.where(query.Condition("q3.path", language_path))
    query.where(query.Condition("q3.value", language))

# Only one audience can be specified
if audience and audience != "all":
    query.join("query_term q4", "q4.doc_id = d.id")
    query.where(query.Condition("q4.path", audience_path))
    query.where(query.Condition("q4.value", audience))

# DEBUG
query.log(logfile=cdr.DEFAULT_LOGDIR + "/media.log")
#query_str = "QUERY:\n%s" % query
#logfile = "d:/cdr/Log/media.log"
#parms = ["PARAMETERS:"] + [repr(p) for p in query._parms]
#cdr.logwrite("%s\n%s" % (query_str, "\n\t".join(parms)), logfile)

# Execute query
try:
    rows = query.execute(cursor).fetchall()
except cdrdb.Error, info:
    msg = "Database error executing MediaCaptionContent.py query"
    extra = (
        "query = %s" % query,
        "error = %s" % str(info),
    )
    cdr.logwrite(str(info))
    cdrcgi.bail(msg, extra=extra)

# If there was no data, we're done
if len(rows) == 0:
    cdrcgi.bail("Your selection criteria did not retrieve any documents",
                extra=["Please click the back button and try again."])

######################################################################
#                 Construct the output spreadsheet                   #
######################################################################

def fillCell(wsRow, colNum, dataList, sep):
    """
    Create a cell on wsRow at colNum with all of the data in dataList.
    """
    count = 0
    text  = ""
    for data in dataList:
        if count > 0:
            # text += "  +  "
            text += sep
        text += data
        count += 1
    wsRow.addCell(colNum, text)

# Create Style objects for Excel
colLabelInterior     = ExcelWriter.Interior("#0000FF", "Solid")
docSeparatorInterior = ExcelWriter.Interior("#C0C0C0", "Solid")
colLabelFont         = ExcelWriter.Font(color="#FFFFFF", bold=True)
sheetNameFont        = ExcelWriter.Font(color="#000000", bold=True)
centerAlign          = ExcelWriter.Alignment(horizontal="Center")
leftAlign            = ExcelWriter.Alignment(horizontal="Left")
dataAlign            = ExcelWriter.Alignment(horizontal="Left",
                                             vertical="Top", wrap="1")

# Create an Excel workbook and a worksheet
audienceTag = { "Health_professionals": " - HP",
                "Patients": " - Patient" }.get(audience, "")
titleText = "Media Caption and Content Report%s" % audienceTag
wb = ExcelWriter.Workbook('ahm', 'NCI')
ws = wb.addWorksheet("Media Caption-Content", frozenRows=3)


# Create all the columns
ws.addCol(1, 45)        # CDR ID
ws.addCol(2, 100)       # Title
ws.addCol(3, 100)       # Diagnosis
ws.addCol(4, 125)       # Proposed Summaries
ws.addCol(5, 125)       # Proposed Glossary Terms
ws.addCol(6, 100)       # Label Names
ws.addCol(7, 125)       # Content Description
ws.addCol(8, 125)       # Caption

# Setup object styles
colLabelStyle        = wb.addStyle(name="colLabel", alignment=centerAlign,
                          font=colLabelFont, interior=colLabelInterior)
docSeparatorStyle    = wb.addStyle(name="docSeparator",
                          interior=docSeparatorInterior)
sheetNameStyle       = wb.addStyle(name="sheetName", alignment=leftAlign,
                          font=sheetNameFont)
dataStyle            = wb.addStyle(name="data", alignment=dataAlign)

# Title row at the top
titleRow = ws.addRow(1, style=sheetNameStyle)
titleRow.addCell(4, value=titleText)

# Coverage of the report
coverageRow = ws.addRow(2, style=sheetNameStyle)
coverageRow.addCell(4, "        %s   -   %s" % (start_date, end_date))

# Column label headers
labelRow = ws.addRow(3, colLabelStyle)
labels = ("CDR ID", "Title", "Diagnosis", "Proposed Summaries",
          "Proposed Glossary Terms", "Label Names",
          "Content Description", "Caption")
col = 1
for label in labels:
    labelRow.addCell(col, label)
    col += 1

######################################################################
#                      Fill the sheet with data                      #
######################################################################

# Fields we'll request from the XML parser
fieldList = (
    ("/Media/MediaTitle", "\n"),
    ("/Media/MediaContent/Diagnoses/Diagnosis","\n"),
    ("/Media/ProposedUse/Summary","\n"),
    ("/Media/ProposedUse/Glossary","\n"),
    ("/Media/PhysicalMedia/ImageData/LabelName","\n"),
    ("/Media/MediaContent/ContentDescriptions/ContentDescription","\n\n"),
    ("/Media/MediaContent/Captions/MediaCaption","\n\n")
)

# Put them in a dictionary for use by parser
wantFields = {}
for fld, sep in fieldList:
    wantFields[fld] = []

# Data starts in worksheet row 3
wsRowNum = 4

for row in rows:
    # Fetch the full record from the database, denormalized with data content
    docId = row[0]
    result = cdr.filterDoc(session,
               filter=["name:Fast Denormalization Filter"], docId=docId)
    if type(result) != type(()):
        cdrcgi.bail("""\
Failure retrieving filtered doc for doc ID=%d<br />
Error: %s""" % (docId, result))

    xmlText = result[0]

   # Is specific language and/or audience requested?
    getLanguage = language != 'all' and language or None
    getAudience = audience != 'all' and audience or None

    # Parse it, getting back a list of fields
    dh = DocHandler(wantFields, getLanguage, getAudience)
    xml.sax.parseString(xmlText, dh)
    gotFields = dh.getResults()

    # DEBUG
    # cdrcgi.bail("docId=%s<br><p>%s</p>" % (docId,gotFields))

    # Add a new row with each piece of info
    wsRow = ws.addRow(wsRowNum, style=dataStyle)
    wsRow.addCell(1, docId)
    colNum = 2
    for fld,sep in fieldList:
        fillCell(wsRow, colNum, gotFields[fld], sep)
        colNum += 1
    wsRowNum += 2

# Output
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=MediaCaptionAndContent.xls"
print
wb.write(sys.stdout, True)
