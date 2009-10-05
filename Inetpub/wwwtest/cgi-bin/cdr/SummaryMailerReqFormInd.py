import cgi, cdr, cdrdb, cdrpub, cdrcgi, re, string, cdrmailcommon, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
type     = fields and fields.getvalue("Type") or None
board     = fields and fields.getvalue("Board") or None
boardname     = fields and fields.getvalue("BoardName") or None
email     = fields and fields.getvalue("EMail") or None
members   = fields and fields.getvalue("Members") or None
check     = fields and fields.getlist("check") or []
title     = "CDR Administration"
#section   = "%s Board Mailer Request Form" % board
SUBMENU   = "Mailer Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'SummaryMailerReqFormInd.py'
#header    = cdrcgi.header(title, title, section, script, buttons)

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
    
class SummaryWithVer:
    def __init__(self, Id, Ver):
        self.summaryId = Id
        self.ver = Ver
    
class MailToList:
    def __init__(self, memberId):
        self.memberId = memberId
        self.summaries = []
    
#----------------------------------------------------------------------
# Submit request if we have one.
#----------------------------------------------------------------------
Mailers = {}
if request == "Submit":
    try:
        # package up the checked mailers, grouped by member    
        for checkItem in check:
            strItem = "%s" % checkItem
            if (strItem.count("-") > 0 ):
                splitTxt = strItem.split("-")
                if ( type == "Member" ):
                    memberID = splitTxt[0]
                    summaryID = splitTxt[1]
                else:
                    memberID = splitTxt[1]
                    summaryID = splitTxt[0]
                if memberID not in Mailers:
                    Mailers[memberID] = MailToList(memberID)
                member = Mailers[memberID]
                if summaryID not in member.summaries:
                    summary = SummaryWithVer(summaryID,"1")
                    member.summaries.append(summary)
    except Exception, e:
           cdrcgi.bail("oops: %s" % e)
    
    try:
        sIn = ""
        for memberID in Mailers:
            member = Mailers[memberID]
            for summary in member.summaries:
                sIn += summary.summaryId
                sIn += ","
        sIn = sIn[0:len(sIn)-1]
    except Exception, e:
           cdrcgi.bail("oops: %s" % e)

    # Get the latest version number for each document
    sBoard = ""
    sQuery = """\
            SELECT DISTINCT d.id, MAX(v.num)
                       FROM doc_version v
                       JOIN document d
                         ON d.id = v.id
                       JOIN query_term q
                         ON q.doc_id = d.id
                       JOIN query_term a
                         ON a.doc_id = d.id
                      WHERE d.active_status = 'A'
                        AND v.publishable = 'Y'
                        AND q.path = '/Summary/SummaryMetaData/PDQBoard'
                                   + '/Board/@cdr:ref'
                        AND a.path = '/Summary/SummaryMetaData/SummaryAudience'
                        AND a.value = 'Health professionals'
                        AND d.id in (%s)
                    GROUP BY d.id""" % sIn

    try:
        sBoard = """CDR%010d""" % (int(board),)
        cursor = conn.cursor()
        cursor.execute(sQuery,timeout = 300)
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s<br>Query = %s" % (info[1][0],sQuery))

    # Check to make sure we have at least one mailer to send out.
    docCount = len(docList)
    if docCount == 0:
        cdrcgi.bail ("No documents found")

    docs = []
    for doc in docList:
        sDoc = "CDR%010d/%d" % (doc[0], doc[1])
        docs.append(sDoc)
        for memberID in Mailers:
            member = Mailers[memberID]
            for summary in member.summaries:
                if (int(summary.summaryId) == int(doc[0])):
                    summary.ver = doc[1]

    # Compose the docList results into a format that cdr.publish() wants
    #   e.g., id=25, version=3, then form: "CDR0000000025/3"
    sPerson = ""
    for memberID in Mailers:
        member = Mailers[memberID]
        sPerson += "%d" % int(member.memberId)
        sPerson += " ["
        for summary in member.summaries:
            #sPerson += "CDR%010d/%d " % (int(summary.summaryId), int(summary.ver))
            sPerson += "%d/%d " % (int(summary.summaryId), int(summary.ver))
        sPerson = sPerson[0:len(sPerson)-1]
        sPerson += "] "
        
    # Drop the job into the queue.
    subset = 'Summary-PDQ Editorial Board'
    parms = (('Board', sBoard),('Person', sPerson))
    result = cdr.publish(credentials = session, pubSystem = 'Mailers',
                         pubSubset = subset, docList = docs,
                         allowNonPub = 'Y', email = email, parms = parms)

    # cdr.publish returns a tuple of job id + messages
    # If serious error, job id = None
    if not result[0] or int(result[0]) < 0:
        cdrcgi.bail("Unable to initiate publishing job:<br>%s<br>Person = %s, len(Person) = %d" % (result[1],sPerson,len(sPerson)))

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
    section   = "%s Board Mailer Request Form" % boardname
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

