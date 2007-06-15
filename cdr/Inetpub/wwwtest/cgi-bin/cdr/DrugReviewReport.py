#----------------------------------------------------------------------
# $Id: DrugReviewReport.py,v 1.1 2007-06-15 04:04:09 ameyer Exp $
#
# Produce an Excel spreadsheet showing problematic drug terms, divided
# into three categories:
#
#   New NCI Thesaurus drug terms.
#   New CDR drug terms.
#   Drug terms requiring review.
#
# Each category appears on a separate worksheet (page) within the overall
# spreadsheet.
#
# Users enter a date range from which to select terms into an HTML form
# and the software then produces the Excel format report.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------

import sys, cgi, cgitb, time, xml.sax, xml.sax.handler, os, os.path
import cdr, cdrcgi, cdrdb, ExcelWriter

cgitb.enable()

# Global worksheet row number, reset for each sheet in workbook
G_wsRow = 0

# Form buttons
BT_SUBMIT  = "Submit"
BT_ADMIN   = cdrcgi.MAINMENU
BT_REPORTS = "Reports Menu"
BT_LOGOUT  = "Logout"
buttons = (BT_SUBMIT, BT_REPORTS, BT_ADMIN, BT_LOGOUT)

session   = None
startDate = None
endDate   = None
errMsg    = ""

fields = cgi.FieldStorage()

# Action
if fields:
    session = cdrcgi.getSession(fields) or cdrcgi.bail("Please login")

    # Navigation
    action = cdrcgi.getRequest(fields)
    if action == BT_REPORTS:
        cdrcgi.navigateTo("Reports.py", session)
    if action == BT_ADMIN:
        cdrcgi.navigateTo("Admin.py", session)
    if action == BT_LOGOUT:
        cdrcgi.logout(session)

    # If user has entered a start date, we've got what we need.
    if fields.has_key("startDate"):\
        # Validate dates
        startDate = fields.getvalue('startDate')
        if not cdr.strptime(startDate, '%Y-%m-%d'):
            errMsg = "Invalid start date '%s' " % startDate
            startDate = None
        if fields.has_key("endDate"):
            endDate = fields.getvalue('endDate')
            if not cdr.strptime(endDate, '%Y-%m-%d'):
                errMsg += "Invalid end date '%s' " % endDate
                startDate = None
        else:
            errMsg += "Missing end date"

        if errMsg:
            errMsg += ".  Please use yyyy-mm-dd format."

# Format errors
if errMsg:
    errMsg = "<p><strong><font color='red'>%s</font></strong></p>" % errMsg

if not startDate or errMsg:
    # If no start date, or invalid one, the form has not been display,
    #   or not filled in, or not filled in correctly
    # Display an HTML form on screen

    # Default dates are 7 days ago to today
    now = time.time()
    ago = now - (7 * 24 * 60 * 60)
    startDate = time.strftime("%Y-%m-%d", time.localtime(ago))
    endDate   = time.strftime("%Y-%m-%d", time.localtime(now))

    # Construct html form
    header = cdrcgi.header("Administrative Subsystem",
             "Drug Review Report", "Drug review report",
             script="DrugReviewReport.py", buttons=buttons)
    html = header + """
<p>To prepare an Excel format report of Drug/Agent terms,
enter a start date and an optional end date for the
creation or import of Drug/Agent terms.  Terms of semantic type
"Drug/Agent" that were created or imported in the specified date
range will be included in the report.</p>

%s

<table width='40%%' border='0'>
 <tr>
  <th align="right">Start date:</th>
  <td><input type='text' name='startDate' value='%s' size='12' /></td>
 </tr><tr>
  <th align="right">End date:</th>
  <td><input type='text' name='endDate' value='%s' size='12' /></td>
 </tr>
 <input type="hidden" name=%s value=%s />
</table>
</form>
</body>
</html>
""" % (errMsg, startDate, endDate, cdrcgi.SESSION, session)

    # Send html and exit
    cdrcgi.sendPage(html)

