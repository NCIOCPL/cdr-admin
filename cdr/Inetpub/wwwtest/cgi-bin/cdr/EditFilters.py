#----------------------------------------------------------------------
#
# $Id: EditFilters.py,v 1.2 2002-09-13 17:08:52 bkline Exp $
#
# Menu of existing filters.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/07/17 18:51:29  bkline
# Easier access to CDR filter editing.
#
#----------------------------------------------------------------------
import cgi, cdrcgi, cdrdb, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
s1      = fields and fields.getvalue('s1') or None
s2      = fields and fields.getvalue('s2') or None

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
#----------------------------------------------------------------------
if request == "New Filter": 
    print "Location:http://%s%s/EditFilter.py?%s=%s&Request=New\n" % (
            cdrcgi.WEBSERVER,
            cdrcgi.BASE,
            cdrcgi.SESSION,
            session)
    sys.exit(0)


#----------------------------------------------------------------------
# Retrieve and display the action information.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Manage Filters"
buttons = ["New Filter", cdrcgi.MAINMENU, "Log Out"]
script  = "EditFilters.py"
header  = cdrcgi.header(title, title, section, script, buttons, numBreaks = 1)

#----------------------------------------------------------------------
# Show the list of existing filters.
#----------------------------------------------------------------------
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
        ORDER BY d.title, d.id""")
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])
form = """\
   <INPUT TYPE='submit' NAME='%s' VALUE='Compare Filters'>&nbsp;&nbsp;
   between
   <INPUT NAME='s1' VALUE='bach'>&nbsp;
   and
   <INPUT NAME='s2' VALUE='mahler'>&nbsp;
   <H2>CDR Filters</H2>
   <TABLE border='1' cellspacing='0' cellpadding='2'>
    <TR>
     <TD><B>DocId</B></TD>
     <TD><B>Action</B></TD>
     <TD><B>DocTitle</B></TD>
    </TR>
""" % cdrcgi.REQUEST

for row in rows:
    form += """\
    <TR>
     <TD>CDR%010d</TD>
     <TD NOALIGN='1'>
      <A HREF='%s/EditFilter.py?%s=%s&Request=Load&DocId=CDR%010d'>Edit</A>
      <A HREF='%s/EditFilter.py?%s=%s&Request=View&DocId=CDR%010d'>View</A>
     </TD>
     <TD VALIGN='top'>%s</TD>
    </TR>
""" % (row[0], 
       cdrcgi.BASE, cdrcgi.SESSION, session, row[0],
       cdrcgi.BASE, cdrcgi.SESSION, session, row[0],
       cgi.escape(row[1]))

#----------------------------------------------------------------------
# Send back the form.
#----------------------------------------------------------------------
form += """\
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + cdrcgi.unicodeToLatin1(form))
