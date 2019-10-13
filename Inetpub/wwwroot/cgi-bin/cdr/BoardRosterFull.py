#!/usr/bin/env python

"""Display the Board Roster with or without assistant information.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc

class Control(Controller):

    SUBTITLE = "PDQ Board Roster"
    BOARD_TYPES = (
        ("editorial", "PDQ Editorial Boards", True),
        ("advisory", "PDQ Editorial Advisory Boards", False),
    )
    GROUPINGS = (
        ("by_member", "Group by board member", True),
        ("by_board", "Group by PDQ board", False),
    )
    FORMATS = (
        ("qc", "QC report format", True),
        ("table", "Tabular report format", False),
    )
    OPTIONAL_COLUMNS = (
        ("board_name", "Board Name", True),
        ("phone", "Phone", False),
        ("fax", "Fax", False),
        ("email", "Email", False),
        ("cdrid", "CDR ID", False),
        ("start_date", "Start Date", False),
        ("govt_employee", "Government Employee", False),
        ("blank", "Blank Column", False),
    )

    @property
    def boards(self):
        if not hasattr(self, "_boards"):
            self._boards = {}
            board_type = f"PDQ {self.board_type.title()} Board"
            query = self.Query("active_doc b", "b.id", "b.title")
            query.join("query_term t", "t.doc_id = b.id")
            query.where("t.path = '/Organization/OrganizationType'")
            query.where(query.Condidition("t.value", board_type))
            for row in query.execute(self.cursor).fetchall():
                self._boards[row.id] = Board(self, row)

    @property
    def board_type(self):
        return self.fields.getvalue("board_type")
    @property
    def grouping(self):
        return self.fields.getvalue("grouping")
    @property
    def report_format(self):
        return self.fields.getvalue("format")
    @property
    def extra_columns(self):
        return self.fields.getlist("column")

    def build_tables(self):
        if self.report_format == "qc":
            return self.qc_report()
        rows = []
    def populate_form(self, page):
        """
        Add the fields to the form page.

        Pass:
            page - HTMLPage object to be populated
        """

        fieldset = page.fieldset("Select Boards")
        for value, label, checked in self.BOARD_TYPES:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("board_type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Grouping")
        for value, label, checked in self.GROUPINGS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("grouping", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Format")
        fieldset.set("id", "report-formats")
        for value, label, checked in self.FORMATS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("format", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optional Table Columns")
        fieldset.set("id", "columns")
        for value, label, checked in self.OPTIONAL_COLUMNS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("column", **opts))
        page.form.append(fieldset)
        page.add_script("""\
