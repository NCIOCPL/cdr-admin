#----------------------------------------------------------------------
#
# $Id: PreferredProtOrgs.py,v 1.2 2006-10-12 19:49:32 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/11/10 18:04:47  bkline
# Preferred Protocol Organizations report.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi

conn1 = cdrdb.connect('CdrGuest')
conn2 = cdrdb.connect('CdrGuest')
cursor1 = conn1.cursor()
cursor2 = conn2.cursor()
cursor1.execute("""\
SELECT DISTINCT q.doc_id, q.int_val, s.title, t.title
           FROM query_term q
           JOIN document s
             ON s.id = q.doc_id
           JOIN document t
             ON t.id = q.int_val
          WHERE path = '/Organization/PreferredProtocolOrganization/@cdr:ref'
""")
orgs = {}
preferredOrgs = {}
class Org:
    def __init__(self, id, name):
        self.id    = id
        self.name  = self.extractName(name)
        self.prots = self.countProts()
    def extractName(self, name):
        semi = name.find(';')
        if semi == -1:
            return name
        return name[:semi]
    def countProts(self):
        cursor2.execute("""\
        SELECT COUNT(DISTINCT doc_id)
          FROM query_term
         WHERE path IN ('/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' +
                        '/LeadOrganizationID/@cdr:ref',
                        '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' +
                        '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref')
           AND int_val = ?""", self.id, timeout = 300)
        return cursor2.fetchall()[0][0]

class PreferredOrg:
    def __init__(self, org):
        self.org = org
        self.linkingOrgs = {}

row = cursor1.fetchone()
while row:
    linkingId, targetId, linkingName, targetName = row
    if not orgs.has_key(linkingId):
        linkingOrg = Org(linkingId, linkingName)
        orgs[linkingId] = linkingOrg
    else:
        linkingOrg = orgs[linkingId]
    if not orgs.has_key(targetId):
        targetOrg = Org(targetId, targetName)
        orgs[targetId] = targetOrg
        preferredOrg = PreferredOrg(targetOrg)
        preferredOrgs[targetId] = preferredOrg
    else:
        preferredOrg = preferredOrgs[targetId]
    if not preferredOrg.linkingOrgs.has_key(linkingId):
        preferredOrg.linkingOrgs[linkingId] = linkingOrg
    row = cursor1.fetchone()

def orgCompare(a, b):
    return cmp(orgs[a].name, orgs[b].name)

table = """\
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th colspan='2'>CDR ID</th>
    <th colspan='2'>Organization</th>
    <th># of Linked Protocols</th>
   </tr>
"""
preferredOrgKeys = preferredOrgs.keys()
preferredOrgKeys.sort(orgCompare)
for preferredOrgKey in preferredOrgKeys:
    preferredOrg = preferredOrgs[preferredOrgKey]
    linkingOrgKeys = preferredOrg.linkingOrgs.keys()
    linkingOrgKeys.sort(orgCompare)
    table += """\
   <tr>
    <td colspan='2'><b>%d</b></td>
    <td colspan='2'><b>%s</b></td>
    <td align='right'><b>%d</b></td>
   </tr>
""" % (preferredOrg.org.id, preferredOrg.org.name, preferredOrg.org.prots)
    for linkingOrgKey in linkingOrgKeys:
        linkingOrg = orgs[linkingOrgKey]
        table += """\
   <tr>
    <td width='20'>&nbsp;</td>
    <td align='right' valign='top'>%d</td>
    <td width='20'>&nbsp;</td>
    <td valign='top'>%s</td>
    <td align='right'>%d</td>
   </tr>
""" % (linkingOrg.id, linkingOrg.name, linkingOrg.prots)

table += """\
  </table>
"""
html = """\
<html>
 <head>
  <title>Preferred Protocol Organization Report</title>
  <style type='text/css'>
   body { font-family: Arial; }
  </style>
 </head>
 <body>
  <hr>
  <h3>PREFERRED PROTOCOL ORGANIZATION REPORT</h3>
  <b>Preferred Protocol Organization</b>
  <br><br>
  %s
 </body>
</html>""" % table
cdrcgi.sendPage(html)
