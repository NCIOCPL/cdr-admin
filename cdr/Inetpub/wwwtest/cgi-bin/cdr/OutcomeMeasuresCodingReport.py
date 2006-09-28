#----------------------------------------------------------------------
#
# $Id: OutcomeMeasuresCodingReport.py,v 1.2 2006-09-28 12:04:16 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/05/04 15:05:00  bkline
# New report for compliance with ICMJE requirements.
#
#----------------------------------------------------------------------

import cdrbatch, cdrcgi, cgi, cdr

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
email       = fields and fields.getvalue("Email")       or None
onlyMissing = fields and fields.getvalue('onlyMissing') or 'N'
title       = "CDR Administration"
section     = "Outcome Measures Coding Report"
SUBMENU     = "Report Menu"
buttons     = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'OutcomeMeasuresCodingReport.py'
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
    This report requires a few minutes to complete.
    When the report processing has completed, email notification
    will be sent to the addresses specified below.  At least
    one email address must be provided.  If more than one
    address is specified, separate the addresses with a blank.
   </p>
   <br>
   <table border='0'>
    <tr>
     <td>
      <b>Email address(es):&nbsp;</b>
     </td>
     <td>
      <input name='Email' size='80' value='%s'><br>
     </td>
    </tr>
   </table>
   <input type='hidden' name='%s' value='%s'>
   <input type='hidden' name='onlyMissing' value='%s'>
  </form>
 </body>
</html>
""" % (cdr.getEmail(session) or "&nbsp;", cdrcgi.SESSION, session, onlyMissing)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------    
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
args = [('only-missing', onlyMissing)]
batch = cdrbatch.CdrBatch(jobName = section, command = command, email = email,
                          args = args)
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId       = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'OutcomeMeasuresCodingReport.py'
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
""" % (cdrcgi.WEBSERVER, cdrcgi.BASE, cdrcgi.SESSION, session, jobId))
