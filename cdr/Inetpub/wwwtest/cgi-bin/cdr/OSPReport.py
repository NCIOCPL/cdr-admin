#----------------------------------------------------------------------
#
# $Id: OSPReport.py,v 1.1 2003-05-08 20:24:01 bkline Exp $
#
# Queue up report for the Office of Science Policy.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import cdrbatch, cdrcgi, cgi, cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
email       = fields and fields.getvalue("Email")    or None
cancer      = fields and fields.getvalue("Cancer")   or None
title       = "CDR Administration"
section     = "Report for Office of Science Policy"
SUBMENU     = "Report Menu"
buttons     = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'OSPReport.py'
command     = 'lib/Python/CdrLongReports.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body { font-family: Arial }
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
    cdrcgi.navigateTo("Mailers.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

def listTermChoices():
    path = "/Term/MenuInformation/MenuItem/MenuParent/@cdr:ref"
    try:
        conn = cdrdb.connect('CdrGuest', dataSource='bach.nci.nih.gov')
        cursor = conn.cursor()
        cursor.execute("""\
   SELECT DISTINCT c.doc_id,
                   n.value
              FROM query_term c
              JOIN query_term n
                ON c.doc_id = n.doc_id
              JOIN query_term p
                ON p.doc_id = c.int_val
             WHERE p.value = 'Disease/diagnosis'
               AND p.path = '/Term/PreferredName'
               AND n.path = '/Term/PreferredName'
               AND c.path = '/Term/MenuInformation/MenuItem' +
                            '/MenuParent/@cdr:ref'
          ORDER BY n.value""")
        rows = cursor.fetchall()
    except Exception, e:
        cdrcgi.bail("Database failure extracting cancer term choices: %s"
                    % str(e))
    html = """\
      <select multiple='1' size='10' name='Cancer'>
"""
    for row in rows:
        html += """\
       <option value='%d'>%s</option>
""" % (row[0], cdrcgi.unicodeToLatin1(cgi.escape(row[1])))
    return html + """\
      </select>"""

#----------------------------------------------------------------------
# Put up the form if we don't have a request yet.
#----------------------------------------------------------------------
if not email or not cancer or request != "Submit":
    form = """\
   <p>
    Please select at least one cancer type for the report.
    This report requires a few minutes to complete.
    When the report processing has completed, email notification
    will be sent to the addresses specified below.  At least
    one email address must be provided.  If more than one
    address is specified, separate the addresses with a blank.
   </p>
   <br>
   <table border='0'>
    <tr>
     <td>
      <b>Email address(es):&nbsp;</b>
     </td>
     <td>
      <input name='Email' size='80'><br>
     </td>
    </tr>
    <tr>
     <td align='right'>
      <b>Cancer type(s):&nbsp;</b>
     <td>
%s
     </td>
    </tr>
   </table>
   <input type='hidden' name='%s' value='%s'>
  </form>
 </body>
</html>
""" % (listTermChoices(), cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------    
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
if type(cancer) not in (type([]), type(())):
    cancer = [cancer]
args = []
for c in cancer:
    name = "TermId%d" % (len(args) + 1)
    args.append((name, c))
# Have to do this on Mahler, since that's the only server with Excel installed.
batch = cdrbatch.CdrBatch(jobName = section, command = command, email = email,
                          args = args, host='mahler.nci.nih.gov')
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Could not start job: " + str(e))
jobId       = batch.getJobId()
buttons     = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'osp.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 """)
cdrcgi.sendPage(header + """\
   <h4>Report has been queued for background processing</h4>
   <p>
    To monitor the status of the job, click this
    <a href='getBatchStatus.py?%s=%s&jobId=%s'><u>link</u></a>
    or use the CDR Administration menu to select 'View
    Batch Job Status'.
   </p>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, jobId))