# If we got here, user clicked submit with valid start and end dates
# Create an Excel workbook
wb = ExcelWriter.Workbook('ahm', 'NCI')

# Create Style objects for Excel
colLabelInterior     = ExcelWriter.Interior("#0000FF", "Solid")
docSeparatorInterior = ExcelWriter.Interior("#C0C0C0", "Solid")
colLabelFont         = ExcelWriter.Font(color="#FFFFFF", bold=True)
sheetNameFont        = ExcelWriter.Font(color="#000000", bold=True)

centerAlign          = ExcelWriter.Alignment(horizontal="Center")
leftAlign            = ExcelWriter.Alignment(horizontal="Left")
dataAlign            = ExcelWriter.Alignment(horizontal="Left",
                                             vertical="Top", wrap="1")

colLabelStyle        = wb.addStyle(name="colLabel", alignment=centerAlign,
                          font=colLabelFont, interior=colLabelInterior)
docSeparatorStyle    = wb.addStyle(name="docSeparator",
                          interior=docSeparatorInterior)
sheetNameStyle       = wb.addStyle(name="sheetName", alignment=leftAlign,
                          font=sheetNameFont)
dataStyle            = wb.addStyle(name="data", alignment=dataAlign)
errorStyle           = wb.addStyle(name="errorStyle", alignment=centerAlign,
                          font=sheetNameFont)

#----------------------------------------------------------------------
# Parser controls for the three worksheets
#----------------------------------------------------------------------

class ColControl:
    """
    Controls the construction of one column.
    There is one sequence of these for each worksheet.
    Some controls are used in more than one worksheet.
    """
    def __init__(self, label, element, index, width=50, funcs=()):
        """
        Pass:
            label    - Column header.
            element  - Element name as ustring.
            index    - Column index
            width    - Width in numeric Excel "points".
            funcs    - Sequence of functions with following interface:
                        Pass:
                            Current ColControl
                            Current text content
                            Current attributes from sax parse
                            Current worksheet
                        Return:
                            Modified or unmodifed text.
                       Func can do whatever it needs to do.
        """
        self.label    = label
        self.element  = element
        self.index    = index
        self.width    = width
        self.funcs    = funcs
        self.style    = None

