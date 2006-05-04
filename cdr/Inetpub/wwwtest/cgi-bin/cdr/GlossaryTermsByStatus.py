#----------------------------------------------------------------------
#
# $Id: GlossaryTermsByStatus.py,v 1.3 2006-05-04 13:59:06 bkline Exp $
#
# The Glossary Terms by Status Report will server as a QC report to check
# which glossary terms were created within a given time frame with a
# particular status set.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2005/08/18 15:00:04  bkline
# Modifications request by Sheri (#1790).
#
# Revision 1.1  2004/10/07 21:39:33  bkline
# Added new report for Sheri, for finding glossary terms created in a
# given date range, and having specified status.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, string, time, xml.dom.minidom, xml.sax.saxutils

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
status   = fields and fields.getvalue("status") or None
session  = fields and fields.getvalue("Session") or None
request  = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate') or None
lang     = fields and fields.getvalue('lang') or None
title    = "CDR Administration"
instr    = "Glossary Terms by Status"
buttons  = ["Submit Request", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
script   = "GlossaryTermsByStatus.py"
header   = cdrcgi.header(title, title, instr, script, buttons)

#----------------------------------------------------------------------
# Handle requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out": 
    cdrcgi.logout(session)

def getOptions(lang):
    if not lang:
        return """\
       <OPTION VALUE='Approved'>Approved</OPTION>
       <OPTION VALUE='Pending'>Pending</OPTION>
       <OPTION VALUE='Revision pending'>Revision pending</OPTION>"""
    else:
        return ("""\
       <OPTION VALUE='Translation approved'>Translation approved</OPTION>
       <OPTION VALUE='Translation pending'>Translation pending</OPTION>
       <OPTION VALUE='Translation revision pending'>"""
                """Translation revision pending</OPTION>""")

#----------------------------------------------------------------------
# As the user for the report parameters.
#----------------------------------------------------------------------
if not fromDate or not toDate or not status:
    now         = time.localtime(time.time())
    toDateNew   = time.strftime("%Y-%m-%d", now)
    then        = list(now)
    then[1]    -= 1
    then[2]    += 1
    then        = time.localtime(time.mktime(then))
    fromDateNew = time.strftime("%Y-%m-%d", then)
    toDate      = toDate or toDateNew
    fromDate    = fromDate or fromDateNew
    form        = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2002-01-01)</TD>
    </TR>
    <TR>
     <TD><B>End Date:&nbsp;</B></TD>
     <TD><INPUT NAME='ToDate' VALUE='%s'>&nbsp;</TD>
    </TR>
    <TR>
     <TD COLSPAN='2'>and select:</TD>
    </TR>
    <TR>
     <TD><B>Term Status:&nbsp;</TD>
     <TD>
      <SELECT NAME='status'>
       <OPTION VALUE=''>Select One</OPTION>
%s      </SELECT>
     </TD>
    </TR>
   </TABLE>
   <INPUT TYPE='hidden' NAME='lang' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, fromDate, toDate, getOptions(lang), lang or "")
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Escape markup special characters.
#----------------------------------------------------------------------
def fix(me):
    if not me:
        return u"&nbsp;"
    return me # xml.sax.saxutils.escape(me)

#----------------------------------------------------------------------
# Prepare definitions for display.
#----------------------------------------------------------------------
def fixList(defs):
    if not defs:
        return u"&nbsp;"
    return fix(u"; ".join(defs))

#----------------------------------------------------------------------
# Extract the complete content of an element, tags and all.
#----------------------------------------------------------------------
def getNodeContent(node, pieces = None):
    if pieces is None:
        pieces = []
    for child in node.childNodes:
        if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
            if child.nodeValue:
                pieces.append(xml.sax.saxutils.escape(child.nodeValue))
        elif child.nodeType == child.ELEMENT_NODE:
            if child.nodeName == 'Insertion':
                pieces.append(u"<span style='color: red'>")
                getNodeContent(child, pieces)
                pieces.append(u"</span>")
            elif child.nodeName == 'Deletion':
                pieces.append(u"<span style='text-decoration: line-through'>")
                getNodeContent(child, pieces)
                pieces.append(u"</span>")
            elif child.nodeName == 'Strong':
                pieces.append(u"<b>")
                getNodeContent(child, pieces)
                pieces.append(u"</b>")
            elif child.nodeName in ('Emphasis', 'ScientificName'):
                pieces.append(u"<i>")
                getNodeContent(child, pieces)
                pieces.append(u"</i>")
            else:
                getNodeContent(child, pieces)
    return u"".join(pieces)

