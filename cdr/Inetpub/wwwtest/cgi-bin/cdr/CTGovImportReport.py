#----------------------------------------------------------------------
#
# $Id: CTGovImportReport.py,v 1.4 2004-01-23 15:52:23 bkline Exp $
#
# Stats on documents imported from ClinicalTrials.gov into CDR.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2004/01/22 00:26:31  bkline
# Added call to cdrcgi.getSession().
#
# Revision 1.2  2003/12/16 15:42:30  bkline
# Added section for failures creating new publishable versions.  Fixed
# typo in style section.
#
# Revision 1.1  2003/11/10 17:59:06  bkline
# Reports stats on documents imported from ClinicalTrials.gov into CDR.
#
#----------------------------------------------------------------------
import cdr, cdrdb, time, cgi, cdrcgi, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
action    = cdrcgi.getRequest(fields)
session   = cdrcgi.getSession(fields)
job       = fields and fields.getvalue('job') or None
title     = "CDR Administration"
section   = "CTGov Import/Update Stats"
SUBMENU   = "Reports Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header    = cdrcgi.header(title, title, section, "CTGovImportReport.py",
                          buttons, method = 'GET')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Establish a database connection.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()

#----------------------------------------------------------------------
# Let the user choose a job if she hasn't done so already.
#----------------------------------------------------------------------
if not job:
    cursor.execute("""\
    SELECT TOP 30 id, dt
      FROM ctgov_import_job
  ORDER BY dt DESC""")
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("No import jobs recorded")
    form = """\
   <b>Select import job:&nbsp;</b>
   <select name = 'job'>
"""
    for row in rows:
        form += """\
    <option value='%d'>%s</option>
""" % (row[0], row[1][:19])
    cdrcgi.sendPage(header + form + """\
   </select>
   <input type='hidden' name='%s' value='%s'>
  </form>
 </body>
</html>""" % (cdrcgi.SESSION, session))

#----------------------------------------------------------------------
# Gather the report data.
#----------------------------------------------------------------------
class Doc:
    def __init__(self, row):
        self.nlmId       = row[0]
        self.locked      = row[1] == 'Y'
        self.new         = row[2] == 'Y'
        self.needsReview = row[3] == 'Y'
        self.pubVersion  = row[4] == 'Y'
        self.cdrId       = row[5]
        self.title       = row[6]
        self.pubVFailed  = row[4] == 'F'
newTrials         = {}
pubVersionCreated = {}
needReview        = {}
noReviewNeeded    = {}
locked            = {}
pubVersionFailure = {}
cursor.execute("SELECT dt FROM ctgov_import_job where id = %s" % job)
dt = cursor.fetchone()[0][:19]
cursor.execute("""\
    SELECT e.nlm_id, e.locked, e.new, e.needs_review, e.pub_version,
           d.id, d.title
      FROM ctgov_import_event e
      JOIN ctgov_import i
        ON i.nlm_id = e.nlm_id
      JOIN document d
        ON d.id = i.cdr_id
     WHERE e.job = %s""" % job)
row = cursor.fetchone()
while row:
    doc = Doc(row)
    if doc.locked:
        locked[doc.nlmId] = doc
    elif doc.new:
        newTrials[doc.nlmId] = doc
    elif doc.pubVersion:
        pubVersionCreated[doc.nlmId] = doc
    elif doc.needsReview:
        needReview[doc.nlmId] = doc
    elif doc.pubVFailed:
        pubVersionFailure[doc.nlmId] = doc
    else:
        noReviewNeeded[doc.nlmId] = doc
    row = cursor.fetchone()

#----------------------------------------------------------------------
# Generate the report.
#----------------------------------------------------------------------
def makeSection(docs, label):
    html = """\
  <h2>%s &ndash; %d</h2>
""" % (label, len(docs))
    if docs:
        keys = docs.keys()
        keys.sort()
        html += """\
   <table border='1' cellpadding='2' cellspacing='0' width='100%'>
    <tr>
     <th align='left' width='120'>NCTID</th>
     <th align='left' width='100'>CDR DocId</th>
     <th align='left'>DocTitle</th>
    </tr>
"""
        for nlmId in keys:
            doc = docs[nlmId]
            html += """\
    <tr>
     <td valign='top'>%s</td>
     <td valign='top'>%d</td>
     <td valign='top'>%s</td>
    </tr>
""" % (doc.nlmId, doc.cdrId, cgi.escape(doc.title))
        html += """\
   </table>
   <br>
"""
    return html

html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>ClinicalTrials.gov Import/Update Statistics Report %s</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 14pt; font-weight: bold }
   h2   { font-size: 12pt; font-weight: bold }
  </style>
 </head>
 <body>
  <center>
   <h1>ClinicalTrials.gov Import/Update Statistics Report</h1>
   <h2>Import run on %s</h2>
   <br><br>
  </center>
""" % (dt, dt)
html += makeSection(newTrials, "New trials imported into CDR")
html += makeSection(needReview, "Updated trials that require review")
html += makeSection(pubVersionCreated,
                    "Updated trials with new publishable version created")
html += makeSection(pubVersionFailure,
                    "Updated trials for which publishable version could "
                    "not be created")
html += makeSection(noReviewNeeded,
                    "Other updated trials that do not require review")
html += makeSection(locked,
                    "Trials not updated because document was checked out")
cdrcgi.sendPage(html + """\
 </body>
</html>""")
