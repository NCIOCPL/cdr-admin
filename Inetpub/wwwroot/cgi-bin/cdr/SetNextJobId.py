#----------------------------------------------------------------------
# Filename: SetNextJobId.py
# --------------------------
# Web interface for resetting the Next Job-ID
# 
# When the WCMS/Gatekeeper database gets refreshed from PROD the ID
# created as the next Job-ID on the lower tiers has likely already been
# used.  As a result the CDR publishing jobs can't be verified 
# anymore against the GK database.
#
# Example:
# On DEV the latest Job-ID is 1000, the PROD Job-ID is 1500. When the
# database for gatekeeper is updated the PROD Job-ID becomes the latest
# GK Job-ID.  The CDR sends a new publishing job with the next Job-ID
# 1002.  At this point *two* jobs exist in the GK DB, the job 1002 
# submitted in PROD *and* the job 1002 submitted from DEV.
# Trying to verify the DEV job will fail and therefore every successively 
# submitted publishing jobs will fail as well.
# In this case we can reset the Job-ID value on DEV to the highest 
# value found on PROD.
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
section = "Set Next Job-ID"
buttons = ['Submit', 'Cancel', cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "SetNextJobId.py", buttons)

#----------------------------------------------------------------------
# Get the current identity value for the pub_proc table
#----------------------------------------------------------------------
def getCurrentId():
    # Connect to database
    conn = cdrdb.connect()
    cursor = conn.cursor()

    query = "select IDENT_CURRENT( 'pub_proc' )"
    cursor.execute(query)
    row = cursor.fetchone()

    if not row:
        cdrcgi.bail("Problem finding current identity value")

    return int(row[0])


#----------------------------------------------------------------------
# Set the identity value for the pub_proc table
# This update can only be done using a stored proceedure
#----------------------------------------------------------------------
def setNewIdValue(newId):
    # Connect to database
    conn = cdrdb.connect()
    cursor = conn.cursor()

    try:
        query = ("EXEC cdr_set_next_job_ID @newID = %d" % newId)
        cursor.execute(query)
    except:
        return False

    return True


#----------------------------------------------------------------------
# Get the last job ID
#----------------------------------------------------------------------
def getLastJobId():
    # Connect to database
    conn = cdrdb.connect()
    cursor = conn.cursor()

    query = "Select max(id) from pub_proc"
    cursor.execute(query)
    row = cursor.fetchone()

    if not row:
        cdrcgi.bail("Problem finding last job ID")

    return int(row[0])


#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

# This tool can only be used by authorized users
if not cdr.canDo(session, "SET_SYS_VALUE"):
    cdrcgi.bail("Sorry, you are not authorized to set the max Job ID %s" % 
                                                                   session)

# We don't allow the update on the production server.  It's only needed
# on the lower tiers.
if cdr.isProdHost():
    cdrcgi.bail("Sorry, this tools is not available on the PROD server")

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Form parameters entered by user
#----------------------------------------------------------------------
setIdValue   = fields and fields.getvalue('SetCurrentIDValue') or None

# The new ID value has to be larger than the current value
# --------------------------------------------------------
if setIdValue:
    newIdValue = int(setIdValue)
    if not newIdValue > getCurrentId():
        cdrcgi.bail("New identity value must be larger than current value");

# Start building the form body here
# ---------------------------------
html = ''

# Has he already done everything and we've checked it?
if request == 'Submit':
    if setIdValue:
        dbSuccess = setNewIdValue(newIdValue)
        if not dbSuccess:
            cdrcgi.bail("Problem updating the current identity value")

    else:
        cdrcgi.bail("Input error, no new identity value provided");

    # Tell user and clear variables for another run if desired
    html = "<p>New value for next Job ID set to: %d </p>" % newIdValue
    setIdValue = None

elif request == 'Cancel':
    # Clear all variables, that will put us back to the first screen
    setIdValue = None

elif request == 'cdrcgi.MAINMENU':
    # Back to main menu
    cdrcgi.navigateTo('Admin.py', session)

#----------------------------------------------------------------------
# Display the user input page (again)
#----------------------------------------------------------------------
if (not setIdValue):

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
 span.label   { display: block; 
                float: left; 
                width: 25%%; }
 label  { display: block; 
          float: left; 
                width: 25%%; }

</style>


<fieldset>
<h3>Setting Next Job-ID (reseeding pub_proc)</h3>
<b>Note</b>:<br> 
This program can be used to set the next job-id used
after a Gatekeeper database has been refreshed from PROD.  
This tool is only needed on the lower tiers.

</fieldset>
<fieldset>
  <div>
  <span class="label">Last Job ID: </span>
  <span class="value">%s</span><br>
  <span class="label">Current ID Value: </span>
  <span class="value">%s</span><br>
  <label for='theId'>Next Job ID: </label>
  <input type='text' name='SetCurrentIDValue' size='10' id='theId' />
  </div>
</fieldset>
""" % (getLastJobId(), getCurrentId())

else:
    cdrcgi.bail("How did we get here?")

html += """
<input type='hidden' name='%s' value='%s' />
""" % (cdrcgi.SESSION, session)

cdrcgi.sendPage(header + html + "</FORM></BODY></HTML>")
