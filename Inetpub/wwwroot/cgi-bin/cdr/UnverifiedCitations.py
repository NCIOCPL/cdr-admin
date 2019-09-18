#----------------------------------------------------------------------
# Reports on citations which have not been verified.
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, time, re
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)

#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn = db.connect()
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail('Database connection failure: %s' % e)

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
<!DOCTYPE html>
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
except Exception as e:
    cdrcgi.bail('Failure selecting citation IDs: %s' % e)

#----------------------------------------------------------------------
# Add one row to the table for each unverified citation.
#----------------------------------------------------------------------
textPattern    = re.compile("<FormattedReference>(.*)</FormattedReference>")
commentPattern = re.compile("<Comment>(.*)</Comment>")
for row in rows:
    resp = cdr.filterDoc(session, ['set:Denormalization Citation Set',
                                   'name:Copy XML for Citation QC Report'],
				   row[0])
    text = textPattern.search(resp[0])
    cmnt = commentPattern.search(resp[0])
    text = text and text.group(1) or 'Unable to retrieve citation title'
    cmnt = cmnt and cgi.escape(cmnt.group(1)) or '&nbsp;'
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
""" % (row[0], cgi.escape(text), cmnt)

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
