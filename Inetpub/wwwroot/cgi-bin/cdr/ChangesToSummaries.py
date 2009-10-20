#----------------------------------------------------------------------
#
# $Id$
#
# Report of history of changes for a board's summaries
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/12/16 15:55:50  bkline
# Report of history of changes for a board's summaries.
#
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
board     = fields.getvalue("Board")      or None
audience  = fields.getvalue("Audience")   or None
startDate = fields.getvalue("StartDate")  or None
endDate   = fields.getvalue("EndDate")    or None
pattern   = re.compile("<DateLastModified[^>]*>([^<]+)</DateLastModified>")

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
 <xsl:include                 href = "cdr:name:Module: STYLE Default"/>
 <xsl:template               match = "/">
  <style type='text/css'>
   <xsl:call-template         name = "defaultStyle"/>
   h1       { font-family: Arial, sans-serif; font-size: 16pt;
              text-align: center; font-weight: bold; }
   h2       { font-family: Arial, sans-serif; font-size: 14pt;
              text-align: center; font-weight: bold; }
   h1.left  { font-family: Arial, sans-serif; font-size: 16pt;
              text-align: left; font-weight: bold; }
   h2.left  { font-family: Arial, sans-serif; font-size: 14pt;
              text-align: left; font-weight: bold; }
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
# Build a picklist for editorial boards, including an option for All.
#----------------------------------------------------------------------
def getBoardList(cursor):
    picklist = """\
    <SELECT NAME='Board'>
     <OPTION VALUE='All' SELECTED='1'>All</OPTION>
"""
    cursor.execute("""\
        SELECT org_name.doc_id, org_name.value
          FROM query_term org_name
          JOIN query_term org_type
            ON org_type.doc_id = org_name.doc_id
         WHERE org_type.value  = 'PDQ Editorial Board'
           AND org_type.path   = '/Organization/OrganizationType'
           AND org_name.path   = '/Organization/OrganizationNameInformation'
                               + '/OfficialName/Name'
      ORDER BY org_name.value""", timeout = 300)
    for docId, orgName in cursor.fetchall():
        picklist += """\
     <OPTION VALUE='%d'>%s</OPTION>
""" % (docId, orgName)
    return picklist + """\
    </SELECT>"""

#----------------------------------------------------------------------
# Assemble the HTML for one summary's changes.
#----------------------------------------------------------------------
def getSummaryChanges(cursor, docId, startDate, endDate):
    cursor.execute("SELECT title FROM document WHERE id = ?", docId)
    docTitle = cursor.fetchall()[0][0]
    semicolon = docTitle.find(";")
    if semicolon != -1:
        docTitle = docTitle[:semicolon]
    html = u"""\
  <table border='0' width = '100%%'>
   <tr>
    <td class='hdg'>%s</td>
    <td align='right' valign='top' class='hdg'>CDR%010d</td>
   </tr>
  </table>
""" % (docTitle, docId)
    cursor.execute("""\
        SELECT num
          FROM doc_version
         WHERE id = ?
           AND publishable = 'Y'
      ORDER BY num DESC""", docId)
    pubVersions = [row[0] for row in cursor.fetchall()]
    for pubVersion in pubVersions:
        cursor.execute("""\
            SELECT xml, dt
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (docId, pubVersion))
        docXml, verDate = cursor.fetchall()[0]
        match = pattern.search(docXml)
        if match:
            dateLastModified = match.group(1)
            if dateLastModified >= startDate and dateLastModified <= endDate:
                verDate = "%s/%s/%s" % (verDate[5:7], verDate[8:10],
                                        verDate[:4])
                resp = cdr.filterDoc('guest', ['name:Summary Changes Report'],
                                     doc = docXml)
                section = resp[0].replace("@@PubVerDate@@", verDate)
                return (docTitle,
                        html + unicode(section, "utf-8") + u"<br><br>\n")
    return [u"", u""]

#----------------------------------------------------------------------
# Generate HTML for changes to one board's summaries.
#----------------------------------------------------------------------
def reportOnBoard(cursor, docId, boardName, startDate, endDate, audience):
    html = """\
  <br>
  <br>
  <h2 class='left'>%s<br>%s</h2>
  <br>
""" % (boardName, audience)
    cursor.execute("""\
SELECT DISTINCT b.doc_id
           FROM query_term b
           JOIN query_term a
             ON a.doc_id = b.doc_id
          WHERE b.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
            AND a.path = '/Summary/SummaryMetaData/SummaryAudience'
            AND b.int_val = ?
            AND a.value = ?""", (docId, audience))
    rows = cursor.fetchall()
    summaries = []
    #if not rows:
    #    cdrcgi.bail("no summaries for %s/%s" % (docId, audience))
    for row in rows:
        summary = getSummaryChanges(cursor, row[0], startDate, endDate)
        if summary[1]:
            summaries.append(summary)
    if not summaries:
        return u""
    summaries.sort(lambda a,b: cmp(a[0], b[0]))
    for summary in summaries:
        html += summary[1]
    return html

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
    boardList = getBoardList(cursor)
    hpSel = patSel = ""
    if audience == "Health Professionals":
        hpSel = " SELECTED='1'"
    elif audience == "Patients":
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
     <INPUT TYPE='radio' NAME='Audience' VALUE='Health Professionals'%s>
      Health Professional<BR>
     <INPUT TYPE='radio' NAME='Audience' VALUE='Patients'%s> Patient
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

#----------------------------------------------------------------------
# We have what we need; put up the report.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Changes to Summaries Report - %s</title>
  %s
 </head>
 <body>
  <h1>Changes to Summaries Report<br>from %s to %s</h1>
""" % (time.strftime("%B %d, %Y"),
       getCommonCssStyle(),
       startDate,
       endDate)

if board == 'All':
    cursor.execute("""\
        SELECT org_name.doc_id, org_name.value
          FROM query_term org_name
          JOIN query_term org_type
            ON org_type.doc_id = org_name.doc_id
         WHERE org_type.value  = 'PDQ Editorial Board'
           AND org_type.path   = '/Organization/OrganizationType'
           AND org_name.path   = '/Organization/OrganizationNameInformation'
                               + '/OfficialName/Name'
      ORDER BY org_name.value""", timeout = 300)
else:
    cursor.execute("""\
        SELECT doc_id, value
          FROM query_term
         WHERE doc_id = ?
           AND path = '/Organization/OrganizationNameInformation'
                    + '/OfficialName/Name'""", board)
for docId, boardName in cursor.fetchall():
    html += reportOnBoard(cursor, docId, boardName, startDate, endDate,
                          audience)

cdrcgi.sendPage(html + """\
 </body>
</html>
""")    