#----------------------------------------------------------------------
# Create/display the report.
#----------------------------------------------------------------------
revisionInfo = status.upper() == 'REVISION PENDING'
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

if lang:
    cursor.execute("""\
    SELECT DISTINCT d.doc_id, d.value
               FROM query_term d
               JOIN query_term s
                 ON d.doc_id = s.doc_id
                AND LEFT(d.node_loc, 4) = LEFT(s.node_loc, 4)
              WHERE d.path = '/GlossaryTerm/SpanishTermDefinition/StatusDate'
                AND s.path = '/GlossaryTerm/SpanishTermDefinition'
                           + '/DefinitionStatus'
                AND s.value = ?
                AND d.value BETWEEN '%s' AND '%s'""" % (fromDate, toDate),
                   status, timeout = 300)
elif revisionInfo:
    cursor.execute("""\
    SELECT DISTINCT s.doc_id, MAX(v.dt)
      FROM query_term s
      JOIN doc_version v
        ON v.id = s.doc_id
     WHERE s.path = '/GlossaryTerm/TermStatus'
       AND s.value = ?
  GROUP BY s.doc_id
    HAVING MAX(v.dt) BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))""" %
                   (fromDate, toDate), status, timeout = 300)
else:
    cursor.execute("""\
    SELECT DISTINCT s.doc_id, MIN(a.dt)
      FROM query_term s
      JOIN audit_trail a
        ON a.document = s.doc_id
     WHERE s.path = '/GlossaryTerm/TermStatus'
       AND s.value = ?
  GROUP BY s.doc_id
    HAVING MIN(a.dt) BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))""" %
               (fromDate, toDate), status, timeout = 300)

class GlossaryTerm:
    def __init__(self, id, node, pubNode = None, spDefStatusDate = None):
        self.id = id
        self.name = None
        self.pronunciation = None
        self.definitions = []
        self.source = None
        self.pubPronunciation = None
        self.pubDefinitions = []
        self.spDefinitions = []
        self.types = []
        self.statusDate = None
        self.spDefStatusDate = spDefStatusDate
        self.spTermName = None
        self.translationResource = None
        for child in node.childNodes:
            if child.nodeName == "TermName":
                self.name = getNodeContent(child)
            elif child.nodeName == "TermPronunciation":
                self.pronunciation = getNodeContent(child)
            elif child.nodeName == "TermDefinition":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "DefinitionText":
                        self.definitions.append(getNodeContent(grandchild))
                        break
            elif child.nodeName == "TermSource":
                self.source = getNodeContent(child)
            elif child.nodeName == "TermType":
                self.types.append(getNodeContent(child))
            elif child.nodeName == "StatusDate":
                self.statusDate = getNodeContent(child)
            elif spDefStatusDate:
                if child.nodeName == 'SpanishTermName':
                    self.spTermName = getNodeContent(child)
                if child.nodeName == 'SpanishTermDefinition':
                    for grandchild in child.childNodes:
                        if grandchild.nodeName == 'DefinitionText':
                            defText = getNodeContent(grandchild)
                            self.spDefinitions.append(defText)
                        elif grandchild.nodeName == 'TranslationResource':
                            trRes = getNodeContent(grandchild)
                            self.translationResource = trRes
        if pubNode:
            for child in pubNode.childNodes:
                if child.nodeName == "TermPronunciation":
                    self.pubPronunciation = getNodeContent(child)
                elif child.nodeName == "TermDefinition":
                    for grandchild in child.childNodes:
                        if grandchild.nodeName == "DefinitionText":
                            value = getNodeContent(grandchild)
                            self.pubDefinitions.append(value)
                            break

