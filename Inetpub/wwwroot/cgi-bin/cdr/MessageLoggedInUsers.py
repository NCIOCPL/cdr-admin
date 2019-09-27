#----------------------------------------------------------------------
# Send a message to users currently logged in to the CDR.
#----------------------------------------------------------------------
import cdr, cdrcgi, cgi
from cdrapi import db
from html import escape as html_escape

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
fromAddr = fields and fields.getvalue("from")    or ''
subject  = fields and fields.getvalue("subject") or ''
body     = fields and fields.getvalue("body")    or ''
title    = "CDR Administration"
section  = "Send email message to users logged on to CDR (all fields required)"
script   = "MessageLoggedInUsers.py"
buttons  = ["Send Message", cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Log into the database.
#----------------------------------------------------------------------
try:
    conn = db.connect(user='CdrGuest')
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail('Database connection failure: %s' % e)

#----------------------------------------------------------------------
# Put up the form if no message yet.
#----------------------------------------------------------------------
if not subject or not body or not fromAddr:
    if not fromAddr:
        try:
            cursor.execute("""\
                    SELECT u.email
                      FROM usr u
                      JOIN session s
                        ON s.usr = u.id
                     WHERE s.name = ?""", session)
            row = cursor.fetchone()
            if row and row[0] and row[0].find('@') != -1: fromAddr = row[0]
        except Exception as e:
            cdrcgi.bail('Failure retrieving your email address: %s' % e)
    form = """\
   <input type='hidden' name='%s' value='%s'>
   <table>
    <tr>
     <td align='right'><b>From:&nbsp;</b></td>
     <td><input name='from' value='%s' size='95'></td>
    </tr>
    <tr>
     <td align='right'><b>Subject:&nbsp;</b></td>
     <td><input name='subject' value='%s' size='95'></td>
    </tr>
    <tr>
     <td align='right'><b>Message Body:&nbsp;</b></td>
     <td><textarea name='body' rows='20' cols='72'>%s</textarea></td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, fromAddr, html_escape(subject, 1),
       html_escape(body.replace('\r', '')))
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Get the address list.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
        SELECT DISTINCT u.email
          FROM session s
          JOIN usr u
            ON u.id = s.usr
         WHERE s.ended IS NULL
           AND u.email LIKE '%@%'""")
    recipients = []
    for row in cursor.fetchall():
        recipients.append(row[0])
except Exception as e:
    cdrcgi.bail('Failure retrieving email addresses: %s' % e)

#----------------------------------------------------------------------
# Send the message.
#----------------------------------------------------------------------
if not recipients:
    cdrcgi.bail("No one with an email address currently logged on")
# XXX DEBUGGING XXX
# body += "\n\nRecipients: " + str(recipients)
# recipients = cdr.getEmailList("Developers Notification")
try:
    opts = dict(subject=subject, body=body)
    message = cdr.EmailMessage(fromAddr, recipients, **opts)
    message.send()
except Exception as e:
    cdrcgi.bail(f"Exception encountered sending message: {e}")
toList = ''
for recip in recipients:
    toList += """\
   <li>%s</li>
""" % recip
cdrcgi.sendPage(header + """\
  <input type='hidden' name = '%s' value='%s'>
  <h3>Mail successfully sent to:</h3>
  <ul>
%s
  </ul>
 </body>
</html>""" % (cdrcgi.SESSION, session, toList))
