#----------------------------------------------------------------------
# Creatign a HTML report to help track who had been invited to the
# Boards in the past, what their current (and past) membership statuses
# are, and reasons why they left PDQ. This information will be helpful
# in discussions about inviting new members.
#                                           Volker Englisch, 2011-09-23
#
# BZIssue::5061 -Board Membership and Invitation History Report
# OCECDR-3649: PDQ Board Invitation History Report - Problem with
#              exclude current members options
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, time
import lxml.etree as etree

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
boardIds   = fields and fields.getvalue("board")    or None
excludeCurrEd = fields and fields.getvalue("NoCurEd")  or False
excludeCurrAd = fields and fields.getvalue("NoCurAd")  or False
dispBoardName = fields and fields.getvalue("bname") or False
dispAoE       = fields and fields.getvalue("aoe")      or False
dispInvDate   = fields and fields.getvalue("idate")    or False
dispResponse  = fields and fields.getvalue("response") or False
dispCurMember = fields and fields.getvalue("member")   or False
dispEndDate   = fields and fields.getvalue("end")      or False
dispReason    = fields and fields.getvalue("reason")   or False
blankCol      = fields and fields.getvalue("blank")    or False
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
title      = "PDQ Board Invitation History Report"
instr      = "Report on Board Member History"
script     = "BoardInvitationHistory.py"
SUBMENU    = "Report Menu"
buttons    = ("Submit", SUBMENU, cdrcgi.MAINMENU)
header     = cdrcgi.header(title, title, instr, script, buttons,
                           method = 'GET',
                           stylesheet = """
    <script type='text/javascript'>
     function doFullReport() {
         document.getElementById('summary').checked = false;
         var form = document.forms[0];
         {
             form.noCurEd.value  = form.noCurEd.checked  ? 'Yes' : 'No';
             form.ainfo.value  = form.ainfo.checked  ? 'Yes' : 'No';
             form.sginfo.value = form.sginfo.checked ? 'Yes' : 'No';
             form.sheet.value  = form.sheet.checked  ? 'summary' : 'full';
         }
     }
    </script>
    <style type="text/css">
     td       { font-size: 12pt; }
     .label   { font-weight: bold; }
     .label2  { font-size: 11pt;
                font-weight: bold; }
     .select:hover { background-color: #FFFFCC; }
     .grey    {background-color: #BEBEBE; }
     .topspace { margin-top: 24px; }

    </style>
""")
dateString = time.strftime("%B %d, %Y")

filterType= {'summary':'name:PDQBoardMember Roster Summary',
             'full'   :'name:PDQBoardMember Roster'}
allRows   = []

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Object for one PDQ board member.
#----------------------------------------------------------------------
class BoardMember:
    def __init__(self, cursor, row):
        self.bmId      = row[0]
        self.persId    = row[1]
        self.fname     = row[2]
        self.lname     = row[3]
        self.boardInfo = row[4]
        ### self.boardId   = row[4]
        ### self.boardname = row[5]
        # self.current   = None
        #self.invDate   = None
        #self.aoe       = ''
        #self.response  = None
        #self.endDate   = None
        #self.reason    = None

        ### if self.boardname.find('Advisory'):
        ###     self.currentAd = True
        ###     self.currentEd = False
        ### else:
        ###     self.currentAd = False
        ###     self.currentEd = True

        cursor.execute("""SELECT xml
                          FROM document
                         WHERE id = ?""", self.bmId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))

        self.allBoardsInfo = {}
        for boardId, boardName in self.boardInfo:
            self.allBoardsInfo[boardId] = {'name':boardName}
            for detailsNode in tree.findall('BoardMembershipDetails'):
                if detailsNode.findall('BoardName')[0].text == boardName:


                    #self.current = detailsNode.findall('CurrentMember')[0].text
                    self.allBoardsInfo[boardId]['current'] = detailsNode.findall('CurrentMember')[0].text
                    #self.invDate   = detailsNode.findall('InvitationDate')[0].text
                    self.allBoardsInfo[boardId]['invdate'] = detailsNode.findall('InvitationDate')[0].text
                    #self.response  = detailsNode.findall('ResponseToInvitation')[0].text
                    self.allBoardsInfo[boardId]['response'] = detailsNode.findall('ResponseToInvitation')[0].text
                    if detailsNode.findall('AreaOfExpertise'):
                        #self.aoe = ", ".join(["%s" % g.text for g in \
                        #                 detailsNode.findall('AreaOfExpertise')])
                        self.allBoardsInfo[boardId]['aoe'] = ", ".join(["%s" % g.text for g in \
                                         detailsNode.findall('AreaOfExpertise')])
                    if detailsNode.findall('TerminationDate'):
                        #self.endDate   = detailsNode.findall('TerminationDate')[0].text
                        self.allBoardsInfo[boardId]['termdate'] = detailsNode.findall('TerminationDate')[0].text
                    if detailsNode.findall('TerminationReason'):
                        #self.reason    = detailsNode.findall('TerminationReason')[0].text
                        self.allBoardsInfo[boardId]['termreason'] = detailsNode.findall('TerminationReason')[0].text
        #cdrcgi.bail(self.allBoardsInfo)


