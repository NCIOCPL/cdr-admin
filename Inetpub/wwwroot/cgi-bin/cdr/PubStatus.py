#----------------------------------------------------------------------
#
# $Id$
#
# Status of a publishing job.
#
# $Log: not supported by cvs2svn $
# Revision 1.32  2008/04/28 16:48:59  venglisc
# Changed the formatting to display errors in red and changed strings to
# Unicode strings. (Bug 3923)
#
# Revision 1.31  2008/02/26 23:47:24  venglisc
# Minor modifications to FilterFailure output to make HTML valid and display
# validation messages. (Bug 3923)
#
# Revision 1.30  2008/01/17 16:03:36  venglisc
# Modifying pushing information after completed job (Bug 3736)
#
# Revision 1.29  2007/12/28 22:41:29  venglisc
# During the new Gatekeeper test phase we needed to be able to review
# pushed documents even though the push job's status was 'Verifying' instead
# of 'Success'.
# Additional minor formatting (CSS) changes and we increased the number of
# documents to be displayed.
#
# Revision 1.28  2007/08/07 20:08:39  ameyer
# Upgraded an error message.  No changes to logic.
#
# Revision 1.27  2007/05/01 21:29:14  venglisc
# Test Message.
#
# Revision 1.26  2007/02/21 00:39:10  ameyer
# If the request specifies jobs to be resumed or killed, we now check
# to be sure the job was still in a Waiting state before proceeding.  This
# prevents errors caused by use of the back, or refresh buttons or by use
# of multiple tabs or windows.
#
# Revision 1.25  2007/02/20 23:57:15  venglisc
# Added line break to correct display of text area.
#
# Revision 1.24  2006/10/19 22:51:56  ameyer
# Added logging of updates of the pub_proc table to publish.log.
#
# Revision 1.23  2006/08/28 22:06:54  venglisc
# Fixed problem causing the first row of the report to be dropped. (Bug 2453)
#
# Revision 1.22  2006/08/24 15:35:24  venglisc
# Minor changes to the if statement listing flavor error report.
#
# Revision 1.21  2006/08/24 14:16:49  venglisc
# Added default else: block to catch invalid entry of 'flavor'.
#
# Revision 1.20  2006/07/05 20:21:35  venglisc
# Modified program to add three flavors of the FilterFailure report:
# flavor = full (default), warning (full w/o errors), error (full w/o warning)
# Since the number of benign warning messages is constantly increasing this
# will allow us to identify true problems (a.k.a. errors) quickly. (Bug 2283)
#
# Revision 1.19  2005/07/28 23:05:08  venglisc
# Modified the program to check all push jobs by default.  This eliminates
# the problem that a push job may be submitted without having checked the
# particular job.  Now a job needs to be unchecked if it should not be
# processed.
#
# Revision 1.18  2005/03/25 17:02:40  venglisc
# Corrected anker link to updated/removed/added section.
# Modified table output by inserting a space after each semicolon ';' to
# allow protocols with many protocol IDs to format properly.
#
# Revision 1.17  2005/01/24 19:29:59  venglisc
# Minor changes to correctly display the FilterFailure error report table.
#
# Revision 1.16  2004/09/27 16:51:00  venglisc
# Modified header alignment of table to align left.
#
# Revision 1.15  2004/03/19 18:48:35  venglisc
# Modified code to pick up document types (the rows of the statistics report)
# from a database query instead of having them hard coded.
# Also made some minor formatting changes:  table columns are now same size.
#
# Revision 1.14  2004/02/27 18:40:05  venglisc
# Added CTGovProtocol Document type to the report output.  Alphabetized the
# display of the document types.
#
# Revision 1.13  2003/08/25 17:54:05  bkline
# Replaced SQL queries for publication job report with queries that are:
#  * much more efficient;
#  * easier to understand; and
#  * correct.
#
# Revision 1.12  2003/06/09 18:56:30  pzhang
# Fixed a bug in TABLE end tag.
# Changed latin-1 to utf8 in html.encode().
#
# Revision 1.11  2003/03/05 16:16:30  pzhang
# Added messages to be part of the failure report.
# Column messages are normally NULL unless something is wrong.
#
# Revision 1.10  2003/02/13 23:05:36  pzhang
# Added CgJobDesc textarea for pushing job description.
# Added code to report published documents.
#
# Revision 1.9  2003/01/08 22:26:31  pzhang
# Added a draft of dispJobDiff().
# Displayed output_dir as None when it is "".
#
# Revision 1.8  2002/11/05 16:04:34  pzhang
# Enhanced interface per Eileen's input
#
# Revision 1.7  2002/09/11 21:11:18  pzhang
# Displayed the top 500 document infor for each type.
#
# Revision 1.6  2002/08/20 15:58:04  pzhang
# Checked session validity before killing or resuming.
#
# Revision 1.5  2002/08/19 22:04:23  pzhang
# Added dispJobSetting(), dispJobControl() and dispCgWork().
#
# Revision 1.4  2002/08/19 16:23:34  pzhang
# Added dispFilterFailures().
#
# Revision 1.3  2002/04/25 21:12:22  bkline
# Fixed bug which was overwriting name of publishing system.
#
# Revision 1.2  2002/02/14 21:46:52  mruben
# Added support for no_output flag [bkline for mruben].
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, re, string, time

# Logfile is same as that used in cdrpub.py
LOG         = "d:/cdr/log/publish.log"
WAIT_STATUS = "Waiting user approval"

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
jobId    = fields and fields.getvalue("id") or None
dispType = fields and fields.getvalue("type") or None
session  = fields and fields.getvalue("Session") or None
request  = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate') or None
docType  = fields and fields.getvalue('docType') or None
cgMode   = fields and fields.getvalue('cgMode') or None
flavor   = fields and fields.getvalue('flavor') or 'full'
docCount = int(fields and fields.getvalue('docCount') or '0')

# Number of documents to be displayed on Pushing Information Report
TOPDOCS  = 5000

