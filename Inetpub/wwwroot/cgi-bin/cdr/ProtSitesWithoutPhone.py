#----------------------------------------------------------------------
#
# $Id$
#
# Queue up report for Protocol sites without contact phone.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/03/04 22:45:01  bkline
# New report on protocol participating sites without a phone after
# vendor filtering.
#
#----------------------------------------------------------------------

import cdr, cdrbatch, cdrcgi, cgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
email       = fields and fields.getvalue("Email")    or None
title       = "CDR Administration"
section     = "Protocol Sites Without Phones"
SUBMENU     = "Report Menu"
buttons     = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'ProtSitesWithoutPhone.py'
command     = 'lib/Python/CdrLongReports.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 """)

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
if not email or request != "Submit":
    form = """\
   <p>
    This report requires at least an hour to complete.
    When the report processing has completed, email notification
    will be sent to the addresses specified below.  At least
    one email address must be provided.  If more than one
    address is specified, separate the addresses with a blank.
   </p>
   <br>
   <b>Email address(es):&nbsp;</b>
   <input name='Email' size='60' value='%s'><br>
   <input type='hidden' name='%s' value='%s'>
  </form>
 </body>
</html>
""" % (cdr.getEmail(session), cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------    
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------    
batch = cdrbatch.CdrBatch(jobName = section, command = command, email = email)
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'ProtSitesWithoutPhone.py'
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
    <a href='getBatchStatus.py?%s=%s&jobId=%s'><u>link</u></a>
    or use the CDR Administration menu to select 'View
    Batch Job Status'.
   </p>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, jobId))
