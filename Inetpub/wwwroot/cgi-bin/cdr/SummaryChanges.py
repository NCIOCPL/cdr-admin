#----------------------------------------------------------------------
# Report of history of changes to a single summary.
#----------------------------------------------------------------------
import cdr, time, cgi, cdrcgi, re
from cdrapi import db
from html import escape as html_escape

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle  = "History of Changes to Summary"
fields    = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session   = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action    = cdrcgi.getRequest(fields)
title     = "CDR Administration"
section   = "History of Changes to Summary"
SUBMENU   = "Reports Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header    = cdrcgi.header(title, title, section, "SummaryChanges.py",
                          buttons, method = 'GET')
docId     = fields.getvalue(cdrcgi.DOCID) or None
docTitle  = fields.getvalue("DocTitle")   or None
dateRange = fields.getvalue("DateRange")  or None
if docId:
    digits = re.sub('[^\d]+', '', docId)
    docId  = int(digits)
try:
    numYears = dateRange and int(dateRange) or 2
except:
    cdrcgi.bail("Invalid date range: %s" % dateRange)
if docTitle:
    docTitle = unicode(docTitle, "utf-8")

#----------------------------------------------------------------------
# Load common style information from repository.
#----------------------------------------------------------------------
def getCommonCssStyle():
    xslScript = """\
<?xml version="1.0"?>
<xsl:transform           xmlns:xsl = "http://www.w3.org/1999/XSL/Transform"
                           version = "1.0"
                         xmlns:cdr = "cips.nci.nih.gov/cdr"
           exclude-result-prefixes = "cdr">
 <xsl:output                method = "html"/>
 <xsl:include                 href = "cdr:name:Module:+STYLE+Default"/>
 <xsl:template               match = "/">
  <style type='text/css'>
   <xsl:call-template         name = "defaultStyle"/>
   h1       { font-family: Arial, sans-serif; font-size: 16pt;
              text-align: center; font-weight: bold; }
   h2       { font-family: Arial, sans-serif; font-size: 14pt;
              text-align: center; font-weight: bold; }
   td.hdg   { font-family: Arial, sans-serif; font-size: 16pt;
              font-weight: bold; }
   p        { font-family: Arial, sans-serif; font-size: 12pt; }
   body     { font-family: Arial; font-size: 12pt; }
   span.SectionRef { text-decoration: underline; font-weight: bold; }
  </style>
 </xsl:template>
</xsl:transform>
"""
    response = cdr.filterDoc('guest', xslScript, doc = "<dummy/>", inline = 1)
    if type(response) in (type(""), type(u"")):
        cdrcgi.bail("Failure loading common CSS style information: %s" %
                    response)
    return response[0]

#----------------------------------------------------------------------
# More than one matching title; let the user choose one.
#----------------------------------------------------------------------
def showTitleChoices(choices):
    form = """\
   <H3>More than one matching document found; please choose one.</H3>
"""
    for choice in choices:
        form += """\
   <INPUT TYPE='radio' NAME='DocId' VALUE='CDR%010d'>[CDR%010d] %s<BR>
""" % (choice[0], choice[0], html_escape(choice[1]))
    cdrcgi.sendPage(header + form + """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='DateRange' VALUE='%d'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, numYears))

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
# If we don't have any information yet, put up the basic form.
#----------------------------------------------------------------------
if not docId and not docTitle:
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>

  <TABLE>
   <TR>
    <TD ALIGN='right'>Document Title:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocTitle'></TD>
   </TR>
   <TR>
    <TD ALIGN='right'>Doc ID:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocId'></TD>
   </TR>
   <TR>
    <TD ALIGN='right'>Date Range:&nbsp;</TD>
    <TD><INPUT NAME='DateRange' VALUE='2' SIZE='2'></TD>
   </TR>
  </TABLE>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn = db.connect(user='CdrGuest')
    cursor = conn.cursor()
except Exception as info:
    cdrcgi.bail("Exception connecting to database: %s" % str(info))

#----------------------------------------------------------------------
# If we have a title, use it to get a document ID.
#----------------------------------------------------------------------
if docTitle:
    param = u"%s%%" % docTitle
    try:
        cursor.execute("""\
            SELECT d.id, d.title
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE d.title LIKE ?
               AND t.name = 'Summary'""", param)
        rows = cursor.fetchall()
    except Exception as info:
        cdrcgi.bail("Failure looking up document title: %s" % str(info))
    if not rows:
        cdrcgi.bail(u"No summary documents match %s" % docTitle)
    if len(rows) > 1:
        showTitleChoices(rows)

#----------------------------------------------------------------------
# From this point on we have what we need for the report.
#----------------------------------------------------------------------
#numYears = 2
#docId = 62978 #62906 #62978
commonStyle = getCommonCssStyle()
startDate = list(time.localtime())
startDate[0] -= numYears
startDate = time.strftime("%Y-%m-%d", time.localtime(time.mktime(startDate)))
conn = db.connect(user='CdrGuest')
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
    if type(resp) in (str, unicode):
        cdrcgi.bail(resp)
    if resp[0].strip():
        if not lastSection or resp[0] != lastSection:
            lastSection = resp[0]
            section = resp[0].replace("@@PubVerDate@@", verDate)
            sections.append(unicode(section, "utf-8"))
sections.reverse()
html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Summary Changes Report for CDR%010d - %s</title>
  %s
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
       commonStyle,
       numYears,
       numYears and "s" or "",
       docTitle,
       docId)
for section in sections:
    html += section + u"<br><hr><br>\n"
html += u"""
 </body>
</html>
"""

#print html
cdrcgi.sendPage(html)
