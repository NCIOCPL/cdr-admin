#----------------------------------------------------------------------
#
# $Id: ProtAbstractMailerReqForm.py,v 1.1 2001-10-16 13:51:35 bkline Exp $
#
# Request form for Initial Protocol Abstract Mailer.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, time, cdrdb, cdrpub

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
docId   = fields and fields.getvalue("DocId")       or None
reqType = fields and fields.getvalue("RequestType") or None
start   = fields and fields.getvalue("StartDate")   or None
email   = fields and fields.getvalue("Email") or None
title   = "CDR Administration"
section = "Protocol Abstract Initial Mailer"
buttons = ["Submit", "Log Out"]
script  = 'ProtAbstractMailerReqForm.py'
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Put up the form if we don't have a request yet.
#----------------------------------------------------------------------
if not request:
    now = time.localtime(time.time())
    then = (now[0], now[1] - 1, now[2], 0, 0, 0, 0, 0, -1)
    then = time.localtime(time.mktime(then))
    then = time.strftime("%Y-%m-%d", then)
    form = """\
   <H2>Enter request parameters</H2>
   <TABLE>
    <TR>
     <TD ALIGN='right' NOWRAP>
      <B>Protocol CDR ID: &nbsp;</B>
     </TD>
     <TD><INPUT NAME='DocId'></TD>
     <TD>
      <B>
       <INPUT TYPE='radio' 
              NAME='RequestType' 
              VALUE='Individual'>Individual Mailer Request
      </B>
     </TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP>
      <B>Protocols Entered Since (YYYY-MM-DD): &nbsp;</B>
     </TD>
     <TD><INPUT NAME='StartDate' VALUE='%s'></TD>
     <TD>
      <B>
       <INPUT TYPE='radio' 
              NAME='RequestType' 
              VALUE='Batch'
              CHECKED>Batch Request
      </B>
     </TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP>
      <B>Optional email notification address: &nbsp;</B>
     </TD>
     <TD COLSPAN='2'><INPUT NAME='Email'></TD>
    </TR>
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
""" % (then, cdrcgi.SESSION, session)
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
if reqType == 'Individual':
    if not docId:
        cdrcgi.bail('No document ID specified.')
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)
    parms  = []
    try:
        cursor.execute("""\
            SELECT MAX(num)
              FROM doc_version
             WHERE id = ?""", (intId,))
        row = cursor.fetchone()
        docList = ((intId, row[0]),)
    except cdrdb.Error, info:
        cdrcgi.bail("No version found for document %d: %s" % (intId,
                                                              info[1][0]))
else:
    if not start:
        cdrcgi.bail('No start date specified')
    parms = [('BeginDate', start)]
    try:
        cursor.callproc("prot_init_mailer_docs", (start,))
        cantUseThisBecauseOfABugInMicrosoftADOCOMObjects = """\
            SELECT DISTINCT d.id, MAX(v.num)
                       FROM doc_version v
                       JOIN document d
                         ON d.id = v.id
                       JOIN query_term s
                         ON s.doc_id = d.id
                      WHERE d.active_status <> 'A'
                        AND s.value IN ('Active', 'Approved-Not Yet Active')
                        AND s.path = '/InScopeProtocol/ProtocolAdminInfo' +
                                     '/CurrentProtocolStatus'
                        AND NOT EXISTS (SELECT *
                                          FROM query_term src
                                         WHERE src.value = 'NCI Liaison ' +
                                                           'Office-Brussels'
                                           AND src.path  = '/InScopeProtocol' +
                                                           '/ProtocolSources' +
                                                           '/ProtocolSource' +
                                                           '/SourceName'
                                           AND src.doc_id = d.id)
                        AND NOT EXISTS (SELECT *
                                          FROM pub_proc_doc p
                                         WHERE p.doc_id = d.id)
                        AND (SELECT MIN(dt)
                               FROM audit_trail a
                              WHERE a.document = d.id) > ?
                   GROUP BY d.id""" #, (start,))
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

# Drop the job into the queue.
subsetName = 'Initial Protocol Abstract Verification Mailers'
result = cdrpub.initNewJob(ctrlDocId, subsetName, session, docList, parms,
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
   </FORM>
  </BODY>
 </HTML>
""" % (result[0], cdrcgi.BASE, result[0])
cdrcgi.sendPage(header + html)