#----------------------------------------------------------------------
# Function to decide if a board member needs to get printed.
# If there is no exclusion criteria specified the board memeber will
# always get printed.  If there is a criteria 'A' specified, the
# appropriate board (Advisory or Editorial) regardless of the type
# (Genetics, Treatment, etc) will turn off printing if the board
# member is currently active on that board.
#----------------------------------------------------------------------
def printRow(boardMember, includeIds, exclude):
    printIt = True

    # Print everything if no exclusion is specified
    # ---------------------------------------------
    if not exclude:
        return printIt

    # Find out if printing needs to be suppressed based on the
    # exclusion criteria
    # --------------------------------------------------------
    # If both current ed board and adv board members need to
    # be excluded check if this person is current for either
    # one.
    if 'Editorial Board' in exclude and \
         'Editorial Advisory Board' in exclude:
        for id in boardMember.allBoardsInfo.keys():
            if 'current' in boardMember.allBoardsInfo[id]        and \
               boardMember.allBoardsInfo[id]['current'] == 'Yes':
               printIt = False
    # If current ed board members need to be excluded check
    # to ensure the board is not an adv board.
    elif 'Editorial Board' in exclude:
        for id in boardMember.allBoardsInfo.keys():
            if 'current' in boardMember.allBoardsInfo[id]        and \
               boardMember.allBoardsInfo[id]['current'] == 'Yes' and \
               boardMember.allBoardsInfo[id]['name'].find('Advisory') == -1:
               printIt = False
    # If current adv board members need to be excluded check
    # to ensure the board is not an ed board.
    elif 'Editorial Advisory Board' in exclude:
        for id in boardMember.allBoardsInfo.keys():
            if 'current' in boardMember.allBoardsInfo[id]        and \
               boardMember.allBoardsInfo[id]['current'] == 'Yes' and \
               boardMember.allBoardsInfo[id]['name'].find('Advisory') > 0:
               printIt = False

    return printIt


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
    except Exception, e:
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
# Build a picklist for PDQ Boards and create an additional option for
# all boards.
# Returns the HTML snipped for a <SELECT/> element.
#----------------------------------------------------------------------
def getBoardPicklist():
    allBoards = []
    picklist = """
     <SELECT NAME='board' size='6' MULTIPLE='MULTIPLE'>
"""
    options = ""
    try:
        cursor.execute("""\
SELECT DISTINCT board.id, board.title
           FROM document board
           JOIN query_term org_type
             ON org_type.doc_id = board.id
          WHERE org_type.path = '/Organization/OrganizationType'
            AND org_type.value IN ('PDQ Editorial Board',
                                   'PDQ Advisory Board')
       ORDER BY board.title""")
        for id, title in cursor.fetchall():
            allBoards.append(id)
            title = cleanTitle(title)
            options += "      <OPTION value='%d'>%s</OPTION>\n" % (id, title)
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])

    allIds = ",".join(["%s" % b for b in allBoards])
    allOpt  = "     <OPTION value='%s' SELECTED='SELECTED'>" % allIds
    allOpt += "All Boards</OPTION>\n"

    return picklist + allOpt + options + "     </SELECT>\n"

