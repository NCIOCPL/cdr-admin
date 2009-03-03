#----------------------------------------------------------------------
#
# $Id: Request4486.py,v 1.1 2009-03-03 21:58:11 bkline Exp $
#
# "We need a new glossary term concept by type QC report to help us ensure
# consistency in the wording of definitions.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, time, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
termType  = fields.getvalue("type")
termName  = fields.getvalue("name")
defText   = fields.getvalue("text")
status    = fields.getvalue("stat")
spanish   = fields.getvalue("span")
audience  = fields.getvalue("audi")
title     = "CDR Administration"
language  = spanish and "ENGLISH &amp; SPANISH" or "ENGLISH"
section   = "Glossary Term Concept by Type Report"
SUBMENU   = "Report Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'Request4486.py'
header    = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
   <style type='text/css'>
    th, td, input { font-size: 10pt; }
    body          { background-color: #DFDFDF;
                    font-family: sans-serif;
                    font-size: 12pt; }
    legend        { font-weight: bold;
                    color: teal;
                    font-family: sans-serif; }
    fieldset      { width: 500px;
                    margin-left: auto;
                    margin-right: auto;
                    display: block; }
    .field        { width: 300px; }
    select        { width: 305px; }
   </style>
""")

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
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except Exception, e:
    cdrcgi.bail('Database connection failure: %s' % e)

#----------------------------------------------------------------------
# Get XML for CDR document with revision markup resolved.
#----------------------------------------------------------------------
def resolveRevisionMarkup(docId):
    parms = (('useLevel', '1'),)
    filt  = ['name:Revision Markup Filter']
    response = cdr.filterDoc('guest', filt, docId, parm = parms)
    if type(response) in (str, unicode):
        cdrcgi.bail(u"Unable to fetch CDR%d: %s" % (docId, response))
    return response[0]

#----------------------------------------------------------------------
# Recursively break down a glossary definition into a chain of text
# strings and placeholders.
#----------------------------------------------------------------------
def breakDownDefinition(node):
    pieces = []
    for child in node.childNodes:
        if child.nodeName == 'PlaceHolder':
            pieces.append(PlaceHolder(child.getAttribute('name')))
        elif child.nodeType == child.ELEMENT_NODE:
            pieces += breakDownDefinition(child)
        elif child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
            pieces.append(child.nodeValue)
    return pieces

#----------------------------------------------------------------------
# Object in which we collect what we need for a glossary term name.
#----------------------------------------------------------------------
class Name:
    def __init__(self, docId, spanish):
        self.docId = docId
        self.englishName = u""
        self.replacements = {}
        if not spanish:
            self.pronunciation = u""
        docXml = resolveRevisionMarkup(docId)
        dom = xml.dom.minidom.parseString(docXml)
        for node in dom.getElementsByTagName('TermName'):
            for child in node.childNodes:
                if child.nodeName == 'TermNameString':
                    self.englishName = cdr.getTextContent(child, True)
                elif not spanish and child.nodeName == 'TermPronunciation':
                    self.pronunciation = cdr.getTextContent(child, True)
        for node in dom.getElementsByTagName('ReplacementText'):
            text = cdr.getTextContent(node, True)
            self.replacements[node.getAttribute('name')] = text
        if spanish:
            self.spanishNames = []
            for node in dom.getElementsByTagName('TranslatedName'):
                for child in node.getElementsByTagName('TermNameString'):
                    self.spanishNames.append(cdr.getTextContent(child, True))

#----------------------------------------------------------------------
# Object to represent a placeholder in a glossary definition.
#----------------------------------------------------------------------
class PlaceHolder:
    def __init__(self, name):
        self.name = name

#----------------------------------------------------------------------
# Object for a glossary term definition (English or Spanish).
#----------------------------------------------------------------------
class Definition:
    def __init__(self, node):
        self.text = []
        self.replacements = {}
        self.audiences = set()
        for child in node.getElementsByTagName('DefinitionText'):
            self.text = breakDownDefinition(child)
        for child in node.getElementsByTagName('ReplacementText'):
            text = cdr.getTextContent(child, True)
            self.replacements[child.getAttribute('name')] = text
        for child in node.getElementsByTagName('Audience'):
            self.audiences.add(cdr.getTextContent(child))
    def resolve(self, replacementsFromNameDoc, termName):
        reps = self.replacements.copy()
        reps.update(replacementsFromNameDoc)
        pieces = []
        for piece in self.text:
            if isinstance(piece, PlaceHolder):
                default = u"[UNRESOLVED PLACEHOLDER %s]" % piece.name
                if piece.name == 'TERMNAME' and termName:
                    rep = cgi.escape(termName)
                elif piece.name == 'CAPPEDTERMNAME' and termName:
                    rep = cgi.escape(termName[0].upper() + termName[1:])
                else:
                    rep = cgi.escape(reps.get(piece.name, default))
                pieces.append(u"<span class='replacement'>%s</span>" % rep)
            else:
                pieces.append(cgi.escape(piece))
        return u"".join(pieces)

#----------------------------------------------------------------------
# Object for a glossary term concept's information.
#----------------------------------------------------------------------
class Concept:
    def __init__(self, docId, cursor, audience, spanish):
        self.docId = docId
        cursor.execute("""\
            SELECT DISTINCT doc_id
                       FROM query_term
                      WHERE path = '/GlossaryTermName/GlossaryTermConcept'
                                 + '/@cdr:ref'
                        AND int_val = ?""", docId)
        rows = cursor.fetchall()
        self.names = [Name(row[0], spanish) for row in rows]
        docXml = resolveRevisionMarkup(docId)
        dom = xml.dom.minidom.parseString(docXml)
        self.definitions = []
        for node in dom.getElementsByTagName('TermDefinition'):
            definition = Definition(node)
            if audience in definition.audiences:
                self.definitions.append(definition)
        if spanish:
            self.spanishDefinitions = []
            for node in dom.getElementsByTagName('TranslatedTermDefinition'):
                definition = Definition(node)
                if audience in definition.audiences:
                    self.spanishDefinitions.append(definition)
    def toHtml(self, spanish):
        termNameRows = 0
        for name in self.names:
            if spanish:
                if name.spanishNames:
                    termNameRows += len(name.spanishNames)
                else:
                    termNameRows += 1
            else:
                termNameRows += 1
        rowspan = termNameRows or 1
        definitionRows = len(self.definitions)
        if spanish and len(self.spanishDefinitions) > definitionRows:
            definitionRows = len(self.spanishDefinitions)
        if definitionRows > 1:
            rowspan += definitionRows - 1
        html = [u"""\
   <tr>
    <td rowspan='%d'>%d</td>
