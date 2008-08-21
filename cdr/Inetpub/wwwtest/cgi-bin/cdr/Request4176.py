#----------------------------------------------------------------------
#
# $Id: Request4176.py,v 1.1 2008-08-21 13:28:03 bkline Exp $
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
#----------------------------------------------------------------------
import cdrdb, xml.dom.minidom, cdr, cgi, cdrcgi

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
                elif child.nodeName == 'indSerialNumber':
                    self.indSerialNumber = cdr.getTextContent(child)

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
    SELECT DISTINCT doc_id
      FROM query_term
     WHERE path LIKE '/InScopeProtocol/RegulatoryInformation' +
                     '/ResponsibleParty/Responsible[PO]%on/[PO]%on/@cdr:ref'
  ORDER BY doc_id""")
docIds = [row[0] for row in cursor.fetchall()]
html = [u"""\
<html>
 <head>
  <title>Protocols with Regulatory Info Block</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   h1   { font-size: 1.2em; color: maroon; }
   .line { clear: both; }
   .label { float: left; text-align: right; width: 200px;
            color: blue; font-weight: bold;  }
   .value { margin-left: 220px; }
   .doc { border-top: solid blue 1px; clear: left; }
  </style>
 </head>
 <body>
  <h1>Protocols with Regulatory Info Block</h1>
"""]
for docId in docIds:
    protocol = Protocol(docId, cursor)
    html.append(u"""\
  <div class='doc'>
   <div class='line'>
    <div class='label'>Document ID</div>
    <div class='value'>CDR%s</div>
   </div>
   <div class='line'>
    <div class='label'>Protocol Title</div>
    <div class='value'>%s</div>
   </div>
""" % (docId, cgi.escape(protocol.title)))
    for phase in protocol.phases:
        html.append(u"""\
   <div class='line'>
    <div class='label'>Phase</div>
    <div class='value'>%s</div>
   </div>
""" % cgi.escape(phase))
    fdaRegulated = section801 = delayedPosting = responsibleParty = u""
    if protocol.regInfo:
        fdaRegulated = cgi.escape(protocol.regInfo.fdaRegulated)
        section801 = cgi.escape(protocol.regInfo.section801)
        delayedPosting = cgi.escape(protocol.regInfo.delayedPosting)
        responsibleParty = cgi.escape(protocol.regInfo.responsibleParty)
    html.append(u"""\
   <div class='line'>
    <div class='label'>FDA Regulated</div>
    <div class='value'>%s</div>
   </div>
   <div class='line'>
    <div class='label'>Section 801</div>
    <div class='value'>%s</div>
   </div>
   <div class='line'>
    <div class='label'>IND Submission Date</div>
    <div class='value'>%s</div>
   </div>
   <div class='line'>
    <div class='label'>Responsible Party</div>
    <div class='value'>%s</div>
   </div>
""" % (fdaRegulated, section801, delayedPosting, responsibleParty))
    if protocol.fdaIndInfo:
        html.append(u"""\
   <div class='line'>
    <div class='label'>IND Grantor</div>
    <div class='value'>%s</div>
   </div>
   <div class='line'>
    <div class='label'>IND Number</div>
    <div class='value'>%s</div>
   </div>
   <div class='line'>
    <div class='label'>IND Submission Date</div>
    <div class='value'>%s</div>
   </div>
   <div class='line'>
    <div class='label'>IND Serial Number</div>
    <div class='value'>%s</div>
   </div>
""" % (cgi.escape(protocol.fdaIndInfo.indGrantor),
       cgi.escape(protocol.fdaIndInfo.indNumber),
       cgi.escape(protocol.fdaIndInfo.indSubmissionDate),
       cgi.escape(protocol.fdaIndInfo.indSerialNumber)))
    html.append(u"""\
  </div>
""")
html.append(u"""\
 </body>
</html>""")
html = u"".join(html)
cdrcgi.sendPage(html)
