#----------------------------------------------------------------------
#
# $Id: EditExternMap.py,v 1.10 2006-08-29 15:46:23 ameyer Exp $
#
# Allows a user to edit the table which maps strings from external
# systems (such as ClinicalTrials.gov) to CDR document IDs.
#
# $Log: not supported by cvs2svn $
# Revision 1.9  2006/08/01 19:37:33  ameyer
# Added "mappable" functionality - involving many changes.
# Also added numerous comments to the code.
#
# Revision 1.8  2005/08/29 20:08:44  bkline
# Added check to make sure document type of mapped document is allowed.
#
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
import cdrdb, cdrcgi, cgi, re, cdr, time

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
# Set the form variables.
#----------------------------------------------------------------------
cdr.logwrite("Program initiation time=%f" % time.time())
fields     = cgi.FieldStorage()
cdr.logwrite("Got field storage time=%f" % time.time())
session    = cdrcgi.getSession(fields)
cdr.logwrite("Got session time=%f" % time.time())
request    = cdrcgi.getRequest(fields)
cdr.logwrite("Got request time=%f" % time.time())
usage      = fields.getvalue('usage')      or None
value      = fields.getvalue('value')      or None
pattern    = fields.getvalue('pattern')    or ""
docId      = fields.getvalue('docId')      or ""
alphaStart = fields.getvalue('alphaStart') or ""
maxRowStr  = fields.getvalue('maxRows')    or "250"
noMapped   = fields.getvalue('noMapped')   or None
noMappable = fields.getvalue('noMappable') or None
cdr.logwrite("Got 6 more fields time=%f" % time.time())
title      = "CDR Administration"
section    = "External Map Editor"
script     = "EditExternMap.py"
logFile    = cdr.DEFAULT_LOGDIR + "/EditExternMap.log"
buttons    = ["Get Values", cdrcgi.MAINMENU, "Log Out"]
extra      = usage and ["Save Changes"] or []
buttons    = extra + buttons
intUsage   = usage and int(usage) or None
maxRows    = int(maxRowStr)
allUsage   = not intUsage
if docId:
    docId = extractInt(docId) or ""
if docId and not pattern:
    allUsage = 1
if docId and (noMapped or noMappable):
    cdrcgi.bail("If searching for a mapped document ID, you must uncheck " + \
                "both mapping check boxes.")
cdr.logwrite("End of program initiation time=%f" % time.time())
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
# Find the value corresponding to an external_map id
#----------------------------------------------------------------------
def lookupValueByMapId(mapRowId):
    try:
        cursor.execute("""\
        SELECT value
          FROM external_map
         WHERE id = ?""", mapRowId)
        row = cursor.fetchone()
        if not row:
            cdrcgi.bail("Error: unable to find value row for id %d" \
                        "<br>Was it already deleted?"
                        % mapRowId)
    except Exception, info:
        cdrcgi.bail("Database error looking up value by map row id=%d: %s" \
                     % (mapRowId, str(info)))

    return row[0]

