#----------------------------------------------------------------------
#
# $Id$
#
# Gather information for reports on ExternalRef elements.
#
# Can be used to find broken links or to compare html/head/title
# elements of linked-to web pages with stored versions in
# ExternalRef/@SourceTitle attributes.
#
# BZIssue::5244 - URL Check report not working
# BZIssue::None - (JIRA::OCECDR-3651) - External Refs report
# JIRA::OCECDR-3800 - Appscan vulnerability remediation
#
#----------------------------------------------------------------------
import cgi
import cdr
import cdrdb
import cdrcgi
import cdrbatch

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
section   = "URL Check"
script    = "CheckUrls.py"
SUBMENU   = 'Report Menu'
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
email     = fields.getvalue('Email')
docType   = fields.getvalue('DocType')
audience  = fields.getvalue('Audience') or ''
language  = fields.getvalue('Language') or ''
jobType   = fields.getvalue('JobType')
doc_types = (
    ("", ""),
    ("GlossaryTermConcept", "Glossary Term Concept"),
    ("Summary", "Summary"),
    ("InScopeProtocol", "In-Scope Protocol"),
    ("CTGovProtocol", "CT.gov Protocol"),
    ("DrugInformationSummary", "Drug Information Summary"),
    ("Person", "Person"),
    ("ClinicalTrialSearchString", "Clinical Trials Search String"),
    ("Citation", "Citation"),
    ("MiscellaneousDocument", "Miscellaneous Document"),
    ("Organization", "Organization"),
)
audiences = (
    ("", ""),
    ("HP", "HP"),
    ("Pat", "Patient"),
)
languages = (
    ("", ""),
    ("EN", "English"),
    ("ES", "Spanish"),
)
job_types = (
    ("UrlErrs", "URL Errors", True),
    ("TitleMismatch", "Page Title Mismatches", False),
    ("AllTitles", "All Page Titles", False),
)
instructions = (
    "This report requires a while to complete. "
    "When the report processing has completed, email notification "
    "will be sent to the addresses specified below.  At least "
    "one email address must be provided.  If more than one "
    "address is specified, separate the addresses with a blank. "
    "The Document Type field is also required."
)

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
if not email or not email.strip() or not docType or not jobType:
    page = cdrcgi.Page(title, subtitle=section, buttons=buttons,
                       action=script, session=session)
    page.add(page.B.FIELDSET(page.B.P(instructions)))
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Required Fields"))
    page.add_select("DocType", "DocType", doc_types)
    page.add_text_field("Email", "Email", value=cdr.getEmail(session) or "")
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Required for Summary or Glossary"))
    page.add_select("Audience", "Audience", audiences)
    page.add_select("Language", "Language", languages)
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select Type of Report"))
    for value, label, checked in job_types:
        page.add_radio("JobType", label, value, checked=checked)
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Validate the form values. The expectation is that any bogus values
# will come from someone tampering with the form, so no need to provide
# the hacker with any useful diagnostic information.
#----------------------------------------------------------------------
for value, values in ((docType, doc_types), (audience, audiences),
                      (language, languages), (jobType, job_types)):
    if value not in [v[0] for v in values]:
        cdrcgi.bail("Corrupted form value")
if jobType == 'UrlErrs' and docType in ('Summary', 'GlossaryTermConcept'):
    if not audience:
        cdrcgi.bail('Audience not specified')
    if not language:
        cdrcgi.bail('Language not specified')

#----------------------------------------------------------------------
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
args = [('docType', docType),
        ('audience', audience),
        ('language', language),
        ('jobType', jobType)]
command = 'lib/Python/CdrLongReports.py'
batch = cdrbatch.CdrBatch(jobName="URL Check", command=command,
                          email=email.strip(), args=args)
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
batch.show_status_page(session, title, section, script, SUBMENU)
