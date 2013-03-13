#----------------------------------------------------------------------
#
# $Id$
#
# Change the status of a batch or publishing job to a failed state.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Change Job Status"
buttons = ['Submit', 'Cancel', cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "FailBatchJob.py", buttons)

#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

if not cdr.canDo(session, "SET_SYS_VALUE"):
    cdrcgi.bail(
        "Sorry, you are not authorized to fail a publishing or batch job")

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Form parameters already entered by user
#----------------------------------------------------------------------
jobType = fields and fields.getvalue('JobType') or None
jobId   = fields and fields.getvalue('JobId') or None
failJob = fields and fields.getvalue('FailJob') or None

if jobId:
    jobId = int(jobId)
    if jobId < 1:
        cdrcgi.bail("Job ID must be a positive integer");

# Connect to database
conn = cdrdb.connect()
cursor = conn.cursor()

# Build form body here
html = ''

# Has he already done everything and we've checked it?
if request == 'Submit' and failJob == 'Yes':
    if jobId:
        if jobType == 'pubJob':
            updateQry = "UPDATE pub_proc SET status='Failure' WHERE id=?"
        elif jobType == 'batchJob':
            updateQry = "UPDATE batch_Job SET status='Aborted' WHERE id=?"
        else:
            cdrcgi.bail("Internal error, unknown jobType");

        cursor.execute(updateQry, jobId)
        conn.commit()

    else:
        cdrcgi.bail("Internal error, no jobId");

    # Tell user and clear variables for another run if desired
    html = "<p>Status for job %d has been changed.</p>" % jobId
    jobType = jobId = failJob = None

elif request == 'Cancel':
    # Clear all variables, that will put us back to the first screen
    jobType = jobId = failJob = None

elif request == 'cdrcgi.MAINMENU':
    # Back to main menu
    cdrcgi.navigateTo('Admin.py', session)

#----------------------------------------------------------------------
# Find out job type and ID
#----------------------------------------------------------------------
if (not jobType or not jobId):

    html += """
<style type='text/css'>
fieldset {
  margin: auto;
}
.error {
  font-size: 2em;
  font-color: red;
  padding: 60px;
}
</style>

<h2>Select a job type and job ID to set status to failed state</h2>

<p>Note: This program cannot be used to change a successful job to
a failed state.  Doing so could cause inconsistency in the database.
Its proper use is only to cleanup after a crash that left a publishing
or batch job in some initial or in-process state that is must be cleared
in order to unblock further jobs.</p>

<fieldset>
  <label for='theId'>Job ID</label>
  <input type='text' name='JobId' size='10' id='theId' />
  <label for='typePub'> Publishing Job</label>
  <input type='radio' name='JobType' value='pubJob' id='typePub' />
  <label for='typeBatch'> Batch Job</label>
  <input type='radio' name='JobType' value='batchJob' id='typeBatch' />
</fieldset>
"""

else:
    # Had jobId and type already, keep them for next round
    html += """
<input type='hidden' name='JobType' value='%s' />
<input type='hidden' name='JobId' value='%s' />
""" % (jobType, jobId)

    newStatus = fields and fields.getvalue('NewStatus') or None
    if not newStatus:
        # Get the existing values for the job
        if jobType == 'pubJob':
            cursor.execute("""
SELECT status, pub_subset, started, completed, output_dir, messages
  FROM pub_proc
 WHERE id = ?""", jobId)

            row = cursor.fetchone()
            if not row:
                cdrcgi.bail("Publishing job %d not found" % jobId)

            html += """
<h2>Data for publishing job %d</h2>
<table border='1'>
 <tr>
  <th>status</th><th>pub_subset</th><th>started</th><th>completed</th>
  <th>output_dir</th><th>messages</th>
 </tr>
 <tr>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
 </tr>
</table>
""" % (jobId,row[0],row[1],row[2],row[3],row[4],row[5])

            # Validate that change to failure is okay
            if row[0] == 'Success':
                html += """
<p class='error'>Successful jobs may not be changed to status = "Failure"</p>
"""
            elif row[0] == 'Failure':
                html += """
<p class='error'>Job status already = "Failure"</p>
"""
            else:
                html += """
<input type='hidden' name='FailJob' value='Yes'>
<p>Click Submit to change the status of this job to "Failure".</p>
"""

        else:
            # Job type is a batch job
            cursor.execute("""
SELECT status, name, started, status_dt, progress
  FROM batch_job
 WHERE id = ?""", jobId)

            row = cursor.fetchone()
            if not row:
                cdrcgi.bail("Batch job %d not found" % jobId)

            html += """
<h2>Data for batch job %d</h2>
<table border='1'>
 <tr>
  <th>id</th><th>status</th><th>name</th>
  <th>started</th><th>status_dt</th><th>progress</th>
 </tr>
 <tr>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
 </tr>
</table>
""" % (jobId,row[0],row[1],row[2],row[3],row[4])

            # Validate that change is okay to fail
            if row[0] == 'Completed':
                html += """
<p class='error'>Completed jobs may not be changed to status="Aborted"</p>
"""
            elif row[0] == 'Aborted':
                html += """
<p class='error'>Job status already = "Aborted"</p>
"""
            else:
                html += """
<input type='hidden' name='FailJob' value='Yes'
<p>Click Submit to change the status of this job to "Aborted".</p>
"""

html += """
<input type='hidden' name='%s' value='%s' />
""" % (cdrcgi.SESSION, session)

cdrcgi.sendPage(header + html + "</FORM></BODY></HTML>")
