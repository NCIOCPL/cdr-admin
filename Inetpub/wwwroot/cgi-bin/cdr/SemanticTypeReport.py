import cgi, cdr, cdrcgi, cdrdb, re, sys, time, ExcelWriter

def getSectionTitle():
    return "Semantic Type Report"

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "Semantic Type Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Semantic Type Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, getSectionTitle(),
                         "SemanticTypeReport.py", buttons, method = 'GET')
semanticType    = fields.getvalue("SemanticType") or None

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Class for storing protocolTypes
#----------------------------------------------------------------------
class ProtocolType:
    def __init__(self, docType,title,statusTerm):
        self.docType = docType
        self.title = title
        self.statusTerm = statusTerm

#----------------------------------------------------------------------
# Populate the protocolTypes
#----------------------------------------------------------------------
protocolTypes = {}
protocolTypes[18] = ProtocolType(18,'InScopeProtocol','/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus')
protocolTypes[34] = ProtocolType(34,'CTGovProtocol','/CTGovProtocol/OverallStatus')

#----------------------------------------------------------------------
# Class for storing the document information
#----------------------------------------------------------------------
class SemanticType:
    def __init__(self, id, title):
        self.id = id
        self.title = title
        splitTitle = title.split(";")
        self.title = splitTitle[0]

semanticTypes = {}

#----------------------------------------------------------------------
# Make the list of semantic types
#----------------------------------------------------------------------
def makeSemanticTypeList(semanticTypes):
    keys = semanticTypes.keys()
    keys.sort(lambda a,b: cmp(semanticTypes[a].title, semanticTypes[b].title))
    html = u"""\
      <select id='SemanticType' name='SemanticType' style='width:500px'
              onchange='semanticTypeChange();'>
       <option value='' selected='1'>Choose One</option>
"""
    for key in keys:
        semanticType = semanticTypes[key]
        html += """\
       <option value='%d'>%s &nbsp;</option>
""" % (semanticType.id, semanticType.title)
    return html + """\
      </select>
"""    

#----------------------------------------------------------------------
# Get the SemanticTypes
#----------------------------------------------------------------------
sQuery ="""SELECT distinct(q.int_val), d.title 
    FROM document d 
    JOIN query_term q
    ON q.int_val = d.id
    WHERE q.path = '/Term/SemanticType/@cdr:ref'
    """

try:
    cursor.execute(sQuery)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])
for id, title in rows:
    if id not in semanticTypes:
        semanticTypes[id] = SemanticType(id,title)

#----------------------------------------------------------------------
# If we have no request, put up the request form.
#----------------------------------------------------------------------
if not semanticType:    
    form = """\
  <input type='hidden' name='%s' value='%s'>
  <table>
   <tr>
    <td align='right'>Semantic Type:&nbsp;</td>
    <td>%s</td>
   </tr>
  </table>
    """ % (cdrcgi.SESSION, session,makeSemanticTypeList(semanticTypes))
      
    cdrcgi.sendPage(header + form + """\
     </body>
    </html>
    """)

class Documents:
    def __init__(self, id, title,status,docType):
        self.id = "CDR%010d" % id
        self.title = title
        self.status = status
        self.docType = docType
        self.terms = []
        
documents = {}

#----------------------------------------------------------------------
# Get the documents
#----------------------------------------------------------------------
keys = protocolTypes.keys()
for key in keys:
    protocolType = protocolTypes[key]
    sQuery="""\
    SELECT d.id, d.title, status.value, term.value
      FROM document d
      JOIN query_term status
        ON status.doc_id = d.id
      JOIN query_term q
        ON q.doc_id = d.id
      JOIN query_term term
        ON term.doc_id = q.int_val
     WHERE q.path LIKE '/%s/%%/@cdr:ref'
       AND status.path = '%s'
       AND d.active_status = 'A'
       AND term.path = '/Term/PreferredName'
       AND q.int_val IN (SELECT doc_id
                           FROM query_term
                          WHERE path = '/Term/SemanticType/@cdr:ref' 
                            AND int_val = %s)
 ORDER BY d.id, term.value
    """ % (protocolType.title,protocolType.statusTerm,semanticType)

    try:
        cursor.execute(sQuery, timeout=300)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    for id, title, status, term in rows:
        if id not in documents:
            documents[id] = Documents(id,title,status,protocolType.docType)
        doc = documents[id]
        doc.terms.append(term)