function check_format(which) {
    let format = jQuery("#report-formats input:checked").val();
    console.log("format is now " + format);
    if (format == "qc")
        jQuery("#columns").hide();
    else
        jQuery("#columns").show();
}
jQuery(function() {
    //jQuery("#report-formats input").click(check_format);
    check_format();
});""")

class Board:

    DETAILS = "/PDQBoardMemberInfo/BoardMembershipDetails"
    BOARD_PATH = f"{DETAILS}/BoardName/@cdr:ref"
    CURRENT_PATH = f"{DETAILS}/CurrentMember"
    PERSON_PATH = f"/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
    IACT = "Integrative, Alternative, and Complementary Therapies"

    def __init__(self, control, row):
        self.__control = control
        self.__row = row
    @property
    def control(self):
        return self.__control
    @property
    def id(self):
        return self.__row.id
    @property
    def title(self):
        if not hasattr(self, "_title"):
            self._title = self.__row.title.replace(self.IACT, "IACT")
    @property
    def members(self):
        if not hasattr(self, "_members"):
            fields = "p.doc_id AS member_id", "p.int_val AS person_id"
            query = self.control.Query("query_term p", *self.FIELDS).unique()
            query.join("active_doc a", "a.id = p.int_val")
            query.join("query_term b", "b.doc_id = p.doc_id")
            query.join("query_term c", "c.doc_id = p.doc_id")
            query.where(query.Condition("p.path", self.PERSON_PATH))
            query.where(query.Condition("b.path", self.BOARD_PATH))
            query.where(query.Condition("c.path", self.CURRENT_PATH))
            query.where(query.Condition("b.int_val", self.id))
            query.where("c.value = 'Yes'")
            self._members = []
            for row in query.execute(self.control.cursor).fetchall():
                self._members.append(self.Member(self, row))
    class Member:
        def __init__(self, board, row):
            self.__board = board
            self.__row = row
        @property
        def board(self):
            return self.__board
        @property
        def member_id(self):
            return self.__row.member_id
        @property
        def person_id(self):
            return self.__row.person_id
        response = cdr.filterDoc('guest',
                                 ['set:Denormalization PDQBoardMemberInfo Set',
                                  'name:Copy XML for Person 2',
                                  filterType[flavor]],
                                  boardMember[0],
                                  parm = [['otherInfo', otherInfo],
                                          ['assistant', assistant]])

Control().run()
'''
# ---------------------------------------------------------------------
# Class to collect all of the information for a single board member
# ---------------------------------------------------------------------
class BoardMemberInfo:
    def __init__(self, person, html):
        self.boardMemberID  = person[0]
        self.boardID   = person[1]
        self.boardName = person[2]
        self.startDate = person[3]
        self.govEmpl   = person[5]
        self.phone     = ''
        self.fax       = ''
        self.email     = ''

        myHtml = lxml.html.fromstring(html)
        self.boardMemberName = myHtml.find('b').text
        table = myHtml.find('table')
        try:
            for element in table.iter():
                if element.tag == 'phone':
                    self.phone = element.text
                elif element.tag == 'fax':
                    self.fax   = element.text
                elif element.tag == 'email':
                    self.email = element.text
        except:
            pass



dateString = time.strftime("%B %d, %Y")

filterType= {'summary':'name:PDQBoardMember Roster Summary',
             'excel'  :'name:PDQBoardMember Roster Excel',
             'full'   :'name:PDQBoardMember Roster'}
#----------------------------------------------------------------------
# Look up title of a board, given its ID.
#----------------------------------------------------------------------
def getBoardName(id):
    try:
        cursor.execute("SELECT title FROM document WHERE id = ?", id)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail('Failure looking up title for CDR%s' % id)
        return cleanTitle(rows[0][0])
    except Exception as e:
        cdrcgi.bail('Looking up board title: %s' % str(e))

#----------------------------------------------------------------------
# Remove cruft from a document title.
#----------------------------------------------------------------------
def cleanTitle(title):
    semicolon = title.find(';')
    if semicolon != -1:
        title = title[:semicolon]
    return title.strip()

#----------------------------------------------------------------------
# Build a picklist for PDQ Boards.
# This function serves two purposes:
# a)  create the picklist for the selection of the board
# b)  create a dictionary in subsequent calls to select the board
#     ID based on the board selected in the first call.
#----------------------------------------------------------------------
def getBoardPicklist(boardType):
    try:
        cursor.execute("""\
