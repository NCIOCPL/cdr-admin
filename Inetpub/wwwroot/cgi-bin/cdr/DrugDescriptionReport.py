#----------------------------------------------------------------------
#
# $Id$
#
# Report to display DrugInfoSummaries
#
# BZIssue::5264 - [DIS] Formatting Changes to Drug Description Report
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, sys, time, xml.dom.minidom

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "CDR QC Report"
fields   = cgi.FieldStorage() or \
                            cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or \
                            cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None #'2002-01-01'
toDate   = fields and fields.getvalue('ToDate')   or None #'2006-06-01'
drug     = fields and fields.getlist("Drug") or []
drugReferenceType = fields and fields.getvalue("DrugReferenceType") or 'NCI'
selectByType = fields and fields.getvalue("SelectByType") or 'Drug'
title    = "CDR Administration"
instr    = "Drug Description Report"
script   = "DrugDescriptionReport.py"
section  = "QC Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
if action == "Submit":
    buttons  = ["Back",SUBMENU, cdrcgi.MAINMENU, "Log Out"]

header   = cdrcgi.header(title, title, instr, script, 
                         buttons, method = 'GET')
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

# -----------------------------------------------------------------
# Building the HTML output. Each DIS is displayed within a table
# with four columns (left and right column for spacing only)
# -----------------------------------------------------------------
def buildIndividualDrugTable(id, name, description, summary):
    html = u"""
  <table>
   <tr>
    <td width=10%%></td>
    <td class='label' width=10%%>CDR-ID</td>
    <td class='info' valign='top'>
      <a href="/cgi-bin/cdr/QcReport.py?Session=guest&DocId=%s">
      %s
      </a>
    </td>
    <td width=10%%></td>
   </tr>
""" % (id, id)
    
    html += u"""\
   <tr>
    <td></td>
    <td class='label' valign='top'>Drug Name</td>
    <td class='info' valign='top'>
     %s
    </td>
    <td></td>
   </tr>
""" % name

    html += u"""\
   <tr>
    <td></td>
    <td class='label' valign='top'>Description</td>
    <td class='info' valign='top'>
     %s
    </td>
    <td></td>
   </tr>
""" % description

    html += u"""\
   <tr>
    <td></td>
    <td class='label' valign='top'>Summary</td>
    <td class='info' valign='top'>
     %s
    </td>
    <td></td>
   </tr>
  </table>
""" % summary.decode('utf-8')

    return html;    
    

# --------------------------------------------------------------------
#
# --------------------------------------------------------------------
def MakeDrugDescriptions(drugInfo):
    keys = drugInfo.keys()
    html=""
    keys.sort(lambda a,b: cmp(drugInfo[a].name, drugInfo[b].name))
    for key in keys:
        drug = drugInfo[key]
        html += buildIndividualDrugTable(drug.id, drug.name, drug.description,
                                         drug.summary)

        # Separator for the individual documents
        html += """\
    <br>
     <hr width=80% align=center/>
    <br>"""

    return html;


# --------------------------------------------------------------------
#
# --------------------------------------------------------------------
def VerifyDate(fieldName,date):
    dateSplit = date.split("-")
    if  len(dateSplit) is not 3:
        cdrcgi.bail('invalid %s<br><br>Make sure format is YYYY-MM-DD' % 
                                                                 fieldName)
    VerifyDateValue(fieldName,"Year",dateSplit[0],4,1900,2099)
    VerifyDateValue(fieldName,"Month",dateSplit[1],2,1,12)
    VerifyDateValue(fieldName,"Day",dateSplit[2],2,1,31)


# --------------------------------------------------------------------
#
# --------------------------------------------------------------------
def VerifyDateValue(fieldName,fieldItem,dateItem,length,minValue,maxValue):
    if not dateItem.isdigit():
        cdrcgi.bail('invalid %s<br><br>%s must not contains non numbers' % 
                                                (fieldName,fieldItem))
    if len(dateItem) is not length:
        cdrcgi.bail('invalid %s<br><br>%s must be %d numbers long' % 
                                                (fieldName,fieldItem,length))

    intVal = int(dateItem)
    if intVal < minValue:
        cdrcgi.bail('invalid %s<br><br>%s must be >= %d' % 
                                                (fieldName,fieldItem,minValue))
    if intVal > maxValue:
        cdrcgi.bail('invalid %s<br><br>%s must be <= %d' % 
                                                (fieldName,fieldItem,maxValue))

    return intVal


