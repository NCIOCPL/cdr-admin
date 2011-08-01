#----------------------------------------------------------------------
#
# $Id$
#
# Report identifying unpublished trials with publishable versions.
#
# BZIssue::5011
#
#----------------------------------------------------------------------
import cdrdb, ExcelWriter, sys, time, cdrcgi

class Protocol:
    def __init__(self, id, date, user, status):
        self.id                 = id
        self.date               = date
        self.user               = user
        self.status             = status
        self.reviewApprovalType = ''
        self.primaryIds         = []
        self.studyCats          = []
        self.specialCats        = []
        self.sourceNames        = []

inScope = {}
ctGov   = {}
prots   = {}
debug   = False #True

def show(what):
    if debug:
        sys.stderr.write(what + '\n')

def fixString(s):
    if not s:
        return u""
    return unicode(s)

def fixList(values):
    return u", ".join([fixString(v) for v in values])

def getDateRange(prots):
    low = ""
    high = ""
    for id in prots:
        date = prots[id].date
        if date:
            date = date[:10]
            if not low or date < low:
                low = date
            if date > high:
                high = date
    if not low or not high:
        return "No Protocols Found"
    if low == high:
        return low
    return "%s through %s" % (low, high)

def addWorksheet(workbook, title, headers, widths, prots):
    worksheet = workbook.addWorksheet(title)
    for col in range(len(headers)):
        worksheet.addCol(col + 1, widths[col])
    row = worksheet.addRow(1, tformat1)
    row.addCell(1, "Newly Publishable Trials", mergeAcross=len(headers) - 1)
    row = worksheet.addRow(2, tformat1)
    row.addCell(1, getDateRange(prots), mergeAcross=len(headers) - 1)
    row = worksheet.addRow(4, tformat2)
    row.addCell(1, "%s Protocols" % title, mergeAcross=1)
    row = worksheet.addRow(6, hdrFormat)
    for col in range(len(headers)):
        row.addCell(col + 1, headers[col])
    keys = prots.keys()
    for key in keys:
        prot = prots[key]
        prot.primaryIds.sort()
        prot.studyCats.sort()
        prot.specialCats.sort()
        prot.sourceNames.sort()
    def sorter(a, b):
        result = cmp(prots[a].studyCats, prots[b].studyCats)
        if result:
            return result
        return cmp(a, b)
    keys.sort(sorter)
    r = 7
    for key in keys:
        prot = prots[key]
        nRows = len(prot.studyCats) or 1
        for rowNum in range(nRows):
            row = worksheet.addRow(r, lformat)
            c = 1
            row.addCell(c, `prot.id`)
            c += 1
            row.addCell(c, fixList(prot.primaryIds))
            c += 1
            if prot.studyCats:
                row.addCell(c, fixString(prot.studyCats[rowNum]))
            c += 1
            if title == 'InScope':
                row.addCell(c, fixList(prot.specialCats))
                c += 1
            row.addCell(c, fixString(prot.status))
            c += 1
            if title == 'InScope':
                row.addCell(c, fixList(prot.sourceNames))
                c += 1
                row.addCell(c, fixString(prot.reviewApprovalType))
                c += 1
            row.addCell(c, prot.date and prot.date[:10] or "")
            c += 1
            row.addCell(c, fixString(prot.user))
            r += 1

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()
cursor.execute("""\
    CREATE TABLE #publishable
             (id INTEGER      NOT NULL,
             ver INTEGER      NOT NULL,
        doc_type VARCHAR(32)  NOT NULL,
          status VARCHAR(255) NOT NULL,
        ver_date DATETIME         NULL,
        usr_name VARCHAR(32)      NULL)""")
show("#publishable created...")
cursor.execute("""\
    INSERT INTO #publishable (id, ver, doc_type, status)
SELECT DISTINCT d.id, MAX(v.num), t.name, s.value
           FROM active_doc d
           JOIN doc_type t
             ON d.doc_type = t.id
           JOIN doc_version v
             ON v.id = d.id
           JOIN query_term s
             ON s.doc_id = d.id
          WHERE t.name IN ('InScopeProtocol', 'CTGovProtocol')
            AND v.publishable = 'Y'
            AND s.path IN ('/InScopeProtocol/ProtocolAdminInfo' +
                           '/CurrentProtocolStatus',
                           '/CTGovProtocol/OverallStatus')
            AND s.value <> 'Withdrawn'
       GROUP BY d.id, t.name, s.value""", timeout = 300)
show("#publishable populated...")
cursor.execute("""\
    UPDATE #publishable
       SET ver_date = v.dt,
           usr_name = u.name
      FROM #publishable d
      JOIN doc_version v
        ON d.id = v.id
       AND d.ver = v.num
      JOIN usr u
        ON u.id = v.usr""")
show("#publishable updated...")
cursor.execute("CREATE TABLE #published (id INTEGER NOT NULL)")
show("#published created...")
cursor.execute("""\
    INSERT INTO #published
SELECT DISTINCT d.doc_id
           FROM pub_proc_doc d
           JOIN #publishable t
             ON t.id = d.doc_id
           JOIN pub_proc p
             ON p.id = d.pub_proc
          WHERE p.pub_subset LIKE 'Push_Documents_To_Cancer.Gov_%'
            AND p.pub_subset <> 'Push_Documents_To_Cancer.Gov_Hotfix-Remove'
            AND p.status = 'Success'
            AND p.completed IS NOT NULL
            AND (d.failure IS NULL OR d.failure <> 'Y')""", timeout = 300)
