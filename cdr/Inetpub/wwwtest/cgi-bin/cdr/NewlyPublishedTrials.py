#----------------------------------------------------------------------
#
# $Id: NewlyPublishedTrials.py,v 1.2 2002-03-20 14:11:55 bkline Exp $
#
# Report on newly published trials in batch.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/03/20 14:08:19  bkline
# Report on newly published protocols.
#
#----------------------------------------------------------------------

import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
jobId   = fields and fields.getvalue('JobId') or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "NewlyPublishedTrials.py"
title   = "CDR Administration"
section = "Newly Published Trials Report"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())

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
if not jobId:
    pass

#----------------------------------------------------------------------
# Routine for generating HTML for top of a category break.
#----------------------------------------------------------------------
def openCat(category):
    return """\
   <tr>
    <td colspan='3'>&nbsp;</td>
   </tr>
   <tr>
    <td colspan='3'>
     <font size='4'>
      <b>%s</b>
     </font>
    </td>
   </tr>
   <tr>
    <td colspan='3'>&nbsp;</td>
   </tr>
   <tr>
    <td>
     <font size='3'>
      <b>Primary ID</b>
     </font>
    </td>
    <td>
     <font size='3'>
      <b>Current Status</b>
     </font>
    </td>
    <td>
     <font size='3'>
      <b>CDR DocID</b>
     </font>
    </td>
   </tr>
""" % category

#----------------------------------------------------------------------
# Routine for generating HTML for bottom of a category break.
#----------------------------------------------------------------------
def closeCat(category, numTrials):
    return """\
   <tr>
    <td colspan='3'>&nbsp;</td>
   </tr>
   <tr>
    <td colspan='3'>
     <font size='3'>Total # of %s trials in batch: %d</font>
    </td>
   </tr>
   <tr>
    <td colspan='3'>&nbsp;</td>
   </tr>
   <tr>
    <td colspan='3'><hr /></td>
   </tr>
""" % (category, numTrials)

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the date of the job.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
        SELECT completed
          FROM pub_proc
         WHERE id = ?""", jobId)
    row = cursor.fetchone()
    if not row[0]:
        cdrcgi.bail("Publication job %d has not completed" % jobId)
    pubDate = row[0]
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving job date: %s' % info[1][0])

#----------------------------------------------------------------------
# Extract the data for the report from the database.  Unfortunately,
# we are unable to invoke the SQL queries directly from this script,
# because of a bug in ADO, which can't handle nested queries and
# placeholders at the same time. :-(
#----------------------------------------------------------------------
    cursor.callproc("cdr_newly_pub_trials", jobId)
    cursor.nextset()
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure extracting report data: %s' % info[1][0])

#----------------------------------------------------------------------
# Start the HTML page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>List of Newly Published Trials in Batch - %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>List of Newly Published Trials in Batch</font>
   </b>
   <br />
   <b>
    <font size='3'>Publication Date: %s</font>
   </b>
   <br />
   <br />
   <b>
    <font size='3'>Published to: Cancer.gov, PDQ licensees</font>
   </b>
   <br />
   <b>
    <font size='3'>Total # of newly published trials in the batch: %d</font>
   </b>
  </center>
  <br />
  <br />
  <table border='0' cellspacing='0' cellpadding='2' width='90%%'>
""" % (time.strftime("%m/%d/%Y", now), pubDate, len(rows))
   
#----------------------------------------------------------------------
# Fill out the body of the report.
#----------------------------------------------------------------------
currentCat  = None
trialsInCat = 0
for row in rows:
    (docId, cat, stat, protId) = row
    if not cat: cat = "Uncategorized"
    if cat != currentCat:
        if trialsInCat:
            html += closeCat(currentCat, trialsInCat)
        currentCat  = cat
        trialsInCat = 0
        html += openCat(currentCat)
    trialsInCat += 1
    html += """\
   <tr>
    <td>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%010d</font>
    </td>
   </tr>
""" % (protId, stat, docId)

#----------------------------------------------------------------------
# Wrap it up and ship it out.
#----------------------------------------------------------------------
if trialsInCat:
    html += closeCat(currentCat, trialsInCat)
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