#----------------------------------------------------------------------
# Display the publishing overall job status.
#----------------------------------------------------------------------
def dispJobStatus():

    #----------------------------------------------------------------------
    # Find some interesting information.
    #----------------------------------------------------------------------
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT d.title,
                   p.pub_subset,
                   u.name,
                   p.output_dir,
                   p.started,
                   p.completed,
                   p.status,
                   p.messages,
                   p.no_output
              FROM document d
              JOIN pub_proc p
                ON p.pub_system = d.id
              JOIN usr u
                ON u.id = p.usr
             WHERE p.id = ?
    """, (jobId,))

        # If we manually enter a JobID for that doesn't exist yet
        # fetching the result will fail and create an error
        # -------------------------------------------------------
        try:
            (pubSystem, subset, name, dir, started, completed, status,
             messages, no_output) = cursor.fetchone()
        except:
            cdrcgi.bail('Job%d does not exist!' % jobId)

    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving job information: %s" % info[1][0])

    title   = "CDR Publishing Job Status"
    instr   = "Job Number %d" % jobId
    setting = """[<A style="text-decoration: underline;" href=
                "pubstatus.py?id=%d&type=Setting">Job settings
                 </A>]""" % jobId
    buttons = []
    header  = cdrcgi.header(title, title, instr, None, buttons)
    html    = """\
       <TABLE>
        <TR>
         <TD class="tlabel">Publishing System: &nbsp;</B></TD>
         <TD class="ttext">%s</TD>
        </TR>
        <TR>
         <TD class="tlabel">System Subset: &nbsp;</B></TD>
         <TD class="ttext">%s %s</TD>
        </TR>
        <TR>
         <TD class="tlabel">User Name: &nbsp;</B></TD>
         <TD class="ttext">%s</TD>
        </TR>
        <TR>
         <TD class="tlabel">Output Location: &nbsp;</B></TD>
         <TD class="ttext">%s</TD>
        </TR>
        <TR>
         <TD class="tlabel">Started: &nbsp;</B></TD>
         <TD class="ttext">%s</TD>
        </TR>
        <TR>
         <TD class="tlabel">Completed: &nbsp;</B></TD>
         <TD class="ttext">%s</TD>
        </TR>
        <TR>
         <TD class="tlabel">Status: &nbsp;</B></TD>
         <TD class="ttext">%s</TD>
        </TR>
        <TR>
         <TD class="tlabel">Messages: &nbsp;</B></TD>
         <TD class="ttext">%s</TD>
        </TR>
       </TABLE>
      </FORM>
     </BODY>
    </HTML>
    """ % (pubSystem, subset, setting, name,
           (no_output == 'Y' and "None") or dir or "None",
           started, completed and completed or "No", status, messages)
    cdrcgi.sendPage(header + html)

#----------------------------------------------------------------------
# Add a table row for an published documents.
#----------------------------------------------------------------------
def addRow(row):
    # Replacing the ";" for the document title since this caused the
    # table formatting to be off due to too words that couldn't be
    # wrapped within the given column width.
    # --------------------------------------------------------------
    return u"""\
   <tr>
    <td valign='top'>%d</td>
    <td valign='top'>%d</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (row[0], row[1], row[2], string.replace(row[3], ";", "; "), row[4])

#----------------------------------------------------------------------
# Display the filter failures: docId, docVer, docType, docTitle, Message.
#----------------------------------------------------------------------
def dispFilterFailures(flavor = 'full'):

    #----------------------------------------------------------------------
    # Find some interesting information.
    #----------------------------------------------------------------------
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT ppd.doc_id,
                   ppd.doc_version,
                   t.name,
                   d.title,
                   ppd.messages,
                   pp.pub_subset,
                   u.name
              FROM pub_proc_doc ppd
              JOIN document d
                ON ppd.doc_id = d.id
              JOIN pub_proc pp
                ON ppd.pub_proc = pp.id
              JOIN usr u
                ON u.id = pp.usr
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE ppd.pub_proc = ?
               AND (ppd.failure = 'Y' OR ppd.messages IS NOT NULL)
          ORDER BY t.name, d.title
    """, (jobId,))
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving job information: %s" % info[1][0])

    title   = u'CDR Publishing Filter Failures'
    instr   = u'Job Number %d' % jobId
    buttons = []
    header  = cdrcgi.header(title, title, instr, None, buttons)
    if not rows:
        cdrcgi.bail("Job%s finished without Failure" % jobId)
    html    = u"""\
       <TABLE>
        <TR>
         <TD ALIGN='right' NOWRAP><B>System Subset: &nbsp;</B></TD>
         <TD>%s</TD>
        </TR>
        <TR>
         <TD ALIGN='right' NOWRAP><B>User Name: &nbsp;</B></TD>
         <TD>%s</TD>
        </TR>
       </TABLE>
    """ % (rows[0][5], rows[0][6])

    html   += u"<BR><TABLE BORDER=1>"
    html   += u"""\
   <tr>
    <td width='10%%' valign='top'><B>Id</B></td>
    <td width='5%%'  valign='top'><B>Ver</B></td>
    <td width='15%%' valign='top'><B>Type</B></td>
    <td width='40%%' valign='top'><B>Title</B></td>
    <td width='35%%' valign='top'><B>Message</B></td>
    </tr>
"""
    # The warnings have been formatted with a "class=warning"
    # attribute for the LI element.
    # -------------------------------------------------------
    textPattern = re.compile(u'<LI class="(.*)</LI>')
    textPattern2 = re.compile(u'<Messages><message>')
    textPattern3 = re.compile(u'</message></Messages>')
    ### errorPattern = re.compile(u'DTDerror')
    errorPattern = re.compile(u'error')

    for row in rows:
        text = textPattern.search(row[4])    # searching for warnings
        eText = errorPattern.search(row[4])  # searching for errors

        if flavor == 'full':
            html += addRow(row)
        elif flavor == 'warning':
            # Only print the row if the pattern was found
            # -------------------------------------------
            if text and not eText:
               html += addRow(row)
        elif flavor == 'error':
            # Print the row if the error pattern was found
            # (it might also contain warnings)
            # --------------------------------------------
            if eText:
               html += addRow(row)
        else:
            cdrcgi.bail('Error: Valid values for flavor are: '
                        '"full", "warning", "error"')

    html  += u'</TABLE></FORM></BODY></HTML>'
    html   = textPattern2.sub(u'<UL style="padding: 0px; margin: 0px; margin-left: 20px">', 
                                       html)
    html   = textPattern3.sub(u'</UL>', html)

    cdrcgi.sendPage(header + html)

#----------------------------------------------------------------------
# Display the job parameters.
#----------------------------------------------------------------------
def dispJobSetting():

    #----------------------------------------------------------------------
    # Find some interesting information.
    #----------------------------------------------------------------------
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT ppp.parm_name,
                   ppp.parm_value,
                   pp.pub_subset,
                   u.name
              FROM pub_proc_parm ppp
              JOIN pub_proc pp
                ON ppp.pub_proc = pp.id
              JOIN usr u
                ON u.id = pp.usr
             WHERE ppp.pub_proc = ?
          ORDER BY ppp.parm_name
    """, (jobId,))
        row = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving job information: %s" % info[1][0])

    title   = "CDR Publishing Job Settings"
    instr   = "Job Number %d" % jobId
    buttons = []
    header  = cdrcgi.header(title, title, instr, None, buttons)
    html    = """\
               <TABLE>
                <TR>
                 <TD class="tlabel">System Subset: &nbsp;</TD>
                 <TD class="ttext">%s</TD>
                </TR>
                <TR>
                 <TD class="tlabel">User Name: &nbsp;</TD>
                 <TD class="ttext">%s</TD>
                </TR>
               </TABLE>
              """ % (row[2], row[3])

    html   += "<BR><TABLE BORDER=1>"
    html   += """\
               <tr>
                <td valign='top'><B>ParamName</B></td>
                <td valign='top'><B>ParamValue</B></td>
                </tr>
              """
    ROW     = "<tr><td>%s</td><td>%s</td></tr>\n"

    html   += ROW % (row[0], row[1])

    row = cursor.fetchone()
    while row:
        html += ROW % (row[0], row[1])
        row   = cursor.fetchone()

    html  += "</TABLE></BODY></HTML>"

    cdrcgi.sendPage(header + html)