#----------------------------------------------------------------------
# Determine whether a user is allowed to edit a specific mapping.
#----------------------------------------------------------------------
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
        errors.append("Failure looking up row %s in external_map table"
                      "<br>Was it already deleted?" % key)
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
    cdr.logwrite("Begin reading form vars for save time=%f" % time.time())

    # Get user id to associate with update to external_map
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

    # Read input to get old and new values of user updateable fields
    # Key on all following dictionaries is external_map table id
    # Value is as documented below.
    pairs    = {}  # Value=Sequence of old/new CDR ID
                   # If value=='DELETE', then delete mapping box was checked
    oldBogus = {}  # Value bogus box initial value
                   #   'Y' = was checked
                   #   'N' = was checked
    newBogus = {}  # Value Y=bogus box is now checked, Y/N
    oldMable = {}  # Value Y=Mappable box was initially checked, Y/N
    newMable = {}  # Value Y=Mappable box is now checked, Y/N

    for field in fields.keys():
        # In parsing the input, the digits in "id-...", "old-id-..." etc.
        #  are an external_map table id, i.e., key to above dictionaries.
        if field.startswith("id-"):
            # key=map table id, val=cdrid of doc mapped to after user input
            key = extractInt(field)
            val = extractInt(fields[field].value)
            if not pairs.has_key(key):
                pairs[key] = [None, val]
            elif pairs[key] != "DELETE":
                pairs[key][1] = val
        elif field.startswith("old-id"):
            # key=map table id, val=cdrid of doc mapped to before user input
            key = extractInt(field)
            val = extractInt(fields[field].value)
            if not pairs.has_key(key):
                pairs[key] = [val, None]
            elif pairs[key] != "DELETE":
                pairs[key][0] = val
        elif field.startswith("del-id"):
            # key=map table id, value="Del map" checked by user
            key = extractInt(field)
            pairs[key] = "DELETE"
        elif field.startswith("old-bogus-"):
            # key=map table id, value=bogus checkbox value before input
            key = extractInt(field)
            oldBogus[key] = fields[field].value
        elif field.startswith("bogus-"):
            # key=map table id, value=bogus checkbox approved by user
            key = extractInt(field)
            newBogus[key] = "Y"
        elif field.startswith("old-mappable-"):
            # key=map table id, value=mappable checkbox before input
            key = extractInt(field)
            oldMable[key] = fields[field].value
        elif field.startswith("mappable-"):
            # key=map table id, value=mappable checkbox approved by uer
            key = extractInt(field)
            newMable[key] = "Y"
    cdr.logwrite("End reading form vars for save time=%f" % time.time())

    # Track changes
    numChanges = 0
    numDeletions = 0
    errors = []

    # Update changes in bogus values
    for rowId, oldValue in oldBogus.items():
        # Don't fool with it if user has also deleted the whole mapping
        if pairs.has_key(rowId) and pairs[rowId] == "DELETE":
            continue
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
                              "to '%s' for row %s: %s" % (newValue,
                                        lookupValueByMapId(rowId), str(e)))

    # Update changes in mappability of a value
    for rowId, oldValue in oldMable.items():
        # Don't fool with it if user has also deleted the whole mapping
        if pairs.has_key(rowId) and pairs[rowId] == "DELETE":
            continue
        newValue = None
        if oldValue == 'Y' and rowId not in newMable:
            newValue = 'N'
        elif oldValue == 'N' and rowId in newMable:
            newValue = 'Y'
        if newValue:
            # Don't allow value to become unmappable if it's already mapped
            if newValue == 'N' and pairs.has_key(rowId) and pairs[rowId][1]:
                errors.append("Can't make \"%s\" non-mappable if it's "
                              "already mapped.  Must also erase CDRID." \
                              % lookupValueByMapId(rowId))
            else:
                try:
                    cursor.execute("""\
                        UPDATE external_map
                           SET mappable = ?
                         WHERE id = ?""", (newValue, rowId))
                    conn.commit()
                    numChanges += 1
                except Exception, e:
                    errors.append(\
                        "failure setting external_map.mappable column "
                        "to '%s' for row %d: %s" % (newValue, rowId, str(e)))

    # Update mappings
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

            # As a double check, Sheri requested that a user must delete
            #  the doc id as well as check the Del map box in order to
            #  confirm that she really wants to delete this.
            if fields.getvalue("id-%d" % key):
                error = "Please erase the CDRID for \"%s\" when deleting " \
                        "the mapping to it." % lookupValueByMapId(key)
                errors.append(error)
            else:
                # Delete the whole row from the mapping table
                try:
                    cursor.execute("DELETE FROM external_map WHERE id = %d" \
                                   % key)
                    conn.commit()
                    cdr.logwrite("row %d (usage=%s; value=%s; CdrDocId=%s) "
                                 "deleted by %s" % (key, usageName, mapValue,
                                                    docId, uName), logFile)
                    numDeletions += 1
                except Exception,info:
                    error = "Failure deleting row %d = %s<br>%s" % \
                             (key, mapValue, str(info))
                    cdr.logwrite(error, logFile)
                    errors.append(error)
        elif (pair != "DELETE" and pair[0] != pair[1] and allowed(key) and
              typeOk(key, pair[1])):
            # Can't map non-mappable values
            if pair[1] and not newMable.has_key(key):
                errors.append(\
                    "Can't map value to %d and have field non-mappable" % \
                    pair[1])
            else:
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
                    cdr.logwrite("row %d changed from %s to %s by %s" % \
                                 (key, fromVal, toVal, uName), logFile)
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
                            question = pair[1] and \
                                       " (does document exist?)" or ""
                            errors.append("Failure setting DocId to %s "
                                          "for value %s%s" % \
                                          (pair[1] or "NULL",
                                           cgi.escape(row[0]), question))
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
# Select a list of usage possibilities.
#----------------------------------------------------------------------
cursor.execute("""\
  SELECT id, name
    FROM external_map_usage
ORDER BY name""")
rows = cursor.fetchall()

