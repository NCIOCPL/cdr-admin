#----------------------------------------------------------------------
#
# $Id: NewlyPublishableTrials.py,v 1.1 2004-06-02 17:53:00 bkline Exp $
#
# Report identifying unpublished trials with publishable versions.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, pyXLWriter, sys, time, cdrcgi

class Protocol:
    def __init__(self, id, date, user):
        self.id          = id
        self.date        = date
        self.user        = user
        self.primaryIds  = []
        self.studyCats   = []
        self.specialCats = []
inScope = {}
ctGov   = {}
prots   = {}
debug   = 0

def show(what):
    if debug:
        sys.stderr.write(what + '\n')

def fixString(s):
    if type(s) == type(u""):
        return s.encode('latin-1', 'replace')
    return `s`

def fixList(list):
    if not list: return ''
    s = fixString(list[0])
    for m in list[1:]:
        s += ", %s" % fixString(m)
    return s

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
    worksheet = workbook.add_worksheet(title)
    for col in range(len(headers)):
        worksheet.set_column(col, widths[col])
        worksheet.write([5, col], headers[col], hdrFormat)
    worksheet.write([0, 0], "Newly Publishable Trials", tformat1)
    worksheet.write([1, 0], getDateRange(prots), tformat1)
    c = 1
    while c < len(headers):
        worksheet.write_blank([0, c], tformat1)
        worksheet.write_blank([1, c], tformat1)
        c += 1
    worksheet.write([3, 0], "%s Protocols" % title, tformat2)
    worksheet.write_blank([3, 1], tformat2)
    keys = prots.keys()
    for key in keys:
        prot = prots[key]
        prot.primaryIds.sort()
        prot.studyCats.sort()
        prot.specialCats.sort()
    def sorter(a, b):
        result = cmp(prots[a].studyCats, prots[b].studyCats)
        if result:
            return result
        return cmp(a, b)
    keys.sort(sorter)
    r = 6
    for key in keys:
        prot = prots[key]
        c = 0
        worksheet.write([r, c], `prot.id`, lformat)
        c += 1
        worksheet.write([r, c], fixList(prot.primaryIds), lformat)
        c += 1
        worksheet.write([r, c], fixList(prot.studyCats), lformat)
        c += 1
        if title == 'InScope':
            worksheet.write([r, c], fixList(prot.specialCats), lformat)
            c += 1
        worksheet.write([r, c], prot.date and prot.date[:10] or "", lformat)
        c += 1
        worksheet.write([r, c], fixString(prot.user), lformat)
        r += 1

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()
cursor.execute("""\
    CREATE TABLE #publishable
             (id INTEGER     NOT NULL,
             ver INTEGER     NOT NULL,
        doc_type VARCHAR(32) NOT NULL,
        ver_date DATETIME        NULL,
        usr_name VARCHAR(32)     NULL)""")
show("#publishable created...")
cursor.execute("""\
    INSERT INTO #publishable (id, ver, doc_type)
SELECT DISTINCT d.id, MAX(v.num), t.name
           FROM active_doc d
           JOIN doc_type t
             ON d.doc_type = t.id
           JOIN doc_version v
             ON v.id = d.id
          WHERE t.name IN ('InScopeProtocol', 'CTGovProtocol')
            AND v.publishable = 'Y'
       GROUP BY d.id, t.name""", timeout = 300)
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
    SELECT p.id, p.ver_date, p.usr_name, p.doc_type
      FROM #publishable p
      JOIN #unpublished u
        ON u.id = p.id""", timeout = 300)
rows = cursor.fetchall()
show("%d rows fetched..." % len(rows))
for id, verDate, usrName, docType in rows:
    protocol = prots[id] = Protocol(id, verDate, usrName)
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
t = time.strftime("%Y%m%d%H%M%S")
if not debug:
    print "Content-type: application/vnd.ms-excel"
    print ("Content-Disposition: attachment; "
           "filename=NewlyPublishedTrials-%s.xls" % t)
    print 

workbook = pyXLWriter.Writer(sys.stdout)
show("workbook created...")
hdrFormat = workbook.add_format()
hdrFormat.set_bold();
hdrFormat.set_align('center')
hdrFormat.set_text_wrap(1)
tformat1 = workbook.add_format()
tformat1.set_bold();
tformat1.set_size(16)
tformat1.set_align('center')
tformat1.set_merge(1)
tformat2 = workbook.add_format()
tformat2.set_bold();
tformat2.set_size(12)
tformat2.set_merge(1)
tformat2.set_align('left')
lformat = workbook.add_format()
lformat.set_align('left')
titles  = ('InScope', 'CTGov')
headers = (
    ('DocID', 'ProtocolID','Study Category', 'Special Category',
     'Date Made\nPublishable', 'User'),
    ('DocID', 'ProtocolID', 'Study Category', 'Date Made\nPublishable', 'User')
    )
widths  = (
    (9.71, 25.29, 18.43, 18.43, 18, 12),
    (9.71, 25.29, 18.43, 18, 12)
    )

addWorksheet(workbook, titles[0], headers[0], widths[0], inScope)
show("%s worksheet created..." % titles[0])
addWorksheet(workbook, titles[1], headers[1], widths[1], ctGov)
show("%s worksheet created..." % titles[1])
workbook.close()
show("done...")
