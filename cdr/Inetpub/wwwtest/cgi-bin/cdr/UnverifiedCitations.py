#----------------------------------------------------------------------
#
# $Id: UnverifiedCitations.py,v 1.2 2002-03-13 16:58:42 bkline Exp $
#
# Reports on citations which have not been verified.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/03/09 03:27:40  bkline
# Added report for unverified citations.
#
#----------------------------------------------------------------------
import cdr, cgi, cdrdb, cdrcgi, time, re

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)

#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Get some general values.
#----------------------------------------------------------------------
now = time.localtime(time.time())
try:
    cursor.execute("""\
            SELECT fullname
              FROM usr
              JOIN session
                ON session.usr = usr.id
             WHERE session.name = ?""", session)
    usr = cursor.fetchone()[0]
except:
    cdrcgi.bail("Unable to find current user name")

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Unverified Citations Report %s %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>Unverified Citations Report</font>
   </b>
   <br />
   <br />
   <font size='4'>%s</font>
  </center>
  <br />
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <td>
     <font size='4'>DocID</font>
    </td>
    <td>
     <font size='4'>Citation</font>
    </td>
    <td>
     <font size='4'>Comment</font>
    </td>
   </tr>
""" % (time.strftime("%m/%d/%Y", now), usr, time.strftime("%B %d, %Y", now))
   
#----------------------------------------------------------------------
# Find out which citations are unverified.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT DISTINCT doc_id
                       FROM query_term
                      WHERE path = '/Citation/VerificationDetails/Verified'
                        AND value = 'No'
                   ORDER BY doc_id""")
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting citation IDs: %s' % info[1][0])

#----------------------------------------------------------------------
# Add one row to the table for each unverified citation.
#----------------------------------------------------------------------
textPattern    = re.compile("<Text>(.*)</Text>")
commentPattern = re.compile("<Comment>(.*)</Comment>")
for row in rows:
    resp = cdr.filterDoc(session, ['name:Citation text and comment'], row[0])
    text = textPattern.search(resp[0])
    cmnt = commentPattern.search(resp[0])
    text = text and text.group(1) or 'Unable to retrieve citation title'
    cmnt = cmnt and cmnt.group(1) or '&nbsp;'
    html += """\
   <tr>
    <td valign='top'>
     <font size='3'>%d</font>
    </td>
    <td valign='top'>
     <font size='3'>%s</font>
    </td>
    <td valign='top'>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (row[0], cdrcgi.decode(text), cdrcgi.decode(cmnt))

#----------------------------------------------------------------------
# Display the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + """\
  </table>
  <br />
  <center>
   <font size='3'>%s</font>
  </center>
 </body>
</html>""" % usr)
