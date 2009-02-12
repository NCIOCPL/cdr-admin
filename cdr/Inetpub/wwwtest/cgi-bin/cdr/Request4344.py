#----------------------------------------------------------------------
#
# $Id: Request4344.py,v 1.1 2009-02-12 16:21:06 bkline Exp $
#
# The Glossary Term Concept by Spanish Definition Status Report will serve
# as a QC report for Spanish and corresponding English Definitions by Status.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrcgi, cgi, cdr, cdrdb, xml.dom.minidom

SPANISH  = '4344'
ENGLISH  = '4342'
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
start    = fields.getvalue('start')
end      = fields.getvalue('end')
status   = fields.getvalue('status')
language = fields.getvalue('language') or 'all'
audience = fields.getvalue('audience')
resource = fields.getvalue('resource')
notes    = fields.getvalue('notes')
blocked  = fields.getvalue('blocked')
report   = fields.getvalue('report') or SPANISH
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "Request4344.py"
title    = "CDR Administration"
part     = report == SPANISH and 'Spanish' or 'English'
section  = "Glossary Term Concept by %s Definition Status" % part
request  = cdrcgi.getRequest(fields)
header   = cdrcgi.header(title, title, section, script, buttons,
                         stylesheet = u"""\
<style type='text/css'>
 th, td { font-size: 12pt; }
 th     { text-align: right; }
</style>
""")
#if start:
#    cdrcgi.bail("%s|%s|%s|%s" % (start, end, status, audience))
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

if request == "Submit Request" and not (start and end and status and audience):
    cdrcgi.bail("Date range, status, and audience are required fields")

def capitalize(me):
    if not me:
        return u""
    return me[0].upper() + me[1:]

#----------------------------------------------------------------------
# Extract the complete content of an element, tags and all.
#----------------------------------------------------------------------
def getNodeContent(node, replacements = None, pieces = None):
    if pieces is None:
        pieces = []
    for child in node.childNodes:
        if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
            if child.nodeValue:
                pieces.append(cgi.escape(child.nodeValue))
        elif child.nodeType == child.ELEMENT_NODE:
            if child.nodeName == 'Insertion':
                pieces.append(u"<span style='color: red'>")
                getNodeContent(child, replacements, pieces)
                pieces.append(u"</span>")
            elif child.nodeName == 'Deletion':
                pieces.append(u"<span style='text-decoration: line-through'>")
                getNodeContent(child, replacements, pieces)
                pieces.append(u"</span>")
            elif child.nodeName == 'Strong':
                pieces.append(u"<b>")
                getNodeContent(child, replacements, pieces)
                pieces.append(u"</b>")
            elif child.nodeName in ('Emphasis', 'ScientificName'):
                pieces.append(u"<i>")
                getNodeContent(child, replacements, pieces)
                pieces.append(u"</i>")
            elif child.nodeName == 'PlaceHolder':
                name = child.getAttribute('name')
                if not name:
                    raise Exception(u"PlaceHolder without name")
                if not replacements:
                    raise Exception(u"No replacements supplied for "
                                    u"placeholder '%s'" % name)
                replacementNode = replacements.get(name)
                if not replacementNode:
                    raise Exception(u"No replacement found for "
                                    u"placeholder '%s'" % name)
                pieces.append(u"<b>")
                if type(replacementNode) in (str, unicode):
                    pieces.append(replacementNode)
                else:
                    #cdrcgi.bail(repr(replacementNode))
                    getNodeContent(replacementNode, replacements, pieces)
                pieces.append(u"</b>")
            else:
                getNodeContent(child, replacements, pieces)
    return u"".join(pieces)

