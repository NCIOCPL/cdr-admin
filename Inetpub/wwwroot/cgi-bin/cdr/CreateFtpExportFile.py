#----------------------------------------------------------------------
#
# CreateFtpExportFile.py
# ------------------
# $Id: CreateFtpExportFile.py $
#
# Creating the file FtpExportData.txt in the output directory.
# This file is needed in order to run the JobmasterNoPub.py job.
# It contains a single job-id, the one for the weekly publishing job.
#----------------------------------------------------------------------
import sys, cdr, cgi, cdrcgi, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
jobId     = fields and fields.getvalue("jobid")           or None
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Create FtpExportData.txt file"
script    = "CreateFtpExport.py"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not jobId:
    header = cdrcgi.header(title, title, instr, script,
                           ("Submit", SUBMENU, cdrcgi.MAINMENU),
                           numBreaks = 1)
    form   = """\
   <input type='hidden' name='%s' value='%s'>
 
   <fieldset>
    <legend>&nbsp;Enter Job ID&nbsp;</legend>
    <label for="byHp"><b>Pub Job ID</b></label>
    <input name='jobid' type='text' id="jobid" value=''>
   </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

# Write the Job-id to file
# ------------------------
try:
    d = int(jobId)
except:
    cdrcgi.bail('You must enter a job-id')

try:
    OUTPUTFILE = 'd:/cdr/output/FtpExportData.txt'
    f = open(OUTPUTFILE, 'w')
    f.write("%d\n" % d)
    f.close()
except:
    cdrcgi.bail('Error creating file')
    
header = cdrcgi.header(title, title, instr, script,
                           numBreaks = 1)
form   = """\
  <b>Successfully created file</b>
  </form>
 </body>
</html>
"""
cdrcgi.sendPage(header + form)
