#----------------------------------------------------------------------
#
# $Id$
#
# Gather information for reports on ExternalRef elements.
#
# Can be used to find broken links or to compare html/head/title
# elements of linked-to web pages with stored versions in
# ExternalRef/@ExRefPageTitle attributes.
#
# BZIssue::5244 - URL Check report not working
# BZIssue::None - (JIRA::OCECDR-3651) - External Refs report
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, cdrbatch

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "URL Check"
SUBMENU = 'Report Menu'
buttons = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "CheckUrls.py", buttons,
                        method = 'GET')
email   = fields and fields.getvalue('Email') or None
docType = fields and fields.getvalue('DocType') or None
audience= fields and fields.getvalue('Audience') or ''
language= fields and fields.getvalue('Language') or ''
jobType = fields and fields.getvalue('JobType') or None

args = [('docType', docType),
        ('audience', audience),
        ('language', language),
        ('jobType', jobType)]

command = 'lib/Python/CdrLongReports.py'
docTypes = cdr.getDoctypes(session)

# Make sure audience and language has been selected for the two doc types
# -----------------------------------------------------------------------
if not audience and docType in ('Summary', 'GlossaryTermConcept'):
    cdrcgi.bail('Input Error: Audience not specified')

if not language and docType in ('Summary', 'GlossaryTermConcept'):
    cdrcgi.bail('Input Error: Language not specified')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Put up the request interface if appropriate.
#----------------------------------------------------------------------
if not email:
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>

   <fieldset>
   <p>
    This report requires a while to complete.
    When the report processing has completed, email notification
    will be sent to the addresses specified below.  At least
    one email address must be provided.  If more than one
    address is specified, separate the addresses with a blank.
   </p>
   </fieldset>

   <br>
   <fieldset>
    <legend>&nbsp;Select Document Type&nbsp;</legend>
     <div style="float: left; width:80px;">
     <b>Doc Type: </b>
     </div>
     <div style="float:left; margin-left:10px;">
     <select name='DocType'>
     <option value='' SELECTED>Select doctype</option>
     <option value='GlossaryTermConcept'>Glossary Term Concept</option>
     <option value='Summary'>Summary</option>
     <option value='InScopeProtocol'>InScopeProtocol</option>
     <option value='CTGovProtocol'>CTGovProtocol</option>
     <option value='DrugInformationSummary'>Drug Information Summary</option>
     <option value='Person'>Person</option>
     <option value='ClinicalTrialSearchString'>Clinical Trials Search String</option>
     <option value='Citation'>Citation</option>
     <option value='MiscellaneousDocument'>Miscellaneous Documents</option>
     <option value='Organization'>Organization</option>

""" % (cdrcgi.SESSION, session)

    #  <option value='%s'>%s &nbsp;</option>
    #for docType in docTypes:
    #    form += """
    #    <option value='%s'>%s &nbsp;</option>
#""" % (docType, docType)

    form += """\
    </select>
     <br>
     </div>
     <div style="margin-left:80px;">
     </div>
    <br><br>
    <b>Email address(es):&nbsp;&nbsp;&nbsp;</b>
    <br>
    <INPUT Name='Email' Size='42' value='%s'>

   </fieldset>
""" % cdr.getEmail(session)

    form += """\
   <fieldset>
    <legend>&nbsp;Select for Summary or Glossary&nbsp;</legend>
     <div>
     <div style="float: left; width: 80px;">
      <b>Audience: </b>
      </div>
      <div style="float: left; margin-left: 10px;">
      <select name="Audience">
       <option value='' SELECTED>Select audience</option>
       <option value='HP'>HP</option>
       <option value='Pat'>Patient</option>
      </select>
      </div>
      </div>

     <br><br>

     <div>
     <div style="float:left; width:  80px;">
      <b>Language: </b>
      </div>
      <div style="float: left; margin-left: 10px;">
      <select name="Language">
       <option value='' SELECTED>Select language</option>
       <option value='EN'>English</option>
       <option value='ES'>Spanish</option>
      </select>
      </div>
      </div>
   </fieldset>

   <fieldset>
    <legend>&nbsp;Select Type of Report&nbsp;</legend>
     <div style="float: left;">
     <strong>
      <input name='JobType' type='radio' value='UrlErrs' checked='checked'>
        URL Errors</input><br />
      <input name='JobType' type='radio' value='TitleMismatch'>
        Page Title Mismatches</input><br />
      <input name='JobType' type='radio' value='AllTitles'>
        All Page Titles</input>
     </div>
     </strong>
   </fieldset>
    <br><br>
"""

    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
batch = cdrbatch.CdrBatch(jobName = "URL Check",
                          command = command, email = email, args = args)
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId       = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'CheckUrls.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body     { font-family: Arial }
   *.uline  { text-decoration: underline;
              color: blue; }
  </style>
 """)
base = "http://%s%s" % (cdrcgi.WEBSERVER, cdrcgi.BASE)
cdrcgi.sendPage(header + """\
   <fieldset>
   <h4>Report has been queued for background processing</h4>
   <p>
    To monitor the status of the job, click this
    <a href='%s/getBatchStatus.py?%s=%s&jobId=%s'>
     <span class="uline">link</span></a>
    or use the CDR Administration menu to select 'View
    Batch Job Status'.
   </p>
   </fieldset>
  </form>
 </body>
</html>
""" % (base, cdrcgi.SESSION, session, jobId))
