#----------------------------------------------------------------------
#
# $Id: GlossaryTermPhrases.py,v 1.4 2004-08-31 12:55:17 bkline Exp $
#
# Report on phrases matching specified glossary term.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2004/08/26 14:08:58  bkline
# Added missing hidden field for trials.
#
# Revision 1.2  2004/08/12 13:43:28  bkline
# Changes requested by Margaret (including ability to restrict the
# report to search specified document types).
#
# Revision 1.1  2004/05/11 17:58:51  bkline
# Report on phrases matching specified glossary term.
#
#----------------------------------------------------------------------

import cdr, cdrdb, cdrcgi, cgi, re, cdrbatch, socket

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
id       = fields and fields.getvalue('Id')      or None
name     = fields and fields.getvalue('Name')    or None
hp       = fields and fields.getvalue('hp')      or None
patient  = fields and fields.getvalue('patient') or None
trials   = fields and fields.getvalue('trials')  or None
email    = fields and fields.getvalue("Email")   or cdr.getEmail(session)
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "GlossaryTermPhrases.py"
title    = "CDR Administration"
section  = "Glossary Term Phrases Report"
header   = cdrcgi.header(title, title, section, script, buttons)
command  = 'lib/Python/CdrLongReports.py'

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
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not name and not id or not email or not (hp or patient or trials):
    form = """\
   <p>
    This report requires a few minutes to complete.
    When the report processing has completed, email notification
    will be sent to all addresses specified below.  At least
    one email address must be provided.  If more than one
    address is specified, separate the addresses with a blank.
   </p>
   <br>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD ALIGN='right'><B>Document ID:&nbsp;</B></TD>
     <TD><INPUT NAME='Id'%s></TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>Glossary Term Name:&nbsp;</B></TD>
     <TD><INPUT NAME='Name'></TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>Email:&nbsp;</B></TD>
     <TD><INPUT NAME='Email'></TD>
    </TR>
    <TR>
     <TD ALIGN='right' VALIGN='top'><B>Document Type:&nbsp;</B></TD>
     <TD><INPUT TYPE='checkbox' NAME='hp'>Health Professional Summaries<BR>
         <INPUT TYPE='checkbox' NAME='patient'>Patient Summaries<BR>
         <INPUT TYPE='checkbox' NAME='trials'>Patient Abstracts</TD>
    </TR>
   </TABLE>
   <BR>
   [NOTE: This report can take several minutes to prepare; please be patient.]
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, id and (" VALUE='%s'" % id) or "")
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Allow the user to select from a list of protocols matching title string.
#----------------------------------------------------------------------
def putUpSelection(rows):
    options = ""
    selected = " SELECTED"
    for row in rows:
        options += """\
    <OPTION VALUE='CDR%010d'%s>CDR%010d: %s</OPTION>
""" % (row[0], selected, row[0], row[1])
        selected = ""
    form = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='Email' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='hp' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='patient' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='trials' VALUE='%s'>
   <H3>Select term for report:<H3>
   <SELECT NAME='Id'>
    %s
   </SELECT>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, email or "", hp or "", patient or "", trials or "", options)
    cdrcgi.sendPage(header + form)
    
#----------------------------------------------------------------------
# Get the document ID.
#----------------------------------------------------------------------
if id:
    digits = re.sub('[^\d]', '', id)
    id     = int(digits)
else:
    try:
        namePattern = name + "%"
        conn   = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("""\
                SELECT DISTINCT d.id, d.title
                           FROM document d
                           JOIN doc_type t
                             ON t.id = d.doc_type
                          WHERE t.name = 'GlossaryTerm'
                            AND d.title LIKE ?""", namePattern,
                       timeout = 300)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure looking up GlossaryTerm name '%s': %s" % (name,
                                                                 info[1][0]))
    if len(rows) > 1: putUpSelection(rows)
    if len(rows) < 1: cdrcgi.bail("Unknown GlossaryTerm '%s'" % name)
    id = rows[0][0]

#----------------------------------------------------------------------    
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
doctypes = ""
if trials:
    doctypes = "PatientAbstracts "
if hp:
    doctypes += "HPSummaries "
if patient:
    doctypes += "PatientSummaries"
doctypes = doctypes.strip()
args = (("id", str(id)),("types", doctypes))

batch = cdrbatch.CdrBatch(jobName = "Glossary Term Search",
                          command = command, email = email,
                          args = args)
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId       = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'GlossaryTermPhrases.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 """)
baseUrl = 'http://%s.nci.nih.gov/cgi-bin/cdr' % socket.gethostname()
cdrcgi.sendPage(header + """\
   <h4>Report has been queued for background processing</h4>
   <p>
    To monitor the status of the job, click this
    <a href='%s/getBatchStatus.py?%s=%s&jobId=%s'><u>link</u></a>
    or use the CDR Administration menu to select 'View
    Batch Job Status'.
   </p>
  </form>
 </body>
</html>
""" % (baseUrl, cdrcgi.SESSION, session, jobId))