#----------------------------------------------------------------------
# Creating the table rows for the HTML output - one row for each member
# and board.
# This requires that the members are coming in sorted because all that
# we do now is to filter the members we don't want to see and add
# additional information for the person that we do want to see.
# Return:  string containing <tr>... info </tr>
#----------------------------------------------------------------------
def makeRow(cursor, row, boardIds, dispColumn, excludeRow):
    if not type(boardIds) == type([]):
        boardIds = [boardIds]
    member = BoardMember(cursor, row)
    bmrow = u""

    for boardId in member.allBoardsInfo.keys():
        # Check if this row needs to be printed
        if not printRow(member, boardIds, excludeRow):
            return bmrow
        ### for skip in excludeRow:
        ###     #cdrcgi.bail("%s - %s" % (member.boardname, skip))
        ###     if member.boardname.find(skip) > 0 and member.current == 'Yes':
        ###         #cdrcgi.bail("%s (%s) : %s, %d" % (member.boardname, skip,
        ###         #     excludeRow, member.boardname.find(skip)))
        ###         return ""

        if str(boardId) in boardIds:
            cssClass = u"%s" % boardId

            if 'current' in member.allBoardsInfo[boardId] and \
                            member.allBoardsInfo[boardId]['current'] == 'Yes':
                cssClass += u" current"
            else:
                cssClass += u" notcurrent"
            bmrow += """
         <tr class="%s">
          <td>%d</td>
          <td>%s, %s</td>
    """ % (cssClass, member.bmId, member.lname, member.fname)

            if 'BoardName' in dispColumn:
                bmrow += """
          <td>%s</td>
    """ % (member.allBoardsInfo[boardId]['name'])

            if 'AoE' in dispColumn:
                bmrow += """
          <td>%s</td>
    """ % ('aoe' in member.allBoardsInfo[boardId] and
                    member.allBoardsInfo[boardId]['aoe'] or "&nbsp;")

            if 'Invitation' in dispColumn:
                bmrow += """
          <td>%s</td>
    """ % ('invdate' in member.allBoardsInfo[boardId] and
                        member.allBoardsInfo[boardId]['invdate'] or "&nbsp;")

            if 'Response' in dispColumn:
                bmrow += """
          <td>%s</td>
    """ % ('response' in member.allBoardsInfo[boardId] and
                         member.allBoardsInfo[boardId]['response'])

            if 'Current' in dispColumn:
                bmrow += """
          <td>%s</td>
    """ % ('current' in member.allBoardsInfo[boardId] and
                        member.allBoardsInfo[boardId]['current'] or '&nbsp;')

            if 'EndDate' in dispColumn:
                bmrow += """
          <td>%s</td>
    """ % ('termdate' in member.allBoardsInfo[boardId] and
                         member.allBoardsInfo[boardId]['termdate'])

            if 'Termination' in dispColumn:
                bmrow += """
          <td>%s</td>
    """ % ('termreason' in member.allBoardsInfo[boardId] and
                           member.allBoardsInfo[boardId]['termreason'])

            # If a blank column is printed
            # ----------------------------
            if 'BlankCol' in dispColumn:
                bmrow += u"""
             <td class="blank">&nbsp;</td>"""

            bmrow += """
         </tr>
    """
    ###         return row
    ###     else:
    ###         return ""
    #    if member.fname == 'Karen':
    #        cdrcgi.bail(member.allBoardsInfo)
    return bmrow


#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not boardIds:
    form   = """\
  <input TYPE='hidden' NAME='%s' VALUE='%s'>

  <table>
   <tr>
    <td class="label">PDQ Board:&nbsp;</TD>
    <td>%s</td>
   </tr>
   <tr>
    <td> </td>
    <td class="select">
     <input type='checkbox' name='NoCurEd' id='edboard'>
     <label for="edboard">Exclude current Ed Board Members</label>
    </td>
   </tr>
   <tr>
    <td> </td>
    <td class="select">
     <input type='checkbox' name='NoCurAd' id='adboard'>
     <label for="adboard">Exclude current Advisory Board Members</label>
    </td>
   </tr>
   <tr>
    <td colspan="2">
     <div style="height: 10px"> </div>
    </td>
   </tr>
   <tr>
    <td> </td>
    <td class="grey">
     <div style="height: 10px"> </div>
     <table>
      <tr>
       <td> </td>
       <td>
       <strong>Include Additional Columns</strong>
       </td>
      </tr>
      <tr>
       <td><span style="margin-left: 20px"> </span></td>
       <td class="select">
        <input type='checkbox' name='bname' id='E1' CHECKED>
        <label for="E1">Board Name</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='aoe' id='E2'>
        <label for="E2">Area of Expertise</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='idate' id='E3'>
        <label for="E3">Invitation Date</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='response' id='E4'>
        <label for="E4">Response to Invitation</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='member' id='E5'>
        <label for="E5">Current Member</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='end' id='E7'>
        <label for="E7">Termination End Date</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='reason' id='E8'>
        <label for="E8">Termination Reason</label>
       </td>
      </tr>
      <tr>
       <td> </td>
       <td class="select">
        <input type='checkbox' name='blank' id='E6'>
        <label for="E6">Blank Column</label>
       </td>
      </tr>
     </table>
    </td>
   </tr>
   </table>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, getBoardPicklist())
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Get the board's name from its ID.  If multiple boards are selected
# we're adjusting the report title
# If 'All Boards' is selected all board IDs are concatenated into a
# single string
#----------------------------------------------------------------------
# Selected single board or AllBoards entry
if not type(boardIds) == type([]):
    if boardIds.find(',') > 0:
        reportTitle = 'PDQ Board Invitation History for All Boards'
        boardIds = boardIds.split(',')  # convert to list
    else:
        boardId    = boardIds and int(boardIds) or None
        reportTitle = getBoardName(boardId)
# Selected multiple boards
else:
    reportTitle = "PDQ Board Invitation History"

#----------------------------------------------------------------------
# Select the list of board members (Lastname, Firstname) and their
# board affiliation.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
          SELECT q.doc_id, q.int_val AS PersonID, fn.value AS First,
                 ln.value AS Last, b.int_val AS BoardID,
                 o.value AS BoardName
            FROM query_term q
            JOIN query_term fn
              ON q.int_val = fn.doc_id
             AND fn.path   = '/Person/PersonNameInformation/GivenName'
            JOIN query_term ln
              ON q.int_val = ln.doc_id
             AND ln.path   = '/Person/PersonNameInformation/SurName'
            JOIN query_term b
              ON q.doc_id  = b.doc_id
             AND b.path    = '/PDQBoardMemberInfo/BoardMembershipDetails' +
                             '/BoardName/@cdr:ref'
            JOIN query_term o
              ON b.int_val = o.doc_id
             AND o.path    = '/Organization/OrganizationNameInformation'  +
                             '/OfficialName/Name'
           WHERE q.path    = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'
 -- and q.doc_id in (639551, 404154) -- 410773, 404154, 369926, 369860)
           ORDER BY ln.value, fn.value, o.value
""", timeout = 300)
    rows = cursor.fetchall()

    boardMembers = []
    lastMemberId = 0
    for row in rows:
        if row[0] == lastMemberId:
            boardMembers[len(boardMembers)-1][4].append([row[4], row[5]])
        else:
            boardMembers.append([row[0], row[1], row[2], row[3],
                                                       [[row[4], row[5]]]])
        lastMemberId = row[0]

