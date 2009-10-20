#----------------------------------------------------------------------
#
# $Id$
#
# Glossary terms which haven't been modified since 2003-09-11.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2006/06/29 14:24:00  bkline
# Switched to CdrGuest DB account.
#
# Revision 1.1  2006/06/29 14:20:34  bkline
# One-off report for Sheri (request #2286).
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields) or 'guest'
request  = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "StaleGlossaryTerms.py"
title   = "CDR Administration"
section = "Stale Glossary Terms"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())

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
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not fromDate:
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='2003-09-12'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2003-09-12)</TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(header + form)


def fix(me):
    return me and cgi.escape(me) or u"&nbsp;"

class GlossaryTerm:
    def __init__(self, cdrId, name, definition):
        self.cdrId      = cdrId
        self.termName   = name
        self.definition = definition
                                
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
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
    HAVING MAX(t.dt) < ?""", fromDate) #'2003-09-12'""")
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
title = u'Glossary Terms Not Modified Since %s' % fromDate #2003-09-11'
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
