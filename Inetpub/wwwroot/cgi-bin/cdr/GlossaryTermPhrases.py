#----------------------------------------------------------------------
# Report on phrases matching specified glossary term.
#
# JIRA::OCECDR-3800 - eliminated security vulnerabilities
# JIRA::OCECDR-4183 - add ability to look for spanish terms
#----------------------------------------------------------------------
import cdr
import cdrbatch
import cdrcgi
from cdrapi import db
import cgi
import re

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
id       = fields.getvalue('Id')
name     = fields.getvalue('Name')
hp       = fields.getvalue('hp')
patient  = fields.getvalue('patient')
language = fields.getvalue("language") or "English"
email    = fields.getvalue("Email") or cdr.getEmail(session)
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "GlossaryTermPhrases.py"
title    = "CDR Administration"
section  = "Glossary Term Phrases Report"
command  = 'lib/Python/CdrLongReports.py'

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
# Parameter validation.
#----------------------------------------------------------------------
if hp and hp != "hp": cdrcgi.bail()
if patient and patient != "patient": cdrcgi.bail()
if id:
    digits = re.sub('[^\d]+', '', id)
    try:
        id = int(digits)
    except:
        id = ""

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not name and not id or not email or not (hp or patient):
    instructions = (
        "This report requires a few minutes to complete. "
        "A document ID or a term name must be provided. If you enter a name "
        "string which matches the start of more than one term name, you "
        "will be asked to select the term name for the report from the "
        "list of matching names. "
        "When the report processing has completed, email notification "
        "will be sent to all addresses specified below.  At least "
        "one email address must be provided.  If more than one "
        "address is specified, separate the addresses with a blank."
    )
    note = "The report can take several minutes to prepare; please be patient."
    page = cdrcgi.Page(title, subtitle=section, action=script,
                       buttons=buttons, session=session)
    page.add(page.B.FIELDSET(page.B.P(instructions)))
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Enter Document ID or Glossary Term Name"))
    page.add_text_field("Id", "Document ID", value=id or "")
    page.add_text_field("Name", "Term Name", value=name or "")
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Enter Required Email Address"))
    page.add_text_field("Email", "Email", value=email or "")
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Document Types (at least one is required)"))
    page.add_checkbox("hp", "Health Professional Summaries", "hp",
                      checked=hp and True or False)
    page.add_checkbox("patient", "Patient Summaries", "patient",
                      checked=patient and True or False)
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Language"))
    for lang in ("English", "Spanish"):
        checked = lang == language
        page.add_radio("language", lang, lang, checked=checked)
    page.add("</fieldset>")
    page.add(page.B.FIELDSET(page.B.P(note, page.B.CLASS("warning"))))
    page.send()

#----------------------------------------------------------------------
# Allow the user to select from a list of protocols matching title string.
#----------------------------------------------------------------------
def putUpSelection(rows):
    page = cdrcgi.Page(title, subtitle=section, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add_css("fieldset { width: 1000px; }")
    page.add(page.B.LEGEND("Select Term For Report"))
    for doc_id, name in rows:
        id_string = cdr.normalize(doc_id)
        label = "%s: %s" % (id_string, name)
        page.add_radio("Id", label, id_string)
    page.add("</fieldset>")
    page.add_hidden_field("Email", email or "")
    page.add_hidden_field("language", language)
    page.add_hidden_field("hp", hp or "")
    page.add_hidden_field("patient", patient or "")
    page.send()

#----------------------------------------------------------------------
# Get the document ID.
#----------------------------------------------------------------------
if not id:
    try:
        namePattern = name + "%"
        conn   = db.connect(timeout=300)
        cursor = conn.cursor()
        cursor.execute("""\
                SELECT DISTINCT d.id, d.title
                           FROM document d
                           JOIN doc_type t
                             ON t.id = d.doc_type
                          WHERE t.name = 'GlossaryTermName'
                            AND d.title LIKE ?""", namePattern)
        rows = cursor.fetchall()
    except Exception as e:
        cdrcgi.bail("Failure looking up GlossaryTermName '%s': %s" % (name, e))
    if len(rows) > 1: putUpSelection(rows)
    if len(rows) < 1: cdrcgi.bail("Unknown GlossaryTermName '%s'" % name)
    id = rows[0][0]

#----------------------------------------------------------------------
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
doctypes = []
doctype_fields = (
    (hp, "HPSummaries"),
    (patient, "PatientSummaries"),
)
doctypes = " ".join([name for field, name in doctype_fields if field])
args = (("id", str(id)), ("types", doctypes), ("language", language))
batch = cdrbatch.CdrBatch(jobName="Glossary Term Search", command=command,
                          email=email, args=args)
try:
    batch.queue()
except Exception as e:
    cdrcgi.bail("Could not start job: " + str(e))
batch.show_status_page(session, title, section, script, SUBMENU)
