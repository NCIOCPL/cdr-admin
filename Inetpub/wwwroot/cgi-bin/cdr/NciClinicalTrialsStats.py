#----------------------------------------------------------------------
#
# $Id$
#
# "We want to create a new report to be added to the Protocols Menu
# in the CDR, to respond to requests for Clinical Trial Statistics."
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2005/06/30 21:56:30  bkline
# Modifications requested by Sheri in request #1748.
#
# Revision 1.2  2005/06/09 18:37:41  bkline
# Cosmetic mods requested by Lakshmi.
#
# Revision 1.1  2005/06/06 20:49:32  bkline
# New report for clinical trials statistics.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, time

def showTotal(label, total):
    totalString = str(total)
    dots = (70 - len(totalString) - len(label) - 2) * u'.'
    return label + u' ' + dots + u' ' + totalString

htmlStrings = [u"""\
<html>
 <head>
  <title>Profile of Active and Approved NCI Sponsored Clinical Trials</title>
 </head>
 <body>
  <h3>Profile of Active and Approved NCI Sponsored Clinical Trials</h3>
  <h4>%s</h4>
  <pre>""" % time.strftime("%Y-%m-%d")]
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #a (id INTEGER)")
conn.commit()
cursor.execute("""\
    INSERT INTO #a
SELECT DISTINCT s.doc_id
           FROM query_term s
           JOIN query_term n
             ON n.doc_id = s.doc_id
           JOIN pub_proc_cg p
             ON p.id = s.doc_id
          WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo'
                       + '/CurrentProtocolStatus'
            AND n.path = '/InScopeProtocol/ProtocolSponsors/SponsorName'
            AND n.value = 'NCI'
            AND s.value IN ('Active', 'Approved-not yet active')""",
               timeout = 300)
conn.commit()
cursor.execute("SELECT COUNT(*) FROM #a")
#print "total protocols:", cursor.fetchall()[0][0]
htmlStrings.append(showTotal(u"TOTAL NUMBER OF NCI SPONSORED PDQ PROTOCOLS",
                             cursor.fetchall()[0][0]))
#print ""

htmlStrings.append("")
cursor.execute("""\
    SELECT COUNT(DISTINCT #a.id)
      FROM #a
      JOIN query_term c
        ON c.doc_id = #a.id
     WHERE c.path = '/InScopeProtocol/ProtocolSpecialCategory/SpecialCategory'
       AND c.value = 'NIH Clinical Center trial'""", timeout = 300)
#print "intramural trials:", cursor.fetchall()[0][0]
htmlStrings.append(showTotal(u"INTRAMURAL TRIALS", cursor.fetchall()[0][0]))
#print ""
htmlStrings.append("")

cursor.execute("""\
    SELECT DISTINCT #a.id, n.value
               FROM #a
               JOIN query_term o
                 ON o.doc_id = #a.id
               JOIN query_term n
                 ON n.doc_id = o.int_val
               JOIN query_term t
                 ON t.doc_id = n.doc_id
              WHERE o.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
                AND n.path = '/Organization/OrganizationNameInformation'
                           + '/OfficialName/Name'
                AND t.path = '/Organization/OrganizationType'
                AND t.value = 'NCI-supported clinical trials group'""",
               timeout = 300)
prots = {}
orgs  = {}
for docId, orgName in cursor.fetchall():
    prots[docId] = 1
    orgs[orgName] = orgs.get(orgName, 0) + 1
#print "cooperative group trials:", len(prots)
htmlStrings.append(showTotal(u"COOPERATIVE GROUP TRIALS", len(prots)))
keys = orgs.keys()
keys.sort()
for key in keys:
    htmlStrings.append(u"    %-60s %5d" % (key, orgs[key]))
#print ""
htmlStrings.append(u"")

cursor.execute("""\
    SELECT DISTINCT #a.id, t.value
               FROM #a
               JOIN query_term t
                 ON #a.id = t.doc_id
              WHERE t.path = '/InScopeProtocol/FundingInfo/NIHGrantContract'
                           + '/NIHGrantContractType'
                AND t.value NOT IN ('U10', 'P30')""", timeout = 300)
