#----------------------------------------------------------------------
#
# $Id$
#
# Report on mailers which haven't been responded to (other than
# status and participant mailers).
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2009/09/16 16:42:07  venglisc
# Initial copy of program to submit a batch job to create the 'Transfer of
# Ownership' report. (Bug 4626)
#
# Revision 1.6  2006/03/14 14:17:18  bkline
# Replaced development server with current server in email link.
#
# Revision 1.5  2006/01/10 16:27:21  bkline
# Took out hard-wiring of report to production server.
#
# Revision 1.4  2004/02/26 21:11:01  bkline
# Replaced hard-coded name of development server with macro from cdr
# module.
#
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
repTitle = 'Protocol Ownership Transfer'
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Protocol Ownership Transfer Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, section, "ProtOwnershipTransfer.py",
                         buttons, method = 'GET')
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
if not email:
    form = """\
   <div style="background-color:lightgray; width:40%%;" class="section">
    <div style="border-top:1px solid black; border-left:1px solid black;
               border-right:3px solid black; border-bottom:3px solid black;
               padding:5px">
     <p>
      This report requires a few minutes to complete.
      When the report processing has completed, email notification
      will be sent to the addresses specified below.  At least
      one email address must be provided.  If more than one
      address is specified, separate the addresses with a blank.
     </p>
    </div>
   </div>
   <br>
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <UL>
    <LI style="list-style: none">Email address(es):&nbsp;&nbsp;&nbsp;
     <INPUT Name='Email' Size='40'>
    </LI>
   </UL>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------    
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
args = (("Host", cdrcgi.WEBSERVER),)

batch = cdrbatch.CdrBatch(jobName = "Protocol Ownership Transfer",
                          command = command, email = email,
                          args = args)
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId       = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'ospx.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 """)
cdrcgi.sendPage(header + """\
   <h4>Report has been queued for background processing</h4>
   <div style="background-color:lightgray; width:40%%;" class="section">
    <div style="border-top:1px solid black; border-left:1px solid black;
               border-right:3px solid black; border-bottom:3px solid black;
               padding:5px">
     <p>
      To monitor the status of the job, click the status-link below
      <div style="color:blue; text-align:center; padding:0;">
       <span style="font-style: italic; font-weight:bold; 
                    text-decoration: underline;">
       <a href='http://%s%s/getBatchStatus.py?%s=%s&jobId=%s'>
        View Batch Job Status
       </a>
       </span>
      </div>
      </p>
      <p>
      or use the CDR Administration menu and select 'View
      Batch Job Status'.
     </p>
    </div>
   </div>
  </form>
 </body>
</html>
""" % (cdrcgi.WEBSERVER, cdrcgi.BASE, cdrcgi.SESSION, session, jobId))