# --------------------------------------------------------------------
# --------------------------------------------------------------------
def getAllNodeText(node):
    s = ""
    if node.nodeName in ["Para"]:
        s += "<br><br>"
    if node.nodeType == node.TEXT_NODE:
        if node.parentNode.nodeName not in ["Deletion"]:
            s += node.data
    for childNode in node.childNodes:
        s += getAllNodeText(childNode)
    s.strip()
    return s


# --------------------------------------------------------------------
# --------------------------------------------------------------------
def getAllSummaryText(node):
    s = ""
    if node.nodeName == "SummarySection":
        s += getAllNodeText(node)
    elif node.nodeName == "Insertion":
        for childNode in node.childNodes:
            s += getAllSummaryText(childNode)
    s.strip()
    return s

    
# --------------------------------------------------------------------
# --------------------------------------------------------------------
if action == "Submit":
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
        VerifyDate("On or After Date",fromDate)
        VerifyDate("On or Before Date",toDate)
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
                 ORDER BY d.title
""" % (sReference, sIn, sDate)

    try:
        cursor.execute(sQuery, timeout = 300)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

    #filterParm = [['insRevLevels', 'publish|approved|proposed']]
    drugInfo={}
    for id, docTitle, docVerNum in rows:
        if id not in drugInfo:
            drugInfo[id] = DrugInfo(id, docTitle, docVerNum, "", "")

    keys = drugInfo.keys()
    for key in keys:
        drugInf = drugInfo[key]
        sQuery = """SELECT d.xml
                      FROM document d
                      JOIN doc_version v 
                        ON v.id = d.id
                     WHERE v.num = %s
                       AND d.id = %s
""" % (drugInf.version, drugInf.id)
        try:
            cursor.execute(sQuery, timeout = 300)
            rows = cursor.fetchall()
        except cdrdb.Error, info:
            cdrcgi.bail("Failure retrieving document XML: %s" % info[1][0])

        dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))

        # Get the Description
        # -------------------
        element = dom.getElementsByTagName('Description')
        drugInf.description = getAllNodeText(element[0])

        # Get the Summary
        # ----------------
        mySummary = cdr.filterDoc('guest', ['name:Format DIS SummarySection'], 
                                  docId = drugInf.id)
        drugInf.summary = mySummary[0]
        ###cdrcgi.bail(u"%s" % mySummary[0].decode('utf-8'))
        ####
        #sSummary = ""
        #for node in dom.documentElement.childNodes:
        #    s = getAllSummaryText(node).strip()
        #    if len(sSummary) > 0 and len(s) > 0 and not sSummary.endswith("<br><br>"):
        #        sSummary += "<br><br>"
        #    sSummary += s
        #sSummary = sSummary.strip()
        #if sSummary.startswith("<br><br>"):
        #    sSummary = sSummary[8:len(sSummary)-1]
        #sSummary = sSummary.replace("<br><br><br><br>","<br><br>")
        #drugInf.summary = sSummary

    now = time.localtime(time.time())
    Date   = time.strftime("%b %d, %Y %I:%M%p", now)

    sDrug = ""
    for dr in drug:
        sDrug += "<INPUT TYPE='hidden' NAME='Drug' VALUE='" + dr + """'>
"""

    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='SelectByType' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='FromDate' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='ToDate' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='DrugReferenceType' VALUE='%s'>
  %s
  <style type='text/css'>
   ul { margin-left: 20pt }
   *.title  { font-size: 15pt; 
              font-family:Arial; 
              color:black;
              font-weight:bold }
   td.label { font-size: 11pt; 
              font-family:Arial; 
              color:black; 
              font-weight:bold }
   td.info  { font-size: 11pt; 
              font-family:Arial; 
              color:black }
   td       { font-size: 11pt; 
              font-family:Arial; 
              color:black }
   li, span.r, p, h4 
            { font-size: 11pt; 
              font-family:'Arial'; 
              color:black;
              margin-bottom: 10pt; 
              font-weight:normal }
   b, th 
   {  font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:bold 
   }
   .error { color: red; }
  </style>
<!-- form method='post' action='%s' -->
   <div align = 'center'>
    <span class='title'>Drug Description Report<br>%s</span>
   </div>
   <br/>
   <div>
   %s
   </div>
  </form>
""" % (cdrcgi.SESSION, session, selectByType, fromDate, toDate, 
       drugReferenceType, sDrug, script, Date, MakeDrugDescriptions(drugInfo))
    
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

