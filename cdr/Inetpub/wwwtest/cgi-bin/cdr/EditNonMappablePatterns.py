#----------------------------------------------------------------------
# Edit the list of non-mappable external_map values.
#
# Allows a user to add or delete patterns from the list of regular
# expressions (in SQL "LIKE" format) for CTGov Facility values that
# cannot be mapped.
#
# $Id: EditNonMappablePatterns.py,v 1.2 2008-08-20 03:52:04 ameyer Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2008/07/23 05:08:56  ameyer
# Initial version.
#
#----------------------------------------------------------------------
import cgitb; cgitb.enable()

import cgi, cdrcgi, cdrdb, cdr

# Use same logfile used for changing values
LF=cdr.DEFAULT_LOGDIR + "/GlobalChangeCTGovMapping.log"

# Constants
MAINTITLE          = "Maintain CTGov non-Mapping Patterns"
SCRIPT             = "EditNonMappablePatterns.py"
MAX_DISPLAY_VALUES = 5000

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
    html = cdrcgi.header(MAINTITLE, MAINTITLE, "Add, delete, or view pattern",
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
        // var url="EditNonMappablePatterns.py?%s=" +
        //          document.getElementById("session").value +
        //          "&newAction=" + addOrView + "&newPattern=" +
        //          document.getElementById("newPattern").value;
        // location.href=url;
    }
 }
</script>
""" % cdrcgi.SESSION)

    html += """
<p>To create a new pattern, enter it, using SQL "LIKE" semantics, in the
input box and click the "<em>Add</em>" button to add it, or the
<em>View</em> button to just view matching values.</p>

<p>There are currently %d existing patterns.
To remove one, click the "<em>Del</em>" link for that pattern or the
<em>View</em> link to just view matching values.<p>

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
    html = cdrcgi.header(MAINTITLE, MAINTITLE, "View values matching pattern",
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
    html    = ""
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
  <td>Value from tde external map table</td>
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
    html += "".join(htmlSeq) + "\n</table>\n"

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
    buttons = ("Another", cdrcgi.MAINMENU, "Log Out")
    html = cdrcgi.header(MAINTITLE, MAINTITLE, "Update completed",
                         script=SCRIPT, buttons=buttons)

    html += """
<p>The update is complete, click "Another" above to perform another
pattern update</p>
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
elif request == "Another":
    # Start all over again as if coming in for the first time
    request = None

# Get relevant variables from last viewed form
oldId      = fields.getvalue("oldId", None)
newPattern = fields.getvalue("newPattern", None)
newAction  = fields.getvalue("newAction", None)

# cdr.logwrite("Top: oldId=%s, newPattern=%s, newAction=%s" %
#               (oldId, newPattern, newAction))

# Is this the first time we're in the function?
if not request and not newAction:
    # Show screen and exit
    showInitialScreen(session)

# Has user confirmed a change?
if request in ("Confirm Add", "Confirm Delete"):
    updateDB(session, oldId, newPattern)

# Perform requested action
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
