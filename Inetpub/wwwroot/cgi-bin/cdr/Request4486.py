#----------------------------------------------------------------------
# "We need a new glossary term concept by type QC report to help us ensure
# consistency in the wording of definitions."
#
# BZIssue::4745 (eliminate empty pronunciation parens; ignore case mismatch)
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
import datetime
from lxml import etree
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
cursor    = db.connect(user="CdrGuest").cursor()
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields) or cdrcgi.bail("Please log in.")
request   = cdrcgi.getRequest(fields)
termType  = fields.getvalue("type")
termName  = fields.getvalue("name")
defText   = fields.getvalue("text")
status    = fields.getvalue("stat")
spanish   = fields.getvalue("span") == "Y"
audience  = fields.getvalue("audi")
logger    = cdr.Logging.get_logger("Request4486")
title     = "CDR Administration"
language  = spanish and "ENGLISH &amp; SPANISH" or "ENGLISH"
section   = "Glossary Term Concept by Type Report"
SUBMENU   = "Report Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'Request4486.py'
start     = datetime.datetime.now()

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)
if request == "Log Out":
    cdrcgi.logout(session)

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
def breakDownDefinition(node, with_tail=False):
    pieces = []
    if node.text is not None:
        pieces = [node.text]
    for child in node.findall("*"):
        if child.tag == "PlaceHolder":
            pieces.append(PlaceHolder(child.get("name")))
            if child.tail is not None:
                pieces.append(child.tail)
        else:
            pieces += breakDownDefinition(child, True)
    if with_tail and node.tail is not None:
        pieces.append(node.tail)
    return pieces

