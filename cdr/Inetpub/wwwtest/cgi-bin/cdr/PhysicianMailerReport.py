#----------------------------------------------------------------------
#
# $Id: PhysicianMailerReport.py,v 1.1 2002-03-02 12:37:13 bkline Exp $
#
# Menu for mailer reports.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
jobId   = fields.getvalue("JobId") or None
title   = "CDR Administration"
section = "Physician Mailer Report"
SUBMENU = "Report Menu"
buttons = session and [SUBMENU, cdrcgi.MAINMENU] or []
header  = cdrcgi.header(title, title, section, "PhysicianMailerReport.py", 
                        buttons)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Mailers.py", session)

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrPublishing')
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Display report if we have a specific request.
#----------------------------------------------------------------------
if jobId:
    try:
        cursor = conn.cursor()
        cursor.execute("""\
  SELECT recip.value,
         zip.value
    FROM query_term recip
    JOIN query_term job
      ON job.doc_id = recip.doc_id
    JOIN query_term zip
      ON zip.doc_id = job.doc_id
   WHERE recip.path = '/Mailer/Recipient'
     AND job.path   = '/Mailer/JobId'
     AND zip.path   = '/Mailer/Address/PostalAddress/PostalCode_ZIP'
     AND job.value  = %s
ORDER BY zip.value""" % jobId)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("No mailer tracking documents found for job %s" % 
                        jobId)
        html = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <TABLE>
   <TR>
    <TH>Postal Code</TH>
    <TH>Physician</TH>
   </TR>""" % (cdrcgi.SESSION, session and session or '')
        for row in rows:
            html += """\
   <TR>
    <TD>%s</TD>
    <TD>%s</TD>
   </TR>""" % (row[1], row[0])
        html += "</TABLE></FORM></BODY></HTML>"
        cdrcgi.sendPage(header + html)
    except cdrdb.Error, info:
        cdrcgi.bail('Failure executing database query: %s' % info[1][0])

#----------------------------------------------------------------------
# Otherwise put up the form.
#----------------------------------------------------------------------
form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <INPUT NAME='JobId'>""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
