#----------------------------------------------------------------------
#
# $Id: CtepOrgIds.py,v 1.1 2005-05-25 14:08:46 bkline Exp $
#
# Create report that can be used to verify that CTEP org ID mappings
# are correct.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrcgi, cdrdb, sys, pyXLWriter, csv, urllib, os, msvcrt, time

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
book   = pyXLWriter.Writer(sys.stdout)
sheet  = book.add_worksheet("CTEP Orgs")
orgs   = loadOrgs(cursor)
row    = 0
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
                cdrName     = org.name.strip().encode('latin-1', 'ignore')
            else:
                cdrId       = ""
                cdrName     = "No match"
        sheet.write([row, 0], cdrId)
        sheet.write_string([row, 1], cdrName)
        sheet.write_string([row, 2], ctepId.strip())
        sheet.write_string([row, 3], ctepName.strip())
        sheet.write_string([row, 4], city.strip())
        sheet.write_string([row, 5], state.strip())
        sheet.write_string([row, 6], country.strip())
        row += 1

keys = orgs.keys()
keys.sort()
for key in keys:
    org = orgs[key]
    if not org.matched:
        row    += 1
        cdrId   = "%d" % org.id
        cdrName = org.name.strip().encode('latin-1', 'ignore')
        sheet.write([row, 0], cdrId)
        sheet.write_string([row, 1], cdrName)
        sheet.write_string([row, 2], key.encode('latin-1', 'ignore'))
        sheet.write_string([row, 3], "Not found on CTEP site")
book.close()