""" % (rowspan, self.docId)]
        rowspan = termNameRows or 1
        name = self.names and self.names[0].englishName or u""
        reps = self.names and self.names[0].replacements or {}
        enDef = u""
        firstEnglishName = name
        if self.definitions:
            enDef = self.definitions[0].resolve(reps, firstEnglishName)
        if spanish:
            spName = spDef = u""
            nameRowspan = 1
            if self.names and self.names[0].spanishNames:
                spName = self.names[0].spanishNames[0]
                if len(self.names[0].spanishNames) > 1:
                    nameRowspan = len(self.names[0].spanishNames)
            firstSpanishName = spName
            if self.spanishDefinitions:
                spDef = self.spanishDefinitions[0].resolve(reps, spName)
            html.append(u"""\
    <td rowspan='%d'>%s</td>
    <td>%s</td>
    <td rowspan='%d'>%s</td>
    <td rowspan='%d'>%s</td>
   </tr>
""" % (nameRowspan, cgi.escape(name), cgi.escape(spName),
       rowspan, enDef, rowspan, spDef))
            if self.names:
                for spName in self.names[0].spanishNames[1:]:
                    html.append(u"""\
   <tr>
    <td>%s</td>
   </tr>
""" % cgi.escape(spName))
                for name in self.names[1:]:
                    nameRowspan = len(name.spanishNames) or 1
                    spName = name.spanishNames and name.spanishNames[0] or u""
                    html.append(u"""\
   <tr>
    <td rowspan='%d'>%s</td>
    <td>%s</td>
   </tr>
