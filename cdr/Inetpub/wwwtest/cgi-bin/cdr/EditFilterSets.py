#----------------------------------------------------------------------
#
# $Id: EditFilterSets.py,v 1.1 2002-11-13 20:38:58 bkline Exp $
#
# Menu of existing filter sets.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, cdrdb, sys, urllib

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
# Handle request for creating a new filter set.
#----------------------------------------------------------------------
if request == "New Filter Set": 
    print "Location:http://%s%s/EditFilterSet.py?%s=%s&Request=New\n" % (
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
buttons = ["New Filter Set", cdrcgi.MAINMENU, "Log Out"]
script  = "EditFilterSets.py"
header  = cdrcgi.header(title, title, section, script, buttons, numBreaks = 1)

#----------------------------------------------------------------------
# Show the list of existing filter sets.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    cursor.execute("""\
            SELECT name,
                   description
              FROM filter_set
          ORDER BY name""")
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail("Database failure retrieving filter sets: %s" % info[1][0])

form = """\
   <h2>CDR Filter Sets</h2>
   <script language='JavaScript'>
    function showTip(tip) {
        window.status = tip;
    }
   </script>
   <ul>
"""
for row in rows:
    name1 = urllib.quote_plus(row[0])
    name2 = cgi.escape(row[0], 1)
    desc  = cgi.escape(row[1], 1).replace("'", "&apos;")
    form += """\
    <li>
     <a href="%s/EditFilterSet.py?%s=%s&Request=Edit&setName=%s"
        onMouseOver="window.status='%s'; return true">%s</a>
    </li>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, name1, desc, name2)

#----------------------------------------------------------------------
# Send back the form.
#----------------------------------------------------------------------
form += """\
   </ul>
   <input type='hidden' name='%s' value='%s'>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + cdrcgi.unicodeToLatin1(form))
