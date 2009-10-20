#----------------------------------------------------------------------
#
# $Id$
#
# Protocol Status Change Report
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2003/11/05 14:49:54  bkline
# Enhancements requested in issue #918.
#
# Revision 1.3  2003/03/19 19:46:10  bkline
# Added new column for protocol status (enhancement request #647).
#
# Revision 1.2  2003/02/07 16:10:45  bkline
# Fix and enhancement requested by Bugzilla #542: changed subset name
# for Cancer.Gov publication to match Peter's new names; dropped rows
# for Organizations with no previous protocol status.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, time, xml.dom.minidom

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "Protocol Status Change Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("CGI Field Storage Not Found",
                                             repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "QC Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "ProtocolStatusChange.py"
header   = cdrcgi.header(title, title, repTitle, script, buttons,
                         method = 'GET')
docId    = fields.getvalue(cdrcgi.DOCID) or None
start    = fields.getvalue("start")      or None
end      = fields.getvalue("end")        or None
now      = time.localtime()
then     = list(now)
then[1] -= 1
then     = time.localtime(time.mktime(then))
if not start or not end:
    start = time.strftime("%Y-%m-%d", then)
    end   = time.strftime("%Y-%m-%d")

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
if not action:
    form = """\
  <input type='hidden' name='%s' value='%s'>
  <table>
   <tr>
    <td align='right'>Start Date:&nbsp;</td>
    <td><input size='20' name='start' value='%s'></td>
   </tr>
   <tr>
    <td align='right'>End Date:&nbsp;</td>
    <td><input size='20' name='end' value='%s'></td>
   </tr>
  </table>
""" % (cdrcgi.SESSION, session, start, end)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")

#----------------------------------------------------------------------
# Protocol + Lead Org combo.
#----------------------------------------------------------------------
class ProtLeadOrg:
    def __init__(self, protId, curStatus, entryDate, enteredBy, prevStatus,
                 published, protStatus, activeStatus, nctId):
        self.protId       = protId
        self.curStatus    = curStatus
        self.entryDate    = entryDate
        self.enteredBy    = enteredBy
        self.prevStatus   = prevStatus
        self.published    = published
        self.protStatus   = protStatus
        self.activeStatus = activeStatus
        self.nctId        = nctId

def extractNctId(dom):
    for node in dom.documentElement.childNodes:
        if node.nodeName == "ProtocolIDs":
            for child in node.childNodes:
                if child.nodeName == "OtherID":
                    idType = None
                    idValue = None
                    for grandchild in child.childNodes:
                        if grandchild.nodeName == "IDType":
                            idType = cdr.getTextContent(grandchild)
                        elif grandchild.nodeName == "IDString":
                            idValue = cdr.getTextContent(grandchild)
                    if idType == "ClinicalTrials.gov ID":
                        return idValue
    return None

#----------------------------------------------------------------------
# If this is a lead org which is in scope (that is, the entry date
# for recording the current status falls in the date range represented
# by start and end) then return a ProtLeadOrg object for it.  Otherwise
# return None.
#----------------------------------------------------------------------
def extractProtLeadOrg(node, start, end, published, protStatus, activeStatus,
                       nctId):
    protId     = None
    prevStatus = None
    curStatus  = None
    entryDate  = None
    enteredBy  = None
    prevDate   = None
    for child in node.childNodes:
        if child.nodeName == "LeadOrgProtocolID":
            if not protId:
                protId = cdr.getTextContent(child)
        elif child.nodeName == "LeadOrgProtocolStatuses":
            for grandchild in child.childNodes:
                if grandchild.nodeName == "CurrentOrgStatus":
                    for greatgrandchild in grandchild.childNodes:
                        if greatgrandchild.nodeName == "StatusName":
                            curStatus = cdr.getTextContent(greatgrandchild)
                        elif greatgrandchild.nodeName == "EnteredBy":
                            enteredBy = cdr.getTextContent(greatgrandchild)
                        elif greatgrandchild.nodeName == "EntryDate":
                            entryDate = cdr.getTextContent(greatgrandchild)
                elif grandchild.nodeName == "PreviousOrgStatus":
                    d = None
                    s = None
                    for greatgrandchild in grandchild.childNodes:
                        if greatgrandchild.nodeName == "StatusName":
                            s = cdr.getTextContent(greatgrandchild)
                        elif greatgrandchild.nodeName == "EntryDate":
                            d = cdr.getTextContent(greatgrandchild)
                    if d and s:
                        if not prevDate or d > prevDate:
                            prevDate = d
                            prevStatus = s
    if curStatus and entryDate and entryDate >= start and entryDate <= end:
        return ProtLeadOrg(protId, curStatus, entryDate, enteredBy, prevStatus,
                           published, protStatus, activeStatus, nctId)
    return None
    
#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    curs = conn.cursor()
except:
    cdrcgi.bail("Unable to connect to the CDR database")

