#----------------------------------------------------------------------
#
# $Id: GlossaryTermsByStatus.py,v 1.1 2004-10-07 21:39:33 bkline Exp $
#
# The Glossary Terms by Status Report will server as a QC report to check
# which glossary terms were created within a given time frame with a
# particular status set.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, string, time, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
status   = fields and fields.getvalue("status") or None
session  = fields and fields.getvalue("Session") or None
request  = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate') or None
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
       <OPTION VALUE='Approved'>Approved</OPTION>
       <OPTION VALUE='Pending'>Pending</OPTION>
      </SELECT>
     </TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, fromDate, toDate)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Create/display the report.
#----------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT s.doc_id, MIN(a.dt)
      FROM query_term s
      JOIN audit_trail a
        ON a.document = s.doc_id
     WHERE s.path = '/GlossaryTerm/TermStatus'
       AND s.value = ?
--       AND MIN(a.dt) BETWEEN 'xs' AND DATEADD(s, -1, DATEADD(d, 1, 'xs'))
  GROUP BY s.doc_id
  HAVING MIN(a.dt) BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))""" % (fromDate, toDate), status)
class GlossaryTerm:
    def __init__(self, id, node):
        self.id = id
        self.name = None
        self.pronunciation = None
        self.definitions = []
        self.source = None
        for child in node.childNodes:
            if child.nodeName == "TermName":
                self.name = cdr.getTextContent(child)
            elif child.nodeName == "TermPronunciation":
                self.pronunciation = cdr.getTextContent(child)
            elif child.nodeName == "TermDefinition":
                for grandchild in child.childNodes:
                    if grandchild.nodeName == "DefinitionText":
                        self.definitions.append(cdr.getTextContent(grandchild))
                        break
            elif child.nodeName == "TermSource":
                self.source = cdr.getTextContent(child)
terms = []
for row in cursor.fetchall():
    doc = cdr.getDoc('guest', row[0], getObject = True)
    dom = xml.dom.minidom.parseString(doc.xml)
    terms.append(GlossaryTerm(row[0], dom.documentElement))
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
   th      { font-size: 12pt; font-weight: bold }
   td      { font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <body>
  <center>
   <span class='t1'>Glossary Terms by Status</span>
   <br />
   <br />
   <span class='t2'>%s Terms<br />From %s to %s</span>
  </center>
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>CDR ID</th>
    <th>Term</th>
    <th>Pronunciation</th>
    <th>Definition</th>
    <th>Definition Source</th>
   </tr>
""" % (status, fromDate, toDate)
for term in terms:
    html += u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (term.id,
       term.name and cgi.escape(term.name) or u"&nbsp;",
       term.pronunciation and cgi.escape(term.pronunciation) or u"&nbsp;",
       term.definitions and cgi.escape(u"; ".join(term.definitions)) or u"&nbsp;",
       term.source and cgi.escape(term.source) or u"&nbsp;")
cdrcgi.sendPage(html + u"""\
  </table>
 </body>
</html>
""")
