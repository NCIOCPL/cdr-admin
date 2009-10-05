#----------------------------------------------------------------------
#
# $Id: MailerHistory.py,v 1.3 2005-03-17 12:54:19 bkline Exp $
#
# Reports on the history of mailers for a particular document.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/10/09 13:00:11  bkline
# Bumped up timeout for database query.
#
# Revision 1.1  2002/05/03 20:28:54  bkline
# New Mailer reports.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
docId      = fields and fields.getvalue('DocId')   or None
SUBMENU   = "Report Menu"
buttons   = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = "MailerHistory.py"
title     = "CDR Administration"
section   = "Mailer History"
header    = cdrcgi.header(title, title, section, script, buttons)

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
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not docId:
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s' />
   <BR />
   <B>Document ID:&nbsp;&nbsp;</B>
   <INPUT NAME='DocId' />
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Extract the document ID as an integer.
#----------------------------------------------------------------------
try:
    digits = re.sub(r'[^\d]', '', docId)
    id     = string.atoi(digits)
except:
    cdrcgi.bail("Invalid document ID: %s, %s" % (docId, digits))

#----------------------------------------------------------------------
# Get the document's title.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT title
              FROM document
             WHERE id = ?""", id)
    row = cursor.fetchone()
    if not row:
        cdrcgi.bail("No such document CDR%010d" % id)
    title = row[0]
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving document title: %s' % info[1][0])

#----------------------------------------------------------------------
# Build the report.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Mailer History Report - CDR%010d</title>
  <basefont face='Arial, Helvetica, sans-serif'>
 </head>
 <body>
  <center>
   <b>
    <font size='4'>Mailer History for CDR%010d</font>
   </b>
   <br />
   <b>
    <font size='4'>%s</font>
   </b>
  </center>
  <br />
  <br />
""" % (id, id, title)
   
#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT type.value,
                   sent.value,
                   checkin.value,
                   change.value,
                   sent.doc_id
              FROM query_term doc
              JOIN query_term type
                ON type.doc_id = doc.doc_id
              JOIN query_term sent
                ON sent.doc_id = doc.doc_id
   LEFT OUTER JOIN query_term checkin
                ON checkin.doc_id = doc.doc_id
               AND checkin.path = '/Mailer/Response/Received'
   LEFT OUTER JOIN query_term change
                ON change.doc_id = doc.doc_id
               AND change.path = '/Mailer/Response/ChangesCategory'
             WHERE type.path = '/Mailer/Type'
               AND sent.path = '/Mailer/Sent'
               AND doc.path = '/Mailer/Document/@cdr:ref'
               AND doc.int_val = ?
          ORDER BY sent.value""", id, 300)
    row = cursor.fetchone()
    if not row:
        cdrcgi.sendPage(html + """\
  <b>
   <font size='3'>No mailers have been sent for CDR%010d.</font>
  </b>
 </body>
</html>
""" % id)
    html += """\
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <td nowrap='1'>
     <b>
      <font size='3'>Doc ID</font>
     </b>
    </td>
    <td nowrap='1'>
     <b>
      <font size='3'>Mailer Type</font>
     </b>
    </td>
    <td nowrap='1'>
     <b>
      <font size='3'>Date Generated</font>
     </b>
    </td>
    <td nowrap='1'>
     <b>
      <font size='3'>Check-In Date</font>
     </b>
    </td>
    <td nowrap='1'>
     <b>
      <font size='3'>Change Category</font>
     </b>
    </td>
   </tr>
"""
    while row:
        html += """\
   <tr>
    <td align='top'>
     <font size='3'>CDR%d</font>
    </td>
    <td align='top'>
     <font size='3'>%s</font>
    </td>
    <td align='top'>
     <font size='3'>%s</font>
    </td>
    <td align='top'>
     <font size='3'>%s</font>
    </td>
    <td align='top'>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (row[4],
       row[0],
       row[1],
       row[2] or "&nbsp;",
       row[3] or "&nbsp;")
        row = cursor.fetchone()
except cdrdb.Error, info:
    cdrcgi.bail('Failure executing query: %s' % info[1][0])

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