#----------------------------------------------------------------------
# If we have all the parameters, create the report.
#----------------------------------------------------------------------
if start and end and status and audience:

    class Definition:
        def __init__(self, node):
            self.status = self.audience = self.statusDate = self.text = None
            self.resources = []
            for child in node.childNodes:
                if child.nodeName == 'DefinitionText':
                    self.text = child
                elif child.nodeName in ('DefinitionResource',
                                        'TranslationResource'):
                    self.resources.append(getNodeContent(child))
                elif child.nodeName == 'Audience':
                    self.audience = getNodeContent(child)
                elif child.nodeName in ('DefinitionStatus',
                                        'TranslatedStatus'):
                    self.status = getNodeContent(child)
                elif child.nodeName in ('StatusDate', 'TranslatedStatusDate'):
                    self.statusDate = getNodeContent(child)
        def getResources(self):
            return u"<br />".join(self.resources) or u"&nbsp;"
        def toHtml(self, repNodes):
            #cdrcgi.bail(repr(repNodes))
            return getNodeContent(self.text, repNodes)

    class NameString:
        def toHtml(self, blocked, withPronunciation = False):
            html = [u"<span class='%s'>%s" %
                    (blocked and u'blocked' or 'active',
                     cgi.escape(self.value))]
            if withPronunciation and self.pronunciation:
                html.append(" (%s)" % self.pronunciation)
            html.append(u"</span>")
            return u"".join(html)
        def getResources(self):
            return u"; ".join(self.resources) or u"&nbsp;"
        def __init__(self, node):
            self.value = u""
            self.pronunciation = u""
            self.resources = []
            for child in node.childNodes:
                if child.nodeName == 'TermNameString':
                    self.value = getNodeContent(child)
                elif child.nodeName == 'TermPronunciation':
                    self.pronunciation = getNodeContent(child)
                elif child.nodeName == 'PronunciationResource':
                    self.resources.append(getNodeContent(child))

    class Name:
        def getPublishedDefinition(self, cursor, report, audience):
            if report == ENGLISH:
                name = 'TermDefinition'
            else:
                name = 'SpanishTermDefinition'
            cursor.execute("""\
                SELECT xml
                  FROM pub_proc_cg
                 WHERE id = ?""", self.docId)
            rows = cursor.fetchall()
            if not rows:
                return None
            dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
            for node in dom.getElementsByTagName(name):
                thisAudience = None
                text = None
                for child in node.childNodes:
                    if child.nodeName == 'Audience':
                        thisAudience = getNodeContent(child)
                    elif child.nodeName == 'DefinitionText':
                        text = child
                if audience == thisAudience:
                    return getNodeContent(text)
            return None

        def __init__(self, docId, cursor):
            self.docId    = docId
            self.english  = None
            self.spanish  = []
            self.lastPub  = None
            self.pubVer   = None
            self.repNodes = {}
            self.blocked  = None
            cursor.execute("""\
                SELECT d.doc_version, p.completed
                  FROM pub_proc_cg c
                  JOIN pub_proc_doc d
                    ON d.doc_id = c.id
                   AND c.pub_proc = d.pub_proc
                  JOIN pub_proc p
                    ON p.id = c.pub_proc
                 WHERE d.doc_id = ?""", docId, timeout = 300)
            rows = cursor.fetchall()
            if rows:
                self.pubVer, self.lastPub = rows[0]
            cursor.execute("""\
                SELECT xml, active_status
                  FROM document
                 WHERE id = ?""", docId)
            try:
                docXml, activeStatus = cursor.fetchall()[0]
                self.blocked = activeStatus != 'A'
                dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
                for node in dom.getElementsByTagName('ReplacementText'):
                    self.repNodes[node.getAttribute('name')] = node
                for node in dom.documentElement.childNodes:
                    if node.nodeName == 'TermName':
                        self.english = NameString(node)
                    elif node.nodeName == 'TranslatedName':
                        self.spanish.append(NameString(node))
            except Exception, e:
                cdr.logwrite("Name(%d): %s" % (docId, e))
                cdrcgi.bail("Name(%d): %s" % (docId, e))
        def __cmp__(self, other):
            if report == ENGLISH:
                diff = cmp(self.english.value, other.english.value)
            else:
                if not self.spanish:
                    if not other.spanish:
                        return cmp(self.docId, other.docId)
                    return 1
                elif not other.spanish:
                    return -1
                else:
                    diff = cmp(self.spanish[0].value, other.spanish[0].value)
            if diff:
                return diff
            return cmp(self.docId, other.docId)
                
    class Concept:
        def toHtml(self, report, status, language, resources, notes):
            if report == ENGLISH:
                return self.toHtmlEnglish(report, status, resources, notes)
            else:
                return self.toHtmlSpanish(report, status, language, resource,
                                          notes)
        def toHtmlEnglish(self, report, status, resources, notes):
            name = u"<span class='error'>NO NAME FOUND</span>"
            resource = u"&nbsp;"
            if self.names and self.names[0].english:
                name = self.names[0].english.toHtml(self.names[0].blocked, True)
                resource = self.names[0].english.getResources()
            rowCount = len(self.names) or 1
            definition = self.enDef.toHtml(self.repNodes)
            if status == 'Revision pending':
                revDef = definition
                definition = (u"<span class='error'>"
                              u"NO PUBLISHED DEFINITION FOUND</span>")
                if self.name:
                    d = self.name.getPublishedDefinition(cursor, report,
                                                         audience)
                    if d:
                        definition = d
            html = [u"""\
   <tr>
    <td rowspan='%d'>%d</td>
    <td>%s</td>
""" % (rowCount, self.docId, name)]
            if resources:
                html.append(u"""\
    <td>%s</td>
""" % resource)
            html.append(u"""\
    <td rowspan='%d'>%s</td>
""" % (rowCount, definition))
            if status == 'Revision pending':
                html.append(u"""\
    <td rowspan='%d'>%s</td>
""" % (rowCount, revDef))
            html.append(u"""\
    <td rowspan='%d'>%s</td>
""" % (rowCount, self.enDef.getResources()))
            if notes:
                html.append(u"""\
    <td rowspan='%d'>&nbsp;</td>
""" % rowCount)
            html.append(u"""\
   </tr>
""")
            for n in self.names[1:]:
                if n.english:
                    name = n.english.toHtml(n.blocked, True)
                    html.append(u"""\
   <tr>
    <td>%s</td>
""" % name)
                    if resources:
                        html.append(u"""\
    <td>%s</td>
""" % n.english.getResources())
                    html.append(u"""\
   </tr>
""")
            return u"".join(html)
                    
        def toHtmlSpanish(self, report, status, language, resources, notes):
            rowCount = 0
            for name in self.names:
                sCount = len(name.spanish) or 1
                rowCount += sCount
            rowCount = rowCount or 1
            html = [u"""\
   <tr>
    <td rowspan='%d'>%d</td>
""" % (rowCount, self.docId)]
            if language == 'all':
                name = u"<span class='error'>NO NAME FOUND</span>"
                if self.names and self.names[0].english:
                    name = self.names[0].english.toHtml(self.names[0].blocked)
                html.append(u"""\
    <td rowspan='%d'>%s</td>
""" % (len(self.names[0].spanish) or 1, name))
            name = u"<span class='error'>NO NAME FOUND</span>"
            if self.names and self.names[0].spanish:
                name = self.names[0].spanish[0].toHtml(self.names[0].blocked)
            html.append(u"""\
    <td>%s</td>
""" % name)
            if language == 'all':
                if self.enDef:
                    definition = self.enDef.toHtml(self.repNodes)
                else:
                    error = u"NO %s DEFINITION FOUND" % audience.upper()
                    definition = u"<span class='error'>%s</span>" % error
                html.append(u"""\
    <td rowspan='%d'>%s</td>
""" % (rowCount, definition))
            html.append(u"""\
    <td rowspan='%d'>%s</td>
""" % (rowCount, self.spDef.toHtml(self.repNodes)))
            if resources:
                html.append(u"""\
    <td rowspan='%d'>%s</td>
""" % (rowCount, self.spDef.getResources()))
            if notes:
                html.append(u"""\
    <td rowspan='%d'></td>
""" % rowCount)
            html.append(u"""\
   </tr>
""")
            if self.names:
                for s in self.names[0].spanish[1:]:
                    html.append(u"""\
   <tr>
    <td>%s</td>
   </tr>
""" % s.toHtml(self.names[0].blocked))

            if language == 'all':
                for n in self.names[1:]:
                    e = u"<span class='error'>NO ENGLISH NAME</span>"
                    s = u"<span class='error'>NO SPANISH NAME</span>"
                    if n.english:
                        e = n.english.toHtml(n.blocked)
                    if n.spanish:
                        s = n.spanish[0].toHtml(n.blocked)
                    html.append(u"""\
   <tr>
    <td rowspan='%d'>%s</td>
    <td>%s</td>
   </tr>
""" % (len(n.spanish) or 1, e, s))
                    for s in n.spanish[1:]:
                        html.append(u"""\
   <tr>
    <td>%s</td>
   </tr>
""" % s.toHtml(n.blocked))
            else:
                for n in self.names[1:]:
                    for s in n.spanish:
                        html.append(u"""\
   <tr>
    <td>%s</td>
   </tr>
""" % s.toHtml(n.blocked))
            return u"".join(html)
            
        def __init__(self, docId, cursor, language, start, end, audience,
                     status):
            self.docId    = docId
            self.spDef    = None
            self.enDef    = None
            self.names    = []
            self.name     = None
            self.repNodes = {}
            self.blocked  = None
            cursor.execute("""\
                SELECT xml, active_status
                  FROM document
                 WHERE id = ?""", docId)
            docXml, activeStatus = cursor.fetchall()[0]
            self.blocked = activeStatus != 'A'
            dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
            enDefs = [Definition(n) for n in
                      dom.getElementsByTagName('TermDefinition')]
            spDefs = [Definition(n) for n in
                      dom.getElementsByTagName('TranslatedTermDefinition')]
            if report == ENGLISH:
                for d in enDefs:
                    if False and docId == 618500:
                        cdrcgi.bail("docId=%d|statusDate=%s|%s|%s; audience=%s|%s; status=%s|%s" %
                                (docId, d.statusDate, start, end,
                                 d.audience, audience, d.status, status))
                    if d.statusDate >= start and d.statusDate <= end:
                        if d.audience == audience and d.status == status:
                            self.enDef = d
                            break
                if not self.enDef:
                    return
            else:
                for d in spDefs:
                    if d.statusDate >= start and d.statusDate <= end:
                        if d.audience == audience and d.status == status:
                            self.spDef = d
                            break
                if not self.spDef:
                    return
                for d in enDefs:
                    if d.audience == audience:
                        self.enDef = d
            for node in dom.getElementsByTagName('ReplacementText'):
                self.repNodes[node.getAttribute('name')] = node
            cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
                AND int_val = ?""", docId)
            self.names = []
            for row in cursor.fetchall():
                n = Name(row[0], cursor)
                if blocked or not n.blocked:
                    self.names.append(n)
            for name in self.names:
                if name.lastPub:
                    if not self.name or name.lastPub > self.name.lastPub:
                        self.name = name
                        break
            if not self.name:
                if self.names:
                    self.names.sort()
                    self.name = self.names[0]
            if self.name:
                #cdrcgi.bail(repr(self.name.repNodes))
                for name in self.name.repNodes:
                    self.repNodes[name] = self.name.repNodes[name]
                if report == ENGLISH:
                    n = self.name.english.value
                else:
                    if self.name.spanish:
                        n = self.name.spanish[0].value
                self.repNodes['TERMNAME'] = n
                self.repNodes['CAPPEDTERMNAME'] = capitalize(n)
            
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    translated = report == SPANISH and 'Translated' or ''
    cursor.execute("""\
        SELECT DISTINCT doc_id
          FROM query_term
         WHERE path = '/GlossaryTermConcept/%sTermDefinition/%sStatusDate'
           AND value BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
      ORDER BY doc_id""" % (translated, translated, start, end))
    concepts = []
    for row in cursor.fetchall():
        docId = row[0]
        concept = Concept(docId, cursor, language, start, end, audience, status)
        if report == SPANISH:
            if concept.spDef:
                concepts.append(concept)
        elif concept.enDef:
            concepts.append(concept)
    html = [u"""\
