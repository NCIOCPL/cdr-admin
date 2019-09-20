#----------------------------------------------------------------------
# Produce an Excel spreadsheet showing significant fields from user
# selected Media documents.
#
# Users enter date, diagnosis, category, and language selection criteria.
# The program selects those documents and outputs the requested fields,
# one document per row.
# Enhancing report to include an additional, optional column with a
# thumbnail image.
#
# BZIssue::4717 (add audience selection criterion)
# BZIssue::4931 Media Caption and Content Report: Bug in Date Selections
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------

import cdr
import cdrcgi
import cgi
import copy
import datetime
import os
import sys
import xml.sax
import xml.sax.handler

from datetime import datetime as dt
from io import BytesIO
from sys import stdout
from xlsxwriter import Workbook
from cdr import get_image
from cdrapi.docs import Doc
from cdrapi.users import Session
from cdrapi import db

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
addImage   = fields.getvalue("image") or "N"

start_date = fields.getvalue("start_date")
end_date   = fields.getvalue("end_date")

# ------------------------
# Testing - Setting values
#start_date = '2019-01-01'
#end_date =   '2019-07-09'
#diagnosis = ["any"]
#category  = ["any"]
#language  = "all"
#audience  = "all"
#addImage  = "Y"
# ------------------------

LOGGER = cdr.Logging.get_logger("MediaCaptionContent")
LOGGER.info("*** started")
URL = "{}/cgi-bin/cdr/GetCdrImage.py?id={}"
FILENAME = "{}.xlsx".format(dt.now().strftime("%Y%m%d%H%M%S"))
output = BytesIO()

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
    conn = db.connect(user="CdrGuest")
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail("Unable to connect to database", extra=[str(e)])

#----------------------------------------------------------------------
# Assemble the lists of valid values.
#----------------------------------------------------------------------
query = db.Query("query_term t", "t.doc_id", "t.value")
query.join("query_term m", "m.int_val = t.doc_id")
query.where("t.path = '/Term/PreferredName'")
query.where("m.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'")
rows = query.unique().order(2).execute(cursor).fetchall()
diagnoses = [("any", "Any Diagnosis")] + [tuple(row) for row in rows]

query = db.Query("query_term", "value", "value")
query.where("path = '/Media/MediaContent/Categories/Category'")
query.where("value <> ''")
results = query.unique().order(1).execute(cursor).fetchall()

categories = [("any", "Any Category")] + [tuple(row) for row in results]
languages = (("all", "All Languages"),
             ("en", "English"),
             ("es", "Spanish"))
audiences = (("all", "All Audiences"),
             ("Health_professionals", "HP"),
             ("Patients", "Patient"))
images    = (("Y", "Yes"), ("N", "No"))

#----------------------------------------------------------------------
# Validate the form values. The expectation is that any bogus values
# will come from someone tampering with the form, so no need to provide
# the hacker with any useful diagnostic information. Dates will be
# scrubbed in the test below.
#----------------------------------------------------------------------
for value, values in ((diagnosis, diagnoses), (audience, audiences),
                      (language, languages), (category, categories),
                      (addImage, images)):
    if isinstance(value, str):
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
    page.add_select("image", "Images", images, "N")
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
query = db.Query("document d", "d.id", "d.title").unique().order(2)
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

# Execute query
try:
    docIds = [row[0] for row in query.execute(cursor).fetchall()]
    #print("docs: {}".format(docIds))
except Exception as e:
    msg = "Database error executing MediaCaptionContent.py query"
    extra = f"query = {query}", f"error = {e}"
    LOGGER.exception("Report database query failure")
    cdrcgi.bail(msg, extra=extra)

# If there was no data, we're done
if len(docIds) == 0:
    cdrcgi.bail("Your selection criteria did not retrieve any documents",
                extra=["Please click the back button and try again."])

######################################################################
#                 Construct the output spreadsheet                   #
######################################################################

# Create a spreadsheet with images (using XlsxWriter)
# ---------------------------------------------------
book = Workbook(output, {"in_memory": True})   # open workbook

audienceTag = { "Health_professionals": " - HP",
                "Patients": " - Patient" }.get(audience, "")

# Creating a sheet with tab caption
titleText = "Media Caption and Content Report%s" % audienceTag
tabText = "Media Caption-Content"
sheet = book.add_worksheet(tabText)          # create worksheet

