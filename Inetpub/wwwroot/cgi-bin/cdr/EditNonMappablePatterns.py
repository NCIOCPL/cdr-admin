#----------------------------------------------------------------------
# Edit the list of non-mappable external_map values.
#
# Allows a user to add or delete patterns from the list of regular
# expressions (in SQL "LIKE" format) for CTGov Facility values that
# cannot be mapped.
#
# $Id$
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2008/08/22 04:00:57  ameyer
# Added ability to review all existing external_map strings and make any
# non-mappable that match the patterns.
# Also made a number of user interface tweaks.
#
# Revision 1.2  2008/08/20 03:52:04  ameyer
# Numerous changes, had to replace simple URL link with javascript.
#
# Revision 1.1  2008/07/23 05:08:56  ameyer
# Initial version.
#
#----------------------------------------------------------------------
import cgitb; cgitb.enable()

import cgi, cdrcgi, cdrdb, cdr, extMapPatChk

# Use same logfile used for changing values
LF=cdr.DEFAULT_LOGDIR + "/GlobalChangeCTGovMapping.log"

# Constants
MAINTITLE          = "Maintain CTGov non-Mapping Patterns"
SCRIPT             = "EditNonMappablePatterns.py"
MAX_DISPLAY_VALUES = 6000

#----------------------------------------------------------------------
#  Subroutines
#----------------------------------------------------------------------
def showInitialScreen(session):
    """
    Put up the initial screen.

    Pass:
        Session credentials.

    Return:
        No return, returns to user's browser.
    """
    global MAINTITLE, SCRIPT

    # Find all existing patterns
    qry = """\
        SELECT id, pattern
          FROM external_map_nomap_pattern
      ORDER BY pattern"""
    try:
        conn = cdrdb.connect("CdrGuest")
        cursor = conn.cursor()
        cursor.execute(qry)
        rows = cursor.fetchall()
        cursor.close()
    except cdrdb.Error, info:
        cdrcgi.bail("Database error fetching patterns: %s" % str(info))

    patternCount = len(rows)

    # Construct the form
    buttons = (cdrcgi.MAINMENU, "Log Out")
    html = u""
    html += cdrcgi.header(MAINTITLE, MAINTITLE, "Add, delete, or view pattern",
                         script=SCRIPT, buttons=buttons, stylesheet="""\
<script type="text/javascript">
 function sendPattern(addOrView) {
    if (!document.getElementById("newPattern").value) {
        alert("Please enter a pattern string in the input box to Add or View");
    }
    else {
        document.forms[0].Request.value = addOrView;
        document.forms[0].newAction.value = addOrView;
        document.forms[0].submit();
    }
 }
</script>
""")

    html += """
<h3>Mark unmappable facilities Non-mappable</h3>
<p>Click <em>Apply</em> to search all CT.gov Facility strings for
values matching non-mappable patterns and mark them as non-mappable.</p>
<p>Click <em>View</em> to just view a list of currently mappable strings
that should be made non-mappable.</p>

<center>
<table border='0' cellspacing='15'>
 <tr>
  <td><input type='submit' name='applyPatterns' value='Apply' /></td>
  <td><input type='submit' name='applyPatterns' value='View' /></td>
 </tr>
</table>
</center>

<hr />

<h3>Update the Non-mappable Pattern Table</h3>

<p>To create a new pattern, enter a string using '_' to stand for
any one character and '%%' for any sequence of 0 or more characters, then
click the "<em>Add</em>" button to add it to the list of non-mappable
patterns, or the <em>View</em> button to just view matching values.</p>

<p>Use '\\_' or '\\%%' for literal underscore and percent signs.  Patterns
are not case sensitive.</p>

<p>There are currently %d existing patterns.
To remove one, click the "<em>Del</em>" link for that pattern or the
<em>View</em> link to just view matching values.<p>

<p>To edit a pattern, Add the correct value and Delete the incorrect one.</p>

<table border="2">
 <tr>
  <td><input type="button" value="Add" onclick="sendPattern('add')" /></td>
  <td><input type="button" value="View" onclick="sendPattern('view')" /></td>
  <td><input type="text" id="newPattern" name="newPattern" size="64" /></td>
 </tr>
""" % (patternCount)

    # Add all existing patterns
    for row in rows:
        html += """
 <tr>
  <td><a href="%s?%s=%s&newAction=del&oldId=%d">Del</a></td>
  <td><a href="%s?%s=%s&newAction=view&oldId=%d">View</a></td>
  <td>%s</td>
 </tr>
""" % (SCRIPT, cdrcgi.SESSION, session, row[0],
       SCRIPT, cdrcgi.SESSION, session, row[0], row[1])

    html += """
</table>
<input type="hidden" id="session" name="%s" value="%s" />
<input type="hidden" name="newAction" />
</form>
</body>
</html>
""" % (cdrcgi.SESSION, session)

    # Send it to the browser, completing this interaction
    cdrcgi.sendPage(html)

