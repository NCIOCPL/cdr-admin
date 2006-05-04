import cdrdb, ExcelWriter, sys

class Org:
    def __init__(self, docId, orgName, orgType):
        self.docId      = docId
        self.orgName    = orgName
        self.orgType    = orgType
        self.activeLead = 0
        self.activeSite = 0
        self.closedLead = 0
    def __cmp__(self, other):
        return cmp(self.orgName, other.orgName)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    CREATE TABLE #orgs
         (doc_id INTEGER,
            name NVARCHAR(255),
        org_type NVARCHAR(255))""")
conn.commit()
cursor.execute("""\
    INSERT INTO #orgs
         SELECT n.doc_id, n.value, t.value
           FROM query_term n
           JOIN query_term t
             ON n.doc_id = t.doc_id
          WHERE n.path = '/Organization/OrganizationNameInformation'
                       + '/OfficialName/Name'
            AND t.path = '/Organization/OrganizationType'
            AND t.value IN ('NCI-designated cancer center',
                            'NCI-designated comprehensive cancer center',
                            'NCI-designated clinical cancer center')""")
conn.commit()
orgs = {}
orgTypes = {}
cursor.execute("SELECT * FROM #orgs")
for docId, orgName, orgType in cursor.fetchall():
    org = Org(docId, orgName, orgType)
    orgs[docId] = org
    if orgType in orgTypes:
        orgTypes[orgType].append(org)
    else:
        orgTypes[orgType] = [org]
#sys.stderr.write("%d orgs\n" % len(orgs))
#sys.stderr.write("%d org types\n" % len(orgTypes))
#for ot in orgTypes:
#    sys.stderr.write("\t%d %s orgs\n" % (len(orgTypes[ot]), ot))
                 
cursor.execute("""\
    SELECT o.doc_id, COUNT(*)
      FROM query_term s
      JOIN query_term l
        ON s.doc_id = l.doc_id
      JOIN #orgs o
        ON o.doc_id = l.int_val
      JOIN document d
        ON d.id = s.doc_id
      JOIN pub_proc_cg c
        ON c.id = d.id
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND s.value IN ('Active', 'Approved-not yet active')
       AND l.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrganizationID/@cdr:ref'
       AND d.active_status = 'A'
  GROUP BY o.doc_id""")
for docId, count in cursor.fetchall():
    orgs[docId].activeLead = count

cursor.execute("""\
    SELECT o.doc_id, COUNT(*)
      FROM query_term s
      JOIN query_term l
        ON s.doc_id = l.doc_id
      JOIN #orgs o
        ON o.doc_id = l.int_val
      JOIN document d
        ON d.id = s.doc_id
      JOIN pub_proc_cg c
        ON c.id = d.id
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND s.value IN ('Closed', 'Completed', 'Temporarily closed')
       AND l.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrganizationID/@cdr:ref'
       AND d.active_status = 'A'
  GROUP BY o.doc_id""")
for docId, count in cursor.fetchall():
    orgs[docId].closedLead = count

cursor.execute("""\
    SELECT o.doc_id, COUNT(*)
      FROM query_term s
      JOIN query_term p
        ON s.doc_id = p.doc_id
       AND LEFT(s.node_loc, 16) = LEFT(p.node_loc, 16)
      JOIN #orgs o
        ON o.doc_id = p.int_val
      JOIN document d
        ON d.id = s.doc_id
      JOIN pub_proc_cg c
        ON c.id = d.id
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/ProtocolSites/OrgSite/OrgSiteStatus'
       AND s.value IN ('Active', 'Approved-not yet active')
       AND p.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref'
       AND d.active_status = 'A'
  GROUP BY o.doc_id""")
for docId, count in cursor.fetchall():
    orgs[docId].activeSite = count

#sys.stderr.write("%d orgs\n" % len(orgs))
#sys.stderr.write("%d org types\n" % len(orgTypes))
#for ot in orgTypes:
#    sys.stderr.write("\t%d %s orgs\n" % (len(orgTypes[ot]), ot))

wb   = ExcelWriter.Workbook()
ws   = wb.addWorksheet("CCB Report", frozenRows = 2)
ws.addCol(1, 250.0)
ws.addCol(2, 200.0)
ws.addCol(3, 85.0)
ws.addCol(4, 85.0)
ws.addCol(5, 85.0)
font = ExcelWriter.Font(bold = True)
align = ExcelWriter.Alignment('Center', 'Center', wrap = True)
style = wb.addStyle(font = font, alignment = align)
row  = ws.addRow(1, style, 40.0)
row.addCell(1, "Trials from NCI-designated Cancer Centers listed in PDQ "
            " Cancer Clinical Trials Registry", mergeAcross = 4)
row = ws.addRow(2, style)
row.addCell(1, "Center Name")
row.addCell(2, "Center Type")
row.addCell(3, "Active/Approved trials as Lead")
row.addCell(4, "Active/Approved Site")
row.addCell(5, "Closed trials as Lead")
align = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style = wb.addStyle(alignment = align)
align = ExcelWriter.Alignment('Right', 'Top', wrap = True)
number = wb.addStyle(alignment = align)
rowNum = 3
keys = orgTypes.keys()
keys.sort()
for key in keys:
    orgType = orgTypes[key]
    orgType.sort()
    for org in orgType:
        row = ws.addRow(rowNum, style)
        row.addCell(1, org.orgName)
        row.addCell(2, org.orgType)
        row.addCell(3, org.activeLead, 'Number', style = number)
        row.addCell(4, org.activeSite, 'Number', style = number)
        row.addCell(5, org.closedLead, 'Number', style = number)
        rowNum += 1
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=Request2113.xml"
print
wb.write(sys.stdout)
