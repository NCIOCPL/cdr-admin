#----------------------------------------------------------------------
# $Id: SummaryTypeChangeReport.py 12622 2014-04-29 19:38:24Z bkline $
#
# Report on the types of changes recorded in selected Summaries.
#
# BZIssue::None  (JIRA::OCECDR-3703)
#
#                                           Alan Meyer, March 2014
#----------------------------------------------------------------------
import cgi, time, datetime, lxml.etree as lx, cdr, cdrcgi, cdrdb

# DEBUG
LOG = "d:/cdr/log/SectionCleanup.log"

SCRIPT = "SummarySectionCleanup.py"

BANNER    = "CDR Administration"
SUBBANNER = "Summary Section Cleanup"
RPTMENU   = "Report Menu"
buttons   = ("Submit", RPTMENU, cdrcgi.MAINMENU)

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
        self.changes  = []


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
    def __init__(self):

        ###if not fields:
        ###    fatal("Unable to load form fields", True)
        fields = cgi.FieldStorage()
        self.session   = cdrcgi.getSession(fields)
        self.request   = cdrcgi.getRequest(fields)

        # Abort and navigate away if so requested
        if self.request == RPTMENU:
            cdrcgi.navigateTo("Reports.py", self.session)
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", self.session)

        self.fields    = fields
        self.repType   = 'basic'
        self.oFormat   = fields.getvalue("oFormat")
        self.spcCdrId  = fields.getvalue("byCdrid") #or 668479
        self.spcTitle  = fields.getvalue("byTitle")
        self.audience  = fields.getvalue("audience")
        self.language  = fields.getvalue("language")
        self.sortOrder = 'orderBySummary'

        # Language is a required field.  If not there we haven't been
        #  through the input form yet and can't get other info
        if not self.language:
            return

        # Boards
        self.boards = self.getSelectedBoards()

        # Validate
        if not self.boards:
            fatal("Must select at least one Board for selected language")

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

    def assembleResults(self):
        """
        Put all of the results from the Summary docs into a data structure
        that has everything needed to drive the display of the report.

        Return:
            List of DocChanges objects in the order produce by the query
            produced in response to the input parameters.
        """

        results = []

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
            extractTOC(cursor, docChg)
            #Only list documents with problem sections
            if docChg.changes:
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
        tables = []

        # Data for one table cumulated here
        rows      = []
        totalRows = 0

        # Fill in all the data for each column
        # Create all rows in the report
        for sumChg in results:
            newRows = self.createRows(sumChg)
            totalRows += 1
            rows.append(newRows)

        # Set title
        caption = 'SummarySection Cleanup Report'
        # Create the one and only table
        options = {'banner': BANNER, 'subtitle': SUBBANNER,
                   'caption': caption}
        #cdrcgi.bail("%s" % rows)
        tables.append(cdrcgi.Report.Table(self.cols, rows, **options))

        # If there weren't any rows, tell user
        if totalRows == 0:
            fatal("%d Summaries examined.  "
                  "No changes found, or none matching report criteria"
                   % self.docCount)

        # Save it all in the object for output
        self.tables = tables


    def createColumns(self):
        """
        Create a sequence of column definitions for the output report.

        Return:
            Sequence of column definitions to add to object.
        """
        columns = []

        # Leftmost column is always a doc title and ID
        columns.append(cdrcgi.Report.Column('CDR-ID', width='80px'))

        # Basic reports need cols for types of change and comments
        columns.append(cdrcgi.Report.Column('Title', width='400px'))

        # Basic reports need cols for types of change and comments
        columns.append(cdrcgi.Report.Column('SummarySections', width='500px'))

        return columns


    def createRows(self, sumChg):
        """
        Create one or more rows to represent a single Summary in the report.

        Pass:
            sumChg  - DocChanges object for this specific Summary.
                      For one flavor of the advanced report there may be
                       multiple DocChanges object passed (in different calls)
                       for one Summary.

        Return:
            Zero or more rows for passed DocChanges object.
        """
        # DEBUG
        debugRowCnt = 0

        # Representation of an empty cell
        EMPTY = ''

        # One row
        row  = []

        # All reports start with a summary ID
        row.append(sumChg.docId)
        row.append(sumChg.docTitle)
        row.append(sumChg.changes)
        return row


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
        if key not in ('Cancer Genetics',
                       'Complementary and Alternative Medicine'):
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
    div     { margin-left: 200px;
              margin-right: 200px;
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
   <div>
    <b>Summary Section Cleanup Report</b>
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

    tocHtml = """
   </div>
"""
    form += tocHtml

    form += """
  </form>
 </body>
</html>
"""
    return header + form

def extractTOC(cursor, docChg):
    """
    For the docChg.docId, find the doc, extract the requested types of
    change if they exist.  Return the results.

    Pass:
        cursor         - Open cursor to the database.
        docChg         - DocChanges object to receive the results.

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

    # Extract all Summary Sections
    tree = lx.fromstring(xml.encode('utf-8'))
    allSections = tree.findall('.//SummarySection')

    # Iterate through all SummarySections
    lastEmpty = 0
    for section in allSections:
        insert = False
        #for ancestor in section.iterancestors():
        #    cdrcgi.bail(repr(ancestor.tag))
        thisSection = list(section)
        children = "%s" % [x.tag for x in thisSection]
        if len(thisSection) == 0:
            docChg.changes.append("*** Empty Section ***")
            lastEmpty = 1
        elif thisSection[0].tag == 'Title':
            if lastEmpty == 1:
                docChg.changes.append("*** %s" % thisSection[0].text)
                lastEmpty = 0
            elif 'Para' in children or 'SummarySection' in children \
                                    or 'Table' in children          \
                                    or 'ItemizedList' in children   \
                                    or 'OrderedList' in children    \
                                    or 'QandASet' in children:
                continue
            else:
                for ancestor in section.iterancestors():
                    if ancestor.tag == 'Insertion':  insert = True

                # These sections appear within Insertion tags
                if insert:
                    continue
                    #docChg.changes.append(thisSection[0].text)
                    #docChg.changes.append("%s (inside Insertion tags)" % children )
                else:
                    docChg.changes.append(thisSection[0].text)
                    docChg.changes.append(children)
                #dada = section.XPath("ancestor::insertion")
                #cdrcgi.bail(dada)
        #elif thisSection[0].tag == 'Title':
        #    docChg.changes.append(thisSection[0].text)
        #if not 'Para' in children and not 'SummarySection' in children:
        #    docChg.changes.append(children)
    if lastEmpty == 1:
        docChg.changes.append("*** Last Section")
        lastEmpty = 0

    return


def getText(child):
    if len(list(child)) == 1 and list(child)[0].tag == 'SectMetaData':
        return ''
    else:
        text = lx.tostring(child, method="text", encoding="utf-8")

    return text


#----------------------------------------------------------------------
# MAIN
#----------------------------------------------------------------------
# Populate board lists
EnglishBoards = []
SpanishBoards = []

createBoardLists()

# Extract variables from the form
cfg = TOCConfig()

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
title = "Summary Type of Change Report"

options   = {'banner': title}
report = cdrcgi.Report('Summary Type of Change Report', outputRpt.tables)
#report = cdrcgi.Report('Summary Type of Change Report', outputRpt.tables,
#                        **options)
#cdrcgi.bail("%s" % dir(report.Table))

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
html = header + u"<br />\n".join(chgList) + u"</form></body></html>"
cdrcgi.sendPage(html)

cdrcgi.bail("Got to the end")