<html>
 <head>
  <meta http-equiv='content-type' content='text/html; charset=UTF-8'>
  <title>%s</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   h1 { color: maroon; }
   .error { color: red; }
   .blocked { color: red; font-weight: bold; }
   table { border-spacing: 0; border-collapse: collapse; empty-cells: show; }
   td, th { border: black 1px solid; padding: 3px; }
   td { vertical-align: top; }
   th { color: green; }
   #notes {width: 200px; }
  </style>
 </head>
 <body>
  <h1>%s</h1>
  <table>
   <tr>
    <th>CDR ID of GTC</th>
""" % (section, section)]
    if report == SPANISH:
        if language == 'all':
            html.append(u"""\
    <th>Term Name (EN)</th>
""")
        html.append(u"""\
    <th>Term Name (ES)</th>
""")
        if language == 'all':
            html.append(u"""\
    <th>Definition (EN)</th>
""")
        html.append(u"""\
    <th>Definition (ES)</th>
""")
        if resource:
            html.append(u"""\
    <th>Translation Resource</th>
""")
    else:
        html.append(u"""\
    <th>Term Name (Pronunciation)</th>
""")
        if resource:
            html.append(u"""\
    <th>Pronun. Resource</th>
""")
        html.append(u"""\
    <th>Definition</th>
