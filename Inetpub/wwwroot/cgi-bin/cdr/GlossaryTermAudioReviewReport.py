#----------------------------------------------------------------------
# $Id$
#
# Report information from the term_audio... database tables that
# track the review of Term audio files.
#
# BZIssue::5128
#----------------------------------------------------------------------

import cgi, cdrdb, cdrcgi
import cgitb
cgitb.enable()

# Constants
SCRIPT  = "GlossaryTermAudioReviewReport.py"
HEADER  = "Glossary Term Audio Review Statistical Report"
BUTTONS = (cdrcgi.MAINMENU, "Logout")

def bail(ctxtMsg, e=None):
    """
    Bail out, producing a debugging message.
    May or may not include an Exception object.

    Pass:
        ctxtMsg - Error context message.
        e       - Exception object of any type.
    """
    msg = "%s:<br />\n" % ctxtMsg
    if e is not None:
        msg += "Exception Type: %s</br />\n" % type(e)
        msg += "Exception msg: %s" % str(e)
    cdrcgi.bail(msg)


def createZipDict(cursor, language):
    """
    Create a dictionary of:
        zipfile_id => [filename, complete(Y/N), numApproved,
                       numRejected, numUnreviewed]

    Includes all zipfiles, we'll see which ones we need later.

    Pass:
        Database cursor.

    Return:
        Reference to dictionary.
    """
    # Dictionary to return
    zipData = {}

    sql = """
SELECT z.filename, z.id, complete, m.review_status, count(*) as count
  FROM term_audio_mp3 m
  JOIN term_audio_zipfile z
    ON m.zipfile_id = z.id
 WHERE m.language = ?
 GROUP BY z.filename, z.id, complete, m.review_status
 ORDER BY z.filename
"""
    try:
        cursor.execute(sql, language)
        rows = cursor.fetchall()
    except Exception as e:
            bail("Unable to select zipfile data", e)

    # No zipId yet
    zipId = -1

    for row in rows:
        # Parse row
        fname, zId, complete, revStat, revCount = row

        # Expecting 3 rows for 3 counters / zipfile
        if zId != zipId:
            # Load the dictionary
            zipRow = [fname, complete, 0, 0, 0]
            zipData[zId] = zipRow
            zipId = zId

        # Update counts by review status:
        if revStat == 'A':  zipRow[2] = revCount
        if revStat == 'R':  zipRow[3] = revCount
        if revStat == 'U':  zipRow[4] = revCount

    # html=u"<html><body>";
    # html+=u"".join(str(zipData))
    # html+=u"</body></html>"
    # cdrcgi.sendPage(html)

    return zipData