def propagatePatterns(session, runMode):
    """
    Load all the patterns in the external_map_nomap_pattern table,
    and check every single external map value against them.

    Optionally update any matching values in the external_map table.

    Heavy lifting is done in the ExternalMapPatternCheck object.

    Pass:
        runMode - 'test' = just report results.
                  'run'  = update the database and report results.
    """
    # DEBUG runMode = "test"
    # Instantiate an object that does everything
    try:
        noMapObj = extMapPatChk.ExternalMapPatternCheck(session=session)
    except cdr.Exception, info:
        # Failed
        cdrcgi.bail("Oops.  ExternalMapPatternCheck reports: %s" % info)

    # If update requested
    if runMode == 'run':
        try:
            noMapObj.updateDatabase()
        except cdr.Exception, info:
            # Failed
            cdrcgi.bail("Error updating the database: %s" % info)

    # Show what happened or would happen
    showNomapReport(noMapObj, runMode)

def showNomapReport(noMapObj, runMode):
    """
    Display a screen showing what did or would happen as a result of
    calling propagatePatterns().

    Pass:
        noMapObj - ExternalMapPatternCheck object.
        runMode  - 'test' or 'run'
    """
    buttons = (cdrcgi.MAINMENU, "Log Out")
    html = u""
    html += cdrcgi.header(MAINTITLE, MAINTITLE, "Results of ApplyPatterns",
                         script=SCRIPT, buttons=buttons)

    # Get summary counts
    chkCount    = noMapObj.getCheckedCount()
    matchCount  = noMapObj.getMatchedCount()
    updateCount = noMapObj.getUpdatedCount()
    mapCount    = noMapObj.getMappedCount()

    # Show update results
    html += """
<h2>Results of applying patterns</h2>
<h3>Summary</h3>
<table border='1'>
 <tr>
  <td>%d</td>
  <td>Mappable CT.gov Facility patterns were checked</td>
 </tr>
 <tr>
  <td>%d</td>
  <td>Values matched a non-mappable pattern</td>
 </tr>
 <tr>
  <td>%d</td>
  <td>Values were updated</td>
 </tr>
 <tr>
  <td>%d</td>
  <td>Values were already mapped and cannot be updated by this program</td>
 </tr>
</table>

<h3>Details</h3>

""" % (chkCount, matchCount, updateCount, mapCount)

    if mapCount > 0:
        mappedRows = noMapObj.getMappedValues()
        html += """
<p><strong>Non-mappable values that were already mapped</strong></p>

<table border='1'>
 <tr>
  <td><strong>Doc ID</strong></td>
  <td><strong>CT.gov Facility string</strong></td>
 </tr>
"""
        for row in mappedRows:
            html += """
 <tr>
  <td>%d</td><td>%s</td>
 </tr>
""" % (row[0], row[1])
        html += "</table>\n"

    if matchCount:
        # Show items that were or would have been marked non-mappable
        if runMode == 'test':
            html += """
<p><strong>The following values would have been updated</strong></p>
"""
        else:
            html += """
<p><strong>The following values were marked non-mappable</strong></p>
"""
        values = noMapObj.getValues()
        html += """
<table border='1'>
 <tr><td><strong>CT.gov Facility string</strong></td></tr>
"""
        for value in values:
            html += " <tr><td>%s</td></tr>\n" % value
        html += "</table>\n"

    html += """
<p>Click the back button or a navigation bar button to continue</p>
"""
    cdrcgi.sendPage(html)