#----------------------------------------------------------------------
# Display the job control page.
#----------------------------------------------------------------------
def dispJobControl():

    # Need CdrPublishing to update pub_proc status.
    conn = cdrdb.connect('CdrPublishing')
    conn.setAutoCommit(1)
    cursor = conn.cursor()

    # Check session validity first by getting user name.
    try:
        cursor.execute("""\
            SELECT TOP 1 u.name
              FROM usr u
              JOIN session s
                ON s.usr = u.id
             WHERE s.name = ?
                       """, (session,))
        row = cursor.fetchone()
        if row and row[0]:
            name = row and row[0]
        else:
            cdrcgi.bail("Invalid session, failure getting user name")
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting user name: %s" % info[1][0])

    # Get a list of jobs to be killed or resumed.
    jobs = fields and fields.getvalue("Jobs") or []
    if jobs and type(jobs) != type([]):
        jobs = [jobs]

    # Kill or resume?
    action = fields and fields.getvalue("Kill") or \
             fields and fields.getvalue("Resume") or ""

    # Check to be sure that jobs are still in wait state.
    # This guards against using the back button, post refresh, or
    #   second tab or window to accidentally resume or kill a job
    #   that was already processed.
    if action and jobs:
        jobsOkay = True
        for job in jobs:
            jobNum = int(job)
            try:
                cursor.execute("""
                    SELECT status
                      FROM pub_proc
                     WHERE id = %d""" % jobNum)
            except cdrdb.Error, info:
                cdrcgi.bail("Failure checking job status: %s" % info[1][0])

            jobStatus = cursor.fetchone()[0]
            if jobStatus != WAIT_STATUS:
                cdrcgi.bail("""
You tried to resubmit job %d, but it is no longer "%s"<br>
Did you accidentally press Back or Refresh?<br>
Please access from the main publishing menu""" % \
                (jobNum, WAIT_STATUS))

    # CG job description sent to GateKeeper.
    cgJobDesc = fields and fields.getvalue("CgJobDesc") or ""
    cgJobDesc = "<CgJobDesc>%s</CgJobDesc>" % cgJobDesc
    if action == "Resume checked jobs":
        jobChecked = int(jobs[0])
        try:
            cursor.execute("""
                SELECT messages
                  FROM pub_proc
                 WHERE id = %d
                           """ % jobChecked
                          )
            row = cursor.fetchone()
            msg = (row and row[0] or '') + cgJobDesc

            cursor.execute("""
                UPDATE pub_proc
                   SET messages  = ?
                 WHERE id        = ?""", (msg, jobChecked))
            cdr.logwrite('%s updated pub_proc messages with "%s"' % \
                         (name, msg), LOG)
        except cdrdb.Error, info:
            msg = 'Failure updating message: %s' % info[1][0]
            raise Exception(msg)

    # Go ahead and kill or resume!
    msg = ""
    if action and jobs:
        msg += " [Jobs just "
        if action == "Kill checked jobs":
            msg += "killed:"
            status = "Failure"
        else:
            msg += "resumed:"
            status = "In process"
        for job in jobs:
            msg += "%s, " % job
            try:
                cursor.execute("""\
                    UPDATE pub_proc
                       SET status = ?
                     WHERE id = ?
                               """, (status, job))
                cdr.logwrite('%s updated pub_proc status to "%s"' % \
                             (name, status), LOG)
            except cdrdb.Error, info:
                cdrcgi.bail("Failure killing or resuming: %s" % info[1][0])
        msg = msg[:-2] + "]"

    # Get jobs waiting for user approval.
    try:
        cursor.execute("""\
            SELECT pp.id,
                   pp.pub_subset,
                   pp.started,
                   pp.status
              FROM pub_proc pp
              JOIN usr u
                ON u.id = pp.usr
              JOIN session s
                ON s.usr = u.id
             WHERE s.name = ?
               AND pp.status = ?
          ORDER BY pp.started
                       """, (session, WAIT_STATUS))
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting pending job: %s" % info[1][0])

    title   = "CDR Publishing Job Controller"
    script  = "PubStatus.py"
    instr   = "User Name %s" % name
    buttons = []
    header  = cdrcgi.header(title, title, instr, script, buttons)

    HEADER1 = """
               <BR>
               <span style="color: navy; font-weight: bold;"> Jobs 
                waiting for user approval%s</span>
               <BR><TABLE BORDER=0>
              """ % msg
    HEADER2 = """
                <tr><td>
                <table border="1">
                <tr>
                <td class="tlabel"></td>
                <td class="tlabel">JobId</td>
                <td class="tlabel">JobName</td>
                <td class="tlabel">Started</td>
                <td class="tlabel">Status</td>
                </tr>
              """
    ROW     = """<tr><td><INPUT TYPE='CHECKBOX' NAME='Jobs' VALUE='%d' CHECKED></td>
                     <td class="ttext">%d</td>
                     <td class="ttext">%s</td>
                     <td class="ttext">%s</td>
                     <td class="ttext">%s</td></tr>
              """

    if not len(rows):
        html = "User <i>%s</i>: There are no (more) push jobs waiting for approval." % name
    else:
        html = """
            <INPUT TYPE='HIDDEN' NAME='id' VALUE='%d'>
            <INPUT TYPE='HIDDEN' NAME='Session' VALUE='%s'>
            <INPUT TYPE='HIDDEN' NAME='type' VALUE='Manage'>
                """ % (jobId, session)

        html += HEADER1
        html += """
                <tr>
                 <td>
                  <table border="0" width="100%%">
                   <tr>
                    <td colspan="5" align="center" valign="center">
                    <br/>
                    <INPUT TYPE='SUBMIT' NAME='Kill' VALUE='Kill checked jobs'>
                    <INPUT TYPE='SUBMIT' NAME='Resume' VALUE='Resume checked jobs'>
                    <br/>&nbsp;
                   </td>
                  </tr>
                 </table>
                </td>
               </tr>
                """
        html += HEADER2

        for row in rows:
            html += ROW % (row[0], row[0], row[1], row[2], row[3])
        html += "</TABLE></td></tr></table>"
        html += "<BR><span style='color: navy;'>Resume checked job(s) with "
        html += "the following description</span><br/>"
        html += "<TEXTAREA NAME='CgJobDesc' ROWS='5' COLS='80'>"
        html += "Enter a brief job description for Cancer.gov.</TEXTAREA>"

    html  += "</BODY></HTML>"

    cdrcgi.sendPage(header + html)

