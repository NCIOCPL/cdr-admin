#----------------------------------------------------------------------
#
# $Id: LeadOrgStatusAndParticipantMailerHistory.py,v 1.2 2003-12-18 01:25:25 bkline Exp $
#
# Reports on the history of S&P mailers for a particular protocol.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/11/10 18:06:58  bkline
# Reports on the history of S&P mailers for a particular protocol.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, re, string, time, cdr, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
docId      = fields and fields.getvalue('DocId')   or None
SUBMENU   = "Report Menu"
buttons   = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = "LeadOrgStatusAndParticipantMailerHistory.py"
title     = "CDR Administration"
section   = "Lead Organization Status and Participant Mailer History"
header    = cdrcgi.header(title, title, section, script, buttons)
now       = time.localtime()

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not docId:
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s' />
   <BR />
   <B>Lead Organization Document ID:&nbsp;&nbsp;</B>
   <INPUT NAME='DocId' />
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Extract the document ID as an integer.
#----------------------------------------------------------------------
try:
    digits = re.sub(r'[^\d]', '', docId)
    id     = string.atoi(digits)
except:
    cdrcgi.bail("Invalid document ID: %s, %s" % (docId, digits))

#----------------------------------------------------------------------
# Get the organization's name.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/Organization/OrganizationNameInformation'
                        + '/OfficialName/Name'
               AND doc_id = ?""", id)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("No such document CDR%010d" % id)
    orgName = rows[0][0]
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving organization name: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the S&P mailers for this organization; go back three years.
#----------------------------------------------------------------------
class MailerJob:
    def __init__(self, id, date):
        self.id             = id
        self.date           = date
        self.noResponse     = []
        self.respNoChange   = []
        self.respWithChange = []
mailerJobs = {}
pups = {}
then = list(now)
then[0] -= 3
threeYearsAgo = time.mktime(then)
threeYearsAgo = time.strftime("%Y-%m-%d", time.localtime(threeYearsAgo))
try:
    cursor.execute("""\
         SELECT mailer_job.int_val AS mailer_job_id,
                prot_id.int_val AS protocol_id,
                reply_date.value AS reply_date,
                change_type.value AS change_type,
                mailer_date.value AS mailer_date,
                pup_id.int_val AS pup_id,
                mailer_job.doc_id as mailer_id
           FROM query_term org_id
           JOIN query_term mailer_job
             ON mailer_job.doc_id = org_id.doc_id
            AND mailer_job.path = '/Mailer/JobId'
           JOIN query_term prot_id
             ON prot_id.doc_id = org_id.doc_id
            AND prot_id.path = '/Mailer/Document/@cdr:ref'
           JOIN query_term pup_id
             ON pup_id.doc_id = org_id.doc_id
            AND pup_id.path = '/Mailer/Recipient/@cdr:ref'
           JOIN query_term mailer_date
             ON mailer_date.doc_id = org_id.doc_id
            AND mailer_date.path = '/Mailer/Sent'
LEFT OUTER JOIN query_term reply_date
             ON reply_date.doc_id = org_id.doc_id
            AND reply_date.path = '/Mailer/Response/Received'
LEFT OUTER JOIN query_term change_type
             ON change_type.doc_id = org_id.doc_id
            AND change_type.path = '/Mailer/Response/ChangesCategory'
          WHERE org_id.int_val = ?
            AND org_id.path = '/Mailer/ProtocolOrg/@cdr:ref'
            AND mailer_date.value >= ?""", (id, threeYearsAgo), 300)
    for (mailerJobId, protocolId, replyDate, changeType, mailerDate,
         pupId, mailerId) in cursor.fetchall():
        if mailerJobs.has_key(mailerJobId):
            mailerJob = mailerJobs[mailerJobId]
        else:
            mailerJobs[mailerJobId] = mailerJob = MailerJob(mailerJobId,
                                                            mailerDate)
        if not replyDate:
            mailerJob.noResponse.append((protocolId, mailerId))
        elif not changeType or changeType == "None":
            mailerJob.respNoChange.append((protocolId, mailerId))
        else:
            mailerJob.respWithChange.append((protocolId, mailerId))
        pups[pupId] = 1
except Exception, info:
    cdrcgi.bail("Failure retrieving mailer history: %s" % str(info))
        
#----------------------------------------------------------------------
# Get the names of the update persons.
#----------------------------------------------------------------------
pupNames = []
for pupId in pups:
    try:
        cursor.execute("""\
            SELECT title
              FROM document
             WHERE id = ?""", pupId)
        title = cursor.fetchall()[0][0]
        semicolon = title.find(';')
        if semicolon != -1:
            title = title[:semicolon]
        pupNames.append(title)
    except Exception, info:
        cdrcgi.bail("Failure retrieving name for PUP CDR%010d: %s" % (pupId,
                                                                      str(info)
                                                                      ))
#----------------------------------------------------------------------
# Build the report.
#----------------------------------------------------------------------
updatePersonLabel = "Update Person%s" % (len(pupNames) <> 1 and "s" or "")
if not pupNames:
    updatePerson = "None"
else:
    sep = ""
    updatePerson = ""
    for name in pupNames:
        updatePerson += "%s%s" % (sep, name)
        sep = "; "
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Lead Organization Status and Participant Mailer History Report</title>
  <style>
   body { font-family: Arial }
  </style>
 </head>
 <body>
  <center>
   <b>
    <font size='4'>Lead Organization Status and Participant
                   Mailer History Report<br>%s
    </font>
   </b>
   <br />
  </center>
  <br />
  <br />
  <table border = '0'>
   <tr>
    <td>
     <b>Lead Organization:&nbsp;&nbsp;</b>
    </td>
    <td>%s</td>
   </tr>
   <tr><td colspan = '2'>&nbsp;</td></tr>
   <tr>
    <td>
     <b>%s:&nbsp;&nbsp;</b>
    </td>
    <td>%s</td>
   </tr>
  </table>
  <br><br>
  <b>
   <font size='3'>Mailer Response History Summary</font>
  </b>
  <br>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Mailer Job</th>
    <th>Mailer Date</th>
    <th># of protocols</th>
    <th># no response</th>
    <th># responses-no changes</th>
    <th># responses with changes</th>
   </tr>
""" % (time.strftime("%B %d, %Y"), orgName, updatePersonLabel, updatePerson)
   
