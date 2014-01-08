#----------------------------------------------------------------------
#
# $Id$
#
# New processing report for unpublishable CT.gov protocols.
#
# BZIssue::4804
# BZIssue::5309 (JIRA::OCECDR-3610)
# JIRA::OCECDR-3692)
#
#----------------------------------------------------------------------
import cdr, ExcelWriter, cdrdb, lxml.etree as etree, time, cdrcgi, sys

try:
    import msvcrt, os
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
except:
    pass

LOGFILE = 'd:/cdr/Log/Reports.log'
FIRST_DATA_ROW = 5

def getCreationDate(cursor, cdrId):
    cursor.execute("""\
        SELECT MIN(v.dt)
          FROM doc_version v
          JOIN doc_type t
            ON t.id = v.doc_type
         WHERE v.id = ?
           AND t.name = 'CTGovProtocol'""", cdrId, timeout=300)
    rows = cursor.fetchall()
    if rows:
        return rows[0][0]
    cursor.execute("""\
        SELECT MIN(dt)
          FROM audit_trail
         WHERE document = ?""", cdrId)
    rows = cursor.fetchall()
    return rows and rows[0][0] or None

def fixDate(d):
    if not d:
        return ""
    if len(d) > 10:
        return d[:10]
    return d

def fixDateTime(d):
    if not d:
        return ""
    if len(d) > 10:
        return d[:10] + 'T' + d[11:]
    return d

class Failure:
    def __init__(self, docId, exception):
        self.docId = docId
        self.exception = exception
    def __cmp__(self, other):
        return cmp(self.docId, other.docId)

class CTGovProtocol:
    def __init__(self, cursor, cdrId):
        self.cdrId        = cdrId
        self.dateCreated  = getCreationDate(cursor, cdrId)
        self.orgStudyId   = None
        self.nctId        = None
        self.user         = None
        self.procStatuses = []
        self.procStart    = None
        self.procEnd      = None
        self.comment      = None
        self.protStatus   = None
        self.phases       = []
        self.transferred  = False
        self.ctrpId       = None
        self.inCtrpTable  = False
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
        rows = cursor.fetchall()
        tree = etree.XML(rows[0][0].encode('utf-8'))
        # debugging failure handling code
        # if cdrId in (447161, 670939):
        #     tree = etree.XML("<bogus>" + rows[0][0].encode('utf-8'))
        haveProtocolProcessingDetails = False
        for node in tree:
            if node.tag == 'IDInfo':
                for child in node:
                    if child.tag == 'OrgStudyID':
                        self.orgStudyId = child.text
                    elif child.tag == 'NCTID':
                        self.nctId = child.text
            elif node.tag == 'ProtocolProcessingDetails':
                if haveProtocolProcessingDetails:
                    continue # William only wants info from the first block
                haveProtocolProcessingDetails = True
                for child in node:
                    if child.tag == 'ProcessingStatus':
                        if child.text:
                            self.procStatuses.append(child.text)
                    elif child.tag == 'EnteredBy':
                        self.user = child.text
                    elif child.tag == 'ProcessingStartDateTime':
                        self.procStart = child.text
                    elif child.tag == 'ProcessingEndDateTime':
                        self.procEnd = child.text
                    elif child.tag == 'Comment':
                        self.comment = child.text
            elif node.tag == 'Phase':
                if node.text:
                    self.phases.append(node.text)
            elif node.tag == 'OverallStatus':
                self.protStatus = node.text
            elif node.tag == 'PDQAdminInfo':
                for child in node.findall('CTGovOwnershipTransferInfo'):
                    self.transferred = True
        if self.nctId:
            cursor.execute("SELECT ctrp_id FROM ctgov_import WHERE nlm_id = ?",
                           self.nctId)
            rows = cursor.fetchall()
            if rows:
                self.ctrpId = rows[0][0]
                if self.ctrpId:
                    cursor.execute("""\
SELECT COUNT(*) FROM ctrp_import WHERE ctrp_id = ?""", self.ctrpId)
                    self.inCtrpTable = cursor.fetchall()[0][0] > 0
                           
    def __cmp__(self, other):
        diff = cmp(other.phases, self.phases)
        if diff:
            return diff
        return cmp(self.dateCreated, other.dateCreated)