#----------------------------------------------------------------------
# Write the excel file
#----------------------------------------------------------------------
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

title = semanticTypes[int(semanticType)].title
t = time.strftime("%Y%m%d%H%M%S")

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
wb      = ExcelWriter.Workbook()
b       = ExcelWriter.Border()
borders = ExcelWriter.Borders(b, b, b, b)

dataFont    = ExcelWriter.Font(name = 'Arial', size = 10)
dataAlign   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
dataStyle  = wb.addStyle(alignment = dataAlign, font = dataFont)

headerFont    = ExcelWriter.Font(name = 'Arial', size = 10, color="#FFFFFF", bold = True)
headerInterior     = ExcelWriter.Interior("#0000FF", "Solid")
headerAlign   = ExcelWriter.Alignment('Center', 'Top', wrap = True)
headerStyle  = wb.addStyle(alignment = headerAlign, font = headerFont, interior=headerInterior)

columnTitleFont    = ExcelWriter.Font(name = 'Arial', size = 10, color="#FFFFFF", bold = True)
columnTitleInterior     = ExcelWriter.Interior("#000088", "Solid")
columnTitleAlign   = ExcelWriter.Alignment('Center', 'Top', wrap = True)
columnTitleStyle  = wb.addStyle(alignment = columnTitleAlign, font = columnTitleFont,interior=columnTitleInterior)

protKeys = protocolTypes.keys()
for protKey in protKeys:
    protocolType = protocolTypes[protKey]
    
    sTmp = protocolType.title[:31]
    ws = wb.addWorksheet(sTmp.replace('/','-'), style=dataStyle, height=45, frozenRows = 5)
    
    numDocs = 0
    # Determine the width of column 3
    #---------------------------------
    colThreeWidth = 220
    charWidth = 4.5
    keys = documents.keys()
    for key in keys:
        doc = documents[key]
        if ( doc.docType == protocolType.docType ):
            numDocs += 1
            for term in doc.terms:
                if colThreeWidth < charWidth*len(term):
                    colThreeWidth = charWidth*len(term)
        
    # Set the colum width
    # -------------------
    ws.addCol( 1, 100)
    ws.addCol( 2, 450)
    ws.addCol( 3, colThreeWidth)
    ws.addCol( 4, 140)

    # Create the top rows
    # ---------------------
    exRow = ws.addRow(1,height=15)
    exRow.addCell(2, 'Semantic Type Report', style = headerStyle, mergeAcross=1)

    sTmp = "Semantic Type : %s" % title
    exRow = ws.addRow(2,height=15)
    exRow.addCell(2, sTmp, style = headerStyle, mergeAcross=1)

    sTmp = "Total Number of Trials: %d" % numDocs
    exRow = ws.addRow(3,height=15)
    exRow.addCell(2, sTmp, style = headerStyle, mergeAcross=1)

    # Create the Header row
    # ---------------------
    exRow = ws.addRow(5, style=columnTitleStyle,height=15)
    exRow.addCell(1, 'CDR-ID')
    exRow.addCell(2, 'Title')
    exRow.addCell(3, 'Term(s)')
    exRow.addCell(4, 'Current Protocol Status')

    # Write the data
    # ---------------------
    rowNum = 5
    keys = documents.keys()
    #sort by status,id
    keys.sort(lambda a,b: cmp(documents[a].status, documents[b].status) or cmp(documents[a].id, documents[b].id))
    for key in keys:
        doc = documents[key]
        if ( doc.docType == protocolType.docType ):
            rowNum += 1
            rowHeight = 45
            # if there are more than 3 terms,
            # set the row height based on the number of terms
            if len(doc.terms) > 3:
                rowHeight = 14 * len(doc.terms)
            exRow = ws.addRow(rowNum, style = dataStyle,height=rowHeight)
            exRow.addCell(1, doc.id, style = dataStyle)
            exRow.addCell(2, doc.title, style = dataStyle)
            strTerm=""
            for term in doc.terms:
                if len(strTerm) > 0:
                    strTerm += '\n'
                strTerm += term
            exRow.addCell(3, strTerm, style = dataStyle)
            exRow.addCell(4, doc.status, style = dataStyle)

print "Content-type: application/vnd.ms-excel"                                  
print "Content-Disposition: attachment; filename=SemanticTypeReport-%s.xls" % t    
print                

wb.write(sys.stdout, asXls = True, big = True)