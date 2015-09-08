#----------------------------------------------------------------------
# $Id$
#
# Report on the types of changes recorded in selected Summaries.
#
# BZIssue::None  (JIRA::OCECDR-3703)
# OCECDR-3900: Modify the Summaries Type of Change report to display 
#              Spanish CAM summaries
#
#                                           Alan Meyer, March 2014
#----------------------------------------------------------------------
import cgi, time, datetime, lxml.etree as lx, cdr, cdrcgi, cdrdb

# DEBUG
LF = "d:/cdr/log/toc.log"

SCRIPT = "SummaryTypeChangeReport.py"

BANNER    = "CDR Administration"
SUBBANNER = "Summaries Type of Change"
RPTMENU   = "Report Menu"
buttons   = ("Submit", RPTMENU, cdrcgi.MAINMENU)

MIN_DATE  = str(datetime.date(2002, 1, 1))
MAX_DATE  = str(datetime.date.today())

def fatal(msg, log=False):
    """
    Display and optionally log an error message.
    """
    if log:
        logMsg = "Summary ToC Report Error: "
        if type(msg) == type([]):
            msg.insert(0, logMsg)
            cdr.logwrite(msg)
        else:
            cdr.logwrite("%s%s" % (logMsg, msg))

    # bail() allows "extras" for sequences
    if type(msg) == type([]):
        cdrcgi.bail(msg[0], extra=msg[1:])
    cdrcgi.bail(msg)

def tableSpacer(table, page):
    """
    Put some space before or after a table.
    """
    page.add_css("table { margin-top: 25px; }")

class DocChanges:
    """
    All of the information about changes made to one Summary document.
    """
    def __init__(self, docId, docTitle, changes=None):

        """
        Encapsulate all info for one document.

        Pass:
            docId    - CDR document ID.
            docTitle - Title of doc from the document table.
            changes  - If non-empty, it's a list of the type that
                       would be created by one or more calls to
                       self.addChange().
        """
        self.docId    = docId
        self.docTitle = docTitle

        # Python alert:
        #  If changes has default changes=[]
        #    [] turns out to be a single list object that has the same
        #    value as the last time it was updated - causing a bug.
        #  Hence we use None instead of [] to get a default of [].
        # How wierd is that?
        if changes is None:
            self.changes = []
        else:
            self.changes = changes

    def addChange(self, typeOfChange, date, comment):
        """
        Add one type of change element to the object.

        Pass:
            typeOfChange - Schema defined string for the type of change, e.g.,
                           "Comprehensive revision".
            date         - ISO format date of revision.
            comment      - Catenation of all comment strings for this change,
                           or None if no comments.
        """
        self.changes.append([typeOfChange, date, comment])

    def showHtml(self):
        """
        HTML format change object, as unicode.
        """
        strings = []
        strings.append(u"%s: %s" %
                       (cdr.exNormalize(self.docId)[0], self.docTitle))
        for chg in self.changes:
            # Date: Type of change /n comments
            strings.append(u" -- %s: %s" % (chg[1], chg[0]))
            strings.append(u" &nbsp; &nbsp; %s" % chg[2])

        display = u'<br />\n'.join(strings)

        return display

    def showText(self):
        """
        Text format change object, as utf-8.
        """
        strings = []
        utxt = u"%s: %s" % (cdr.exNormalize(self.docId)[0], self.docTitle)
        strings.append(utxt.encode('ascii', 'replace'))
        for chg in self.changes:
            # Date: Type of change /n comments
            strings.append(" -- %s: %s %s" % (chg[1], chg[0], chg[2]))

        return "\n".join(strings)

