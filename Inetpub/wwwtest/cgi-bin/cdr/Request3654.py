#----------------------------------------------------------------------
#
# $Id: Request3654.py,v 1.1 2008-09-02 20:58:57 bkline Exp $
#
# Scientific Protocol Tracking Report.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import cdrdb, sys, cdr, ExcelWriter, xml.dom.minidom, time

debugging = len(sys.argv) > 1 and 'debug' in sys.argv[1].lower()

class ScientificProtocolTrackingReport:
    def run(self, job):
        cursor = cdrdb.connect('CdrGuest').cursor()
        cursor.execute("""\
            SELECT d.id
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE t.name = 'ScientificProtocolInfo'
               AND d.active_status = 'A'""", timeout = 300)
        docIds = [row[0] for row in cursor.fetchall()]
        protocols = []
        statuses = {}
        for docId in docIds:
            protocol = self.Protocol(docId, cursor)
            protocols.append(protocol)
            if debugging:
                sys.stderr.write("parsed CDR%d (%d of %d)\n" % (docId,
                                                                len(protocols),
                                                                len(docIds)))
            for statusInfo in protocol.statusInfo:
                val = statusInfo.status
                statuses[val] = statuses.get(val, 0) + 1
        protocols.sort()
        book = ExcelWriter.Workbook()
        styles = self.Styles(book)
        sheet = book.addWorksheet(u"Summary")
        sheet.addCol(1, 125)
        sheet.addCol(2, 25)
        row = sheet.addRow(1, styles.header)
        row.addCell(1, u"Processing Status Values")
        row = sheet.addRow(3, styles.header)
        row.addCell(1, u"Total Trials: %d" % len(protocols))
        rowNum = 5
        keys = statuses.keys()
        keys.sort()
        for key in keys:
            row = sheet.addRow(rowNum)
            row.addCell(1, key, style = styles.left)
            row.addCell(2, statuses[key], style = styles.right)
            rowNum += 1
            if debugging:
                sys.stderr.write("added status %s\n" % key)
        headers = (u"CDR Inscope ID", u"CDR Scientific ID",
                   u"PDQ Primary ID", u"Processing Status", u"User",
                   u"Processing Start Date", u"Processing End Date",
                   u"Date Received", u"Date Submission Complete",
                   u"Processing Priority", u"Missing Information",
                   u"Primary Lead Organization Status",
                   u"CTGov Duplicate")
        sheet = book.addWorksheet(u"Trials in Process")
        col = 1
        row = sheet.addRow(1, styles.header)
        for header in headers:
            sheet.addCol(col, 100)
            row.addCell(col, header)
            col += 1
        rowNum = 2
        for protocol in protocols:
            si = protocol.reportableStatusInfo
            ps = self.__makeVal([i.status for i in si])
            users = self.__makeVal([i.user for i in si])
            start = self.__makeVal([i.startDate for i in si])
            end = self.__makeVal([i.endDate for i in si])
            rcvd = self.__makeVal(protocol.datesReceived)
            sub = self.__makeVal(protocol.datesSubmissionComplete)
            mi = self.__makeVal(protocol.missingInfo)
            priorities = []
            for i in si:
                priorities += i.priorities
            pr = self.__makeVal(priorities)
            row = sheet.addRow(rowNum, style = styles.left)
            row.addCell(1, protocol.inScopeId)
            row.addCell(2, protocol.docId)
            row.addCell(3, protocol.primaryId)
            row.addCell(4, ps)
            row.addCell(5, users)
            row.addCell(6, start)
            row.addCell(7, end)
            row.addCell(8, rcvd)
            row.addCell(9, sub)
            row.addCell(10, pr)
            row.addCell(11, mi)
            row.addCell(12, protocol.currentOrgStatus)
            row.addCell(13, protocol.ctGovDuplicate)
            rowNum += 1
        now = time.strftime("%Y%m%d%H%M%S")
        filename = "ScientificProtocolProcessingReport-%s.xls" % now
        if debugging:
            fp = open(filename, 'wb')
        else:
            fp = sys.stdout
            print "Content-type: application/vnd.ms-excel"
            print "Content-Disposition: attachment; filename=%s" % filename
            print
        book.write(fp, True)
        if debugging:
            fp.close()

    @staticmethod
    def __makeVal(vals):
        vals = list(set(vals))
        vals.sort()
        return u"; ".join([unicode(val) for val in vals])
        
    class Protocol:
        class StatusInfo:
            def __init__(self, node):
                self.status = None
                self.user = None
                self.startDate = None
                self.endDate = None
                self.priorities = []
                for child in node.childNodes:
                    if child.nodeName == 'ProcessingStatus':
                        self.status = cdr.getTextContent(child).strip()
                    elif child.nodeName == 'ProcessingPriority':
                        priority = cdr.getTextContent(child).strip()
                        if priority:
                            self.priorities.append(priority)
                    elif child.nodeName == 'StartDateTime':
                        self.startDate = cdr.getTextContent(child).strip()
                    elif child.nodeName == 'EndDateTime':
                        self.endDate = cdr.getTextContent(child).strip()
                    elif child.nodeName == 'User':
                        self.user = cdr.getTextContent(child).strip()
            def __cmp__(self, other):
                """
                Latest dates go before earlier dates.  Blocks with no
                StartDate value go before blocks with a StartDate value.
                """
                if not self.startDate:
                    if other.startDate:
                        return -1
                    return 0
                if not other.startDate:
                    return 1
                return cmp(other.startDate, self.startDate)
        def __init__(self, docId, cursor):
            self.docId = docId
            self.inScopeId = None
            self.primaryId = None
            self.statusInfo = []
            self.reportableStatusInfo = []
            self.datesReceived = []
            self.datesSubmissionComplete = []
            self.missingInfo = []
            self.currentOrgStatus = None
            self.ctGovDuplicate = None
            self.__parseScientificDoc(docId, cursor)
            if self.inScopeId:
                self.__parseInScopeDoc(self.inScopeId, cursor)
            self.datesSubmissionComplete.sort()
            self.datesSubmissionComplete.reverse()
            self.statusInfo.sort()
            latestStartDate = None
            for si in self.statusInfo:
                if not latestStartDate:
                    latestStartDate = si.startDate
                if si.startDate == latestStartDate:
                    self.reportableStatusInfo.append(si)
        def __cmp__(self, other):
            return cmp(self.datesSubmissionComplete,
                       other.datesSubmissionComplete)
        def __parseScientificDoc(self, docId, cursor):
            cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
            docXml = cursor.fetchall()[0][0]
            dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
            for node in dom.documentElement.childNodes:
                if node.nodeName == 'InScopeDocID':
                    inScopeIdString = node.getAttribute('cdr:ref')
                    try:
                        self.inScopeId = cdr.exNormalize(inScopeIdString)[1]
                    except:
                        pass
                elif node.nodeName == 'ProtocolIDs':
                    for child in node.childNodes:
                        if child.nodeName == 'PrimaryID':
                            for grandchild in child.childNodes:
                                if grandchild.nodeName == 'IDString':
                                    p = cdr.getTextContent(grandchild).strip()
                                    if p:
                                        self.primaryId = p
                elif node.nodeName == 'ProtocolProcessingDetails':
                    for child in node.childNodes:
                        if child.nodeName == 'ProcessingStatuses':
                            for gc in child.childNodes:
                                if gc.nodeName == 'ProcessingStatusInfo':
                                    psi = self.StatusInfo(gc)
                                    self.statusInfo.append(psi)
                        elif child.nodeName == 'MissingRequiredInformation':
                            for gc in child.childNodes:
                                if gc.nodeName == 'MissingInformation':
                                    mi = cdr.getTextContent(gc).strip()
                                    if mi:
                                        self.missingInfo.append(mi)
        def __parseInScopeDoc(self, docId, cursor):
            cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
            docXml = cursor.fetchall()[0][0]
            dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
            for node in dom.documentElement.childNodes:
                if node.nodeName == 'ProtocolSources':
                    for child in node.childNodes:
                        if child.nodeName == 'ProtocolSource':
                            self.__parseProtocolSource(child)
                elif node.nodeName == 'ProtocolAdminInfo':
                    for child in node.childNodes:
                        if child.nodeName == 'ProtocolLeadOrg':
                            if not self.currentOrgStatus:
                                self.__parseLeadOrg(child)
                elif node.nodeName == 'CTGovDuplicate':
                    cdrId = node.getAttribute('cdr:ref')
                    if cdrId:
                        self.ctGovDuplicate = cdr.exNormalize(cdrId)[1]
        def __parseLeadOrg(self, node):
            leadOrgRole = None
            currentOrgStatus = None
            for child in node.childNodes:
                if child.nodeName == 'LeadOrgRole':
                    leadOrgRole = cdr.getTextContent(child)
                elif child.nodeName == 'LeadOrgProtocolStatuses':
                    for grandchild in child.childNodes:
                        if grandchild.nodeName == 'CurrentOrgStatus':
                            for greatGrandchild in grandchild.childNodes:
                                if greatGrandchild.nodeName == 'StatusValue':
                                    val = cdr.getTextContent(greatGrandchild)
                                    if val:
                                        currentOrgStatus = val
            if leadOrgRole == 'Primary' and currentOrgStatus:
                self.currentOrgStatus = currentOrgStatus
                                        
        def __parseProtocolSource(self, node):
            for child in node.childNodes:
                if child.nodeName == 'DateReceived':
                    dr = cdr.getTextContent(child).strip()
                    if dr:
                        self.datesReceived.append(dr)
                elif child.nodeName == 'DateSubmissionComplete':
                    dsc = cdr.getTextContent(child).strip()
                    if dsc:
                        self.datesSubmissionComplete.append(dsc)
                                              
    class Styles:
        def __init__(self, wb):

            # Create the style for the title of a sheet.
            font        = ExcelWriter.Font(name = 'Arial', size = 16,
                                           bold = True)
            align       = ExcelWriter.Alignment('Center', 'Center')
            self.title  = wb.addStyle(alignment = align, font = font)

            # Create the style for the column headers.
            font        = ExcelWriter.Font(name = 'Arial', size = 10,
                                           bold = True, color = 'green')
            align       = ExcelWriter.Alignment('Center', 'Center', True)
            self.header = wb.addStyle(alignment = align, font = font)

            # Create the style for the linking cells.
            font        = ExcelWriter.Font('blue', None, 'Arial', size = 10)
            align       = ExcelWriter.Alignment('Left', 'Top', True)
            self.url    = wb.addStyle(alignment = align, font = font)

            # Create the style for the left-aligned cells.
            font        = ExcelWriter.Font(name = 'Arial', size = 10)
            self.left   = wb.addStyle(alignment = align, font = font)

            # Create the style for the centered cells.
            align       = ExcelWriter.Alignment('Center', 'Top', True)
            self.center = wb.addStyle(alignment = align, font = font)

            # Create the style for the right-aligned cells.
            align       = ExcelWriter.Alignment('Right', 'Top', True)
            self.right  = wb.addStyle(alignment = align, font = font)

if sys.platform == "win32":
   import os, msvcrt
   msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

report = ScientificProtocolTrackingReport()
report.run(None)
