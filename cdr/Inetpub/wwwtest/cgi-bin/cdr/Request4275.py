#----------------------------------------------------------------------
#
# $Id: Request4275.py,v 1.4 2008-10-02 12:16:55 bkline Exp $
#
# "We would like a new Mailer report so we can track responses easier.
#
# Please place the report in Admin Menu/Reports/Mailers/
# "Mailers Received - Detailed"
#
# The user interface should be the following:
#
# Document Type (select "all"  or a specific Mailer Type value from picklist)
# Changes Category (select "all" or a specific  Changes Category value from
# picklist)
# Start Date (default one month from current date)
# End Date   (default current date) 
#
# The Output should be in a spreadsheet with the following columns:
#  DocID
#  Mailer Type
#  Recipient
#  Address
#  Document
#  Date Received
#  Changes Category"
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2008/09/15 19:13:22  bkline
# More tweaks requested by Sheri.
#
# Revision 1.2  2008/09/11 20:50:13  bkline
# Tweaks requested by Sheri after the fact.
#
# Revision 1.1  2008/09/11 18:45:44  bkline
# New report for Sheri on detailed mailer information.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, time, sys, ExcelWriter, lxml.etree as etree

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
mType     = fields.getvalue("mailerType") or None
category  = fields.getvalue("category") or None
begin     = fields.getvalue("begin") or None
end       = fields.getvalue("end") or None
title     = "CDR Administration"
section   = "Detailed Mailer Report"
SUBMENU   = "Report Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'Request4275.py'
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
class Mailer:
    class Doc:
        def __init__(self, docId, docTitle):
            self.docId = docId
            self.docTitle = docTitle
    recipients = {}
    documents  = {}
    urlBase    = (u"http://%s%s/QcReport.py?Session=guest&DocId=%%d" %
                  (cdrcgi.WEBSERVER, cdrcgi.BASE))
    def __init__(self, mailerId, cursor):
        self.docId = mailerId
        self.mailerType = u""
        self.address = u""
        self.recipient = None
        self.document = None
        self.response = u""
        self.changes = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", mailerId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        for e in tree.findall('Type'):
            self.mailerType = e.text.strip()
        for e in tree.findall('Recipient'):
            self.recipient = Mailer.getRecipient(e, cursor)
        for e in tree.findall('Document'):
            self.document = Mailer.getDocument(e, cursor)
        for e in tree.findall('MailerAddress/Email'):
            self.address = e.text.strip()
        for r in tree.findall('Response'):
            for e in r.findall('Received'):
                self.response = e.text[:10]
            for e in r.findall('ChangesCategory'):
                if e.text:
                    change = e.text.strip()
                    if change:
                        self.changes.append(change)
    @classmethod
    def getDocument(cls, e, cursor):
        docId = e.get('{cips.nci.nih.gov/cdr}ref')
        try:
            docId = cdr.exNormalize(docId)[1]
        except:
            return None
        if docId in cls.documents:
            return cls.documents[docId]
        cursor.execute("""\
            SELECT title
              FROM document
             WHERE id = ?""", docId)
        rows = cursor.fetchall()
        title = rows and rows[0][0] or u"" 
        cls.documents[docId] = Mailer.Doc(docId, title)
        return cls.documents[docId]
    @classmethod
    def getRecipient(cls, e, cursor):
        docId = e.get('{cips.nci.nih.gov/cdr}ref')
        try:
            docId = cdr.exNormalize(docId)[1]
        except:
            return None
        if docId in cls.recipients:
            return cls.recipients[docId]
        cursor.execute("""\
            SELECT title
              FROM document
             WHERE id = ?""", docId)
        rows = cursor.fetchall()
        title = rows and rows[0][0] or u""
        if title:
            title = title.split(";")
            if len(title) > 1 and title[0].lower() == 'inactive':
                title = u"%s (Inactive)" % title[1]
            else:
                title = title[0]
        cls.recipients[docId] = Mailer.Doc(docId, title)
        return cls.recipients[docId]
    def addToSheet(self, sheet, nextRow, style, urlStyle):
        row = sheet.addRow(nextRow, style)
        nextRow += 1
        mergeDown = None
        if len(self.changes) > 1:
            mergeDown = len(self.changes) - 1
        row.addCell(1, self.docId, mergeDown = mergeDown)
        row.addCell(2, self.mailerType, mergeDown = mergeDown)
        if self.recipient:
            href = self.urlBase % self.recipient.docId
            row.addCell(3, self.recipient.docTitle, style = urlStyle,
                        href = href, mergeDown = mergeDown)
        row.addCell(4, self.address or u" ", mergeDown = mergeDown)
        if self.document:
            row.addCell(5, self.document.docId, mergeDown = mergeDown)
            href = self.urlBase % self.document.docId
            row.addCell(6, self.document.docTitle, style = urlStyle,
                        href = href, mergeDown = mergeDown)
        row.addCell(7, self.response, mergeDown = mergeDown)
        if self.changes:
            row.addCell(8, self.changes[0])
            for c in self.changes[1:]:
                row = sheet.addRow(nextRow, style)
                nextRow += 1
                row.addCell(8, c)
        return nextRow