class TOCConfig:
    """
    Holds all configuration parameters.
    """
    def __init__(self, fields):

        if not fields:
            fatal("Unable to load form fields", True)
        self.session   = cdrcgi.getSession(fields)
        self.request   = cdrcgi.getRequest(fields)

        # Abort and navigate away if so requested
        if self.request == RPTMENU:
            cdrcgi.navigateTo("Reports.py", self.session)
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", self.session)

        self.fields    = fields
        self.repType   = fields.getvalue("repTypeA")
        self.oFormat   = fields.getvalue("oFormat")
        self.spcCdrId  = fields.getvalue("byCdrid")
        self.spcTitle  = fields.getvalue("byTitle")
        self.audience  = fields.getvalue("audience")
        self.language  = fields.getvalue("language")
        self.startDate = fields.getvalue("startDate", MIN_DATE)
        self.endDate   = fields.getvalue("endDate", MAX_DATE)
        self.sortOrder = fields.getvalue("sortOrder")

        # Determine report type from checkbox
        if not self.repType:
            self.repType = 'basic'

        # Dates must be present and valid
        if not cdr.valFromToDates('%Y-%m-%d', self.startDate, self.endDate,
                                  MIN_DATE, MAX_DATE):
            cdrcgi.bail(
                "Start/End dates must be in valid YYYY-MM-DD format, in "
                "range between start of CDR (2002-01-01) and today")

        # Human readable forms of start and end date
        self.startShowDate = self.startDate
        if self.startDate == MIN_DATE:
            self.startShowDate = 'Beginning'
        self.endShowDate = self.endDate
        if self.endDate == MAX_DATE:
            self.endShowDate = time.strftime('%Y-%m-%d')

        # Language is a required field.  If not there we haven't been
        #  through the input form yet and can't get other info
        if not self.language:
            return

        # Boards, types of change
        self.boards = self.getSelectedBoards()
        self.requestedTypes = self.getSelectedTypesOfChange()

        # Are there any comments in the output report?
        self.hasComments = False
        for key, val in self.requestedTypes.items():
            if val:
                self.hasComments = True

        self.sortedTypes = sorted(self.requestedTypes.keys())

        # Validate
        if not self.boards:
            fatal("Must select at least one Board for selected language")
        if not self.sortedTypes:
            fatal("Must select at least one Type of Change for report")

    def getSelectedBoards(self):
        """
        Get all of the boards selected on an input form.

        Pass:
            Output of cgi.FieldStorage().

        Return:
            Array of full board names for English or Spanish.
            'all' if all boards selected.
            [] if nothing checked.
        """
        # Want all boards?
        if self.language in self.fields.getlist('alllang'):
            return 'all'

        # Not all, search for them
        if self.language == 'English':
            boardList = EnglishBoards
            inputId   = 'enboard'
        else:
            boardList = SpanishBoards
            inputId   = 'esboard'

        # All the checked boards
        boardsChecked = self.fields.getlist('boardId')
        if not boardsChecked:
            return None

        # Use checkbox values to lookup list values
        boardsFound = []
        for chk in boardsChecked:
            # Extract number from 'enboard2', 'esboard0', etc.
            # Get corresponding full board name
            if chk[:7] == inputId:
                idx = int(chk[7:])
                boardsFound.append(boardList[idx][1])

        # Return whatever we got.  May be an empty set
        return boardsFound

    def getSelectedTypesOfChange(self):
        """
        Get the types of changes desired in the report.

        Return:
            Dictionary of requested change types:
                Key = Type of change string, one of the types found in the
                      docs in the database.
                Val = True  = Include comments
                      False = No comments
        """
        # Check for all types, all comments, if so, no more to do
        if self.fields.getvalue('allTcCm'):
            return self.getAllTypesOfChange()

        # Insert the info to return here
        typeDict = {}

        # Get the exact same list of types used in the input form
        typesOfChange = cdr.getSchemaEnumVals('SummarySchema.xml',
                                              'SummaryChangeType')

        # Extract TOCs from the form and see if corresponding comments checked
        typs  = self.fields.getlist('typ')
        cmnts = self.fields.getlist('cmt')
        for typ in typs:
            # Looking for "typ0", "typ1" ... "cmt0" ...
            typIdx = int(typ[3:])
            typName = typesOfChange[typIdx]
            cmtName = "cmt%d" % typIdx
            includeCmts = False
            if cmtName in cmnts:
                includeCmts = True
            typeDict[typName] = includeCmts

        # Return results, may be empty
        return typeDict

    def getAllTypesOfChange(self):
        """
        Get all possible types of change - used for advanced report.

        Return:
            Dictionary of requested change types:
                Key = Type of change string, one of the types found in the
                      docs in the database.
                Val = True  = Include comments
                      False = No comments
        """
        # Insert the info to return here
        typeDict = {}

        # Get the exact same list of types used in the input form
        typesOfChange = cdr.getSchemaEnumVals('SummarySchema.xml',
                                              'SummaryChangeType')

        for toc in typesOfChange:
            typeDict[toc] = True

        return typeDict

    def assembleResults(self):
        """
        Put all of the results from the Summary docs into a data structure
        that has everything needed to drive the display of the report.

        Return:
            List of DocChanges objects in the order produce by the query
            produced in response to the input parameters.
        """

        results = []

        # Basic report gets latest change, else use start/end dates
        if self.repType == 'basic':
            # Force use of latest date, ignoring start/end dates
            latest    = True
            startDate = MIN_DATE
            endDate   = MAX_DATE
        else:
            latest    = False
            startDate = self.startDate
            endDate   = self.endDate

        # If all boards requested, use [] for getSummaryIds()
        boards = self.boards
        if boards == 'all':
            boards = []

        # Get the doc IDs and titles for all qualified docs
        if self.spcCdrId or self.spcTitle:
            idTitles = self.getIdentifiedDocs()
        else:
            idTitles = cdr.getSummaryIds(self.language, self.audience, boards,
                                         status='A', published=True,
                                         titles=True, sortby='title')

        try:
            conn = cdrdb.connect('CdrGuest')
            cursor = conn.cursor()
        except cdrdb.Error, info:
            fatal("Unable to connect to the database to read XML: %s" \
                         % str(info), True)

        # Produce an object for each doc
        for pair in idTitles:
            docId, docTitle = pair
            docChg = DocChanges(docId, docTitle)

            # Parse the doc to find changes
            extractTOC(cursor, docChg, self.requestedTypes,
                       startDate, endDate, latest)
            results.append(docChg)

        return results

    def getIdentifiedDocs(self):
        """
        Get the id and title for doc(s) specified by ID(s) or title.

        Allows multiple IDs as space separated strings, e.g.:
            "1234 5678" or "CDR0000001234 cdr0000005678".

        Only one title allowed and it is only checked if no IDs have been
        specified.  If title has two hits, one HP and one Patient, use
        self.audience to disambiguate.

        Return:
            Sequence of [[id, title], ...]
            Bail if not found or no found ID is not a Summary.
            (Silently ignoring case where one is not found but another is.)
        """
        if self.spcCdrId:
            # Get a sequence of normalized doc IDs
            rawIds = self.spcCdrId.split()
            docIds = []
            for raw in rawIds:
                try:
                    cooked = cdr.exNormalize(raw)[1]
                except cdr.Exception as e:
                    fatal(str(e))
                docIds.append(cooked)

            # Search for them
            qry = cdrdb.Query('document d', 'd.id', 'd.title')
            qry.join('doc_type t', 'd.doc_type = t.id')
            qry.where(qry.Condition('d.id', docIds, 'IN'))
            qry.where(qry.Condition('t.name', 'Summary'))
            qry.order('d.id')

            cursor = qry.execute()
            idTitles = cursor.fetchall()
            cursor.close()

            if not idTitles:
                fatal('No Summaries found with CDR-ID(s): "%s"' %
                       self.spcCdrId)

        else:
            # Search for title as leading substring
            titleLead = self.spcTitle + '%'
            qry = cdrdb.Query('document d', 'd.id', 'd.title')
            qry.join('doc_type t', 'd.doc_type = t.id')
            qry.join('query_term q', 'd.id = q.doc_id')
            qry.where(qry.Condition('d.title', titleLead, 'LIKE'))
            qry.where(qry.Condition('d.active_status', 'A'))
            qry.where(qry.Condition('t.name', 'Summary'))
            qry.where(qry.Condition('q.path',
                                   '/Summary/SummaryMetaData/SummaryAudience'))
            qry.where(qry.Condition('q.value', self.audience))
            qry.order('d.id')

            cursor = qry.execute()
            idTitles = cursor.fetchall()
            cursor.close()

            # Must be exactly one
            if len(idTitles) == 0:
                fatal('No Summary found with leading title chars: "%s"'
                       % self.spcTitle)
            if len(idTitles) > 1:
                msg    = [u"Multiple Summaries match title lead:",]
                count  = 0
                maxCnt = 10
                for docId, docTitle in idTitles:
                    msg.append(" %d: %s" % (docId, docTitle))
                    count += 1
                    if count > maxCnt:
                        msg.append("Stopped after %d titles" % count)
                fatal(msg)

        return idTitles

    def sortResultsByTOC(self, results):
        """
        Sort a list of DocChanges objects by TypeOfChange.
        Produces a new list in which one document may appear multiple
        times, once for each TypeOfChange.

        Old format:
            One DocChanges object per Summary.
            Each contains all changes to report for that Summary.

        New format:
            One DocChanges object per Summary per type of change.
            Each contains all changes of one type for that Summary.
              If there is no change of that type, then no DocChanges object.

        Pass:
            results - list produced by self.assembleResults().

        Return:
            New results list, reorganized as above, with all DocChanges
            objects ordered alphabetically by type of change, then by Summary.

        """
        # Create a list for each type of change
        tocDocs = {}
        for toc in self.sortedTypes:
            tocDocs[toc] = []

        # Walk through the results, assigning changes to divided lists
        for docChg in results:
            for chg in docChg.changes:
                toc     = chg[0]
                docList = tocDocs[toc]
                newChg  = DocChanges(docChg.docId, docChg.docTitle)
                newChg.addChange(chg[0], chg[1], chg[2])
                docList.append(newChg)

        # Consolidate all of the lists into one, alpha ordered by type
        newResults = []
        for toc in self.sortedTypes:
            newResults.extend(tocDocs[toc])

        return newResults


