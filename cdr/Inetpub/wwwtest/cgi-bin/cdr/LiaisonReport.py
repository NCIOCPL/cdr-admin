#----------------------------------------------------------------------
#
# $Id: LiaisonReport.py,v 1.4 2003-08-25 20:13:49 bkline Exp $
#
# NCI Liaison Office/Brussels Protocol Report.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2003/01/02 14:18:47  bkline
# Fixed typo on <style> attribute.
#
# Revision 1.2  2002/10/18 13:53:51  bkline
# Added more filtering to SQL query; cosmetic change.
#
# Revision 1.1  2002/09/23 17:36:40  bkline
# New report for European protocols.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "LiaisonReport.py"
title    = "CDR Administration"
repTitle = "NCI Liaison Office/Brussels Protocol Report"
section  = repTitle
header   = cdrcgi.header(title, title, section, script, buttons)
now      = time.localtime(time.time())

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
# Object representing a protocol.
#----------------------------------------------------------------------
class Protocol:
    def __init__(self, id, status, protocolId, lastMod):
        self.id         = id
        self.status     = status
        self.protocolId = protocolId
        self.lastMod    = lastMod
        self.otherIds   = []
        
#----------------------------------------------------------------------
# Compare numeric portion of protocol ID.
#----------------------------------------------------------------------
nonDigits = re.compile(r"[^\d]+")
def numSort(id1, id2):
    n1 = nonDigits.sub("", id1)
    n2 = nonDigits.sub("", id2)
    if not n1: return -1
    if not n2: return  1
    return cmp(int(n1), int(n2))

#----------------------------------------------------------------------
# Custom sorting logic from Margaret:
#   "Protocol ID field sorted first by EORTC with numbers sequential,
#    then EU with numbers sequential, then others sorted alphabetically."
#----------------------------------------------------------------------
def protSorter(k1, k2):
    if not protocols.has_key(k1): return -1
    if not protocols.has_key(k2): return  1
    p1 = protocols[k1]
    p2 = protocols[k2]
    id1 = p1.protocolId
    id2 = p2.protocolId
    if id1.startswith("EORTC-"):
        if id2.startswith("EORTC-"):
            return numSort(id1, id2)
        else:
            return -1
    elif id2.startswith("EORTC-"):
        return 1
    elif id1.startswith("EU-"):
        if id2.startswith("EU-"):
            return numSort(id1, id2)
        else:
            return -1
    elif id2.startswith("EU-"):
        return 1
    else:
        return cmp(id1, id2)

#----------------------------------------------------------------------
# Get the protocol original title.
#----------------------------------------------------------------------
def getOriginalTitle(id):
    xslScript = """\
<?xml version='1.0'?>
<xsl:transform             xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                           xmlns:cdr = 'cips.nci.nih.gov/cdr'
                             version = '1.0'>

 <xsl:output                  method = 'xml'/>
 <xsl:template                 match = '/'>
  <OriginalTitle>
   <xsl:value-of              select = 'InScopeProtocol/ProtocolTitle
                                        [@Type="Original"]'/>
  </OriginalTitle>
 </xsl:template>
</xsl:transform>
"""
    response = cdr.filterDoc('guest', xslScript, id, inline = 1)
    if type(response) in (type(""), type(u"")):
        cdrcgi.bail("Failure extracting protocol original "
                    "title for CDR%010d: %s" % (id, response))
    return unicode(response[0], "utf-8")
    
