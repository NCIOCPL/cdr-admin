#----------------------------------------------------------------------
#
# $Id$
#
# New processing report for unpublishable CT.gov protocols.
#
# BZIssue::4804
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
                    continue # William only wants onfo from the first block
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
    def __cmp__(self, other):
        diff = cmp(other.phases, self.phases)
        if diff:
            return diff
        return cmp(self.dateCreated, other.dateCreated)

def main():
    global FIRST_DATA_ROW
    counts = {}
    transferredCount = 0
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()

    #--------------------------------------------------------------
    # Collect the protocol information.
    #--------------------------------------------------------------
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

    #--------------------------------------------------------------
    # Create the workbook.
    #--------------------------------------------------------------
    book = ExcelWriter.Workbook()
    font = ExcelWriter.Font(name='Arial', size=10)
    normalStyle = book.addStyle(font=font)
    font = ExcelWriter.Font(color='#FF0000', name='Arial', size=10)
    redStyle = book.addStyle(font=font)
    dateStyle = book.addStyle(font=font, numFormat='YYYY-mm-dd')
    datetimeStyle = book.addStyle(font=font, numFormat='YYYY-mm-dd HH:MM:SS')
    font = ExcelWriter.Font(name='Arial', size=10, bold=True)
    boldStyle = book.addStyle(font=font)
    font = ExcelWriter.Font(name='Arial', size=10, bold=True, color='#FF0000')
    errorStyle = book.addStyle(font=font)
    align = ExcelWriter.Alignment('Center', 'Center', wrap=True)
    background = ExcelWriter.Interior('#DDD9C3')
    labelStyle = book.addStyle(alignment=align, font=font, interior=background)
    font = ExcelWriter.Font(name='Arial', size=12, bold=True)
    titleStyle = book.addStyle(alignment=align, font=font)
    sheet = book.addWorksheet('CTGov', normalStyle)
    widths = (60, 100, 100, 200, 100, 100, 100, 60, 100, 100, 350)
    labels = ('CDR ID', 'Org Study ID', 'NCT ID', 'Processing Status(es)',
              'User', 'Processing Start', 'Processing End', 'Date Created',
              'Phase(s)', 'Overall Status', 'Comment')
    for i, width in enumerate(widths):
        sheet.addCol(i + 1, width)
    row = sheet.addRow(1, titleStyle)
    row.addCell(1, "CTGov Protocol Processing Status Report", mergeAcross=10)
    row = sheet.addRow(2, titleStyle)
    row.addCell(1, time.strftime("%Y-%m-%d %H:%M"), mergeAcross=10)
    row = sheet.addRow(4, labelStyle)
    for i, label in enumerate(labels):
        row.addCell(i + 1, label)

    #--------------------------------------------------------------
    # Populate the report.
    #--------------------------------------------------------------
    for i, failure in enumerate(failures):
        row = sheet.addRow(i + FIRST_DATA_ROW, errorStyle)
        row.addCell(1, failure.docId)
        row.addCell(2, u"FAILURE: %s" % failure.exception, mergeAcross=9)
    FIRST_DATA_ROW += len(failures)
    for i, protocol in enumerate(protocols):
        row = sheet.addRow(i + FIRST_DATA_ROW,
                           protocol.transferred and redStyle or normalStyle)
        row.addCell(1, protocol.cdrId)
        if protocol.orgStudyId:
            row.addCell(2, protocol.orgStudyId)
        if protocol.nctId:
            row.addCell(3, protocol.nctId)
        if protocol.procStatuses:
            row.addCell(4, u"; ".join(protocol.procStatuses))
        if protocol.user:
            row.addCell(5, protocol.user)
        if protocol.procStart:
            row.addCell(6, fixDateTime(protocol.procStart))
        if protocol.procEnd:
            row.addCell(7, fixDateTime(protocol.procEnd))
        if protocol.dateCreated:
            row.addCell(8, fixDate(protocol.dateCreated))
        if protocol.phases:
            row.addCell(9, u"; ".join(protocol.phases))
        if protocol.protStatus:
            row.addCell(10, protocol.protStatus)
        if protocol.comment:
            row.addCell(11, protocol.comment)

    row = sheet.addRow(FIRST_DATA_ROW + 2 + len(protocols), boldStyle)
    row.addCell(1, "Total Count", mergeAcross=1)
    row.addCell(3, len(protocols), "Number")
    statuses = counts.keys()
    statuses.sort()
    for i, status in enumerate(statuses):
        row = sheet.addRow(FIRST_DATA_ROW + len(protocols) + 3 + i)
        row.addCell(1, status, mergeAcross=1)
        row.addCell(3, counts[status], "Number")
    row = sheet.addRow(FIRST_DATA_ROW + len(protocols) + 3 + len(counts),
                       redStyle)
    row.addCell(1, "Transferred Trials", mergeAcross=1)
    row.addCell(3, transferredCount, "Number")
    stamp = time.strftime("%Y%m%d%H%M%S")
    name = "procstat-%s.xls" % stamp
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=%s" % name
    print
    book.write(sys.stdout, True)

if __name__ == '__main__':
    main()