#----------------------------------------------------------------------
# Add one row for each mailer job.
#----------------------------------------------------------------------
jobIds = mailerJobs.keys()
jobIds.sort()
jobIds.reverse()
for jobId in jobIds:
    job = mailerJobs[jobId]
    totalProtocols = (len(job.noResponse) + len(job.respNoChange) +
                      len(job.respWithChange))
    html += """\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td align='center'>%d</td>
    <td align='center'>%d</td>
    <td align='center'>%d</td>
    <td align='center'>%d</td>
   </tr>
""" % (jobId,
       job.date and job.date[:10] or "*** NO DATE ***",
       totalProtocols,
       len(job.noResponse),
       len(job.respNoChange),
       len(job.respWithChange))
html += """\
  </table>
  <br><br>
"""

#----------------------------------------------------------------------
# Show protocols with no response in most recent job.
#----------------------------------------------------------------------
if not jobIds:
    cdrcgi.sendPage(html + """\
  <b>
   <font size='3'>No S&P mailer jobs have been run for this protocol.</font>
  </b>
 </body>
</html>
""")
lastJob = mailerJobs[jobIds[0]]
if not lastJob.noResponse:
    cdrcgi.sendPage(html + """\
  <b>
   <font size='3'>All protocols in last mailer job have responses.</font>
  </b>
 </body>
</html>
""")
html += """\
  <b>
   <font size='3'>List of protocols in last mailer job with no response</font>
  </b>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th align='left'>Mailer ID</th>
    <th align='left'>Protocol ID</th>
    <th align='left'>Title</th>
   </tr>
"""
xslScript = """\
<?xml version='1.0'?>
<xsl:transform             xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                           xmlns:cdr = 'cips.nci.nih.gov/cdr'
                             version = '1.0'>

 <xsl:output                  method = 'xml'/>
 <xsl:template                 match = '/'>
  <ProtocolTitles>
   <xsl:apply-templates       select = 'InScopeProtocol/ProtocolTitle
                                        [@Type="Original"]'/>
   <xsl:apply-templates       select = 'InScopeProtocol/ProtocolAdminInfo/
                                        ProtocolLeadOrg
                                        [LeadOrganizationID/
                                        @cdr:ref="CDR%010d"]'/>
  </ProtocolTitles>
 </xsl:template>
 <xsl:template                 match = 'ProtocolTitle'>
  <OriginalTitle>
   <xsl:value-of              select = '.'/>
  </OriginalTitle>
 </xsl:template>
 <xsl:template                 match = 'ProtocolLeadOrg'>
  <OrgProtocolId>
   <xsl:value-of              select = 'LeadOrgProtocolID'/>
  </OrgProtocolId>
 </xsl:template>
</xsl:transform>
""" % id
for protocolId, mailerId in lastJob.noResponse:
    response = cdr.filterDoc('guest', xslScript, protocolId, inline = 1)
    if type(response) in (type(""), type(u"")):
        cdrcgi.bail("Failure extracting protocol titles for CDR%010d: %s"
                    % (protocolId, response))
    orgProtId = "None"
    originalTitle = "None"
    docElem = xml.dom.minidom.parseString(response[0]).documentElement
    for node in docElem.childNodes:
        if node.nodeName == "OriginalTitle":
            originalTitle = cdr.getTextContent(node)
        elif node.nodeName == "OrgProtocolId":
            orgProtId = cdr.getTextContent(node)
    html += u"""\
   <tr>
    <td valign='top'>CDR%010d</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (mailerId, orgProtId, originalTitle)

#----------------------------------------------------------------------
# Display the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
