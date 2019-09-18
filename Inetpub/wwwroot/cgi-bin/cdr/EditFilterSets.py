#----------------------------------------------------------------------
# Menu of existing filter sets.
#
# BZIssue::3716 - Unicode encoding cleanup
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, sys, urllib
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
s1      = fields and fields.getvalue('s1') or None
s2      = fields and fields.getvalue('s2') or None
title   = "CDR Administration"
section = "Manage Filters"
script  = "EditFilterSets.py"

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
# Generate a report listing the content of all filter sets.
#----------------------------------------------------------------------
if request == "Deep Report":
    cdrcgi.navigateTo("ShowFilterSets.py", session)
elif request == "Report":
    buttons = ["New Filter Set", cdrcgi.MAINMENU, "Log Out"]
    header  = cdrcgi.header(title, title, "Filter Set Report", script, buttons,
            stylesheet = """\
  <style type='text/css'>
   li { font-size: 12pt; font-weight: normal; color:black }
   h2 {font-size: 13pt; font-family:Arial; color:black; font-weight:bold }
  </style>
""")
    sets = cdr.getFilterSets('guest')
    setDict = {}
    report = u""
    for set in sets:
        filterSet = cdr.getFilterSet('guest', set.name)
        setDict[set.name] = filterSet
    keys = setDict.keys()
    keys.sort()
    for key in keys:
        report += u"<h2>%s</h2><ul>\n" % cgi.escape(key)
        for member in setDict[key].members:
            report += u"<li>%s %s</li>\n" % (type(member.id) == type(9) and
                    "[S]" or "[F]", cgi.escape(member.name))
        report += u"</ul>\n"
    cdrcgi.sendPage(header + report + u"</form></body></html>")

#----------------------------------------------------------------------
# Handle request for creating a new filter set.
#----------------------------------------------------------------------
if request == "New Filter Set":
    print("Location:http://%s%s/EditFilterSet.py?%s=%s&Request=New\n" % (
            cdrcgi.WEBSERVER,
            cdrcgi.BASE,
            cdrcgi.SESSION,
            session))
    sys.exit(0)


#----------------------------------------------------------------------
# Retrieve and display the action information.
#----------------------------------------------------------------------
buttons = ["Deep Report", "Report", "New Filter Set",
           cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, script, buttons, numBreaks = 1)

#----------------------------------------------------------------------
# Show the list of existing filter sets.
#----------------------------------------------------------------------
try:
    conn = db.connect(user='CdrGuest')
    cursor = conn.cursor()
    cursor.execute("""\
            SELECT name,
                   description
              FROM filter_set
          ORDER BY name""")
    rows = cursor.fetchall()
except Exception as e:
    cdrcgi.bail("Database failure retrieving filter sets: %s" % e)

form = u"""\
   <h2>CDR Filter Sets</h2>
   <script language='JavaScript'>
    function showTip(tip) {
        window.status = tip;
    }
   </script>
   <ul>
"""
for row in rows:
    ### name1 = urllib.quote_plus(row[0])
    name1 = urllib.quote_plus(row[0].encode('utf-8'))
    name2 = cgi.escape(row[0], 1)
    desc  = cgi.escape(row[1], 1).replace("'", "&apos;")
    form += u"""\
    <li>
     <a href="%s/EditFilterSet.py?%s=%s&Request=Edit&setName=%s"
        onMouseOver="window.status='%s'; return true">%s</a>
    </li>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, name1, desc, name2)

#----------------------------------------------------------------------
# Send back the form.
#----------------------------------------------------------------------
form += u"""\
   </ul>
   <input type='hidden' name='%s' value='%s'>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form)