#----------------------------------------------------------------------
# Display the pub_proc_cg_work table info.
#----------------------------------------------------------------------
def dispCgWork():

    title   = "CDR Document Pushing Information"
    instr   = "Job Number %d" % jobId
    buttons = []
    header  = cdrcgi.header(title, title, instr, None, buttons)

    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()

    ###
    # The pub_proc_cg_work table only holds the data from the last
    # push job.  If the user is trying to get the information from 
    # a previous push job display a notification that this is not
    # the data he/she is looking for.
    # -------------------------------------------------------------
    try:
        cursor.execute("""\
             SELECT max(id)
               FROM pub_proc
              WHERE pub_system = 178
                AND pub_subset like 'Push_Documents_to_Cancer.gov_%'
                       """)
        lastPushJob = cursor.fetchone()
        if lastPushJob and lastPushJob[0] > jobId:
            cdrcgi.bail("Sorry, but another push job (Job%s) already removed \
                         the data you're looking for!" % lastPushJob[0])
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting latest push job ID: %s" % info[1][0])

    ###

    # Is there any documents in PPCW?
    try:
        cursor.execute("""\
            SELECT count(*)
              FROM pub_proc_cg_work ppcw
                       """)
        numRows = cursor.fetchone()
        if numRows and numRows[0] == 0:
            cdrcgi.bail("No rows in pub_proc_cg_work. No docs to be pushed.")
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting row count in PPCW: %s." % info[1][0])

    #----------------------------------------------------------------------
    # Find vendor and push jobs.
    #----------------------------------------------------------------------
    try:
        cursor.execute("""\
            SELECT ppv.pub_subset, ppp.pub_subset
              FROM pub_proc_cg_work ppcw
              JOIN pub_proc ppv
                ON ppv.id = ppcw.vendor_job
              JOIN pub_proc ppp
                ON ppp.id = ppcw.cg_job
                       """)
        (vendor, push) = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting vendor and push job info from PPCW.")

    #----------------------------------------------------------------------
    # Find number of removed documents.
    #----------------------------------------------------------------------
    try:
        cursor.execute("""\
            SELECT count(ppcw.id)
              FROM pub_proc_cg_work ppcw
             WHERE ppcw.xml IS NULL
                       """)
        oneRow = cursor.fetchone()
        nRemoved = 0
	if oneRow and oneRow[0]:
	    nRemoved = oneRow[0]
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting removed count from PPCW.")

    #----------------------------------------------------------------------
    # Find removed document information.
    #----------------------------------------------------------------------
    try:
        numDocs = (nRemoved > TOPDOCS) and TOPDOCS or nRemoved or 1
        cursor.execute("""\
            SELECT TOP %d ppcw.id, ppcw.doc_type, d.title
              FROM pub_proc_cg_work ppcw
              JOIN document d
                ON d.id = ppcw.id
             WHERE ppcw.xml IS NULL
          ORDER BY ppcw.doc_type, d.title
                       """ % numDocs)
        rowsRemoved = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting removed info from PPCW.")

    #----------------------------------------------------------------------
    # Find number of updated documents.
    #----------------------------------------------------------------------
    try:
        cursor.execute("""\
            SELECT count(*)
              FROM pub_proc_cg_work ppcw
              JOIN pub_proc_cg ppc
                ON ppcw.id = ppc.id
             WHERE NOT ppcw.xml IS NULL
                       """)
        oneRow = cursor.fetchone()
        nUpdated = 0
	if oneRow and oneRow[0]:
	    nUpdated = oneRow[0]
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting updated count from PPCW.")

    #----------------------------------------------------------------------
    # Find updated document information.
    #----------------------------------------------------------------------
    try:
        numDocs = (nUpdated > TOPDOCS) and TOPDOCS or nUpdated or 1
        cursor.execute("""\
            SELECT TOP %d ppcw.id, ppcw.doc_type, d.title
              FROM pub_proc_cg_work ppcw
              JOIN document d
                ON d.id = ppcw.id
              JOIN pub_proc_cg ppc
                ON ppcw.id = ppc.id
             WHERE NOT ppcw.xml IS NULL
          ORDER BY ppcw.doc_type, d.title
                       """ % numDocs)
        rowsUpdated = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting updated info from PPCW.")

    #----------------------------------------------------------------------
    # Find number of added documents.
    #----------------------------------------------------------------------
    try:
        cursor.execute("""\
            SELECT count(*)
              FROM pub_proc_cg_work ppcw
              JOIN document d
                ON d.id = ppcw.id
             WHERE NOT ppcw.xml IS NULL
               AND NOT EXISTS (
                       SELECT *
                         FROM pub_proc_cg ppc
                        WHERE ppc.id = ppcw.id
                              )
                       """)
        oneRow = cursor.fetchone()
        nAdded = 0
	if oneRow and oneRow[0]:
	    nAdded = oneRow[0]
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting added count from PPCW.")

    #----------------------------------------------------------------------
    # Find added document information.
    #----------------------------------------------------------------------
    try:
        numDocs = (nAdded > TOPDOCS) and TOPDOCS or nAdded or 1
        cursor.execute("""\
            SELECT TOP %d ppcw.id, ppcw.doc_type, d.title
              FROM pub_proc_cg_work ppcw
              JOIN document d
                ON d.id = ppcw.id
             WHERE NOT ppcw.xml IS NULL
               AND NOT EXISTS (
                       SELECT *
                         FROM pub_proc_cg ppc
                        WHERE ppc.id = ppcw.id
                              )
          ORDER BY ppcw.doc_type, d.title
                       """ % numDocs)
        rowsAdded = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting added info from PPCW.")

    # Create links when appropriate.
    LINK     = "<A style='text-decoration: underline;' href='#%s'>%d</A>"
    lRemoved = nRemoved and LINK % ('Removed', nRemoved) or '%d' % nRemoved
    lUpdated = nUpdated and LINK % ('Updated', nUpdated) or '%d' % nUpdated
    lAdded   = nAdded and LINK % ('Added', nAdded) or '%d' % nAdded

    html    = """\
        <TABLE>
           <TR>
             <TD ALIGN='right' NOWRAP><B>Vendor Job Name: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Pushing Job Name: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Removed Documents: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Updated Documents: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Added Documents: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>
           </TABLE>
              """ % (vendor, push, lRemoved, lUpdated, lAdded)

    HEADER  = """\
               <BR>
               <span style="color: red; font-weight: bold;">Documents 
                 %s %s</span>
               <BR>
               <a NAME='%s'></a>
               %s
               <TABLE BORDER=1>
                <tr>
                <th class="theader">DocId</th>
                <th class="theader">DocType</th>
                <th class="theader">DocTitle</th>
                </tr>
              """
    ROW     = """<tr><td class="ttext">%s</td>
                     <td class="ttext">%s</td>
                     <td class="ttext">%s</td></tr>"""

    # Only if the push job hasn't finished yet will we be able to 
    # display the newly added documents.  Once the job finished the 
    # comparison between pub_proc_cg and pub_proc_cg_work will give
    # incorrect results and new documents will be listed as updated
    # once.  We want to warn the user about this fact.
    # -------------------------------------------------------------
    try:
        cursor.execute("""\
             SELECT status
               FROM pub_proc
              WHERE pub_system = 178
                AND pub_subset like 'Push_Documents_to_Cancer.gov_%'
                AND id = ?
                       """, jobId)
        jobStatus = cursor.fetchone()[0]
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting latest push job ID: %s" % info[1][0])

    # Inserting a space after ';' to allow line breaks between
    # protocol numbers in HTML output.        VE, 2005-03-25
    # --------------------------------------------------------
    listCount = ""
    DISCLAIMER = "<br>"
    if nRemoved:
        if nRemoved > TOPDOCS:
            listCount = "(Top %s only)" % TOPDOCS
        html   += HEADER % ('Removed', listCount, 'Removed', DISCLAIMER)
        for row in rowsRemoved:
            html += ROW % (row[0], row[1], string.replace(row[2], ';', '; '))
        html  += "</TABLE></BODY>"

    if nAdded:
        if nAdded > TOPDOCS:
            listCount = "(Top %s only)" % TOPDOCS
        html   += HEADER % ('Added', listCount, 'Added', DISCLAIMER)
        for row in rowsAdded:
            html += ROW % (row[0], row[1], string.replace(row[2], ';', '; '))
        html  += "</TABLE></BODY>"

    if nUpdated:
        if jobStatus in ['Verifying', 'Success']:
            DISCLAIMER = """\
            <b>Note:</b> The push job already finished. Any newly 
            added documents are now displayed as updates.<br><br>"""
        if nUpdated > TOPDOCS:
            listCount = "(Top %s only)" % TOPDOCS
        html   += HEADER % ('Updated', listCount, 'Updated', DISCLAIMER)

        for row in rowsUpdated:
            html += ROW % (row[0], row[1], string.replace(row[2], ';', '; '))
        html  += "</TABLE></BODY>"

    html  += "</HTML>"

    cdrcgi.sendPage(header + html)

