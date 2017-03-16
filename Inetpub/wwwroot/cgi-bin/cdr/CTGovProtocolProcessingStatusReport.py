#----------------------------------------------------------------------
# New processing report for unpublishable CT.gov protocols.
#
# BZIssue::4804
# BZIssue::5309 (JIRA::OCECDR-3610)
# JIRA::OCECDR-3692
#----------------------------------------------------------------------
import cdr, cdrdb, lxml.etree as etree, time, cdrcgi, sys

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

def addSheet(title, styles, failures, protocols, counts, transferred):
    sheet = styles.add_sheet(title)
    banner = "CTGov Protocol Processing Status Report"
    report_time = time.strftime("%Y-%m-%d %H:%M")
    widths = (10, 20, 20, 20, 40, 20, 20, 20, 10, 20, 25, 50)
    labels = ("CDR ID", "Org Study ID", "NCT ID",
              "CTRP ID", "Processing Status(es)",
              "User", "Processing Start", "Processing End", "Date Created",
              "Phase(s)", "Overall Status", "Comment")
    assert(len(widths) == len(labels))
    for i, chars in enumerate(widths):
        sheet.col(i).width = styles.chars_to_width(chars)
    sheet.write_merge(0, 0, 0, len(widths) - 1, banner, styles.banner)
    sheet.write_merge(1, 1, 0, len(widths) - 1, report_time, styles.header)
    sheet.write_merge(2, 2, 0, len(widths) - 1, "")
    for col, label in enumerate(labels):
        sheet.write(3, col, label, styles.header)

    #--------------------------------------------------------------
    # Populate the sheet.
    #--------------------------------------------------------------
    row = 4
    for i, failure in enumerate(sorted(failures)):
        desc = u"FAILURE: %s" % failure.execption
        sheet.write(row, 0, failure.docId, styles.error)
        sheet.write_merge(row, row, 1, len(widths) - 2, desc, styles.error)
        row += 1
    for i, protocol in enumerate(sorted(protocols)):
        style = protocol.transferred and styles.red or styles.left
        ctrp = None
        if protocol.ctrpId:
            style = styles.blue
            ctrp = protocol.ctrpId
            if protocol.inCtrpTable:
                style = styles.purple
                ctrp += " (X)"
        sheet.write(row, 0, protocol.cdrId, style)
        sheet.write(row, 1, protocol.orgStudyId or "", style)
        sheet.write(row, 2, protocol.nctId or "", style)
        sheet.write(row, 3, ctrp or "", style)
        sheet.write(row, 4, u"; ".join(protocol.procStatuses), style)
        sheet.write(row, 5, protocol.user or "", style)
        sheet.write(row, 6, fixDateTime(protocol.procStart), style)
        sheet.write(row, 7, fixDateTime(protocol.procEnd), style)
        sheet.write(row, 8, fixDate(protocol.dateCreated), style)
        sheet.write(row, 9, u"; ".join(protocol.phases), style)
        sheet.write(row, 10, protocol.protStatus or "", style)
        sheet.write(row, 11, protocol.comment or "", style)
        row += 1

    row += 2
    sheet.write_merge(row, row, 0, 1, "Total Count", styles.bold)
    sheet.write(row, 2, len(protocols), styles.bold)
    row += 1
    for i, status in enumerate(sorted(counts)):
        sheet.write_merge(row, row, 0, 1, status)
        sheet.write(row, 2, counts[status])
        row += 1
    sheet.write_merge(row, row, 0, 1, "Transferred Trials", styles.red)
    sheet.write(row, 2, transferred, styles.red)

def main():
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()

    #--------------------------------------------------------------
    # Create the styles and workbook.
    #--------------------------------------------------------------
    styles = cdrcgi.ExcelStyles()

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
    addSheet('Unpublished', styles, failures, protocols, counts,
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
    addSheet("Published - need admin info", styles, failures, protocols,
             counts, transferredCount)

    #--------------------------------------------------------------
    # Send the workbook back to the user.
    #--------------------------------------------------------------
    stamp = time.strftime("%Y%m%d%H%M%S")
    name = "procstat-%s.xls" % stamp
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=%s" % name
    print
    styles.book.save(sys.stdout)

if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        cdrcgi.bail("whoops: %s" % e)
