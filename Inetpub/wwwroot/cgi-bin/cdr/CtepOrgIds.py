#----------------------------------------------------------------------
#
# $Id$
#
# Create report that can be used to verify that CTEP org ID mappings
# are correct.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/05/25 14:08:46  bkline
# Report used to verify that CTEP org ID mappings are correct.
#
#----------------------------------------------------------------------
import cdrcgi, cdrdb, sys, csv, urllib, os, msvcrt, time, ExcelWriter

class Org:
    def __init__(self, id, name):
        self.id      = id
        self.name    = name
        self.matched = False

def loadOrgs(cursor):
    cursor.execute("""\
        SELECT n.doc_id, n.value, m.value
          FROM query_term n
          JOIN external_map m
            ON m.doc_id = n.doc_id
          JOIN external_map_usage u
            ON u.id = m.usage
         WHERE u.name = 'CTEP_Institution_Code'
           AND n.path = '/Organization/OrganizationNameInformation'
                      + '/OfficialName/Name'""")
    orgs = {}
    row = cursor.fetchone()
    while row:
        cdrId, orgName, ctepId = row
        key = ctepId.strip().upper()
        orgs[key] = Org(cdrId, orgName)
        row = cursor.fetchone()
    return orgs

try:
    t      = time.strftime("%Y%m%d%H%M%S")
    url    = 'http://ctep.cancer.gov/forms/Organization_Codes.txt'
    urlObj = urllib.urlopen(url)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=CtepOrgIds-%s.xls" % t
    print ""
except:
    cdrcgi.bail('CTEP server unavailable; please try again later')

conn   = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
book   = ExcelWriter.Workbook()
sheet  = book.addWorksheet("CTEP Orgs")
orgs   = loadOrgs(cursor)
rowNum = 1
#format = book.add_format()
labels = True
#format.set_num_format(49)
for values in csv.reader(urlObj):
    if len(values) == 5:
        ctepId, ctepName, city, state, country = values
        if labels:
            cdrId   = "CDR ID"
            cdrName = "CDR Org Name"
            labels  = False
        else:
            key = ctepId.strip().upper()
            org = orgs.get(key)
            if org:
                org.matched = True
                cdrId       = "%d" % org.id
                cdrName     = org.name.strip()
            else:
                cdrId       = "-----"
                cdrName     = "No match"
        row = sheet.addRow(rowNum)
        row.addCell(1, cdrId)
        row.addCell(1, cdrName)
        row.addCell(1, ctepId.strip())
        row.addCell(1, ctepName.strip())
        row.addCell(1, city.strip())
        row.addCell(1, state.strip())
        row.addCell(1, country.strip())
        rowNum += 1

keys = orgs.keys()
keys.sort()
for key in keys:
    org = orgs[key]
    if not org.matched:
        rowNum += 1
        cdrId = "%d" % org.id
        cdrName = org.name.strip()
        row = sheet.addRow(rowNum)
        row.addCell(1, cdrId)
        row.addCell(2, cdrName)
        row.addCell(3, key)
        row.addCell(4, "Not found on CTEP site")
book.write(sys.stdout, True)
