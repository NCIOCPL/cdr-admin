#----------------------------------------------------------------------
#
# BZIssue::4258
# BZIssue::4250
# BZIssue::4807 - Board Member not listed on Mailer Reports
#
# [Request 4258:]
#
# "We need to have a report to give us some information about the summary
# mailers.  This report will be generated in an Excel Spreadsheet, and
# contain columns for Mailer ID, Board Member Name, Summary Name, Mailer
# Date Generated, Mailer Date Checked In, and Change Category.
#
# "To run the report, we would like to be able to select a Board (Editorial
# or Editorial Advisory), select whether we want it sorted by Board Member
# or by Summary Name, and select whether we want to show information for
# the Last Mailer, or the Last Checked-In Mailer.  I will put a sample in
# as an attachment.
#
# [Request 4259:]
#
# "We need a report that will give us the mailer history for all of the
# summaries on a Board over a selected date range.  The report should be
# generated in Excel, and have columns for Mailer ID, Board Member Name,
# Summary Name, Mailer Date Generated, Mailer Date Checked In, and Change
# Category.
#
# "To run the report, we would like to be able to select the Board
# (Editorial or Advisory), enter a Date Range, and select whether to sort
# by Board Member or by Summary.  I will put in a sample of the report.
# Request form for generating RTF letters to board members."
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, time
import lxml.etree as etree

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
flavor    = fields.getvalue("flavor") or None
board     = fields.getvalue("board") or None
begin     = fields.getvalue("begin") or None
end       = fields.getvalue("end") or None
sortBy    = fields.getvalue("sortBy") or "member"
selectBy  = fields.getvalue("selectBy") or "lastMailer"

