#----------------------------------------------------------------------
#
# RunReports.py
# -------------
# $Id: $
#
# Web interface to allow running command line utility jobs/reports in
# CBIIT environment
#
#----------------------------------------------------------------------
import sys, cdr, cgi, cdrcgi, time
import cdr, cgi, cdrcgi, re, cdrdb, os

LOGFILE = "%s/RunReports.log" % cdr.DEFAULT_LOGDIR
PUBPATH = os.path.join('d:\\cdr', 'publishing')
PROG    = 'RunReports.py'

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
repOptions= fields and fields.getvalue("repoptions")   or '--help'
repName   = fields and fields.getvalue("reportname")   or None
jobMode   = fields and fields.getvalue("mode")         or "test"
submit    = fields and fields.getvalue("SubmitButton") or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Run CDR Utilities"
script    = "RunReports.py"
SUBMENU   = "Report Menu"
buttons   = (cdrcgi.MAINMENU)

if jobMode == 'test':
    runmode = '--testmode'
else:
    runmode = '--livemode'

options = ''
if not repOptions:
    cdrcgi.bail('No repOptions: >%s<' % repr(repOptions))

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
session = '518127B0-AFD042-107-WGE4HRAGAWQS'
repName = '/cdr/publishing/ICRDBStatsReport.py'

if not repName:
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
    <select name='reportname' id='reportname'>
     <option>/cdr/publishing/ICRDBStatsReport.py</option>
     <option>/cdr/publishing/PubEmail.py</option>
     <option CHECKED='1'>Success</option>
    </select>
    <input name='repoptions' type='text' size='25' id="repoptions" >
    <label for="idAll">Job options</label>
    <br>
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
    cdr.logwrite("%s: Name: %s" % (PROG, repName), LOGFILE)
    cdr.logwrite("%s: mode:   %s" % (PROG, jobMode), LOGFILE)
    
    if repOptions == '--help':
        cmd = u'%s %s' % (repName, repOptions)

        cdr.logwrite('Submitting command...\n%s' % repr(cmd), LOGFILE)

        myCmd = cdr.runCommand(cmd)

        cdr.logwrite("Code: %s" % myCmd.code, LOGFILE)
        cdr.logwrite("Outp: %s" % myCmd.output, LOGFILE)
        cdrcgi.bail('%s' % myCmd.output)
    else:
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
