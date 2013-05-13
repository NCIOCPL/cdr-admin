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
#
#----------------------------------------------------------------------

import sys, cgi, cgitb, time, xml.sax, xml.sax.handler, os, os.path, copy
import cdr, cdrcgi, cdrdb, ExcelWriter

cgitb.enable()

# No errors yet
errMsgs = ""

# CGI form variables
session   = None
startDate = None
endDate   = None
diagnosis = None
category  = None
language  = None
audience  = None

# Form buttons
BT_SUBMIT  = "Submit"
BT_ADMIN   = cdrcgi.MAINMENU
BT_REPORTS = "Reports Menu"
BT_LOGOUT  = "Logout"
buttons = (BT_SUBMIT, BT_REPORTS, BT_ADMIN, BT_LOGOUT)

# Has the user entered anything yet?
fields = cgi.FieldStorage()
if fields:
    session = cdrcgi.getSession(fields) or cdrcgi.bail("Please login")

    # Standard button navigation
    action = cdrcgi.getRequest(fields)
    if action == BT_REPORTS:
        cdrcgi.navigateTo("Reports.py", session)
    if action == BT_ADMIN:
        cdrcgi.navigateTo("Admin.py", session)
    if action == BT_LOGOUT:
        cdrcgi.logout(session)

    # Start and end dates are required
    if fields.has_key("startDate"):
        # Validate dates
        startDate = fields.getvalue('startDate')
        if not cdr.strptime(startDate, '%Y-%m-%d'):
            errMsgs += "Invalid start date '%s'.<br />" % startDate
            startDate = None
        if fields.has_key("endDate"):
            endDate = fields.getvalue('endDate')
            if not cdr.strptime(endDate, '%Y-%m-%d'):
                errMsgs += "Invalid end date '%s'.<br />" % endDate
                startDate = None
        else:
            errMsgs += "Missing end date.<br />"

        if errMsgs:
            errMsgs += "Please use yyyy-mm-dd format."

    # Other fields are optional
    if fields.has_key("diagnosis"):
        diagnosis = fields.getlist("diagnosis")
    if fields.has_key("category"):
        category = fields.getlist("category")
    if fields.has_key("language"):
        language = fields.getvalue("language")
    if fields.has_key("audience"):
        audience = fields.getvalue("audience")

# Format errors for display
if errMsgs:
    errMsgs = "<p><strong><font color='red'>%s</font></strong></p>" % errMsgs

# Connection to database
try:
    conn = cdrdb.connect()
except cdrdb.Error, info:
    cdrcgi.bail("Unable to connect to database:<br />%s" % str(info))

if not startDate or errMsgs:
    # If no start date, or invalid one, the form has not been displayed,
    #   or not filled in, or not filled in correctly
    # Display an HTML form on screen

    # Setup default dates for 30 days ago through today
    now = time.time()
    ago = now - (30 * 24 * 60 * 60)
    startDate = time.strftime("%Y-%m-%d", time.localtime(ago))
    endDate   = time.strftime("%Y-%m-%d", time.localtime(now))

    # Query to fetch all of the Diagnosis ids and terms in Media documents
    diagnosisMenuQry = """\
SELECT DISTINCT qt.doc_id, qt.value
  FROM query_term qt
  JOIN query_term qm
    ON qt.doc_id = qm.int_val
 WHERE qt.path = '/Term/PreferredName'
   AND qm.int_val IN (
    SELECT DISTINCT int_val
      FROM query_term
     WHERE path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'
  )
 ORDER BY qt.value
"""
    # Query to fetch all categories used in Media documents
    # Ignores any defined categories that aren't actually used
    # Fetches each twice for easy use in cdrcgi.generateHtmlPicklist()
    categoryMenuQry = """\
SELECT DISTINCT value, value
  FROM query_term
 WHERE path = '/Media/MediaContent/Categories/Category'
 ORDER BY 1
"""

    # Pattern for forming option items in picklist selects
    optionPattern = "<option value='%s'>%s</option>"

    # Add these attributes to "select" element
    selAttrs = "multiple='1' size='5'"

    # First option for diagnosis and category picklists
    dftDiagnosis = \
      "<option value='any' selected='1'>Any Diagnosis</option>\n"
    dftCategory  = \
      "<option value='any' selected='1' multiple='1'>Any Category</option>\n"

    # Construct html form
    header = cdrcgi.header("Administrative Subsystem",
             "Media Caption and Content Report",
             "Media Caption and Content Report",
             script="MediaCaptionContent.py", buttons=buttons)
    html = header + """
<fieldset>
<legend>&nbsp;Instructions&nbsp;</legend>
<p style="font-size: 10pt; font-weight: 600">
To prepare an Excel format report of Media Caption and Content
information, enter starting and ending dates (inclusive) for the
last versions of the Media documents to be retrieved.  You may also
select documents with specific diagnoses, categories, language, or
audience of the content description.  Relevant fields from the Media
documents that meet the selection criteria will be displayed in an
Excel spreadsheet.
</p>
</fieldset>

%s

    <fieldset>
     <legend>&nbsp;Time Frame&nbsp;</legend>
     <center>
      <table width="100%%" border='0'>
       <tr>
        <td width="25%%" align="right" nowrap="1"><b>Start date: </b></td>
        <td align="left"><input type='text' name='startDate' 
                                size='12' value='%s' />
       </tr>
       <tr>
        <td align="right" nowrap="1">
         <b>&nbsp; &nbsp; &nbsp; End date: </b>
        </td>
        <td align="left"><input type='text' name='endDate' 
                                size='12' value='%s' />
       </tr>
      </table>
     </center>
    </fieldset>
""" % (errMsgs, startDate, endDate)

    html += """
    <fieldset>
     <legend>&nbsp;Include Specific Content&nbsp;</legend>
     <center>
      <table width="100%%" border='0'>
       <tr>
        <td width="25%%" align="right"><b>Diagnosis: </b></td><td align="left">
    %s
       </tr>
       <tr>
        <td align="right"><b>Category: </b></td><td align="left">
    %s
       </tr>
       <tr>
        <td align="right"><b>Language: </b></td><td align="left">
          <select name="language">
           <option value="all" selected="1">All Languages</option>
           <option value="en">English</option>
           <option value="es">Spanish</option>
          </select></td>
       </tr>
       <tr>
        <td align="right"><b>Audience: </b></td><td align="left">
          <select name="audience">
           <option value="all" selected="1">All Audiences</option>
           <option value="Health_professionals">HP</option>
           <option value="Patients">Patient</option>
          </select></td>
       </tr>
      </table>
     </center>
    </fieldset>
   <input type="hidden" name=%s value=%s />
  </form>
 </body>
</html>
""" % (
       cdrcgi.generateHtmlPicklist(conn, "diagnosis", diagnosisMenuQry,
                optionPattern, selAttrs=selAttrs, firstOpt=dftDiagnosis),
       cdrcgi.generateHtmlPicklist(conn, "category", categoryMenuQry,
                optionPattern, selAttrs=selAttrs, firstOpt=dftCategory),
       cdrcgi.SESSION, session)

    # Send html and exit
    cdrcgi.sendPage(html)

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

