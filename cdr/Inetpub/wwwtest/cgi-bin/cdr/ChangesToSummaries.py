#----------------------------------------------------------------------
#
# $Id: ChangesToSummaries.py,v 1.1 2003-12-16 15:55:50 bkline Exp $
#
# Report of history of changes to a single summary.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, time, cgi, cdrcgi, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle  = "Changes To Summaries Report"
fields    = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session   = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action    = cdrcgi.getRequest(fields)
title     = "CDR Administration"
section   = "Changes To Summaries Report"
SUBMENU   = "Reports Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header    = cdrcgi.header(title, title, section, "ChangesToSummaries.py",
                          buttons, method = 'GET')
boardId   = fields.getvalue("BoardId")    or None
audience  = fields.getvalue("Audience")   or None
startDate = fields.getvalue("StartDate")  or None
endDate   = fields.getvalue("EndDate")    or None

#----------------------------------------------------------------------
# Build a picklist for editorial boards, including an option for All.
#----------------------------------------------------------------------
def getBoardList():
    try:
        cursor.execute("""\
            SELECT DISTINCT d.id, d.title
                       FROM document d
                       JOIN query_term q
                         ON q.doc_id = d.id
                      WHERE q.path = '/Organization/OrganizationType'
                        AND q.value = 'PDQ Editorial Board'
                   ORDER BY d.title""")
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Can't find any editorial boards.")
    except Exception, info:
        cdrcgi.bail("Database failure fetching editorial boards: %s" %
                    str(info))
    html = """\
     <SELECT NAME='BoardId'>
      <OPTION VALUE='' SELECTED='1'>All</OPTION>
"""
    for row in rows:
        html += """\
      <OPTION VALUE='%d'>%s</OPTION>
""" % (row[0], cgi.escape(row[1]))
    return html + """\
     </SELECT>"""

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
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except Exception, info:
    cdrcgi.bail("Exception connecting to database: %s" % str(info))

#----------------------------------------------------------------------
# If we don't have any information yet, put up the basic form.
#----------------------------------------------------------------------
if not startDate or not endDate or not audience:
    boardList = getBoardList()
    hpSel = patSel = ""
    if audience == "Health Professional":
        hpSel = " SELECTED='1'"
    elif audience == "Patient":
        patSel = " SELECTED='1'"
    if not endDate or not startDate:
        endDate = time.strftime("%Y-%m-%d")
        startDate = list(time.localtime())
        startDate[1] -= 1
        startDate[2] += 1
        startDate = time.mktime(startDate)
        startDate = time.localtime(startDate)
        startDate = time.strftime("%Y-%m-%d", startDate)
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>

  <TABLE>
   <TR>
    <TD ALIGN='right'>
     <B>PDQ Board:&nbsp;</B>
    </TD>
    <TD>
%s
    </TD>
   </TR>
   <TR>
    <TD ALIGN='right'>
     <B>Audience:&nbsp;</B>
    </TD>
    <TD>
     <INPUT TYPE='radio' NAME='Audience' VALUE='Health Professional'%s>
      Health Professional<BR>
     <INPUT TYPE='radio' NAME='Audience' VALUE='Patient'%s>Patient
    </TD>
   </TR>
   <TR>
    <TD ALIGN='right'>
     <B>Date Last Modified Range:&nbsp;</B>
    </TD>
    <TD>
     <TABLE BORDER='0'>
      <TR>
       <TD ALIGN='right'>
        <B>Start Date&nbsp;</B>
       </TD>
       <TD><INPUT SIZE='60' NAME='StartDate' VALUE='%s'></TD>
      </TR>
      <TR>
       <TD ALIGN='right'>
        <B>End Date&nbsp;</B>
       </TD>
       <TD><INPUT SIZE='60' NAME='EndDate' VALUE='%s'></TD>
      </TR>
     </TABLE>
    </TD>
   </TR>
  </TABLE>
""" % (cdrcgi.SESSION, session, boardList, hpSel, patSel, startDate, endDate)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

cdrcgi.bail("Sorry, that's as far as I've gotten!")

#----------------------------------------------------------------------
# If we have a title, use it to get a document ID.
#----------------------------------------------------------------------
if docTitle:
    param = "%s%%" % docTitle
    try:
        cursor.execute("""\
            SELECT d.id, d.title
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE d.title LIKE ?
               AND t.name = 'Summary'""", param)
        rows = cursor.fetchall()
    except Exception, info:
        cdrcgi.bail("Failure looking up document title: %s" % str(info))
    if not rows:
        cdrcgi.bail("No summary documents match %s" % docTitle)
    if len(rows) > 1:
        showTitleChoices(rows)

#----------------------------------------------------------------------
# From this point on we have what we need for the report.
#----------------------------------------------------------------------
#numYears = 2
#docId = 62978 #62906 #62978
startDate = list(time.localtime())
startDate[0] -= numYears
startDate = time.strftime("%Y-%m-%d", time.localtime(time.mktime(startDate)))
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("SELECT title FROM document WHERE id = ?", docId)
docTitle = cursor.fetchall()[0][0]
semicolon = docTitle.find(";")
if semicolon != -1:
    docTitle = docTitle[:semicolon]
cursor.execute("""\
    SELECT num, dt
      FROM doc_version
     WHERE id = ?
       AND dt >= ?
       AND publishable = 'Y'
  ORDER BY num""", (docId, startDate))
sections = []
lastSection = None
for row in cursor.fetchall():
    verDate = "%s/%s/%s" % (row[1][5:7], row[1][8:10], row[1][:4])
    resp = cdr.filterDoc('guest', [#'set:Denormalization Summary Set',
                                   'name:Summary Changes Report'], docId,
                         docVer = "%d" % row[0])
    if resp[0].strip():
        if not lastSection or resp[0] != lastSection:
            lastSection = resp[0]
            section = resp[0].replace("@@PubVerDate@@", verDate)
            sections.append(section)
sections.reverse()
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Summary Changes Report for CDR%010d - %s</title>
  <style type='text/css'>
   h1       { font-family: Arial, sans-serif; font-size: 16pt;
              text-align: center; font-weight: bold; }
   h2       { font-family: Arial, sans-serif; font-size: 14pt;
              text-align: center; font-weight: bold; }
   td.hdg   { font-family: Arial, sans-serif; font-size: 16pt;
              font-weight: bold; }
   p        { font-family: Arial, sans-serif; font-size: 12pt; }
   span.SectionRef { text-decoration: underline; font-weight: bold; }
  </style>
 </head>
 <body>
  <h1>History of Changes to Summary Report<br>
      Changes Made in the Last %d Year%s</h1>
  <table border='0' width = '100%%'>
   <tr>
    <td class='hdg'>%s</td>
    <td align='right' valign='top' class='hdg'>CDR%010d</td>
   </tr>
  </table>
""" % (docId,
       time.strftime("%B %d, %Y"),
       numYears,
       numYears and "s" or "",
       docTitle,
       docId)
for section in sections:
    html += section + "<br><hr><br>\n"
html += """
 </body>
</html>
"""

#print html
cdrcgi.sendPage(html)