class Member:
    def __init__(self, id, docTitle):
        self.summaries = []
        self.id = id
        self.name = docTitle
        delim = docTitle.find(';')
        if delim != -1:
            self.name = docTitle[:delim]
        delim = self.name.find('(')
        if delim != -1:
            self.name = self.name[:delim]
        self.name = self.name.strip()
        
class Summary:
    def __init__(self, id, docTitle):
        self.members = []
        self.id = id
        self.ver = 0
        self.name = docTitle
        delim = docTitle.find(';')
        if delim != -1:
            self.name = docTitle[:delim]
        delim = self.name.find('(')
        if delim != -1:
            self.name = self.name[:delim]
        self.name = self.name.strip()


selMembers = {}
selSummaries = {}

cursor = conn.cursor()

sQuery = ""
if ( type == "Member" ):
    # Get a list of all members
    if (members == 'All' ):
        sQuery = """\
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
                AND q.int_val = %s""" % board
    else:
        sQuery = """\
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
                AND q.doc_id in (%s)""" % members
                                                
    cursor.execute(sQuery)
    rows = cursor.fetchall()
    for memberId, boardId, docTitle in rows:
        if memberId not in selMembers:
           selMembers[memberId] = Member(memberId, docTitle)
           
    #get the documents for each member
    sIn = "AND board_member.id in ("
    sIn += "Select int_val from query_term q where q.path = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref' and doc_id in ("
    first = 1
    for id in selMembers:
        if not first:
            sIn += ","
        sIn += "%d" % id
        first = 0
    sIn += "))"
    
    selMembers.clear()
    
    sQuery = """\
          SELECT DISTINCT board_member.id,board_member.title,summary.doc_id, summary.value
           FROM document board_member
           JOIN query_term summary_board_member
             ON summary_board_member.int_val = board_member.id
            AND summary_board_member.path = '/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref'
           JOIN query_term summary_board
             ON summary_board.doc_id = summary_board_member.doc_id
            AND summary_board.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
            AND LEFT(summary_board.node_loc, 8) = 
                LEFT(summary_board_member.node_loc, 8)
           JOIN query_term summary
             ON summary.doc_id = summary_board.doc_id
           JOIN query_term audience
             ON audience.doc_id = summary.doc_id
            AND audience.path = '/Summary/SummaryMetaData/SummaryAudience'
            AND audience.value = 'Health professionals'
            AND summary.path = '/Summary/SummaryTitle'
            AND summary.doc_id in (select id from document where active_status = 'A') 
          WHERE summary_board.int_val = %s %s order by summary.value""" % (board,sIn)
          
    #cdrcgi.bail(sQuery)
          
    cursor.execute(sQuery)
    rows = cursor.fetchall()
    #sTmp = ""
    for memberId, memberTitle, summaryId, docTitle in rows:
       #sTmp += "memberId = %d  memberTitle = %s summaryID = %d docTitle = %s     " % (memberId, memberTitle, summaryId, docTitle)
       if memberId not in selMembers:
           selMembers[memberId] = Member(memberId,memberTitle)
       member = selMembers[memberId]
       if summaryId not in member.summaries:
           summary = Summary(summaryId, docTitle)
           member.summaries.append(summary)
           
    #cdrcgi.bail(sTmp)

