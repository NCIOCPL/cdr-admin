#----------------------------------------------------------------------
#
# $Id: NewlyPublishedTrials.py,v 1.1 2002-03-20 14:08:19 bkline Exp $
#
# Report on newly published trials in batch.
#
# $Log: not supported by cvs2svn $
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
# We have a report request.  Honor it.
#----------------------------------------------------------------------
"""
cnPath = "/InScopeProtocol/ProtocolDetail/StudyCategory/StudyCategoryName"
ctPath = "/InScopeProtocol/ProtocolDetail/StudyCategory/StudyCategoryType"
stPath = "/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus"
idPath = "/InScopeProtocol/ProtocolIDs/PrimaryID/IDString"
"""

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
# Find out whether the last thing we sent to Cancer.gov for these 
# documents was a publish ('Export') or an unpublish ('Remove') event.
#----------------------------------------------------------------------
try:
    """cursor.execute(""\
        SELECT ppd1.doc_id,
               pp1.pub_subset
          INTO #foo
          FROM pub_proc_doc ppd1
          JOIN pub_proc pp1
            ON pp1.id = ppd1.pub_proc
          JOIN pub_proc_doc ppd2
            ON ppd2.doc_id = ppd1.doc_id
         WHERE ppd2.pub_proc = ?
           AND pp1.id = (SELECT MAX(pp3.id)
                           FROM pub_proc pp3
                           JOIN pub_proc_doc ppd3
                             ON ppd3.doc_id = ppd1.doc_id
                            AND ppd3.pub_proc = pp3.id
                           JOIN query_term ps
                             ON ps.doc_id = pp3.pub_system
                          WHERE pp3.id < ppd2.pub_proc
                            AND ps.path = '/PublishingSystem/SystemName'
                            AND ps.value = 'Primary'
                            AND pp3.pub_subset IN ('Export', 'Remove'))"",
                          jobId)
    #conn.commit()
    cursor.execute("SELECT * FROM #foo")
    numRows2 = len(cursor.fetchall())
    cdrcgi.bail("first query: %d; second query: %d" % (numRows, numRows2))
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving publishing history: %s' % info[1][0])

#----------------------------------------------------------------------
# Pull together the information needed for the report.
#----------------------------------------------------------------------
try:
    cursor.execute(""\
 SELECT DISTINCT ppd.doc_id,
                 cat.value,
                 stat.value,
                 id.value
            FROM pub_proc_doc ppd
            JOIN query_term cat
              ON cat.doc_id = ppd.doc_id
             AND cat.path = '%s'
            JOIN query_term cat_type
              ON cat_type.doc_id = ppd.doc_id
             AND cat_type.path = '%s'
             AND LEFT(cat_type.node_loc, 8) = LEFT(cat.node_loc, 8)
            JOIN query_term stat
              ON stat.doc_id = ppd.doc_id
             AND stat.path = '%s'
            JOIN query_term id
              ON id.doc_id = ppd.doc_id
             AND id.path = '%s'
           WHERE ppd.pub_proc = ?
             AND ppd.doc_id NOT IN (SELECT doc_id
                                      FROM #prev_event
                                     WHERE pub_subset = 'Export')
        ORDER BY cat.value,
                 id.value,
                 stat.value"" % (cnPath,
                                  ctPath,
                                  stPath,
                                  idPath),
                                  jobId)"""
    cursor.callproc("cdr_newly_pub_trials", jobId)
    #cursor.execute("{call cdr_newly_pub_trials(?)}", (jobId,))
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
