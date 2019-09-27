#----------------------------------------------------------------------
# Report information from the term_audio... database tables that
# track the review of Term audio files.
#
# BZIssue::5128
# JIRA::OCECDR-3800 - eliminated security vulnerabilities
#----------------------------------------------------------------------

import cgi
import cdrcgi
from cdrapi import db

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

    return zipData

# Main
if __name__ == "__main__":

    language  = None
    revStatus = None
    errors    = []

    # Find any posted parameters
    fields    = cgi.FieldStorage()
    session   = cdrcgi.getSession(fields)
    request   = cdrcgi.getRequest(fields)
    language  = fields.getvalue("language")
    revStatus = fields.getvalue("revStatus")
    startDate = fields.getvalue("startDate", "2010-01-01")
    endDate   = fields.getvalue("endDate", "2999-01-01")
    reportType= fields.getvalue("reportType", "full")
    beenHere  = fields.getvalue("beenHere")

    # Canceled?
    if request == "Admin Menu":
        cdrcgi.navigateTo("Admin.py", session)

    # Validate inputs
    if language and language not in ("English", "Spanish"):
        language = None
    if revStatus and revStatus not in ("A", "R", "U"):
        revStatus = None
    if not cdrcgi.is_date(startDate):
        startDate = "2010-01-01"
    if not cdrcgi.is_date(endDate):
        endDate = "2999-01-01"
    if reportType != "summary":
        reportType = "full"
    if beenHere:
        # Must specify langage and review status, dates can be defaulted
        if not language:
            errors.append("Language is required")
        if not revStatus:
            errors.append("Approval status is required")

        # Dates have to make sense
        if endDate < startDate:
            errors.append("End date cannot be before start date")

    # Extend end date to cover all of the time that day, not just 0:0:0
    endDate += " 23:59:59"

    #######################################################
    # Prompt for inputs if we don't have what we need
    #######################################################
    if not language or not revStatus or errors:
        buttons = ('Submit', 'Admin Menu')
        page = cdrcgi.Page(HEADER, subtitle="Enter report parameters",
                           action=SCRIPT, buttons=buttons, session=session)
        instructions = (
            "Select a language and approval status for the term names "
            "to include in the report.  Optionally add start and/or "
            "end dates for the term reviews to limit the size of the output."
        )
        page.add(page.B.FIELDSET(page.B.P(instructions)))
        if errors:
            page.add("<fieldset>")
            page.add(page.B.LEGEND("Validation Errors", page.B.CLASS("error")))
            page.add("<ul class='error'>")
            for error in errors:
                page.add(page.B.LI(error))
            page.add("</ul>")
            page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Language"))
        page.add_radio("language", "English", "English")
        page.add_radio("language", "Spanish", "Spanish")
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Approval Status"))
        page.add_radio("revStatus", "Approved", "A")
        page.add_radio("revStatus", "Rejected", "R")
        page.add_radio("revStatus", "Unreviewed", "U")
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Full or Summary Report"))
        page.add_radio("reportType", "Full report showing terms", "full",
                       checked=True)
        page.add_radio("reportType", "Summary report with grand totals only",
                       "summary")
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Optional Start and End Dates"))
        page.add_date_field("startDate", "Start date")
        page.add_date_field("endDate", "End date")
        page.add("</fieldset>")
        page.add(page.B.INPUT(name="beenHere", value="beenHere",
                              type="hidden"))
        page.send()

    #######################################################
    # We have input parameters.  Create the report.
    #######################################################

    # Connect to the database
    try:
        conn = db.connect()
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

    # Formatting for report
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
                if reportType == "full":
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
                zipId = row[0]
                if reportType == "full":
                    # Start a new zipfile output
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
            if reportType == "full":
                html.append("""\
 <tr>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
 </tr>""" % (row[1], str(row[2])[:10], row[3]))
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

    html = "".join(html)
    cdrcgi.sendPage(html)