#----------------------------------------------------------------------
# Show a period to pick publishing jobs.
#----------------------------------------------------------------------
def selectPubDates():

    title   = "CDR Administration"
    instr   = "Publishing Job Activities"
    buttons = ["Submit Request", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
    script  = "PubStatus.py"
    header  = cdrcgi.header(title, title, instr, script, buttons)

    now         = time.localtime(time.time())
    toDate      = time.strftime("%Y-%m-%d", now)
    then        = list(now)
    then[1]    -= 1
    then[2]    += 1
    then        = time.localtime(time.mktime(then))
    fromDate    = time.strftime("%Y-%m-%d", then)
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2002-01-01)</TD>
    </TR>
    <TR>
     <TD><B>End Date:&nbsp;</B></TD>
     <TD><INPUT NAME='ToDate' VALUE='%s'>&nbsp;</TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, fromDate, toDate)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Show all publishing jobs within the period.
#----------------------------------------------------------------------
def dispJobsByDates():

    title   = "CDR Administration"
    instr   = "Publishing Job Summary"
    buttons = ["Report Menu", cdrcgi.MAINMENU, "Log Out"]
    script  = "PubStatus.py"
    header  = cdrcgi.header(title, title, instr, script, buttons,
                            stylesheet = """
  <style type = 'text/css'>
    th             { font: bold 16px arial; 
                     background-color:  #AFAFAF; }
   .text           { font: bold 10pt arial; 
                     color: black; }
   .link           { font: bold 10pt arial; 
                     color: black; }
  </style>
                            """)

    conn   = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()

    form = """
      <center style="font: bold 18px arial;">
        <span>Publishing Job Report<br />From %s to %s</span>
      </center>
      <br />
      <br />
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
           """ % (fromDate, toDate, cdrcgi.SESSION, session)

    #----------------------------------------------------------------------
    # Extract the job information from the database.
    #----------------------------------------------------------------------
    try:
        cursor.execute("""\
                SELECT pp.id, pp.pub_subset, pp.started,
		               pp.completed, count(pp.id) AS numDocs, pp.status
                  FROM pub_proc pp, pub_proc_doc ppd
                 WHERE pp.started >= '%s'
                   AND pp.completed <= DATEADD(s, -1, DATEADD(d, 1, '%s'))
                   AND pp.status in ('Success','Verifying')
                   AND pp.id = ppd.pub_proc
                   AND ppd.failure IS NULL
                   AND pp.pub_system IN (
                           SELECT d.id
                             FROM document d, doc_type t
                            WHERE d.doc_type = t.id
                              AND t.name = 'PublishingSystem'
                              AND d.title = 'Primary'
                                     )
              GROUP BY pp.id, pp.pub_subset, pp.started, pp.completed,
                       pp.status
              ORDER BY pp.id DESC
                       """ % (fromDate, toDate)
                      )

        row        = cursor.fetchone()
        if not row:
            cdrcgi.sendPage(header + """
              <span style="font: bold 18px arial;">
               No publishing jobs during this period.
              </span>
             </body>
            </html>
                                   """)

        form += """
            <span style="font: 15px arial">
             <B>Note:</b> A 
              <span style="background-color: #FF7F50;">Colored row</span> 
                did not complete loading to the Cancer.gov live site</span>
            <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
                <tr>
                    <th nowrap='1'>Job ID</th>
                    <th nowrap='1'>Job Name</th>
                    <th nowrap='1'>Job Status Reports</th>
                    <th nowrap='1'>Starting Time</th>
                    <th nowrap='1'>Ending Time</th>
                    <th nowrap='1'>NumDocs</th>
                </tr>
                """
        while row:
            id, name, started, completed, count, curStatus = row

            # Indicate that a job is still being loaded on Cancer.gov
            # by setting a different background color
            if curStatus == 'Verifying':
                form += '<tr style="background-color: #FF7F50;">'
            else:
                form += '<tr>'

            form += """
                    <td nowrap='1'>
                     <a style="text-decoration: underline; color: black;"
                        href="PubStatus.py?id=%d&type=Report&%s=%s">
                      <span class="link">%d</span></a>
                    </td>
                    <td nowrap='1'>
                     <a style="text-decoration: underline; color: black;"
                        href="PubStatus.py?id=%d&type=Report&%s=%s">
                      <span class="link">%s<span class="link"></a>
                    </td>
                    <td nowrap='1'>&nbsp;
                     <a style="text-decoration: underline; color: black;"
                        href="PubStatus.py?id=%d">
                      <span class="link">status</span></a>
                     <br />
                     &nbsp;
                     <a style="text-decoration: underline; color: black;"
                        href="PubStatus.py?id=%d&type=FilterFailure&flavor=error"
                        ><span class="link">errors</span></a>, 
                     &nbsp;
                     <a style="text-decoration: underline; color: black;"
                        href="PubStatus.py?id=%d&type=FilterFailure&flavor=warning"
                        ><span class="link">warnings</span></a>, 
                     &nbsp; 
                     <a style="text-decoration: underline; color: black;"
                        href="PubStatus.py?id=%d&type=FilterFailure&flavor=full"
                        ><span class="link">both</span></a>
                    </td>
                    <td nowrap='1'>
                     <span class="text">%s</span>
                    </td>
                    <td nowrap='1'>
                     <span class="text">%s</span>
                    </td>
                    <td nowrap='1'>
                     <span class="text">%d</span>
                    </td>
                </tr>
                    """ % (id, cdrcgi.SESSION, session, id,
                           id, cdrcgi.SESSION, session, name,
                           id, id, id, id,
                           started, completed, count)

            row = cursor.fetchone()

        form += "</table>"
    except cdrdb.Error, info:
        cdrcgi.bail('Failure executing query: %s' % info[1][0])

    cdrcgi.sendPage(header + form + "</BODY></HTML>")