SELECT DISTINCT board.id, board.title
           FROM document board
           JOIN query_term org_type
             ON org_type.doc_id = board.id
          WHERE org_type.path = '/Organization/OrganizationType'
            AND org_type.value IN ('PDQ %s Board')
       ORDER BY board.title""" % boardType)
        rows = cursor.fetchall()
        allBoards = {}
        for id, title in rows:
            if id != 256088:
                allBoards[id] = cleanTitle(title)
    except Exception as e:
        cdrcgi.bail('Database query failure: %s' % e)
    return allBoards


# -------------------------------------------------
# Create the table row for a specific person
# -------------------------------------------------
def addTableRow(person, columns):
    tableRows = {}
    for colHeader, colDisplay in columns:
        if colHeader == 'Board Name':
            tableRows[colHeader] = person.boardName
        elif colHeader == 'Phone':
            tableRows[colHeader] = person.phone
        elif colHeader == 'Fax':
            tableRows[colHeader] = person.fax
        elif colHeader == 'Email':
            tableRows[colHeader] = person.email
        elif colHeader == 'CDR-ID':
            tableRows[colHeader] = person.boardMemberID
        elif colHeader == 'Start Date':
            tableRows[colHeader] = person.startDate
        elif colHeader == 'Gov. Empl':
            tableRows[colHeader] = person.govEmpl
        elif colHeader == 'Blank':
            tableRows[colHeader] = ''

    htmlRow = """\
       <tr>
        <td>%s</td>""" % person.boardMemberName

    for colHeader, colDisplay in columns:
        if colDisplay == 'Yes' and colHeader == 'Email':
            htmlRow += """
        <td class="email">
         <a href="mailto:%s">%s</a>
        </td>""" % (tableRows[colHeader], tableRows[colHeader])
        elif colDisplay == 'Yes' and colHeader == 'Blank':
            htmlRow += """
        <td class="blank">&nbsp;</td>"""
        elif colDisplay == 'Yes':
            htmlRow += """
        <td>%s</td>""" % tableRows[colHeader]

    htmlRow += """
       </tr>"""
    return htmlRow

#----------------------------------------------------------------------
# Get the board's name from its ID.
#----------------------------------------------------------------------
allBoards = getBoardPicklist(boardType)
boardIds  = list(allBoards)

#----------------------------------------------------------------------
# Main SELECT query
#----------------------------------------------------------------------
try:
    cursor.execute("""\
 SELECT DISTINCT member.doc_id, member.int_val,
                 term_start.value, person_doc.title, ge.value
            FROM query_term member
            JOIN query_term curmemb
              ON curmemb.doc_id = member.doc_id
             AND LEFT(curmemb.node_loc, 4) = LEFT(member.node_loc, 4)
            JOIN query_term person
              ON person.doc_id = member.doc_id
            JOIN document person_doc
              ON person_doc.id = person.doc_id
            JOIN query_term ge
              ON ge.doc_id = person_doc.id
             AND ge.path = '/PDQBoardMemberInfo/GovernmentEmployee'
 LEFT OUTER JOIN query_term term_start
              ON term_start.doc_id = member.doc_id
             AND LEFT(term_start.node_loc, 4) = LEFT(member.node_loc, 4)
             AND term_start.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/TermStartDate'
           WHERE member.path  = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/BoardName/@cdr:ref'
             AND curmemb.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/CurrentMember'
             AND person.path  = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'
             AND curmemb.value = 'Yes'
             AND person_doc.active_status = 'A'
             AND member.int_val in (%s)
           ORDER BY member.int_val""" %
                      ", ".join([str(x) for x in boardIds]))
    rows = cursor.fetchall()
    boardMembers = []

    for docId, boardId, term_start, name, ge in rows:
        boardName = getBoardName(boardId)
        boardMembers.append([docId, boardId, boardName, term_start, name, ge])

except Exception as e:
    cdrcgi.bail('Database query failure: %s' % e)

# Sorting the list alphabetically by board member
# or by board member grouped by board name
# -----------------------------------------------
if sortType == 'Member':
    getcount = operator.itemgetter(4)
    sortedMembers = sorted(boardMembers, key=getcount)
else:
    sortedMembers = sorted(boardMembers, key=operator.itemgetter(2, 4))

# We're creating two flavors of the report here: excel and html
# (but users decided later not to use the Excel report anymore)
# -------------------------------------------------------------
if rptType == 'html':
    # ---------------------------------------------------------------
    # Create the HTML Output Page
    # ---------------------------------------------------------------
    html = """\
<!DOCTYPE html>
<html>
  <head>
    <title>PDQ Board Member Roster Report - %s</title>
    <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>
    <style type='text/css'>
       h1       { font-family: Arial, sans-serif;
                  font-size: 16pt;
                  text-align: center;
                  font-weight: bold; }
       h2       { font-family: Arial, sans-serif;
                  font-size: 14pt;
                  text-align: center;
                  font-weight: bold; }
       p        { font-family: Arial, sans-serif;
                  font-size: 12pt; }
       #summary td, #summary th
                { border: 1px solid black; }
       #hdg     { font-family: Arial, sans-serif;
                  font-size: 16pt;
                  font-weight: bold;
                  text-align: center;
                  padding-bottom: 20px;
                  border: 0px; }
       #summary { border: 0px; }

       /* The Board Member Roster information is created via a global */
       /* template for Persons.  The italic display used for the QC   */
       /* report does therefore need to be suppressed here.           */
       /* ----------------------------------------------------------- */
       i        { font-family: Arial, sans-serif; font-size: 12pt;
                  font-style: normal; }
       span.SectionRef { text-decoration: underline; font-weight: bold; }

       .theader { background-color: #CFCFCF; }
       .name    { font-weight: bold;
                  vertical-align: top; }
       .phone, .email, .fax, .cdrid
                { vertical-align: top; }
       .blank   { width: 100px; }
       .bheader { font-family: Arial, sans-serif;
                  font-size: 14pt;
                  font-weight: bold; }
       #main    { font-family: Arial, Helvetica, sans-serif;
                  font-size: 12pt; }
    </style>
  </head>
  <body id="main">
    <h1>All %s Boards<br>
    """ % (boardType, boardType)

    # Adjusting the report title depending on the input values
    # --------------------------------------------------------
    if sortType == 'Member':
        html += """\
      <span style="font-size: 12pt">by Member</span><br>
