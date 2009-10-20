#----------------------------------------------------------------------
#
# $Id$
#
# Generates report on mailers for which reponses have been recorded
# during a specified date range.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2003/05/08 20:22:07  bkline
# Style cleanup; added sort of report rows.
#
# Revision 1.1  2002/04/25 02:58:53  bkline
# New report for mailer checkin.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
fromDate   = fields and fields.getvalue('FromDate')   or None
toDate     = fields and fields.getvalue('ToDate')     or None
mailerType = fields and fields.getvalue('MailerType') or None
SUBMENU    = "Report Menu"
buttons    = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script     = "MailerCheckinReport.py"
title      = "CDR Administration"
section    = "Mailer Checkin"
header     = cdrcgi.header(title, title, section, script, buttons)
now        = time.localtime(time.time())

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
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Gather the list of mailer types from the query_term table.
#----------------------------------------------------------------------
def getMailerTypes():
    types = []
    try:
        cursor.execute("""\
            SELECT DISTINCT value
                       FROM query_term
                      WHERE path = '/Mailer/Type'
                   ORDER BY value""", timeout = 300)
        for row in cursor.fetchall():
            types.append(row[0])
    except cdrdb.Error, info:
        cdrcgi.bail('Failure fetching mailer types: %s' % info[1][0])
    return types

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not fromDate or not toDate:
    toDate      = time.strftime("%Y-%m-%d", now)
    then        = list(now)
    then[1]    -= 1
    then[2]    += 1
    then        = time.localtime(time.mktime(then))
    fromDate    = time.strftime("%Y-%m-%d", then)
    mailerTypes = getMailerTypes()
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Document Type:&nbsp;</B></TD>
     <TD>
      <SELECT NAME='MailerType'>
      <OPTION VALUE='' SELECTED>All Types</OPTION>
""" % (cdrcgi.SESSION, session)
    for mailerType in mailerTypes:
        form += """\
      <OPTION VALUE='%s'>%s &nbsp;</OPTION>
""" % (mailerType, mailerType)
    form += """\
    </TR>
    <TR>
     <TD><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2002-01-01)</TD>
    </TR>
    <TR>
     <TD><B>End Date:&nbsp;</B></TD>
     <TD><INPUT NAME='ToDate' VALUE='%s'>&nbsp;</TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (fromDate, toDate)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# We have a request; do it.
#----------------------------------------------------------------------
headerMailerType = mailerType and ("%s Mailers" % mailerType) or \
                                   "All Mailer Types"
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <style type='text/css'>
   body   { font-family: Arial,Helvetica,sans-serif; }
   h2     { font-size: 13.5pt; font-weight: bold; text-align: center; }
   td     { font-size: 11pt; text-align: left; }
   th     { font-size: 12pt; text-align: left; font-weight: bold; }
   td.r, 
   th.r   { text-align: right; }
  </style>
  <title>Mailer Checkin Report %s %s</title>
  <basefont face='Arial, Helvetica, sans-serif'>
 </head>
 <body>
  <h2>Mailer Responses Checked In<br>From %s to %s</h2>
  <br />
""" % (headerMailerType, time.strftime("%m/%d/%Y", now), fromDate, toDate)
   
#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
try:
    typeQual = mailerType and ("AND t.value = '%s'" % mailerType) or ""
    cursor.execute("""\
            SELECT t.value,
                   COUNT(DISTINCT t.doc_id)
              FROM query_term t
              JOIN query_term i
                ON i.doc_id = t.doc_id
             WHERE i.value BETWEEN ? AND ?
               AND i.path = '/Mailer/Response/Received'
               AND t.path = '/Mailer/Type'
               %s
          GROUP BY t.value""" % typeQual, (fromDate, toDate))
    totals = {}
    for mailerType, total in cursor.fetchall():
        totals[mailerType] = total
    cursor.execute("""\
            SELECT t.value,
                   c.value,
                   COUNT(*)
              FROM query_term t
              JOIN query_term c
                ON c.doc_id = t.doc_id
              JOIN query_term i
                ON i.doc_id = t.doc_id
             WHERE i.value BETWEEN ? AND ?
               AND i.path = '/Mailer/Response/Received'
               AND t.path = '/Mailer/Type'
               AND c.path = '/Mailer/Response/ChangesCategory'
               %s
          GROUP BY t.value, c.value
          ORDER BY t.value, c.value""" % typeQual, (fromDate, toDate))
    lastMailerType = None
    row            = cursor.fetchone()
    if not row:
        cdrcgi.sendPage(html + """\
  <b>
   <font size='3'>No matching checkins found.</font>
  </b>
 </body>
</html>
""")
    html += """\
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <th nowrap='1'>Mailer Type</th>
    <th nowrap='1'>Change Category</th>
    <th nowrap='1'>Count</th>
   </tr>
"""
    mailerTypeLabel = "&nbsp;"
    while row:
        mailerType, changeCategory, count = row
        if mailerType != lastMailerType:
            mailerTypeLabel = mailerType
            if lastMailerType:
                total = totals.get(lastMailerType, 0)
                html += """\
   <tr>
    <th class='r'>Total</td>
    <td>&nbsp;</td>
    <th class='r'>%d</td>
   </tr>
   <tr>
    <td colspan='3'>&nbsp;</td>
   </tr>
""" % total
            lastMailerType = mailerType
        html += """\
   <tr>
    <th>%s</td>
    <td>%s</td>
    <td class='r'>%d</td>
   </tr>
""" % (mailerTypeLabel, changeCategory, count)
        mailerTypeLabel = "&nbsp;"
        row = cursor.fetchone()
except cdrdb.Error, info:
    cdrcgi.bail('Failure executing query: %s' % info[1][0])

if lastMailerType:
    total = totals.get(lastMailerType, 0)
    html += """\
   <tr>
    <th class='r'>Total</td>
    <td>&nbsp;</td>
    <th class='r'>%d</td>
   </tr>
""" % total

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