""" % (nameRowspan, cgi.escape(name.englishName), cgi.escape(spName)))
                    for spName in name.spanishNames[1:]:
                        html.append(u"""\
   <tr>
    <td>%s</td>
   </tr>
""" % cgi.escape(spName))
        else:
            if self.names:
                name += u" (%s)" % self.names[0].pronunciation
            html.append(u"""\
    <td>%s</td>
    <td rowspan='%d'>%s</td>
   </tr>    
""" % (cgi.escape(name), rowspan, enDef))
            for name in self.names[1:]:
                enName = u"%s (%s)" % (name.englishName, name.pronunciation)
                html.append(u"""\
   <tr>
    <td>%s</td>
   </tr>
""" % cgi.escape(enName))
        i = 1
        while i < definitionRows:
            enDef = u""
            if i < len(self.definitions):
                enDef = self.definitions[i].resolve(reps, firstEnglishName)
            html.append(u"""\
   <tr>
    <td>%s</td>
""" % enDef)
            if spanish:
                spDef = u""
                if i < len(self.spanishDefinitions):
                    spName = firstSpanishName
                    spDef = self.spanishDefinitions[i].resolve(reps, spName)
                html.append(u"""\
    <td>%s</td>
""" % spDef)
            html.append(u"""\
   </tr>