class OutputReport:
    """
    Construct a report to send to user.
    """
    def __init__(self, config, results):
        """
        Constructor.

        Actually produces the entire report.

        Pass:
            config  - TOCConfig object with all report parms.
            results - Sequence of DocChanges objects, produced by
                      assembleResults().
        """
        self.cfg = config

        # Get count of documents now, sortResultsByTOC will change results len
        self.docCount = len(results)

        # Create columns with count and type of change ordered list
        self.cols     = self.createColumns()
        self.colCount = len(self.cols)

        # Cumulate tables:
        #  Basic has one table
        #  Advanced may have one for each type of change
        tables = []

        # Data for one table cumulated here
        rows      = []
        totalRows = 0

        # Fill in all the data for each column
        if self.cfg.repType == 'basic' or \
           self.cfg.sortOrder == 'orderBySummary':

            # Create all rows in the report
            for sumChg in results:
                newRows = self.createRows(sumChg)
                if newRows:
                    totalRows += len(newRows)
                    rows.extend(newRows)

            # Set title
            if self.cfg.repType == 'basic':
                caption = 'Type of Change Report (Most Recent Change)'
            else:
                caption = ['Type of Change Report (All Changes by Summary)',
                 '%s - %s' % (self.cfg.startShowDate, self.cfg.endShowDate)]

            # Create the one and only table
            options = {'banner': BANNER, 'subtitle': SUBBANNER,
                       'caption': caption}
            tables.append(cdrcgi.Report.Table(self.cols, rows, **options))

        # Advanced report sorted by type of change
        else:
            results     = self.cfg.sortResultsByTOC(results)
            lastTocType = None

            for sumChg in results:
                if not sumChg.changes:
                    # No blank lines in this report
                    # None should be produced by the sorting, but maybe later
                    # XXX Not sure that's true but we'll do it for now
                    # XXX sortResultsBy... may already have removed empties
                    continue
                chg     = sumChg.changes[0]
                tocType = chg[0]

                # Starting a new type of change?
                if tocType != lastTocType:
                    # Finish any old one
                    if rows:
                        # Create a table for completed type of change
                        tables.append(self.makeTocTable(lastTocType,
                                                        self.cols, rows))
                        totalRows += len(rows)
                        rows = []
                rows.extend(self.createRows(sumChg))
                lastTocType = tocType

            # Create table for last tocType
            if rows:
                totalRows += len(rows)
                tables.append(self.makeTocTable(lastTocType, self.cols, rows))

        # If there weren't any rows, tell user
        if totalRows == 0:
            fatal("%d Summaries examined.  "
                  "No changes found, or none matching report criteria"
                   % self.docCount)

        # Save it all in the object for output
        self.tables = tables

    def makeTocTable(self, tocType, cols, rows):
        """
        Create and populate a cdrcgi.Report.Table object with data
        for a particular type of change.

        Helper for OutputReport constructor.

        Pass:
            tocType - Type of change string.
            cols    - Sequence of column objects.
            rows    - Sequence of table rows, each a sequence of cell values.

        Return:
            Populated object.
        """
        plural_s = ''
        if len(rows) > 1:
            plural_s = 's'
        caption   = ["Type of Change Report", tocType,
                 '%s - %s: (%d change%s)'
                 % (self.cfg.startShowDate, self.cfg.endShowDate,
                    len(rows), plural_s)]

        # Use first word of the type of change as a worksheet name
        words     = tocType.split()
        sheetName = words[0]

        # Create and return the new table
        return cdrcgi.Report.Table(cols, rows, caption=caption,
                       sheet_name=sheetName, html_callback_pre=tableSpacer)

    def createColumns(self):
        """
        Create a sequence of column definitions for the output report.
        Number and types of columns depend on config parms.

        Return:
            Sequence of column definitions to add to object.
        """
        columns = []

        # Leftmost column is always a doc title and ID
        columns.append(cdrcgi.Report.Column('Summary', width='220px'))

        # Basic reports need cols for types of change and comments
        if self.cfg.repType == 'basic':
            tocKeys = sorted(self.cfg.requestedTypes.keys())
            for toc in tocKeys:
                columns.append(cdrcgi.Report.Column(toc, width='105px'))
                if self.cfg.requestedTypes[toc]:
                    columns.append(cdrcgi.Report.Column('Comment',
                                                         width='150px'))

        # Advanced reports
        else:
            if self.cfg.sortOrder == 'orderBySummary':
                # Need a column for type of change
                columns.append(
                    cdrcgi.Report.Column('Type of Change', width='150px'))
            columns.append(cdrcgi.Report.Column('Date', width='80px'))
            if self.cfg.hasComments:
                columns.append(cdrcgi.Report.Column('Comment', width='180px'))

        return columns

    def createRows(self, sumChg, noTitle=False):
        """
        Create one or more rows to represent a single Summary in the report.

        Based on the requirements recorded in the JIRA issue OCECDR-3703:

            The basic report will always and only have one row per Summary.
                If there is no data, all values in row are empty except the
                 document title (id).
            The advanced report will have:
                No rows for a doc with no changes.
                One row per change in a doc with multiple changes.

        Pass:
            sumChg  - DocChanges object for this specific Summary.
                      For one flavor of the advanced report there may be
                       multiple DocChanges object passed (in different calls)
                       for one Summary.
            noTitle - Don't show a title, this is a continuation of the title
                       on the previous row.

        Return:
            Zero or more rows for passed DocChanges object.
        """
        # DEBUG
        # debugRowCnt = 0

        # Representation of an empty cell
        EMPTY = ''

        # List of rows
        rows = []

        # One row
        row  = []

        # All reports start with a summary ID
        if noTitle:
            row.append(EMPTY)
        else:
            row.append(self.makeTitle(sumChg))

        # Basic report
        if self.cfg.repType == 'basic':
            if len(sumChg.changes) == 0:
                # No changes in this Summary, set blank row
                i = 1
                while i < self.colCount:
                    row.append(EMPTY)
                    i += 1
            else:
                # Don't add the same type of change twice
                seenTocs = set()

                # In case we need to produce multiple rows for one doc
                nextRowChg = DocChanges(sumChg.docId, sumChg.docTitle)

                # Process changes in sorted order.  Col headers done that way
                for key in self.cfg.sortedTypes:
                    for chg in sumChg.changes:
                        if chg[0] == key:
                            # If type of chg already reported, set this aside
                            if key in seenTocs:
                                nextRowChg.addChange(chg[0], chg[1], chg[2])
                                continue

                            seenTocs.add(key)
                            row.append(chg[1])
                            if self.cfg.requestedTypes[key]:
                                row.append(chg[2] if chg[2] else EMPTY)

                    # If we haven't seen this type of chg, provide empty cells
                    if key not in seenTocs:
                        row.append(EMPTY)
                        if self.cfg.requestedTypes[key]:
                            row.append(EMPTY)

                # Add the one and only row to the returned sequence of rows
                rows.append(row)

                # Were any additional rows required?
                if len(nextRowChg.changes) > 0:
                    rows.extend(self.createRows(nextRowChg, True))

        # Advanced report
        else:
            # No blank rows in this report - XXX Maybe not?
            if len(sumChg.changes) == 0:
                # Return empty result
                return rows

            # If ordered by Summary
            if self.cfg.sortOrder == 'orderBySummary':
                haveTitle = True
                for chg in sumChg.changes:
                    # Only show title once
                    if not haveTitle:
                        row.append(EMPTY)
                    haveTitle = False

                    # Type of change, date, comment
                    row.append(chg[0])
                    row.append(chg[1])
                    if self.cfg.hasComments:
                        if chg[2]:
                            row.append(chg[2])
                        else:
                            row.append(EMPTY)

                    rows.append(row)
                    row = []

            # Else by type of change
            else:
                # For this report, each DocChanges has exactly one change
                #  (see TOCConfig.sortResultsByTOC())
                for chg in sumChg.changes:
                    row.append(chg[1])
                    if self.cfg.hasComments:
                        if chg[2]:
                            row.append(chg[2])
                        else:
                            row.append(EMPTY)
                    rows.append(row)

        # Return zero or more rows
        return rows

    def makeTitle(self, sumChg):
        """
        Construct a title.  Helper function for createRows().

        Pass:
            sumChg - DocChanges object.

        Return:
            Unicode string representing a Summary.
        """
        # Strip unneded info from the title
        title   = sumChg.docTitle
        tailPos = title.find(';')
        if tailPos > 0:
            title = title[:tailPos]

        return (u"%s (%d)" % (title, sumChg.docId))