#----------------------------------------------------------------------
# Build a CGI form picklist for the mailer change categories.
#----------------------------------------------------------------------
def makeChangeCategoryPicklist(cursor):
    cursor.execute("""\
  SELECT DISTINCT value
    FROM query_term
   WHERE path = '/Mailer/Response/ChangesCategory'
     AND value IS NOT NULL
     AND value <> ''
ORDER BY value""", timeout = 300)
    html = [u"""\
<select name='category'>
 <option value=''>All</option>
"""]
    for row in cursor.fetchall():
        html.append(u"""\
 <option>%s</option>
""" % (cgi.escape(row[0])))
    html.append(u"""\
</select>
""")
    return u"".join(html)

#----------------------------------------------------------------------
# Build a CGI form picklist for the mailer types.
#----------------------------------------------------------------------
def makeMailerTypePicklist(cursor):
    cursor.execute("""\
  SELECT DISTINCT value
    FROM query_term
   WHERE path = '/Mailer/Type'
     AND value IS NOT NULL
     AND value <> ''
ORDER BY value""", timeout = 300)
    html = [u"""\
<select name='mailerType'>
 <option value=''>All</option>
"""]
    for row in cursor.fetchall():
        html.append(u"""\
<option>%s</option>
""" % (cgi.escape(row[0])))
    html.append(u"""\
</select>
""")
    return u"".join(html)

#----------------------------------------------------------------------
# Display the form for the report's parameters.
#----------------------------------------------------------------------
def createForm(cursor):
    mailerTypes = makeMailerTypePicklist(cursor)
    categories  = makeChangeCategoryPicklist(cursor)
    now = time.strftime("%Y-%m-%d")
    then = str(cdr.calculateDateByOffset(-30))[:10]
    form = u"""\
   <input type='hidden' name='%s' value='%s' />
   <table border='0'>
    <tr>
     <th align='right'>Mailer Type: </th>
     <td>%s</td>
    </tr>
    <tr>
     <th align='right'>Changes Category: </th>
     <td>%s</td>
    </tr>
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
""" % (cdrcgi.SESSION, session, mailerTypes, categories, then, now)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Add the title row and the column headers.
#----------------------------------------------------------------------
def addColumnHeaders(book, sheet, startDate, endDate, total):
    font  = ExcelWriter.Font(size = 12, bold = True)
    align = ExcelWriter.Alignment('Center', 'Top')
    style = book.addStyle(font = font, alignment = align)
    sheet.addCol(1,  70)
    sheet.addCol(2, 150)
    sheet.addCol(3, 200)
    sheet.addCol(4, 200)
    sheet.addCol(5,  70)
    sheet.addCol(6, 300)
    sheet.addCol(7,  70)
    sheet.addCol(8, 200)
    row = sheet.addRow(1, style)
    row.addCell(1, u"Mailers Received - Detailed", mergeAcross = 6)
    row = sheet.addRow(2, style)
    row.addCell(1, "%s to %s" % (startDate, endDate), mergeAcross = 6)
    row = sheet.addRow(3, style)
    row.addCell(1, "Total: %d" % total, mergeAcross = 6)
    row = sheet.addRow(5, style)
    row.addCell(1, u"DocID")
    row.addCell(2, u"Mailer Type")
    row.addCell(3, u"Recipient")
    row.addCell(4, u"Address")
    row.addCell(5, u"CDR ID")
    row.addCell(6, u"Document")
    row.addCell(7, u"Date Received")
    row.addCell(8, u"Changes Category")

#----------------------------------------------------------------------
# Generate the Mailer Tracking Report.
#----------------------------------------------------------------------
def createReport(cursor, mailerType, changeCategory, startDate, endDate):
    userEndDate = endDate
    try:
        endDate = str(cdr.calculateDateByOffset(1, endDate[:10]))
    except:
        cdrcgi.bail("Invalid end date: '%s'" % endDate)
    where = ("WHERE r.value BETWEEN ? and ? "
             "AND r.path = '/Mailer/Response/Received'")
    join = ""
    parms = [startDate, endDate]
    if mailerType:
        where += " AND t.value = ? AND t.path = '/Mailer/Type'"
        join += " JOIN query_term t ON r.doc_id = t.doc_id"
        parms.append(mailerType)
    if changeCategory:
        where += (" AND c.value = ? "
                  "AND c.path = '/Mailer/Response/ChangesCategory'")
        join += " JOIN query_term c ON c.doc_id = r.doc_id"
        parms.append(changeCategory)
    sql = u"""\
        SELECT DISTINCT r.doc_id
          FROM query_term r
          %s
         %s
      ORDER BY r.doc_id""" % (join, where)
    cursor.execute(sql, parms)
    mailerIds = [row[0] for row in cursor.fetchall()]
    book = ExcelWriter.Workbook()
    sheet = book.addWorksheet('Mailers')
    addColumnHeaders(book, sheet, startDate, userEndDate, len(mailerIds))
    alignment = ExcelWriter.Alignment('Left', 'Top', True)
    font = ExcelWriter.Font('blue', True)
    style = book.addStyle(alignment = alignment)
    urlStyle = book.addStyle(font = font, alignment = alignment)
    nextRow = 6
    for mailerId in mailerIds:
        mailer = Mailer(mailerId, cursor)
        nextRow = mailer.addToSheet(sheet, nextRow, style, urlStyle)
    try:
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except:
        pass
    stamp = time.strftime("%Y%m%d%H%M%D")
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=SummMailRep-%s.xls" % stamp
    print
    book.write(sys.stdout, True)

#----------------------------------------------------------------------
# Create the report or as for the report parameters.
#----------------------------------------------------------------------
if begin and end:
    createReport(cursor, mType, category, begin, end)
else:
    createForm(cursor)