def checkPattern(action, session, patternId=None, pattern=None):
    """
    Display all of the strings covered by a particular pattern.
    The pattern may be identified by an ID, or by a string, but
    not both.

    If the action is to add or delete the pattern, confirmation
    is requested.

    Pass:
        action    - One of "add", "del" or "view".
        session   - User credentials.
        patternId - Unique id in external_map_nomap_pattern table.
        pattern   - Pattern string, if it's a new pattern.

    Return:
        No return, returns to user's browser.
    """
    global MAINTITLE, SCRIPT

    # Does pattern duplicate an existing one?
    if action == "addNew":
        try:
            qry = """
              SELECT count(*)
                FROM external_map_nomap_pattern
               WHERE pattern = ?
            """
            conn = cdrdb.connect("CdrGuest")
            cursor = conn.cursor()
            cursor.execute(qry, (pattern,))
            row = cursor.fetchone()
            cursor.close()
        except cdrdb.Error, info:
            cdrcgi.bail("Database error checking for pattern duplicate: %s" %
                        str(info))
        if row[0] > 0:
            cdrcgi.bail('The pattern: "%s" is already in the database' %
                         pattern)

    # Convert patternId if supplied
    if patternId:
        qry = """
          SELECT pattern
            FROM external_map_nomap_pattern
           WHERE id = ?
        """
        try:
            conn = cdrdb.connect("CdrGuest")
            cursor = conn.cursor()
            cursor.execute(qry, (patternId,))
            row = cursor.fetchone()
            cursor.close()
        except cdrdb.Error, info:
            cdrcgi.bail("Database error fetching pattern for id=%s: %s" % \
                        (patternId, str(info)))

        if not row or not row[0]:
            cdrcgi.bail("Internal error, no pattern found for ID=%s: " % \
                         patternId)
        pattern = row[0]

    # Find all of the values matching the pattern
    qry = """
      SELECT TOP %d m.value, m.doc_id, m.bogus, m.mappable
        FROM external_map m
        JOIN external_map_usage u
          ON m.usage = u.id
       WHERE u.name = 'CT.gov Facilities'
         AND value LIKE ?
    ORDER BY m.mappable DESC, m.doc_id DESC, m.value ASC
     """ % MAX_DISPLAY_VALUES
    try:
        conn = cdrdb.connect("CdrGuest")
        cursor = conn.cursor()
        cursor.execute(qry, (pattern,))
        rows = cursor.fetchall()
        cursor.close()
    except cdrdb.Error, info:
        cdrcgi.bail("Database error fetching values for pattern=%s: %s" % \
                    (pattern, str(info)))

    valueCount = len(rows)
    # cdr.logwrite("Found %d hits" % valueCount)

    # Were any of the values already mapped
    mappedCount   = 0
    mappableCount = 0
    i = 0
    while i < valueCount and rows[i][3] == 'Y':
        mappableCount += 1
        if rows[i][1]:
            mappedCount += 1
        i += 1

    # Buttons depend on requested action.
    buttons = []
    # cdr.logwrite("checkPattern: action=%s" % action)
    if action == "addNew":
        buttons.append("Confirm Add")
    if action == "delOld":
        buttons.append("Confirm Delete")
    buttons += [cdrcgi.MAINMENU, "Log Out"]

    # Construct the form
    html = u""
    html += cdrcgi.header(MAINTITLE, MAINTITLE, "View values matching pattern",
                         script=SCRIPT, buttons=buttons)

    # Show the pattern string
    html += """
<p><strong>%d</strong> total external_map string values match the pattern:<br />
 &nbsp; &nbsp; "<strong>%s</strong>"</p>
""" % (valueCount, pattern)

    # If caller wanted to do more than just view these, ask for confirmation
    if action == "add":
        html += """
<p>Click "Confirm Add" above to confirm the addition of "%s" to the list
of patterns for unmappable CTGov Facility values.</p>
""" % pattern

    if action == "del":
        html += """
<p>Click "Confirm Delete" above to confirm the deletion of "%s" from the list
of patterns for unmappable CTGov Facility values.</p>
""" % pattern

    if valueCount == MAX_DISPLAY_VALUES:
        html += """
<p>More than %d values were found, results are truncated at %d values</p>
""" % (valueCount, valueCount)

    # If some already mapped
    if mappedCount:
        html += """
<p><strong>Warning!</strong> %d values matching the pattern have already
been mapped</p>
""" % mappedCount
    else:
        html += """
<p>No values matching the pattern have yet been mapped</p>
"""

    html += """
<p>[Click the browser Back button to return to the pattern selection screen
with no changes to the list of unmappable patterns.]</p>
"""
    if mappableCount:
        html += showValues(rows, 0, mappableCount)

    # If some others (there should be) show them separately
    if valueCount > mappableCount:
        html += showValues(rows, mappableCount, valueCount - mappableCount)

    # Save values if we have them
    # Have to do it this way to prevent creating variables = "None"
    if oldId:
        html += '<input type="hidden" name="oldId" value="%s" />\n' % oldId
    if newPattern:
        html += '<input type="hidden" name="newPattern" value="%s" />\n' % \
                cgi.escape(newPattern, True)

    # Termination
    html += """
<input type="hidden" name="%s" value="%s" />
<input type="hidden" name="newAction" />
</form>
</body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(html)

def showValues(rows, firstRow, count):
    """
    Construct an HTML table with all of the data in the rows sequence,
    starting from the first specified.

    Used to construct a table of values already mapped, or a table of those
    not yet mapped.

    Pass:
        rows     - Sequence of rows returned by checkPattern() query.
        firstRow - Use this as the first row in the table.
        count    - Show this many.

    Return:
        String of HTML.
    """

    # if firstRow has a docId, this is a table of mapped values
    showIds = ""
    html    = u""
    if rows[firstRow][3] == 'Y':
        html += "\n<h3>%d Mappable values</h3>\n" % count
        showIds = "\n  <td>DocID</td\n"
    else:
        html += "\n<h3>%d Non-Mappable values</h3>\n" % count
    html += """