def createBoardLists():
    """
    Populate two global variables:
        EnglishBoards
        SpanishBoards

    Structure created for each is a list, in alpha order, of:
        Short board name, Full board name, Board organization CDR ID
    """
    # Search database for names
    global EnglishBoards, SpanishBoards

    boardDict = cdr.getBoardNames('editorial', 'short')

    # Invert dict (to val[key]), removing " Editorial Board"
    boardVdict = {}
    for key, val in boardDict.items():
        # Kludges to get name users want
        val2 = val.replace(' Editorial Board', '')
        if val2.startswith('Cancer Complementary'):
            val2 = val2.replace('Cancer ', '')
        boardVdict[val2] = key

    for key in sorted(boardVdict.keys()):
        pair = (key, boardVdict[key])
        EnglishBoards.append(pair)
        ### if key not in ('Cancer Genetics',
        ###                'Complementary and Alternative Medicine'):
        if key not in ('Cancer Genetics'):
            SpanishBoards.append(pair)

def createBoardsMenu():
    """
    Create an input form for selecting boards for English and Spanish.

    Return:
        Block of HTML for inclusion in the input parameter form.
    """
    html  = createBoardMenu('English')
    html += createBoardMenu('Spanish')
    html += """
     </td>
    </tr>
   </table>
   </fieldset>
"""
    return html