#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s -- %s</title>
  <style type = 'text/css'>
   body    { font-family: Arial, Helvetica, sans-serif }
   span.t1 { font-size: 14pt; font-weight: bold }
   span.t2 { font-size: 12pt; font-weight: bold }
   th      { text-align: center; vertical-align: top; 
             font-size: 12pt; font-weight: bold }
   td      { text-align: left; vertical-align: top; 
             font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <body>
  <center>
   <span class='t1'>%s</span>
   <br />
   <br />
  </center>
""" % (repTitle, time.strftime("%B %d, %Y"), repTitle)
   
#----------------------------------------------------------------------
# Extract the protocol information from the database.
#----------------------------------------------------------------------
protocols     = {}
protStatPath  = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
pdqKeyPath    = '/InScopeProtocol/PdqKey'
sourcePath    = '/InScopeProtocol/ProtocolSources/ProtocolSource/SourceName'
primaryIdPath = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
otherIdPath   = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
lastModPath   = '/InScopeProtocol/DateLastModified'

try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    conn.setAutoCommit(1)
    cursor.execute("""\
SELECT DISTINCT d.doc_id,
                d.value
           INTO #european_protocols
           FROM query_term d
           JOIN document p
             ON p.id = d.doc_id
          WHERE d.path = '%s'
            AND d.value IN ('Active', 
                            'Approved-not yet active', 
                            'Temporarily Closed')
            AND p.active_status = 'A'
            AND EXISTS (SELECT *
                          FROM primary_pub_doc
                         WHERE doc_id = d.doc_id)
            AND (EXISTS (SELECT * 
                           FROM query_term
                          WHERE path IN ('%s', '%s')
                            AND doc_id = d.doc_id
                            AND (value LIKE 'EU-%%' 
                             OR  value LIKE 'EORTC-%%'))
             OR EXISTS  (SELECT *
                           FROM query_term
                          WHERE doc_id = d.doc_id
                            AND path = '%s'
                            AND value = 'NCI Liaison Office-Brussels'))""" % (
            protStatPath,
            primaryIdPath,
            otherIdPath,
            sourcePath))
    cursor.execute("""\
   SELECT DISTINCT p.doc_id,
                   p.value,
                   i.value,
                   m.value
              FROM #european_protocols p
   LEFT OUTER JOIN query_term i
                ON i.doc_id = p.doc_id
               AND i.path = '%s'
   LEFT OUTER JOIN query_term m
                ON m.doc_id = p.doc_id
               AND m.path = '%s'""" % (primaryIdPath, lastModPath))
    for row in cursor.fetchall():
        protocols[row[0]] = Protocol(row[0], row[1], row[2], row[3])
    cursor.execute("""\
   SELECT DISTINCT p.doc_id,
                   i.value
              FROM #european_protocols p
              JOIN query_term i
                ON i.doc_id = p.doc_id
             WHERE i.path = '%s'""" % otherIdPath)
    for row in cursor.fetchall():
        key, otherId = row
        if otherId:
            protocols[key].otherIds.append(otherId)
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Make sure we have some documents to report on.
#----------------------------------------------------------------------
if not protocols:
    cdrcgi.sendPage(html + """\
  <span class='t2'>No documents found to report.</span>
 </body>
</html>
""")

#----------------------------------------------------------------------
# Start the table.
#----------------------------------------------------------------------
html += """\
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <th>CDR Doc ID</th>
    <th>Protocol ID</th>
    <th>Other IDs</th>
    <th>Original Title</th>
    <th>Protocol Status</th>
    <th>Date Last Modified</th>
   </tr>
"""

#----------------------------------------------------------------------
# Sort the protocols.
#----------------------------------------------------------------------
keys = protocols.keys()
keys.sort(protSorter)


#----------------------------------------------------------------------
# Populate the table.
#----------------------------------------------------------------------
for key in keys:
    protocol = protocols[key]
    otherIds = ", ".join(protocol.otherIds)
    html += """\
   <tr>
    <td align='top'>%d</td>
    <td align='top'>%s</td>
    <td align='top'>%s</td>
    <td align='top'>%s</td>
    <td align='top'>%s</td>
    <td align='top'>%s</td>
   </tr>
""" % (protocol.id,
       protocol.protocolId or "&nbsp;",
       otherIds or "&nbsp;",
       getOriginalTitle(protocol.id),
       protocol.status or "&nbsp;",
       protocol.lastMod or "&nbsp;")

#----------------------------------------------------------------------
# Display the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(cdrcgi.unicodeToLatin1(html + """\
  </table>
 </body>
</html>
"""))
