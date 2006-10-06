#----------------------------------------------------------------------
#
# $Id: NewlyPublishedTrials2.py,v 1.2 2006-09-28 15:11:20 bkline Exp $
#
# "We need a newly published trials report which lists InScope Protocol
# and CTGov trials that have published versions, but do not have a
# previously published version. The report will be generated by a user
# selected date range.  
#
# This report has the same fields as the newly publishable trials report,
# but it will also include totals.Report identifying unpublished trials
# with publishable versions." [Sheri Khana, request #2443]
#
# Note that this script is given the name it has to avoid conflicts
# with NewlyPublishedTrials.py, a report that was retired a little
# over two years ago.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/09/28 11:56:43  bkline
# Request #2443.
#
#----------------------------------------------------------------------
import cdrdb, pyXLWriter, sys, time, cdrcgi, cgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
startDate = fields and fields.getvalue('start') or None
endDate   = fields and fields.getvalue('end') or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "NewlyPublishedTrials2.py"
title   = "CDR Administration"
section = "Newly Published Trials Report"
header  = cdrcgi.header(title, title, section, script, buttons)

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
if not (startDate and endDate):
    now = time.localtime()
    then = (now[0], now[1], now[2] - 7, 0, 0, 0, 0, 0, -1)
    then = time.localtime(time.mktime(then))
    now = time.strftime("%Y-%m-%d")
    then = time.strftime("%Y-%m-%d", then)
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <table border='0'>
    <tr>
     <td><b>Start Date&nbsp;</b></td>
     <td><input name='start' value='%s'></td>
    </tr>
    <tr>
     <td><b>End Date&nbsp;</b></td>
     <td><input name='end' value='%s'></td>
    </tr>
   </table>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, then, now)
    cdrcgi.sendPage(header + form)

class Protocol:
    def __init__(self, id, docType, date, user):
        self.id                 = id
        self.docType            = docType
        self.date               = date
        self.user               = user
        self.status             = None
        self.reviewApprovalType = ''
        self.primaryIds         = set()
        self.studyCats          = set()
        self.specialCats        = set()
        self.sourceNames        = set()

inScope    = {}
ctGov      = {}
prots      = {}
debug      = False
statuses   = {}
sources    = {}
approvals  = {}
categories = {}

def show(what):
    if debug:
        sys.stderr.write(what + '\n')

def fixString(s):
    if type(s) == type(u""):
        return s.encode('latin-1', 'replace')
    return str(s)

def fixList(list):
    if not list: return ''
    s = fixString(list[0])
    for m in list[1:]:
        s += ", %s" % fixString(m)
    return s

def getDateRange():
    return "%s through %s" % (startDate, endDate)

def createSortedList(valueSet):
    valueList = list(valueSet)
    valueList.sort()
    return valueList

def writeTotals(sheet, values, title, row):
    sheet.write([row, 0], title, tformat3)
    row += 1
    keys = values.keys()
    keys.sort()
    for key in keys:
        sheet.write([row, 0], key, lformat)
        sheet.write([row, 1], values[key], rformat)
        row += 1
    return row + 2

def addTotalsSheet(workbook, prots, inScope, ctGov):
    worksheet = workbook.add_worksheet('Totals')
    worksheet.set_column(0, 30)
    worksheet.set_column(1, 5)
    worksheet.write([0, 0], "Newly Published Trials", tformat1)
    worksheet.write([1, 0], getDateRange(), tformat1)
    worksheet.write([3, 0], "InScope and CTGov Totals", tformat2)
    for c in range(1, 8):
        worksheet.write_blank([0, c], tformat1)
        worksheet.write_blank([1, c], tformat1)
    #worksheet.write_blank([3, 1], tformat2)
        
    row = writeTotals(worksheet, categories, "Study Category",            5)
    row = writeTotals(worksheet, statuses,   "Current Protocol Status", row)
    row = writeTotals(worksheet, sources,    "Protocol Source",         row)
    row = writeTotals(worksheet, approvals,  "Approval",                row)

