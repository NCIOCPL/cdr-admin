#----------------------------------------------------------------------
# "The Processing Status Report will display the documents (GTC and GTN)
# that correspond with the Processing Status selected by the user."
#
# Sheri says we are only to use the first processing status we find.
#
# BZIssue::4705
# BZIssue::4777
# JIRA::OCECDR-3800
#----------------------------------------------------------------------
import cdr
import cdrcgi
from cdrapi import db
import cgi
from lxml import etree

#----------------------------------------------------------------------
# Collect the CGI field data.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
status   = fields.getvalue("status")
show_all = fields.getvalue("all") == "yes"
language = fields.getvalue("language")
audience = fields.getvalue("audience")
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
title    = "Glossary Processing Status Report"
script   = "GlossaryProcessingStatusReport.py"
SUBMENU  = "Report Menu"
buttons  = ("Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out")

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
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Collect the list of status values.
#----------------------------------------------------------------------
def get_status_values():
    values = set()
    for name in ('GlossaryTermName', 'GlossaryTermConcept'):
        doc_type = cdr.getDoctype('guest', name)
        valid_vals = dict(doc_type.vvLists)
        vv_list = valid_vals['ProcessingStatusValue']
        values |= set(vv_list)
    return values

#----------------------------------------------------------------------
# Extract text recursively from etree element.
#----------------------------------------------------------------------
def getText(e, pieces = None):
    if pieces is None:
        pieces = []
        top = True
    else:
        top = False
    if e.text is not None:
        pieces.append(e.text)
    for child in e:
        getText(child, pieces)
    if e.tail is not None:
        pieces.append(e.tail)
    if top:
        return u"".join(pieces)

#----------------------------------------------------------------------
# For Spanish names we need to know whether they're alternate names.
#----------------------------------------------------------------------
class SpanishName:
    def __init__(self, node):
        self.string = u""
        self.alternate = node.get('NameType') == 'alternate'
        for s in node.findall('TermNameString'):
            self.string = getText(s)
    def __unicode__(self):
        # Can't call cgi.escape() if string = None
        if self.string:
            name = cgi.escape(self.string)
        else:
            name = u""
        if self.alternate:
            return u"<span class='alt'>%s</span>" % name
        return name

#----------------------------------------------------------------------
# Object representing a glossary term name.
#----------------------------------------------------------------------
class Name:
    def __init__(self, docId, cursor, conceptId = None):
        self.docId = docId
        self.string = u"[NO NAME]"
        self.spanish = []
        self.status = u""
        self.comment = u""
        self.conceptId = conceptId
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        for n in tree.findall('TermName'):
            for s in n.findall('TermNameString'):
                self.string = getText(s)
        for n in tree.findall('TranslatedName'):
            self.spanish.append(SpanishName(n))
        eName = language == 'en' and 'TermName' or 'TranslatedName'
        for n in tree.findall(eName):
            comments = n.findall('Comment')
            if comments:
                self.comment = Comment(comments[0])
                break
        for statuses in tree.findall('ProcessingStatuses'):
            for status in statuses.findall('ProcessingStatus'):
                for statusValue in status.findall('ProcessingStatusValue'):
                    v = getText(statusValue)
                    if v:
                        self.status = v
                if self.status:
                    break
        if self.conceptId is None:
            cursor.execute("""\
        SELECT DISTINCT int_val
          FROM query_term
         WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
           AND doc_id = ?""", docId)
            rows = cursor.fetchall()
            self.conceptId = rows and rows[0][0] or u""
    def __unicode__(self):
        if 'spanish' not in status.lower():
            return u"%s (CDR%d)" % (cgi.escape(self.string), self.docId)
        return u"%s (CDR%d)" % (u"; ".join([u"%s" % n for n in self.spanish]),
                                self.docId)

#----------------------------------------------------------------------
# Object representing a glossary term concept.
#----------------------------------------------------------------------
class Concept:
    def __init__(self, docId, cursor = None):
        self.docId = cursor and docId or u''
        self.status = u""
        self.names = {}
        self.comment = u""
        if self.docId:
            cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
            row = cursor.fetchone()
            if not row:
                return
            tree = etree.XML(row[0].encode('utf-8'))
            eName = 'TermDefinition'
            if language != 'en':
                eName = 'TranslatedTermDefinition'
            for d in tree.findall(eName):
                for a in d.findall('Audience'):
                    if a.text == audience:
                        comments = d.findall('Comment')
                        if comments:
                            self.comment = Comment(comments[0])
                            break
            for statuses in tree.findall('ProcessingStatuses'):
                for status in statuses.findall('ProcessingStatus'):
                    for statusValue in status.findall('ProcessingStatusValue'):
                        v = getText(statusValue)
                        if v:
                            self.status = v
                    if self.status:
                        break

#----------------------------------------------------------------------
# Object which records what we need to know for a comment.
#----------------------------------------------------------------------
class Comment:
    def __init__(self, node):
        self.text = getText(node)
        self.audience = node.get('audience') or u''
        self.date = node.get('date') or u''
        self.user = node.get('user') or u''
    def __unicode__(self):
        text = self.text
        if not text:
            text = u"[NO TEXT ENTERED FOR COMMENT]"
        return u"[audience=%s; date=%s; user=%s] %s" % (self.audience,
                                                        self.date,
                                                        cgi.escape(self.user),
                                                        cgi.escape(text))