sheet.freeze_panes(3, 0)                     # Freeze first 3 rows

# Specify columns and column headers, adjust if image is displayed
# ----------------------------------------------------------------
last_col = 7
widths = (10, 25, 25, 25, 25, 25, 25, 25)
labels = ("CDR ID", "Title", "Diagnosis", "Proposed Summaries",
          "Proposed Glossary Terms", "Label Names",
          "Content Description", "Caption")

if addImage == 'Y':
    last_col = 8
    widths += (30,)
    labels += ('Image',)

# First header row - Report title
merge_format = book.add_format({'align': 'center',
                                 'bold': True})
header_format = book.add_format({'bold': True,
                                 'align': 'center',
                                 'fg_color': '#0000FF',
                                 'font_color': '#FFFFFF'})
cell_format = book.add_format({'text_wrap': True,
                               'align': 'left',
                               'valign': 'top'})
sheet.merge_range(0, 0, 0, last_col, titleText, merge_format)

# Second header row - Date range
coverage = "%s -- %s" % (start_date, end_date)
sheet.merge_range(1, 0, 1, last_col, coverage, merge_format)

for i, width in enumerate(widths):
    sheet.set_column(i, i, width)

# Adding the header row with formatting
for col, label in enumerate(labels):
    sheet.write(2, col, label, header_format)

#assert(len(widths) == len(labels))


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
    ("/Media/MediaContent/Captions/MediaCaption","\n\n"),
    ("/Media/PhysicalMedia/ImageData/ImageEncoding","\n")
)

if addImage == 'Y':
    assert(len(labels) - 1 == len(fieldList))
else:
    assert(len(labels)     == len(fieldList))

# Put them in a dictionary for use by parser
wantFields = {}
for fld, sep in fieldList:
    wantFields[fld] = []

# Is specific language and/or audience requested?
getLanguage = language != 'all' and language or None
getAudience = audience != 'all' and audience or None

# Populate the data cells
row = 3
filters = ["name:Fast Denormalization Filter"]
OPTS = dict(x_offset=10, y_offset=10)

for docId in docIds:
    # print(docId)
    # Fetch the full record from the database, denormalized with data content
    result = cdr.filterDoc(session, filter=filters, docId=docId)
    if not isinstance(result, tuple):
        cdrcgi.bail("""\
Failure retrieving filtered doc for doc ID=%d<br />
Error: %s""" % (docId, result))

    # Parse it, getting back a list of fields
    # ---------------------------------------
    dh = DocHandler(wantFields, getLanguage, getAudience)
    xmlText = result[0]
    xml.sax.parseString(xmlText, dh)
    gotFields = dh.getResults()

    # Write the CDR-ID first, then add the summary info from the
    # fieldlist but skipping the first item indicating media type
    # -----------------------------------------------------------
    sheet.write(row, 0, docId, cell_format)

    for i, field_info in enumerate(fieldList[:-1], start=1):
        path, separator = field_info
        values = separator.join(gotFields[path])
        sheet.write(row, i, values, cell_format)

    # Add the image thumbnail
    # -----------------------
    if addImage == 'Y':
        path, separator = fieldList[-1]
        values = gotFields[path]

        if values and values[0] == 'JPEG':
            doc = Doc(session, id=docId)
            try:
                image = get_image(doc.id, height=200, width=200, return_stream=True)
            except Exception as e:
                LOGGER.exception("Fetching blob for %s", doc.id)

                #args = doc.cdr_id, doc.has_blob, e
                #sys.stderr.write("{} ({}) failed: {}\n".format(*args))
                continue

            OPTS["url"] = URL.format(cdr.CBIIT_NAMES[2], doc.id)
            OPTS["image_data"] = image
            #OPTS["tip"] = doc.title

            sheet.insert_image(row, 8, "dummy", OPTS)
            sheet.set_row(row, 100)
            sheet.set_column(8, 8, 60)

    row += 2

LOGGER.info("*** finished")
#sys.exit()
# Output
book.close()
output.seek(0)
book_bytes = output.read()
stdout.buffer.write(f"""\
Content-type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename={FILENAME}
Content-length: {len(book_bytes):d}

""".encode("utf-8"))
stdout.buffer.write(book_bytes)
