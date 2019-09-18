#----------------------------------------------------------------------
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
# BZIssue::4304 - modifications requested by William
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, time, sys, lxml.etree as etree
from cdrapi import db
from html import escape as html_escape

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
    conn = db.connect(user='CdrGuest')
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail('Database connection failure: %s' % e)

#----------------------------------------------------------------------
# Object in which we collect what we need for the mailers.
#----------------------------------------------------------------------
class Mailer:
    class Doc:
        def __init__(self, docId, docTitle):
            self.docId = docId
            self.docTitle = docTitle
    all_changes = 0
    recipients = {}
    documents  = {}
    urlBase    = (u"https://%s%s/QcReport.py?Session=guest&DocId=%%d" %
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
            self.mailerType = self.get_text(e)
        for e in tree.findall('Recipient'):
            self.recipient = Mailer.getRecipient(e, cursor)
        for e in tree.findall('Document'):
            self.document = Mailer.getDocument(e, cursor)
        for e in tree.findall('MailerAddress/Email'):
            self.address = self.get_text(e)
        for r in tree.findall('Response'):
            for e in r.findall('Received'):
                self.response = self.get_text(e)[:10]
            for e in r.findall('ChangesCategory'):
                change = self.get_text(e)
                if change:
                    self.changes.append(change)
                    Mailer.all_changes += 1
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
    def addToSheet(self, styles, sheet, row):
        sheet.write(row, 0, self.docId, styles.left)
        sheet.write(row, 1, self.mailerType, styles.left)
        if self.recipient:
            url = self.urlBase % self.recipient.docId
            link = styles.link(url, self.recipient.docTitle)
            sheet.write(row, 2, link, styles.url)
        sheet.write(row, 3, self.address, styles.left)
        if self.document:
            doc_id = self.document.docId
            url = self.urlBase % doc_id
            link = styles.link(url, self.document.docTitle)
            sheet.write(row, 4, doc_id, styles.left)
            sheet.write(row, 5, link, styles.url)
        sheet.write(row, 6, self.response, styles.left)
        sheet.write(row, 7, "\n".join(self.changes), styles.left)
        return row + 1
    @staticmethod
    def get_text(node):
        if node is None or node.text is None:
            return ""
        return node.text.strip()

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
ORDER BY value""")
    html = [u"""\
<select name='category'>
 <option value=''>All</option>
"""]
    for row in cursor.fetchall():
        html.append(u"""\
 <option>%s</option>
""" % (html_escape(row[0])))
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
ORDER BY value""")
    html = [u"""\
<select name='mailerType'>
 <option value=''>All</option>
"""]
    for row in cursor.fetchall():
        html.append(u"""\
<option>%s</option>
""" % (html_escape(row[0])))
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
def addColumnHeaders(styles, sheet, startDate, endDate, total):
    banner = "Mailers Received - Detailed"
    date_range = "%s to %s" % (startDate, endDate)
    total = "Total: %d" % total
    widths = (10, 40, 40, 40, 10, 60, 10, 40)
    labels = ("DocID", "Mailer Type", "Recipient", "Email Address", "CDR ID",
              "Document", "Date Received", "Changes Category")
    assert(len(widths) == len(labels))
    for col, chars in enumerate(widths):
        sheet.col(col).width = styles.chars_to_width(chars)
    sheet.write_merge(0, 0, 0, len(labels) - 1, banner, styles.banner)
    sheet.write_merge(1, 1, 0, len(labels) - 1, date_range, styles.header)
    sheet.write_merge(2, 2, 0, len(labels) - 1, total, styles.header)
    for col, label in enumerate(labels):
        sheet.write(4, col, label, styles.header)

#----------------------------------------------------------------------
# Generate the Mailer Tracking Report.
#----------------------------------------------------------------------
def createReport(cursor, mailerType, changeCategory, startDate, endDate):
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
    styles = cdrcgi.ExcelStyles()
    sheet = styles.add_sheet("Mailers")
    addColumnHeaders(styles, sheet, startDate, endDate, len(mailerIds))
    row = 5
    for mailerId in mailerIds:
        mailer = Mailer(mailerId, cursor)
        row = mailer.addToSheet(styles, sheet, row)
    try:
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except:
        pass
    stamp = time.strftime("%Y%m%d%H%M%S")
    print("Content-type: application/vnd.ms-excel")
    print("Content-Disposition: attachment; filename=SummMailRep-%s.xls" % stamp)
    print()
    styles.book.save(sys.stdout)

#----------------------------------------------------------------------
# Create the report or as for the report parameters.
#----------------------------------------------------------------------
if begin and end:
    createReport(cursor, mType, category, begin, end)
else:
    createForm(cursor)
