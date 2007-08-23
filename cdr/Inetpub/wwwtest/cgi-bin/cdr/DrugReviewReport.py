#----------------------------------------------------------------------
# $Id: DrugReviewReport.py,v 1.6 2007-08-23 19:36:31 ameyer Exp $
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
# Revision 1.5  2007/08/09 14:24:33  ameyer
# Fixed failure to add comments on 3rd worksheet DefinitionText.
#
# Revision 1.4  2007/07/31 14:18:32  ameyer
# Added code to tell Windows to set output to binary mode for Excel97 format.
#
# Revision 1.3  2007/07/27 02:19:13  ameyer
# Added some logging.
# Switched to output in XML (wb.write...False).
#
# Revision 1.2  2007/07/25 03:27:53  ameyer
# This version appears to meet all requirements.
#
# Revision 1.1  2007/06/15 04:04:09  ameyer
# Initial version.  Only two of three worksheets so far implemented.
#
#
#----------------------------------------------------------------------

import sys, cgi, cgitb, time, xml.sax, xml.sax.handler, os, os.path
import cdr, cdrcgi, cdrdb, ExcelWriter

# Global list of head node numbers of blocks of elements with an
#   included ReviewStatus element = 'Problematic'
# See class ProblematicHandler for details.
g_problemBlockSet = None

def logMsg(msg):
    cdr.logwrite(msg, "d:/cdr/Log/drr.log")

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
                            Document handler, providing access to almost
                            everything.
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

#------------------------------------------------------------------
# Track where we are for the parsers
#------------------------------------------------------------------
class PathStack:
    """
    Keeps track of where we are and how we got here (ancestry).
    Maintains several data structures:
        Stack of paths of element names.
        Stack of relative node numbers, where each next node is
            the next number
    """
    def __init__(self):
        """
        Start with empty stacks.
        """
        self.fullPath = []
        self.nextNodeNum = 0
        self.nodeNumStack = []

    def pathPush(self, elemName):
        """
        Add a name to the path.

        Pass:
            elemName - plain element name, no path prefix, no namespace.

        Return:
            Full path as a string.
        """
        # Add to stack of element names
        fullPath = self.pathGet() + '/' + elemName
        self.fullPath.append(fullPath)

        # Add to stack of node numbers
        self.nodeNumStack.append(self.nextNodeNum)
        self.nextNodeNum += 1

        return fullPath

    def pathPop(self):
        """
        Remove an item from the top of the fullPath stack, returning it.
        """
        self.nodeNumStack.pop()
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

    def getNodeNum(self, ancestor):
        """
        Return the node number of an element in the pathStack.

        Pass:
            ancestor - 0 = Get current node's node number
                       1 = Get parent node's number
                       2 = Get grandparent node's number
                       etc.
        Or -1 if None
        """
        numStackLen = len(self.nodeNumStack)
        if numStackLen > ancestor:
            return self.nodeNumStack[numStackLen - (ancestor+1)]
        return -1

class DocHandler(xml.sax.handler.ContentHandler):
    """
    Sax parser content handler for Term documents.
    """
    def __init__(self, docXml, ws, ctlHash, docId, dt, dtCol):
        """
        Content handler constructor.

        Pass:
            docXml  - Reference to the full XML string, used in
                      findProblematicFields function.
            ws      - ExcelWriter.Worksheet, already initialized.
            ctlHash - Dictionary of path -> ColControl for all
                      elements (xpaths) that have some processing.
            docId   - Always written to column 1 of sheet.
            dt      - Create/import date, written to dtCol column.
            dtCol   - Column number, origin 1, for create/import date.
        """
        global g_problemBlockSet

        self.docXml      = docXml
        self.ws          = ws
        self.ctlHash     = ctlHash
        self.docId       = docId
        self.dt          = dt[0:10]
        self.dtCol       = dtCol
        self.pathStack   = None

        # If the global problem block set exists, pre-parse the doc
        #   finding all of the fields with ReviewStatus='Problematic'
        # This will populate the global with a set of nodes of fields
        #   and parents of fields with Problematic ReviewStatus.
        if g_problemBlockSet != None:
            xml.sax.parseString(docXml, ProblematicHandler())

    def startDocument(self):
        """
        Initialization needed for each new document.
        """
        global G_wsRow

        # ColControl we're currently working on, nest them in a stack
        self.colCtls = []
        self.curCtl  = None

        # Stack of full xpaths to current node push at start, pop at end
        self.pathStack = PathStack()

        # Many paths are ignored, curPath has content only if we're
        #   working on one that should not be ignored
        self.curPath = None

        # Text is gathered here in characters() callback
        self.text = ""

        # Tracking count of OtherName elements
        # 2nd and subsequent OtherName element starts a new row
        self.otherNameCount = 0

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
        global g_problemBlockSet

        # Construct full path to this field and maintain path stack
        fullPath = self.pathStack.pathPush(name)

        # Is it of interest?
        if self.ctlHash.has_key(fullPath):
            self.curCtl = self.ctlHash[fullPath]
            self.colCtls.append(self.curCtl)
            self.curPath = fullPath

            # Save attributes
            self.attrs = attrs

        # Here's the hack for adding OtherName rows
        if fullPath == "/Term/OtherName":
            self.otherNameCount += 1
            if self.otherNameCount > 1:
                # And the hack for problematic fields
                nodeNum = self.pathStack.getNodeNum(0)
                if g_problemBlockSet==None or nodeNum in g_problemBlockSet:
                    self.ssRow += 1
                    self.curRow = self.ws.addRow(self.ssRow, dataStyle)

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
            if self.curPath == self.pathStack.pathGet():

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
        self.pathStack.pathPop()

    def endDocument(self):
        """
        Cleanup.
        """
        # Update global row
        global G_wsRow
        G_wsRow = self.ssRow + 1


