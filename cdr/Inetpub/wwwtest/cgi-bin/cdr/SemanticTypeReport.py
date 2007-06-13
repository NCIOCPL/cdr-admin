import cgi, cdr, cdrcgi, cdrdb, re, sys, pyXLWriter, time

#----------------------------------------------------------------------
# Dynamically create the title of the menu section (request #809).
#----------------------------------------------------------------------
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
    def __init__(self, id, title,status):
        self.id = "CDR%010d" % id
        self.title = title
        self.status = status
        
documents = {}

#----------------------------------------------------------------------
# Get the documents
#----------------------------------------------------------------------
sQuery="""select distinct(d.id), d.title, status.value
FROM Document d
JOIN query_term status
ON status.doc_id = d.id
JOIN query_term q
ON q.doc_id = d.id
WHERE q.path = '/InScopeProtocol/Eligibility/Diagnosis/@cdr:ref' and
status.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus' and
d.active_status = 'A' and
q.int_val in
(select d.id
FROM document d
JOIN query_term semantic
ON d.id = semantic.doc_id
WHERE semantic.path = '/Term/SemanticType/@cdr:ref' 
and semantic.int_val = %s)
""" % semanticType

try:
    cursor.execute(sQuery)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])
for id, title, status in rows:
    if id not in documents:
        documents[id] = Documents(id,title,status)

#----------------------------------------------------------------------
# Write the excel file
#----------------------------------------------------------------------
def fix(name):
    return (name.replace(u'\u2120', u'(SM)')
                .replace(u'\u2122', u'(TM)')
                .encode('latin-1', 'ignore'))
title = semanticTypes[int(semanticType)].title
t = time.strftime("%Y%m%d%H%M%S")
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=SemanticTypeReport-%s.xls" % t
print
workbook = pyXLWriter.Writer(sys.stdout)

sTmpTitle = title[:31]
worksheet = workbook.add_worksheet(fix(sTmpTitle.replace("/","-")))

format = workbook.add_format()
format.set_bold();
format.set_color('white')
format.set_bg_color('blue')
format.set_align('center')
format.set_text_wrap(wrap=1);

worksheet.set_column(0, 15)
worksheet.set_column(1, 80)
worksheet.set_column(2, 20)
worksheet.write([0, 1], "Semantic Type Report", format)
sTmp = "Semantic Type : %s" % title
worksheet.write([1, 1], sTmp, format)
sTmp = "Total Number of Trials: %d" % len(documents)
worksheet.write([2, 1], sTmp, format)
row = 5
worksheet.write([row, 0], "CDR ID", format)
worksheet.write([row, 1], "Title", format)
worksheet.write([row, 2], "Current Protocol Status", format)
row += 1

keys = documents.keys()
keys.sort(lambda a,b: cmp(documents[a].id, documents[b].id))
format = workbook.add_format()
format.set_text_wrap(wrap=1);
for key in keys:
    doc = documents[key]
    worksheet.write([row, 0], doc.id,format)
    worksheet.write_string([row, 1], fix(doc.title),format)
    worksheet.write_string([row, 2], fix(doc.status),format)
    row += 1
workbook.close()