import cgi, cdr, cdrdb, cdrpub, cdrcgi, re, string, cdrmailcommon, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
type     = fields and fields.getvalue("Type") or None
board     = fields and fields.getvalue("Board") or None
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
    
class MailtToList:
    def __init__(self, memberId):
        self.memberId = memberId
        self.summary = []
    
#----------------------------------------------------------------------
# Submit request if we have one.
#----------------------------------------------------------------------
Mailers = {}
if request == "Submit":
#    if check and check.count() > 1:
#        cdrcgi.bail(check)
#        for checkItem in check:
#            strItem = "%s" % item
#        splitTxt = str.split("-")
#        if (splitTxt.count() > 1) :
#            if ( type == "Member" ):
#                memberID = splitTxt[0]
#                summaryID = splitTxt[1]
#            else:
#                memberID = splitTxt[1]
#                summaryID = splitTxt[0]
#            if memberId not in Mailers:
#                Mailers[memberId] = MailToList(memberId)
#            member = Mailers[memberId]
#            if summaryID not in member.summary
#                 member.summary.append(summaryID)
				 
     cdrcgi.bail("To do")			 

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
          WHERE summary_board.int_val = %s""" % board
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
          WHERE summary_board.int_val = %s""" % (members,board)
          
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
    html = """&nbsp;&nbsp;<input type="checkbox" name="check" value="%d" CHECKED onclick="radioClick(this);">""" % id
    html += "<b>" + name + "</b><br>"
    
    for member in members:
       html += """&nbsp;&nbsp;&nbsp;&nbsp;<input type="checkbox" name="check" value="%d-%d" CHECKED>%s</input><br>""" % (id,member.id,member.name)
        
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
  </form>
 </body>
</html>
""" % (section, buildTable(selMembers,selSummaries),cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form)