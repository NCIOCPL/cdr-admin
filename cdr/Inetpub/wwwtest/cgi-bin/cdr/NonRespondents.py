#----------------------------------------------------------------------
#
# $Id: NonRespondents.py,v 1.4 2004-02-26 21:11:01 bkline Exp $
#
# Report on mailers which haven't been responded to (other than
# status and participant mailers).
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2003/07/29 12:33:25  bkline
# Changed label (60-120) at users' request.  Plugged in hard-coded
# web server name (Mahler).
#
# Revision 1.2  2003/06/13 20:29:42  bkline
# Moved primary functionality to CdrLongReports.py
#
# Revision 1.1  2003/06/10 13:56:11  bkline
# First cut at Mailer non-respondents report.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, sys, time, cdrbatch

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Non Respondents Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, section, "NonRespondents.py",
                         buttons, method = 'GET')
docType  = fields and fields.getvalue("DocType")    or None
age      = fields and fields.getvalue("Age")        or None
email    = fields and fields.getvalue("Email")      or None
command  = 'lib/Python/CdrLongReports.py'

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Put up the request interface if appropriate.
#----------------------------------------------------------------------
if not docType or not age or not email:
    form = """\
   <p>
    This report requires a few minutes to complete.
    When the report processing has completed, email notification
    will be sent to the addresses specified below.  At least
    one email address must be provided.  If more than one
    address is specified, separate the addresses with a blank.
   </p>
   <br>
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <OL>
    <LI>Type of mailer:&nbsp;&nbsp;&nbsp;
     <SELECT NAME='DocType'>
      <OPTION VALUE='Organization'>Organization</OPTION>
      <OPTION VALUE='Person'>Person</OPTION>
      <OPTION VALUE='InScopeProtocol'>Protocol Summary</OPTION>
     </SELECT>
    </LI>
    <BR><BR><BR>
    <LI>Non-response time:&nbsp;&nbsp;&nbsp;
     <SELECT NAME='Age'>
      <OPTION VALUE='15'>15-29 days since last mailer</OPTION>
      <OPTION VALUE='30'>30-59 days since last mailer</OPTION>
      <OPTION VALUE='60'>60-120 days since last mailer</OPTION>
     </SELECT>
    </LI>
    <BR><BR><BR>
    <LI>Email address(es):&nbsp;&nbsp;&nbsp;
     <INPUT Name='Email' Size='40'>
    </LI>
   </OL>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------    
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
args = (("Age", age), ("BaseDocType", docType), ("Host", cdrcgi.WEBSERVER))

# Have to do this on the development machine, since that's the only
# server with Excel installed.
batch = cdrbatch.CdrBatch(jobName = "Mailer Non-Respondents",
                          command = command, email = email,
                          args = args, host = cdr.DEV_HOST)
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId       = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'osp.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 """)
cdrcgi.sendPage(header + """\
   <h4>Report has been queued for background processing</h4>
   <p>
    To monitor the status of the job, click this
    <a href='http://%s%s/getBatchStatus.py?%s=%s&jobId=%s'><u>link</u></a>
    or use the CDR Administration menu to select 'View
    Batch Job Status'.
   </p>
  </form>
 </body>
</html>
""" % (cdr.DEV_HOST, cdrcgi.BASE, cdrcgi.SESSION, session, jobId))

