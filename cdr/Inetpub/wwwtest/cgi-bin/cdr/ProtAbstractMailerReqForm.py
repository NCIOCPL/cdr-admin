#----------------------------------------------------------------------
#
# $Id: ProtAbstractMailerReqForm.py,v 1.4 2002-10-10 19:18:09 bkline Exp $
#
# Request form for Initial Protocol Abstract Mailer.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/02/21 22:34:00  bkline
# Added navigation buttons.
#
# Revision 1.2  2001/12/01 18:06:37  bkline
# Replaced SQL query approach to work around SQL Server bug.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, cdrpub

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
docId      = fields and fields.getvalue("DocId") or None
email      = fields and fields.getvalue("Email") or None
title      = "CDR Administration"
section    = "Protocol Abstract Initial Mailer"
SUBMENU    = "Mailer Menu"
buttons    = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script     = 'ProtAbstractMailerReqForm.py'
header     = cdrcgi.header(title, title, section, script, buttons)
subsetName = 'Protocol-Initial abstract'

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
# Put up the form if we don't have a request yet.
#----------------------------------------------------------------------
if not request:
    form = """\
   <H2>Enter request parameters</H2>
   <H5>Protocol ID and email notification address are both optional.
       If Protocol ID is specified, only a mailer for that protocol
       will be generated; otherwise all eligible protocols for which
       abstract mailers have not yet been sent will have mailers
       generated.</H5>
   <TABLE>
    <TR>
     <TD ALIGN='right' NOWRAP>
      <B>Protocol CDR ID: &nbsp;</B>
     </TD>
     <TD><INPUT NAME='DocId'></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP>
      <B>Notification email address: &nbsp;</B>
     </TD>
     <TD><INPUT NAME='Email'></TD>
    </TR>
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + "</BODY></HTML>")

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrPublishing')
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Find the publishing system control document.
#----------------------------------------------------------------------
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

#----------------------------------------------------------------------
# Determine which documents are to be published.
#----------------------------------------------------------------------
if docId:
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)
    try:
        cursor.execute("""\
            SELECT MAX(num)
              FROM doc_version
             WHERE id = ?""", (intId,))
        row = cursor.fetchone()
        if not row:
            cdrcgi.bail("No versions have been saved yet for CDR%010d" % intId)
        docList = ((intId, row[0]),)
    except cdrdb.Error, info:
        cdrcgi.bail("No version found for document %d: %s" % (intId,
                                                              info[1][0]))
else:
    statPath = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
    srcPath  = '/InScopeProtocol/ProtocolSources/ProtocolSource/SourceName'
    brussels = 'NCI Liaison Office-Brussels'
    try:
        cursor.execute("""\
            SELECT DISTINCT protocol.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN ready_for_review
                         ON ready_for_review.doc_id = doc_version.id
                       JOIN document protocol
                         ON protocol.id = ready_for_review.doc_id
                       JOIN query_term prot_status
                         ON prot_status.doc_id = protocol.id
                      WHERE prot_status.value IN ('Active', 
                                                  'Approved-not yet active')
                        AND prot_status.path = '%s'
                        AND NOT EXISTS (SELECT *
                                          FROM query_term src
                                         WHERE src.value = '%s'
                                           AND src.path  = '%s'
                                           AND src.doc_id = protocol.id)
                        AND NOT EXISTS (SELECT *
                                          FROM pub_proc p
                                          JOIN pub_proc_doc pd
                                            ON p.id = pd.pub_proc
                                         WHERE pd.doc_id = protocol.id
                                           AND p.pub_subset = '%s'
                                           AND (p.status = 'Success'
                                           AND pd.failure IS NULL
                                            OR p.completed IS NULL))
                   GROUP BY protocol.id""" % (statPath, brussels, srcPath,
                                              subsetName))
        docList = cursor.fetchall()
        if not docList:
            cdrcgi.bail("No documents match the selection criteria")
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

# Drop the job into the queue.
docs = []
for doc in docList:
    docs.append("CDR%010d/%d" % (doc[0], doc[1]))
result = cdr.publish(credentials = session, pubSystem = 'Mailers',
                     pubSubset = subsetName, docList = docs,
                     allowNonPub = 'Y', email = email)

# cdr.publish returns a tuple of job id + messages
# If serious error, job id = None
if not result[0] or int(result[0]) < 0:
    cdrcgi.bail("Unable to initiate publishing job:<br>%s" % result[1])

jobId = int(result[0])

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
""" % (jobId, cdrcgi.BASE, jobId, cdrcgi.SESSION, session)
cdrcgi.sendPage(header + html)