class DocHandler(xml.sax.handler.ContentHandler):
    """
    Sax parser content handler for Term documents.
    """
    def __init__(self, ws, ctlHash, docId, dt, dtCol):
        """
        Content handler constructor.

        Pass:
            ws      - ExcelWriter.Worksheet, already initialized.
            ctlHash - Dictionary of path -> ColControl for all
                      elements (xpaths) that have some processing.
            docId   - Always written to column 1 of sheet.
            dt      - Create/import date, written to dtCol column.
            dtCol   - Column number, origin 1, for create/import date.
        """
        self.ws      = ws
        self.ctlHash = ctlHash
        self.docId   = docId
        self.dt      = dt[0:10]
        self.dtCol   = dtCol

    def startDocument(self):
        """
        Initialization needed for each new document.
        """
        global G_wsRow

        # ColControl we're currently working on, nest them in a stack
        self.colCtls = []
        self.curCtl  = None

        # Stack of full xpaths to current node push at start, pop at end
        self.fullPath  = []

        # Many paths are ignored, curPath has content only if we're
        #   working on one that should not be ignored
        self.curPath = None

        # Text is gathered here in characters() callback
        self.text = ""

        # Tracking count of OtherName elements
        # 2nd and subsequent OtherName element starts a new row
        self.otherNameCount = 0

        # Tracking review status
        # There are several of them in the doc, need to know the current
        #   one, if it's problematic
        self.reviewStatus = None

        # Tracking last element
        # Need to know if /Term/Comment follows PreferredName or some
        #   other element
        self.lastElement = None

        # Next spreadsheet row we're working on
        self.ssRow = G_wsRow

        # Put docId and create/import date in the right colums
        self.curRow = self.ws.addRow(self.ssRow, style=dataStyle)
        # Excel likes to warn you if you send a number as a string,
        #   even if you explicitly say it's a String!
        self.curRow.addCell(1, self.docId, dataType='Number')
        self.curRow.addCell(self.dtCol, str(self.dt))

    def startElement(self, name, attrs):
        """
        When encountering a field.
        """
        global dataStyle

        # Construct full path to this field
        fullPath = self.pathPush(name)

        # Here's the hack for adding OtherName rows
        if fullPath == "/Term/OtherName":
            self.otherNameCount += 1
            if self.otherNameCount > 1:
                self.ssRow += 1
                self.curRow = self.ws.addRow(self.ssRow, dataStyle)

        # Is it of interest?
        if self.ctlHash.has_key(fullPath):
            self.curCtl = self.ctlHash[fullPath]
            self.colCtls.append(self.curCtl)
            self.curPath = fullPath

            # XXX Do I always want attrs?  Maybe yes, maybe no
            self.attrs = attrs

    def characters(self, content):
        """
        If we're working on a field of interest, accumulate content.
        """
        if self.curCtl:
            self.text += content

    def endElement(self, name):
        """
        If we complete a field of interest, process it
        """
        # If there is a current field of interest
        if self.curCtl:
            # If this is the end of that field
            if self.curPath == self.pathGet():

                # Execute any fancy routines
                for func in self.curCtl.funcs:
                    self.text = func(self)

                # If there's any text (or any left after funcs)
                #   add it to the spreadsheet in current row
                if self.text:
                    self.curRow.addCell(self.curCtl.index, self.text)

                # We're done work on field
                self.curCtl = None
                self.colCtls.pop()
                self.curPath = None
                self.text = ""

        # Whether we did anything with it or not, we're done with this field
        self.pathPop()

    def endDocument(self):
        """
        Cleanup.
        """
        # Update global row
        global G_wsRow
        G_wsRow = self.ssRow + 1

    #------------------------------------------------------------------
    # path stack helpers
    #------------------------------------------------------------------
    def pathPush(self, elemName):
        """
        Add a name to the path.

        Pass:
            elemName - plain element name, no path prefix, no namespace.

        Return:
            Full path as a string.
        """
        fullPath = self.pathGet() + '/' + elemName
        self.fullPath.append(fullPath)
        return fullPath

    def pathPop(self):
        """
        Remove an item from the top of the fullPath stack, returning it.
        """
        return self.fullPath.pop()

    def pathGet(self):
        """
        Return the current path, but without popping it off the stack.
        Return empty string if stack is empty.
        """
        pathLen = len(self.fullPath)
        if pathLen > 0:
            return self.fullPath[len(self.fullPath)-1]
        return ""

def addCols(sheet, colList):
    """
    Create columns in a worksheet using a sequence of ColControls

    Pass:
        sheet   - Worksheet to add to.
        colList - Sequence of columns
    """
    # First column gets special label styling
    for col in colList:
        sheet.addCol(col.index, col.width)