except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

# ---------------------------------------------------------------
# Create the HTML Output Page
# ---------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'
                      'http://www.w3.org/TR/html4/loose.dtd'>
<html>
 <head>
  <title>PDQ Board Member History Report</title>
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
   I        { font-family: Arial, sans-serif; font-size: 12pt;
              font-style: normal; }
   span.SectionRef { text-decoration: underline; font-weight: bold; }

   .theader { background-color: #CFCFCF; }
   .name    { font-weight: bold;
              vertical-align: top; }
   .phone, .email, .fax, .cdrid
            { vertical-align: top; }
   .blank   { width: 100px; }
   .notcurrent { background-color: None; }  /* #BEBEBE; } */
   #main    { font-family: Arial, Helvetica, sans-serif;
              font-size: 12pt; }
  </style>
 </head>
 <body id="main">
"""

###         html += u"""
###         <table width='100%%'>
###           <td>%s<td>
###         </table>""" % unicode(response[0], 'utf-8')

# Identify which columns to print
# -------------------------------
columns = []
exclude = []
htmlCol = ''
# What needs to be excluded?
# --------------------------
if excludeCurrEd:
    exclude.append('Editorial Board')
if excludeCurrAd:
    exclude.append('Editorial Advisory Board')

# What needs to be displayed?
# ---------------------------
if dispBoardName:
    columns.append('BoardName')
    htmlCol += '    <th>Board Name</th>\n'
if dispAoE:
    columns.append('AoE')
    htmlCol += '    <th>Area of Expertise</th>\n'
if dispInvDate:
    columns.append('Invitation')
    htmlCol += '    <th>Invitation Date</th>\n'
if dispResponse:
    columns.append('Response')
    htmlCol += '    <th>Response to Invitation</th>\n'
if dispCurMember:
    columns.append('Current')
    htmlCol += '    <th>Current Member</th>\n'
if dispEndDate:
    columns.append('EndDate')
    htmlCol += '    <th>Termination End Date</th>\n'
if dispReason:
    columns.append('Termination')
    htmlCol += '    <th>Termination Reason</th>\n'
if blankCol:
    columns.append('BlankCol')
    htmlCol += '    <th>Blank</th>\n'

# Create the HTML table for the summary sheet
# -------------------------------------------
html += u"""\
   <table id="summary" cellspacing="0" cellpadding="5">
    <tr>
     <td id="hdg" colspan="%d">%s<br>
       <span style="font-size: 12pt">%s</span>
     </td>
    </tr>
""" % (len(columns) + 2, reportTitle, dateString)

html += u"""\
    <tr>
     <th>ID</th>
     <th>Name</th>
%s""" % htmlCol

html += u"""\
    </tr>"""

for boardMember in boardMembers:
    tableRow = makeRow(cursor, boardMember, boardIds, columns, exclude)
    html += u"%s" % tableRow

# for bmId, personID, first, last, bordId, boardName in rows:
#     boardMembers.append(BoardMember(docId, eic_start, eic_finish,
#                                                term_start, name))
html += u"""
  </table>
 </body>
</html>
"""

# The users don't want to display the country if it's the US.
# Since the address is build by a common address module we're
# better off removing it in the final HTML output
# ------------------------------------------------------------
cdrcgi.sendPage(html.replace('U.S.A.<br>', ''))
