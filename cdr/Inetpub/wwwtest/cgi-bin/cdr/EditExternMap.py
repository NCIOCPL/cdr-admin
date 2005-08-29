#----------------------------------------------------------------------
#
# $Id: EditExternMap.py,v 1.8 2005-08-29 20:08:44 bkline Exp $
#
# Allows a user to edit the table which maps strings from external
# systems (such as ClinicalTrials.gov) to CDR document IDs.
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2005/07/05 12:33:34  bkline
# Added support for new 'bogus' column in external_map table.
#
# Revision 1.6  2004/08/27 19:07:32  bkline
# Cosmetic changes requested by Lakshmi (comment #4, request #1297).
#
# Revision 1.5  2004/08/19 22:12:23  bkline
# Added support for deleting rows from the external_map table.
#
# Revision 1.4  2004/08/10 15:38:19  bkline
# Added support for separate permissions for different mapping types.
#
# Revision 1.3  2003/12/31 18:35:43  bkline
# Changed type of button form widget to 'button'.
#
# Revision 1.2  2003/12/19 20:40:18  bkline
# Added ability to get mapping values by mapped document ID.
#
# Revision 1.1  2003/12/16 15:57:45  bkline
# Allows a user to edit the table which maps strings from external
# systems (such as ClinicalTrials.gov) to CDR document IDs.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, re, cdr

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
usage    = fields and fields.getvalue('usage')   or None
value    = fields and fields.getvalue('value')   or None
pattern  = fields and fields.getvalue('pattern') or ""
docId    = fields and fields.getvalue('docId')   or ""
title    = "CDR Administration"
section  = "External Map Editor"
script   = "EditExternMap.py"
logFile  = cdr.DEFAULT_LOGDIR + "/EditExternMap.log"
buttons  = ["Get Values", cdrcgi.MAINMENU, "Log Out"]
extra    = usage and ["Save Changes"] or []
buttons  = extra + buttons
intUsage = usage and int(usage) or None
allUsage = not intUsage
if docId and not pattern:
    allUsage = 1
style    = """\
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
# Collect some useful names.
#----------------------------------------------------------------------
cursor.execute("SELECT id, name FROM external_map_usage")
usageNames = {}
for usageId, usageName in cursor.fetchall():
    usageNames[usageId] = usageName
cursor.execute("SELECT id, name FROM doc_type")
typeNames = {}
for typeId, typeName in cursor.fetchall():
    typeNames[typeId] = typeName
cursor.execute("SELECT usage, doc_type FROM external_map_type")
usageTypes = {}
for mapId, mapType in cursor.fetchall():
    if mapId in usageTypes:
        usageTypes[mapId][mapType] = typeNames[mapType]
    else:
        usageTypes[mapId] = { mapType: typeNames[mapType] }

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


def allowed(key):
    cursor.execute("""\
    SELECT a.name, u.name
      FROM action a
      JOIN external_map_usage u
        ON u.auth_action = a.id
      JOIN external_map m
        ON m.usage = u.id
     WHERE m.id = ?""", key)
    rows = cursor.fetchall()
    if not rows:
        errors.append("Failure looking up row %s in external_map table" % key)
        return False
    actionName, usageName = rows[0]
    if actionName not in allowed.actions:
        allowed.actions[actionName] = cdr.canDo(session, actionName)
    if allowed.actions[actionName]:
        return True
    if usageName not in allowed.usageErrors:
        allowed.usageErrors[usageName] = 1
        errors.append("User %s not authorized "
                      "to edit %s mappings" % (uName,
                                               usageName))
    return False
allowed.actions = {}
allowed.usageErrors = {}

def typeOk(mapId, docId):
    if not docId:
        return True
    cursor.execute("SELECT usage FROM external_map WHERE id = ?", mapId)
    rows = cursor.fetchall()
    if not rows:
        errors.append("Unable to find usage for mapping %s" % mapId)
        return False
    usageId = rows[0][0]
    cursor.execute("SELECT doc_type FROM document WHERE id = ?", docId)
    rows = cursor.fetchall()
    if not rows:
        errors.append("Unable to find document type for CDR%s" % docId)
        return False
    typeId = rows[0][0]
    if usageId not in usageTypes:
        errors.append("CDR%s: %s documents not allowed for %s" %
                      (docId, typeNames[typeId], usageNames[usageId]))
        return False
    if typeId not in usageTypes[usageId].keys():
        errors.append("CDR%s: %s documents not allowed for %s" %
                      (docId, typeNames[typeId], usageNames[usageId]))
        return False
    return True

#----------------------------------------------------------------------
# Save changes to the current record if appropriate.
#----------------------------------------------------------------------
form = ""
if request == "Save Changes":
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
    oldBogus = {}
    newBogus = {}
    for field in fields.keys():
        if field.startswith("id-"):
            key = extractInt(field)
            val = extractInt(fields[field].value)
            if not pairs.has_key(key):
                pairs[key] = [None, val]
            elif pairs[key] != "DELETE":
                pairs[key][1] = val
        elif field.startswith("old-id"):
            key = extractInt(field)
            val = extractInt(fields[field].value)
            if not pairs.has_key(key):
                pairs[key] = [val, None]
            elif pairs[key] != "DELETE":
                pairs[key][0] = val
        elif field.startswith("del-id"):
            key = extractInt(field)
            pairs[key] = "DELETE"
        elif field.startswith("old-bogus-"):
            key = extractInt(field)
            oldBogus[key] = fields[field].value
        elif field.startswith("bogus-"):
            key = extractInt(field)
            newBogus[key] = "Y"
    numChanges = 0
    numDeletions = 0
    errors = []
    for rowId, oldValue in oldBogus.items():
        newValue = None
        if oldValue == 'Y' and rowId not in newBogus:
            newValue = 'N'
        elif oldValue == 'N' and rowId in newBogus:
            newValue = 'Y'
        if newValue:
            try:
                cursor.execute("""\
                    UPDATE external_map
                       SET bogus = ?
                     WHERE id = ?""", (newValue, rowId))
                conn.commit()
                numChanges += 1
            except Exception, e:
                errors.append("failure setting external_map.bogus column "
                              "to '%s' for row %d: %s" % (newValue, rowId,
                                                          str(e)))
                
    for key in pairs:
        pair = pairs[key]
        if pair == "DELETE" and allowed(key):
            row = None
            try:
                cursor.execute("""\
                SELECT u.name, m.value, m.doc_id
                  FROM external_map_usage u
                  JOIN external_map m
                    ON m.usage = u.id
                 WHERE m.id = ?""", key)
                rows = cursor.fetchall()
                if rows:
                    row = rows[0]
            except:
                pass
            if not row:
                error = "failure looking up values for row %d" % key
                cdr.logwrite(error, logFile)
                errors.append(error)
                continue
            usageName, mapValue, docId = row
            try:
                cursor.execute("DELETE FROM external_map WHERE id = %d" % key)
                conn.commit()
                cdr.logwrite("row %d (usage=%s; value=%s; CdrDocId=%d) "
                             "deleted by %s" % (key, usageName, mapValue,
                                                docId, uName),
                             logFile)
                numDeletions += 1
            except:
                error = "Failure deleting row %d" % key
                cdr.logwrite(error, logFile)
                errors.append(error)
        elif (pair != "DELETE" and pair[0] != pair[1] and allowed(key) and
              typeOk(key, pair[1])):
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
    section += " (%d change%s saved; %d row%s deleted)" % (numChanges,
                                         numChanges != 1 and "s" or "",
                                         numDeletions,
                                         numDeletions != 1 and "s" or "")
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
       <option value='0'%s>All usages</option>
""" % (allUsage and " selected='1'" or "")
for row in rows:
    selected = ""
    if not allUsage and intUsage == row[0]:
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
    <tr>
     <td align='right' nowrap='1'>
      <b>Document ID:&nbsp;</b>
     </td>
     <td>
      <input name='docId' value="%s">
     </td>
    </tr>
   </table>
   <input type='hidden' name='%s' value='%s'>