#----------------------------------------------------------------------
# Find the protocols and lead orgs which belong in the report.
#----------------------------------------------------------------------
protLeadOrgs = {}
path = "/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg" \
       "/LeadOrgProtocolStatuses/CurrentOrgStatus/EntryDate"
try:
    conn.setAutoCommit(1)

    # Doing things this way to skirt lame bugs in ADO.
    curs.execute("CREATE TABLE #interesting_protocols(id INTEGER)")
    curs.execute("CREATE TABLE #published_subset(id INTEGER)")
    curs.execute("""\
            INSERT INTO #interesting_protocols (id)
        SELECT DISTINCT doc_id
                   FROM query_term
                  WHERE path = '%s'
                    AND value BETWEEN ? AND ?""" % path, (start, end))
    
    curs.execute("""\
            INSERT INTO #published_subset (id)
        SELECT DISTINCT ppd.doc_id
                   FROM pub_proc pp
                   JOIN pub_proc_doc ppd
                     ON ppd.pub_proc = pp.id
                   JOIN #interesting_protocols ip
                     ON ip.id = ppd.doc_id
                  WHERE pp.pub_subset LIKE 'Push_Documents_To_Cancer.Gov%'
                    AND pp.status = 'Success'
                    AND ppd.failure IS NULL""")
    curs.execute("""
          SELECT ip.id, ps.id, d.xml, d.active_status
            FROM #interesting_protocols ip
            JOIN document d
              ON d.id = ip.id
 LEFT OUTER JOIN #published_subset ps
              ON ps.id = d.id""")
    row = curs.fetchone()
    while row:
        id, pubId, doc, activeStatus = row
        #cdrcgi.bail("id is %d" % id)
        published = pubId and "Y" or "N"
        try:
            dom = xml.dom.minidom.parseString(doc.encode('utf-8'))
        except:
            cdrcgi.bail("Failure parsing CDR%010d" % id)
        statElems = dom.getElementsByTagName("CurrentProtocolStatus")
        protStat = ""
        if statElems:
            protStat = cdr.getTextContent(statElems[0])
        nctId = extractNctId(dom)
        for elem in dom.getElementsByTagName("ProtocolLeadOrg"):
            protLeadOrg = extractProtLeadOrg(elem, start, end, published,
                                             protStat, activeStatus, nctId)
            if protLeadOrg:
                #cdrcgi.bail("got one!")
                key = (protLeadOrg.protId, id)
                protLeadOrgs[key] = protLeadOrg
        row = curs.fetchone()
except:
    raise
    cdrcgi.bail("Database failure selecting protocol documents")

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
today = time.strftime("%B %d, %Y")
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Protocol Status Change Report - %s</title>
  <style type='text/css'>
   th,h2    { font-family: Arial, sans-serif; font-size: 11pt;
              text-align: center; font-weight: bold; }
   h1       { font-family: Arial, sans-serif; font-size: 12pt;
              text-align: center; font-weight: bold; }
   td       { font-family: Arial, sans-serif; font-size: 10pt; }
  </style>
 </head>
 <body>
  <h1>Protocol Status Change Report</h1>
  <h2>From %s To %s</h2>
  <br><br>
  <center>
  <table border='1' cellspacing='0' cellpadding='1'>
   <tr>
    <th>DocID</th>
    <th>Lead Org Protocol ID</th>
    <th>NCTID</th>
    <th>Previous Org Status</th>
    <th>Current Org Status</th>
    <th>Current Protocol Status</th>
    <th>Entry Date</th>
    <th>Any Pub?</th>
    <th>LastV Pub?</th>
    <th>Entered By</th>
   </tr>
""" % (today, start, end)

#----------------------------------------------------------------------
# Loop through the update persons, in surname order.
#----------------------------------------------------------------------
keys = protLeadOrgs.keys()
keys.sort()
for key in keys:
    protLeadOrg = protLeadOrgs[key]
    if protLeadOrg.prevStatus:
        docId = "CDR%d" % key[1]
        vers = cdr.lastVersions('guest', docId)
        if type(vers) in (type(''), type(u'')):
            lastVPub = vers
        elif vers[0] == -1:
            lastVPub = 'N/A'
        elif vers[0] == vers[1]:
            lastVPub = 'Y'
        else:
            lastVPub = 'N'
        if protLeadOrg.activeStatus != 'A':
            lastVPub += ' (B)'
        html += """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (docId,
       protLeadOrg.protId     or "&nbsp;",
       protLeadOrg.nctId      or "&nbsp;",
       protLeadOrg.prevStatus,
       protLeadOrg.curStatus  or "&nbsp;",
       protLeadOrg.protStatus or "&nbsp;",
       protLeadOrg.entryDate  or "&nbsp;",
       protLeadOrg.published,
       lastVPub,
       protLeadOrg.enteredBy  or "&nbsp;")

#----------------------------------------------------------------------
# Show the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + """\
  </table></center>
 </body>
</html>
""")
