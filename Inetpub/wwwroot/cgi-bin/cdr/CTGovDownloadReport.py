#----------------------------------------------------------------------
# Stats on documents downloaded from ClinicalTrials.gov.
#----------------------------------------------------------------------
import cdr, cdrdb, time, cgi, cdrcgi, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
action    = cdrcgi.getRequest(fields)
session   = cdrcgi.getSession(fields)
fromDate  = fields and fields.getvalue('from-date') or None
toDate    = fields and fields.getvalue('to-date')   or None
title     = "CDR Administration"
section   = "CTGov Download Stats"
SUBMENU   = "Reports Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header    = cdrcgi.header(title, title, section, "CTGovDownloadReport.py",
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
# Let the user choose a date range if she hasn't done so already.
#----------------------------------------------------------------------
if not fromDate or not toDate:
    now  = time.localtime()
    then = list(now[:])
    then[1] -= 1
    then = time.localtime(time.mktime(then))
    then = time.strftime("%Y-%m-%d", then)
    now  = time.strftime("%Y-%m-%d", now)
    cdrcgi.sendPage(header + """\
   <table border='0'>
    <tr>
     <td align='right'><b>Start date:&nbsp;</td>
     <td><input name='from-date' value='%s'></td>
    </tr>
    <tr>
     <td align='right'><b>End date:&nbsp;</td>
     <td><input name='to-date' value='%s'></td>
    </tr>
   </table>
   <input type='hidden' name='%s'value='%s'>
  </form>
 </body>
</html>""" % (then, now, cdrcgi.SESSION, session))

#----------------------------------------------------------------------
# Request #1062: added dropped trials to the report.
#----------------------------------------------------------------------
class DroppedTrial:
    def __init__(self, nlmId, cdrId, disposition):
        self.nlmId       = nlmId
        self.cdrId       = cdrId
        self.disposition = disposition

def findDroppedTrials(cursor):
    droppedTrials = []
    cursor.execute("""\
        SELECT i.nlm_id, i.cdr_id, d.name
          FROM ctgov_import i
          JOIN ctgov_disposition d
            ON d.id = i.disposition
         WHERE dropped = 'Y'
      ORDER BY i.nlm_id""")
    for row in cursor.fetchall():
        droppedTrials.append(DroppedTrial(row[0], row[1], row[2]))
    return droppedTrials

#----------------------------------------------------------------------
# Gather the report data.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT dt, total_trials, new_trials, updated, unchanged, pdq_cdr,
           duplicates, out_of_scope, closed
      FROM ctgov_download_stats
     WHERE dt BETWEEN ? AND ?
  ORDER BY dt DESC""", (fromDate, toDate + " 23:59:59"))
rows = cursor.fetchall()
if not rows:
    cdrcgi.bail("No download jobs found between %s and %s" % (fromDate,
                                                              toDate))
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>ClinicalTrials.gov Download Statistics Report %s - %s</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 14pt; font-weight: bold }
   h2   { font-size: 12pt; font-weight: bold }
  </style>
 </head>
 <body>
  <center>
   <h1>ClinicalTrials.gov Download Statistics Report</h1>
   <h2>%s through %s</h2>
   <br>
""" % (fromDate, toDate, fromDate, toDate)
droppedTrials = findDroppedTrials(cursor)
if droppedTrials:
    html += """\
   <h2>These trials have been dropped by NLM</h2>
   <table border='1' cellpadding='2' cellspacing='0'>
    <tr>
     <th>NCT ID</th>
     <th>CDR ID</th>
     <th>Disposition</th>
    </tr>
"""
    for droppedTrial in droppedTrials:
        html += """\
    <tr>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
    </tr>
""" % (droppedTrial.nlmId,
       droppedTrial.cdrId and ("CDR%d" % droppedTrial.cdrId) or "None",
       droppedTrial.disposition)
    html += """\
   </table>
   <br><br>
"""
html += """\
   <table border='1' cellpadding='2' cellspacing='0'>
    <tr>
     <th>Date</th>
     <th>Total</th>
     <th>New</th>
     <th>Updates</th>
     <th>Unchanged</th>
     <th>PDQ/CDR</th>
     <th>Duplicates</th>
     <th>Out of scope</th>
     <th>Closed</th>
    </tr>
"""
for row in rows:
    html += """\
    <tr>
     <td>%s</td>
     <td align='right'>%d</td>
     <td align='right'>%d</td>
     <td align='right'>%d</td>
     <td align='right'>%d</td>
     <td align='right'>%d</td>
     <td align='right'>%d</td>
     <td align='right'>%d</td>
     <td align='right'>%d</td>
    </tr>
""" % (tuple([row[0][:10]] + row[1:]))
cdrcgi.sendPage(html + """\
   </table>
  </center>
 </body>
</html>
""")
