#----------------------------------------------------------------------
#
# $Id: SummaryMailerReqForm.py,v 1.2 2002-02-21 22:34:00 bkline Exp $
#
# Request form for generating PDQ Editorial Board Members Mailing.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrpub, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
board   = fields and fields.getvalue("Board") or None
email   = fields and fields.getvalue("Email") or None
title   = "CDR Administration"
section = "PDQ Editorial Board Members Mailing"
SUBMENU = "Mailer Menu"
buttons = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = 'PDQMailerRequestForm.py'
header  = cdrcgi.header(title, title, section, script, buttons)

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
               AND d.title = 'Mailers'
""")
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
                   GROUP BY d.id
""", (board,))
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

    # Drop the job into the queue.
    subsetName = 'PDQ Editorial Board Members Mailing'
    parms = (('Board', board),)
    result = cdrpub.initNewJob(ctrlDocId, subsetName, session, rows, parms,
                               email)
    if type(result) == type(""):
        cdrcgi.bail(result)
    elif type(result) == type(u""):
        cdrcgi.bail(result.encode('latin-1'))
    header  = cdrcgi.header(title, title, section, None, [])
    html = """\
    <H3>Job Number %d Submitted</H3>
    <B>
     <FONT COLOR='black'>Use
      <A HREF='%s/PubStatus.py?id=%d'>this link</A> to view job status.
     </FONT>
    </B>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   </FORM>
  </BODY>
 </HTML>
""" % (result[0], cdrcgi.BASE, result[0], cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + html)

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
                        AND q.value = 'PDQ editorial board'
""")
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving PDQ Editorial Board info: %s" % 
                    info[1][0])
    if not rows:
        cdrcgi.bail("Unable to find any PDQ Editorial Board documents")
    html = """\
      <SELECT NAME='Board'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
"""
    for row in rows:
        html += """\
       <OPTION VALUE='CDR%010d'>%s &nbsp;</OPTION>
""" % (row[0], row[1])
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
