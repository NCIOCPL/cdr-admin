#----------------------------------------------------------------------
#
# $Id$
#
# Menu of existing filters.
#
# BZIssue::3716
#
#----------------------------------------------------------------------
import cgi, cdrcgi, cdrdb, sys, string, socket

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
s1      = fields and fields.getvalue('s1') or None
s2      = fields and fields.getvalue('s2') or None
orderBy = fields and fields.getvalue('OrderBy') or None
LABEL   = "Compare Filters With the Production Server"

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Show top-level filter params.
#----------------------------------------------------------------------
if request == "Filter Params":
    cdrcgi.navigateTo("GetXsltParams.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Show the differences between the filters on two servers.
#----------------------------------------------------------------------
if request == LABEL:
    print "Location:http://%s%s/FilterDiffs.py\n" % (
            cdrcgi.WEBSERVER, cdrcgi.BASE)

#----------------------------------------------------------------------
# Retrieve and display the action information.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Manage Filters"
buttons = ["Filter Params", cdrcgi.MAINMENU, "Log Out"]
script  = "EditFilters.py"
header  = cdrcgi.header(title, title, section, script, buttons, numBreaks = 1)

#----------------------------------------------------------------------
# Show the list of existing filters.
#----------------------------------------------------------------------
if orderBy and orderBy == "DocId":
    orderBy = "d.id, d.title"
else:
    orderBy = "d.title, d.id"

try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    cursor.execute("""\
          SELECT d.id,
                 d.title
            FROM document d
            JOIN doc_type t
              ON t.id = d.doc_type
           WHERE t.name = 'Filter'
        ORDER BY %s""" % orderBy)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

sortReq = u"<A HREF='%s/EditFilters.py?%s=%s&OrderBy=%s'>%s</A>"
form = u"""\
   <INPUT TYPE='submit' NAME='%s' VALUE='%s'>
   <H2>CDR Filters</H2>
   <TABLE border='1' cellspacing='0' cellpadding='2'>
    <TR>
     <TD><B>%s</B></TD>
     <TD><B>Action</B></TD>
     <TD><B>%s</B></TD>
    </TR>
""" % (cdrcgi.REQUEST, LABEL,
       sortReq % (cdrcgi.BASE, cdrcgi.SESSION, session, "DocId", "DocId"),
       sortReq % (cdrcgi.BASE, cdrcgi.SESSION, session, "", "DocTitle")
      )

for row in rows:
    form += u"""\
    <TR>
     <TD>CDR%010d</TD>
     <TD NOALIGN='1'>
      <A HREF='%s/EditFilter.py?%s=%s&Request=View&DocId=CDR%010d'>View</A>
     </TD>
     <TD VALIGN='top'>%s</TD>
    </TR>
""" % (row[0],
       cdrcgi.BASE, cdrcgi.SESSION, session, row[0],
       cgi.escape(row[1]))

#----------------------------------------------------------------------
# Send back the form.
#----------------------------------------------------------------------
form += u"""\
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form)
