#----------------------------------------------------------------------
#
# $Id: EditExternMap.py,v 1.1 2003-12-16 15:57:45 bkline Exp $
#
# Allows a user to edit the table which maps strings from external
# systems (such as ClinicalTrials.gov) to CDR document IDs.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, re, cdr

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
usage   = fields and fields.getvalue('usage')   or None
value   = fields and fields.getvalue('value')   or None
pattern = fields and fields.getvalue('pattern') or ""
title   = "CDR Administration"
section = "External Map Editor"
script  = "EditExternMap.py"
logFile = cdr.DEFAULT_LOGDIR + "/EditExternMap.log"
buttons = ["Get Values", cdrcgi.MAINMENU, "Log Out"]
extra   = usage and ["Save Changes"] or []
buttons = extra + buttons
style   = """\
  <style  type='text/css'>input.r { background-color: EEEEEE }</style>
  <script type='text/javascript'>
   <!--
   function viewDoc(id) {
       var pageUrl    = "QcReport.py?DocId=" + id + "&Session=%s";
       var windowName = window.open(pageUrl, id);
   }
   -->
  </script>
""" % session
header  = cdrcgi.header(title, title, section, script, buttons,
                        stylesheet = style)

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
# Establish a database connection.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()

#----------------------------------------------------------------------
# Extract integer from string; uses all decimal digits.
#----------------------------------------------------------------------
def extractInt(str):
    if type(str) == type(9):
        return str
    if not str or type(str) not in (type(""), type(u"")):
        return None
    digits = re.sub(r"[^\d]", "", str)
    if not digits:
        return None
    return int(digits)

#----------------------------------------------------------------------
# Save changes to the current record if appropriate.
#----------------------------------------------------------------------
form = ""
if request == "Save Changes":
    if not cdr.canDo(session, "EDIT EXTERNAL MAP"):
        cdrcgi.bail("User not authorized to make changes to this data.")
    cursor.execute("""\
    SELECT u.id, u.name
      FROM session s
      JOIN usr u
        ON u.id = s.usr
     WHERE s.name = ?""", session)
    rows = cursor.fetchall()
    if len(rows) != 1:
        cdrcgi.bail("Failure looking up user for current session")
    uid = rows[0][0]
    uName = rows[0][1]
    pairs = {}
    for field in fields.keys():
        if field.startswith("id-"):
            key = extractInt(field)
            val = extractInt(fields[field].value)
            if not pairs.has_key(key):
                pairs[key] = [None, val]
            else:
                pairs[key][1] = val
        elif field.startswith("old-id"):
            key = extractInt(field)
            val = extractInt(fields[field].value)
            if not pairs.has_key(key):
                pairs[key] = [val, None]
            else:
                pairs[key][0] = val
    numChanges = 0
    errors = []
    for key in pairs:
        pair = pairs[key]
        if pair[0] != pair[1]:
            try:
                cursor.execute("""\
                UPDATE external_map
                   SET doc_id = ?,
                       usr = ?,
                       last_mod = GETDATE()
                 WHERE id = ?""", (pair[1], uid, key))
                conn.commit()
                numChanges += 1
                fromVal = pair[0] or "NULL"
                toVal   = pair[1] or "NULL"
                cdr.logwrite("row %d changed from %s to %s by %s" % (key,
                                                                     fromVal,
                                                                     toVal,
                                                                     uName),
                             logFile)
            except:
                try:
                    cursor.execute("""\
                    SELECT value
                      FROM external_map
                     WHERE id = ?""", key)
                    row = cursor.fetchone()
                    if not row:
                        errors.append("Internal error: unable to find "
                                      "value row for id %d" % key)
                    else:
                        question = pair[1] and " (does document exist?)" or ""
                        errors.append("Failure setting DocId to %s "
                                      "for value %s%s" % (pair[1] or "NULL",
                                                          cgi.escape(row[0]),
                                                          question))
                except:
                    cdrcgi.bail("Database failure looking up row %s" % key)
    section += " (%d change%s saved)" % (numChanges,
                                         numChanges != 1 and "s" or "")
    header  = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = style)
    for error in errors:
        form += """\
  <span style='color: red; font-family: Arial'><b>%s</b></span><br>
""" % error
    if errors:
        form += """\
  <br><br>
"""
##     html = """\
## <html>
##  <body>
## """
##     for key in pairs:
##         pair = pairs[key]
##         didWhat = pair[0] == pair[1] and "(unchanged)" or ("(changed to %s)"
##                                                            % pair[1])
##         html += """\
## value in row %d was %s %s<br>
## """ % (key, pair[0], didWhat)
##     cdrcgi.sendPage(html + """\
##  </body>
## </html>
## """)
##     html = """\
## <html>
##  <body>
##   <table>
## """
##     for field in fields.keys():
##         if type(fields[field]) != type([]):
##             html += """\
##    <tr>
##     <td>%s</td>
##     <td>%s</td>
##    </tr>
## """ % (field, fields[field].value)
##         else:
##             for f in fields[field]:
##                 html += """\
##    <tr>
##     <td>%s</td>
##     <td>%s</td>
##    </tr>
## """ % (field, f.value)
##     #cdrcgi.bail("Haven't implemented Save Changes yet")
##     cdrcgi.sendPage(html + """\
##   </table>
##  </body>
## </html>""")

