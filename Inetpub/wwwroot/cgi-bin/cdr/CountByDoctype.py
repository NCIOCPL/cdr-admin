#----------------------------------------------------------------------
# Running the Publishing Documents Report Count as a batch job
#
# BZIssue::5237 - Report for publication document counts fails on
#                 non-production server
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, cdrbatch

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Published Documents Count"
SUBMENU = 'Report Menu'
buttons = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "CountByDoctype.py", buttons,
                        method = 'GET')
email   = fields and fields.getvalue('email') or None
command = 'lib/Python/CdrLongReports.py'
docTypes = cdr.getDoctypes(session)

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
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>

   <fieldset>
   <p>
    This report requires a while to complete.
    When the report processing has completed, email notification
    will be sent to the addresses specified below.  At least
    one email address must be provided.  If more than one
    address is specified, separate the addresses with a blank.
   </p>

    <br>
    <b>Email address(es):&nbsp;&nbsp;&nbsp;</b>
    <br>
    <INPUT Name='email' Size='70' value='%s'>

""" % (cdrcgi.SESSION, session, cdr.getEmail(session))

    cdrcgi.sendPage(header + form + """\
   </fieldset>
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------    
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
batch = cdrbatch.CdrBatch(jobName = "Published Documents Count",
                          command = command, email = email)
try:
    batch.queue()
except Exception as e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId       = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'CountByDoctype.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 """)
base = "http://%s%s" % (cdrcgi.WEBSERVER, cdrcgi.BASE)

cdrcgi.sendPage(header + """\
   <fieldset>
   <h4>Report has been queued for background processing</h4>
   <p>
    To monitor the status of the job, click this
    <a href='%s/getBatchStatus.py?%s=%s&jobId=%s'>
     <span style="text-decoration:underline;color:blue;">link</span>
    </a>
    or use the CDR Administration menu option 
    <span style="font-style:italic;">View Batch Job Status</span>.
   </p>
   </fieldset>
  </form>
 </body>
</html>
""" % (base, cdrcgi.SESSION, session, jobId))
