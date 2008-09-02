#----------------------------------------------------------------------
#
# $Id: ProtocolsLinkedToTerms.py,v 1.1 2008-09-02 20:44:01 bkline Exp $
#
# "We would like a modified version of the Linked documents report for
# Terms linked to Protocols.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, ExcelWriter, cdrdb, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
docId    = fields.getvalue("DocId")          or None
docTitle = fields.getvalue("DocTitle")       or None
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
title    = "Linked Documents Report"
instr    = "Protocols Linked to Terms"
script   = "ProtocolsLinkedToTerms.py"
SUBMENU  = 'Report Menu'
buttons  = (SUBMENU, cdrcgi.MAINMENU)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Object holding what we need for one row of the report.
#----------------------------------------------------------------------
class Protocol:
    def __init__(self, docId, docType, cursor):
        self.docId      = docId
        self.docType    = docType
        self.title      = None
        self.categories = []
        self.status     = None
        if docType == 'CTGovProtocol':
            path = '/CTGovProtocol/OverallStatus'
        elif docType == 'InScopeProtocol':
            path = '/%s/ProtocolAdminInfo/CurrentProtocolStatus' % docType
        else:
            path = None
        if path:
            cursor.execute("""\
                SELECT value
                  FROM query_term
                 WHERE path = '%s'
                   AND doc_id = ?""" % path, docId)
            for row in cursor.fetchall():
                self.status = row[0]
        if docType == 'CTGovProtocol':
            prefix = '/CTGovProtocol/PDQIndexing'
        else:
            prefix = '/%s/ProtocolDetail' % docType
        path = '%s/StudyCategory/StudyCategoryName' % prefix
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '%s'
               AND doc_id = ?""" % path, docId)
        for row in cursor.fetchall():
            self.categories.append(row[0])
        if docType == 'CTGovProtocol':
            cursor.execute("""\
                SELECT value
                  FROM query_term
                 WHERE path = '/CTGovProtocol/OfficialTitle'
                   AND doc_id = ?""", docId)
        else:
            cursor.execute("""\
                SELECT p.value
                  FROM query_term p
                  JOIN query_term t
                    ON p.doc_id = t.doc_id
                   AND LEFT(p.node_loc, 4) = LEFT(t.node_loc, 4)
                 WHERE p.path = '/%s/ProtocolTitle'
                   AND t.path = '/%s/ProtocolTitle/@Type'
                   AND t.value = 'Professional'
                   AND p.doc_id = ?""" % (docType, docType), docId)
        for row in cursor.fetchall():
            self.title = row[0]
    def __cmp__(self, other):
        return cmp(self.docId, other.docId)
        t1 = self.title and self.title.lower() or u''
        t2 = other.title and other.title.lower() or u''
        diff = cmp(t1, t2)
        if diff:
            return diff
        return cmp(self.docId, other.docId)

#----------------------------------------------------------------------
# If we have a document ID, produce a report.
#----------------------------------------------------------------------
if docId:
    try:
        docId = cdr.exNormalize(docId)[1]
    except:
        cdrcgi.bail("Invalid document ID '%s'" % docId)

    # Find the protocols linked to this term.
    query = """\
        SELECT DISTINCT d.id, t.name
           FROM document d
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN link_net n
             ON n.source_doc = d.id
          WHERE n.target_doc = ?
            AND t.name IN ('InScopeProtocol', 'CTGovProtocol',
                           'ScientificProtocolInfo')"""
    try:
        cursor.execute(query, docId, timeout = 300)
        rows = cursor.fetchall()
    except Exception, e:
        cdrcgi.bail('Database query failure: %s' % e)
    protocols = [Protocol(row[0], row[1], cursor) for row in rows]

    # Build the report and show it.
    now = time.strftime("%Y-%m-%d")
    title = "Protocols Linked to Terms %s" % now
    book = ExcelWriter.Workbook()
    sheet = book.addWorksheet("Linking Protocols")
    
    try:
        import msvcrt, os, sys
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except:
        pass

    font      = ExcelWriter.Font(size = 12, bold = True)
    align     = ExcelWriter.Alignment('Center', 'Bottom', wrap = True)
    style1    = book.addStyle(font = font, alignment = align)
    align     = ExcelWriter.Alignment('Left', 'Top', wrap = True)
    style2    = book.addStyle(alignment = align)
    row1      = sheet.addRow(1, style1)
    row2      = sheet.addRow(2, style1)
    row4      = sheet.addRow(4, style1)
    rowNumber = 5
    sheet.addCol(1,  70)
    sheet.addCol(2, 300)
    sheet.addCol(3, 150)
    sheet.addCol(4, 150)
    sheet.addCol(5, 100)
    row1.addCell(1, title, mergeAcross = 4)
    row2.addCell(1, "Total: %d" % len(protocols), mergeAcross = 4)
    row4.addCell(1, "CDR ID")
    row4.addCell(2, "Protocol Title")
    row4.addCell(3, "Study Category Name")
    row4.addCell(4, "Current Protocol Status")
    row4.addCell(5, "Document Type")
    protocols.sort()
    for p in protocols:
        row = sheet.addRow(rowNumber, style2)
        rowNumber += 1
        row.addCell(1, p.docId)
        row.addCell(2, p.title)
        row.addCell(3, u"; ".join(p.categories))
        row.addCell(4, p.status)
        row.addCell(5, p.docType)
    stamp = time.strftime("%Y%m%d%H%M%D")
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=p2t-%s.xls" % stamp
    print
    book.write(sys.stdout, True)
    sys.exit(0)

#----------------------------------------------------------------------
# Search for linked document by title, if so requested.
#----------------------------------------------------------------------
if docTitle:
    header   = cdrcgi.header(title, title, instr, script, ("Submit",
                                                           SUBMENU,
                                                           cdrcgi.MAINMENU))
    titleParam = docTitle
    if docTitle[-1] != '%':
        titleParam += '%'
    query = """\
SELECT d.id, d.title
  FROM document d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE d.title LIKE ?
   AND t.name = 'Term'"""
    try:
        cursor.execute(query, titleParam)
        row = cursor.fetchone()

        # Check to make sure we got at least one row.
        if not row:
            cdrcgi.bail("No documents match '%s'" % docTitle)
        form = []
        while row:
            form.append(u"""\
    <input type='radio' name='DocId' value='%d' /> CDR%010d %s<br />
""" % (row[0], row[0], cgi.escape(row[1])))
            row = cursor.fetchone()
        form.append("""\
   <input type='hidden' name='%s' value='%s'>
  </form>
 </body>
</html>""" % (cdrcgi.SESSION, session and session or ''))
        form = u"".join(form)
    except Exception, e:
        cdrcgi.bail('Database query failure: %s' % e)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Put up the main request form.
#----------------------------------------------------------------------
header   = cdrcgi.header(title, title, instr, script, ("Submit",
                                                       SUBMENU,
                                                       cdrcgi.MAINMENU))
form     = u"""\
   <TABLE CELLSPACING='1' CELLPADDING='1' BORDER='0'>
    <TR>
     <TD ALIGN='right'><B>Term Document ID:&nbsp;</B></TD>
     <TD><INPUT NAME='DocId' SIZE='13' /></TD>
    <TR><TD align='center'>or</TD></TR>
    <TR>
     <TD ALIGN='right'><B>Term Document Title:&nbsp;</B></TD>
     <TD><INPUT NAME='DocTitle' SIZE='50' /></TD>
    </TR>
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session and session or '')
cdrcgi.sendPage(header + form)