class Styles:
    def __init__(self, bk):
        font = ExcelWriter.Font(name='Arial', size=10)
        self.normal = bk.addStyle(font=font)
        self.date = bk.addStyle(font=font, numFormat='YYYY-mm-dd')
        self.datetime = bk.addStyle(font=font, numFormat='YYYY-mm-dd HH:MM:SS')
        font = ExcelWriter.Font(color='#FF0000', name='Arial', size=10)
        self.red = bk.addStyle(font=font)
        font = ExcelWriter.Font(color='#7E354D', name='Arial', size=10)
        self.maroon = bk.addStyle(font=font)
        font = ExcelWriter.Font(color='#800000', name='Arial', size=10)
        self.maroon = bk.addStyle(font=font)
        font = ExcelWriter.Font(color='#8C001A', name='Arial', size=10)
        self.burgundy = bk.addStyle(font=font)
        font = ExcelWriter.Font(color='#0000FF', name='Arial', size=10)
        self.blue = bk.addStyle(font=font)
        font = ExcelWriter.Font(name='Arial', size=10, bold=True)
        self.bold = bk.addStyle(font=font)
        font = ExcelWriter.Font(name='Arial', size=10, bold=True,
                                color='#FF0000')
        self.error = bk.addStyle(font=font)
        align = ExcelWriter.Alignment('Center', 'Center', wrap=True)
        bg = ExcelWriter.Interior('#DDD9C3')
        self.label = bk.addStyle(alignment=align, font=font, interior=bg)
        font = ExcelWriter.Font(name='Arial', size=12, bold=True)
        self.title = bk.addStyle(alignment=align, font=font)

def addSheet(book, title, styles, failures, protocols, counts, transferred):
    first_data_row = 5
    sheet = book.addWorksheet(title, styles.normal)
    widths = (60, 100, 100, 100, 200, 100, 100, 100, 60, 100, 100, 350)
    labels = ('CDR ID', 'Org Study ID', 'NCT ID',
              'CTRP ID', 'Processing Status(es)',
              'User', 'Processing Start', 'Processing End', 'Date Created',
              'Phase(s)', 'Overall Status', 'Comment')
    for i, width in enumerate(widths):
        sheet.addCol(i + 1, width)
    row = sheet.addRow(1, styles.title)
    row.addCell(1, "CTGov Protocol Processing Status Report", mergeAcross=10)
    row = sheet.addRow(2, styles.title)
    row.addCell(1, time.strftime("%Y-%m-%d %H:%M"), mergeAcross=10)
    row = sheet.addRow(4, styles.label)
    for i, label in enumerate(labels):
        row.addCell(i + 1, label)

    #--------------------------------------------------------------
    # Populate the sheet.
    #--------------------------------------------------------------
    for i, failure in enumerate(failures):
        row = sheet.addRow(i + first_data_row, styles.error)
        row.addCell(1, failure.docId)
        row.addCell(2, u"FAILURE: %s" % failure.exception, mergeAcross=9)
    first_data_row += len(failures)
    for i, protocol in enumerate(protocols):
        style = protocol.transferred and styles.red or styles.normal
        ctrp = None
        if protocol.ctrpId:
            style = styles.blue
            ctrp = protocol.ctrpId
            if protocol.inCtrpTable:
                style = styles.burgundy
                ctrp += " (X)"
        row = sheet.addRow(i + first_data_row, style)
        row.addCell(1, protocol.cdrId)
        if protocol.orgStudyId:
            row.addCell(2, protocol.orgStudyId)
        if protocol.nctId:
            row.addCell(3, protocol.nctId)
        if ctrp:
            row.addCell(4, ctrp)
        if protocol.procStatuses:
            row.addCell(5, u"; ".join(protocol.procStatuses))
        if protocol.user:
            row.addCell(6, protocol.user)
        if protocol.procStart:
            row.addCell(7, fixDateTime(protocol.procStart))
        if protocol.procEnd:
            row.addCell(8, fixDateTime(protocol.procEnd))
        if protocol.dateCreated:
            row.addCell(9, fixDate(protocol.dateCreated))
        if protocol.phases:
            row.addCell(10, u"; ".join(protocol.phases))
        if protocol.protStatus:
            row.addCell(11, protocol.protStatus)
        if protocol.comment:
            row.addCell(12, protocol.comment)

    row = sheet.addRow(first_data_row + 2 + len(protocols), styles.bold)
    row.addCell(1, "Total Count", mergeAcross=1)
    row.addCell(3, len(protocols), "Number")
    statuses = counts.keys()
    statuses.sort()
    for i, status in enumerate(statuses):
        row = sheet.addRow(first_data_row + len(protocols) + 3 + i)
        row.addCell(1, status, mergeAcross=1)
        row.addCell(3, counts[status], "Number")
    row = sheet.addRow(first_data_row + len(protocols) + 3 + len(counts),
                       styles.red)
    row.addCell(1, "Transferred Trials", mergeAcross=1)
    row.addCell(3, transferred, "Number")

