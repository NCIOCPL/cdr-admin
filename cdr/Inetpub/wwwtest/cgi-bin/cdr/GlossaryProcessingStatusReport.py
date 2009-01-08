#----------------------------------------------------------------------
#
# $Id: GlossaryProcessingStatusReport.py,v 1.1 2009-01-08 22:08:56 bkline Exp $
#
# "The Processing Status Report will display the documents (GTC and GTN)
# that correspond with the Processing Status selected by the user."
#
# Sheri says we are only to use the first processing status we find.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi
etree = cdr.importEtree()

#----------------------------------------------------------------------
# Collect the CGI field data.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
status   = fields.getvalue('status')
showAll  = fields.getvalue('all')
language = fields.getvalue('language')
audience = fields.getvalue('audience')
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
title    = "Glossary Processing Status Report"
script   = "GlossaryProcessingStatusReport.py"
SUBMENU  = "Report Menu"
buttons  = ("Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out")
header   = cdrcgi.header(title, title, title, script, buttons)

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
# Object representing a glossary term name.
#----------------------------------------------------------------------
class Name:
    def __init__(self, docId, cursor, conceptId = None):
        self.docId = docId
        self.string = u"[NO NAME]"
        self.status = u""
        self.comment = u""
        self.conceptId = conceptId
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        for n in tree.findall('TermName'):
            for s in n.findall('TermNameString'):
                self.string = s.text
        eName = language == 'en' and 'TermName' or 'TranslatedName'
        for n in tree.findall(eName):
            comments = n.findall('Comment')
            if comments:
                self.comment = Comment(comments[0])
                break
        for statuses in tree.findall('ProcessingStatuses'):
            for status in statuses.findall('ProcessingStatus'):
                for statusValue in status.findall('ProcessingStatusValue'):
                    v = statusValue.text
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
        return u"%s (CDR%d)" % (cgi.escape(self.string), self.docId)

#----------------------------------------------------------------------
# Object representing a glossary term concept.
#----------------------------------------------------------------------
class Concept:
    def __init__(self, docId, cursor = None):
        self.docId = cursor and docId or u''
        self.status = u""
        self.names = {}
        self.comment = u""
        if cursor:
            cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
            docXml = cursor.fetchall()[0][0]
            tree = etree.XML(docXml.encode('utf-8'))
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
                        v = statusValue.text
                        if v:
                            self.status = v
                    if self.status:
                        break

#----------------------------------------------------------------------
# Object which records what we need to know for a comment.
#----------------------------------------------------------------------
class Comment:
    def __init__(self, node):
        self.text = node.text
        self.audience = node.get('audience') or u''
        self.date = node.get('date') or u''
        self.user = node.get('user') or u''
    def __unicode__(self):
        return u"[audience=%s; date=%s; user=%s] %s" % (self.audience,
                                                        self.date,
                                                        cgi.escape(self.user),
                                                        cgi.escape(self.text))

#----------------------------------------------------------------------
# Generate the report.
#----------------------------------------------------------------------
def report(status):

    # Collect all the concepts with matching processing statuses.
    concepts = {}
    cursor = cdrdb.connect('CdrGuest').cursor()
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

    # Collect all the names with matching processing statuses.
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
                concept = Concept(name.conceptId, showAll and cursor or None)
                concepts[name.conceptId] = concept
            concept.names[docId] = name

    # Fill in any names with the wrong statuses if we're showing everything.
    if showAll:
        for conceptId in concepts:
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

    # Build the HTML report.
    html = [u"""\
<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   h1 { font-size: 14pt; color: maroon; font-family: Arial, sans-serif; }
   h1 { text-align: center; }
   th { color: blue; }
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
    <th>CDR ID of GTC</th>
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
        if showAll or concept.status == status:
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

#----------------------------------------------------------------------
# Put up the request form for the report.
#----------------------------------------------------------------------
def showForm():
    docType = cdr.getDoctype('guest', 'GlossaryTermName')
    validVals = dict(docType.vvLists)
    vvList = validVals['ProcessingStatusValue']
    statusValues = set(vvList)
    docType = cdr.getDoctype('guest', 'GlossaryTermConcept')
    validVals = dict(docType.vvLists)
    vvList = validVals['ProcessingStatusValue']
    statusValues |= set(vvList)
    form = [u"""\
   <input type='hidden' name='%s' value='%s'>
   <table>
    <tr>
     <td align='right'><b>Processing Status:&nbsp;</b></td>
     <td>
      <select name='status'>
       <option value=''>Select Processing Status Value</option>
""" % (cdrcgi.SESSION, session)]
    for statusValue in statusValues:
        form.append(u"""\
       <option value='%s'>%s</option>
""" % (statusValue, statusValue))
    form.append(u"""\
      </select>
     </td>
    </tr>
    <tr>
     <td align='right'>
      <b>Show ALL related term names and concepts?:&nbsp;</b>
     </td>
     <td><input type='checkbox' name='all' /></td>
    </tr>
    <tr>
     <td align='right'><b>Language:&nbsp;</b></td>
     <td>
      English <input type='radio' name='language' value='en' />
      &nbsp;
      Spanish <input type='radio' name='language' value='es' />
     </td>
    </tr>
    <tr>
     <td align='right'><b>Audience:&nbsp;</b></td>
     <td>
      Patient
      <input type='radio' name='audience' value='Patient' />
      &nbsp;
      Health professional
      <input type='radio' name='audience' value='Health professional' />
     </td>
    </tr>
    <tr>
     <td colspan='2'><i>The required language and audience choices
      determine which comments will be included in the report.</i></td>
    </tr>
   </table>
  </form>
 </body>
</html>""")
    cdrcgi.sendPage(header + u"".join(form))

if status and language and audience:
    report(status)
else:
    showForm()