#------------------------------------------------------------------
# Create some useful temporary tables holding information about
# the current and previous publishing jobs.  These tables speed
# things up, and also make the logic for what we're doing more
# transparent.
#------------------------------------------------------------------
def createTemporaryPubInfoTables(cursor, conn, latestFullLoad, cgJob):

    #------------------------------------------------------------------
    # What was the last Cancer.gov push job for each document?
    # This will be before the current job, but no earlier than
    # the most recent full load of Cancer.gov.
    #------------------------------------------------------------------
    try:
        cursor.execute("""\
            CREATE TABLE #prev_job_for_doc
                 (doc_id INTEGER,
                  job_id INTEGER)""")
        conn.commit()
        cursor.execute("""\
             INSERT INTO #prev_job_for_doc
                  SELECT d.doc_id, MAX(p.id) job_id
                    FROM pub_proc_doc d
                    JOIN primary_pub_job p
                      ON p.id = d.pub_proc
                   WHERE p.id BETWEEN %d AND %d
                     AND p.pub_subset LIKE 'Push_Documents_To_Cancer.Gov_%%'
                     AND d.failure IS NULL
                GROUP BY d.doc_id""" % (latestFullLoad, cgJob - 1))
        conn.commit()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting previous push job ids: %s" % info[1][0])

    #------------------------------------------------------------------
    # Now, for each of those documents, get the flag indicating
    # whether we were sending the document to Cancer.gov or pulling it.
    #------------------------------------------------------------------
    try:
        cursor.execute("""\
            CREATE TABLE #removed_flag
                 (doc_id INTEGER,
                 removed CHAR)""")
        conn.commit()
        cursor.execute("""\
             INSERT INTO #removed_flag
                  SELECT d.doc_id, d.removed
                    FROM pub_proc_doc d
                    JOIN #prev_job_for_doc p
                      ON p.job_id = d.pub_proc
                     AND d.doc_id = p.doc_id""")
        conn.commit()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure collecting removed flags for previous push jobs"
                    ": %s" % info[1][0])

    #------------------------------------------------------------------
    # Get the document IDs for the documents that were removed by
    # the current job.
    #------------------------------------------------------------------
    try:
        cursor.execute("CREATE TABLE #removed_docs (doc_id INTEGER)")
        conn.commit()
        cursor.execute("""\
            INSERT INTO #removed_docs
                 SELECT doc_id
                   FROM pub_proc_doc
                  WHERE pub_proc = ?
                    AND removed = 'Y'
                    AND failure IS NULL""", cgJob)
        conn.commit()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting IDs for removed docs: %s" % info[1][0])

    #------------------------------------------------------------------
    # Get the document IDs for the documents that were sent to
    # Cancer.gov by the current job (that is, the ones that we
    # didn't pick up by the previous query).
    #------------------------------------------------------------------
    try:
        cursor.execute("CREATE TABLE #sent_docs (doc_id INTEGER)")
        conn.commit()
        cursor.execute("""\
            INSERT INTO #sent_docs
                 SELECT doc_id
                   FROM pub_proc_doc
                  WHERE pub_proc = ?
                    AND removed = 'N'
                    AND failure IS NULL""", cgJob)
        conn.commit()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting IDs for docs sent to CG: %s" % info[1][0])

    #------------------------------------------------------------------
    # Get the IDs for the documents that were changed.  These are the
    # documents for which we have a previous job (#prev_job_for_doc)
    # and for which the 'removed' flag is off.
    #------------------------------------------------------------------
    try:
        cursor.execute("CREATE TABLE #changed_docs (doc_id INTEGER)")
        conn.commit()
        cursor.execute("""\
            INSERT INTO #changed_docs
                 SELECT d.doc_id
                   FROM pub_proc_doc d
                   JOIN #removed_flag f
                     ON f.doc_id = d.doc_id
                  WHERE d.pub_proc = ?
                    AND d.failure IS NULL
                    AND d.removed = 'N'
                    AND f.removed = 'N'""", cgJob)
        conn.commit()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting IDs for docs modified on CG: %s" %
                    info[1][0])

    #------------------------------------------------------------------
    # Now get the IDs for the documents which we sent to Cancer.gov
    # that they didn't have already (because they hadn't ever had
    # them or because the last transaction removed them).  In this
    # context "ever" means from the last full load, which sort of
    # starts history with a clean slate as far as their site goes.
    # This is just the sent docs minus the changed docs.
    #------------------------------------------------------------------
    try:
        cursor.execute("CREATE TABLE #new_docs (doc_id INTEGER)")
        conn.commit()
        cursor.execute("""\
            INSERT INTO #new_docs
                 SELECT doc_id
                   FROM #sent_docs
                  WHERE doc_id NOT IN (SELECT doc_id
                                         FROM #changed_docs)""")
        conn.commit()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting IDs for docs new to Cancer.gov: %s" %
                    info[1][0])