show("#published populated...")
cursor.execute("CREATE TABLE #unpublished (id INTEGER NOT NULL)")
show("#unpublished created...")
cursor.execute("""\
    INSERT INTO #unpublished
         SELECT id
           FROM #publishable
          WHERE id NOT IN (SELECT id FROM #published)""", timeout = 300)
show("#unpublished populated...")
cursor.execute("""\
    SELECT p.id, p.ver_date, p.usr_name, p.doc_type, p.status
      FROM #publishable p
      JOIN #unpublished u
        ON u.id = p.id""", timeout = 300)
rows = cursor.fetchall()
show("%d rows fetched..." % len(rows))
for id, verDate, usrName, docType, status in rows:
    protocol = prots[id] = Protocol(id, verDate, usrName, status)
    if docType == 'InScopeProtocol':
        inScope[id] = protocol
    else:
        ctGov[id] = protocol
show("protocol objects created...")
cursor.execute("""\
    SELECT DISTINCT q.doc_id, q.value
               FROM query_term q
               JOIN #unpublished u
                 ON u.id = q.doc_id
              WHERE q.path IN ('/InScopeProtocol/ProtocolIDs' +
                               '/PrimaryID/IDString',
                               '/CTGovProtocol/IDInfo/OrgStudyID')""",
               timeout = 300)
rows = cursor.fetchall()
show("%d protocol IDs fetched..." % len(rows))
for id, value in rows:
    if value not in prots[id].primaryIds:
        prots[id].primaryIds.append(value)
show("protocol IDs inserted into protocol objects...")
cursor.execute("""\
    SELECT DISTINCT q.doc_id, q.value
               FROM query_term q
               JOIN #unpublished u
                 ON u.id = q.doc_id
              WHERE q.path IN ('/CTGovProtocol/PDQIndexing/StudyCategory' +
                               '/StudyCategoryName',
                               '/InScopeProtocol/ProtocolDetail' +
                               '/StudyCategory/StudyCategoryName')""",
               timeout = 300)
rows = cursor.fetchall()
show("%d study categories fetched..." % len(rows))
for id, value in rows:
    if value not in prots[id].studyCats:
        prots[id].studyCats.append(value)
show("study categories inserted into protocol objects...")
cursor.execute("""\
    SELECT DISTINCT q.doc_id, q.value
               FROM query_term q
               JOIN #unpublished u
                 ON u.id = q.doc_id
              WHERE q.path = '/InScopeProtocol/ProtocolSpecialCategory'
                           + '/SpecialCategory'""", timeout = 300)
rows = cursor.fetchall()
show("%d special categories fetched..." % len(rows))
for id, value in rows:
    if value not in prots[id].specialCats:
        prots[id].specialCats.append(value)
show("special categories inserted into protocol objects...")       
cursor.execute("""\
    SELECT DISTINCT q.doc_id, q.value
               FROM query_term q
               JOIN #unpublished u
                 ON u.id = q.doc_id
              WHERE q.path = '/InScopeProtocol/ProtocolApproval' +
                             '/ReviewApprovalType'""", timeout = 300)
rows = cursor.fetchall()
show("%d review approval types fetched..." % len(rows))
for id, value in rows:
    prots[id].reviewApprovalType = value
show("review approval types inserted into protocol objects...")
cursor.execute("""\
    SELECT DISTINCT q.doc_id, q.value
               FROM query_term q
               JOIN #unpublished u
                 ON u.id = q.doc_id
              WHERE q.path = '/InScopeProtocol/ProtocolSources/ProtocolSource'
                           + '/SourceName'""", timeout = 300)
rows = cursor.fetchall()
show("%d protocol sources fetched..." % len(rows))
for id, value in rows:
    if value not in prots[id].sourceNames:
        prots[id].sourceNames.append(value)
show("protocol sources inserted into protocol objects...")       
t = time.strftime("%Y%m%d%H%M%S")
if not debug:
    print "Content-type: application/vnd.ms-excel"
    print ("Content-Disposition: attachment; "
           "filename=NewlyPublishableTrials-%s.xls" % t)
    print 

workbook = ExcelWriter.Workbook()
show("workbook created...")
align = ExcelWriter.Alignment('Center', wrap=True)
font = ExcelWriter.Font(bold=True)
hdrFormat = workbook.addStyle(alignment=align, font=font)
align = ExcelWriter.Alignment('Center')
font = ExcelWriter.Font(bold=True, size=16)
tformat1 = workbook.addStyle(alignment=align, font=font)
align = ExcelWriter.Alignment('Left')
font = ExcelWriter.Font(bold=True, size=12)
tformat2 = workbook.addStyle(alignment=align, font=font)
lformat = workbook.addStyle(alignment=align)
titles  = ('InScope', 'CTGov')
headers = (
    ('DocID', 'ProtocolID','Study Category', 'Special Category',
     'Current\nProtocol\nStatus', 'Source', 'Approval',
     'Date Made\nPublishable', 'User'),
    ('DocID', 'ProtocolID', 'Study Category', 'Overall\nStatus',
     'Date Made\nPublishable', 'User')
    )
widths  = (
    (50, 150, 100, 100, 100, 100, 100, 100, 75),
    (50, 150, 100, 100, 100, 75)
    )

addWorksheet(workbook, titles[0], headers[0], widths[0], inScope)
show("%s worksheet created..." % titles[0])
addWorksheet(workbook, titles[1], headers[1], widths[1], ctGov)
show("%s worksheet created..." % titles[1])
workbook.write(sys.stdout, True)
show("done...")
