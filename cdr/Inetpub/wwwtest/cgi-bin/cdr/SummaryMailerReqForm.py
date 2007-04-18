#----------------------------------------------------------------------
#
# $Id: SummaryMailerReqForm.py,v 1.10 2007-04-18 11:31:41 kidderc Exp $
#
# Request form for generating PDQ Editorial Board Members Mailing.
#
# $Log: not supported by cvs2svn $
# Revision 1.9  2007/04/12 12:44:29  kidderc
# 3132. Add ability to send mailers based on person or document.
#
# Revision 1.7  2007/04/06 14:58:01  bkline
# Removed unused modules from import statement in preparate for turning
# over enhancement of this script to Charlie Kidder.
#
# Revision 1.6  2005/05/13 22:41:04  venglisc
# Modified to pre-populate the email input field with the session owners
# email address. (Bug 1664)
#
# Revision 1.5  2002/11/13 20:35:25  bkline
# Ready for user testing.
#
# Revision 1.4  2002/11/07 12:51:25  bkline
# Fixed variable name (changed mailType to subset).
#
# Revision 1.3  2002/10/24 20:02:03  bkline
# Expanded script to handle both board types.
#
# Revision 1.2  2002/02/21 22:34:00  bkline
# Added navigation buttons.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrpub, cdrcgi, re, string, cdrmailcommon, sys, socket

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
board     = fields and fields.getvalue("board") or None
email     = fields and fields.getvalue("email") or None
boardType = fields and fields.getvalue("BoardType") or "Editorial"
maxMails  = fields and fields.getvalue("maxMails") or 'No limit'
members   = fields and fields.getlist("member") or []
summaries   = fields and fields.getlist("summary") or []
RadioSelect = fields and fields.getvalue("RadioSelect") or 'All'
title     = "CDR Administration"
section   = "PDQ %s Board Members Mailer Request Form" % boardType
SUBMENU   = "Mailer Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'SummaryMailerReqForm.py'
header    = cdrcgi.header(title, title, section, script, buttons)
if maxMails == 'No limit': maxDocs = sys.maxint
else:
    try:
        maxDocs = int(maxMails)
    except:
        cdrcgi.bail("Invalid value for maxMails: %s" % maxMails)
if maxDocs < 1:
    cdrcgi.bail("Invalid value for maxMails: %s" % maxMails)

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

boardError = "&nbsp;"

#----------------------------------------------------------------------
# Check to make sure all inputs ar valid and there's a publishing
# control document.
#----------------------------------------------------------------------
def doRealityCheck():
    # Reality check.
    if not board:
        cdrcgi.bail('You must select a board')

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
    
#----------------------------------------------------------------------
# Send All mailers to all board members. Default selection.
#----------------------------------------------------------------------
def sendToAll():
    # Find the documents to be published.
    sBoard = ""
    sQuery = """\
            SELECT DISTINCT TOP %d d.id, MAX(v.num)
                       FROM doc_version v
                       JOIN document d
                         ON d.id = v.id
                       JOIN query_term q
                         ON q.doc_id = d.id
                       JOIN query_term a
                         ON a.doc_id = d.id
                      WHERE d.active_status = 'A'
                        AND v.publishable = 'Y'
                        AND q.value = ?
                        AND q.path = '/Summary/SummaryMetaData/PDQBoard'
                                   + '/Board/@cdr:ref'
                        AND a.path = '/Summary/SummaryMetaData/SummaryAudience'
                        AND a.value = 'Health professionals'
                    GROUP BY d.id""" %  (maxDocs,)
		
    try:
        sBoard = """CDR%010d""" % (int(board),)
        cursor = conn.cursor()
        cursor.execute(sQuery,sBoard,timeout = 300)
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

    # Check to make sure we have at least one mailer to send out.
    docCount = len(docList)
    if docCount == 0:
        cdrcgi.bail ("No documents found")

    # Compose the docList results into a format that cdr.publish() wants
    #   e.g., id=25, version=3, then form: "CDR0000000025/3"
    docs = []
    
    for doc in docList:
        sDoc = "CDR%010d/%d" % (doc[0], doc[1])
        docs.append(sDoc)
        
    # Drop the job into the queue.
    subset = 'Summary-PDQ %s Board' % boardType
    parms = (('Board', sBoard),('Person', ''))
    result = cdr.publish(credentials = session, pubSystem = 'Mailers',
                         pubSubset = subset, docList = docs,
                         allowNonPub = 'Y', email = email, parms = parms)

    # cdr.publish returns a tuple of job id + messages
    # If serious error, job id = None
    if not result[0] or int(result[0]) < 0:
        cdrcgi.bail("Unable to initiate publishing job:<br>%s" % result[1])

    jobId = int(result[0])

    # Log what happened
    msgs = ["Started directory mailer job - id = %d" % jobId,
            "                      Mailer type = %s" % subset,
            "          Number of docs selected = %d" % docCount]
    if docCount > 0:
        msgs.append ("                        First doc = %s" % docs[0])
    if docCount > 1:
        msgs.append ("                       Second doc = %s" % docs[1])
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

