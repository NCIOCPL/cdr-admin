#----------------------------------------------------------------------
# $Id: getBatchStatus.py,v 1.1 2002-08-02 03:41:37 ameyer Exp $
#
# CGI program for displaying the status of batch jobs.
#
# Administrator may use this to see past or current batch job
# status information.
#
# Program may be invoked with posted variables to display status
# to a user.  If no variables are posted, the program displays
# a form to get user parameters for the status request, then
# processes them.
#
# May post:
#   jobId     = ID of job in batch_jobs table.
#   jobName   = Name of job.
#   jobAge    = Number of days to look backwards for jobs.
#   jobStatus = One of the status strings in cdrbatch.py.
#
# As with many other CDR CGI programs, the same program functions
# both to display a form and to read its contents.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------

import cdr, cdrbatch, cgi, cdrcgi

# Parse form variables
fields = cgi.FieldStorage()
if not fields:
    cdrcgi.bail ("Unable to load form fields - should not happen!")

# Establish user session and authorization
session = cdrcgi.getSession(fields)
if not session:
    cdrcgi.bail ("Unknown or expired CDR session.")

# Is user cancelling request?
if fields.getvalue ("cancel", None):
    # Cancel button pressed.  Return user to admin screen
    cdrcgi.navigateTo ("Admin.py", session)

# See what we've got from user entry of calling program
jobId     = fields.getvalue ("jobId", None)
jobName   = fields.getvalue ("jobName", None)
jobAge    = fields.getvalue ("jobAge", None)
jobStatus = fields.getvalue ("jobStatus", None)

# Find out if user wants a new request
newreq = fields.getvalue ("newreq", None)

# If new request or no input parms, we need to output a form
if newreq or (not jobId and not jobName and not jobAge and not jobStatus):

    # Construct display headers in standard format
    html = cdrcgi.header ("CDR Batch Job Status Request",
                          "CDR Batch Job Status Request",
                          "View batch jobs",
                          "getBatchStatus.py")

    # Add saved session
    html += "<input type='hidden' name='%s' value='%s' />" % \
            (cdrcgi.SESSION, session)

    # Data entry form
    html += """
<p>Enter a job ID <i>or</i> any other parameters</p>
<table>
 <tr>
  <td align='right'>Job ID: </td>
  <td><input type='text' name='jobId' width='10' /></td>
 </tr>
 <tr>
  <td align='right'>Job name: </td>
  <td><input type='text' name='jobName' width='30' /></td>
 </tr>
 <tr>
  <td align='right'>Number of days to look back: </td>
  <td><input type='text' name='jobAge' width='3' /></td>
 </tr>
 <tr>
  <td align='right'>Job status: </td>
  <td><select name='jobStatus'>
       <option></option>
       <option>%s</option>
       <option>%s</option>
       <option>%s</option>
       <option>%s</option>
       <option>%s</option>
       <option>%s</option>
       <option>%s</option>
       <option>%s</option>
       <option>%s</option>
       <option>%s</option>
      </select></td>
 </tr>
</table>
<p><p>
<table border='0' align='center' cellpadding='6'>
 <tr>
  <td><input type='submit' name='submit' value='Submit' /></td>
  <td><input type='submit' name='cancel' value='Cancel' /></td>
 </tr>
</table>
</form>
</body>
</html>
""" % (cdrbatch.ST_QUEUED, \
       cdrbatch.ST_INITIATING, \
       cdrbatch.ST_IN_PROCESS, \
       cdrbatch.ST_SUSPEND, \
       cdrbatch.ST_SUSPENDED, \
       cdrbatch.ST_RESUME, \
       cdrbatch.ST_STOP, \
       cdrbatch.ST_STOPPED, \
       cdrbatch.ST_COMPLETED, \
       cdrbatch.ST_ABORTED)

    # Display the page and exit
    cdrcgi.sendPage (html)

# If we got here, we have parameters for the status display
# Get status information from the database
statusRows = cdrbatch.getJobStatus (idStr=jobId, name=jobName,
                                    ageStr=jobAge, status=jobStatus)

# Display results in a form
html = cdrcgi.header ("CDR Batch Job Status Review",
                      "CDR Batch Job Status Review",
                      "Batch status search results",
                      "getBatchStatus.py")

# Return current info to repeat report if requested
html += "<input type='hidden' name='%s' value='%s' />\n" % \
         (cdrcgi.SESSION, session)
if jobId:
    html += "<input type='hidden' name='jobId' value='%s' />\n" % jobId
if jobName:
    html += "<input type='hidden' name='jobName' value='%s' />\n" % jobName
if jobAge:
    html += "<input type='hidden' name='jobAge' value='%s' />\n" % jobAge
if jobStatus:
    html += "<input type='hidden' name='jobStatus' value='%s' />\n" % jobStatus

# Tell user if nothing found
if not len (statusRows):
    html += "<h3>Sorry, no batch jobs matched the criteria you entered</p>\n"

else:
    # Put results in a table for display
    html += """
<table border='1'>
 <tr>
  <td><b>ID</b></td>
  <td><b>Job name</b></td>
  <td><b>Started</b></td>
  <td><b>Status</b></td>
  <td><b>Last info</b></td>
  <td><b>Last message</b></td>
 </tr>
"""
    for row in statusRows:
        html += """
 <tr>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
 </tr>
""" % (row[0], row[1], row[2], row[3], row[4], row[5])

    html += "</table>\n"

# Whether we had results or not, close form
html += """
<p><p>
<table border='0' align='center' cellpadding='6'>
 <tr>
  <td><input type='submit' name='repeat' value='   Refresh   ' /></td>
  <td><input type='submit' name='newreq' value=' New Request ' /></td>
  <td><input type='submit' name='cancel' value='Back to Admin' /></td>
 </tr>
</table>
</form>
</body>
</html>
"""

# Display the page and exit
cdrcgi.sendPage (html)
