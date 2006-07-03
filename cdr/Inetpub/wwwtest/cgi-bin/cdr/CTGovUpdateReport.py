#----------------------------------------------------------------------
# Compare CTgovProtocol documents from an import job with the current
# publishable version of the the same documents.
#
# Done for Bugzilla issue #1881
#
# $Id: CTGovUpdateReport.py,v 1.3 2006-07-03 20:11:51 ameyer Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2006/01/10 20:10:15  ameyer
# Minor change to comments and screen title.
#
# Revision 1.1  2005/12/23 02:19:53  ameyer
# Report differences between imported and current working docs.
#
#----------------------------------------------------------------------

import time, cgi, cdr, cdrcgi, cdrdb, cdrbatch, CTGovUpdateCommon

# Load fields from the submitted form, if any
fields     = cgi.FieldStorage()
request    = cdrcgi.getRequest(fields)
session    = cdrcgi.getSession(fields)
importJobs = fields and fields.getlist('importJobs') or None
diffFmt    = fields and fields.getvalue('diffFmt') or None
emails     = fields and fields.getvalue('email') or None

# Custom button labels
CTGOV_MENU = "CTGov Menu"
LOGOUT     = "Log Out"

# Num days to look backward for import jobs
# XXX DEBUGGING ON MAHLER REQUIRES A BIG NUMBER
JOB_DAYS   = 240

# Stuff common to both interactive and batch portions
JOB_NAME    = CTGovUpdateCommon.JOB_NAME
REPORT_FILE = CTGovUpdateCommon.REPORT_FILE
REPORT_URL  = CTGovUpdateCommon.REPORT_URL
SCRIPT      = CTGovUpdateCommon.SCRIPT
LF          = CTGovUpdateCommon.LF

# Full path to batch portion of program
JOB_PATH    = "d:/cdr/lib/Python/" + SCRIPT

#----------------------------------------------------------------------
# Get a pair of formated dates
#----------------------------------------------------------------------
def getDates(limitTime, subDays):
    """
    Generate a pair of dates in YYYY-MM-DD format.

    Pass:
        limitTime - Seconds since epoch for latest time to convert.
        subDays   - Number of days to subtract from limitTime.

    Return:
        Tuple of:
            limitTime date.
            Earlier date.
    """
    dateFmt   = "%Y-%m-%d"
    before    = limitTime - (60 * 60 * 24 * subDays)
    limitDate = time.strftime(dateFmt, time.gmtime(limitTime))
    earlyDate = time.strftime(dateFmt, time.gmtime(before))

    return (limitDate, earlyDate)

#----------------------------------------------------------------------
# Locate import jobs and dates
#----------------------------------------------------------------------
def getJobList(daysBack):
    """
    Locate the import jobs and dates in the ctgov_import_job table
    for the last daysBack days.

    Pass:
        daysBack - Number of days to look back from today.

    Return:
        List of pairs of job id + date/time, in reverse chronological order.
    """
    # Get boundary dates
    (lastDate, firstDate) = getDates(time.time(), daysBack)

    # Search the ctgov_import_job table to find jobs in that range
    try:
        conn   = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
          SELECT id, dt FROM ctgov_import_job
           WHERE dt >= '%s'
             AND dt <= '%s'
          ORDER BY dt DESC""" % (firstDate, lastDate))
        rows = cursor.fetchall()
        cursor.close()
    except cdrdb.Error, info:
        cdrcgi.bail("Error fetching job ids: %s" % str(info))

    return rows

#----------------------------------------------------------------------
# Generate an option list for import jobs
#----------------------------------------------------------------------
def genJobOptionList():
    """
    Create a list of HTML select options listing all of the
    CTGovImport jobs run in the last 60 days.

    Pass:
        Job date/time list selected in getJobList()

    Return:
        Option list as an HTML string.
    """
    global JOB_DAYS

    # Get the job info
    jobList = getJobList(JOB_DAYS)

    if len(jobList) < 1:
        html = "<option value='-1'>No jobs in last %d days</option>" % JOB_DAYS
    else:
        html = ""
        for i in range(len(jobList)):
            html += "   <option value='%d'>%s</option>\n" % \
                    (jobList[i][0], jobList[i][1])

    return html


#----------------------------------------------------------------------
# Generate the input HTML form
#----------------------------------------------------------------------
def genInputForm(usrSession):
    """
    Create an input form for display to the user.

    Return:
        HTML form as a string.
    """
    # Get email address to put in form
    emailAddr = cdr.getEmail(usrSession)

    # Build form
    title   = "CDR Administration"
    section = "Imported CTGovProtocols vs. CWDs"
    script  = "CTGovUpdateReport.py"
    buttons = ["Submit Request", CTGOV_MENU, cdrcgi.MAINMENU, LOGOUT]
    html    = cdrcgi.header(title, title, section, script, buttons) + \
"""
<p>This program generates a report comparing all
CTGovProtocol documents imported on one or more dates against
the current working versions of the same documents.</p>

