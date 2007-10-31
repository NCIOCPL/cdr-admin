#----------------------------------------------------------------------
#
# $Id: Request3472.py,v 1.2 2007-10-31 15:59:23 bkline Exp $
#
# PDQ Submission Portal Statistics Summary Report.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2007/08/27 18:09:35  bkline
# PDQ Protocol Submissions Portal Activity Report (request #3472).
#
#----------------------------------------------------------------------
import cgi, cdrcgi, cdr, xml.dom.minidom, urllib

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
start     = fields.getvalue("start") or ""
end       = fields.getvalue("end")   or ""
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "PDQ Submission Portal Statistics Summary Report"
script    = "Request3472.py"
SUBMENU   = "Report Menu"
buttons   = ("Submit", SUBMENU, cdrcgi.MAINMENU)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Start the web page.
#----------------------------------------------------------------------
html = [cdrcgi.header(title, title, instr, script, buttons, stylesheet = """\
  <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
  <script language='JavaScript' src='/js/CdrCalendar.js'></script>
  <style type='text/css'>
   .t { font-size: 12pt; }
   th { font-size: 11pt; }
   h1 { font-size: 14pt; }
   td { font-size: 11pt; font-weight: bold; }
   p  { font-size: 11pt; width: 600px; border: 1px solid navy;
        padding: 3px; }
  </style>
""", numBreaks = 1), #bkgd = 'F9F9F9', numBreaks = 1),
        u"""\
   <h1>Protocol Submissions Portal Activity Report</h1>
   <br />
   <p>
    <!--
    Please enter the starting and ending dates for the range to be
    convered by the report.
    There may be overlap in the trials represented by the rows in
    the report, as the date ranges are used separately for set of
    trials counted for a given row.  For example, if the date range
    entered is for 2007-08-01 through 2007-08-31, the last row in
    the report's table will show the total number of all trials
    imported during that period, even if some of those trials were
    submitted earlier than 2007-08-01.
    -->
    Please enter the date range to be covered by the report.
   </p>
   <br />
   <table border='0'>
    <tr>
     <th>Starting Date:&nbsp;</th>
     <td><input name='start' id='start' class='CdrDateField' value='%s'></td>
    </tr>
    <tr>
     <th>Ending Date:&nbsp;</th>
     <td><input name='end' id='end' class='CdrDateField' value='%s'></td>
    </tr>
   </table>
""" % (start, end)]

#----------------------------------------------------------------------
# CTS statistics.
#----------------------------------------------------------------------
class Stats:
    def __init__(self, docXml):
        dom = xml.dom.minidom.parseString(docXml)
        topElem = dom.documentElement
        self.start = topElem.getAttribute('start')
        self.end = topElem.getAttribute('end')
        self.incomplete = None
        self.duplicate = None
        self.started = None
        self.imported = None
        for node in topElem.childNodes:
            if node.nodeName == 'incomplete':
                self.incomplete = int(cdr.getTextContent(node))
            elif node.nodeName == 'submitted':
                self.submitted = int(cdr.getTextContent(node))
            elif node.nodeName == 'duplicate':
                self.duplicate = int(cdr.getTextContent(node))
            elif node.nodeName == 'imported':
                self.imported = int(cdr.getTextContent(node))

#----------------------------------------------------------------------
# Create report if we have either end of the date range specified.
#----------------------------------------------------------------------
if start or end:
    delim = "?"
    url = cdr.emailerCgi() + "/cts-stats.py"
    if start:
        url += "%sstart=%s" % (delim, start)
        delim = "&"
    if end:
        url += "%send=%s" % (delim, end)
    try:
        f = urllib.urlopen(url)
        docXml = f.read()
        stats = Stats(docXml)
        start = stats.start
        end = stats.end
    except Exception, e:
        cdrcgi.bail("Failure retrieving statistics: %s" % e)
    html.append(u"""\
  <br />
  <br />
  <table border='0'>
   <tr>
    <th class='t'>Protocol Submissions Portal Activity Report</th>
   </tr>
    <tr>
     <th>%s - %s</th>
    </tr>
    <tr>
     <td align='center'>
      <table border='0'>
       <tr><td>&nbsp;</td></tr>
       <tr>
        <th align='right'>Trials started but not submitted:&nbsp;</th>
        <td align='right'>%s</td>
       </tr>
       <tr>
        <th align='right'>Trials successfully submitted:&nbsp;</th>
        <td align='right'>%s</td>
       </tr>
       <tr><td>&nbsp;</td></tr>
       <tr>
        <th align='right'>Trials marked as duplicate:&nbsp;</th>
        <td align='right'>%s</td>
       </tr>
       <tr>
        <th align='right'>*Trials imported:&nbsp;</th>
        <td align='right'>%s</td>
       </tr>
      </table>
     </td>
    </tr>
   </table>
   <br />
   *Includes trials that may have been submitted through the portal
   before the specified date range but imported during the date range.
""" % (stats.start, stats.end, stats.incomplete, stats.submitted,
       stats.duplicate, stats.imported))
    
#----------------------------------------------------------------------
# Put up the form fields with explanation.
#----------------------------------------------------------------------
html.append(u"""\
  </form>
 </body>
</html>
""")
html = u"".join(html)
cdrcgi.sendPage(html)