# --------------------------------------------------------------------
# --------------------------------------------------------------------
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
    cursor.execute(sQuery, timeout = 300)
                                                
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
    if not drug or 'All' in drug:
        selected = "selected"
    else:
        selected=""
    
    html = u"""\
      <select id='Drug' name='Drug' style='width:450px' multiple size=12>
      <option value='All' %s>All Drugs   (Select this to report on all the below drugs)</option>
""" % selected

    for key in keys:
        thisDrug = drugs[key]
        sDrugId = "%s" % thisDrug.id        
        if sDrugId in drug:
            selected="selected"
        else:
            selected=""
        html += """\
       <option value='%d' %s>%s &nbsp;</option>
""" % (thisDrug.id, selected,thisDrug.name)
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
style       = "style='width: 100px'"
drugStartDisplay = "none"
dateStartDisplay = "none"
typeStartDisplay = "none"
drugStartChecked = ""
dateStartChecked = ""
typeStartChecked = ""
nciChecked = ""
nlmChecked = ""
fdaChecked = ""

if selectByType == 'Drug':
    drugStartDisplay = "block"
    drugStartChecked = "checked"
elif selectByType == 'Date':
    dateStartDisplay = "block"
    dateStartChecked = "checked"
else:
    typeStartDisplay = "block"
    typeStartChecked = "checked"

if drugReferenceType == "NCI":
    nciChecked = "checked"
elif drugReferenceType == "NLM":
    nlmChecked = "checked"
else:
    fdaChecked = "checked"

# Setting up the form to pick the report type
# --------------------------------------------
form = """\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <style type='text/css'>
   label, b, td
   {  font-size: 11pt; 
      font-family:'Arial';
   }
   *.usage
   {  font-size: 10pt; 
      font-family:'Arial';
   }
  </style>

  <script language='JavaScript'>
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

  <form method='post' action='%s'>
   <fieldset>
    <legend>&nbsp;Select how to filter for drugs&nbsp;</legend>
     <input type="radio" name="SelectByType" id="DrugCheck" 
            value="Drug" %s onClick="radioClicked('Drug')">
     <label for="DrugCheck">By Drug Name</label>
     <br>
     <input type="radio" name="SelectByType" id="DateCheck" 
            value="Date" %s onClick="radioClicked('Date')">
     <label for="DateCheck">By Date of Last Published Version</label>
     <br>
     <input type="radio" name="SelectByType" id="TypeCheck" 
            value="ReferenceType" %s onClick="radioClicked('ReferenceType')">
     <label for="TypeCheck">By Drug Reference Type</label>
   </fieldset>
   <br>
""" % (cdrcgi.SESSION, session, script, 
       drugStartChecked, dateStartChecked, typeStartChecked)
   
form += """\
   <div id='DrugControls' style="display:%s">
    <fieldset>
     <legend>&nbsp;Select Drugs&nbsp;</legend>
     <span class='usage'>Use Ctrl+'Click' to select more than one.</span>
     %s
     <br>
    </fieldset>
   </div>
""" % (drugStartDisplay, makeDrugList(drugs)) 

form += """\
   <div id='DateControls' style="display:%s">
    <fieldset>
     <legend>&nbsp;Select Date Range of last pub version&nbsp;</legend>
     <TABLE BORDER='0' style='float:left'>
      <TR>
       <TD ALIGN='right'>On or After Date:&nbsp;</TD>
       <TD><INPUT NAME='FromDate' VALUE='%s' %s></td>
      </TR>
      <TR>
       <TD ALIGN='right'>On or Before Date:&nbsp;</TD>
       <TD><INPUT NAME='ToDate' VALUE='%s' %s>&nbsp;</TD>
      </TR>
     </TABLE>
     <span class='usage'>Use format YYYY-MM-DD for dates, e.g. 2002-01-01</span>

    </fieldset>
   </div>
""" % (dateStartDisplay, fromDate, style, toDate, style)

form += """\
   <div id='TypeControls' style="display:%s">
    <fieldset>
     <legend>&nbsp;Select Drug Reference Type&nbsp;</legend>
      <input type="radio" name="DrugReferenceType" 
             value="NCI" %s id="NCIRadio">
      <label for="NCIRadio">NCI</label>
      <br>
      <input type="radio" name="DrugReferenceType" 
             value="FDA" %s id="FDARadio">
      <label for="FDARadio">FDA</label>
      <br>
      <input type="radio" name="DrugReferenceType" 
             value="NLM" %s id="NLMRadio">
      <label for="NLMRadio">NLM</label>
    </fieldset>
   </div>
  </form>
""" % (typeStartDisplay, nciChecked, fdaChecked, nlmChecked)

cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")    
