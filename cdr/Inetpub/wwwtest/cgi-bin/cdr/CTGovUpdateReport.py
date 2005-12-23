#----------------------------------------------------------------------
# Compare CTgovProtocol documents from an import job with the current
# publishable version of the the same documents.
#
# $Id: CTGovUpdateReport.py,v 1.1 2005-12-23 02:19:53 ameyer Exp $
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import time, cgi, cdr, cdrcgi, cdrdb, cdrxdiff

# Load fields from the submitted form, if any
fields     = cgi.FieldStorage()
request    = cdrcgi.getRequest(fields)
session    = cdrcgi.getSession(fields)
importJobs = fields and fields.getlist('importJobs') or None
diffFmt    = fields and fields.getvalue('diffFmt') or None

# Custom button labels
CTGOV_MENU = "CTGov Menu"
LOGOUT     = "Log Out"

# Num days to look backward for import jobs
# XXX DEBUGGING ON MAHLER REQUIRES A BIG NUMBER
JOB_DAYS   = 240

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
def genInputForm():
    """
    Create an input form for display to the user.

    Return:
        HTML form as a string.
    """
    # Build form
    title   = "CDR Administration"
    section = "CTGov Updates Report"
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

<input type='hidden' name='%s' value='%s' />
</form>
</body>
</html>
""" % (genJobOptionList(), cdrcgi.SESSION, session)

    return html

#----------------------------------------------------------------------
# Error reporting
#----------------------------------------------------------------------
def reportError(msg):
    # Write message to default error log file
    cdr.logwrite(msg)

    # And bail out with msg to user
    cdrcgi.bail(msg)

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
        reportError("Unable to find date of first job: %s" % str(info))

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
        reportError("Unable to find date of job after last: %s" % str(info))

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
        reportError("Unable to select doc IDs: %s" % str(info))

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
        reportError("Unable to select version numbers: %s" % str(info))

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

    # If no fields loaded, display the input form
    if not importJobs:
        cdrcgi.sendPage(genInputForm())

    # Convert job ids to numbers for min/max check
    jobNums = []
    for job in importJobs:
        jobNums.append(int(job))

    # Generate list of docId, verNum pairs from user selected jobs
    idVerDt = findImportedDocs(min(jobNums), max(jobNums))

    # Create an object for differencing the docs
    diffObj = None
    if   diffFmt == "XDiff": diffObj = cdrxdiff.XDiff()
    elif diffFmt == "UDiff": diffObj = cdrxdiff.UDiff()
    if not diffObj:
        reportError("Internal error: Unrecognized diffFmt '%s'" % diffFmt)
    # Put color info in the diff buffer, then fetch it out again
    if diffFmt == "XDiff":
        diffObj.showColors("newer version", "older version")
        colors = diffObj.getDiffText()
    else:
        # XXX Future
        colors = ""

    # Put the output into a sequence - will be converted to string at end
    buf = []

    # Output report header
    buf.append("""
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Imported CTGovProtocol vs. Current Working Documents Report</title>
  %s
 </head>
 <body>
 <h1>Imported CTGovProtocol vs. Current Working Documents</h1>

<h2>Date: %s</h2>

<p>
""" % (diffObj.getStyleHtml(), time.ctime()))

    if len(importJobs) == 1:
        buf.append(\
            "This report compares all documents imported by job number %s" % \
             importJobs[0][1])
    else:
        buf.append("""\
This report compares the last version of each document imported
between job number %s and job number %s
""" % (importJobs[0][1], importJobs[-1][1]))

    buf.append("""
against the current working document for each of the documents.</p>

<p>For each imported document, the report lists the:</p>
<ul>
 <li>Document ID.</li>
 <li>Version number of the version created by the import program.</li>
 <li>Date/time imported.</li>
 <li>Date/time of last update of the current working document.</li>
 <li>A difference report or a note that no differences were found.</li>
</ul>

<p>The documents are pre-filtered before comparing them so that
only significant fields are compared.</p>

<hr />
<center>
 %s
</center>
<hr />
""" % colors)

    # Counters
    docCount  = 0   # Total docs we compare
    diffCount = 0   # Total that were different from CWDs

    # Get a connection for efficiency
    try:
        conn   = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
    except cdrdb.Error, info:
        reportError("Unable to connect to DB to start run: %s" % str(info))

    # Run the difference report
    for (docId, docVer, docDt) in idVerDt:
        # Header for one document
        buf.append("""
<br /><font size="+1">%s version: %d dated: %s vs CWD dated: %s</font><br />
""" % \
                    (cdr.exNormalize(docId)[0], docVer, docDt,
                    cdr.getCWDDate(docId, conn)))

        # Do the diff
        diffText = diffObj.diff(doc1Id=docId, doc1Ver=docVer, doc2Ver=0,
               filter=['name:Extract Significant CTGovProtocol Elements'])
        if diffText:
            buf.append(diffText)
            buf.append("<br />")
            diffCount += 1
        else:
            buf.append("[No significant differences]")
        docCount += 1

    # Summary and termination
    buf.append("""
<center>
<hr />
<h2>Summary</h2>
<table border='2' cellpadding='10'>
 <tr>
  <th align='right'>Total documents processed: </th>
  <th>%d</th>
 </tr>
 <tr>
  <th align='right'>Documents with differences: </th>
  <th>%d</th>
 </tr>
</table>
</center>
</body>
</html>
""" % (docCount, diffCount))

    # Consolidate and output the report
    cdrcgi.sendPage("\n".join(buf))