#----------------------------------------------------------------------
# Report what has been added, removed, and updated in this job.
#----------------------------------------------------------------------
def dispJobReport():

    title   = "CDR Administration"
    instr   = "Publishing Job Summary"
    buttons = ["Report Menu", cdrcgi.MAINMENU, "Log Out"]
    script  = "PubStatus.py"
    header  = cdrcgi.header(title, title, instr, script, buttons)

    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()


    #----------------------------------------------------------------------
    # Get subset name.
    #----------------------------------------------------------------------
    subSet = ""
    try:
        cursor.execute("""\
                SELECT pp.pub_subset
                  FROM pub_proc pp
                 WHERE id = %d
                   AND pp.status in ('Success', 'Verifying')
                   AND pp.pub_system IN (
                           SELECT d.id
                             FROM document d, doc_type t
                            WHERE d.doc_type = t.id
                              AND t.name = 'PublishingSystem'
                              AND d.title = 'Primary'
                                        )
                       """ % jobId
                      )
        row = cursor.fetchone()
        if row and row[0]:
            subSet = row[0]
        else:
            cdrcgi.bail("Job%d is not a successful publishing job." % jobId)

    except cdrdb.Error, info:
        cdrcgi.bail("Failure in query for Job%d: %s." % (jobId, info[1][0]))

    #----------------------------------------------------------------------
    # If subSet is for a Vendor job, find the CG job.
    # If subSet is for a CG job, find the vendor job.
    #----------------------------------------------------------------------
    pushJobName = "Push_Documents_To_Cancer.Gov_"
    cg_job = subSet.find(pushJobName) != -1 and jobId or 0
    vendor_job = cg_job == 0 and jobId or 0
    cg_job_name = ""
    vendor_job_name = ""

    if cg_job:
        cg_job_name = subSet
        vendor_job_name = subSet[len(pushJobName):]
        try:
            cursor.execute("""\
                SELECT id
                  FROM pub_proc
                 WHERE status = 'Success'
                   AND pub_subset = ?
                   AND id < ?
              ORDER BY id DESC
                           """,
                           (vendor_job_name, cg_job)
                          )
            row = cursor.fetchone()
            if row and row[0]:
                vendor_job = row[0]
            else:
                cdrcgi.bail("No Vendor job for CG Job%d." % jobId)

        except cdrdb.Error, info:
            cdrcgi.bail("No Vendor job for CG Job%d: %s" % (jobId, info[1][0]))
    else:
        cg_job_name = pushJobName + subSet
        vendor_job_name = subSet
        try:
            cursor.execute("""\
                SELECT id
                  FROM pub_proc
                 WHERE status = 'Success'
                   AND pub_subset = ?
                   AND id > ?
              ORDER BY id
                           """,
                           (cg_job_name, vendor_job)
                          )
            row = cursor.fetchone()
            if row and row[0]:
                cg_job = row[0]
            else:
                cdrcgi.bail("No CG job for Vendor Job%d." % jobId)

        except cdrdb.Error, info:
            cdrcgi.bail("No CG job for Vendor Job%d: %s." % (
                    jobId, info[1][0]))

    # Get the latest Full Load.
    try:
        cursor.execute("""\
            SELECT MAX(id)
              FROM pub_proc
             WHERE status = 'Success'
               AND pub_subset = ?
               AND id <= ?
                       """,
                       (pushJobName + 'Full-Load', cg_job)
                      )
        row = cursor.fetchone()
        if row and row[0]:
            latestFullLoad = row[0]
        else:
            cdrcgi.bail("No latest full load for job %s." % cg_job)
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting latest full load for job %s: %s." % (
            cg_job, info[1][0]))

    # See comments for this function.
    createTemporaryPubInfoTables(cursor, conn, latestFullLoad, cg_job)

    # How many documents are published in vendor job?
    try:
        cursor.execute("""\
            SELECT t.name, count(t.name)
              FROM pub_proc_doc ppd, document d, doc_type t
             WHERE ppd.failure IS NULL
               AND ppd.doc_id = d.id
               AND d.doc_type = t.id
               AND ppd.pub_proc = ?
          GROUP BY t.name""", vendor_job)
        rowsPublished = cursor.fetchall()
        numPublished = 0
        for row in rowsPublished:
            numPublished += row[1]

    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting vendor_count for %d: %s." % (
                    vendor_job, info[1][0]))

    #------------------------------------------------------------------
    # Get the counts (by doc type) of documents removed from Cancer.gov.
    #------------------------------------------------------------------
    try:
        cursor.execute("""
            SELECT t.name, count(t.name)
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
              JOIN #removed_docs r
                ON r.doc_id = d.id
          GROUP BY t.name""")
        rowsRemoved = cursor.fetchall()
        numRemoved = 0
        for row in rowsRemoved:
            numRemoved += row[1]

    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting removed doc counts for job %d: %s." % (
                    cg_job, info[1][0]))

    #------------------------------------------------------------------
    # Get the counts (by doc type) of documents updated on Cancer.gov.
    #------------------------------------------------------------------
    try:
        cursor.execute("""\
            SELECT t.name, count(t.name)
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
              JOIN #changed_docs c
                ON c.doc_id = d.id
          GROUP BY t.name""")
        rowsUpdated = cursor.fetchall()
        numUpdated = 0
        for row in rowsUpdated:
            numUpdated += row[1]
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting updated doc counts for job %d: %s." % (
            cg_job, info[1][0]))

    #------------------------------------------------------------------
    # Get the counts (by doc type) of all documents sent to Cancer.gov
    # that they didn't already have.
    #------------------------------------------------------------------
    try:
        cursor.execute("""\
            SELECT t.name, count(t.name)
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
              JOIN #new_docs n
                ON n.doc_id = d.id
          GROUP BY t.name""")
        rowsAdded = cursor.fetchall()
        numAdded = 0
        for row in rowsAdded:
            numAdded += row[1]
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting counts of new documents sent to CG "
                    "by job %d: %s" % (cg_job, info[1][0]))

    #------------------------------------------------------------------
    # Get the list of document types.
    # We need this so that we are able to display doc types even if
    # there is no entry/count in the document table. The output of this
    # query serves as the row label for the statistics Report output.
    # We do this by selecting all known doc types from the last Export
    # job and combine the result with all new doc types from the
    # current job (in case a new doc type gets introduces with a
    # hotfix).
    #------------------------------------------------------------------
    try:
        cursor.execute("""\
            SELECT DISTINCT t.name
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
              JOIN pub_proc_doc ppd
                ON ppd.doc_id = d.id
              JOIN pub_proc p
                ON p.id = ppd.pub_proc
             WHERE p.id = (SELECT MAX(id)
                             FROM pub_proc
                            WHERE pub_subset IN ('Full-Load', 'Export')
                          )
            UNION
            SELECT DISTINCT t.name
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
              JOIN #new_docs n
                ON n.doc_id = d.id
             ORDER BY 1
""")

        docTypes = []
        for row in cursor.fetchall():
            if row[0]:
               docTypes.append(row[0])
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting list of document types from pub_proc ")

    #------------------------------------------------------------------
    # Build the report HTML.
    #------------------------------------------------------------------
    form = """
       <center>
       <b>
        <font size='4'>Publishing Job Pair Summary</font>
       </b>
           """
    form += """
        <BR><BR>
        <TABLE ALIGN='center'>
           <TR>
             <TD ALIGN='right' NOWRAP><B>Vendor Job: &nbsp;</B></TD>
             <TD>%s (Job%d)</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Pushing Job: &nbsp;</B></TD>
             <TD>%s (Job%d)</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Published Documents: &nbsp;</B></TD>
             <TD>%d</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Added Documents: &nbsp;</B></TD>
             <TD>%d</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Updated Documents: &nbsp;</B></TD>
             <TD>%d</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Removed Documents: &nbsp;</B></TD>
             <TD>%d</TD>
            </TR>
        </TABLE>
              """ % (vendor_job_name, vendor_job, cg_job_name, cg_job,
                     numPublished, numAdded, numUpdated, numRemoved)

    form += """
        <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
        <BR>
        <TABLE WIDTH="50%%" ALIGN='center' BORDER='1'>
           <TR>
             <TD              ALIGN='center'><B>DocType</B></TD>
             <TD WIDTH="18%%" ALIGN='center'><B>Published</B></TD>
             <TD WIDTH="18%%" ALIGN='center'><B>Added</B></TD>
             <TD WIDTH="18%%" ALIGN='center'><B>Updated</B></TD>
             <TD WIDTH="18%%" ALIGN='center'><B>Removed</B></TD>
           </TR>
           """ % (cdrcgi.SESSION, session)
    ROW = """<TR>
             <TD ALIGN='left' NOWRAP>%s</TD>
             <TD ALIGN='right' NOWRAP>%d</TD>
             <TD ALIGN='right' NOWRAP>%s</TD>
             <TD ALIGN='right' NOWRAP>%s</TD>
             <TD ALIGN='right' NOWRAP>%s</TD>
           </TR>
          """
    LINK = "<A STYLE='text-decoration: underline;' "
    LINK += "HREF='PubStatus.py?id=%d&type=RepDetail&docType=%s"
    LINK += "&docCount=%d&cgMode=%s&%s=%s'>%d</A>"

    for type in docTypes:
        nPublished = 0
        nAdded = 0
        nUpdated = 0
        nRemoved = 0
        for row in rowsPublished:
            if row[0] == type:
                nPublished = row[1]
                break
        for row in rowsAdded:
            if row[0] == type:
                nAdded = row[1]
                break
        for row in rowsUpdated:
            if row[0] == type:
                nUpdated = row[1]
                break
        for row in rowsRemoved:
            if row[0] == type:
                nRemoved = row[1]
                break
        form += ROW % (
            type,
            nPublished,
            nAdded and LINK % (cg_job, type, nAdded, 'Added',
                               cdrcgi.SESSION, session, nAdded) or "0",
            nUpdated and LINK % (cg_job, type, nUpdated, 'Updated',
                                 cdrcgi.SESSION, session, nUpdated) or "0",
            nRemoved and LINK % (cg_job, type, nRemoved, 'Removed',
                                 cdrcgi.SESSION, session, nRemoved) or "0"
                      )

    form += "</TABLE>"

    cdrcgi.sendPage(header + form + "</BODY></HTML>")