def createBoardMenu(language):
    """
    Create an input form for selecting boards for one language.
    Subroutine of createBoardsMenu().

    Pass:
        language - 'English' or 'Spanish' (no checking done)

    Return:
        Block of HTML for inclusion in the input parameter form.
    """
    # Header for the section
    if language == 'English':
        boardList = EnglishBoards
        checked   = ' checked'
        inputId   = 'enboard'
        allLang   = 'allEnglish'
    else:
        boardList = SpanishBoards
        checked   = ''
        inputId   = 'esboard'
        allLang   = 'allSpanish'
    html = """
    <tr>
     <td width=100>
      <label><input name='language' type='radio' value='%s' %s />%s</label>
     </td>
     <td valign='top'>
      Select PDQ Summaries: (one or more)
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <label><input type='checkbox' name='alllang' id='%s' value='%s'
              onclick="javascript:uncheckMultiBox('%s')" %s />All %s
      </label><br>
""" % (language, checked, language, allLang, language,
       inputId, checked, language)

    # Selection for editorial boards
    idx = 0
    for row in boardList:
        html += """
      <label><input type='checkbox' name='boardId' value='%s%d' id='%s%d'
              onclick="javascript:checkIt('%s', false)" />All %s</label>
      <br />
""" % (inputId, idx, inputId, idx, allLang, row[0])
        idx += 1

    # Rest of the section
    html += """
     </td>
    </tr>
"""
    return html

