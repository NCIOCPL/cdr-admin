#----------------------------------------------------------------------
#
# $Id: ExternMapFailures.py,v 1.8 2006-08-07 21:08:14 ameyer Exp $
#
# Report on values found in external systems (such as ClinicalTrials.gov)
# which have not yet been mapped to CDR documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2004/12/27 20:33:18  bkline
# Cleaned up formatting of form.
#
# Revision 1.6  2004/12/22 16:35:40  bkline
# Implemented modifications requested in issue #1339.
#
# Revision 1.5  2003/12/18 16:00:27  bkline
# Modified table titles at Lakshmi's request and added overall title
# for report.
#
# Revision 1.4  2003/12/17 00:36:48  bkline
# Modified queries to ignore time portion of date-time value in sorting and
# display, and to show latest rows first.
#
# Revision 1.3  2003/12/16 15:43:45  bkline
# Split report into two sections and modified the sort order at Lakshmi's
# request.
#
# Revision 1.2  2003/11/25 12:46:52  bkline
# Minor formatting and encoding fixes.
#
# Revision 1.1  2003/11/10 18:01:15  bkline
# Report on values found in external systems (such as ClinicalTrials.gov)
# which have not yet been mapped to CDR documents.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, time, cgi, cdr

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
usages  = fields and fields.getlist('usage') or []
age     = fields and fields.getvalue('age') or 1000
mapChek = fields and fields.getvalue('mappable') or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "ExternMapFailures.py"
title   = "CDR Administration"
section = "External Map Failures Report"
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Establish a database connection.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not usages:
    form = """\
   <input type='hidden' name='%s' value='%s'>
   <table border='0'>
    <tr>
     <td valign='center' align='right'>
      <b>Select map usage(s):&nbsp;</b>
      <br>(Use Ctrl key to select multiple usages)&nbsp;&nbsp;
     </td>
     <td>
      <select multiple='multiple' name='usage'>
""" % (cdrcgi.SESSION, session)
    cursor.execute("""\
        SELECT name
          FROM external_map_usage
      ORDER BY name""")
    for row in cursor.fetchall():
        name = cgi.escape(row[0], True)
        form += """\
       <option value="%s">%s &nbsp;</option>
""" % (name, name)
    spacer= '&nbsp; ' * 5
    form += """\
      </select>
     </td>
     <td><b>%sView failures from past
      <input name='age' value='30' size='3'> days<br /><br />
      %sInclude non-mappable values
      <input type='checkbox' name='mappable' />
     </td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (spacer, spacer)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Gather the report data.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>External Map Failures</title>
  <style type='text/css'>
   body { font-family: Arial; }
  </style>
 </head>
 <body>
  <center>
   <h1>External Map Failures Report</h1>
   <h3>%s</h3>
  </center>
""" % time.strftime("%B %d, %Y")
for usage in usages:
    html += """
  <br>
  <br>
  <center>
   <h2>%s</h2>
  </center>
""" % usage

    # in/ex/clude non-mappable values
    if mapChek:
        mapSelect = ""
    else:
        mapSelect = "AND m.mappable <> 'N'"

    qry = """\
  SELECT m.value, m.last_mod
    FROM external_map m
    JOIN external_map_usage u
      ON u.id = m.usage
   WHERE doc_id IS NULL
     AND u.name = ?
     AND DATEDIFF(day, m.last_mod, GETDATE()) < ?
     %s
ORDER BY CONVERT(CHAR(10), m.last_mod, 102) DESC, m.value""" % mapSelect

    cursor.execute(qry, (usage, age))
    rows = cursor.fetchall()
    if rows:
        html += """\
  <table border='1' cellpadding='2' cellspacing='0' width='100%'>
   <tr>
    <th>Value</th>
    <th width='110'>Recorded</th>
   </tr>
"""
        for value, recorded in rows:
            html += """\
   <tr>
    <td>%s</td>
    <td nowrap = '1' align='center' valign='top'>%s</td>
   </tr>
""" % (cdrcgi.unicodeToLatin1(value), recorded[:10])
        html += """\
  </table>
"""
    else:
        html += """
  <i>No recent unmapped values found.</i>
"""
cdrcgi.sendPage(html + """\
 </body>
</html>""")