""")
            i += 1
        return u"".join(html)

#----------------------------------------------------------------------
# Create the picklist for term type.
#----------------------------------------------------------------------
def makeTermTypePicklist(cursor):
    selected = " selected='selected'"
    cursor.execute("""\
        SELECT DISTINCT value
                   FROM query_term
                  WHERE path = '/GlossaryTermConcept/TermType'
               ORDER BY value""")
    html = [u"<select name='type'>"]
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Unable to find unique glossary concept term types")
    for row in rows:
        if row[0] != 'Other':
            option = cgi.escape(row[0])
            html.append(u"<option%s>%s</option>" % (selected, option))
            selected = u""
    html.append(u"<option>Other</option></select>")
    return u"".join(html)

#----------------------------------------------------------------------
# Create the picklist for definition statuses; hard-wired from specs.
#----------------------------------------------------------------------
def makeDefinitionStatusPicklist():
    return (u"<select name='stat'>"
            u"<option selected='selected'>Approved</option>"
            u"<option>New pending</option>"
            u"<option>Revision pending</option>"
            u"<option>Rejected</option>"
            u"</select>")

#----------------------------------------------------------------------
# Create the picklist used to select an audience.
#----------------------------------------------------------------------
def makeAudiencePicklist():
    return (u"<select name='audi'>"
            u"<option selected='selected'>Patient</option>"
            u"<option>Health Professional</option>"
            u"</select>")

#----------------------------------------------------------------------
# Display the form for the report's parameters.
#----------------------------------------------------------------------
def createForm(cursor):
    form = u"""\
   <fieldset><legend>Report Criteria</legend>
    <input type='hidden' name='%s' value='%s' />
    <table border='0'>
     <tr>
      <th align='right'>Term Type:&nbsp;</th>
      <td>%s</td>
     </tr>
     <tr>
      <th align='right'>Term Name:&nbsp;</th>
      <td><input class='field' name='name' /></td>
     </tr>
     <tr>
      <th align='right'>Definition Text:&nbsp;</th>
      <td><input class='field' name='text' /></td>
     </tr>
     <tr>
      <th align='right'>Definition Status:&nbsp;</th>
      <td>%s</td>
     </tr>
     <tr>
      <th align='right'>Audience:&nbsp;</th>
      <td>%s</td>
     </tr>
     <tr>
      <th align='right'>Display Spanish?&nbsp;</th>
      <td align='left'><input type='checkbox' name='span' /></td>
     </tr>
    </table>
   </fieldset>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, makeTermTypePicklist(cursor),
       makeDefinitionStatusPicklist(), makeAudiencePicklist())
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Generate the Mailer Tracking Report.
#----------------------------------------------------------------------
def createReport(cursor, conceptType, status, audience, name, text, spanish):
    params = [conceptType, status, audience]
    query = """\
SELECT DISTINCT t.doc_id
           FROM query_term t
           JOIN query_term s
             ON t.doc_id = s.doc_id
           JOIN query_term a
             ON a.doc_id = s.doc_id
            AND LEFT(a.node_loc, 4) = LEFT(s.node_loc, 4)
"""
    if name:
        query += """\
           JOIN query_term c
             ON c.int_val = t.doc_id
           JOIN query_term n
             ON n.doc_id = c.doc_id
"""
    if text:
        query += """\
           JOIN query_term d
             ON d.doc_id = a.doc_id
            AND LEFT(d.node_loc, 4) = LEFT(a.node_loc, 4)
"""
    query += """\
          WHERE t.path = '/GlossaryTermConcept/TermType'
            AND s.path = '/GlossaryTermConcept/TermDefinition'
                       + '/DefinitionStatus'
            AND a.path = '/GlossaryTermConcept/TermDefinition/Audience'
            AND t.value = ?
            AND s.value = ?
            AND a.value = ?
"""
    if name:
        query += """\
            AND c.path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
            AND n.path = '/GlossaryTermName/TermName/TermNameString'
            AND n.value LIKE ?
"""
        params.append(name)
    if text:
        query += """\
            AND d.path = '/GlossaryTermConcept/TermDefinition/DefinitionText'
            AND d.value LIKE ?
"""
        params.append(text)
    query += """\
       ORDER BY t.doc_id
"""
    #cdrcgi.bail("QUERY: %s; PARAMS: %s" % (query, params))
    cursor.execute(query, tuple(params), timeout = 600)
    conceptIds = [row[0] for row in cursor.fetchall()]
    #cdrcgi.bail(conceptIds)
    concepts = [Concept(cid, cursor, audience, spanish) for cid in conceptIds]
    title = "%s - %s" % (section, language)
    report = [u"""\
<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   table { border-collapse: collapse; }
   th, td { border: 1px solid black; }
   td { vertical-align: top; }
   th { color: blue; }
   .replacement  { background-color: yellow; font-weight: bold; }
   h1 { font-size: 16pt; color: maroon; text-align: center; }
  </style>
 </head>
 <body>
  <h1>%s<br />%s<br />%s</h1>
  <table>
   <tr>
    <th>CDR ID of GTC</th>
""" % (title, title, conceptType, time.strftime("%Y-%m-%d %H:%M:%S"))]
    if spanish:
        report.append(u"""\
    <th>Term Names (English)</th>
    <th>Term Names (Spanish)</th>
    <th>Definition (English)</th>
    <th>Definition (Spanish)</th>
   </tr>
""")
    else:
        report.append(u"""\
    <th>Term Names (Pronunciations)</th>
    <th>Definition (English)</th>
   </tr>
""")
    report.append(u"""\
   </tr>
""")
    for concept in concepts:
        report.append(concept.toHtml(spanish))
    report.append(u"""\
  </table>
 </body>
</html>
""")
    cdrcgi.sendPage(u"".join(report))

#----------------------------------------------------------------------
# Create the report or as for the report parameters.
#----------------------------------------------------------------------
if termName or defText:
    createReport(cursor, termType, status, audience, termName, defText,
                 spanish)
else:
    createForm(cursor)
