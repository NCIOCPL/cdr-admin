#----------------------------------------------------------------------
#
# $Id$
#
# Make a blocked document active.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
id       = fields and fields.getvalue(cdrcgi.DOCID) or None
title    = "CDR Administration"
section  = "Unblock CDR Document"
buttons  = ["Unblock", cdrcgi.MAINMENU, "Log Out"]
script   = "UnblockDoc.py"
report   = u""

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
# Wrap an HTML element telling what happened.
#----------------------------------------------------------------------
def makeReport(what, color = 'green'):
    report = (u"<span style='font-weight: bold; font-family: Arial; "
              u"color: %s'>" % color)
    if type(what) in (type(""), type(u"")):
        what = [what]
    for piece in what:
        report += piece + u"<br>"
    report += u"</span>"
    return report

#----------------------------------------------------------------------
# Handle request to unblock the document.
#----------------------------------------------------------------------
if request == "Unblock":
    if not id:
        cdrcgi.bail("Missing required document ID.")
    try:
        oldStatus = cdr.getDocStatus('guest', id)
        if oldStatus == 'I':
            try:
                cdr.unblockDoc(session, id)
                report = makeReport("Successfully unblocked %s" %
                                    cdr.normalize(id))
            except Exception, e:
                report = makeReport(e.args[0], "red")
        else:
            report = makeReport("Document %s is not blocked" % id, "red")
    except Exception, e:
        report = makeReport(e.args[0], "red")
                     
#----------------------------------------------------------------------
# Display the form for merging two protocol documents.
#----------------------------------------------------------------------
header  = cdrcgi.header(title, title, section, script, buttons)
form = """\
%s
<br>Document ID:&nbsp;<input name='%s'>
<input type='hidden' name='%s' value='%s' >
""" % (report, cdrcgi.DOCID, cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</form></body></html>")