#----------------------------------------------------------------------
# Pre-parser parser - functions and sax parser
#
# See coments under ProblematicHandler for explanation.
#
# Functions used there are also used in the DocHandler, primary
# parser class.
#----------------------------------------------------------------------
class ProblematicHandler(xml.sax.handler.ContentHandler):
    """
    Another sax parser.

    The third worksheet requires that we only display blocks of
    information of certain types when one of the elements in that
    block, with the name ReviewStatus, has the content 'Problematic'.

    The ReviewStatus elements typically come _after_ the elements
    they control.  So there is a look ahead problem that is easy
    to solve in a dom based solution but not a sax solution.

    Since I made the wrong choice at the beginning - using sax
    instead of the more flexible dom, I've decided to live with it
    and just parse the docs for worksheet 3 twice, once to find out
    which blocks have a ReviewStatus='Problematic' and once to
    do the rest of the processing.  The performance penalty is
    negligible since the number of docs affected is small and their
    size is small.

    Communication is via a global.  The set g_problemBlockSet will
    contain identifying numbers for every block that has a
    ReviewStatus='Problematic".  The numbers are node numbers for
    the head node for the block - managed identically in both parsing
    passes.

    Alas, once you go far enough down the road of a mistake, the
    best choice is sometimes to go farther.
    """
    def startDocument(self):
        # Clear the global set of problematic head nodes
        global g_problemBlockSet
        g_problemBlockSet = set()

        # Stack of full xpaths to current node push at start, pop at end
        # Must work just like DocHandler
        self.pathStack = PathStack()

    def startElement(self, name, attrs):
        # Stack maintenance
        self.pathStack.pathPush(name)

        # New text for this element
        self.text = ''

    def characters(self, content):
        # Cumulate text
        self.text += content

    def endElement(self, name):
        global g_problemBlockSet

        # If we have a problematic review status, save the node number
        #   of the parent of the current node
        if name == 'ReviewStatus':
            if self.text == 'Problematic':
                g_problemBlockSet.add(self.pathStack.getNodeNum(1))

        # Stack maintenance
        self.pathStack.pathPop()

def addCols(sheet, colList):
    """
    Create columns in a worksheet using a sequence of ColControls

    Pass:
        sheet   - Worksheet to add to.
        colList - Sequence of columns
    """
    if None:  # Unused for now
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
        errRow.addCell(2, "NO DOCUMENTS FOUND")

        # We're done with this worksheet
        return

    # Process each document found by the query
    docCount = 0
    for row in rows:
        (docId, docDate) = row

        # Fetch the XML for this ID
        dXml = cdr.getDoc(session, docId)
        docXml = cdr.getCDATA(dXml)
        if not docXml:
            # Found a bad doc in database
            logMsg("DrugReviewReport.py can't get docXml for docId=%d\n%s" \
                         % (docId, dXml))
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
        xml.sax.parseString(docXml, DocHandler(docXml, ws, colHash, docId,
                                               docDate, dateCol))


# Front ends, passing parameters
def chkReviewStatus1(handler):
    return chkReviewStatus(handler, 1)

def chkReviewStatus3(handler):
    return chkReviewStatus(handler, 3)

