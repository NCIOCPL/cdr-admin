import cgi, cdr, cdrcgi, cdrdb, re, sys, time

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "CDR QC Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None #'2002-01-01'
toDate   = fields and fields.getvalue('ToDate')   or None #'2006-06-01'
drug   = fields and fields.getlist("Drug") or []
drugReferenceType = fields and fields.getvalue("DrugReferenceType") or 'NCI'
selectByType = fields and fields.getvalue("SelectByType") or 'Drug'
title    = "CDR Administration"
section  = "QC Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, "Drug Description Report",
                         "DrugDescriptionReport.py", buttons, method = 'GET')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)
elif action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

class DrugInfo:
    def __init__(self, id, docTitle, version, description, summary):
        self.id = id
        self.name = docTitle
        self.version = version
        self.description = description
        self.summary = summary
        delim = docTitle.find(';')
        if delim != -1:
            self.name = docTitle[:delim]
        delim = self.name.find('(')
        if delim != -1:
            self.name = self.name[:delim]
        self.name = self.name.strip()

def buildIndividualDrugTable(id,name,description,summary):
    html = "<table>"
    html += "<tr>"
    html += "<td width = 10%></td>"
    html += "<td width = 10%><h3>CDRID</h3></td>"
    html += """<td><h4>%s</h4></td>""" %id
    html += "<td width = 10%></td>"
    html += "</tr>"
    
    html += "<tr>"
    html += "<td></td>"
    html += "<td><h3>Drug Name</h3></td>"
    html += """<td><h4>%s</h4></td>""" % name
    html += "<td></td>"
    html += "</tr>"

    html += "<tr></tr>"

    html += "<tr>"
    html += "<td></td>"
    html += "<td><h3>Description</h3></td>"
    html += """<td><h4>%s</h4></td>""" % description
    html += "<td></td>"
    html += "</tr>"

    html += "<tr></tr>"

    html += "<tr>"
    html += "<td></td>"
    html += "<td><h3>Summary</h3></td>"
    html += """<td><h4>%s</h4></td>""" % summary
    html += "<td></td>"
    html += "</tr>"    

    html += "</table>"

    return html;    
    
def MakeDrugDescriptions(drugInfo):
    keys = drugInfo.keys()
    html=""
    keys.sort(lambda a,b: cmp(drugInfo[a].name, drugInfo[b].name))
    for key in keys:
        drug = drugInfo[key]
        html += buildIndividualDrugTable(drug.id,drug.name,drug.description,drug.summary)
        html += "<br><hr width=80% align=center /><br>"

    return html;
    
