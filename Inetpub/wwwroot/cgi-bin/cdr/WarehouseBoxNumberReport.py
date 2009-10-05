import cgi, cdr, cdrcgi, cdrdb, re, sys

#----------------------------------------------------------------------
# Dynamically create the title of the menu section (request #809).
#----------------------------------------------------------------------
def getSectionTitle():
    return "Warehouse Box Number Report"

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "Warehouse Box Number Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Warehouse Box Number Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, getSectionTitle(),
                         "WarehouseBoxNumberReport.py", buttons, method = 'GET')
warehouseBoxNumber    = fields.getvalue("WarehouseBoxNumber") or None
#warehouseBoxNumber = "726"

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
# If we have no request, put up the request form.
#----------------------------------------------------------------------
if not warehouseBoxNumber:
    form = """\
  <input type='hidden' name='%s' value='%s'>
  <table>
   <tr>
    <td align='right'>Warehouse Box Number:&nbsp;</td>
    <td><input size='20' name='WarehouseBoxNumber'></td>
   </tr>
  </table>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")

#----------------------------------------------------------------------
# Class for storing the document information
#----------------------------------------------------------------------
class Document:
    def __init__(self, id, docTitle):
        self.id = id
        self.title = docTitle
        #splitDocTitle = docTitle.split(";")
        #self.title = splitDocTitle[len(splitDocTitle)-1]

documents = {}

def DrawDocumentRow(doc):
    sRow = "<tr><td>&nbsp;%s&nbsp;</td><td>&nbsp;%s&nbsp;</td>" % (doc.id,doc.title)
    return sRow

def DrawDocumentRows(documents):
    sRows = """<table border = 1><th width = 10%>Doc ID</th><th>Protocol Title</th>"""
    
    keys = documents.keys()
    keys.sort(lambda a,b: cmp(documents[a].id, documents[b].id))
    for key in keys:
        doc = documents[key]
        sRows += DrawDocumentRow(doc)
    sRows += "</table>"
    return sRows

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Fetch the documents for the given Warehouse Box Number
#----------------------------------------------------------------------
#sQuery = """
#SELECT d.id, d.title 
#FROM query_term q
#JOIN document d
#ON d.id = q.doc_id
#WHERE q.path = '/InScopeProtocol/RelatedDocuments/WarehouseBoxNumber'
#and d.active_status = 'A'
#and q.int_val = %s
#and q.doc_id in (select doc_id from query_term where
#path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
#and value ='Active')
#""" % warehouseBoxNumber

sQuery = """
SELECT d.id, d.title 
FROM query_term q
JOIN document d
ON d.id = q.doc_id
WHERE q.path = '/InScopeProtocol/RelatedDocuments/WarehouseBoxNumber'
and q.int_val = %s
""" % warehouseBoxNumber

try:
    cursor.execute(sQuery)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])
for id, docTitle in rows:
    if id not in documents:
        documents[id] = Document(id,docTitle)

#----------------------------------------------------------------------
# Create the Report
#----------------------------------------------------------------------

buttons  = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, getSectionTitle(),
            "WarehouseBoxNumberReport.py", buttons, method = 'GET')

if not len(documents):
    #sQuery = """
    #SELECT distinct(int_val) 
    #FROM query_term q
    #WHERE q.path = '/InScopeProtocol/RelatedDocuments/WarehouseBoxNumber'
    #and q.doc_id in (select doc_id from query_term where
    #path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
    #and value ='Active')
    #order by int_val
    #"""
    
    sQuery = """
    SELECT distinct(int_val) 
    FROM query_term q
    WHERE q.path = '/InScopeProtocol/RelatedDocuments/WarehouseBoxNumber'
    order by int_val
    """
    try:
        cursor.execute(sQuery)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database connection failure: %s' % info[1][0])

    sId = "<table border =1><th>Allowable Warehouse Box Numbers<th>"
    for id in rows:
        sId += "<tr><td>%s</td></tr>" % id[0]
    sId += "<table>"
    
    form = """\
      <input type='hidden' name='%s' value='%s'>
      <tb>%s is not a valid Warehouse Box Number</tb><br><br>
      Use one of these values:<br>
      %s
    """ % (cdrcgi.SESSION, session,warehouseBoxNumber,sId)

else:    
    form = """\
      <input type='hidden' name='%s' value='%s'>
      <table border=1>
       <tr>
        <td align='right'>&nbsp;Warehouse Box Number:&nbsp;</td>
        <td align='left'>&nbsp;%s&nbsp;</td>
       </tr>
       <tr>
        <td align='right'>&nbsp;Total Number of Trials:&nbsp;</td>
        <td align='left'>&nbsp;%s&nbsp;</td>
       </tr>
      </table><br>
      %s
    """ % (cdrcgi.SESSION, session,warehouseBoxNumber,len(documents),DrawDocumentRows(documents))

cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")
                    