def selectIndividualDocuments(type):
    sUrl = "Location:http://"
    sUrl += socket.gethostname()
    sUrl += ".nci.nih.gov"
    sUrl += cdrcgi.BASE
    sUrl += "/"
    sUrl += "SummaryMailerReqFormInd.py?"
    sArgs = cdrcgi.SESSION 
    sArgs += "="
    sArgs += session
    sArgs += "&"
    sArgs += "Board="
    sArgs += board
    sArgs += "&"
    if email:
        sArgs += "EMail="
        sArgs += email
        sArgs += "&"
    sArgs += "Type=" + type + "&"
    if not members or 'all' in members:
        sArgs += "Members=All" 
    else:
        sArgs += "Members="
        for member in members:
            sArgs += "%d" % int(member)
            sArgs += ","
        sArgs = sArgs[0:len(sArgs)-1]
    sUrl += sArgs
    print sUrl

#----------------------------------------------------------------------
# Submit request if we have one.
#----------------------------------------------------------------------
if request == "Submit":
    doRealityCheck()
    if ( RadioSelect == 'All' ):
        sendToAll()
    elif ( RadioSelect == 'Member' ):
        selectIndividualDocuments('Member')
    elif ( RadioSelect == 'Summary' ):
        selectIndividualDocuments('Summary')
    
#----------------------------------------------------------------------
# Board Class
#----------------------------------------------------------------------
class Board:
    def __init__(self, id):
        self.id = id
        self.members = []
        self.summaries = []
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
        
class BoardSummary:
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
summaries = {}
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
                AND d.active_status = 'A'
                AND q.int_val in ( (select DISTINCT ind.id FROM document ind
                       JOIN query_term inq
                         ON inq.doc_id = ind.id
                      WHERE inq.path = '/Organization/OrganizationType'
                        AND inq.value = 'PDQ %s Board') )""" % boardType)
                                                
rows = cursor.fetchall()
for memberId, boardId, docTitle in rows:
    if boardId not in boards:
        boards[boardId] = Board(boardId)
    if memberId not in members:
        members[memberId] = BoardMember(memberId, docTitle)
    board = boards[boardId]
    member = members[memberId]
    board.members.append(member)
    
sQuery = """\
            SELECT DISTINCT d.id, MAX(v.num), q.int_val, d.title
                       FROM doc_version v
                       JOIN document d
                         ON d.id = v.id
                       JOIN query_term q
                         ON q.doc_id = d.id
                       JOIN query_term a
                         ON a.doc_id = d.id
                      WHERE d.active_status = 'A'
                        AND v.publishable = 'Y'
                        AND q.int_val in ( (select DISTINCT ind.id FROM document ind
                                            JOIN query_term inq
                                            ON inq.doc_id = ind.id
                                            WHERE inq.path = '/Organization/OrganizationType'
                                            AND inq.value = 'PDQ %s Board') )
                        AND q.path = '/Summary/SummaryMetaData/PDQBoard'
                                   + '/Board/@cdr:ref'
                        AND a.path = '/Summary/SummaryMetaData/SummaryAudience'
                        AND a.value = 'Health professionals'
                    GROUP BY d.id,d.title,q.int_val""" %  (boardType,)
		
try:
    cursor.execute(sQuery)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])
        
for summaryId, docVerNum, boardId, docTitle in rows:
    if boardId not in boards:
        boards[boardId] = Board(boardId)
    if summaryId not in summaries:
        summaries[summaryId] = BoardSummary(summaryId, docTitle)
    board = boards[boardId]
    summary = summaries[summaryId]
    board.summaries.append(summary)

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
        board.summaries.sort(lambda a,b: cmp(a.name, b.name))
        objects += """%s
       '%s': new Board('%s', '%s', [""" % (outerComma, board.id,
                                           board.id, board.boardType)
        innerComma = ''
    # Add Board members
        for member in board.members:
            objects += """%s
           new Option('%s', '%s')""" % (innerComma,
                                        member.name.replace("'", "\\'"),
                                        member.id)
            innerComma = ','
        objects += """],["""
        innerComma = ''
     # add summaries
        for summary in board.summaries:
            objects += """%s
           new Option('%s', '%s')""" % (innerComma,
                                        summary.name.replace("'", "\\'"),
                                        summary.id)
            innerComma = ','
        innerComma = ''
        objects += """])"""
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
   li, span.r, p, h4 
   { 
        font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:normal 
   }
   b, th 
   {  font-size: 11pt; font-family:'Arial'; color:black;
        margin-bottom: 10pt; font-weight:bold 
   }
   .error { color: red; }
  </style>
  <script language='JavaScript'>
   function submitRequest() 
   {
       if (!document.forms[0].board.value)
       {
           alert('You must select a board!');
           if (document.forms[0].board.focus)
               document.forms[0].board.focus();
           return;
       }
       
       document.forms[0].action = 'DumpParams.py';
       document.forms[0].Request.value = 'Submit';
       document.forms[0].method = 'POST';
       document.forms[0].submit();
   }
   
   function Board(id, boardType, members, summaries) 
   {
       this.id        = id;
       this.boardType = boardType;
       this.members   = members;
       this.summaries = summaries;
   }
%s

   function radioClicked(whichOne)
   {
       var elem = document.getElementById('ListboxTitle');
       if (whichOne == 'Member')
            elem.innerHTML = 'Select Board Member(s):&nbsp;';
       else if (whichOne == 'Summary')
            elem.innerHTML = 'Select Summaries:&nbsp;';
       else
            elem.innerHTML = '';
       boardChange();
   }
       
   function boardChange()
   {
		var radioValue = "All";
		for (i=document.forms[0].RadioSelect.length-1; i > -1; i--)
			if (document.forms[0].RadioSelect[i].checked)
			{
				radioValue = document.forms[0].RadioSelect[i].value;
				i = -1;
			}
		var boardElem        = document.forms[0].board;
		var memberElem       = document.forms[0].member;
		var boardOptions     = boardElem.options;
		var memberOptions    = memberElem.options;
		memberOptions.length = 0;
		if ( radioValue == "Member" )
			memberOptions[0]     = new Option('All Members of Board', 'all',
											true, true);
		else if ( radioValue == "Summary" )
			memberOptions[0]     = new Option('All Summaries for Board', 'all',
											true, true);
		var boardIndex       = boardElem.selectedIndex;
		if (boardIndex == -1)
			return;
		var boardId          = boardOptions[boardIndex].value;
		if (!boardId)
			return;
		var board            = boards[boardId];	
		var itemsForBoard  = board.members;
		if ( radioValue == "Member" )
			itemsForBoard  = board.members;
		else if ( radioValue == "Summary" )
			itemsForBoard  = board.summaries;
		if ( radioValue != "All" )	
			for (var i = 0; i < itemsForBoard.length; ++i)
			{
				var item       = itemsForBoard[i];
				item.selected  = false;
				memberOptions[memberOptions.length] = item;
			}
   }
  </script>
 """ % makeBoardObjects())