#----------------------------------------------------------------------
# Scrub the values to make sure they haven't been tampered with.
#----------------------------------------------------------------------
status_values = get_status_values()
if status not in status_values:
    status = None
if language not in ("en", "es"):
    language = None
if audience not in ("Patient", "Health Professional"):
    audience = None

#----------------------------------------------------------------------
# If we don't have a report request, show the request form.
#----------------------------------------------------------------------
if not status or not language or not audience:
    page = cdrcgi.Page("CDR Reports", subtitle=title, action=script,
                       buttons=buttons, session=session)
    instructions = (
        "All fields are required. The option to include linked glossary "
        "documents causes the report to include glossary term concept "
        "documents which do not have the selected status but are linked "
        "by at least one glossary term name document which does have "
        "that status. It also causes the inclusion of glossary term name "
        "documents which do not have the selected status but whose concept "
        "document has that status."
    )
    page.add(page.B.FIELDSET(page.B.P(instructions)))
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select Processing Status"))
    page.add_select("status", "Status", sorted(status_values))
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Include Linked Glossary Documents?"))
    page.add_radio("all", "Show only documents with selected status", "no",
                   checked=True)
    page.add_radio("all",
                   "Also show linked glossary documents with other statuses",
                   "yes")
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Language"))
    page.add_radio("language", "English", "en", checked=True)
    page.add_radio("language", "Spanish", "es")
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Audience"))
    page.add_radio("audience", "Patient", "Patient", checked=True)
    page.add_radio("audience", "Health Professional", "Health Professional")
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Collect all the concepts with matching processing statuses.
#----------------------------------------------------------------------
concepts = {}
cursor = db.connect(user='CdrGuest').cursor()
cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/GlossaryTermConcept/ProcessingStatuses'
                         + '/ProcessingStatus/ProcessingStatusValue'
                AND value = ?""", status)
for row in cursor.fetchall():
    docId = row[0]
    concept = Concept(docId, cursor)
    if concept.status == status:
        concepts[docId] = concept

#----------------------------------------------------------------------
# Collect all the names with matching processing statuses.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/GlossaryTermName/ProcessingStatuses'
                         + '/ProcessingStatus/ProcessingStatusValue'
                AND value = ?""", status)
for row in cursor.fetchall():
    docId = row[0]
    name = Name(docId, cursor)
    if name.status == status:
        concept = concepts.get(name.conceptId)
        if concept is None:
            concept = Concept(name.conceptId, show_all and cursor or None)
            concepts[name.conceptId] = concept
        concept.names[docId] = name

#----------------------------------------------------------------------
# Fill in any names with the wrong statuses if we're showing everything.
#----------------------------------------------------------------------
if show_all:
    for conceptId in concepts:
        if not conceptId:
            continue
        concept = concepts[conceptId]
        cursor.execute("""\
   SELECT DISTINCT doc_id
              FROM query_term
             WHERE path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
               AND int_val = ?""", conceptId)
        for row in cursor.fetchall():
            nameId = row[0]
            if nameId not in concept.names:
                concept.names[nameId] = Name(nameId, cursor, conceptId)

#----------------------------------------------------------------------
# Assemble the report.
#----------------------------------------------------------------------
html = [u"""\
<!DOCTYPE html>
<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   h1 { font-size: 14pt; color: maroon; font-family: Arial, sans-serif; }
   h1 { text-align: center; }
   th { color: blue; }
   .alt { color: red; }
   table { border-collapse: collapse; empty-cells: show; border-spacing: 0; }
   th, td { border: black solid 1px; padding: 3px; }
   body { font-family: "Times New Roman", serif; }
   h1 { font-size: 16pt; }
   th, td { font-size: 11pt; }
  </style>
 </head>
 <body>
  <h1>%s</h1>
  <table>
   <tr>
    <th colspan='3'>Glossary Term Concept</th>
    <th colspan='3'>Glossary Term Name</th>
   </tr>
   <tr>
    <th>CDR ID</th>
    <th>Processing Status</th>
    <th>Last Comment</th>
    <th>Term Names</th>
    <th>Processing Status</th>
    <th>Last Comment</th>
   </tr>
""" % (title, title)]
conceptIds = concepts.keys()
conceptIds.sort()
for conceptId in conceptIds:
    concept = concepts[conceptId]
    nameIds = concept.names.keys()
    rowspan = len(nameIds) or 1
    gtcId = gtcStatus = gtcComment = gtn = gtnStatus = gtnComment = u""
    if show_all or concept.status == status:
        gtcId = concept.docId
        gtcStatus = concept.status or u""
        gtcComment = concept.comment or u""
    nameIds.sort()
    if nameIds:
        gtn = concept.names[nameIds[0]]
        gtnStatus = gtn.status
        gtnComment = gtn.comment
    html.append(u"""\
   <tr>
    <td valign='top' rowspan='%d'>%s</td>
    <td valign='top' rowspan='%d'>%s</td>
    <td valign='top' rowspan='%d'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (rowspan, gtcId, rowspan, gtcStatus, rowspan, gtcComment,
       gtn, gtnStatus, gtnComment))
    for nameId in nameIds[1:]:
        name = concept.names[nameId]
        html.append(u"""\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (name, name.status, name.comment))
html.append(u"""\
  </table>
 </body>
</html>""")
cdrcgi.sendPage(u"".join(html))