def addWorksheet(workbook, title, headers, widths, prots):
    worksheet = workbook.add_worksheet(title)
    for col in range(len(headers)):
        worksheet.set_column(col, widths[col])
        worksheet.write([5, col], headers[col], hdrFormat)
    worksheet.write([0, 0], "Newly Published Trials", tformat1)
    worksheet.write([1, 0], getDateRange(), tformat1)
    c = 1
    while c < len(headers):
        worksheet.write_blank([0, c], tformat1)
        worksheet.write_blank([1, c], tformat1)
        c += 1
    worksheet.write([3, 0], "%s Protocols" % title, tformat2)
    #c = 1
    #while c < len(headers):
    #    worksheet.write_blank([3, c], tformat2)
    #    c += 1
    #worksheet.write_blank([3, 1], tformat2)
    keys = prots.keys()
    for key in keys:
        prot             = prots[key]
        prot.primaryIds  = createSortedList(prot.primaryIds)
        prot.studyCats   = createSortedList(prot.studyCats)
        prot.specialCats = createSortedList(prot.specialCats)
        prot.sourceNames = createSortedList(prot.sourceNames)
    def sorter(a, b):
        result = cmp(prots[a].studyCats, prots[b].studyCats)
        if result:
            return result
        return cmp(a, b)
    keys.sort(sorter)
    r = 6
    for key in keys:
        prot = prots[key]
        nRows = len(prot.studyCats) or 1
        for rowNum in range(nRows):
            c = 0
            worksheet.write([r, c], `prot.id`, lformat)
            c += 1
            worksheet.write([r, c], fixList(prot.primaryIds), lformat)
            c += 1
            if prot.studyCats:
                worksheet.write([r, c], fixString(prot.studyCats[rowNum]),
                                lformat)
            c += 1
            if title == 'InScope':
                worksheet.write([r, c], fixList(prot.specialCats), lformat)
                c += 1
            worksheet.write([r, c], fixString(prot.status), lformat);
            c += 1
            if title == 'InScope':
                worksheet.write([r, c], fixList(prot.sourceNames), lformat)
                c += 1
                worksheet.write([r, c], fixString(prot.reviewApprovalType),
                                lformat)
                c += 1
            worksheet.write([r, c], prot.date and prot.date[:10] or "",
                            lformat)
            c += 1
            worksheet.write([r, c], fixString(prot.user), lformat)
            r += 1
    r += 2
    worksheet.write([r, 0], "Total: %d" % len(prots), tformat3)

#if len(sys.argv) == 3:
#    debug     = True
#    startDate = '2006-01-01'
#    endDate   = '2006-09-01'
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

#----------------------------------------------------------------------
# Start by creating a list of all protocols first published in the
# date range specified by the user.
#----------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
# conn.setAutoCommit()
cursor = conn.cursor()
cursor.execute("""\
    CREATE TABLE #trials
             (id INT         NOT NULL,
        doc_type VARCHAR(32) NOT NULL,
         pub_job INT         NOT NULL,
        pub_date DATETIME    NOT NULL)""")
conn.commit()
show("#trials table created")
cursor.execute("""\
    INSERT INTO #trials (id, doc_type, pub_job, pub_date)
    SELECT d.id, t.name, MIN(e.id), MIN(e.completed)
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
      JOIN published_doc p
        ON p.doc_id = d.id
      JOIN pub_event e
        ON e.id = p.pub_proc
     WHERE t.name in ('InScopeProtocol', 'CTGovProtocol')
       AND e.pub_subset LIKE 'Push_Documents_To_Cancer.Gov%%'
       AND e.pub_subset NOT LIKE '%%-Remove'
  GROUP BY d.id, t.name
    HAVING MIN(e.completed) BETWEEN '%s' AND '%s 23:59:59'""" % (startDate,
                                                                 endDate),
               timeout = 300)
conn.commit()
show("#trials table filled")

#----------------------------------------------------------------------
# Next we create objects for each of the protocols in the report.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT t.id, t.doc_type, t.pub_date, u.name
      FROM #trials t
      JOIN pub_proc_doc d
        ON d.doc_id = t.id
       AND d.pub_proc = t.pub_job
      JOIN doc_version v
        ON v.id = t.id
       AND v.num = d.doc_version
      JOIN usr u
        ON u.id = v.usr""", timeout = 300)
for docId, docType, pubDate, userName in cursor.fetchall():
    p = prots[docId] = Protocol(docId, docType, pubDate, userName)
    if p.docType == 'InScopeProtocol':
        inScope[docId] = p
    else:
        ctGov[docId] = p
show("protocol objects created")

#----------------------------------------------------------------------
# Fill in the protocol status values.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT q.doc_id, q.value
      FROM query_term q
      JOIN #trials t
        ON t.id = q.doc_id
     WHERE path IN ('/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus',
                    '/CTGovProtocol/OverallStatus')""", timeout = 300)
for docId, status in cursor.fetchall():
    status = status.strip()
    statuses[status] = statuses.get(status, 0) + 1
    prots[docId].status = status.strip()
show("status values added")