<table border="2">
 <tr>%s
  <td>Bogus</td>
  <td>Mpbl</td>
  <td>Value from the external map table</td>
 </tr>
""" % showIds

    # Add the data
    rowx = firstRow
    htmlSeq = []
    for i in range(count):
        row = rows[rowx]
        rowx += 1
        if showIds:
            docId = "\n  <td>%s</td>\n" % row[1]
        else:
            docId = ""
        htmlSeq.append("""
 <tr>%s
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
 </tr>
""" % (docId, row[2], row[3], row[0]))

    # Flatten to string
    html += u"".join(htmlSeq) + "\n</table>\n"

    return html

def updateDB(session, oldId=None, newPattern=None):
    """
    Insert or delete a row in the external_map_nomap_pattern table.

    Pass:
        session    - User credentials.
        oldId      - Ir present, delete this.
        newPattern - If present, insert this.
    Return:
        No return, send confirmation to client.
    """
    # Define update
    if newPattern:
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute("""\
          INSERT INTO external_map_nomap_pattern (pattern)
               VALUES (?)
            """, (newPattern,))
            conn.commit()
            cursor.close()
        except cdrdb.Error, info:
            cdrcgi.bail("Error inserting new pattern: %s" % str(info))
    else:
        try:
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute("""\
          DELETE FROM external_map_nomap_pattern
           WHERE id = ?
            """, (int(oldId),))
            conn.commit()
            cursor.close()
        except cdrdb.Error, info:
            cdrcgi.bail("Error deleting old pattern: %s" % str(info))

    # Tell user
    buttons = ("Continue", cdrcgi.MAINMENU, "Log Out")
    html = u""
    html += cdrcgi.header(MAINTITLE, MAINTITLE, "Update completed",
                         script=SCRIPT, buttons=buttons)

    html += """
<p>The update is complete, click "Continue" above to return to the main
screen</p>
<input type="hidden" name="%s" value="%s" />
<input type="hidden" name="newAction" />
</form>
</body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(html)


#----------------------------------------------------------------------
#  Main
#----------------------------------------------------------------------

# Parse form variables
fields = cgi.FieldStorage()
if not fields:
    cdrcgi.bail ("Unable to load form fields - should not happen!", logfile=LF)

# Establish user session
session = cdrcgi.getSession(fields)
if not session:
    cdrcgi.bail ("Unknown or expired CDR session.", logfile=LF)

# User authorized?
if not cdr.canDo (session, "EDIT CTGOV MAP"):
    cdrcgi.bail (
    "Sorry, user not authorized to change external_map non-mappable patterns",
                 logfile=LF)

# Navigation
request = cdrcgi.getRequest(fields)
if request in (cdrcgi.MAINMENU, "Cancel"):
    cdrcgi.navigateTo ("Admin.py", session)
elif request == "Log Out":
    cdrcgi.logout(session)
elif request == "Continue":
    # Start all over again as if coming in for the first time
    request = None

# Get relevant variables from last viewed form
oldId         = fields.getvalue("oldId", None)
newPattern    = fields.getvalue("newPattern", None)
newAction     = fields.getvalue("newAction", None)
applyPatterns = fields.getvalue("applyPatterns", None)

# cdr.logwrite("request=%s oldId=%s newPattern=%s applyPatterns=%s newAction=%s" % (request, oldId, newPattern, applyPatterns, newAction))

# Is this the first time we're in the function?
if not (request or newAction or applyPatterns):
    # Show screen and exit
    showInitialScreen(session)

# Has user confirmed a change?
if request in ("Confirm Add", "Confirm Delete"):
    updateDB(session, oldId, newPattern)

# Perform requested action
if applyPatterns:
    if applyPatterns == "Apply":
        runMode = "run"
    else:
        runMode = "test"
    propagatePatterns(session, runMode)

if newAction == "add":
    if not newPattern:
        cdrcgi.bail("You must first create a new pattern to add it")
    checkPattern("addNew", session, pattern=newPattern)

if newAction == "del":
    checkPattern("delOld", session, patternId=oldId)

if newAction == "view":
    # cdrcgi.bail("request=%s, oldId=%s, newPattern=%s, newAction=%s" %\
    #   (request, oldId, newPattern, newAction))
    if not (newPattern or oldId):
        cdrcgi.bail(
         "You must enter a new pattern or select an existing one to view")
    if oldId:
        checkPattern("view", session, patternId=oldId)
    else:
        checkPattern("view", session, pattern=newPattern)

# Shouldn't get here
cdrcgi.bail("How did I get here?")