terms = []
for row in cursor.fetchall():
    doc = cdr.getDoc('guest', row[0], getObject = True)
    dom = xml.dom.minidom.parseString(doc.xml)
    pdom = None
    if revisionInfo:
        versions = cdr.lastVersions('guest', 'CDR%010d' % row[0])
        if versions[1] != -1:
            doc = cdr.getDoc('guest', row[0], getObject = True,
                             version = str(versions[1]))
            pdom = xml.dom.minidom.parseString(doc.xml)
    terms.append(GlossaryTerm(row[0], dom.documentElement,
                              pdom and pdom.documentElement or None,
                              lang and row[1] or None))
terms.sort(lambda a,b: cmp(a.name, b.name))
html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Glossary Terms by Status</title>
  <style type 'text/css'>
   body    { font-family: Arial, Helvetica, sans-serif }
   span.t1 { font-size: 14pt; font-weight: bold }
   span.t2 { font-size: 12pt; font-weight: bold }
   th      { font-size: 10pt; font-weight: bold }
   td      { font-size: 10pt; font-weight: normal }
   @page   { margin-left: 0cm; margin-right: 0cm; }
   body, table   { margin-left: 0cm; margin-right: 0cm; }
  </style>
 </head>
 <body>
  <center>
   <span class='t1'>Glossary Terms by Status</span>
   <br />
   <br />
   <span class='t2'>%s Terms<br />From %s to %s</span>
  </center>
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
""" % (status, fromDate, toDate)
if lang:
    if status.upper() == 'TRANSLATION REVISION PENDING':
        html += """\
   <tr>
    <th>CDR ID</th>
    <th>English Term</th>
    <th>Spanish Term</th>
    <th>Approved English Definition Revision</th>
    <th>Pending Spanish Translation Revision</th>
    <th>Translation Resource</th>
    <th>Status Date</th>
   </tr>
"""
    else:
        html += """\
   <tr>
    <th>CDR ID</th>
    <th>English Term</th>
    <th>Spanish Term</th>
    <th>English Definition</th>
    <th>Spanish Translation</th>
    <th>Translation Resource</th>
    <th>Status Date</th>
   </tr>
"""
elif revisionInfo:
    html += """\
   <tr>
    <th>CDR ID</th>
    <th>Term</th>
    <th>Last Pub Ver Pronunciation</th>
    <th>Revised Pronunciation</th>
    <th>Last Pub Ver Definition</th>
    <th>Revised Definition</th>
    <th>Definition Source</th>
    <th>Term Type</th>
    <th>Status Date</th>
   </tr>
"""
else:
    html += """\
   <tr>
    <th>CDR ID</th>
    <th>Term</th>
    <th>Pronunciation</th>
    <th>Definition</th>
    <th>Definition Source</th>
    <th>Term Type</th>
    <th>Status Date</th>
   </tr>
"""
for term in terms:
    if lang:
        html += u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (term.id,
       fix(term.name),
       fix(term.spTermName),
       fixList(term.definitions),
       fixList(term.spDefinitions),
       fix(term.translationResource),
       term.spDefStatusDate and term.spDefStatusDate[:10] or u"&nbsp;")
    elif revisionInfo:
        html += u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (term.id,
       fix(term.name),
       fix(term.pubPronunciation),
       fix(term.pronunciation),
       fixList(term.pubDefinitions),
       fixList(term.definitions),
       fix(term.source),
       fixList(term.types),
       term.statusDate and term.statusDate[:10] or u"&nbsp;")
    else:
        html += u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (term.id,
       fix(term.name),
       fix(term.pronunciation),
       fixList(term.definitions),
       fix(term.source),
       fixList(term.types),
       term.statusDate and term.statusDate[:10] or u"&nbsp;")
cdrcgi.sendPage(html + u"""\
  </table>
 </body>
</html>
""")
