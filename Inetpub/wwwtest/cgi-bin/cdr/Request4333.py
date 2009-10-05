#----------------------------------------------------------------------
#
# $Id: Request4333.py,v 1.2 2009-03-02 16:10:25 bkline Exp $
#
# "We need a New Published Glossary Terms Report which will serve as a
# QC report to verify which new Glossary Term Name documents have been
# published within the given time frame.  We would like a new Mailer
# report so we can track responses easier.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2009/02/12 16:21:06  bkline
# New glossary report.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, time, sys, ExcelWriter, lxml.etree as etree

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
begin     = fields.getvalue("begin") or None
end       = fields.getvalue("end") or None
title     = "CDR Administration"
section   = "New Published Glossary Terms"
SUBMENU   = "Report Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'Request4333.py'
header    = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script type='text/javascript' language='JavaScript'
           src='/js/CdrCalendar.js'></script>
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
    .CdrDateField { width: 100px; }
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
# Object in which we collect what we need for the mailers.
#----------------------------------------------------------------------
class TermName:
    def __init__(self, docId, firstPub, cursor):
        self.docId = docId
        self.firstPub = firstPub
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/GlossaryTermName/TermName/TermNameString'
               AND doc_id = ?""", docId)
        self.enName = cursor.fetchall()[0][0]
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/GlossaryTermName/TranslatedName/TermNameString'
               AND doc_id = ?""", docId)
        self.spNames = [row[0] for row in cursor.fetchall()]
    def addToSheet(self, sheet, nextRow, style, urlStyle):
        spNames = u"; ".join(self.spNames)
        row = sheet.addRow(nextRow, style)
        nextRow += 1
        #mergeDown = None
        #if len(self.changes) > 1:
        #    mergeDown = len(self.changes) - 1
        row.addCell(1, self.docId) #, mergeDown = mergeDown)
        row.addCell(2, self.enName) #, mergeDown = mergeDown)
        row.addCell(3, u"; ".join(self.spNames))
        row.addCell(4, str(self.firstPub)[:10])
        return nextRow

#----------------------------------------------------------------------
# Display the form for the report's parameters.
#----------------------------------------------------------------------
def createForm(cursor):
    #mailerTypes = makeMailerTypePicklist(cursor)
    #categories  = makeChangeCategoryPicklist(cursor)
    now = time.strftime("%Y-%m-%d")
    then = str(cdr.calculateDateByOffset(-7))[:10]
    form = u"""\
   <input type='hidden' name='%s' value='%s' />
   <table border='0'>
    <tr>
     <th align='right'>Start Date: </th>
     <td><input class='CdrDateField' name='begin' id='begin'
                value='%s' /></td>
    </tr>
    <tr>
     <th align='right'>End Date: </th>
     <td><input class='CdrDateField' name='end' id='end'
                value='%s' /></td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, then, now)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Add the title row and the column headers.
#----------------------------------------------------------------------
def addColumnHeaders(book, sheet, startDate, endDate, total):
    font  = ExcelWriter.Font(size = 10, bold = True, color = 'blue')
    align = ExcelWriter.Alignment('Center', 'Top')
    style = book.addStyle(font = font, alignment = align)
    sheet.addCol(1,  70)
    sheet.addCol(2, 200)
    sheet.addCol(3, 200)
    sheet.addCol(4, 200)
    row = sheet.addRow(1, style)
    #row.addCell(1, u"Mailers Received - Detailed", mergeAcross = 6)
    #row = sheet.addRow(2, style)
    #row.addCell(1, "%s to %s" % (startDate, endDate), mergeAcross = 6)
    #row = sheet.addRow(3, style)
    #row.addCell(1, "Total: %d" % total, mergeAcross = 6)
    #row = sheet.addRow(5, style)
    row.addCell(1, u"CDR ID")
    row.addCell(2, u"Term Name (English)")
    row.addCell(3, u"Term Name (Spanish)")
    row.addCell(4, u"Date First Published")

#----------------------------------------------------------------------
# Generate the Mailer Tracking Report.
#----------------------------------------------------------------------
def createReport(cursor, startDate, endDate):
    cursor.execute("""\
        SELECT d.id, d.first_pub
          FROM document d
          JOIN doc_type t
            ON t.id = d.doc_type
         WHERE t.name = 'GlossaryTermName'
           AND d.first_pub BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
           AND d.active_status = 'A'
         ORDER BY d.id""" % (startDate, endDate), timeout = 300)
    rows = cursor.fetchall()
    names = []
    for docId, firstPub in rows:
        names.append(TermName(docId, firstPub, cursor))
    book = ExcelWriter.Workbook()
    sheet = book.addWorksheet('Term Names')
    addColumnHeaders(book, sheet, startDate, endDate, len(names))
    alignment = ExcelWriter.Alignment('Left', 'Top', True)
    font = ExcelWriter.Font('blue', True)
    style = book.addStyle(alignment = alignment)
    urlStyle = book.addStyle(font = font, alignment = alignment)
    nextRow = 2
    for name in names:
        nextRow = name.addToSheet(sheet, nextRow, style, urlStyle)
    font = ExcelWriter.Font(size = 10, bold = True)
    style = book.addStyle(font = font)
    row = sheet.addRow(nextRow, style)
    row.addCell(1, u"Total: %d" % len(names))
    try:
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except:
        pass
    stamp = time.strftime("%Y%m%d%H%M%S")
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=TermNames-%s.xls" % stamp
    print
    book.write(sys.stdout, True)

#----------------------------------------------------------------------
# Create the report or as for the report parameters.
#----------------------------------------------------------------------
if begin and end:
    createReport(cursor, begin, end)
else:
    createForm(cursor)