#----------------------------------------------------------------------
# Fill in the protocol primary IDs.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT q.doc_id, q.value
      FROM query_term q
      JOIN #trials t
        ON t.id = q.doc_id
     WHERE q.path IN ('/InScopeProtocol/ProtocolIDs/PrimaryID/IDString',
                      '/CTGovProtocol/IDInfo/OrgStudyID')""", timeout = 300)
for docId, protId in cursor.fetchall():
    prots[docId].primaryIds.add(protId)
show("primary IDs added")

#----------------------------------------------------------------------
# Fill in the protocol study categories.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT q.doc_id, q.value
      FROM query_term q
      JOIN #trials t
        ON t.id = q.doc_id
     WHERE q.path IN ('/CTGovProtocol/PDQIndexing/StudyCategory' +
                      '/StudyCategoryName',
                      '/InScopeProtocol/ProtocolDetail' +
                      '/StudyCategory/StudyCategoryName')""", timeout = 300)
for docId, value in cursor.fetchall():
    category = value.strip()
    prots[docId].studyCats.add(category)
    categories[category] = categories.get(category, 0) + 1
show("study categories added")

cursor.execute("""\
    SELECT q.doc_id, q.value
      FROM query_term q
      JOIN #trials t
        ON t.id = q.doc_id
     WHERE q.path = '/InScopeProtocol/ProtocolSpecialCategory'
                  + '/SpecialCategory'""", timeout = 300)
for docId, value in cursor.fetchall():
    prots[docId].specialCats.add(value.strip())
show("special categories added")

#----------------------------------------------------------------------
# Next we get the review approval type values.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT q.doc_id, q.value
      FROM query_term q
      JOIN #trials t
        ON t.id = q.doc_id
     WHERE q.path = '/InScopeProtocol/ProtocolApproval'
                  + '/ReviewApprovalType'""", timeout = 300)
for docId, value in cursor.fetchall():
    approval = value.strip()
    prots[docId].reviewApprovalType = approval
    approvals[approval] = approvals.get(approval, 0) + 1
show("review approval types added")

#----------------------------------------------------------------------
# Finally, collect the protocol source names.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT q.doc_id, q.value
      FROM query_term q
      JOIN #trials t
        ON t.id = q.doc_id
     WHERE q.path = '/InScopeProtocol/ProtocolSources/ProtocolSource'
                  + '/SourceName'""", timeout = 300)
for docId, value in cursor.fetchall():
    source = value.strip()
    prots[docId].sourceNames.add(source)
    sources[source] = sources.get(source, 0) + 1
show("protocol source names added")

#----------------------------------------------------------------------
# Create the report.
#----------------------------------------------------------------------
t = time.strftime("%Y%m%d%H%M%S")
if not debug:
    print "Content-type: application/vnd.ms-excel"
    print ("Content-Disposition: attachment; "
           "filename=NewlyPublishedTrials-%s.xls" % t)
    print 

workbook = pyXLWriter.Writer(sys.stdout)
show("workbook created")
hdrFormat = workbook.add_format()
hdrFormat.set_bold()
hdrFormat.set_align('center')
hdrFormat.set_text_wrap(1)
tformat1 = workbook.add_format()
tformat1.set_bold()
tformat1.set_size(16)
tformat1.set_align('center')
tformat1.set_merge(1)
tformat2 = workbook.add_format()
tformat2.set_bold()
tformat2.set_size(12)
tformat2.set_align('left')
#tformat2.set_merge(1)
tformat3 = workbook.add_format()
tformat3.set_bold()
rformat = workbook.add_format()
rformat.set_align('right')
lformat = workbook.add_format()
lformat.set_align('left')
titles  = ('InScope', 'CTGov')
headers = (
    ('DocID', 'ProtocolID','Study Category', 'Special Category',
     'Current\nProtocol\nStatus', 'Source', 'Approval',
     'Date\nPublished', 'User'),
    ('DocID', 'OrgStudyID', 'Study Category', 'Overall\nStatus',
     'Date Published', 'User')
    )
widths  = (
    (9.71, 25.29, 18.43, 18.43, 18.43, 18.43, 18.43, 18, 12),
    (9.71, 25.29, 18.43, 18.43, 18, 12)
    )
addTotalsSheet(workbook, prots, inScope, ctGov)
addWorksheet(workbook, titles[0], headers[0], widths[0], inScope)
show("%s worksheet created" % titles[0])
addWorksheet(workbook, titles[1], headers[1], widths[1], ctGov)
show("%s worksheet created" % titles[1])
workbook.close()
show("done")