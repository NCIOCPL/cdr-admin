#----------------------------------------------------------------------
#
# $Id: Request4176.py,v 1.3 2008-08-21 15:08:26 bkline Exp $
#
# "Once we implement the regulatory information block, I would like  report
# that we can run periodically or is generated weekly that lists the
# following information for trials that have Regulatory Info Block element:
#
#    Original Title
#    Phase
#    Regulatory Information block information
#    FDA IND info (if it exists)"
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2008/08/21 15:06:56  bkline
# Rewritten; Sheri wants a spreadsheet now instead of a web-based
# report, and the users have changed the schema in a way that
# invalidated original logic for finding the RegulatoryInformation
# blocks.
#
# Revision 1.1  2008/08/21 13:28:03  bkline
# Report on trials with regulatory information, implemented in
# accordance with original requirements.
#
#----------------------------------------------------------------------
import cdrdb, xml.dom.minidom, cdr, cgi, cdrcgi, ExcelWriter, time, sys

class Protocol:
    def __init__(self, docId, cursor):
        self.docId = docId
        self.regInfo = None
        self.title = None
        self.phases = []
        self.fdaIndInfo = None
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'ProtocolTitle':
                if node.getAttribute('Type') == 'Original':
                    self.title = cdr.getTextContent(node)
            elif node.nodeName == 'ProtocolPhase':
                self.phases.append(cdr.getTextContent(node))
            elif node.nodeName == 'RegulatoryInformation':
                self.regInfo = Protocol.RegulatoryInformation(node, cursor)
            elif node.nodeName == 'FDAINDInfo':
                self.fdaIndInfo = Protocol.FdaIndInfo(node)
    class RegulatoryInformation:
        def __init__(self, node, cursor):
            self.fdaRegulated = u""
            self.section801 = u""
            self.delayedPosting = u""
            self.responsibleParty = u""
            for child in node.childNodes:
                if child.nodeName == 'FDARegulated':
                    self.fdaRegulated = cdr.getTextContent(child)
                elif child.nodeName == 'Section801':
                    self.section801 = cdr.getTextContent(child)
                elif child.nodeName == 'DelayedPosting':
                    self.delayedPosting = cdr.getTextContent(child)
                elif child.nodeName == 'ResponsibleParty':
                    docId = None
                    for n in child.getElementsByTagName('Person'):
                        docId = n.getAttribute('cdr:ref')
                    for n in child.getElementsByTagName('Organization'):
                        docId = n.getAttribute('cdr:ref')
                    if docId:
                        docId = cdr.exNormalize(docId)[1]
                        cursor.execute("""\
                            SELECT title
                              FROM document
                             WHERE id = ?""", docId)
                        title = cursor.fetchall()[0][0]
                        semicolon = title.find(';')
                        if semicolon:
                            title = title[:semicolon]
                        self.responsibleParty = u"%s (CDR%d)" % (title, docId)
    class FdaIndInfo:
        def __init__(self, node):
            self.indGrantor = u""
            self.indNumber = u""
            self.indSubmissionDate = u""
            self.indSerialNumber = u""
            for child in node.childNodes:
                if child.nodeName == 'INDGrantor':
                    self.indGrantor = cdr.getTextContent(child)
                elif child.nodeName == 'INDNumber':
                    self.indNumber = cdr.getTextContent(child)
                elif child.nodeName == 'INDSubmissionDate':
                    self.indSubmissionDate = cdr.getTextContent(child)
                elif child.nodeName == 'INDSerialNumber':
                    self.indSerialNumber = cdr.getTextContent(child)

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT DISTINCT doc_id
      FROM query_term
     WHERE path LIKE '/InScopeProtocol/RegulatoryInformation/FDARegulated'
  ORDER BY doc_id""")
docIds = [row[0] for row in cursor.fetchall()]
book = ExcelWriter.Workbook()
sheet = book.addWorksheet("Request4176")
font = ExcelWriter.Font(bold = True)
style = book.addStyle(font = font)
sheet.addCol(1, 50)
sheet.addCol(2, 200)
sheet.addCol(3, 75)
sheet.addCol(4, 80)
sheet.addCol(5, 60)
sheet.addCol(6, 120)
sheet.addCol(7, 200)
sheet.addCol(8, 100)
sheet.addCol(9, 100)
sheet.addCol(10, 125)
sheet.addCol(11, 100)
row = sheet.addRow(1, style)
row.addCell(1, u"CDR ID", style)
row.addCell(2, u"Protocol Title", style)
row.addCell(3, u"Phase(s)", style)
row.addCell(4, u"FDA Regulated", style)
row.addCell(5, u"Section 801", style)
row.addCell(6, u"IND Submission Date", style)
row.addCell(7, u"Responsible Party", style)
row.addCell(8, u"IND Grantor", style)
row.addCell(9, u"IND Number", style)
row.addCell(10, u"IND Submission Date", style)
row.addCell(11, u"IND Serial Number", style)
align = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style = book.addStyle(alignment = align)
rowNum = 2
for docId in docIds:
    protocol = Protocol(docId, cursor)
    row = sheet.addRow(rowNum, style)
    rowNum += 1
    row.addCell(1, docId)
    row.addCell(2, protocol.title)
    row.addCell(3, u", ".join(protocol.phases))
    if protocol.regInfo:
        row.addCell(4, protocol.regInfo.fdaRegulated)
        row.addCell(5, protocol.regInfo.section801)
        row.addCell(6, protocol.regInfo.delayedPosting)
        row.addCell(7, protocol.regInfo.responsibleParty)
    if protocol.fdaIndInfo:
        row.addCell(8, protocol.fdaIndInfo.indGrantor)
        row.addCell(9, protocol.fdaIndInfo.indNumber)
        row.addCell(10, protocol.fdaIndInfo.indSubmissionDate)
        row.addCell(11, protocol.fdaIndInfo.indSerialNumber)
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
now = time.strftime("%Y%m%d%H%M%S")
name = "Request4176-%s.xls" % now
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
book.write(sys.stdout, True)
