#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/05/04 15:00:22  bkline
# New Glossary Term report.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, string, time, xml.dom.minidom, xml.sax.saxutils

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
types    = fields.getlist("type") or []
session  = fields.getvalue("Session") or None
audience = fields.getvalue("audience") or "All"
request  = cdrcgi.getRequest(fields)
title    = "CDR Administration"
instr    = "Glossary Terms by Type"
buttons  = ["Submit Request", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
script   = "GlossaryTermsByType.py"
header   = cdrcgi.header(title, title, instr, script, buttons)
conn     = cdrdb.connect('CdrGuest')
cursor   = conn.cursor()

#----------------------------------------------------------------------
# Handle requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out": 
    cdrcgi.logout(session)

def getTermTypes(cursor):
    cursor.execute("""\
        SELECT DISTINCT value
                   FROM query_term
                  WHERE path = '/GlossaryTerm/TermType'
               ORDER BY value""")
    return "\n".join(["""\
    <option value='%s'>%s</option>""" % (r[0], r[0])
               for r in cursor.fetchall()])
        
#----------------------------------------------------------------------
# As the user for the report parameters.
#----------------------------------------------------------------------
if not types:
    form        = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD align='right'><B>Glossary Term Type:&nbsp;</B></TD>
     <TD>
      <SELECT NAME='type' MULTIPLE='1'>
%s      </SELECT>
     </TD>
    <TR>
     <TD align='right'><B>Audience:&nbsp;</B></TD>
     <TD>
      <SELECT NAME='audience'>
       <option value='Both' selected='1'>Both</option>
       <option value='Health professional'>Health professional</option>
       <option value='Patient'>Patient</option>
      </SELECT>
     </TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, getTermTypes(cursor))
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
def unacceptableGetNodeContent(node):
    pieces = []
    for child in node.childNodes:
        piece = child.toxml()
        if type(piece) != unicode:
            piece = unicode(piece, 'utf-8')
        pieces.append(piece)
    return u"".join(pieces)

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

class Definition:
    def __init__(self, text, audience):
        self.text = text
        self.audience = audience

#----------------------------------------------------------------------
# Create/display the report.
#----------------------------------------------------------------------
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
        self.audience = ""
        self.status = None
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
                text = None
                audience = None
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "DefinitionText":
                        text = getNodeContent(grandchild)
                    elif grandchild.nodeName == "Audience":
                        audience = getNodeContent(grandchild)
                self.definitions.append(Definition(text, audience))
            elif child.nodeName == "TermSource":
                self.source = getNodeContent(child)
            elif child.nodeName == "TermStatus":
                self.status = getNodeContent(child)
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

def addTypeBlock(cursor, termType, html):
    html.append("""\
  <br />
  <center>
   <span class='t2'>%s Terms</span>
  </center>
  <br />
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <th>CDRID</th>
    <th>Term</th>
    <th>Pronunciation</th>
    <th>Definition</th>
    <th>Term Source</th>
    <th>Audience</th>
    <th>Term Status</th>
   </tr>""" % termType)
    cursor.execute("""\
        SELECT DISTINCT doc_id
                   FROM query_term
                  WHERE path = '/GlossaryTerm/TermType'
                    AND value = ?""", termType)

    terms = []
    for row in cursor.fetchall():
        doc = cdr.getDoc('guest', row[0], getObject = True)
        dom = xml.dom.minidom.parseString(doc.xml)
        terms.append(GlossaryTerm(row[0], dom.documentElement))
        terms.sort(lambda a,b: cmp(a.name, b.name))
    for term in terms:
        if not term.definitions and audience == 'Both':
            term.definitions.append(Definition(None, None))
        for definition in term.definitions:
            if audience != 'Both' and definition.audience:
                if audience != definition.audience:
                    continue

            html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (term.id,
               fix(term.name),
               fix(term.pronunciation),
               fix(definition.text),
               fix(term.source),
               fix(definition.audience),
               fix(term.status)))
    html.append("""\
  </table>""")

html = [u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Glossary Terms by Type</title>
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
   <span class='t1'>Glossary Terms by Type</span>
  </center>"""]
for t in types:
    addTypeBlock(cursor, t, html)
html.append(u"""\
 </body>
</html>
"""
)
cdrcgi.sendPage(u"\n".join(html))
