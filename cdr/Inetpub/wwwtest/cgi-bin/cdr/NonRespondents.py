#----------------------------------------------------------------------
#
# $Id: NonRespondents.py,v 1.1 2003-06-10 13:56:11 bkline Exp $
#
# Report on mailers which haven't been responded to (other than
# status and participant mailers).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, sys, time

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Non Respondents Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, section, "NonRespondents.py",
                         buttons, method = 'GET')
docType  = fields.getvalue("DocType")    or None
age      = fields.getvalue("Age")        or None

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
# Put up the request interface if appropriate.
#----------------------------------------------------------------------
if not docType or not age:
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <OL>
    <LI>Type of mailer:&nbsp;&nbsp;&nbsp;
     <SELECT NAME='DocType'>
      <OPTION VALUE='Organization'>Organization</OPTION>
      <OPTION VALUE='Person'>Person</OPTION>
      <OPTION VALUE='InScopeProtocol'>Protocol Summary</OPTION>
     </SELECT>
    </LI>
    <BR><BR><BR>
    <LI>Non-response time:&nbsp;&nbsp;&nbsp;
     <SELECT NAME='Age'>
      <OPTION VALUE='15'>15-29 days since last mailer</OPTION>
      <OPTION VALUE='30'>30-59 days since last mailer</OPTION>
      <OPTION VALUE='60'>over 60 days since last mailer</OPTION>
     </SELECT>
    </LI>
   </OL>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the report.
#----------------------------------------------------------------------
now = time.localtime()
startDate = list(now)
endDate   = list(now)
if age == "15":
    startDate[2] -= 29
    endDate[2]   -= 15
    ageString     = '15-29 days since last mailer'
elif age == "30":
    startDate[2] -= 59
    endDate[2]   -= 30
    ageString     = '30-59 days since last mailer'
else:
    startDate[0]  = 1990
    endDate[2]   -= 60
    ageString     = 'Over 60 days since last mailer'
startDate = time.mktime(startDate)
endDate   = time.mktime(endDate)
startDate = time.strftime("%Y-%m-%d", time.localtime(startDate))
endDate   = time.strftime("%Y-%m-%d 23:59:59.999", time.localtime(endDate))
try:
    cursor.execute("""\
        CREATE TABLE #last_mailers (doc_id INTEGER, mailer_id INTEGER)""")
    conn.commit()
    cursor.execute("""\
INSERT INTO #last_mailers
     SELECT q1.int_val, MAX(q1.doc_id)
       FROM query_term q1
       JOIN query_term q2
         ON q1.doc_id = q2.doc_id
       JOIN document d
         ON d.id = q1.int_val
       JOIN doc_type t
         ON t.id = d.doc_type
      WHERE t.name = ?
        AND q1.path = '/Mailer/Document/@cdr:ref'
        AND q2.path = '/Mailer/Sent'
        AND q2.value BETWEEN ? AND ?
   GROUP BY q1.int_val""", (docType, startDate, endDate), timeout = 300)
    conn.commit()
    cursor.execute("""\
        CREATE TABLE #no_reply (doc_id INTEGER, mailer_id INTEGER)""")
    conn.commit()
    cursor.execute("""\
INSERT INTO #no_reply
     SELECT lm.doc_id, lm.mailer_id
       FROM #last_mailers lm
      WHERE NOT EXISTS(SELECT *
                         FROM query_term q
                        WHERE q.doc_id = lm.mailer_id
                          AND q.path = '/Mailer/Response/Received')""",
                   timeout = 300)
    conn.commit()
    cursor.execute("""\
         SELECT recip_name.title, 
                #no_reply.doc_id, 
                base_doc.doc_id, 
                mailer_type.value, 
                mailer_sent.value, 
                response_received.value,
                changes_category.value
           FROM document recip_name
           JOIN query_term recipient
             ON recipient.int_val = recip_name.id
           JOIN #no_reply
             ON #no_reply.mailer_id = recipient.doc_id
           JOIN query_term base_doc
             ON base_doc.int_val = #no_reply.doc_id
           JOIN query_term mailer_type
             ON mailer_type.doc_id = base_doc.doc_id
           JOIN query_term mailer_sent
             ON mailer_sent.doc_id = base_doc.doc_id
LEFT OUTER JOIN query_term response_received
             ON response_received.doc_id = base_doc.doc_id
            AND response_received.path = '/Mailer/Response/Received'
LEFT OUTER JOIN query_term changes_category
             ON changes_category.doc_id = base_doc.doc_id
            AND changes_category.path = '/Mailer/Response/ChangesCategory'
          WHERE recipient.path = '/Mailer/Recipient/@cdr:ref'
            AND mailer_type.path = '/Mailer/Type'
            AND mailer_sent.path = '/Mailer/Sent'
            AND base_doc.path = '/Mailer/Document/@cdr:ref'
       ORDER BY recip_name.title, #no_reply.doc_id, base_doc.doc_id DESC""",
    timeout = 300)
    rows = cursor.fetchall()
except Exception, info:
    cdrcgi.bail("Database failure fetching report information: %s" % str(info))
if docType == "InScopeProtocol":
    docType = "Protocol Summary"
html = """\
<html>
 <head>
  <title>Mailer Non-Respondents Report</title>
  <style type='text/css'>
   h1 { font-family: Arial; font-size: 14pt; text-align: center; }
   tr { vertical-align: top; }
   th { font-family: Arial; font-size: 11pt; font-weight: bold;
        text-align: left; }
   td { font-family: Arial; font-size: 10pt; }
  </style>
 </head>
 <body>
  <h1>Mailer Non-Respondents Report<br>%s</h1>
  <br><br>
  <table border='0'>
   <tr>
    <th>Mailer Type</th>
    <th>%s</th>
   </tr>
   <tr>
    <th>Non response Time&nbsp;&nbsp;&nbsp;&nbsp;</th>
    <th>%s</th>
   </tr>
  </table>
  <br><br>
""" % (time.strftime("%B %d, %Y"), docType, ageString)
lastRecipName = ""
lastBaseDocId = None
if not rows:
    cdrcgi.bail("No data found for report")
for row in rows:
    if row[0] == lastRecipName:
        recipName = "&nbsp;"
    else:
        if lastRecipName:
            html += """\
  </table>
  <br>
"""
        html += """
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th nowrap='1' width='26%'>Recipient Name</th>
    <th nowrap='1' width='12%'>Base DocID</th>
    <th nowrap='1' width='12%'>Mailer DocID</th>
    <th nowrap='1' width='26%'>Mailer Type</th>
    <th nowrap='1' width='12%'>Generated Date</th>
    <th nowrap='1' width='12%'>Response Date</th>
   </tr>
"""
        recipName = lastRecipName = row[0]
        semicolon = recipName.find(";")
        if semicolon != -1:
            recipName = recipName[:semicolon]
        recipName = cgi.escape(cdrcgi.unicodeToLatin1(recipName))
    if row[1] == lastBaseDocId:
        baseDocId = "&nbsp;"
    else:
        baseDocId = "CDR%d" % row[1]
        lastBaseDocId = row[1]
    generatedDate = row[4] and row[4][:10] or "&nbsp;"
    responseDate  = row[5] and row[5][:10] or "&nbsp;"
    if row[6] == "Returned to sender":
        responseDate = "RTS"
    html += """
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>CDR%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (recipName, baseDocId, row[2], row[3], generatedDate, responseDate)
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