prots = {}
types = {}
for docId, contractType in cursor.fetchall():
    prots[docId] = 1
    types[contractType] = types.get(contractType, 0) + 1
#print "NCI Grant supported trials:", len(prots)
htmlStrings.append(showTotal(u"NCI GRANT SUPPORTED TRIALS", len(prots)))
keys = types.keys()
keys.sort()
for key in keys:
    htmlStrings.append(u"    %-60s %5d" % (key, types[key]))
#print ""
htmlStrings.append(u"")

cursor.execute("""\
    SELECT DISTINCT #a.id, t.value
               FROM #a
               JOIN query_term o
                 ON o.doc_id = #a.id
               JOIN query_term t
                 ON t.doc_id = o.int_val
              WHERE o.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
                AND t.path = '/Organization/OrganizationType'
                AND t.value IN ('NCI-designated comprehensive cancer center',
                                'NCI-designated clinical cancer center',
                                'NCI-designated cancer center')""",
               timeout = 300)
prots = {}
types = {}
for docId, orgType in cursor.fetchall():
    prots[docId] = 1
    types[orgType] = types.get(orgType, 0) + 1
#print "cooperative group trials:", len(prots)
htmlStrings.append(showTotal(u"NCI-DESIGNATED CANCER CENTER INITIATED TRIALS",
                             len(prots)))
keys = types.keys()
keys.sort()
for key in keys:
    htmlStrings.append(u"    %-60s %5d" % (key, types[key]))
#print ""
htmlStrings.append(u"")

cursor.execute("""\
    SELECT DISTINCT #a.id, t.value
               FROM #a
               JOIN query_term o
                 ON o.doc_id = #a.id
               JOIN query_term t
                 ON t.doc_id = o.int_val
              WHERE o.path IN ('/InScopeProtocol/ProtocolAdminInfo'
                             + '/ProtocolLeadOrg/ProtocolSites/OrgSite'
                             + '/OrgSiteID/@cdr:ref',
                               '/InScopeProtocol/ProtocolAdminInfo'
                             + '/ExternalSites/ExternalSite'
                             + '/ExternalSiteOrg/ExternalSiteOrgID/@cdr:ref')
                AND t.path = '/Organization/OrganizationType'
                AND t.value IN ('NCI-designated comprehensive cancer center',
                                'NCI-designated clinical cancer center',
                                'NCI-designated cancer center')""",
               timeout = 300)
prots = {}
types = {}
for docId, orgType in cursor.fetchall():
    prots[docId] = 1
    types[orgType] = types.get(orgType, 0) + 1
#print "cooperative group trials:", len(prots)
htmlStrings.append(showTotal(u"NCI-DESIGNATED CANCER CENTERS AS "
                             u"SITES FOR TRIALS", len(prots)))
keys = types.keys()
keys.sort()
for key in keys:
    htmlStrings.append(u"    %-60s %5d" % (key, types[key]))

htmlStrings.append("")
cursor.execute("""\
    SELECT DISTINCT #a.id, c.value
      FROM #a
      JOIN query_term c
        ON c.doc_id = #a.id
     WHERE c.path = '/InScopeProtocol/ProtocolSpecialCategory/SpecialCategory'
""", timeout = 300)
cats = {}
prots = {}
for docId, cat in cursor.fetchall():
    prots[docId] = True
    cats[cat] = cats.get(cat, 0) + 1
htmlStrings.append(showTotal(u"NCI-SPONSORED PDQ PROTOCOLS WITH "
                             "SPECIAL CATEGORY ELEMENT", len(prots)))
keys = cats.keys()
keys.sort()
for key in keys:
    htmlStrings.append(u"    %-60s %5d" %
                       (key or "[element present but empty]", cats[key]))
htmlStrings.append("")

htmlStrings.append(u"""\

[* Numbers of trials may be lower than sums of individual breakdown
   counts because of overlap within trials.]
  </pre>
 </body>
</html>""")
cdrcgi.sendPage(u"\n".join(htmlStrings) + "\n")
