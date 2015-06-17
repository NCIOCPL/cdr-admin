#----------------------------------------------------------------------
#
# $Id: BoardMeetingDates.py 9572 2010-04-02 17:25:19Z volker $
#
# Report listing the Board meetings by date or board.
#
#----------------------------------------------------------------------
import cdr, cdrcgi, cgi, os, time, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
startDate  = fields.getvalue('StartDate') or None
endDate    = fields.getvalue('EndDate')   or None
SUBMENU    = "Report Menu"
buttons    = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script     = "RunICRDBStatReport.py"
title      = "CDR Administration"
section    = "Submit PCIB Statistics Report"
header     = cdrcgi.header(title, title, section, script, buttons,
                            method = 'GET',
                            stylesheet = """\
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script type='text/javascript' language='JavaScript'
           src='/js/CdrCalendar.js'></script>
   <style type='text/css'>
    body          { background-color: #DFDFDF;
                    font-family: sans-serif;
                    font-size: 12pt; }
    legend        { font-weight: bold;
                    color: teal;
                    font-family: sans-serif; }
    fieldset      { width: 500px;
                    margin-left: auto;
                    margin-right: auto;
                    display: block; }
    .CdrDateField { width: 100px; }
   </style>
   <script type='text/javascript' language='JavaScript'>
    function someBoards() {
        document.getElementById('AllBoards').checked = false;
    }
    function allBoards(widget, n) {
        for (var i = 1; i <= n; ++i)
            document.getElementById('E' + i).checked = false;
    }
   </script>
""")
rptStyle = """\
  <style type='text/css'>
   *.board       { font-weight: bold;
                   text-decoration: underline;
                   font-size: 12pt; }
   .dates        { font-size: 11pt; }
   .title        { font-size: 16pt;
                   font-weight: bold;
                   text-align: center; }
   p.instruction { font-size: 12pt; }
   .subtitle     { font-size: 12pt; }
   .blank        { background-color: #FFFFFF; }
  </style>"""
rptHeader  = cdrcgi.rptHeader(title, bkgd = 'FFFFFF', stylesheet = rptStyle)
footer     = """\
 </body>
</html>"""

# Setting directory and file names
# --------------------------------
PUBPATH = os.path.join('d:\\cdr', 'publishing')
LOGFILE = 'ICRDBStats.log'

prog    = 'ICRDBStatsReport.py'
options = ' --livemode --email --include --startdate="%s" --enddate="%s"'

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
# Normalize a year, month, day tuple into a standard date-time value.
#----------------------------------------------------------------------
def normalizeDate(y, m, d):
    return time.localtime(time.mktime((y, m, d, 0, 0, 0, 0, 0, -1)))

#----------------------------------------------------------------------
# Generate a pair of dates suitable for seeding the user date fields.
#----------------------------------------------------------------------
def getDefaultDates():
    import time
    yr, mo, da, ho, mi, se, wd, yd, ds = time.localtime()
    startYear = normalizeDate(yr, 1, 1)
    endYear   = normalizeDate(yr, mo, da)
    return (time.strftime("%Y-%m-%d", startYear),
            time.strftime("%Y-%m-%d", endYear))

# ---------------------------------------------------------------------
# *** Main starts here ***
# ---------------------------------------------------------------------
#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not (startDate and endDate):
    startDate, endDate = getDefaultDates()
    form = """\
   <input type='hidden' name='%s' value='%s'>
   <fieldset class='dates'>
    <legend>&nbsp;Run PCIB Report for specific time frame&nbsp;</legend>
    <p style="font-size: 12pt;">The PCIB Report runs on every 1st of the month 
       for the previous month.  Specify the <em>start date</em> and 
       <em>end date</em> to run the report for a different time frame.  </p>
    <p style="font-size: 12pt;">An email including the report will be sent to 
       MB and VE.</p>
       
    <label for='ustart'>Start Date:</label>
    <input name='StartDate' value='%s' class='CdrDateField'
           id='ustart'> &nbsp;
    <label for='uend'>End Date:</label>
    <input name='EndDate' value='%s' class='CdrDateField'
           id='uend'>
    <p style="font-size: 12pt;">
       Please click the <em>Submit</em> button only once to create this 
       report!</p>
   </fieldset>
  </form>
""" % (cdrcgi.SESSION, session, startDate, endDate)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")


cmd   = os.path.join(PUBPATH, prog + options % (startDate, endDate))
myCmd = cdr.runCommand(cmd, joinErr2Out = False)

if myCmd.error:
   l = cdr.Log(LOGFILE)
   l.write('*** Error submitting RunICRDBStatReport.py\n%s' % 
                                           myCmd.error, stdout = True)
   raise Exception

#print cmd
#sys.exit(0)

# We have everything we need.  Show it to the user
# ------------------------------------------------
html = """<h3>PCIB Statistics Report submitted</h3>
        <p>The report finished and has been submitted via email.
        <br/>
        You may close this window."""
cdrcgi.sendPage(rptHeader + html + footer)
