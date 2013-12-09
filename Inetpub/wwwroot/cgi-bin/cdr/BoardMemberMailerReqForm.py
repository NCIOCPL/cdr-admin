#----------------------------------------------------------------------
#
# $Id$
#
# Request form for generating RTF letters to board members.
#
# BZIssue::1664
# BZIssue::4939
# JIRA::OCECDR-3679 - workaround for IE Javascript bug
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrpub, cdrcgi, re, string, cdrmailcommon, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
board     = fields and fields.getvalue("board") or None
letter    = fields and fields.getvalue("letter") or None
email     = fields and fields.getvalue("email") or None
members   = fields and fields.getlist("member") or []
title     = "CDR Administration"
section   = "PDQ Board Member Correspondence Mailers"
SUBMENU   = "Mailer Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'BoardMemberMailerReqForm.py'
header    = cdrcgi.header(title, title, section, script, buttons)

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
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrPublishing')
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Just for testing.
#----------------------------------------------------------------------
def showDocsAndRun(rows):
    if not rows:
        rows = []
    html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Protocol S&amp;P Doc List</title>
  <style type='text/css'>
   th,h2    { font-family: Arial, sans-serif; font-size: 11pt;
              text-align: center; font-weight: bold; }
   h1       { font-family: Arial, sans-serif; font-size: 12pt;
              text-align: center; font-weight: bold; }
   td       { font-family: Arial, sans-serif; font-size: 10pt; }
  </style>
 </head>
 <body>
  <h1>Protocol S&amp;P Doc List</h1>
  <h2>%d docs selected</h2>
  <br><br>
  <table border='1' cellspacing='0' cellpadding='1'>
   <tr>
    <th>Document</th>
    <th>Version</th>
   </tr>
""" % len(rows)
    for row in rows:
        html += """\
   <tr>
    <td align='center'>CDR%010d</td>
    <td align='center'>%d</td>
   </tr>
""" % (row[0], row[1])
    cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")

#----------------------------------------------------------------------
# Submit request if we have one.
#----------------------------------------------------------------------
boardError = "&nbsp;"
letterError = "&nbsp;"
if request == "Submit":

    # Reality check.
    if not board:
        boardError = "<span class='error'>Board selection is required</span>"
    if not letter:
        letterError = "<span class='error'>Letter selection is required</span>"

    if board and letter:
        board = int(board)
    
        # Find the publishing system control document.
        try:
            cursor = conn.cursor()
            cursor.execute("""\
            SELECT d.id
              FROM document d
              JOIN doc_type t
                ON t.id    = d.doc_type
             WHERE t.name  = 'PublishingSystem'
               AND d.title = 'Mailers'""")
            rows = cursor.fetchall()
        except cdrdb.Error, info:
            cdrcgi.bail('Database failure looking up control document: %s' %
                        info[1][0])
        if len(rows) < 1:
            cdrcgi.bail('Unable to find control document for Mailers')
        if len(rows) > 1:
            cdrcgi.bail('Multiple Mailer control documents found')
        ctrlDocId = rows[0][0]

        # Find the documents to be published.
        try:
            if not members or 'all' in members:
                cursor.execute("""\
    SELECT DISTINCT v.id, MAX(v.num)
               FROM doc_version v
               JOIN query_term q
                 ON q.doc_id = v.id
               JOIN document d
                 ON d.id = v.id
              WHERE q.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                           + '/BoardName/@cdr:ref'
                AND v.val_status = 'V'
                AND q.int_val = ?
                AND d.active_status = 'A'
           GROUP BY v.id""", board, timeout = 300)
                docList = cursor.fetchall()
            else:
                docList = []
                for member in members:
                    member = int(member)
                    cursor.execute("""\
            SELECT MAX(num)
              FROM doc_version
             WHERE id = ?
               AND val_status = 'V'""", member)
                    docList.append((member, cursor.fetchall()[0][0]))
        except cdrdb.Error, info:
            cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])
        #showDocsAndRun(docList)

        # Check to make sure we have at least one mailer to send out.
        docCount = len(docList)
        if docCount == 0:
            cdrcgi.bail ("No documents found")

        # Compose the docList results into a format that cdr.publish() wants
        #   e.g., id=25, version=3, then form: "CDR0000000025/3"
        docs = []
        for doc in docList:
            docs.append("CDR%010d/%d" % (doc[0], doc[1]))

        # Drop the job into the queue.
        subset = 'PDQ Board Member Correspondence Mailer'
        parms = (('Board', board),('Letter', letter))
        result = cdr.publish(credentials = session, pubSystem = 'Mailers',
                             pubSubset = subset, docList = docs,
                             allowNonPub = 'Y', email = email, parms = parms)

        # cdr.publish returns a tuple of job id + messages
        # If serious error, job id = None
        if not result[0] or int(result[0]) < 0:
            cdrcgi.bail("Unable to initiate publishing job:<br>%s" % result[1])

        jobId = int(result[0])

        # Log what happened
        msgs = ["Started correspondence mailer job - id = %d" % jobId,
                "                           Mailer type = %s" % subset,
                "               Number of docs selected = %d" % docCount]
        if docCount > 0:
            msgs.append("                             First doc = %s" %
                        docs[0])
        if docCount > 1:
            msgs.append("                            Second doc = %s" %
                        docs[1])
        cdr.logwrite (msgs, cdrmailcommon.LOGFILE)

        # Tell user how to get status
        header = cdrcgi.header(title, title, section, None, [])
        cdrcgi.sendPage(header + """\
    <H3>Job Number %d Submitted</H3>
    <B>
     <FONT COLOR='black'>Use
      <A HREF='%s/PubStatus.py?id=%d'>this link</A> to view job status.
     </FONT>
    </B>
   </FORM>
  </BODY>
 </HTML>