#----------------------------------------------------------------------
# Display the table search criteria input fields
#----------------------------------------------------------------------
includeUnmappedChecked = ""
if noMapped:
    includeUnmappedChecked = " checked='1'"
includeUnmappableChecked = ""
if noMappable:
    includeUnmappableChecked = " checked='1'"
form += """\
   <table border='0'>
    <tr>
     <td align='right' nowrap='1'>
      <b>Select a map usage:&nbsp;</b>
     </td>
     <td>
      <select name='usage'>
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
     <td>Select the kind of mapping to show, or select all kinds.</td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>
      <b>Pattern for values:&nbsp;</b>
     </td>
     <td>
      <input name='pattern' value="%s">
     </td>
     <td>Find specific text values, with optional SQL %% wildcards.</td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>
      <b>Document ID:&nbsp;</b>
     </td>
     <td>
      <input name='docId' value="%s">
     </td>
     <td>Include all values that map to this input document ID.<br />
    Leave "Pattern for values" blank if <em>only</em> this doc ID desired.</td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>
      <b>Alphabetical start:&nbsp;</b>
     </td>
     <td>
      <input name='alphaStart' value="%s">
     </td>
     <td>Start listing values beginning with this alphabetical string.<br />
    Use this as an alternative to searching for a Pattern or Document ID.<br />
    It is ignored if Pattern or Document ID are specified.</td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>
      <b>Max values to retrieve:&nbsp;</b>
     </td>
     <td>
      <input name='maxRows' value="%d">
     </td>
     <td>Return a maximum of this many rows of values.<br />
    Enter a number bigger than the max values in the database<br />
    if you want no limit on retrievals.</td>
    </tr>
    <tr>
    <tr>
     <td align='right' nowrap='1'>
      <b>Only include unmapped values:&nbsp;</b>
     </td>
     <td>
      <input type='checkbox' name='noMapped' value='1'%s>
     </td>
     <td>If checked, no values that already have doc IDs will appear.</td>
    </tr>
    <tr>
     <td align='right' nowrap='1'>
      <b>Also include unmappable values:&nbsp;</b>
     </td>
     <td>
      <input type='checkbox' name='noMappable' value='1'%s>
     </td>
     <td>If checked, both mappable and unmappable values appear, else only
     mappable values.</td>
    </tr>
   </table>
   <input type='hidden' name='%s' value='%s'>
""" % (pattern and cgi.escape(pattern, 1) or "", docId, alphaStart,
       maxRows, includeUnmappedChecked, includeUnmappableChecked,
       cdrcgi.SESSION, session)