def addWorksheet(session, wb, title, colList, qry, dateCol):
    """
    Create a complete worksheet using style for this report.

    Creates the worksheet and adds all rows to it.

    Pass:
        session - Logged in session.
        wb      - Workbook created via ExcelWriter.
        title   - column header.
        colList - Sequence of ColControls for sheet.
        qry     - SQL query to select rows for the sheet.  Each row must
                  have two columns, CDR doc ID, doc creation date.
        dateCol - Worksheet column for create/import date.

    Return:
        Reference to sheet
    """
    global G_wsRow
    global sheetNameStyle, colLabelStyle, errorStyle, docSeparatorStyle
    global dataStyle

    # ExcelWriter creates the worksheet
    ws = wb.addWorksheet(title, frozenRows=2)

    # Setup standard rows
    sheetRow = ws.addRow(1, style=sheetNameStyle)
    sheetRow.addCell(1, value=title)
    labelRow = ws.addRow(2, style=colLabelStyle)

    # First row for document data
    G_wsRow = 3

    # Setup column headers in 2rd row
    for col in colList:
        ws.addCol(col.index, col.width)
        if col.label:
            labelRow.addCell(col.index, col.label)

    # Index the column list
    # Also remember highest column received
    colHash = {}
    colHash['@@maxColIndex'] = 0
    for col in colList:
        colHash[col.element] = col
        if col.index > colHash['@@maxColIndex']:
            colHash['@@maxColIndex'] = col.index

    # Perform SQL selection
    rows = None
    conn = cdrdb.connect()
    try:
        cursor = conn.cursor()
        cursor.execute(qry)
        rows = cursor.fetchall()
        cursor.close()
    except cdrdb.Error, info:
        cdrcgi.bail("Database error searching for %s:<br> %s" % (
                    title, str(info)))

    # If no rows, tell user
    if len(rows) == 0:
        errRow = ws.addRow(3, style=errorStyle)
        errRow.addCell(1, "NO DOCUMENTS FOUND")

        # We're done with this worksheet
        return

    # Process each document found by the query
    docCount = 0
    for row in rows:
        (docId, docDate) = row

        # Fetch the XML for this ID
        docXml = cdr.getCDATA(cdr.getDoc(session, docId))
        if not docXml:
            # Found a bad doc in database
            cdr.logwrite("DrugReviewReport.py can't get docXml for docId=%d" \
                         % docId)
            continue
        docCount += 1

        # If past the first doc, create a separator row
        if docCount > 1:
            row = ws.addRow(G_wsRow, style=docSeparatorStyle)
            row.addCell(1, " ", style=docSeparatorStyle,
                        mergeAcross=colHash['@@maxColIndex'] - 1)
            G_wsRow += 1

        # Parse and process the document
        # Parse uses and updates G_wsRow, tracking spreadsheet rows
        xml.sax.parseString(docXml, DocHandler(ws, colHash, docId, docDate,
                                               dateCol))


def chkReviewStatus(handler):
    """
    Called when we get a ReviewStatus.
    Saves info that enables us to determine if the block we are working
    on is 'Problematic'.
    """
    if handler.text == 'Problematic':
        handler.problematic = handler.fullPath
    else:
        handler.problematic = None


def addComment(handler):
    """
    Call this function if a comment is received.
    It adds text to an already existing cell in the worksheet.
    """
    # Only add the comment if it has an attribute CommentAudience="External"
    #DBG if True:
    # XXX My test data doesn't have this attr.
    if handler.attrs.has_key("CommentAudience"):
        if handler.attrs.getValue("CommentAudience") == "External":

            # Get current value in the ColControl.index cell
            cell = handler.curRow.getCell(handler.curCtl.index)
            if (cell):
                value = cell.getValue()
            else:
                value = ""
                cell = handler.curRow.addCell(handler.curCtl.index, value)

            # Style the text of the comment.
            # Users wanted a new line, italics and different color, but
            #   Bob found no Python/Perl/Excel interface for that
            comment = "  **comment: [%s]" % handler.text

            # Append comment text to it
            value += comment

            # Replace cell content using the new value
            cell.replaceValue(value)

            # Don't do anything else with comment
            return ""

#----------------------------------------------------------------------
# Main
#----------------------------------------------------------------------