if action == "Submit":
    filters = {'DrugInformationSummary':["set:QC DrugInfoSummary Set"]}
    sIn = ""
    sReference = ""
    sDate = ""
    if selectByType == 'Drug':
        if not drug or 'All' in drug:
            sIn = ""
        else:
            sIn = " and d.id in ("
            for dr in drug:
                sIn += dr + ","
            sIn = sIn[0:len(sIn)-1]
            sIn += ") "
    elif selectByType == 'Date':
        sDate = """HAVING MAX(a.dt) BETWEEN '%s' AND '%s'""" % (fromDate,toDate)
    else:
        sReference = """ AND d.id in (select doc_id from query_term
        where path = '/DrugInformationSummary/DrugReference/DrugReferenceType' and value = '%s')""" % drugReferenceType

    sQuery = """SELECT d.id, d.title, MAX(v.num)
 FROM document d 
 JOIN doc_version v 
 ON v.id = d.id 
 JOIN doc_type t 
 ON t.id = d.doc_type 
 JOIN audit_trail a 
 ON a.document = d.id 
 WHERE t.name = 'DrugInformationSummary' 
 %s 
 %s 
 GROUP BY d.id, d.title 
 %s
 ORDER BY d.title""" % (sReference,sIn,sDate)

    try:
        cursor.execute(sQuery)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

    #filterParm = [['insRevLevels', 'publish|approved|proposed']]
    drugInfo={}
    for id, docTitle, docVerNum in rows:
        if id not in drugInfo:
            drugInfo[id] = DrugInfo(id,docTitle,docVerNum,"","")

    keys = drugInfo.keys()
    for key in keys:
        drugInf = drugInfo[key]
        sQuery = """SELECT d.xml
FROM document d
JOIN doc_version v 
ON v.id = d.id
WHERE v.num = %s
AND d.id = %s
        """ % (drugInf.version,drugInf.id)
        try:
            cursor.execute(sQuery)
            rows = cursor.fetchall()
        except cdrdb.Error, info:
            cdrcgi.bail("Failure retrieving document XML: %s" % info[1][0])

        for xml in rows:
            s = "%s" % xml
            splitTxt = s.split("<Description>");
            splitTxt2 = splitTxt[1].split("</Description>");
            drugInf.description = splitTxt2[0]

            splitTxt = s.split("<SummarySection");
            iCnt = 0
            s = splitTxt[1]
            for c in s:
                if c == '>':
                    s = s[iCnt+1:len(s)]
                    break
                else:
                    iCnt = iCnt + 1
                    
            splitTxt = s.split("</SummarySection>");
            s = splitTxt[0]
            s = s.replace("\\n","")
            s = s.replace("\\'","'")
            drugInf.summary = s
            drugInfo[key] = drugInf

    now = time.localtime(time.time())
    Date   = time.strftime("%m/%d/%y", now)

    form = """\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
<style type='text/css'>
   ul { margin-left: 20pt }
   h2 { font-size: 15pt; font-family:Arial; color:black; font-weight:bold}
   h3 { font-size: 13pt; font-family:Arial; color:black; font-weight:bold }
   h4 { font-size: 13pt; font-family:Arial; color:black }
   li, span.r, p, h4 
   { 
        font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:normal 
   }
   b, th 
   {  font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:bold 
   }
   .error { color: red; }
  </style>
<form>
<div align = 'center'>
<h2>Drug Description Report<br>%s</h2>
</div>
<div>
%s
</div>
</form>
""" % (cdrcgi.SESSION, session,Date,MakeDrugDescriptions(drugInfo))
    
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

class Drug:
    def __init__(self, id, docTitle):
        self.id = id
        self.name = docTitle
        delim = docTitle.find(';')
        if delim != -1:
            self.name = docTitle[:delim]
        delim = self.name.find('(')
        if delim != -1:
            self.name = self.name[:delim]
        self.name = self.name.strip()

drugs = {}

sQuery = """\
    SELECT d.id, d.title
  FROM document d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE t.name = 'DrugInformationSummary'
 ORDER BY d.title"""

try:
    cursor.execute(sQuery)
                                                
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])
    
for id, docTitle in rows:
    if id not in drugs:
        drugs[id] = Drug(id,docTitle)

#----------------------------------------------------------------------
# Generate a picklist for the PDQ Editorial Boards.
#----------------------------------------------------------------------
def makeDrugList(drugs):
    keys = drugs.keys()
    keys.sort(lambda a,b: cmp(drugs[a].name, drugs[b].name))
    html = u"""\
      <select id='Drug' name='Drug' style='width:600px' multiple size=12>
      <option value='All' selected=1>All Drugs   (Select this to report on all the below drugs)</option>
"""
    for key in keys:
        drug = drugs[key]
        html += """\
       <option value='%d'>%s &nbsp;</option>
""" % (drug.id, drug.name)
    return html + """\
      </select>
"""

#----------------------------------------------------------------------
# If we have a document type but no doc ID or title, ask for the title.
#----------------------------------------------------------------------

now         = time.localtime(time.time())
toDateNew   = time.strftime("%Y-%m-%d", now)
then        = list(now)
then[0]    -= 1
then        = time.localtime(time.mktime(then))
fromDateNew = time.strftime("%Y-%m-%d", then)
toDate      = toDate or toDateNew
fromDate    = fromDate or fromDateNew
style       = "style='width: 200px'"
drugStartDisplay = "none"
dateStartDisplay = "none"
typeStartDisplay = "none"
drugStartChecked = ""
dateStartChecked = ""
typeStartChecked = ""

if selectByType == 'Drug':
    drugStartDisplay = "block"
    drugStartChecked = "checked"
