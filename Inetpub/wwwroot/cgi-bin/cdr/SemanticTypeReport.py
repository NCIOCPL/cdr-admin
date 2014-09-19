#----------------------------------------------------------------------
#
# $Id$
#
# Excel report on links from protocol documents to terms having a
# specified semantic type. Takes about a minute to run (depending
# on the type).
#
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cgi
import cdrcgi
import cdrdb
import sys
import datetime
import ExcelWriter

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
wb                  = ExcelWriter.Workbook()
b                   = ExcelWriter.Border()
borders             = ExcelWriter.Borders(b, b, b, b)
dataFont            = ExcelWriter.Font(name='Arial', size=10)
dataAlign           = ExcelWriter.Alignment('Left', 'Top', wrap=True)
dataStyle           = wb.addStyle(alignment=dataAlign, font=dataFont)
headerFont          = ExcelWriter.Font(name='Arial', size=10, color="#FFFFFF",
                                       bold=True)
headerInterior      = ExcelWriter.Interior("#0000FF", "Solid")
headerAlign         = ExcelWriter.Alignment('Center', 'Top', wrap=True)
headerStyle         = wb.addStyle(alignment=headerAlign, font=headerFont,
                                  interior=headerInterior)
columnTitleFont     = ExcelWriter.Font(name='Arial', size=10, color="#FFFFFF",
                                       bold=True)
columnTitleInterior = ExcelWriter.Interior("#000088", "Solid")
columnTitleAlign    = ExcelWriter.Alignment('Center', 'Top', wrap=True)
columnTitleStyle    = wb.addStyle(alignment=columnTitleAlign,
                                  font=columnTitleFont,
                                  interior=columnTitleInterior)

for protKey in protocolTypes:
    protocolType = protocolTypes[protKey]
    sTmp = protocolType.title[:31]
    ws = wb.addWorksheet(sTmp.replace('/','-'), style=dataStyle, height=45,
                         frozenRows=5)
    numDocs = 0

    # Determine the width of column 3
    #---------------------------------
    colThreeWidth = 220
    charWidth = 4.5
    for doc in documents:
        if doc.docType == protocolType.docType:
            numDocs += 1
            for term in doc.terms:
                if colThreeWidth < charWidth * len(term):
                    colThreeWidth = charWidth * len(term)

    # Set the colum width
    # -------------------
    ws.addCol(1, 100)
    ws.addCol(2, 450)
    ws.addCol(3, colThreeWidth)
    ws.addCol(4, 140)

    # Create the top rows
    # ---------------------
    exRow = ws.addRow(1, height=15)
    exRow.addCell(2, 'Semantic Type Report', style=headerStyle, mergeAcross=1)

    sTmp = "Semantic Type : %s" % title
    exRow = ws.addRow(2, height=15)
    exRow.addCell(2, sTmp, style=headerStyle, mergeAcross=1)

    sTmp = "Total Number of Trials: %d" % numDocs
    exRow = ws.addRow(3, height=15)
    exRow.addCell(2, sTmp, style=headerStyle, mergeAcross=1)

    # Create the Header row
    # ---------------------
    exRow = ws.addRow(5, style=columnTitleStyle, height=15)
    exRow.addCell(1, 'CDR-ID')
    exRow.addCell(2, 'Title')
    exRow.addCell(3, 'Term(s)')
    exRow.addCell(4, 'Current Protocol Status')

    # Write the data
    # ---------------------
    rowNum = 5
    for doc in documents:
        if doc.docType == protocolType.docType:
            rowNum += 1
            rowHeight = 45
            # if there are more than 3 terms,
            # set the row height based on the number of terms
            if len(doc.terms) > 3:
                rowHeight = 14 * len(doc.terms)
            exRow = ws.addRow(rowNum, style=dataStyle, height=rowHeight)
            exRow.addCell(1, doc.id, style=dataStyle)
            exRow.addCell(2, doc.title, style=dataStyle)
            strTerm=""
            for term in doc.terms:
                if len(strTerm) > 0:
                    strTerm += '\n'
                strTerm += term
            exRow.addCell(3, strTerm, style=dataStyle)
            exRow.addCell(4, doc.status, style=dataStyle)

print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=SemanticTypeReport-%s.xls" % t
print

wb.write(sys.stdout, asXls=True, big=True)
