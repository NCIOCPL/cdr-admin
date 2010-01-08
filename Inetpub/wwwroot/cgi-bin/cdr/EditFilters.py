#----------------------------------------------------------------------
#
# $Id$
#
# Menu of existing filters.
#
# Revision 1.5  2007/11/03 14:15:07  bkline
# Unicode encoding cleanup (issue #3716).
#
# Revision 1.4  2003/02/25 20:04:49  pzhang
# Showed edit feature only on Dev machine (MAHLER now).
# Sorted filter list by DocId or DocTitle.
#
# Revision 1.3  2002/11/08 13:40:52  bkline
# Added new report to show all top-level param for XSL/T filters.
#
# Revision 1.2  2002/09/13 17:08:52  bkline
# Added View command and button to compare all filters between two
# servers.
#
# Revision 1.1  2002/07/17 18:51:29  bkline
# Easier access to CDR filter editing.
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

#----------------------------------------------------------------------
# Edit only on Dev machine.
# Since we moved to SVN for source control we're not editing filters
# through this interface anymore
#----------------------------------------------------------------------
localhost = socket.gethostname()
#if string.upper(localhost) == "MAHLER":
#    localhost= "Dev"

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
if request == "Compare Filters":
    if not s1 or not s2:
        cdrcgi.bail("Must specify both servers")
    print "Location:http://%s%s/FilterDiffs.py?s1=%s&s2=%s\n" % (
            cdrcgi.WEBSERVER, cdrcgi.BASE, s1, s2)

#----------------------------------------------------------------------
# Handle request for creating a new filter.
# This is now being done using the command
#   CreateFilter.py
#----------------------------------------------------------------------
# if request == "New Filter": 
#     print "Location:http://%s%s/EditFilter.py?%s=%s&Request=New\n" % (
#             cdrcgi.WEBSERVER,
#             cdrcgi.BASE,
#             cdrcgi.SESSION,
#             session)
#     sys.exit(0)


#----------------------------------------------------------------------
# Retrieve and display the action information.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Manage Filters"
if localhost == "Dev":
    buttons = ["New Filter", "Filter Params", cdrcgi.MAINMENU, "Log Out"]
else:
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
   <INPUT TYPE='submit' NAME='%s' VALUE='Compare Filters'>&nbsp;&nbsp;
   between
   <INPUT NAME='s1' VALUE='bach'>&nbsp;
   and
   <INPUT NAME='s2' VALUE='mahler'>&nbsp;
   <H2>CDR Filters</H2>
   <TABLE border='1' cellspacing='0' cellpadding='2'>
    <TR>
     <TD><B>%s</B></TD>
     <TD><B>Action</B></TD>
     <TD><B>%s</B></TD>
    </TR>
""" % (cdrcgi.REQUEST,
       sortReq % (cdrcgi.BASE, cdrcgi.SESSION, session, "DocId", "DocId"),
       sortReq % (cdrcgi.BASE, cdrcgi.SESSION, session, "", "DocTitle")
      )

DevEdit = u"""
          <A HREF='%s/EditFilter.py?%s=%s&Request=Load&DocId=CDR%010d'>Edit</A>
          """ 

for row in rows:
    form += u"""\
    <TR>
     <TD>CDR%010d</TD>
     <TD NOALIGN='1'>
      %s
      <A HREF='%s/EditFilter.py?%s=%s&Request=View&DocId=CDR%010d'>View</A>
     </TD>
     <TD VALIGN='top'>%s</TD>
    </TR>
""" % (row[0], 
       (localhost == "Dev") and DevEdit % (cdrcgi.BASE, 
                                cdrcgi.SESSION, session, row[0]) or "",
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
