#----------------------------------------------------------------------
# Excel report on links from protocol documents to terms having a
# specified semantic type. Takes about a minute to run (depending
# on the type).
#
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------
import cgi
import cdrcgi
import cdrdb
import sys
import datetime

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
cursor   = cdrdb.connect("CdrGuest").cursor()
repTitle = "Semantic Type Report"
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Semantic Type Report"
script   = "SemanticTypeReport.py"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
semanticType = fields.getvalue("SemanticType")
if semanticType:
    try:
        semanticType = int(semanticType)
    except:
        semanticType = None

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)
if action == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Get the SemanticTypes
#----------------------------------------------------------------------
class SemanticType:
    def __init__(self, id, title):
        self.id = id
        self.title = title.split(";")[0]
    def __cmp__(self, other):
        return cmp(self.title, other.title)
semanticTypes = {}
query = cdrdb.Query("document d", "d.id", "d.title").unique()
query.join("query_term t", "t.int_val = d.id")
query.where("t.path = '/Term/SemanticType/@cdr:ref'")
for doc_id, doc_title in query.execute(cursor).fetchall():
    semanticTypes[doc_id] = SemanticType(doc_id, doc_title)

#----------------------------------------------------------------------
# If we have no request, put up the request form.
#----------------------------------------------------------------------
if not semanticType:
    options = [(st.id, st.title) for st in sorted(semanticTypes.values())]
    page = cdrcgi.Page(title, subtitle=section, action=script,
                       buttons=buttons, session=session, method="GET")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select a Single Semantic Type For the Report"))
    page.add_select("SemanticType", "Type Name", [(0, "")] + options, 0)
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Class for storing protocolTypes
#----------------------------------------------------------------------
class ProtocolType:
    def __init__(self, docType, title, statusPath):
        self.docType = docType
        self.title = title
        self.statusPath = statusPath
    def __cmp__(self, other):
        return cmp(self.title, other.title)

#----------------------------------------------------------------------
# Populate the protocolTypes.
#----------------------------------------------------------------------
protocolTypes = {}
paths = (
    "/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus",
    "/CTGovProtocol/OverallStatus"
)
for path in paths:
    type_name = path.split("/")[1]
    cursor.execute("SELECT id FROM doc_type WHERE name = ?", type_name)
    type_id = cursor.fetchall()[0][0]
    protocolTypes[type_id] = ProtocolType(type_id, type_name, path)

#----------------------------------------------------------------------
# Class for storing the document information
#----------------------------------------------------------------------
class Document:
    def __init__(self, id, title,status,docType):
        self.id = "CDR%010d" % id
        self.title = title
        self.status = status
        self.docType = docType
        self.terms = []
    def __cmp__(self, other):
        result = cmp(self.status, other.status)
        if not result:
            result = cmp(self.id, other.id)
        return result

#----------------------------------------------------------------------
# Get the documents. The parameters used for string interpolation in
# the query have been vetted to ensure that they haven't been tampered
# with. If you modify this query, make sure that's still true.
#----------------------------------------------------------------------
documents = []
document_ids = {}
keys = protocolTypes.keys()
for key in keys:
    protocolType = protocolTypes[key]
    subquery = cdrdb.Query("query_term", "doc_id")
    subquery.where("path = '/Term/SemanticType/@cdr:ref'")
    subquery.where("int_val = %d" % semanticType)
    query = cdrdb.Query("document d", "d.id", "d.title", "s.value", "t.value")
    query.join("query_term s", "s.doc_id = d.id")
    query.join("query_term q", "q.doc_id = d.id")
    query.join("query_term t", "t.doc_id = q.int_val")
    query.where("q.path LIKE '/%s/%%/@cdr:ref'" % protocolType.title)
    query.where("s.path = '%s'" % protocolType.statusPath)
    query.where("d.active_status = 'A'")
    query.where("t.path = '/Term/PreferredName'")
    query.where(query.Condition("q.int_val", subquery, "IN"))
    query.order("d.id", "t.value")
    query.log(label="SEMANTIC TYPE REPORT QUERY")
    rows = query.execute(cursor, 300).fetchall()
    for id, title, status, term in rows:
        document = document_ids.get(id)
        if not document:
            document = Document(id, title, status, protocolType.docType)
            document_ids[id] = document
            documents.append(document)
        document.terms.append(term)
documents.sort()

#----------------------------------------------------------------------
# Write the excel file
#----------------------------------------------------------------------
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

title = semanticTypes[int(semanticType)].title
now = datetime.datetime.now()
t = now.strftime("%Y%m%d%H%M%S")

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
styles = cdrcgi.ExcelStyles()

CHAR_WIDTH = 4.5

for protocolType in sorted(protocolTypes.values()):
    sheet = styles.add_sheet(protocolType.title)
    numDocs = 0

    # Determine the column widths
    #---------------------------------
    widths = [18, 80, 40, 25]
    for doc in documents:
        break
        if doc.docType == protocolType.docType:
            numDocs += 1
            for term in doc.terms:
                width = CHAR_WIDTH * len(term)
                if widths[2] < width:
                    widths[2] = width

    # Set the column widths
    # -------------------
    for col, width in enumerate(widths):
        sheet.col(col).width = styles.chars_to_width(width)

    # Create the top rows
    # ---------------------
    banners = (
        "Semantic Type Report",
        "Semantic Type : %s" % title,
        "Total Number of Trials: %d" % numDocs
    )
    style = styles.banner
    for row, banner in enumerate(banners):
        sheet.write_merge(row, row, 0, 3, banner, style)
        style = styles.header
    sheet.write_merge(len(banners), len(banners), 0, 3, "")
    sheet.set_panes_frozen(True)
    sheet.set_horz_split_pos(len(banners) + 2)

    # Create the Header row
    # ---------------------
    row = len(banners) + 1
    headers = ("CDR-ID", "Title", "Term(s)", "Current Protocol Status")
    for col, header in enumerate(headers):
        sheet.write(row, col, header, styles.header)

    # Write the data
    # ---------------------
    for doc in documents:
        if doc.docType == protocolType.docType:
            row += 1
            sheet.write(row, 0, doc.id, styles.left)
            sheet.write(row, 1, doc.title, styles.left)
            sheet.write(row, 2, "\n".join(doc.terms), styles.left)
            sheet.write(row, 3, doc.status, styles.left)

print("Content-type: application/vnd.ms-excel")
print("Content-Disposition: attachment; filename=SemanticTypeReport-%s.xls" % t)
print()

styles.book.save(sys.stdout)
