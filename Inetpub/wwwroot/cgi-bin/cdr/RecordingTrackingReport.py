#----------------------------------------------------------------------
# We need a Media Tracking report.  This spreadsheet report will keep track of
# the development and processing statuses of the Media documents.
#
# BZIssue::4880 - Board Meeting Recordings Tracking Report
#                 (report adapted from Media Tracking Report)
# BZIssue::5068 - [Media] Board Meeting Recording Tracking Report to
#                 display blocked documents
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------
import cgi
import cdr
import cdrdb
import cdrcgi
import datetime
import lxml.etree as etree
import sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
cursor   = cdrdb.connect("CdrGuest").cursor()
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
fromDate = fields.getvalue('FromDate')
toDate   = fields.getvalue('ToDate')
today    = datetime.date.today().strftime("%B %d, %Y")
title    = "CDR Administration"
instr    = "Board Meeting Recordings Tracking Report - %s" % today
buttons  = ["Submit", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
script   = "RecordingTrackingReport.py"

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Ask the user for the report parameters. William asked that the start
# date be hard-coded to March 1, 2010
#----------------------------------------------------------------------
if not cdrcgi.is_date(fromDate) or not cdrcgi.is_date(toDate):
    toDate = datetime.date.today()
    #fromDate = toDate - datetime.timedelta(30)
    fromDate = "2010-03-01"
    page = cdrcgi.Page(title, subtitle=instr, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select Date Range"))
    page.add_date_field("FromDate", "Start Date", value=fromDate)
    page.add_date_field("ToDate", "End Date", value=toDate)
    page.add("</fieldset>")
    page.send()

class Status:
    def __init__(self, node):
        self.value = u''
        self.date = u''
        self.comment = u''
        for child in node:
            if child.tag == "ProcessingStatusValue":
                self.value = child.text
            elif child.tag == "ProcessingStatusDate":
                self.date = child.text
            elif child.tag == "Comment" and not self.comment:
                self.comment = child.text.strip()

#----------------------------------------------------------------------
# Media document object definition.
#----------------------------------------------------------------------
class MediaDoc:
    def __init__(self, cursor, docId, docTitle, encoding):
        self.docId         = docId
        self.docTitle      = docTitle
        self.encoding      = encoding
        self.title         = None
        self.comment       = None
        self.dateCreated   = None
        self.dateVersioned = None
        self.statuses      = []

        # Get the date the document was first saved (this can be different
        # then the date of the first version)
        # ----------------------------------------------------------------
        query = cdrdb.Query("audit_trail t", "t.dt")
        query.join("action a", "a.id = t.action AND a.name = 'Add Document'")
        query.where(query.Condition("t.document", docId))
        rows = query.execute(cursor).fetchall()
        self.dateCreated = rows and rows[0][0] and str(rows[0][0])[:10] or None

        # Get the date the document was last versioned
        # ----------------------------------------------------------------
        query = cdrdb.Query("doc_version", "id", "MAX(num)", "dt",
                            "publishable").group("id", "dt", "publishable")
        query.where(query.Condition("id", docId))
        rows = query.execute(cursor).fetchall()
        self.dateVersioned = rows and rows[0][2] \
                                  and str(rows[0][2])[:10] or None
        self.flag = rows and rows[0][3] and str(rows[0][3]) or None

        # Get the XML of the document to select additional data elements
        # --------------------------------------------------------------
        query = cdrdb.Query("document", "xml")
        query.where(query.Condition("id", docId))
        docXml = query.execute(cursor).fetchall()[0][0]
        tree = etree.XML(docXml.encode("utf-8"))
        for node in tree:
            if node.tag == "ProcessingStatuses":
                for child in node:
                    if child.tag == "ProcessingStatus":
                        self.statuses.append(Status(child))
            elif node.tag == "MediaTitle":
                self.title = node.text
            elif node.tag == "Comment":
                self.comment = node.text

    def addToSheet(self, sheet, styles, row):
        sheet.write(row, 0, self.docId, styles.center)
        sheet.write(row, 1, self.title, styles.left)
        sheet.write(row, 2, self.encoding, styles.left)
        sheet.write(row, 3, self.dateCreated or u'', styles.center)
        sheet.write(row, 4, self.flag, styles.center)
        sheet.write(row, 5, self.dateVersioned, styles.center)
        sheet.write(row, 6, self.comment, styles.left)
        return row + 1

#----------------------------------------------------------------------
# Create/display the report. Can't use the active_doc view, because
# several of the meeting recording documents are blocked. String
# interpolation for the dates in the HAVING clause is safe, because
# we have vetted them with calls to cdrcgi.is_date().
#----------------------------------------------------------------------
query = cdrdb.Query("document d", "d.id", "d.title", "r.value", "MAX(v.dt)")
query.join("doc_type t", "t.id = d.doc_type")
query.join("doc_version v", "v.id = d.id")
query.join("query_term c", "d.id = c.doc_id")
query.join("query_term r", "d.id = r.doc_id")
query.where("c.path = '/Media/MediaContent/Categories/Category'")
query.where("r.path = '/Media/PhysicalMedia/SoundData/SoundEncoding'")
query.where("t.name = 'Media'")
query.where("c.value = 'Meeting Recording'")
query.group("d.id", "d.title", "r.value")
query.having("MAX(v.dt) BETWEEN '%s' AND '%s 23:59:59'" % (fromDate, toDate))
query.order("d.title").execute(cursor, 300)

#----------------------------------------------------------------------
# Set up the spreadsheet.
#----------------------------------------------------------------------
styles = cdrcgi.ExcelStyles()
sheet = styles.add_sheet("Board Meeting Recordings", frozen_rows=3)
widths = 10, 60, 10, 10, 15, 10, 60
headers = ("CDRID", "Media Title", "Encoding", "Date Created",
           "Last Version Publishable", "Version Date", "Comments")
assert(len(widths) == len(headers))
for i, chars in enumerate(widths):
    sheet.col(i).width = styles.chars_to_width(chars)
title = "Board Meeting Recordings Tracking Report"
subtitle = "From %s - %s" % (fromDate, toDate)
sheet.write_merge(0, 0, 0, len(headers) - 1, title, styles.banner)
sheet.write_merge(1, 1, 0, len(headers) - 1, subtitle, styles.header)
for i, header in enumerate(headers):
    sheet.write(2, i, header, styles.header)
row = 3
for docId, docTitle, encoding, created in cursor.fetchall():
    mediaDoc = MediaDoc(cursor, docId, docTitle, encoding)
    row = mediaDoc.addToSheet(sheet, styles, row)
now = datetime.datetime.now()
name = 'RecordingTrackingReport-%s.xls' % now.strftime("%Y%m%d%H%M%S")
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
print("Content-type: application/vnd.ms-excel")
print("Content-Disposition: attachment; filename=%s" % name)
print()
styles.book.save(sys.stdout)