"""
    else:
        html += """\
      <span style="font-size: 12pt">by Board and Member</span><br>
"""
    html += """\
      <span style="font-size: 12pt">%s</span>
    </h1>
""" % (dateString)

    boardTitle = None
    lastBoardTitle = None

    # Need to create the table wrapper for the summary sheet
    # We always print at least the board member name as a column
    # -----------------------------------------------------------
    if flavor == 'summary':
        html += """\
    <table id="summary" cellspacing="0" cellpadding="5">
      <tr class="theader">
        <th class="thcell">Name</th>
"""

        # Add column headings
        # -------------------
        for colHeader, colDisplay in columns:
            if colDisplay == 'Yes':
                html += """\
        <th class="thcell">%s</th>
""" % colHeader
        html += """\
      </tr>
"""

    # Loop through the list of sorted members to get the address info
    # ---------------------------------------------------------------
    for boardMember in sortedMembers:
        boardTitle = boardMember[2]
        response = cdr.filterDoc('guest',
                                 ['set:Denormalization PDQBoardMemberInfo Set',
                                  'name:Copy XML for Person 2',
                                  filterType[flavor]],
                                  boardMember[0],
                                  parm = [['otherInfo', otherInfo],
                                          ['assistant', assistant]])
        if type(response) in (str, bytes):
            cdrcgi.bail("%s: %s" % (boardMember[0], response))

        # For the report we're just attaching the resulting HTML
        # snippets to the previous output.
        #
        # We need to wrap each person in a table in order to prevent
        # page breaks within address blocks after the convertion to
        # MS-Word.
        # -----------------------------------------------------------
        filtered_member_info = response[0]
        if flavor == 'full':
            # If we're grouping by board we need to display the board name
            # as a title.
            # ------------------------------------------------------------
            if not sortType == 'Member' and not lastBoardTitle == boardTitle:
                html += """\
    <br>
    <span class="bheader">%s</span>
    <br>
""" % (boardTitle)

            # If we're not grouping by board we need to print the board for
            # each board member
            # -------------------------------------------------------------
            if sortType == 'Member':
                html += """\
    <table width='100%%'>
      <tr>
        <td>%s<span style="font-style: italic">%s</span><br><br><td>
      </tr>
    </table>
""" % (filtered_member_info, boardMember[2])
            else:
                html += """\
    <table width='100%%'>
      <tr><td>%s<br><td></tr>
    </table>
""" % filtered_member_info
            lastBoardTitle = boardTitle

        # Creating the Summary sheet output
        # ---------------------------------
        else:
            memberInfo = BoardMemberInfo(boardMember, response[0])

            # If we're grouping by board we need to display the board name
            # as an individuel row in the table
            # ------------------------------------------------------------
            if not sortType == 'Member' and not lastBoardTitle == boardTitle:
                html += """\
      <tr><td class="theader" colspan="%d"><b>%s</b></td></tr>
""" % (countCols(columns) + 1, boardTitle)
            #if sortType == 'Member':
            html += """\
%s
""" % (addTableRow(memberInfo, columns))

            lastBoardTitle = boardTitle

    # Need to end the table wrapper for the summary sheet
    # ------------------------------------------------------
    if not flavor == 'full':
        html += """\
    </table>
"""

    html += """
    <br>
  </body>
</html>
"""

    # The users don't want to display the country if it's the US.
    # Since the address is build by a common address module we're
    # better off removing it in the final HTML output
    # ------------------------------------------------------------
    cdrcgi.sendPage(html.replace('U.S.A.<br>', ''))

else:
    cdrcgi.bail("Sorry, don't know report type: %s" % rptType)
'''
