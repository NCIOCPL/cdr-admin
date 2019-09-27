#----------------------------------------------------------------------
# Web interface to allow running the ReverifyPushJob program in the
# CBIIT environment
#----------------------------------------------------------------------
import sys, os, cdr, cgi, cdrcgi, time
from cdrapi import db

LOGNAME = "ReverifyJob"
LOGGER  = cdr.Logging.get_logger(LOGNAME)
LOGFILE = f"{cdr.DEFAULT_LOGDIR}/ReverifyJob.log"
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
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Reverify Gatekeeper Push Job"
script    = "ReverifyJob.py"
SUBMENU   = "Report Menu"
buttons   = (cdrcgi.MAINMENU)

if jobMode == 'test':
    runmode = '--testmode'
elif jobMode != 'live':
    cdrcgi.bail()
else:
    runmode = '--livemode'

jobId = 0
if job:
    try:
        jobId = int(job)
    except:
        # Removed print of invalid job ID for AppScan security
        cdrcgi.bail('Job-ID not a number')

# Validate other parms
if request:
    cdrcgi.valParmVal(request, valList=('Submit', cdrcgi.MAINMENU))
if jobStatus:
    cdrcgi.valParmVal(jobStatus, valList=('Failure','Stalled','Success'))

# -------------------------------------------------------------------
#
# -------------------------------------------------------------------
def getUserName(session):
    cursor = db.connect(user="CdrGuest").cursor()
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
    LOGGER.info('--------------------------------------------')
    LOGGER.info("%s: session %r", PROG, session)
    LOGGER.info("%s: user:   %r", PROG, user)
    LOGGER.info("%s: job-id: %s", PROG, jobId)
    LOGGER.info("%s: status: %s", PROG, jobStatus)
    LOGGER.info("%s: mode:   %s", PROG, jobMode)

    args = PROG, session, jobId, jobStatus, runmode
    cmd = "{} --session={} --jobid={} --status={} {}".format(*args)
    cmd = os.path.join(PUBPATH, cmd)

    LOGGER.info('Submitting command...\n%s', cmd)

    process = cdr.run_command(f"{cdr.PYTHON} {cmd}", merge_output=True)

    LOGGER.info("Code: %s" % process.returncode)
    LOGGER.info("Outp: %s" % process.stdout)
    report = process.stdout

except TypeError as e:
    print(f"*** Error: {e}")
    LOGGER.exception('*** Error: Submitting Publishing Job failed')
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