def chkReviewStatus(handler, ancestor):
    """
    Called when we get a field that is only to be displayed if
    a ReviewStatus in the same block is set to 'Problematic'.

    Checks g_problemBlockSet to see if this node or its parent
    is involved with a problematic review status.  The global
    is set in a pre-pass parse.

    Uses relative node numbers, not element names.  That way we
    can distinguish specific occurrences of fields.

    Pass:
        handler  - DocHandler instance
        ancestor - How far up the tree do we look?

    Returns:
        Contents of field, if problematic
        Null string if field is not problematic
    """
    global g_problemBlockSet

    # Is the current node in the set?
    if handler.pathStack.getNodeNum(ancestor) in g_problemBlockSet:
       return handler.text
    return ""


def addComment(handler):
    """
    Call this function if a comment is received.
    It adds text to an already existing cell in the worksheet.
    """
    # Only add the comment if it has an attribute audience="External"
    #DBG if True:
    if handler.attrs.has_key("audience"):
        if handler.attrs.getValue("audience") == "External":

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
    ColControl("Preferred Name", u"/Term/PreferredName", 2, 105),
    ColControl("Other Names", u"/Term/OtherName/OtherTermName", 3, 105),
    ColControl("Other Name Type", u"/Term/OtherName/OtherNameType", 4, 80),
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

    # Special functions
    ColControl(None, u"/Term/Comment", 2, 105, (addComment,)),
    ColControl(None, u"/Term/OtherName/Comment", 3, 105, (addComment,)),
    ColControl(None, u"/Term/Definition/Comment", 8, 210, (addComment,)),
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
g_problemBlockSet = None
ws = addWorksheet(session, wb, "New Drugs from NCI Thesaurus", wsCols,
                  qry, 9)

#----------------------------------------------------------------------
# Worksheet 2: New drugs from the CDR
#----------------------------------------------------------------------
wsCols = (
    ColControl("CDR ID", None, 1, 45),
    ColControl("Preferred Name", u"/Term/PreferredName", 2, 140),
    ColControl("Other Names", u"/Term/OtherName/OtherTermName", 3, 140),
    ColControl("Other Name Type", u"/Term/OtherName/OtherNameType", 4, 80),
    ColControl("Date Created", None, 5, 65),

    # Special functions
    ColControl(None, u"/Term/Comment", 2, 140, (addComment,)),
    ColControl(None, u"/Term/OtherName/Comment", 3, 140, (addComment,)),
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

g_problemBlockSet = None
ws = addWorksheet(session, wb, "New Drugs from the CDR", wsCols, qry, 5)

#----------------------------------------------------------------------
# Worksheet 3: Drugs to be Reviewed
#----------------------------------------------------------------------
wsCols = (
    ColControl("CDR ID", None, 1, 45),
    ColControl("Preferred Name", u"/Term/PreferredName", 2, 105),
    ColControl("Other Names", u"/Term/OtherName/OtherTermName", 3, 105,
        (chkReviewStatus1,)),
    ColControl("Other Name Type", u"/Term/OtherName/OtherNameType", 4, 80,
        (chkReviewStatus1,)),
    ColControl("Source",
        u"/Term/OtherName/SourceInformation/VocabularySource/SourceCode",
        5, 90, (chkReviewStatus3,)),
    ColControl("TType",
        u"/Term/OtherName/SourceInformation/VocabularySource/SourceTermType",
        6, 70, (chkReviewStatus3,)),
    ColControl("SourceID",
        u"/Term/OtherName/SourceInformation/VocabularySource/SourceTermId",
        7, 45, (chkReviewStatus3,)),
    ColControl("Definition", u"/Term/Definition/DefinitionText", 8, 210,
        (chkReviewStatus1,)),
    ColControl("Date Created", None, 9, 65),

    # Special functions
    ColControl(None, u"/Term/Comment", 2, 105, (addComment,)),
    ColControl(None, u"/Term/OtherName/Comment", 3, 105, (addComment,)),
    ColControl(None, u"/Term/Definition/Comment", 8, 210, (addComment,))
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
   AND (
       q2.path = '/Term/OtherName/ReviewStatus'
      OR
       q2.path = '/Term/Definition/ReviewStatus'
      OR
       q2.path = '/Term/ReviewStatus'
       )
   AND q2.value = 'Problematic'
  AND a.dt > '%s'
  AND a.dt < '%s'
 GROUP BY a.document, a.dt
""" % (drugAgentDocId, startDate, endDate)

g_problemBlockSet = set()
ws = addWorksheet(session, wb, "Drugs to be Reviewed", wsCols, qry, 9)

# DEBUG
#DBG fname = "d:/cdr/log/DrugTerm.xls"
#DBG if os.path.exists(fname):
#DBG     os.remove(fname)
#DBG fp = open(fname, "wb")
#DBG wb.write(fp, False)
#DBG fp.close()
#DBG cdr.logout(session)
#DBG cdrcgi.bail("All done")
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=DrugReviewReport.xls"
print
wb.write(sys.stdout, True)
