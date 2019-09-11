#----------------------------------------------------------------------
# Make a blocked document active.
# Modified July 2015 as part of security sweep.
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi
import re

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
doc_id   = fields.getvalue(cdrcgi.DOCID) or ""
title    = "CDR Administration"
section  = "Unblock CDR Document"
buttons  = ["Unblock", cdrcgi.MAINMENU, "Log Out"]
script   = "UnblockDoc.py"
message  = error = None

#----------------------------------------------------------------------
# Scrub the document ID.
#----------------------------------------------------------------------
matches = re.findall(r"\d+", doc_id)
doc_id = matches and matches[0] or ""

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Handle request to unblock the document.
#----------------------------------------------------------------------
if request == "Unblock":
    if not doc_id:
        error = "Missing required document ID."
    else:
        try:
            oldStatus = cdr.getDocStatus('guest', doc_id)
            if oldStatus == 'I':
                try:
                    cdr.unblockDoc(session, doc_id)
                    message = "Successfully unblocked CDR%s" % doc_id
                except Exception as e:
                    error = e.message[0]
            else:
                error = "CDR%s was not blocked" % doc_id
        except Exception as e:
            error = e.message[0]

#----------------------------------------------------------------------
# Display the form for requesting that a document be unblocked.
#----------------------------------------------------------------------
page = cdrcgi.Page(title, subtitle=section, action=script, buttons=buttons,
                   session=session)
page.add("<fieldset>")
page.add(page.B.LEGEND("Specify document to be unblocked"))
if message:
    page.add(page.B.P(message, page.B.CLASS("warning")))
if error:
    page.add(page.B.P(error, page.B.CLASS("error")))
page.add_text_field(cdrcgi.DOCID, "Document ID")
page.add("</fieldset>")
page.send()