elif selectByType == 'Date':
    dateStartDisplay = "block"
    dateStartChecked = "checked"
else:
    typeStartDisplay = "block"
    typeStartChecked = "checked"

form = """\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <style type='text/css'>
   ul { margin-left: 20pt }
   h2 { font-size: 14pt; font-family:Arial; color:Navy }
   h3 { font-size: 13pt; font-family:Arial; color:black; font-weight:bold }
   h4 { font-size: 14pt; font-family:Arial; color:black }
   li, span.r, p, h4 
   { 
        font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:normal 
   }
   b, th 
   {  font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:bold 
   }
   .error { color: red; }
  </style>
  <script language='JavaScript'>

   function bodyLoad()
   {
       radioClicked('Drug')
   }
   
   function radioClicked(whichOne)
   {
       var elemDrugControls = document.getElementById('DrugControls');
       var elemDateControls = document.getElementById('DateControls');
       var elemTypeControls = document.getElementById('TypeControls');

       var elemDrugCheck = document.getElementById('DrugCheck');
       var elemDateCheck = document.getElementById('DateCheck');
       var elemTypeCheck = document.getElementById('TypeCheck');

       elemDrugControls.style.display = "none";
       elemDateControls.style.display = "none";
       elemTypeControls.style.display = "none";
       elemDrugCheck.checked=0
       elemDateCheck.checked=0
       elemTypeCheck.checked=1
       
       if (whichOne == 'Drug')
       {
           elemDrugControls.style.display = "block";
           elemDrugCheck.checked=1
       }
       else if (whichOne == 'Date')
       {
           elemDateControls.style.display = "block";
           elemDateCheck.checked=1
       }
       else
       {
           elemTypeControls.style.display = "block";
           elemTypeCheck.checked=1
       }
   }
       
  </script>
  <form>
  <p>
     Select how you want to filter for drugs: 
     </p>
     <h4>
    <input type="radio" name="SelectByType" id="DrugCheck" value="Drug" %s onClick="radioClicked('Drug')">By Drug Name</input><br>
    <input type="radio" name="SelectByType" id="DateCheck" value="Date" %s onClick="radioClicked('Date')">By Date of Last Published Version</input><br>
    <input type="radio" name="SelectByType" id="TypeCheck" value="ReferenceType" %s onClick="radioClicked('ReferenceType')">By Drug Reference Type</input><br>
    </h4>
    <div id = 'DrugControls' display='%s'><br><br>
     <p>
     Select the Drug(s) from the list below. Use Ctrl+'Click' to select more than one. 
     </p>
     %s
     <br>
     <br>
     <br>
     </div>
     <div id = 'DateControls' style="display:%s"><br><br>
     <p>
     Select The Date Range of the Last Published Version: 
     </p>
     <TABLE BORDER='0'>
    <TR>
     <TD ALIGN='right'><B>On or After Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='%s' %s></td>
     <td>
         (use format YYYY-MM-DD for dates, e.g. 2002-01-01)</TD>
        </td>
    </TR>
    <TR>
     <TD ALIGN='right'><B>On or Before Date:&nbsp;</B></TD>
     <TD><INPUT NAME='ToDate' VALUE='%s' %s>&nbsp;</TD>
    </TR></TABLE>
    <br>
    </div>
    <div id = 'TypeControls' style="display:%s"><br><br>
    <p>
     Select The Drug Reference Type:
     </p>
     <h4>
    <input type="radio" name="DrugReferenceType" value="NCI" checked=1 id="NCIRadio">NCI</input><br>
    <input type="radio" name="DrugReferenceType" value="FDA" id="FDARadio">FDA</input><br>
    <input type="radio" name="DrugReferenceType" value="NLM" id="NLMRadio">NLM</input><br>
    </h4>
    </div>
    </form>
""" % (cdrcgi.SESSION, session,drugStartChecked,dateStartChecked,typeStartChecked,drugStartDisplay,makeDrugList(drugs),dateStartDisplay,fromDate, style, toDate, style, typeStartDisplay)
header = header.replace("<BODY BGCOLOR='EEEEEE'>","<BODY BGCOLOR='EEEEEE' onLoad='bodyLoad()'>")
cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")    