def createAdvancedMenu():
    """
    Create the part of the report used for filling in parameters for
    an advanced report.

    Return;
        Block of HTML for inclusion in the input parameter form.
    """
    html = """
    <div class='advanced'>
     <b>Type of Change History Report</b>
      <br />
      <br />
      &nbsp;<label class='legend'><input type='checkbox' name='repTypeA'
             value='advanced'> Show Type of Change History</input></label>
      <br />
     <fieldset>
      <legend>&nbsp;Date Limits for Changes&nbsp;</legend>
      <label for='startDate'> Start date </label>
      <input type='text' name='startDate' id='startDate' value='%s'
            class='CdrDateField' size=10 />
      <label for='endDate'> &nbsp; &nbsp; &nbsp; End date </label>
      <input type='text' name='endDate' id='endDate' value='%s'
            class='CdrDateField' size=10 />
     </fieldset>

     <fieldset>
      <legend>&nbsp;Organization of Results&nbsp;</legend>

      <input type='radio' name='sortOrder' id='orderBySummary'
             value='orderBySummary' checked='checked' />
      <label for='orderBySummary'>By Summary &nbsp; &nbsp; </label>

      <input type='radio' name='sortOrder' id='orderByType'
             value='orderByType' />
      <label for='orderByType'>By Type of Change</label>
     </fieldset>
    </div>
""" % (MIN_DATE, MAX_DATE)

    return html