<p>Select one or more CTGov import jobs from the drop down list
below.  All import jobs from the last 60 days are shown.</p>

<p>If more than one import job is selected, all import jobs
ranging from the earliest job selected to the latest job
selected (inclusive), will be examined to find CTGovProtocols
imported in any of them.  A single document might appear in
more than one of the jobs in the range.  If so, the program
will use the last imported version in the set for its comparison.</p>

<table border='0'>
 <tr>
  <th align='right'>Import job</th>
  <td><select name='importJobs' size='8' multiple='multiple'>
%s
      </select></td>
  </td>
 </tr>
</table>

<p />

<table border='0'>
 <tr>
   <th align='right'>Output results in composite format</th>
   <td><input type='radio' name='diffFmt' value='XDiff' checked='checked'/>
       </td>
 </tr>
 <tr>
   <th align='right'>Output results in UNIX diff format</th>
   <td><input type='radio' name='diffFmt' value='UDiff' /></td>
 </tr>
</table>

<p>The report will be written to the following file.  It will
overwrite any previous report stored there:</p>

<p> &nbsp; &nbsp; <a href='%s'>%s</a>.</p>

<p>If you wish to be notified when the report is ready, please
enter one or more email addresses below.</p>

<p>Email(s): <input type='text' name='email' value='%s' size='80' /></p>