#----------------------------------------------------------------------
# Object in which we collect what we need for a glossary term name.
#----------------------------------------------------------------------
class Name:
    COUNT = 0
    def __init__(self, docId, spanish):
        Name.COUNT += 1
        self.docId         = docId
        self.englishName   = u""
        self.replacements  = {}
        self.blocked       = False
        self.pronunciation = u""
        self.spanishNames  = []

        docXml = resolveRevisionMarkup(docId)
        root = etree.fromstring(docXml)
        for node in root.findall("TermName/TermNameString"):
            self.englishName = cdr.get_text(node, u"")
        if not spanish:
            for node in root.findall("TermName/TermPronunciation"):
                self.pronunciation = cdr.get_text(node, u"")
        for node in root.findall("ReplacementText"):
            self.replacements[node.get("name")] = cdr.get_text(node, u"")
        if spanish:
            for node in root.findall("TranslatedName/TermNameString"):
                name = cdr.get_text(node)
                if name:
                    self.spanishNames.append(name)
        query = db.Query("document", "active_status")
        query.where(query.Condition("id", docId))
        if query.execute(cursor).fetchall()[0][0] == u"I":
            self.blocked = True

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
        for child in node.findall("DefinitionText"):
            self.text = breakDownDefinition(child)
        for child in node.findall("ReplacementText"):
            self.replacements[child.get("name")] = cdr.get_text(child, u"")
        for child in node.findall("Audience"):
            self.audiences.add(cdr.get_text(child, u"").upper())
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
    COUNT = 0
    def __init__(self, docId, cursor, audience, spanish):
        Concept.COUNT += 1
        self.docId = docId
        self.htmlBlocked = u"<span class='error'>[Blocked]</span>"
        query = db.Query("query_term", "doc_id").unique()
        query.where("path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'")
        query.where(query.Condition("int_val", docId))
        rows = query.execute(cursor).fetchall()
        self.names = [Name(row[0], spanish) for row in rows]
        docXml = resolveRevisionMarkup(docId)
        root = etree.fromstring(docXml)
        self.definitions = []
        for node in root.findall("TermDefinition"):
            definition = Definition(node)
            if audience.upper() in definition.audiences:
                self.definitions.append(definition)
        if spanish:
            self.spanishDefinitions = []
            for node in root.findall("TranslatedTermDefinition"):
                definition = Definition(node)
                if audience.upper() in definition.audiences:
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

        # Processing the Terms if English and Spanish need to be displayed
        # ----------------------------------------------------------------
        if spanish:
            spName = spDef = u""
            termBlocked = u""
            nameRowspan = 1
            if self.names and self.names[0].spanishNames:
                spName = self.names[0].spanishNames[0]
                if len(self.names[0].spanishNames) > 1:
                    nameRowspan = len(self.names[0].spanishNames)

            firstSpanishName = spName
            if self.spanishDefinitions:
                spDef = self.spanishDefinitions[0].resolve(reps, spName)

            # Need to indicate if a term has been blocked
            # -------------------------------------------
            if self.names[0].blocked:
                termBlocked = self.htmlBlocked

            html.append(u"""\
    <td rowspan='%d'>%s %s</td>
    <td>%s</td>
    <td rowspan='%d'>%s</td>
    <td rowspan='%d'>%s</td>
   </tr>
""" % (nameRowspan, cgi.escape(name), termBlocked, cgi.escape(spName),
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
                    if name.blocked:
                        termBlocked = self.htmlBlocked

                    html.append(u"""\
   <tr>
    <td rowspan='%d'>%s %s</td>
    <td>%s</td>
   </tr>
""" % (nameRowspan, cgi.escape(name.englishName), termBlocked,
                                                  cgi.escape(spName)))
                    for spName in name.spanishNames[1:]:
                        html.append(u"""\
   <tr>
    <td>%s</td>
   </tr>
""" % cgi.escape(spName))
        # Processing the Terms if only English names are requested
        # --------------------------------------------------------
        else:
            # Processing the first name
            # -------------------------
            termBlocked = u""
            if self.names and self.names[0].pronunciation:
                name += u" (%s)" % self.names[0].pronunciation

                # Need to indicate if a term has been blocked
                # -------------------------------------------
                if self.names[0].blocked:
                    termBlocked = self.htmlBlocked

            html.append(u"""\
    <td>%s %s</td>
    <td rowspan='%d'>%s</td>
   </tr>
""" % (cgi.escape(name), termBlocked, rowspan, enDef))

            # Processing all other names (except the first)
            # ---------------------------------------------
            for name in self.names[1:]:
                enName = name.englishName
                if name.pronunciation:
                    enName += (" (%s)" % name.pronunciation)
                if name.blocked:
                    termBlocked = self.htmlBlocked
                html.append(u"""\
   <tr>
    <td>%s %s</td>
   </tr>
""" % (cgi.escape(enName), termBlocked))

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
# Create the valid values lists.
#----------------------------------------------------------------------
query = db.Query("query_term", "value").unique().order(1)
query.where("path = '/GlossaryTermConcept/TermType'")
query.where("value <> 'Other'")
term_types = [row[0] for row in query.execute(cursor).fetchall()]
term_types.append("Other")
statuses = ("Approved", "New pending", "Revision pending", "Rejected")
audiences = ("Patient", "Health Professional")

#----------------------------------------------------------------------
# Validate the request parameters.
#----------------------------------------------------------------------
if termType and termType not in term_types:
    cdrcgi.bail("Corrupt form data")
if status and status not in statuses:
    cdrcgi.bail("Corrupt form data")
if audience and audience not in audiences:
    cdrcgi.bail("Corrupt form data")

#----------------------------------------------------------------------
# Display the form for the report's parameters.
#----------------------------------------------------------------------
def createForm():
    now = datetime.date.today()
    then = now - datetime.timedelta(7)
    page = cdrcgi.Page(title, subtitle=section, action=script,
                       buttons=buttons, session=session)
    instructions = u"""\
You must specifiy either a term name start, or text from the definitions
of the terms to be selected. All other selection criteria are required."""
    page.add(page.B.FIELDSET(page.B.P(instructions)))
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Selection Options"))
    page.add_select("type", "Term Type", term_types, term_types[0])
    page.add_text_field("name", "Term Name")
    page.add_text_field("text", "Definition Text")
    page.add_select("stat", "Definition Status", statuses, "Approved")
    page.add_select("audi", "Audience", audiences, audiences[0])
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Display Options"))
    page.add_radio("span", "English Only", "N", checked=True)
    page.add_radio("span", "Include Spanish", "Y")
    page.add("</fieldset>")
    page.add_css(".labeled-field label { width: 120px; }")
    page.send()

#----------------------------------------------------------------------
# Generate the Mailer Tracking Report.
#----------------------------------------------------------------------
def createReport(cursor, conceptType, status, audience, name, text, spanish):
    query = db.Query("query_term t", "t.doc_id").unique().order(1)
    query.join("query_term s", "s.doc_id = t.doc_id")
    query.join("query_term a", "a.doc_id = t.doc_id"
               " AND LEFT(a.node_loc, 4) = LEFT(s.node_loc, 4)")
    query.where("t.path = '/GlossaryTermConcept/TermType'")
    query.where("s.path = '/GlossaryTermConcept/TermDefinition"
                "/DefinitionStatus'")
    query.where("a.path = '/GlossaryTermConcept/TermDefinition/Audience'")
    query.where(query.Condition("t.value", conceptType))
    query.where(query.Condition("s.value", status))
    query.where(query.Condition("a.value", audience))
    if name:
        query.join("query_term c", "c.int_val = t.doc_id")
        query.join("query_term n", "n.doc_id = c.doc_id")
        query.where("c.path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'")
        query.where("n.path = '/GlossaryTermName/TermName/TermNameString'")
        query.where(query.Condition("n.value", name + "%", "LIKE"))
    if text:
        query.join("query_term d", "d.doc_id = a.doc_id"
                   " AND LEFT(d.node_loc, 4) = LEFT(a.node_loc, 4)")
        query.where("d.path = '/GlossaryTermConcept/TermDefinition"
                    "/DefinitionText'")
        query.where(query.Condition("d.value", "%" + text + "%", "LIKE"))
    # FOR DEBUGGING query.log(label="REQUEST4486 QUERY")
    conceptIds = [row[0] for row in query.execute(cursor, 600).fetchall()]
    logger.info("found %d concept IDs", len(conceptIds))
    concepts = [Concept(cid, cursor, audience, spanish) for cid in conceptIds]
    logger.info("concept objects loaded with %d names", Name.COUNT)
    title = "%s - %s" % (section, language)
    report = [u"""\
<!DOCTYPE html>
<html>
 <head>
  <meta charset="utf-8">
  <title>%s</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   table { border-collapse: collapse; }
   th, td { border: 1px solid black; }
   td { vertical-align: top; }
   th { color: blue; }
   .replacement  { background-color: yellow; font-weight: bold; }
   h1 { font-size: 16pt; color: maroon; text-align: center; }
   .error { color: red; font-weight: bold; }
   .timer { color: green; font-size: 8pt; }
  </style>
 </head>
 <body>
  <h1>%s<br />%s<br />%s</h1>
  <table>
   <tr>
    <th>CDR ID of GTC</th>
""" % (title, title, conceptType,
       datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))]
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
    elapsed = datetime.datetime.now() - start
    args = len(conceptIds), elapsed.total_seconds()
    timer = "Processed {:d} concepts in {:f} seconds".format(*args)
    report.append(u"""\
  </table>
  <p class="timer">{}</p>
 </body>
</html>
""".format(timer))
    cdrcgi.sendPage(u"".join(report))

#----------------------------------------------------------------------
# Create the report or as for the report parameters.
#----------------------------------------------------------------------
if termName or defText:
    try:
        createReport(cursor, termType, status, audience, termName, defText,
                     spanish)
    except Exception as e:
        logger.exception("report failed")
        cdrcgi.bail("report failed: {}".format(e))
else:
    createForm()