""" % (jobId, cdrcgi.BASE, jobId))

class Board:
    def __init__(self, id):
        self.id = id
        self.members = []
        cursor.execute("""\
    SELECT value
      FROM query_term
     WHERE path = '/Organization/OrganizationNameInformation'
                + '/OfficialName/Name'
       AND doc_id = ?""", id, timeout = 300)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("No name found for board %d" % id)
        self.name = rows[0][0]
        cursor.execute("""\
    SELECT value
      FROM query_term
     WHERE doc_id = ?
       AND path = '/Organization/OrganizationType'
       AND value IN ('PDQ Editorial Board', 'PDQ Advisory Board')""", id,
                       timeout = 300)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Can't find board type for '%s'" % self.name)
        if len(rows) > 1:
            cdrcgi.bail("Multiple board types found for '%s'" % self.name)
        if rows[0][0].upper() == 'PDQ EDITORIAL BOARD':
            self.boardType = 'editorial'
        else:
            self.boardType = 'advisory'
        
class BoardMember:
    def __init__(self, id, docTitle):
        self.id = id
        self.name = docTitle
        delim = docTitle.find(';')
        if delim != -1:
            self.name = docTitle[:delim]
        delim = self.name.find('(')
        if delim != -1:
            self.name = self.name[:delim]
        self.name = self.name.strip()

boards = {}
members = {}
cursor = conn.cursor()
cursor.execute("""\
    SELECT DISTINCT q.doc_id, q.int_val, d.title
               FROM query_term q
               JOIN document d
                 ON q.doc_id = d.id
               JOIN doc_version v
                 ON v.id = d.id
              WHERE path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                         + '/BoardName/@cdr:ref'
                AND v.val_status = 'V'
                AND d.active_status = 'A'""", timeout = 300)
rows = cursor.fetchall()
for memberId, boardId, docTitle in rows:
    if boardId not in boards:
        boards[boardId] = Board(boardId)
    if memberId not in members:
        members[memberId] = BoardMember(memberId, docTitle)
    board = boards[boardId]
    member = members[memberId]
    board.members.append(member)

#----------------------------------------------------------------------
# Generate a picklist for the PDQ Editorial Boards.
#----------------------------------------------------------------------
def makeBoardList(boards):
    keys = boards.keys()
    keys.sort(lambda a,b: cmp(boards[a].name, boards[b].name))
    html = u"""\
      <select id='board' name='board' style='width:500px'
              onchange='boardChange();'>
       <option value='' selected='1'>Choose One</option>
"""
    for key in keys:
        board = boards[key]
        html += """\
       <option value='%d'>%s &nbsp;</option>
""" % (board.id, board.name)
    return html + """\
      </select>
"""

#----------------------------------------------------------------------
# Create JavaScript for a list of Board objects.
#----------------------------------------------------------------------
def makeBoardObjects():
    objects = """\
   var boards = {"""
    outerComma = ''
    for key in boards:
        board = boards[key]
        board.members.sort(lambda a,b: cmp(a.name, b.name))
        objects += """%s
       '%s': new Board('%s', '%s', [""" % (outerComma, board.id,
                                           board.id, board.boardType)
        innerComma = ''
        for member in board.members:
            objects += """%s
           new Option('%s', '%s')""" % (innerComma,
                                        member.name.replace("'", "\\'"),
                                        member.id)
            innerComma = ','
        objects += """
       ])"""
        outerComma = ','
    return objects + """
   };"""
        
#----------------------------------------------------------------------
# Put up the form if we don't have a request yet.
#----------------------------------------------------------------------
header = cdrcgi.header(title, title, section, script, buttons,
                       stylesheet = """\
 <style type='text/css'>
   ul { margin-left: 20pt }
   h2 { font-size: 14pt; font-family:Arial; color:Navy }
   h3 { font-size: 13pt; font-family:Arial; color:black; font-weight:bold }
   li, span.r { 
        font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:normal 
   }
   b, th {  font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:bold 
   }
   .error { color: red; }
  </style>
  <script language='JavaScript'>
   function submitRequest() {
       if (!document.forms[0].board.value) {
           alert('You must select a board!');
           if (document.forms[0].board.focus)
               document.forms[0].board.focus();
           return;
       }
       if (!document.forms[0].letter.value) {
           alert('OK, which letter should we send out?');
           if (document.forms[0].letter.focus)
               document.forms[0].letter.focus();
           return;
       }
       document.forms[0].action = 'DumpParams.py';
       document.forms[0].Request.value = 'Submit';
       document.forms[0].method = 'POST';
       document.forms[0].submit();
   }
   function Board(id, boardType, members) {
       this.id        = id;
       this.boardType = boardType;
       this.members   = members;
   }