# Get the document id for the Term doc for semantic type = 'Drug/Agent'
conn = cdrdb.connect()
drugAgentDocId = 0
try:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT doc_id
          FROM query_term
         WHERE path='/Term/PreferredName'
           AND value='Drug/Agent'
    """)
    row = cursor.fetchone()
    drugAgentDocId = row[0]
    cursor.close()
except cdrdb.Error, info:
    cdrcgi.bail("Database error fetching Drug/Agent docId: %s" % (str(info)))

#----------------------------------------------------------------------
# Worksheet 1: New drugs from NCI Thesaurus
#----------------------------------------------------------------------
wsCols = (
    ColControl("CDR ID", None, 1, 45),
    ColControl("Preferred Name", u"/Term/PreferredName", 2, 100),
    ColControl("Other Names", u"/Term/OtherName/OtherTermName", 3, 88),
    ColControl("Other Name Type", u"/Term/OtherName/OtherNameType", 4, 105),
    ColControl("Source",
        u"/Term/OtherName/SourceInformation/VocabularySource/SourceCode",
        5, 90),
    ColControl("TType",
       u"/Term/OtherName/SourceInformation/VocabularySource/SourceTermType",
       6, 70),
    ColControl("SourceID",
       u"/Term/OtherName/SourceInformation/VocabularySource/SourceTermId",
       7, 45),
    ColControl("Definition", u"/Term/Definition/DefinitionText", 8, 210),
    ColControl("Date Created", None, 9, 65),
    ColControl(None, u"/Term/Comment", 1, 0, (addComment,)),
    ColControl(None, u"/Term/ReviewStatus", 1, 0, (chkReviewStatus,)),
    ColControl(None, u"/Term/OtherName/ReviewStatus", 1,0,(chkReviewStatus,)),
    ColControl(None, u"/Term/Definition/ReviewStatus", 1,0,(chkReviewStatus,)),
)

qry = """
SELECT a.document, a.dt
  FROM audit_trail a
  JOIN query_term q1
    ON q1.doc_id = a.document
  JOIN query_term q2
    ON q2.doc_id = a.document
 WHERE q1.path = '/Term/SemanticType/@cdr:ref'
   AND q1.int_val = %d
   AND a.action = 1
   AND q2.path = '/Term/OtherName/SourceInformation/VocabularySource/SourceCode'
   AND q2.value = 'NCI Thesaurus'
  AND a.dt > '%s'
  AND a.dt < '%s'
 GROUP BY a.document, a.dt
""" % (drugAgentDocId, startDate, endDate)

# cdrcgi.bail("here")
ws = addWorksheet(session, wb, "New Drugs from NCI Thesaurus", wsCols,
                  qry, 9)

#----------------------------------------------------------------------
# Worksheet 2: New drugs from the CDR
#----------------------------------------------------------------------
wsCols = (
    ColControl("CDR ID", None, 1, 45),
    ColControl("Preferred Name", u"/Term/PreferredName", 2, 140),
    ColControl("Other Names", u"/Term/OtherName/OtherTermName", 3, 140),
    ColControl("Other Name Type", u"/Term/OtherName/OtherNameType", 4, 105),
    ColControl("Date Created", None, 5, 65),
    ColControl(None, u"/Term/Comment", 1, 0, (addComment,)),
    ColControl(None, u"/Term/ReviewStatus", 1, 0, (chkReviewStatus,)),
    ColControl(None, u"/Term/OtherName/ReviewStatus", 1,0,(chkReviewStatus,)),
)

qry = """
SELECT a.document, a.dt
  FROM audit_trail a
  JOIN query_term q1
    ON q1.doc_id = a.document
 WHERE q1.path = '/Term/SemanticType/@cdr:ref'
   AND q1.int_val = %d
   AND a.action = 1
   AND a.dt > '%s'
   AND a.dt < '%s'
   AND a.document NOT IN (
    SELECT doc_id
      FROM query_term
     WHERE path='/Term/OtherName/SourceInformation/VocabularySource/SourceCode'
       AND value = 'NCI Thesaurus'
    )
 GROUP BY a.document, a.dt
""" % (drugAgentDocId, startDate, endDate)

ws = addWorksheet(session, wb, "New Drugs from the CDR", wsCols, qry, 5)

# DEBUG
#DBG fname = "d:/cdr/log/DrugTerm.xls"
#DBG if os.path.exists(fname):
#DBG     os.remove(fname)
#DBG fp = open(fname, "wb")
#DBG wb.write(fp, False)
#DBG fp.close()
#DBG cdr.logout(session)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=DrugReviewReport.xls"
print
wb.write(sys.stdout, True)