# Main
if __name__ == "__main__":

    language  = None
    revStatus = None
    errMsg    = ""

    # Find any posted parameters
    fields = cgi.FieldStorage()
    if fields:
        session   = cdrcgi.getSession(fields)
        request   = cdrcgi.getRequest(fields)
        language  = fields.getvalue("language", None)
        revStatus = fields.getvalue("revStatus", None)
        startDate = fields.getvalue("startDate", "2010-01-01")
        endDate   = fields.getvalue("endDate", "2999-01-01")
        beenHere  = fields.getvalue("beenHere", None)

        # Extend end date to cover all of the time that day, not just 0:0:0
        endDate += " 23:59:59"

        # Canceled?
        if request == "Admin Menu":
            cdrcgi.navigateTo("Admin.py", session)

        # User must specify langage and review status, dates can be defaulted
        if beenHere:
            if not language:
                errMsg += "Language is required<br />\n"
            if not revStatus:
                errMsg += "Approval status is required<br />\n"
            if errMsg:
                errMsg = "<p class='errmsg'>" + errMsg + "</p>\n"

    # Stylesheet for both versions of output
    stylesheet = """\
    <link type='text/css' rel='stylesheet'
          href='/stylesheets/CdrCalendar.css'>
    <script type='text/javascript' language='JavaScript'
             src='/js/CdrCalendar.js'></script>
    <style type='text/css'>
      h1         {font: 16pt 'Times New Roman'; font-weight: bold;
                  text-align: center;}
      .errmsg    {font: 11pt 'Times New Roman'; color: red; font-weight: bold;}
      th         {font: 12pt 'Times New Roman'; font-weight: bold;
                  background-color: blue; color: white; text-align: left;}
      td         {font: 11pt 'Times New Roman';}
      /* tr:nth-child(odd) {background-color: #ffe; } */
      td.summary {font: 10pt 'Times New Roman'; font-weight: bold;}
      p          {font: 14pt 'Times New Roman';}
      p.totals   {text-align: center; font-weight: bold;}
      table.data {margin-left: auto; margin-right: auto;
                  margin-bottom: 2em; width: 75%;}
     </style>"""

    html = []

    #######################################################
    # Prompt for inputs if we don't have what we need
    #######################################################
    if not fields or not language or not revStatus:
        # Headers
        buttons = ('Submit', 'Admin Menu')
        html.append(cdrcgi.header(HEADER, HEADER,
                                  "Enter report parameters",
                                  script=SCRIPT, buttons=buttons,
                                  stylesheet=stylesheet))

        # html.append("<h1>Term Audio Pronunciation Review Report</h1>")

        html.append("""\
<p>Select a language and approval status for the term names to include in the
report.  Optionally add start and/or end dates for the term reviews to
limit the size of the output.</p>
%s
<fieldset>
 <legend> Select Language </legend>
   <input type="radio" name="language" value="English" />
   <label for="English">English</label>
   <br />
   <input type="radio" name="language" value="Spanish" />
   <label for="Spanish">Spanish</label>
</fieldset>
<fieldset>
 <legend> Select Approval Status </legend>
   <input type="radio" name="revStatus" value="A" />
   <label for="A">Approved</label>
   <br />
   <input type="radio" name="revStatus" value="R" />
   <label for="R">Rejected</label>
   <br />
   <input type="radio" name="revStatus" value="U" />
   <label for="U">Unreviewed</label>
</fieldset>
<fieldset>
 <legend> Optional Start and End Dates </legend>
   <input type="text" name="startDate" id="startDate"
          class="CdrDateField size="10" />
   <label for="startDate">Start date (YYYY-MM-DD)</label>
   <br />
   <input type="text" name="endDate" id="endDate"
          class="CdrDateField size="10" />
   <label for="endDate">End date (YYYY-MM-DD)</label>
</fieldset>

<input type="hidden" name="beenHere" value="beenHere" />
<input type="hidden" name="%s" value="%s" />
</form>
</body>
</html>""" % (errMsg, cdrcgi.SESSION, session))

        html = u"\n".join(html)
        cdrcgi.sendPage(html)

    #######################################################
    # We have input parameters.  Create the report.
    #######################################################

    # Connect to the database
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
    except Exception as e:
        bail("Unable to access database", e)

    # Get information about all of the zipfiles
    zipData = createZipDict(cursor, language)

    # Get all of the term by term review info
    qry = """
SELECT z.id, m.term_name, m.review_date, u.fullname
  FROM term_audio_mp3 m
  JOIN usr u
    ON m.reviewer_id = u.id
  JOIN term_audio_zipfile z
    ON m.zipfile_id = z.id
 WHERE m.language = ?
   AND m.review_status = ?
   AND m.review_date >= ?
   AND m.review_date <= ?
 ORDER BY z.filename, m.term_name
"""

    try:
        cursor.execute(qry, (language, revStatus, startDate, endDate))
    except Exception as e:
        bail("Error fetching term status", e)

    html = []
    buttons = ("Another report", cdrcgi.MAINMENU)
    html.append(cdrcgi.header(HEADER, HEADER,
                              "Pronunciation report",
                              script=SCRIPT, buttons=buttons,
                              stylesheet=stylesheet))

    # Description of the report
    if revStatus == 'A': statusName = "Approved"
    if revStatus == 'R': statusName = "Rejected"
    if revStatus == 'U': statusName = "Unreviewed"

    # Accumulators for counts of each status
    countApproved   = 0
    countRejected   = 0
    countUnreviewed = 0

    html.append("<h1>%s %s Audio Pronunciations</h1>\n" %
                (statusName, language))

    # Initialize zipId to no legal value
    zipId = -1

    while True:
        row = cursor.fetchone()
        if not row or row[0] != zipId:
            # Terminate old zipfile if we have one
            if zipId >=0:
                html.append("""\
 <tr>
  <td class='summary' colspan='3'>Subtotal - %s only: &nbsp;
  Approved=%d &nbsp; Rejected=%d &nbsp; Unreviewed=%d</td>
 </tr>
</table>
""" % (language, zipData[zipId][2], zipData[zipId][3], zipData[zipId][4]))

                # Add subtotals to totals
                countApproved   += zipData[zipId][2]
                countRejected   += zipData[zipId][3]
                countUnreviewed += zipData[zipId][4]

        if row:
            if row[0] != zipId:
                # Start a new zipfile output
                zipId = row[0]
                html.append("""\
<table class='data' border="1">
 <tr>
  <th colspan='3'>%s</th>
 </tr>
 <tr>
  <th width='50%%'>Term</th>
  <th width='20%%'>Review Date</th>
  <th width='30%%'>User</th>
 </tr>
""" % zipData[zipId][0])
            html.append("""\
 <tr>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
 </tr>""" % (row[1], row[2][:10], row[3]))
        else:
            break

    # Final totals
    if countApproved + countRejected + countUnreviewed == 0:
        html += """
<p>No terms were found for the language and date range of the report.<p>
"""
    else:
        html += """
<p class='totals'>Total - %s only for these zipfiles: &nbsp;
  Approved=%d &nbsp; Rejected=%d &nbsp; Unreviewed=%d</td></p>
""" % (language, countApproved, countRejected, countUnreviewed)

    html.append("""\
<input type="hidden" name="%s" value="%s" />
</table>
</form>
</body>
</html>
""" % (cdrcgi.SESSION, session))


    html = u"".join(html)
    cdrcgi.sendPage(html)
