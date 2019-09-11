#----------------------------------------------------------------------
# Reports on audit trail content.
# BZIssue::1283 - add support for searching by user
#----------------------------------------------------------------------
import cdr, cdrcgi, cgi, time
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate')   or None
docType  = fields and fields.getvalue('DocType')  or None
user     = fields and fields.getvalue('User')     or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "ActivityReport.py"
title   = "CDR Administration"
section = "Document Activity Report"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())

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
# Validate some user input
#----------------------------------------------------------------------
# cgi.escape of dates will not be required after this validation
if fromDate:
    if not cdr.strptime(fromDate, '%Y-%m-%d'):
        cdrcgi.bail('Start Date must be valid date in YYYY-MM-DD format')
if toDate:
    if not cdr.strptime(toDate, '%Y-%m-%d'):
        cdrcgi.bail('End Date must be valid date in YYYY-MM-DD format')
if docType:
    if docType not in cdr.getDoctypes(session):
        cdrcgi.bail('Unknown doc type requested: "%s"' % cgi.escape(docType))

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not fromDate or not toDate:
    toDate   = time.strftime("%Y-%m-%d", now)
    then     = list(now)
    then[2] -= 6
    then     = time.localtime(time.mktime(then))
    fromDate = time.strftime("%Y-%m-%d", then)
    docTypes = cdr.getDoctypes(session)
    if type(docTypes) in [type(""), type(u"")]:
        cdrcgi.bail(docTypes)
    if fromDate < cdrcgi.DAY_ONE: fromDate = cdrcgi.DAY_ONE
    form = f"""\
   <input type="hidden" name="{cdrcgi.SESSION}" value="{session}">
   <table border="0">
    <tr>
     <td><b>User:&nbsp;</b></td>
     <td><input name="User" value="">&nbsp;</TD>
    </tr>
    <tr>
     <td><b>Document Type:&nbsp;</b></td>
     <td>
      <select name="DocType">
      <option value="" selected>All Types</option>
"""
    for docType in docTypes:
        form += f"""\
      <option value="{docType}">{docType} &nbsp;</option>
"""
    form += f"""\
    </tr>
    <tr>
     <td><b>Start Date:&nbsp;</b></td>
     <td><input name="FromDate" value="{fromDate}">&nbsp;
         (use format YYYY-MM-DD for dates, e.g. {cdrcgi.DAY_ONE})</td>
    </tr>
    <tr>
     <td><b>End Date:&nbsp;</b></td>
     <td><input name="ToDate" value="{toDate}">&nbsp;</td>
    </tr>
   </table>
  </form>
 </body>
</html>
"""
    cdrcgi.sendPage(header+form)

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
headerDocType = docType and ("%s Documents" % docType) or "All Document Types"
reportDate = time.strftime("%m/%d/%Y", now)
html = [f"""\
<!DOCTYPE html>
<html>
 <head>
  <title>Document Activity Report {headerDocType} -- {reportDate}</title>
  <style>
   body    {{ font-family: Arial, Helvetica, sans-serif }}
   span.ti {{ font-size: 14pt; font-weight: bold }}
   th      {{ text-align: center; vertical-align: top;
             font-size: 12pt; font-weight: bold }}
   td      {{ text-align: left; vertical-align: top;
             font-size: 12pt; font-weight: normal }}
  </style>
 </head>
 <body>
  <center>
   <span class="ti">CDR Document Activity</span>
   <br />
   <span class="ti">From {fromDate} to {toDate}</span>
  </center>
  <br />
  <br />
  <table border="1" cellspacing="0" cellpadding="2">
   <tr>
    <th>Who</th>
    <th>When</th>
    <th>Action</th>
    <th>DocType</th>
    <th>DocID</th>
    <th>DocTitle</th>
    <th>Comment</th>
   </tr>
"""]

#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
if fromDate < cdrcgi.DAY_ONE: fromDate = cdrcgi.DAY_ONE
try:
    # Create array of question mark parameter value substitutions
    # Avoids SQL injection vulnerability found by AppScan on previous version
    qmarkVals = [fromDate, toDate]
    userQual  = ""
    if user:
        userQual = "AND u.name = ?"
        qmarkVals.append(user)
    dtQual = ""
    if docType:
        dtQual = "AND t.name = ?"
        qmarkVals.append(docType)

    # Execute dynamically built query
    conn     = db.connect()
    cursor   = conn.cursor()
    cursor.execute("""\
         SELECT a.document,
                u.name,
                u.fullname,
                a.dt,
                t.name,
                act.name,
                d.title,
                a.comment
           FROM audit_trail a
           JOIN usr u
             ON u.id = a.usr
           JOIN all_docs d
             ON d.id = a.document
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN action act
             ON act.id = a.action
          WHERE a.dt BETWEEN ? AND DATEADD(s, -1, DATEADD(d, 1, ?))
            %s
            %s
        ORDER BY a.dt DESC""" % (userQual, dtQual), qmarkVals)

    rows = cursor.fetchall()
except Exception as e:
    cdr.logwrite('DB Failure: info=%s' % e)
    cdrcgi.bail('Database connection failure: %s' % e)

template = f"{cdcgi.BASE}/QcReport.py?docId={{}}&{cdrcgi.SESSION}={session}"
for doc_id, user, fullname, when, doctype, action, title, comment in rows:
    cdr_id = cdr.normalize(doc_id)
    url = template.format(cdr_id)
    comment = cgi.escape(comment) if comment else "&nbsp;"
    html.append(f"""\
   <tr>
    <td nowrap="1">{fullname} ({user})</td>
    <td nowrap="1">{when}</td>
    <td nowrap="1">{action}</td>
    <td nowrap="1">{doctype}</td>
    <td nowrap="1"><a href="{url}">{cdr_id}</a></td>
    <td nowrap="1">{cgi.escape(title[:20])} ...</td>
    <td>{comment}</td>
   </tr>
""")
html.append("""\
  </table>
 </body>
</html>
""")
cdrcgi.sendPage("".join(html))
