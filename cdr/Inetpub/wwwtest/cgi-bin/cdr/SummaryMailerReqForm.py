#----------------------------------------------------------------------
#
# $Id: SummaryMailerReqForm.py,v 1.3 2002-10-24 20:02:03 bkline Exp $
#
# Request form for generating PDQ Editorial Board Members Mailing.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/02/21 22:34:00  bkline
# Added navigation buttons.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrpub, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
board     = fields and fields.getvalue("Board") or None
email     = fields and fields.getvalue("Email") or None
boardType = fields and fields.getvalue("BoardType") or "Editorial"
title     = "CDR Administration"
section   = "PDQ %s Board Members Mailing" % boardType
SUBMENU   = "Mailer Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'SummaryMailerReqForm.py'
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
# Submit request if we have one.
#----------------------------------------------------------------------
if request == "Submit":

    # Reality check.
    if not board:
        cdrcgi.bail('Board not selected')

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
        cursor.execute("""\
            SELECT DISTINCT d.id, MAX(v.num)
                       FROM doc_version v
                       JOIN document d
                         ON d.id = v.id
                       JOIN query_term q
                         ON q.doc_id = d.id
                      WHERE d.active_status = 'A'
                        AND v.publishable = 'Y'
                        AND q.value = ?
                        AND q.path = '/Summary/SummaryMetaData/PDQBoard'
                                   + '/Board/@cdr:ref'
                   GROUP BY d.id""", (board,))
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
        docs.append("CDR%010d/%d" % (doc[0], doc[1]))

    # Drop the job into the queue.
    subset = 'Summary-PDQ %s Board' % boardType
    parms = (('Board', board),)
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
            "                      Mailer type = %s" % mailType,
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

#----------------------------------------------------------------------
# Generate a picklist for the PDQ Editorial Boards.
#----------------------------------------------------------------------
def makePicklist(conn):

    try:
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT DISTINCT d.id, d.title
                       FROM document d
                       JOIN query_term q
                         ON q.doc_id = d.id
                      WHERE q.path = '/Organization/OrganizationType'
                        AND q.value = 'PDQ %s Board'""" % boardType)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving PDQ %s Board info: %s" % 
                    (boardType, info[1][0]))
    if not rows:
        cdrcgi.bail("Unable to find any PDQ %s Board documents" % boardType)
    html = """\
      <SELECT NAME='Board'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
"""
    for id, title in rows:
        boardName = title.split(';')[0]
        html += """\
       <OPTION VALUE='CDR%010d'>%s &nbsp;</OPTION>
""" % (id, boardName)
    html += """\
      </SELECT>
"""
    return html

#----------------------------------------------------------------------
# Put up the form if we don't have a request yet.
#----------------------------------------------------------------------
form = """\
   <H2>Select board name and optional email address for notification</H2>
   <TABLE>
    <TR>
     <TD ALIGN='right'><B>Board Name</B></TD>
     <TD>%s</TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP>
      <B>Email notification address: &nbsp;</B>
     </TD>
     <TD><INPUT NAME='Email' SIZE='55'></TD>
    </TR>
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
""" % (makePicklist(conn), cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</BODY></HTML>")