#----------------------------------------------------------------------
# Report what has been added, removed, or updated in each doc type.
#----------------------------------------------------------------------
def dispJobRepDetail():

    title   = "CDR Administration"
    instr   = "Publishing Job Detail"
    buttons = ["Report Menu", cdrcgi.MAINMENU, "Log Out"]
    script  = "PubStatus.py"
    header  = cdrcgi.header(title, title, instr, script, buttons)

    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    pushJobName = "Push_Documents_To_Cancer.Gov_"

    # Get the latest Full Load.
    try:
        cursor.execute("""\
            SELECT MAX(id)
              FROM pub_proc
             WHERE status = 'Success'
               AND pub_subset = ?
               AND id <= ?
                       """,
                       (pushJobName + 'Full-Load', jobId)
                      )
        row = cursor.fetchone()
        if row and row[0]:
            latestFullLoad = row[0]
        else:
            cdrcgi.bail("No latest full load for job %s." % jobId)
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting latest full load for job %s: %s." % (
            jobId, info[1][0]))

    if cgMode in ('Updated', 'Added'):
        createTemporaryPubInfoTables(cursor, conn, latestFullLoad, jobId)

    # What documents are removed by cg job?
    if cgMode == 'Removed':
        try:
            cursor.execute("""
                SELECT TOP 500 ppd.doc_id, ppd.doc_version, d.title
                  FROM pub_proc_doc ppd, document d, doc_type t
                 WHERE ppd.failure IS NULL
                   AND ppd.doc_id = d.id
                   AND ppd.removed = 'Y'
                   AND d.doc_type = t.id
                   AND t.name = ?
                   AND ppd.pub_proc = ?
              ORDER BY d.title
                           """, (docType, jobId)
                          )
            rows = cursor.fetchall()

        except cdrdb.Error, info:
            cdrcgi.bail("Failure getting removed for %d: %s." % (
                        jobId, info[1][0]))

    # What documents are updated by cg job?
    elif cgMode == 'Updated':
        try:
            cursor.execute("""\
                SELECT TOP 500 p.doc_id, p.doc_version, d.title
                  FROM pub_proc_doc p
                  JOIN #changed_docs c
                    ON c.doc_id = p.doc_id
                  JOIN document d
                    ON d.id = p.doc_id
                  JOIN doc_type t
                    ON t.id = d.doc_type
                 WHERE t.name = ?
                   AND p.pub_proc = ?
              ORDER BY d.title""", (docType, jobId))
            rows = cursor.fetchall()

        except cdrdb.Error, info:
            cdrcgi.bail("Failure getting updated for job %d: %s." % (
                jobId, info[1][0]))

    # What documents are newly added by cg job?
    elif cgMode == 'Added':
        try:
            cursor.execute("""\
                SELECT TOP 500 p.doc_id, p.doc_version, d.title
                  FROM pub_proc_doc p
                  JOIN #new_docs n
                    ON n.doc_id = p.doc_id
                  JOIN document d
                    ON d.id = p.doc_id
                  JOIN doc_type t
                    ON t.id = d.doc_type
                 WHERE t.name = ?
                   AND p.pub_proc = ?
              ORDER BY d.title""", (docType, jobId))
            rows = cursor.fetchall()

        except cdrdb.Error, info:
            cdrcgi.bail("Failure getting added for job %d: %s." % (
                jobId, info[1][0]))

    form = """
       <center>
       <b>
        <font size='4'>Documents Pushed to Cancer.gov</font>
        <br><br>
        <font size='3'>Job ID: %d</font>
        <br>
        <font size='3'>%s</font>
       </b>
       </center>
           """ % (jobId, docType)

    form += """
        <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
        <BR>
        <TABLE ALIGN='center'><TR><TD>
        <b><font size='3'>%s %d documents %s</font></b>
        </TD></TR>
        <TR><TD>
        <TABLE ALIGN='center' BORDER='1'>
           <TR>
             <TD ALIGN='center' NOWRAP><B>DocId</B></TD>
             <TD ALIGN='center' NOWRAP><B>DocVersion</B></TD>
             <TD ALIGN='left' NOWRAP><B>DocTitle</B></TD>
           </TR>
           """ % (cdrcgi.SESSION, session, cgMode, docCount,
                  (docCount > 500 ) and "(Top 500 listed only)" or "")
    ROW = """<TR>
             <TD ALIGN='right' NOWRAP>%d</TD>
             <TD ALIGN='right' NOWRAP>%d</TD>
             <TD ALIGN='left'>%s</TD>
           </TR>
          """

    for row in rows:
        form += ROW % (row[0], row[1], row[2])

    form += "</TABLE></TD></TR></TABLE>"

    cdrcgi.sendPage(header + form + "</BODY></HTML>")

#----------------------------------------------------------------------
# Handle requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out":
    cdrcgi.logout(session)

if session and not dispType:
    if not fromDate or not toDate:
        selectPubDates()
    else:
        dispJobsByDates()
elif not jobId:
    cdrcgi.bail("Job ID not supplied")

jobId = int(jobId)
if not dispType:
    dispJobStatus()
elif dispType == "FilterFailure":
    dispFilterFailures(flavor)
elif dispType == "Setting":
    dispJobSetting()
elif dispType == "CgWork":
    dispCgWork()
elif dispType == "Manage":
    if not session:
        cdrcgi.bail("A session ID must be provided for this page.")
    dispJobControl()
elif dispType == "Report":
    dispJobReport()
elif dispType == "RepDetail":
    dispJobRepDetail()
else:
    cdrcgi.bail("Display type: %s not supported." % dispType)