#----------------------------------------------------------------------
# Show the rows that match the selection criteria.
#----------------------------------------------------------------------
if request in ("Save Changes", "Get Values"):
    # Set optional where clauses based on user input
    whereUsage = intUsage and ("AND m.usage = %d" % intUsage) or ""
    whereNoMap = noMapped and " AND m.doc_id IS NULL" or ""
    if noMappable:
        whereNoMappable = ""
    else:
        whereNoMappable = " AND m.mappable = 'Y'"

    cdr.logwrite("SQL initiation time=%f" % time.time())
    # Construct and execute specific query for user input
    if pattern:
        cursor.execute("""\
         SELECT top %d m.id, m.value, m.doc_id, u.name, m.bogus, m.mappable
           FROM external_map m
           JOIN external_map_usage u
             ON u.id = m.usage
          WHERE m.value LIKE ?
            %s %s %s
       ORDER BY m.value""" % (maxRows,whereUsage,whereNoMap,whereNoMappable),
                              pattern)
    elif docId:
        cursor.execute("""\
         SELECT top %d m.id, m.value, m.doc_id, u.name, m.bogus, m.mappable
           FROM external_map m
           JOIN external_map_usage u
             ON u.id = m.usage
          WHERE m.doc_id = %d
       ORDER BY m.value""" % (maxRows, extractInt(docId)))
    elif alphaStart:
        cursor.execute("""\
         SELECT top %d m.id, m.value, m.doc_id, u.name, m.bogus, m.mappable
           FROM external_map m
           JOIN external_map_usage u
             ON u.id = m.usage
          WHERE m.value >= ?
            %s %s %s
       ORDER BY m.value""" % (maxRows,whereUsage,whereNoMap,whereNoMappable),
                              alphaStart)
    else:
        cursor.execute("""\
         SELECT top %d m.id, m.value, m.doc_id, u.name, m.bogus, m.mappable
           FROM external_map m
           JOIN external_map_usage u
             ON u.id = m.usage
          WHERE 1 = 1
            %s %s %s
       ORDER BY m.value""" % (maxRows,whereUsage,whereNoMap,whereNoMappable))
    row = cursor.fetchone()

    cdr.logwrite("SQL completion time=%f" % time.time())
    # No hits?
    if not row:
        form += """\
  <br>
  <h4>No matching values found</h4>
"""
    # Output table of hits
    else:
        form += """\
  <br>
  <table border='1' cellspacing='1' cellpadding='1'>
   <tr>
    <td align='center'><b>Variant String</b></td>
    <td align='center'><b>CDRID</b></td>
   </tr>
"""
        # Produce each row in the table
        formPieces = []
        while row:
            mapId  = row[0]
            mapVal = row[1]
            if not row[2]:
                button = "&nbsp;"
            else:
                button = ("<button name='view' type='button' value='%s'"
                          " onclick='viewDoc(%s)'>"
                          "View</button>" % (row[2], row[2]))
            extra = allUsage and (" [%s]" % row[3]) or ""
            value = "%s%s" % (mapVal, extra)
            value = cgi.escape(value, 1)
            bogus = row[4] == 'Y' and " checked='1'" or ""
            mapOk = row[5] == 'Y' and " checked='1'" or ""
            # value = ("<input class='r' readonly='1' size='80' "
            #         "name='name-%d' value=\"%s\">" % (mapId, value))
            docId = "<input size='8' name='id-%d' value='%s'>" % (mapId,
                                                               row[2] or "")
            formPieces.append("""\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td>%s</td>""" % (value, docId, button))
            # Only need to delete mappings if mapped values are included
            # Forgive the pesky double negative
            if not noMapped:
                formPieces.append("""\
    <td nowrap='1'>
     <input type='checkbox' name='del-id-%d'>&nbsp;Del map?
    </td>""" % mapId)
            formPieces.append("""\
    <td nowrap='1'>
     <input type='checkbox' name='bogus-%d'%s>&nbsp;Bogus?
    </td>
    <td nowrap='1'>
     <input type='checkbox' name='mappable-%d'%s>&nbsp;Mappable?
    </td>
    <td>
     <input type='hidden' name='old-id-%d' value='%s'>
     <input type='hidden' name='old-bogus-%d' value='%s'>
     <input type='hidden' name='old-mappable-%d' value='%s'>
    </td>
   </tr>
""" % (mapId, bogus, mapId, mapOk, mapId, row[2] or "",
       mapId, row[4], mapId, row[5]))
            row = cursor.fetchone()
        # Put form together
        form = form + u"".join(formPieces) + """\
  </table>
  </form>
 </body>
</html>
"""
cdr.logwrite("Form completion time=%f" % time.time())
cdrcgi.sendPage(header + form)
