#----------------------------------------------------------------------
# Report identifying unpublished trials with publishable versions.
# BZIssue::5011
#----------------------------------------------------------------------
import datetime
import sys
import cdrcgi
import cdrdb

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
    def sort_sets(self):
        self.primaryIds.sort()
        self.studyCats.sort()
        self.specialCats.sort()
        self.sourceNames.sort()
    def __cmp__(self, other):
        result = cmp(self.studyCats, other.studyCats)
        if result:
            return result
        return cmp(self.id, other.id)

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

def addWorksheet(styles, title, headers, widths, prots):
    assert(len(headers) == len(widths))
    sheet = styles.add_sheet(title)
    for col, points in enumerate(widths):
        sheet.col(col).width = styles.points_to_width(points)
    banner = "Newly Publishable Trials"
    date_range = getDateRange(prots)
    sheet.write_merge(0, 0, 0, len(widths) - 1, banner, styles.banner)
    sheet.write_merge(1, 1, 0, len(widths) - 1, date_range, styles.banner)
    sheet.write_merge(3, 3, 0, 1, "%s Protocols" % title, styles.title)
    for col, header in enumerate(headers):
        sheet.write(5, col, header, styles.header)
    for prot in prots.values():
        prot.sort_sets()
    row = 6
    for prot in sorted(prots.values()):
        rows = len(prot.studyCats) or 1
        for i in range(rows):
            sheet.write(row, 0, str(prot.id), styles.left)
            sheet.write(row, 1, fixList(prot.primaryIds), styles.left)
            if prot.studyCats:
                sheet.write(row, 2, fixString(prot.studyCats[i]), styles.left)
            col = 3
            if title == 'InScope':
                sheet.write(row, col, fixList(prot.specialCats), styles.left)
                col += 1
            sheet.write(row, col, fixString(prot.status), styles.left)
            col += 1
            if title == 'InScope':
                sheet.write(row, col, fixList(prot.sourceNames), styles.left)
                col += 1
                approval_type = fixString(prot.reviewApprovalType)
                sheet.write(row, col, approval_type, styles.left)
                col += 1
            prot_date = prot.date and prot.date[:10] or ""
            sheet.write(row, col, prot_date, styles.left)
            col += 1
            sheet.write(row, col, fixString(prot.user), styles.left)
            row += 1

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
t = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
if not debug:
    print "Content-type: application/vnd.ms-excel"
    print ("Content-Disposition: attachment; "
           "filename=NewlyPublishableTrials-%s.xls" % t)
    print

styles = cdrcgi.ExcelStyles()
styles.title = styles.style(styles.bold_font(12))
styles.banner.font.height = 16 * 20 # 16 pt
show("workbook created...")
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

addWorksheet(styles, titles[1], headers[1], widths[1], ctGov)
show("%s worksheet created..." % titles[1])
addWorksheet(styles, titles[0], headers[0], widths[0], inScope)
show("%s worksheet created..." % titles[0])
styles.book.save(sys.stdout)
show("done...")