def createInputForm(session):
    """
    Create an input form for the user to enter report parameters.

    Users asked to use the same form as in SummariesTocReport.py.  This
    form is copied and modified from that script.  (Making a common form
    would be possible, but less flexible.)

    Pass:
        Active session ID.

    Return:
        Form HTML.
    """
    header = cdrcgi.header(BANNER, BANNER, SUBBANNER, SCRIPT,
                           buttons, stylesheet = """
   <LINK type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css' />
   <SCRIPT type='text/javascript' language='JavaScript'
            src='/js/CdrCalendar.js'></SCRIPT>
   <STYLE type="text/css">
    TD      { font-size:  12pt; }
    LI.none { list-style-type: none }
    DL      { margin-left: 0; padding-left: 0 }
    fieldset.singletoc label { width: 80px; float: left; }
    .instructions { font: 12pt "Arial"; }
    .legend { font-weight: bold; color: teal; font-family: sans-serif; }
    div     { margin-left: 100px;
              margin-right: 100px;
              display: block;
              font: 12pt "Arial";
              border: 2px solid white;
              margin-top: 20px;
              margin-bottom: 20px;
              padding: 5px;
              background: #CCCCCC; }
    div.head{ border: none;
              margin-top: 0;
              background: transparent; }
    fieldset {
        margin: 10px;
        width: auto; }
   </STYLE>

   <SCRIPT type="text/javascript" lang="JavaScript">
    function checkIt(boxId, checked) {
        var chkVal = '';
        if (checked)
            chkVal = "checked";
        var elem = document.getElementById(boxId)
        if (elem) {
            elem.checked = chkVal;
            return true;
        }
        return false;
    }

    // Uncheck ids beginning enboard, esboard, typ, cmt, as requested
    function uncheckMultiBox(prefix) {
        var i=0;
        while (true) {
            var boardId = prefix + i;
            if (!checkIt(boardId, false))
                break;
            ++i;
        }
    }

    // Uncheck specific change types and comments
    function uncheckTypes() {
        uncheckMultiBox('toc');
        uncheckMultiBox('cmt');
    }

    </SCRIPT>

"""                           )
    form   = """\
   <input type='hidden' name='%s' value='%s'>
   <input type='hidden' name='singletoc' value='N'>
<div class='head'>
<p>The basic form of this report displays the most recent change information
for each of the selected Summaries.</p>

<p>To see earlier changes, scroll down, check the box marked
"Show Type of Change History", and enter any Date Limits and Organization
Of Results choices.</p>
</div>

   <div>
    <b>Type of Change Report</b>
    <fieldset class='radio'>
     <legend>&nbsp;Format&nbsp;</legend>

     <input class='radio' type='radio' name='oFormat' id='fmtHtml'
            value='html' checked='checked' />
     <label class='radio' for='orderBySummary'>Web Page &nbsp; &nbsp; </label>

     <input class='radio' type='radio' name='oFormat' id='fmtExcel'
            value='excel' />
     <label class='radio' for='oFormat'>Excel Workbook</label>
    </fieldset>
    <fieldset>
     <legend>&nbsp;Audience&nbsp;</legend>
     <label>
     <input name='audience' type='radio' value='Health Professionals'
         checked='checked' />
     Health Professionals &nbsp; &nbsp;
     </label>
     <label><input name='audience' type='radio' value='Patients' />Patients</label>
    </fieldset>

   <fieldset class='singletoc'>
    <legend>&nbsp;For Specific Summaries - CDR-ID or Document Title&nbsp;</legend>
    <label for="byCdrid">CDR-ID(s)</label>
    <input name='byCdrid' size='50' id="byCdrid">
    <br />
    <label for="byTitle">Title</label>
    <input name='byTitle' size='50' id='byTitle'>
   </fieldset>

   <fieldset>
    <legend>&nbsp;For Multiple Summaries - Summary Language and Summary Type&nbsp;</legend>
   <table border = '0'>
    <tr>
""" % (cdrcgi.SESSION, session)

    form += createBoardsMenu()

    # Add checkboxes for types of change and comments
    typesOfChange = cdr.getSchemaEnumVals('SummarySchema.xml',
                                          'SummaryChangeType')

    tocHtml = """
   <fieldset>
    <legend>
      &nbsp;Change types + comments &nbsp;
    </legend>
   <table border = '0'>
     <tr>
      <td colspan='2'><input type='checkbox' name='allTcCm' value='allTcCm'
          onclick="javascript:uncheckTypes()" id='allTcCm' checked='checked'
       >All types and all comments (or select below)</td>
     </tr>
"""
    for i in range(len(typesOfChange)):
        tocHtml += """
     <tr>
      <td><input type='checkbox' name='typ' value='toc%d' id='toc%d'
              onclick="javascript:checkIt('allTcCm', false)"
           >%s</td>
      <td><input type='checkbox' name='cmt' value='cmt%d' id='cmt%d'
           >Comments</td>
     </tr>
""" % (i, i, typesOfChange[i], i, i)

    tocHtml += """
    </table>
   </fieldset>
   </div>
"""
    form += tocHtml

    form += createAdvancedMenu()

    form += """
  </form>
 </body>
</html>
"""
    return header + form