def main():
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()

    #--------------------------------------------------------------
    # Create the workbook.
    #--------------------------------------------------------------
    book = ExcelWriter.Workbook()
    styles = Styles(book)

    #--------------------------------------------------------------
    # Collect the protocol information for the first sheet.
    #--------------------------------------------------------------
    counts = {}
    transferredCount = 0
    cursor.execute("""\
             SELECT DISTINCT v.id
               FROM doc_version v
               JOIN doc_type t
                 ON v.doc_type = t.id
              WHERE t.name = 'CTGovProtocol'
                AND v.publishable = 'Y'""", timeout=300)
    publishable = set([row[0] for row in cursor.fetchall()])
    #print "noted %d publishable docs" % len(publishable)
    cursor.execute("""\
            SELECT a.id
              FROM active_doc a
              JOIN doc_type t
                ON t.id = a.doc_type
             WHERE t.name = 'CTGovProtocol'""", timeout=300)
    protocols = []
    failures = []
    rows = cursor.fetchall()
    #print "%d rows fetched" % len(rows)
    for row in rows:
        docId = row[0]
        if docId not in publishable:
            try:
                protocol = CTGovProtocol(cursor, docId)
                if protocol.transferred:
                    transferredCount += 1
                for status in protocol.procStatuses:
                    counts[status] = counts.get(status, 0) + 1
                protocols.append(protocol)
            except Exception, e:
                failures.append(Failure(docId, e))
                cdr.logwrite("CDR%d: %s" % (docId, e), LOGFILE)
    protocols.sort()
    failures.sort()
    addSheet(book, 'Unpublished', styles, failures, protocols, counts,
             transferredCount)

    #--------------------------------------------------------------
    # Create the sheet for OCECDR-3692.
    #--------------------------------------------------------------
    counts = {}
    transferredCount = 0
    protocols = []
    failures = []
    cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path = '/CTGovProtocol/ProtocolProcessingDetails'
                     + '/ProcessingStatus'
            AND value = 'Published - need admin info'""", timeout=300)
    rows = cursor.fetchall()
    for row in rows:
        docId = row[0]
        try:
            protocol = CTGovProtocol(cursor, docId)
            if protocol.transferred:
                transferredCount += 1
            for status in protocol.procStatuses:
                counts[status] = counts.get(status, 0) + 1
            protocols.append(protocol)
        except Exception, e:
            failures.append(Failure(docId, e))
            cdr.logwrite("CDR%d: %s" % (docId, e), LOGFILE)
    protocols.sort()
    failures.sort()
    addSheet(book, "Published - need admin info", styles, failures, protocols,
             counts, transferredCount)

    #--------------------------------------------------------------
    # Send the workbook back to the user.
    #--------------------------------------------------------------
    stamp = time.strftime("%Y%m%d%H%M%S")
    name = "procstat-%s.xls" % stamp
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=%s" % name
    print
    book.write(sys.stdout, True)

if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        cdrcgi.bail("whoops: %s" % e)