""" % (pattern and cgi.escape(pattern, 1) or "",
       docId, cdrcgi.SESSION, session)

#----------------------------------------------------------------------
# Show the rows that match the selection criteria.
#----------------------------------------------------------------------
if request in ("Save Changes", "Get Values"):
    whereUsage = intUsage and ("AND m.usage = %d" % intUsage) or ""
    if pattern:
        cursor.execute("""\
         SELECT m.id, m.value, m.doc_id, u.name, m.bogus
           FROM external_map m
           JOIN external_map_usage u
             ON u.id = m.usage
          WHERE m.value LIKE ?
            %s
       ORDER BY m.value""" % whereUsage, pattern)
    elif docId:
        cursor.execute("""\
         SELECT m.id, m.value, m.doc_id, u.name, m.bogus
           FROM external_map m
           JOIN external_map_usage u
             ON u.id = m.usage
          WHERE m.doc_id = %d
       ORDER BY m.value""" % extractInt(docId))
    else:
        cursor.execute("""\
         SELECT m.id, m.value, m.doc_id, u.name, m.bogus
           FROM external_map m
           JOIN external_map_usage u
             ON u.id = m.usage
          WHERE 1 = 1
            %s
       ORDER BY m.value""" % whereUsage)
    row = cursor.fetchone()
    if not row:
        form += """\
  <br>
  <h4>No matching values found</h4>
"""
    else:
        form += """\
  <br>
  <table border='0' cellspacing='1' cellpadding='1'>
   <tr>
    <td align='center'><b>Variant String</b></td>
    <td align='center'><b>CDRID</b></td>
   </tr>
"""
        while row:
            if not row[2]:
                button = "&nbsp;"
            else:
                button = ("<button name='view' type='button' value='%s'"
                          " onclick='viewDoc(%s)'>"
                          "View</button>" % (row[2], row[2]))
            extra = allUsage and (" [%s]" % row[3]) or ""
            value = "%s%s" % (row[1], extra)
            value = cgi.escape(value, 1)
            bogus = row[4] == 'Y' and " checked='1'" or ""
            value = ("<input class='r' readonly='1' size='80' "
                     "name='name-%d' value=\"%s\">" % (row[0], value))
            docId = "<input size='8' name='id-%d' value='%s'>" % (row[0],
                                                               row[2] or "")
            form += """\
   <tr>
    <td valign='top'>%s</a></td>
    <td valign='top'>%s</td>
    <td>%s</td>
    <td nowrap='1'>
     <input type='checkbox' name='del-id-%d'>&nbsp;Delete mapping?
    </td>
    <td nowrap='1'>
     <input type='checkbox' name='bogus-%d'%s>&nbsp;Bogus?
    </td>
    <input type='hidden' name='old-id-%d' value='%s'>
    <input type='hidden' name='old-bogus-%d' value='%s'>
   </tr>
""" % (value, docId, button, row[0], row[0], bogus, row[0], row[2] or "",
       row[0], row[4])
            row = cursor.fetchone()
        form += """\
  </table>
"""
cdrcgi.sendPage(header + form + """\
  </form>
 </body>
</html>
""")
