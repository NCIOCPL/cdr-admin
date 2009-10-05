#----------------------------------------------------------------------
#
# $Id: GlossaryConceptDocsModified.py,v 1.2 2008-10-30 12:39:16 bkline Exp $
#
# "The Glossary Term Concept - Documents Modified Report will serve as a
# QC report to verify which documents were changed within a given time
# frame. The report will be separated into English and Spanish.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2008/10/14 12:51:55  bkline
# New "documents modified" reports for restructured glossary documents.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, time, ExcelWriter, sys, lxml.etree as etree

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
startDate = fields.getvalue("startdate")
endDate   = fields.getvalue("enddate")
language  = fields.getvalue("language")
audience  = fields.getvalue("audience")
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "Glossary Concept Documents Modified Report"
instr     = "Glossary Concept Documents Modified Report"
script    = "GlossaryConceptDocsModified.py"
SUBMENU   = "Report Menu"
buttons   = ("Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out")
header    = cdrcgi.header(title, title, instr, script, buttons)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we don't have the required parameters, ask for them.
#----------------------------------------------------------------------
if not startDate or not endDate or not language or not audience:
    now = cdr.calculateDateByOffset(0)
    then = cdr.calculateDateByOffset(-7)
    form   = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE>
    <TR>
     <TD ALIGN='right'><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='startdate' VALUE='%s' />
      (use format YYYY-MM-DD for dates, e.g. 2005-01-01)
     </TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>End Date:&nbsp;</B></TD>
     <TD><INPUT NAME='enddate' VALUE='%s' /></TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>Language:&nbsp;</B></TD>
     <TD>
      English <INPUT TYPE='radio' NAME='language' VALUE='en' />
      &nbsp;
      Spanish <INPUT TYPE='radio' NAME='language' VALUE='es' />
     </TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>Audience:&nbsp;</B></TD>
     <TD>
      Patient
      <INPUT TYPE='radio' NAME='audience' VALUE='Patient' />
      &nbsp;
      Health professional
      <INPUT TYPE='radio' NAME='audience' VALUE='Health professional' />
     </TD>
    </TR>
    <TR>
     <TD COLSPAN='2'><I>The required language and audience choices
      determine which comments will be included in the report.</I></TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, then, now)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Object for GlossaryTerm document info we need.
#----------------------------------------------------------------------
class GlossaryTermConcept:
    class Comment:
        def __init__(self, node):
            self.text     = node.text
            self.date     = node.get('date', None)
            self.audience = node.get('audience', None)
            self.user     = node.get('user', None)
        def __cmp__(self, other):
            return cmp(self.date, other.date)
        def toString(self):
            return u"[date: %s; user: %s; audience: %s] %s" % (self.date,
                                                               self.user,
                                                               self.audience,
                                                               self.text)
    def __init__(self, docId, docVersion, language, audience, cursor):
        cursor.execute("""\
            SELECT v.title, v.xml, v.publishable, d.first_pub
              FROM doc_version v
              JOIN document d
                ON d.id = v.id
             WHERE v.id = ?
               AND v.num = ?""", (docId, docVersion))
        rows                  = cursor.fetchall()
        tree                  = etree.XML(rows[0][1].encode('utf-8'))
        self.docId            = docId
        self.docVersion       = docVersion
        self.publishable      = rows[0][2] == 'Y'
        self.title            = rows[0][0]
        self.firstPub         = rows[0][3]
        self.comment          = None
        self.dateLastModified = None
        elementName           = 'TermDefinition'
        if language != 'en':
            elementName = 'TranslatedTermDefinition'
        for definitionNode in tree.findall(elementName):
            if language == 'en' or definitionNode.get('language') == language:
                audienceNodes = definitionNode.findall('Audience')
                audiences = set([n.text for n in audienceNodes])
                if audience in audiences:
                    commentNodes = definitionNode.findall('Comment')
                    if commentNodes:
                        self.comment = self.Comment(commentNodes[0])
                    dlmNode = definitionNode.find('DateLastModified')
                    if dlmNode is not None:
                        self.dateLastModified = dlmNode.text
                    break

#----------------------------------------------------------------------
# Create the report.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT v.id, MAX(v.num)
      FROM doc_version v
      JOIN doc_type t
        ON t.id = v.doc_type
      JOIN active_doc a
        ON v.id = a.id
     WHERE t.name = 'GlossaryTermConcept'
       AND v.dt BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
  GROUP BY v.id""" % (startDate, endDate), timeout = 300)
rows = cursor.fetchall()
terms = []
for docId, docVersion in rows:
    term = GlossaryTermConcept(docId, docVersion, language, audience, cursor)
    terms.append(term)
terms.sort(lambda a, b: cmp(a.title, b.title))
book   = ExcelWriter.Workbook('CDR', 'NCI')
align  = ExcelWriter.Alignment(vertical = 'Top', wrap = True)
normal = book.addStyle(alignment = align)
align  = ExcelWriter.Alignment(vertical = 'Top', horizontal = 'Center')
center = book.addStyle(alignment = align)
sheet  = book.addWorksheet('GlossaryTerm')
font   = ExcelWriter.Font('#FFFFFF', bold = True)
bkgrd  = ExcelWriter.Interior('#0000FF')
align  = ExcelWriter.Alignment('Center', 'Center', True)
hdrs   = book.addStyle(alignment = align, font = font, interior = bkgrd)
row    = sheet.addRow(1, hdrs)
sheet.addCol(1, 50)
sheet.addCol(2, 70)
sheet.addCol(3, 75)
sheet.addCol(4, 70)
sheet.addCol(5, 350)
row.addCell(1, u'DocId')
row.addCell(2, u'Date Last Modified')
row.addCell(3, u'Publishable?')
row.addCell(4, u'Date First Published')
row.addCell(5, u'Last Comment')
rowNum = 2
for term in terms:
    dlm = term.dateLastModified or ''
    if dlm:
        dlm = dlm[:10]
    firstPub = term.firstPub or ''
    if firstPub:
        firstPub = firstPub[:10]
    row = sheet.addRow(rowNum, normal)
    row.addCell(1, term.docId, 'Number', center)
    row.addCell(2, dlm, style = center)
    row.addCell(3, term.publishable and u'Y' or u'N', style = center)
    row.addCell(4, firstPub, style = center)
    row.addCell(5, term.comment and term.comment.toString() or u'')
    rowNum += 1
try:
    import os, msvcrt
    msvcrt.setmode (1, os.O_BINARY)
except:
    cdrcgi.bail("Failure setting binary mode")
now  = time.strftime("%Y%m%d%H%M%S")
name = 'GlossaryConceptDocumentsModified-%s.xls' % now
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
book.write(sys.stdout, True)