# Create base query for the documents
selQry = """\
SELECT DISTINCT d.id, d.title
  FROM document d
  JOIN doc_type t
    ON d.doc_type = t.id
  JOIN doc_version v
    ON d.id = v.id
"""

# Create base where clause
whereClause = """\
 WHERE t.name = 'Media'
   AND v.dt >= '%s'
   AND v.dt < dateadd(day, 1, '%s')
""" % (startDate, endDate)

# If optional criteria entered, add the requisite joins
# One or more diagnoses
if diagnosis and diagnosis != ['any']:
    selQry += """\
  JOIN query_term qdiag
    ON qdiag.doc_id = d.id
"""
    diagList = ""
    for diag in diagnosis:
        if diagList:
            diagList += ","
        diagList += "%s" % diag
    # Note: var diagnosis is a list of 1 or more integer CDR IDs
    whereClause += """\
   AND qdiag.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'
   AND qdiag.int_val IN (%s)
""" % diagList

# One or more categories
if category and category != ['any']:
    selQry += """\
  JOIN query_term qcat
    ON qcat.doc_id = d.id
"""
    # Category is a string, not a CDR ID.  Have to make a list
    catList = ""
    for cat in category:
        if catList:
            catList += ","
        catList += "'%s'" % cat
    whereClause += """\
   AND qcat.path = '/Media/MediaContent/Categories/Category'
   AND qcat.value IN (%s)
""" % catList

# Only one language can be specified
if language and language != 'all':
    selQry += """\
  JOIN query_term qlang
    ON qlang.doc_id = d.id
"""
    whereClause += """\
   AND qlang.path = '/Media/MediaContent/Captions/MediaCaption/@language'
   AND qlang.value = '%s'
""" % language

# Only one audience can be specified
if audience and audience != 'all':
    selQry += """\
  JOIN query_term audience
    ON audience.doc_id = d.id
"""
    whereClause += """\
   AND audience.path = '/Media/MediaContent/Captions/MediaCaption/@audience'
   AND audience.value = '%s'
""" % audience

# Put it all together
selQry += whereClause + " ORDER BY d.title"

# DEBUG
cdr.logwrite(selQry, "d:/cdr/Log/media.log")

# Execute query
try:
    cursor = conn.cursor()
    cursor.execute(selQry)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    msg = "Database error executing MediaCaptionContent.py selQry<br>\n" + \
          "selQry = %s<br>\nError: %s\n" % (selQry, str(info))
    cdr.logwrite(msg)
    cdrcgi.bail(msg)

# If there was no data, we're done
if len(rows) == 0:
    cdrcgi.bail("""\
Your selection criteria did not retrieve any documents<br />
Please click the back button and try again.""")

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
coverageRow.addCell(4, "        %s   -   %s" % (startDate, endDate))

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
