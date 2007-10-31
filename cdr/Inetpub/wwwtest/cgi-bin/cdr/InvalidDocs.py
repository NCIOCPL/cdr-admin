#----------------------------------------------------------------------
#
# $Id: InvalidDocs.py,v 1.2 2007-10-31 16:12:58 bkline Exp $
#
# Reports on invalid or blocked CDR documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2007/08/27 17:13:03  bkline
# Report for Sheri on invalid and blocked documents (#3533).
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
docType = fields and fields.getvalue('docType')
docType = docType and int(docType) or None
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "InvalidDocs.py"
title   = "CDR Administration"
section = "Invalid Documents"
header  = cdrcgi.header(title, title, section, script, buttons,
                        stylesheet = """\
  <style type='text/css'>
   h1 { font-size: 14pt }
   th { font-size: 10pt }
  </style>
""")

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
# Get the list of active document types.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT id, name
      FROM doc_type
     WHERE active = 'Y'
       AND xml_schema IS NOT NULL
       AND name NOT IN ('Filter', 'xxtest', 'schema')
  ORDER BY name""")
docTypes = cursor.fetchall()

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
html = [header, u"""\
   <input type='hidden' name='%s', value='%s'>
   <b>Document Type:&nbsp;</b>
   <select name='docType'>
    <option value=''></option>
""" % (cdrcgi.SESSION, session)]
for dt in docTypes:
    selected = ""
    if dt[0] == docType:
        selected = u" selected='1'"
    html.append(u"""\
    <option value='%d'%s>%s&nbsp;</option>
""" % (dt[0], selected, dt[1]))
html.append(u"""\
   </select>
  </form>
""")

#----------------------------------------------------------------------
# If a report has been requested, show it.
#----------------------------------------------------------------------
if docType:
    cursor.execute("""\
        SELECT v.id, v.title, v.val_status, d.active_status
          FROM doc_version v
          JOIN document d
            ON d.id = v.id
          JOIN doc_type t
            ON d.doc_type = t.id
         WHERE t.id = ?
           AND v.num = (SELECT MAX(num)
                          FROM doc_version
                         WHERE id = v.id)
           AND v.val_status = 'I' /* <> 'V' */
      ORDER BY v.id""", docType)
    rows = cursor.fetchall()
    html.append(u"""\
  <h1>Invalid %s Documents</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>ID</th>
    <th>Title</th>
<!--<th>Status</th>-->
   </tr>
""" % dict(docTypes).get(docType))
    for row in rows:
        if row[3] != 'I':
            html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
<!--<td>%s</td>-->
   </tr>
""" % (row[0], cgi.escape(row[1]), row[2]))
    html.append(u"""\
  </table>
  <br>
  <h1>Blocked Documents</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>ID</th>
    <th>Title</th>
<!--<th>Status</th>-->
   </tr>
""")
    for row in rows:
        if row[3] == 'I':
            html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
<!--<td>%s</td>-->
   </tr>
""" % (row[0], cgi.escape(row[1]), row[2]))
    html.append(u"""\
  </table>
""")
html.append(u"""\
 </body>
</html>
""")
cdrcgi.sendPage(u"".join(html))

html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Import run on %s</title>
  <style type 'text/css'>
   body     { font-family: Arial, Helvetica, sans-serif }
   span.ti  { font-size: 14pt; font-weight: bold }
   span.sub { font-size: 12pt; font-weight: bold }
   th       { text-align: center; vertical-align: top; 
              font-size: 12pt; font-weight: bold }
   td       { text-align: left; vertical-align: top; 
              font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <span class='ti'>%s Import/Update Statistics Report</span>
   <br />
   <span class='sub'>Import run on %s</span>
  </center>
  <br />
  <br />
""" #% (jobDate, source, jobDate)
