#----------------------------------------------------------------------
#
# $Id: CheckUrls.py,v 1.2 2002-02-21 15:22:02 bkline Exp $
#
# Reports on URLs which cannot be reached.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import httplib, urlparse, socket, cdrdb, cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
SUBMENU = 'Report Menu'

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
header = cdrcgi.header('CDR Report on Inactive Hyperlinks',
                       'CDR Reports',
                       'Inactive Hyperlinks',
                       'CheckUrls.py',
                       (SUBMENU, cdrcgi.MAINMENU))
table  = """\
<TABLE BORDER='0' WIDTH='100%' CELLSPACING='1' CELLPADDING='2'>
 <TR BGCOLOR='silver'>
  <TD><B>Source Doc</B></TD>
  <TD><B>Element</B></TD>
  <TD><B>URL</B></TD>
  <TD><B>Problem</B></TD>
 </TR>
"""

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
    query  = """\
SELECT source_doc, source_elem, url
  FROM link_net
 WHERE url LIKE 'http%'
"""
    cursor.execute(query)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.sendPage(header + """\
  <H3>No Inactive Hyperlinks Found</H3>
 </BODY>
</HTML>
""")
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Keep track of hosts we know are not responding at all.
#----------------------------------------------------------------------
deadHosts = {}

#----------------------------------------------------------------------
# Report on a bad URL
#----------------------------------------------------------------------
def report(row, err):
    global table
    table += """\
   <TR BGCOLOR='white'>
    <TD>CDR%010d</TD>
    <TD>%s</TD>
    <TD>%s</TD>
    <TD>%s</TD>
   </TR>
""" % (row[0], row[1], row[2], err)

#----------------------------------------------------------------------
# Check each URL in the result set.
#----------------------------------------------------------------------
for row in rows:
    url      = row[2]
    pieces   = urlparse.urlparse(url)
    host     = pieces[1]
    selector = pieces[2]
    if pieces[3]: selector += ";" + pieces[3]
    if pieces[4]: selector += "?" + pieces[4]
    if pieces[5]: selector += "#" + pieces[5]
    if not host:
        report(row, "Malformed URL")
        continue
    if deadHosts.has_key(host):
        report(row, "Host not responding")
        continue
    if pieces[0] not in ('http','https'):
        report(row, "Unexpected protocol")
        continue
    try:
        http = httplib.HTTP(host)
        http.putrequest('GET', selector)
        http.endheaders()
        reply = http.getreply()
        if reply[0] / 100 != 2:
            report(row, "%s: %s" % (reply[0], reply[1]))
        """
        print "REPLY CODE:", reply[0]
        print "   MESSAGE:", reply[1]
        print "   HEADERS:", reply[2]
        """
    except IOError, msg:
        report(row, "IOError: %s" % msg)
    except socket.error, msg:
        deadHosts[host] = 1
        report(row, "Host not responding")
    except:
        report(row, "Unrecognized error")

cdrcgi.sendPage(header + table + "</TABLE></BODY></HTML>")
