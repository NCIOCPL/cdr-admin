#----------------------------------------------------------------------
#
# $Id: CheckUrls.py,v 1.4 2003-11-05 14:47:47 bkline Exp $
#
# Reports on URLs which cannot be reached.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/02/21 15:43:13  bkline
# Added navigation buttons.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdrdb, cdrcgi, cdrbatch

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "URL Check"
SUBMENU = 'Report Menu'
buttons = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "CheckUrls.py", buttons,
                        method = 'GET')
email   = fields and fields.getvalue('email') or None
command = 'lib/Python/CdrLongReports.py'

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Put up the request interface if appropriate.
#----------------------------------------------------------------------
if not email:
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
    <b>Email address(es):&nbsp;&nbsp;&nbsp;</b>
     <INPUT Name='email' Size='40'>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------    
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
batch = cdrbatch.CdrBatch(jobName = "URL Check",
                          command = command, email = email)
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId       = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'CheckUrls.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 """)
base = "http://%s%s" % (cdrcgi.WEBSERVER, cdrcgi.BASE)
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
""" % (base, cdrcgi.SESSION, session, jobId))
