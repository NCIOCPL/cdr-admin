#----------------------------------------------------------------------
#
# $Id: StaleGlossaryTerms.py,v 1.2 2006-06-29 14:24:00 bkline Exp $
#
# Glossary terms which haven't been modified since 2003-09-11.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/06/29 14:20:34  bkline
# One-off report for Sheri (request #2286).
#
#----------------------------------------------------------------------
import cdrdb, xml.dom.minidom, cdr, cdrcgi, cgi, sys

def fix(me):
    return me and cgi.escape(me) or u"&nbsp;"

class GlossaryTerm:
    def __init__(self, cdrId, name, definition):
        self.cdrId      = cdrId
        self.termName   = name
        self.definition = definition
                                
conn = cdrdb.connect()
cursor = conn.cursor('CdrGuest')
cursor.execute("CREATE TABLE #gt (id INTEGER, dt DATETIME)")
conn.commit()
cursor.execute("""\
INSERT INTO #gt
     SELECT t.document, MAX(t.dt)
       FROM audit_trail t
       JOIN action a
         ON t.action = a.id
       JOIN document d
         ON d.id = t.document
       JOIN doc_type g
         ON g.id = d.doc_type
      WHERE a.name IN ('ADD DOCUMENT', 'MODIFY DOCUMENT')
        AND g.name = 'GlossaryTerm'
     GROUP BY t.document
    HAVING MAX(t.dt) < '2003-09-12'""")
conn.commit()
cursor.execute("""\
         SELECT t.id, n.value, d.value
           FROM #gt t
LEFT OUTER JOIN query_term n
             ON t.id = n.doc_id
            AND n.path = '/GlossaryTerm/TermName'
LEFT OUTER JOIN query_term d
             ON t.id = d.doc_id
            AND d.path = '/GlossaryTerm/TermDefinition/DefinitionText'
       ORDER BY n.value""", timeout = 300)
terms = []
row = cursor.fetchone()
while row:
    terms.append(GlossaryTerm(row[0], row[1], row[2]))
    row = cursor.fetchone()
terms.sort(lambda a,b: cmp(a.termName, b.termName))
title = u'Glossary Terms Not Modified Since 2003-09-11'
html = [u"""\
<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   body { font-family: Arial; }
   h1   { font-size: 14pt; color: blue; }
   td, th { font-size: 10pt; }
   th   { color: green; }
   td   { color: maroon; }
  </style>
 </head>
 <body>
  <center><h1>%s</h1></center>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>DocID</th>
    <th>Term Name</th>
    <th>Definition</th>
   </tr>
""" % (title, title)]
for term in terms:
    html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (term.cdrId, fix(term.termName), fix(term.definition)))
html.append(u"""\
  </table>
 </body>
</html>
""")
cdrcgi.sendPage(u"".join(html))