def extractTOC(cursor, docChg, requestedTypes,
               startDate=MIN_DATE, endDate=MAX_DATE, latest=True):
    """
    For the docChg.docId, find the doc, extract the requested types of
    change if they exist.  Return the results.

    The rules for selecting data to return are:
        Get info for the type of change on the latest date.
        If more than one type of change occurred on the same date:
            If they are different types:
                Return both.
            Else:
                Return just the last one encountered.

    Pass:
        cursor         - Open cursor to the database.
        docChg         - DocChanges object to receive the results.
        requestedTypes - Dictionary of requested types to fetch:
                           Key = Type name, e.g., "Comprehensive revision".
                           Val = True = Include comments.
                                 False = Do not include comments.
        startDate      - Only get changes >= this date.
        endDate        - Only get changes <= this date.
        latest         - True  = Just find the latest change meeting criteria.
                         False = Find all changes meeting criteria.

    Return:
        Void.  The passed docChg object has the changes installed.
               Note that there may not be any actual changes.
    """
    docId = docChg.docId

    # Get the XML
    try:
        cursor.execute("SELECT xml FROM document WHERE id=%d" % docId)
        row = cursor.fetchone()
    except cdrdb.Error as e:
        fatal("DB Error fetching docId=%d: %s" % (docId, str(e)))
    if not row:
        fatal("No XML found for docId=%d, can't happen!" % docId)
    xml = row[0]

    # Extract type of change data
    tree = lx.fromstring(xml.encode('utf-8'))
    changes = tree.findall('TypeOfSummaryChange')

    # If only want the latest change(s).  Find the date of latest change
    latestDate = ''
    if latest:
        for sumChg in changes:
            dateChg = sumChg.find('Date')
            dateTxt = dateChg.text
            if dateTxt > latestDate:
                latestDate = dateTxt

    # Find results, if any
    for sumChg in changes:
        typeChg = sumChg.find('TypeOfSummaryChangeValue')
        typeTxt = typeChg.text

        # Ignored type?
        if not requestedTypes.has_key(typeTxt):
            continue

        # Latest date?  Date is required, but just in case
        dateChg = sumChg.find('Date')
        if dateChg is not None:
            dateTxt = dateChg.text
            if latest and dateTxt < latestDate:
                continue

            # Date range?
            if dateTxt < startDate or dateTxt > endDate:
                continue

        # Comments
        comments = ''
        if requestedTypes[typeTxt] == True:
            commentChanges = sumChg.findall('Comment')
            separator = ''
            for cmtChg in commentChanges:
                comments = separator + cmtChg.text
                separator = ' / '

        # If we got here, we have data, output it
        docChg.addChange(typeTxt, dateTxt, comments)

    return

#----------------------------------------------------------------------
# MAIN
#----------------------------------------------------------------------
# Populate board lists
EnglishBoards = []
SpanishBoards = []

createBoardLists()

# Extract variables from the form
cfg = TOCConfig(cgi.FieldStorage())

# If starting fresh, put up the report parameter input form
# Language must be present if we've had a round trip
if not cfg.language:
    html = createInputForm(cfg.session)
    cdrcgi.sendPage(html)

# Get all results in a list of DocChanges objects
results = cfg.assembleResults()

# Create the report
if results:
    outputRpt = OutputReport(cfg, results)
else:
    fatal("No changes found by specified parameters")

# Setup banner fields
subTitle = time.strftime('Report produced: %A %B %d, %Y %I:%M %p')
if cfg.repType == 'basic':
    rType    = 'Basic'
else:
    rType = 'Advanced'
    if cfg.startDate == MIN_DATE:
        startDate = 'Beginning'
    else:
        startDate = cfg.startDate
    if cfg.endDate == MAX_DATE:
        endDate = 'Current date'
    else:
        endDate = cfg.endDate
    subTitle += ' -- %s to %s' % (startDate, endDate)
title = "Summary Type of Change Report - %s" % rType

options   = {'banner': title, 'subtitle': subTitle}
report = cdrcgi.Report('Summary Type of Change Report', outputRpt.tables,
                        **options)

# Display
if cfg.oFormat == 'html':
    report.send('html')
else:
    report.send('excel')

# DEBUG - SHOW THE RESULTS - CAN'T GET HERE IF SUCCESSFUL
chgList = []
for chg in results:
    chgList.append(chg.showHtml())
header = cdrcgi.header(BANNER, BANNER, SUBBANNER, SCRIPT, buttons)
html = header + u"<br /><br />\n".join(chgList) + u"</form></body></html>"
cdrcgi.sendPage(html)

cdrcgi.bail("Got to the end")