%s
   var letters = {
       'advisory': [
           new Option('Advisory Board Invitation Letter', 'adv-invitation'),
           new Option('Advisory Board Review Letter for Email',
                      'adv-summ-email'),
           new Option('Advisory Board Review Letter for FedEx',
                      'adv-summ-fedex'),
           new Option('Advisory Board Still Interested Letter',
                      'adv-interested'),
           new Option('Advisory Board Thank You Letter',  'adv-thankyou'),
           new Option('Advisory Board Big Thank You Letter',
                      'adv-big-thankyou')
       ],
       'editorial': [
           new Option('Editorial Board Invitation Letter', 'ed-invitation'),
           new Option('Editorial Board Welcome Letter',    'ed-welcome'),
           new Option('Editorial Board Short Welcome Letter',
                      'ed-short-welcome'),
           new Option('Editorial Board Renewal Letter',    'ed-renewal'),
           new Option('Editorial Board Editor-in-Chief Renewal Letter',
                      'ed-ec-renewal'),
           new Option('Editorial Board Goodbye Letter',    'ed-goodbye'), 
           new Option('Editorial Board Goodbye For Good Letter',
                      'ed-goodbye-forever'),
           new Option('Editorial Board Thank You Letter',  'ed-thankyou'),
           new Option('Editorial Board Comprehensive Review Letter',
                      'ed-comp-review')
      ]
   };
       
   function boardChange() {
       var boardElem        = document.forms[0].board;
       var letterElem       = document.forms[0].letter;
       var memberElem       = document.forms[0].member;
       var boardOptions     = boardElem.options;
       var letterOptions    = letterElem.options;
       var memberOptions    = memberElem.options;
       letterOptions.length = memberOptions.length = 0;
       letterOptions[0]     = new Option('Choose One', '', true, true);
       memberOptions[0]     = new Option('All Members of Board', 'all',
                                         true, true);
       var boardIndex       = boardElem.selectedIndex;
       if (boardIndex == -1)
           return;
       var boardId          = boardOptions[boardIndex].value;
       if (!boardId)
           return;
       var board            = boards[boardId];
       var lettersForBoard  = letters[board.boardType];
       for (var i = 0; i < lettersForBoard.length; ++i) {
           var letter       = lettersForBoard[i];
           letter.selected  = false;
           letterOptions[letterOptions.length] = letter;
       }
       var membersForBoard  = board.members;
       for (var i = 0; i < membersForBoard.length; ++i) {
           var member       = membersForBoard[i];
           member.selected  = false;
           memberOptions[memberOptions.length] = member;
       }
   }
  </script>
 """ % makeBoardObjects())
form = """\
   <h2>PDQ Board Member Correspondence Mailers</h2>
   <ul>
    <li>
     Select a PDQ Board from the first picklist below.  Then select
     which letter should be sent and one or more individuals from the
     list of board members (or prospective board members).
     It may take a minute to select documents to be included in the mailing.
     Please be patient.
    </li>
    <li>
     To receive email notification when the job is completed, enter your 
     email address.
    </li>
    <li>
     Click Submit to start the mailer job.
    </li>
   </ul>
   <table border='0' cellpadding='1' cellspacing='0'>
    <tr>
     <th align='right'>Select Board:&nbsp;</th>
     <td>
%s
     </td>
     <td>%s</td>
    </tr>
    <tr>
     <th align='right'>Select Letter:&nbsp;</th>
     <td>
      <select id='letter' name='letter' style='width:500px'>
       <option value='' selected>Choose One</option>
      </select>
     </td>
     <td>%s</td>
    </tr>
    <tr>
     <th align='right'>Select Board Member(s):&nbsp;<br></th>
     <td>
      <select id='member' name='member' style='width:500px' multiple size=10>
       <option value='all' selected>All Members of Board</option>
      </select>
     </td>
     <td>&nbsp;</td>
    </tr>
    <tr>
     <th align='right'>Email Address:&nbsp;</th>
     <td><input name='email' style='width: 500px' value='%s'></td>
     <td>&nbsp;</td>
    </tr>
    <tr>
     <td align='center' colspan='2'>
      <br><br>
      <input type='submit' name='Request' value='Submit'>
     </td>
     <td>&nbsp;</td>
    </tr>
   </table>
   <input type='hidden' name='%s' value='%s'>
  </form>
 </body>
</html>
""" % (makeBoardList(boards), boardError, letterError, cdr.getEmail(session),
       cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form)