<input type='hidden' name='%s' value='%s' />
</form>
</body>
</html>
""" % (genJobOptionList(), REPORT_URL, REPORT_URL, emailAddr,
       cdrcgi.SESSION, session)

    return html

#----------------------------------------------------------------------
# Find imported documents
#----------------------------------------------------------------------
def findImportedDocs(firstJob, lastJob):
    """
    Find the document ID, version number, and date for each document
    in a range of one or more import job.

    Document ids are identified in the ctgov_import table, but
    version numbers are not identified anywhere.  The numbers
    have to be deduced by looking for versions created:

        After the earliest job start date in the range.
        Before the next job after the latest in the range.
        Having a comment like 'ImportCTGovProtocols: %'.

    Pass:
        firstJob - Earliest ctgov_import_job job id in the range.
        lastJob  - Last in range, may be the same as firstJob.

    Return:
        List of triples of:
            Document ID
            Version number
            Version creation date
    """
    conn   = None
    cursor = None
    # Connect
    try:
        conn   = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
    except cdrdb.Error, info:
        cdrcgi.bail("Unable to connect to retrieve doc IDs: %s" % str(info))

    # Find the date_time of the firstJob
    try:
        cursor.execute("SELECT dt FROM ctgov_import_job WHERE id = %d" \
                        % firstJob)
        firstDate = cursor.fetchone()[0]
    except cdrdb.Error, info:
        cdrcgi.bail("Unable to find date of first job: %s" % str(info),
                    logfile=LF)

    # Find date_time of the next job after the last in range
    # If none, use today's date_time
    try:
        cursor.execute("SELECT id, dt FROM ctgov_import_job WHERE id = %d" \
                        % (lastJob + 1))
        limitJob = cursor.fetchone()
        if limitJob:
            limitDate  = limitJob[1]
        else:
            limitDate  = time.strftime("%Y-%m-%d %H:%M:%S")
    except cdrdb.Error, info:
        cdrcgi.bail("Unable to find date of job after last: %s" % str(info),
                    logfile=LF)

    # Find doc IDs in the requested range
    try:
        cursor.execute("""
         SELECT d.cdr_id AS id, max(j.dt) AS dt
           INTO #ctgov_diff_temp
           FROM ctgov_import d,
                ctgov_import_event e,
                ctgov_import_job j
          WHERE d.nlm_id = e.nlm_id
            AND e.job = j.id
            AND j.id <= %d
            AND j.id >= %d
       GROUP BY d.cdr_id
            """ % (lastJob, firstJob))
    except cdrdb.Error, info:
        cdrcgi.bail("Unable to select doc IDs: %s" % str(info),
                    logfile=LF)

    # Find the latest version number in range for each doc
    try:
        cursor.execute("""
         SELECT v.id, MAX(v.num), t.dt
           FROM doc_version v, #ctgov_diff_temp t
          WHERE v.id = t.id
            AND v.dt > '%s'
            AND v.dt < '%s'
            AND v.comment LIKE 'ImportCTGovProtocols: %%'
       GROUP BY v.id, t.dt""" % (firstDate, limitDate))
        docIdVer = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Unable to select version numbers: %s" % str(info),
                    logfile=LF)

    cursor.close()

    return docIdVer

#----------------------------------------------------------------------
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Main processing
#----------------------------------------------------------------------
if __name__ == "__main__":
    # Handle request to jump elsewhere
    if request == cdrcgi.MAINMENU:
        cdrcgi.navigateTo("Admin.py", session)
    elif request == CTGOV_MENU:
        cdrcgi.navigateTo("CTGov.py", session)
    elif request == "Log Out":
        cdrcgi.logout(session)

    # If a batch job is already running, wait
    countRunning = 0
    try:
        # Gets number of active Global Change jobs
        countRunning = cdrbatch.activeCount(JOB_NAME)
    except cdrbatch.BatchException, e:
        cdrcgi.bail (str(e), logfile=LF)
    if countRunning > 0:
        cdrcgi.bail ("""
    Another version of this report appears to be currently runninge.<br>
    Please wait until it completes before starting another.<br>
    See <a href='getBatchStatus.py?Session=%s&jobName=%s&jobAge=1'>
    <u>Batch Status Report</u></a>
    or go to the CDR Administration menu and select 'View Batch Job Status'.</p>
    <p><p><p>""" % (session, JOB_NAME))

    # If no fields loaded, display the input form
    if not importJobs:
        cdrcgi.sendPage(genInputForm(session))

    # Do some validation
    if diffFmt not in ('XDiff', 'UDiff'):
        cdrcgi.bail("Internal error: Unrecognized diffFmt '%s'" % diffFmt,
                    logfile=LF)

    # Arguments passed to batch job
    args = ( ('importJobs', importJobs), ('diffFmt', diffFmt) )

    # DEBUG
    cdr.logwrite("type(importJobs)=%s" % type(importJobs))
    cdr.logwrite("importJobs=%s" % str(importJobs))
    cdr.logwrite("type(args)=%s" % type(args))
    cdr.logwrite("args=%s" % str(args))

    # Create and launch the batch job
    job = cdrbatch.CdrBatch(jobName=JOB_NAME, command=JOB_PATH,
                            args=args, email=emails)
    try:
        job.queue()
    except Exception, e:
        cdrcgi.bail("Unable to launch batch job: " + str(e), logfile=LF)

    # Report to user
    title   = "CDR Administration"
    section = "Imported CTGovProtocols vs. CWDs"
    script  = "CTGovUpdateReport.py"
    buttons = [CTGOV_MENU, cdrcgi.MAINMENU, LOGOUT]
    html    = cdrcgi.header(title, title, section, script, buttons) + \
"""
<p>The job has been started.</p>
<p>Output will be written to: <a href='%s'>%s</a>.</p>
<p>If an email address was provided, email will be sent when the
report is complete.</p>
</form>
</body>
</html>
""" % (REPORT_URL, REPORT_URL)
    cdrcgi.sendPage(html)