else:
    if (members == 'All' ):
        sQuery = """\
          SELECT DISTINCT board_member.id,board_member.title,summary.doc_id, summary.value
           FROM document board_member
           JOIN query_term summary_board_member
             ON summary_board_member.int_val = board_member.id
            AND summary_board_member.path = '/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref'
           JOIN query_term summary_board
             ON summary_board.doc_id = summary_board_member.doc_id
            AND summary_board.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
            AND LEFT(summary_board.node_loc, 8) = 
                LEFT(summary_board_member.node_loc, 8)
           JOIN query_term summary
             ON summary.doc_id = summary_board.doc_id
           JOIN query_term audience
             ON audience.doc_id = summary.doc_id
            AND audience.path = '/Summary/SummaryMetaData/SummaryAudience'
            AND audience.value = 'Health professionals'  
            AND summary.path = '/Summary/SummaryTitle'
            AND summary.doc_id in (select id from document where active_status = 'A') 
          WHERE summary_board.int_val = %s order by board_member.title""" % board
    else:
        sQuery = """\
          SELECT DISTINCT board_member.id,board_member.title,summary.doc_id, summary.value
           FROM document board_member
           JOIN query_term summary_board_member
             ON summary_board_member.int_val = board_member.id
            AND summary_board_member.path = '/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref'
           JOIN query_term summary_board
             ON summary_board.doc_id = summary_board_member.doc_id
            AND summary_board.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
            AND LEFT(summary_board.node_loc, 8) = 
                LEFT(summary_board_member.node_loc, 8)
           JOIN query_term summary
             ON summary.doc_id = summary_board.doc_id
           JOIN query_term audience
             ON audience.doc_id = summary.doc_id
            AND audience.path = '/Summary/SummaryMetaData/SummaryAudience'
            AND audience.value = 'Health professionals'  
            AND summary.path = '/Summary/SummaryTitle'
            AND summary.doc_id in (%s) 
          WHERE summary_board.int_val = %s order by board_member.title""" % (members,board)
          
    cursor.execute(sQuery)
    rows = cursor.fetchall()
    #sTmp = ""
    for memberId, memberTitle, summaryId, docTitle in rows:
       #sTmp += "memberId = %d  memberTitle = %s summaryID = %d docTitle = %s     " % (memberId, memberTitle, summaryId, docTitle)
       if summaryId not in selSummaries:
           #sTmp += "summary Id = %d doc Title = %s " % (summaryId,docTitle)
           selSummaries[summaryId] = Summary(summaryId,docTitle)
       summary = selSummaries[summaryId]
       if memberId not in summary.members:
           member = Member(memberId, memberTitle)
           #sTmp += "member Id = %d member Title = %s " % (memberId,memberTitle)
           summary.members.append(member)

    #cdrcgi.bail(sTmp)
           
    #cdrcgi.bail("session = %s board = %s type = %s email = %s members = %s" % (session,board,type,email,members))
    
def buildIndividualTable(id,name,members):
    html = """&nbsp;&nbsp;&nbsp;&nbsp;<input type="checkbox" name="check" value="%d" CHECKED onclick="radioClick(this);">""" % id
    html += "<b>" + name + "</b><br>"
    
    for member in members:
       html += """&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<input type="checkbox" name="check" value="%d-%d" CHECKED>%s</input><br>""" % (id,member.id,member.name)
        
    return html

def buildTable(selMembers,selSummaries):
    html = """<input type="checkbox" name="check" value="All" CHECKED onclick="radioClick(this);"><b>All</b></input><br><br>"""
    if ( type == "Member" ):
        keys = selMembers.keys()
        keys.sort(lambda a,b: cmp(selMembers[a].name, selMembers[b].name))
        for key in keys:
            member = selMembers[key]
            html += buildIndividualTable(member.id,member.name,member.summaries)
            html += "<br><br>"
    else:
        keys = selSummaries.keys()
        keys.sort(lambda a,b: cmp(selSummaries[a].name, selSummaries[b].name))
        for key in keys:
            summary = selSummaries[key]
            html += buildIndividualTable(summary.id,summary.name,summary.members)
            html += "<br><br>"
    return html    
    
#----------------------------------------------------------------------
# Put up the form if we don't have a request yet.
#----------------------------------------------------------------------
sQuery = """\
    SELECT value
      FROM query_term
     WHERE path = '/Organization/OrganizationNameInformation'
                + '/OfficialName/Name'
       AND doc_id = %s""" % board
       
cursor.execute(sQuery)
rows = cursor.fetchall()
if not rows:
    cdrcgi.bail("No name found for board %d" % board)
boardname = rows[0][0]
        
section   = "%s Board Mailer Request Form" % boardname
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
       document.forms[0].action = 'DumpParams.py';
       document.forms[0].Request.value = 'Submit';
       document.forms[0].method = 'POST';
       document.forms[0].submit();
   }
   
   function radioClick(theCheckBox)
   {
       value = theCheckBox.value;
       checked = theCheckBox.checked;
                   
       for (i = 0; i < document.forms[0].check.length; i++)
       {
            split_string = document.forms[0].check[i].value.split("-");
            thisValue = split_string[0];
            if ( (thisValue == value) || (value == "All") )
                document.forms[0].check[i].checked = checked;
       }
   }
  </script>
 """)
form = """\
   <h2>%s</h2>
   %s
   <input type='hidden' name='%s' value='%s'>
   <input type='hidden' name='Type' value='%s'>
   <input type='hidden' name='Board' value='%s'>
   <input type='hidden' name='EMail' value='%s'>
   <input type='hidden' name='BoardName' value='%s'>
  </form>
 </body>
</html>
""" % (section, buildTable(selMembers,selSummaries),cdrcgi.SESSION, session,type,board,email,boardname)
cdrcgi.sendPage(header + form)