form = """\
   <h2>%s</h2>
   <ul>
    <li>
     <p>
     To generate mailers for a %s board, first, select the board's name from
     the picklist below. 
     </p><p>
     <b>If you check 'Send All Summaries to all Board Members'</b>, all summaries will be sent to all appropriate board members.
     </p><p>
     If you want to select specific summaries to send to specific board members check one of the other two radio buttons.
     </p><p>
     <b>If you check 'Select by Summary'</b>,
     You can select from the list below the radio buttons, the specific summaries you want to include in the mailer. You will be sent to a new page that contains
     the members who can receive the mailer, grouped by summary.
     </p><p>
     <b>If you check 'Select by Board Member'</b>,
     You can select from the list below the radio buttons, the specific members you want to include in the mailer. You will be sent to a new page that contains
     the summaries that can be sent, grouped by Board Member.
     </p><p>
     It may take a minute to select documents to be included in the mailing.
     Please be patient.
     If you want to, you can limit the number of summary documents for
     which mailers will be generated in a given job, by entering a 
     maximum number.
     </p>
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
     <td>
     </td>
     <td>
     <h4>
     <input type="radio" name="RadioSelect" value="All" checked onClick="radioClicked('All')">Send All Summaries to all Board Members<br>
     <input type="radio" name="RadioSelect" value="Summary" onClick="radioClicked('Summary')">Select by Summary<br>
     <input type="radio" name="RadioSelect" value="Member" onClick="radioClicked('Member')">Select by Board Member<br>
     </h4>
     </td>
    </tr>
    <tr>
     <th align='right' id='ListboxTitle'><br></th>
     <td>
      <select id='member' name='member' style='width:500px' multiple size=10>
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
    <th align='right'>Maximum number of documents:&nbsp;</th>
    <td>
    <input type='text' name='maxMails' size='12' value='No limit' />
    </td>
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
""" % (section, boardType,makeBoardList(boards), boardError, cdr.getEmail(session),
       cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form)

 