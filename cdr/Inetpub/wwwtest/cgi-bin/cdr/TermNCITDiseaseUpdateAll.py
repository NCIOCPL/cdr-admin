#----------------------------------------------------------------------
#
# $Id: TermNCITDiseaseUpdateAll.py
#
# Check all Drug/Agent terms and update with data from the NCI
# Thesaurus
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, time, NCIThes, os.path, cdrbatch, ExcelReader

try: # Windows needs stdio set for binary mode.
    import msvcrt
    msvcrt.setmode (0, os.O_BINARY) # stdin  = 0
    msvcrt.setmode (1, os.O_BINARY) # stdout = 1
except ImportError:
    pass


#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
radio     = fields.getvalue("Radio") or None
email     = fields and fields.getvalue("email") or None
title     = "CDR Administration"
instr     = "Update all Disease Terms from NCI Thesaurus"
script    = "TermNCITDiseaseUpdateAll.py"
SUBMENU   = "Report Menu"

#------- DEBUG SETTINGS ---------------
#session = '4767BD22-2E92FC-248-CK7LEVL5AMV3'
#radio = 'CheckUpdate'
#request = "Submit"
#--------------------------------------

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)
    
#----------------------------------------------------------------------
# Save the uploaded set.
#----------------------------------------------------------------------
def saveSet(filterDefFile):    
    if filterDefFile.file:
        bytes = filterDefFile.file.read()
    else:
        bytes = filterDefFile.value
        
    if not bytes:
        cdrcgi.bail("Empty file")
    #cdrcgi.bail("number of bytes: %d" % len(bytes))
    name = time.strftime('d:/cdr/uploads/DefinitionFilter-%Y%m%d%H%M%S.xls')
    try:
        f = open(name, 'wb')
        f.write(bytes)
        f.close()
    except Exception, e:
        cdrcgi.bail("Failure storing %s: %s" % (name, e))
    return name

#----------------------------------------------------------------------
# Send to backend process
#----------------------------------------------------------------------
def sendToBackEnd():
    
    name = ''
    command = 'lib/Python/CdrLongReports.py'
    doDBUpdate = 0
    if radio == "DoDataUpdate":
        doDBUpdate = 1

    try:
        filterDefFile = fields['FilterDefFile']
    except:
        filterDefFile = None
    
    if filterDefFile is not None:
        name = saveSet(filterDefFile)


    #------------ DEBUG ------------------------------------------------------------------------
    #excelOutputFile = time.strftime('d:\cdr\uploads\ImportResults-%Y%m%d%H%M%S.xls')
    #NCIThes.updateAllTerms(session,'d:\cdr\Utilities\DefinitionFilter.xls',excelOutputFile,0,1)
    #cdrcgi.bail("Done")
    #-------------------------------------------------------------------------------------------

    args = (('doDBUpdate', doDBUpdate),
        ('excelFile', name),
        ('drug', 0),
        ('session',session))

    batch = cdrbatch.CdrBatch(jobName = instr, command = command, email = email,
                              args = args)
    try:
        batch.queue()
    except Exception, e:
        cdrcgi.bail("Could not start job: " + str(e))
    jobId       = batch.getJobId()
    buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
    
    header      = cdrcgi.header(title, title, instr, '', ("Submit",SUBMENU,
                            cdrcgi.MAINMENU),
                                stylesheet = """\
      <style type='text/css'>
       body { font-family: Arial }
      </style>
     """)
    cdrcgi.sendPage(header + """\
       <h4>Report is being run in background processing</h4>
       <p>
        To monitor the status of the job, click this
        <a href='http://%s%s/getBatchStatus.py?%s=%s&jobId=%s'><u>link</u></a>
        or use the CDR Administration menu to select 'View
        Batch Job Status'.
       </p>
      </form>
     </body>
    </html>
    """ % (cdrcgi.WEBSERVER, cdrcgi.BASE, cdrcgi.SESSION, session, jobId))
        
            
if request == "Submit":
    sendToBackEnd()

#----------------------------------------------------------------------
# Show the page
#----------------------------------------------------------------------

header = cdrcgi.header(title, title, instr, script,
                           ("Submit",SUBMENU,
                            cdrcgi.MAINMENU),
                           formExtra = " enctype='multipart/form-data'",
                           numBreaks = 1)

form   = """\
   <input type='hidden' name='%s' value='%s'>
   
<table align=center>
<tr>
<td width=5%%>
</td>
<td width = 95%%>
   <p id = 'statusTxt' align = center>
   Select 'Submit Test' to see what will be updated.<br>
   Select 'Submit Update...' to update the data in the database.<br><br>
   </p>
</td>
</tr>
<tr></tr>
<tr>
<td></td>
<td align=center>
   <input type='radio' value='CheckUpdate' name='Radio' CHECKED>Submit Test
   &nbsp;&nbsp;&nbsp;&nbsp;
   <input type='radio' value='DoDataUpdate' name='Radio'>Submit Update
</td>
</tr>
</table>
<br><br>
<p>Enter an excel(.xls) file name or browse to select a file that will be used to map the concepts to the CDRIDs (Most likely DiseaseTermNCITMappings.xls):<br>
  <input type='file' name='FilterDefFile' size='60' maxsize='10000000' />
<br><br>
<p>Specify the email address to send notification(s) to:</p>
<b>Email Address:</b>&nbsp;<input name='email' style='width: 500px' value='%s'>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, cdr.getEmail(session))
cdrcgi.sendPage(header + form)