#----------------------------------------------------------------------
# Edit a single record if requested.
#----------------------------------------------------------------------
## if value:
##     cdrcgi.bail("Haven't implemented that part yet")
    
#----------------------------------------------------------------------
# Show the list of usage possibilities.
#----------------------------------------------------------------------
cursor.execute("""\
  SELECT id, name
    FROM external_map_usage
ORDER BY name""")
rows = cursor.fetchall()
form += """\
   <table border='0'>
    <tr>
     <td align='right' nowrap='1'>
      <b>Select a map usage:&nbsp;</b>
     </td>
     <td>
      <select name='usage' width='60'>
"""
intUsage = usage and int(usage) or None
for row in rows:
    selected = ""
    if intUsage is not None and intUsage == row[0]:
        selected = " selected='1'"
    form += """\
       <option value='%d'%s>%s</option>
""" % (row[0], selected, cgi.escape(row[1]))
form += """\
      </select>
     </td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>
      <b>Pattern for values:&nbsp;</b>
     </td>
     <td>
      <input name='pattern' value="%s">
     </td>
    </tr>
   </table>
   <input type='hidden' name='%s' value='%s'>
""" % (pattern and cgi.escape(pattern, 1) or "",
                cdrcgi.SESSION, session)

#----------------------------------------------------------------------
# Show the rows that match the selection criteria.
#----------------------------------------------------------------------
if intUsage:
    if pattern:
        cursor.execute("""\
         SELECT m.id, m.value, m.doc_id, u.name, m.last_mod
           FROM external_map m
LEFT OUTER JOIN usr u
             ON u.id = m.usr
          WHERE m.usage = ?
            AND m.value LIKE ?
       ORDER BY m.value""", (intUsage, pattern))
    else:
        cursor.execute("""\
         SELECT m.id, m.value, m.doc_id, u.name, m.last_mod
           FROM external_map m
LEFT OUTER JOIN usr u
             ON u.id = m.usr
          WHERE m.usage = ?
       ORDER BY m.value""", intUsage)
    row = cursor.fetchone()
    if not row:
        form += """\
  <br>
  <h4>No matching values found</h4>
"""
    else:
        form += """\
  <br><table border='0' cellspacing='1' cellpadding='1'>
    <!--
  <table border='1' cellpadding='0' cellspacing='0'>
   <tr>
    <td align='center' nowrap='1'><b>Value</b></td>
    <td align='center' nowrap='1' ><b>DocId</b></td>
    <td align='center' nowrap='1' width='120'><b>Last Changed</b></td>
    <td align='center' nowrap='1' width='100'><b>Mapped By</b></td>
   </tr>
      -->
"""
        while row:
            if not row[2]:
                button = "&nbsp;"
            else:
                button = ("<button name='view' type='submit' value='%s'"
                          " onclick='viewDoc(%s)'>"
                          "View</button>" % (row[2], row[2]))
            value = cgi.escape(row[1], 1)
##             href  = ("%s/EditExternMap.py?%s=%s&value=%s&usage=%s" %
##                      (cdrcgi.BASE, cdrcgi.SESSION, session, value, usage))
            value = ("<input class='r' readonly='1' size='120' "
                     "name='name-%d' value=\"%s\">" % (row[0], value))
            docId = "<input size='8' name='id-%d' value='%s'>" % (row[0],
                                                               row[2] or "")
            form += """\
   <tr>
    <td valign='top'>%s</a></td>
    <td valign='top'>%s</td>
    <td>%s</td>
    <input type='hidden' name='old-id-%d' value='%s'>
    <!--
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
      -->
   </tr>
""" % (value, docId, button, row[0], row[2] or "",
       #row[2] and ("CDR%d" % row[2]) or "&nbsp;",
       row[4] or "&nbsp;", row[3] or "&nbsp;")
            row = cursor.fetchone()
        form += """\
  </table>
"""
cdrcgi.sendPage(header + form + """\
  </form>
 </body>
</html>
""")
