#----------------------------------------------------------------------
#
# ReverifyJob.py
# -------------
# $Id: $
#
# Web interface to allow running the ReverifyPushJob program in the 
# CBIIT environment
#
#----------------------------------------------------------------------
import sys, cdr, cgi, cdrcgi, time
import cdr, cgi, cdrcgi, re, cdrdb, os

LOGFILE = "%s/ReverifyJob.log" % cdr.DEFAULT_LOGDIR
PUBPATH = os.path.join('d:\\cdr', 'publishing')
PROG    = 'ReverifyPushJob.py'

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
job       = fields and fields.getvalue("jobid")        or 0
jobStatus = fields and fields.getvalue("status")       or None
jobMode   = fields and fields.getvalue("mode")         or "test"
submit    = fields and fields.getvalue("SubmitButton") or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Reverify Gatekeeper Push Job"
script    = "ReverifyJob.py"
SUBMENU   = "Report Menu"
buttons   = (cdrcgi.MAINMENU)

if jobMode == 'test':
    runmode = '--testmode'
else:
    runmode = '--livemode'

jobId = 0
if job:
    try:
        jobId = int(job)
    except:
        cdrcgi.bail('Job-ID not a number: %s' % repr(job))

# -------------------------------------------------------------------
#
# -------------------------------------------------------------------
def getUserName(session):
    cursor = cdrdb.connect("CdrGuest").cursor()
    cursor.execute("""\
SELECT u.name
  FROM usr u
  JOIN session s
    ON s.usr = u.id
 WHERE s.name = ?""", session)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Can't find session user name")
    return rows[0][0]


# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y")

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
# jobStatus = 'Failure'
# jobId = 1234
# session = '515F47B2-EC81EB-107-AG1T8VWZU7LA'
if not jobId and not jobStatus:
    header = cdrcgi.header(title, title, instr + ' - ' + dateString, 
                           script,
                           ("Submit",
                            cdrcgi.MAINMENU),
                           numBreaks = 1,
                           stylesheet = """
   <STYLE type="text/css">
    TD      { font-size:  12pt; }
    LI.none { list-style-type: none }
    DL      { margin-left: 0; padding-left: 0 }
   </STYLE>
"""                           )
    form   = """\
   <input type='hidden' name='%s' value='%s'>
 
   <fieldset>
    <legend>&nbsp;Enter Pub-Job Values&nbsp;</legend>
    <input name='jobid' type='text' size='10' id="jobid" >
    <label for="idAll">Job-Id (12345)</label>
    <br>
    <select name='status' id="status">
     <option>Failure</option>
     <option>Stalled</option>
     <option CHECKED='1'>Success</option>
    </select>
    <label for="idOne">Job status</label>
    <br>
    <input name='mode' type='radio' id="test"
           value='test' CHECKED>
    <label for="byHp">Test mode</label>
    <br>
    <input name='mode' type='radio' id="live"
           value='live'>
    <label for="byPat">Live mode</label>
   </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

if not session: 
    cdrcgi.bail("Unknown or expired CDR session.")

try:
    user = getUserName(session) 
    cdr.logwrite('--------------------------------------------', LOGFILE)
    cdr.logwrite("%s: session %s" % (PROG, repr(session)), LOGFILE)
    cdr.logwrite("%s: user:   %s" % (PROG, repr(user)), LOGFILE)
    cdr.logwrite("%s: job-id: %s" % (PROG, jobId), LOGFILE)
    cdr.logwrite("%s: status: %s" % (PROG, jobStatus), LOGFILE)
    cdr.logwrite("%s: mode:   %s" % (PROG, jobMode), LOGFILE)
    
    cmd = os.path.join(PUBPATH, u'%s --session=%s --jobid=%d --status=%s %s' % (
                                 PROG, session, jobId, jobStatus, runmode))

    cdr.logwrite('Submitting command...\n%s' % repr(cmd), LOGFILE)

    myCmd = cdr.runCommand(cmd)

    cdr.logwrite("Code: %s" % myCmd.code, LOGFILE)
    cdr.logwrite("Outp: %s" % myCmd.output, LOGFILE)
    report = myCmd.output

except TypeError:
    e = sys.exc_info()[0]
    print '*** Error: %s' % e
    
    cdr.logwrite('*** Error: Submitting Publishing Job failed', LOGFILE)
    sys.exit(1)


header = cdrcgi.header(title, title, instr + ' - ' + dateString, 
                           script,
                           ("Submit",
                            cdrcgi.MAINMENU),
                           numBreaks = 1,
                           stylesheet = """
   <STYLE type="text/css">
    TD      { font-size:  12pt; }
    LI.none { list-style-type: none }
    DL      { margin-left: 0; padding-left: 0 }
   </STYLE>
"""                           )
footer = """\
     </BODY>
    </HTML> 
"""     

# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + '<pre>' + report + '</pre>' + footer)