""")
        if status == 'Revision pending':
            html.append("""\
    <th>Definition (Revision pending)</th>
""")
        html.append(u"""\
    <th>Definition Resource</th>
""")
    if notes:
        html.append(u"""\
    <th id='notes'>QC Notes</th>
""")
    html.append(u"""\
   </tr>
""")
    for concept in concepts:
        html.append(concept.toHtml(report, status, language, resource, notes))
    html.append(u"""\
  </table>
 </body>
</html>""")
    cdrcgi.sendPage(u"".join(html))
#    print """\
#Content-type: text/html; charset=utf-8
#"""
#    print u"".join(html).encode('utf-8')

else:
    start = cdr.calculateDateByOffset(-7)
    end   = cdr.calculateDateByOffset(0)
    form  = [u"""\
   <input type='hidden' name='%s' value='%s' />
   <input type='hidden' name='report' value='%s' />
   <table border='0'>
    <tr>
     <th nowrap='nowrap'>Start Date:&nbsp;</th>
     <td><input name='start' value='%s' /></td>
    </tr>
    <tr>
     <th nowrap='nowrap'>End Date:&nbsp;</th>
     <td><input name='end' value='%s' /></td>
    </tr>
    <tr>
     <th nowrap='nowrap'>Definition Status:&nbsp;</th>
     <td>
      <select name='status'>
       <option value=''>Choose Status</option>
       <option value='Approved'>Approved</option>
       <option>New pending</option>
       <option>Revision pending</option>
       <option>Rejected</option>
      </select>
     </td>
    </tr>
""" % (cdrcgi.SESSION, session, report, start, end)]
    if report == SPANISH:
        resourceType = 'Translation'
        form.append(u"""\
    <tr>
     <th>Language:&nbsp;</th>
     <td>
      <select name='language'>
       <option value='es'>Spanish</option>
       <option value='all'>Select All</option>
      </select>
     </td>
    </tr>
""")
    else:
        resourceType = 'Pronunciation'
    form.append(u"""\
    <tr>
     <th>Audience:&nbsp;</th>
     <td>
      <select name='audience'>
       <option value=''>Choose Audience</option>
       <option>Patient</option>
       <option>Health professional</option>
      </select>
     </td>
    </tr>
    <tr>
     <th nowrap='nowrap'>Display %s Resource:&nbsp;</th>
     <td><input type='checkbox' name='resource' /></td>
    </tr>
    <tr>
     <th nowrap='nowrap'>Display QC Notes Column:&nbsp;</th>
     <td><input type='checkbox' name='notes' /></td>
    </tr>
    <tr>
     <th nowrap='nowrap'>Include Blocked Term Name Documents:&nbsp;</th>
     <td><input type='checkbox' name='blocked' /></td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % resourceType)
    cdrcgi.sendPage(header + u"".join(form))