title     = "CDR Administration"
section   = "Summary Mailer %sReport" % (flavor == "4259" and "History " or "")
SUBMENU   = "Mailer Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'SummaryMailerReport.py'
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
    cdrcgi.navigateTo("Mailers.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Make sure a report type was specified.
#----------------------------------------------------------------------
if flavor not in ("4258", "4259"):
    cdrcgi.bail("Missing required flavor parameter")

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
except Exception, e:
    cdrcgi.bail('Database connection failure: %s' % e)

#----------------------------------------------------------------------
# Build a CGI form picklist for the PDQ boards.
#----------------------------------------------------------------------
def makeBoardPicklist(cursor):
    cursor.execute("""\
  SELECT DISTINCT b.doc_id, b.value
    FROM query_term b
    JOIN query_term s
      ON b.doc_id = s.int_val
   WHERE s.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
     AND b.path = '/Organization/OrganizationNameInformation'
                + '/OfficialName/Name'
ORDER BY b.value""", timeout = 300)
    html = [u"""\
<select name='board'>
"""]
    for docId, boardName in cursor.fetchall():
        html.append(u"""\
<option value='%d'>%s</option>
""" % (docId, cgi.escape(boardName)))
    html.append(u"""\
</select>
""")
    return u"".join(html)

#----------------------------------------------------------------------
# Add the title row and the column headers.
#----------------------------------------------------------------------
def addHeaderRows(sheet, styles, cursor, board, titleStart):
    boardName = getBoardName(cursor, board)
    now       = time.strftime(u"%Y-%m-%d")
    title     = "%s - %s  %s" % (titleStart, boardName, now)
    widths = (10, 30, 60, 10, 10, 40)
    headers = ("Mailer ID", "Board Member", "Summary", "Sent", "Response",
               "Changes")
    for col, chars in enumerate(widths):
        sheet.col(col).width = styles.chars_to_width(chars)
    sheet.write_merge(0, 0, 0, len(widths) - 1, title, styles.banner)
    for col, header in enumerate(headers):
        sheet.write(2, col, header, styles.header)

#----------------------------------------------------------------------
# Generate the Summary Mailer Report.
#----------------------------------------------------------------------
def report4258(sheet, styles, cursor, board, selectBy):
    if selectBy == "lastMailer":
        dateField = "Sent"
        title = u"Summary Mailer Report (Last)"
    else:
        dateField = "Response/Received"
        title = u"Summary Mailer Report (Last Checked-In)"
    addHeaderRows(sheet, styles, cursor, board, title)
    dateField = selectBy == "lastMailer" and "Sent" or "Response/Received"
    cursor.execute("""\
        SELECT DISTINCT r.doc_id, r.int_val, s.int_val, d.value
          FROM query_term r
          JOIN query_term s
            ON s.doc_id = r.doc_id
          JOIN query_term d
            ON d.doc_id = r.doc_id
          JOIN #board_member m
            ON m.person_id = r.int_val
          JOIN #board_summary b
            ON b.doc_id = s.int_val
         WHERE r.path = '/Mailer/Recipient/@cdr:ref'
           AND s.path = '/Mailer/Document/@cdr:ref'
           AND d.path = '/Mailer/%s'""" % dateField, timeout = 300)
    mailers = {}
    for m, r, s, d in cursor.fetchall():
        if d and BoardMember.members[r].membershipActive(d):
            key = (r, s)
            if key not in mailers or mailers[key][1] < d:
                mailers[key] = (m, d)
    finishReport(sheet, styles, cursor, [v[0] for v in mailers.values()])

#----------------------------------------------------------------------
# Generate the Summary Mailer History Report.
#----------------------------------------------------------------------
def report4259(sheet, styles, cursor, board, begin, end):
    if not begin or not end:
        cdrcgi.bail("Both date range parameters are required for this report.")
    end = cdr.calculateDateByOffset(1, end)
    title = u"Summary Mailer History Report (%s - %s)" % (begin, end)
    addHeaderRows(sheet, styles, cursor, board, title)
    cursor.execute("""\
        SELECT DISTINCT mailer.doc_id, sent.value, member.person_id
          FROM query_term mailer
          JOIN query_term sent
            ON sent.doc_id = mailer.doc_id
          JOIN query_term recip
            ON recip.doc_id = mailer.doc_id
          JOIN #board_member member
            ON member.person_id = recip.int_val
          JOIN #board_summary summary
            ON summary.doc_id = mailer.int_val
         WHERE mailer.path = '/Mailer/Document/@cdr:ref'
           AND sent.path = '/Mailer/Sent'
           AND recip.path = '/Mailer/Recipient/@cdr:ref'
           AND sent.value BETWEEN '%s' AND '%s'""" %
                   (begin, end), timeout = 300)
    mailerIds = []
    for mailerId, sent, personId in cursor.fetchall():
        if BoardMember.members[personId].membershipActive(sent):
            mailerIds.append(mailerId)
    finishReport(sheet, styles, cursor, mailerIds)

#----------------------------------------------------------------------
# Add the data rows to the report.
#----------------------------------------------------------------------
def finishReport(sheet, styles, cursor, mailerIds):
    mailers = [Mailer(mailerId, cursor) for mailerId in mailerIds]
    mailers.sort()
    row = 3
    for mailer in mailers:
        row = mailer.addRow(sheet, styles, row)

#----------------------------------------------------------------------
# Object that knows about all the spans of membership in a board for
# a single board member.
#----------------------------------------------------------------------
class BoardMember:
    members = {}
    class Membership:
        def __init__(self, node):
            self.start = self.end = self.boardId = None
            for e in node.findall('BoardName'):
                a = e.get('{cips.nci.nih.gov/cdr}ref')
                try:
                    self.boardId = cdr.exNormalize(a)[1]
                except:
                    pass
            for e in node.findall('TermStartDate'):
                d = e.text
                if d:
                    self.start = d
            for e in node.findall('TerminationDate'):
            #for e in node.findall('TermEndDate'):
                d = e.text
                if d:
                    self.end = d
    def __init__(self, cursor, personId, memberId, boardId):
        tomorrow      = str(cdr.calculateDateByOffset(1))
        self.personId = personId
        self.memberId = memberId
        self.terms    = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", memberId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        for e in tree.findall('BoardMembershipDetails'):
            membership = BoardMember.Membership(e)
            #cdrcgi.bail("%s: %s: %s - %s" % (memberId, membership.boardId,
            #                             membership.start, membership.end))
            if membership.boardId == boardId and membership.start:
                self.terms.append(membership)
    def membershipActive(self, when):
        for term in self.terms:
            if term.start <= when:
                if not term.end or term.end >= when:
                    return True
        return False

#----------------------------------------------------------------------
# Object in which we collect what we need for the mailers.
#----------------------------------------------------------------------
class Mailer:
    sortBy = "member"
    recipients = {}
    summaries = {}
    def __init__(self, mailerId, cursor):
        self.docId = mailerId
        self.recipient = u""
        self.summary = u""
        self.sent = u""
        self.response = u""
        self.changes = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", mailerId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        for e in tree.findall('Recipient'):
            self.recipient = Mailer.getRecipient(e, cursor)
        for e in tree.findall('Document'):
            self.summary = Mailer.getSummary(e, cursor)
        for e in tree.findall('Sent'):
            self.sent = e.text[:10]
        for r in tree.findall('Response'):
            for e in r.findall('Received'):
                self.response = e.text and e.text[:10] or u""
            for e in r.findall('ChangesCategory'):
                if e.text:
                    change = e.text.strip()
                    if change:
                        self.changes.append(change)
    def __cmp__(self, other):
        if Mailer.sortBy == "member":
            diff = cmp(self.recipient, other.recipient)
            if diff:
                return diff
            return cmp(self.summary, other.summary)
        diff = cmp(self.summary, other.summary)
        if diff:
            return diff
        return cmp(self.recipient, other.recipient)
    @classmethod
    def getSummary(cls, e, cursor):
        docId = e.get('{cips.nci.nih.gov/cdr}ref')
        try:
            docId = cdr.exNormalize(docId)[1]
        except:
            return u""
        if docId in cls.summaries:
            return cls.summaries[docId]
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/Summary/SummaryTitle'
               AND doc_id = ?""", docId)
        rows = cursor.fetchall()
        title = rows and rows[0][0] or u""
        cls.summaries[docId] = title
        return title
    @classmethod
    def getRecipient(cls, e, cursor):
        docId = e.get('{cips.nci.nih.gov/cdr}ref')
        try:
            docId = cdr.exNormalize(docId)[1]
        except:
            return u""
        if docId in cls.recipients:
            return cls.recipients[docId]
        cursor.execute("""\
            SELECT title
              FROM document
             WHERE id = ?""", docId)
        rows = cursor.fetchall()
        title = rows and rows[0][0] or u""
        cls.recipients[docId] = title.split(u";")[0]
        return cls.recipients[docId]
    def addRow(self, sheet, styles, row):
        sheet.write(row, 0, self.docId, styles.center)
        sheet.write(row, 1, self.recipient, styles.left)
        sheet.write(row, 2, self.summary, styles.left)
        sheet.write(row, 3, self.sent, styles.center)
        sheet.write(row, 4, self.response, styles.center)
        sheet.write(row, 5, u"".join(self.changes), styles.left)
        return row + 1

#----------------------------------------------------------------------
# Get the board name from the organization record.
#----------------------------------------------------------------------
def getBoardName(cursor, boardId):
    cursor.execute("""\
        SELECT value
          FROM query_term
         WHERE path = '/Organization/OrganizationNameInformation'
                    + '/OfficialName/Name'
           AND doc_id = ?""", boardId)
    return cursor.fetchall()[0][0]

#----------------------------------------------------------------------
# Create the report if we have a request for one.
#----------------------------------------------------------------------
if board:

    try:
        import msvcrt, os, sys
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except:
        pass

    cursor = conn.cursor()
    cursor.execute("CREATE TABLE #board_member (person_id INT, member_id INT)")
    cursor.execute("CREATE TABLE #board_summary (doc_id INT)")
    cursor.execute("""\
        INSERT INTO #board_member
        SELECT DISTINCT m.int_val, m.doc_id
          FROM query_term m
          JOIN query_term b
            ON m.doc_id = b.doc_id
          JOIN active_doc d
            ON d.id = m.doc_id
         WHERE m.path = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'
           AND b.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                      + '/BoardName/@cdr:ref'
           AND b.int_val = ?""", board)
    cursor.execute("""\
        INSERT INTO #board_summary
        SELECT DISTINCT doc_id
          FROM query_term
         WHERE path = '/Summary/SummaryMetaData/PDQBoard'
                    + '/Board/@cdr:ref'
           AND int_val = ?""", board)
    conn.commit()
    cursor.execute("SELECT person_id, member_id FROM #board_member")
    for personId, memberId in cursor.fetchall():
        BoardMember.members[personId] = BoardMember(cursor, personId, memberId,
                                                    int(board))
    styles = cdrcgi.ExcelStyles()
    sheet = styles.add_sheet(section)
    Mailer.sortBy = sortBy

    if flavor == "4258":
        report4258(sheet, styles, cursor, board, selectBy)
    else:
        report4259(sheet, styles, cursor, board, begin, end)
    stamp = time.strftime("%Y%m%d%H%M%S")
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=SummMailRep-%s.xls" % stamp
    print
    styles.book.save(sys.stdout)

else:
    boards = makeBoardPicklist(conn.cursor())
    form = [u"""\
   <input type='hidden' name='flavor' value='%s' />
   <input type='hidden' name='%s' value='%s' />
   <table border='0'>
    <tr>
     <th align='right'>Board: </th>
     <td>%s</td>
    </tr>
""" % (flavor, cdrcgi.SESSION, session, boards)]
    if flavor == "4259":
        form.append(u"""\
    <tr>
     <th align='right'>Start: </th>
     <td><input class='CdrDateField' name='begin' id='begin' /></td>
    </tr>
    <tr>
     <th align='right'>End: </th>
     <td><input class='CdrDateField' name='end' id='end' /></td>
    </tr>
""")
    form.append(u"""\
    <tr>
     <th align='right'>Sort By: </th>
     <td>
      <input type='radio' name='sortBy' value='member' checked='1' />
      Board Member
      <input type='radio' name='sortBy' value='summary' />
      Summary Name
     </td>
    </tr>
""")
    if flavor == "4258":
        form.append(u"""\
    <tr>
     <th align='right'>Show: </th>
     <td>
      <input type='radio' name='selectBy' value='lastMailer' checked='1' />
      Last Mailer
      <input type='radio' name='selectBy' value='lastCheckedInMailer' />
      Last Checked-In Mailer
     </td>
    </tr>
""")
    form.append(u"""\
   </table>
  </form>
 </body>
</html>
""")

    cdrcgi.sendPage(header + u"".join(form))
