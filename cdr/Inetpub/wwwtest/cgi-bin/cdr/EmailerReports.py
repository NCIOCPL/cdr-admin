#----------------------------------------------------------------------
#
# $Id: EmailerReports.py,v 1.4 2005-03-03 14:27:21 bkline Exp $
#
# Reports on status of electronic mailers.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2004/12/27 20:32:56  bkline
# Added missing import for sys module.
#
# Revision 1.2  2004/09/09 15:23:46  bkline
# Fixed typo; added date-range defaults (request #1328).
#
# Revision 1.1  2004/07/13 18:02:48  bkline
# Administrative support for electronic mailers.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, time, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
start    = fields and fields.getvalue('start')   or None
end      = fields and fields.getvalue('end')     or None
jobId    = fields and fields.getvalue('jobId')   or None
repType  = fields and fields.getvalue('repType') or None
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "EmailerReports.py"
title    = "CDR Administration"
section  = "Web Mailer Updates"
header   = cdrcgi.header(title, title, section, script, buttons,
                         stylesheet ="""\
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
  </style>
  <script language='JavaScript'>
   
  </script>
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

if request == "Submit Request":
    if not repType:
        cdrcgi.bail('Report type not selected')
    if cdr.isProdHost():
        host = 'pdqupdate.cancer.gov'
    else:
        host = 'verdi.nci.nih.gov'
    base = ('http://%s/PDQUpdate/cgi-bin/EmailerReports.py?repType=%s' %
            (host, repType))
    if start and end:
        url = '%s&start=%s&end=%s' % (base, start, end)
    elif jobId:
        url = '%s&jobId=%s' % (base, jobId)
    else:
        cdrcgi.bail('Neither job ID nor date range specified')
    print "Location:%s\n" % url
    sys.exit(0)

#----------------------------------------------------------------------
# Build the list of jobs.
#----------------------------------------------------------------------
def makeJobList():
    import cdrmailcommon
    conn = cdrmailcommon.emailerConn('dropbox')
    cursor = conn.cursor()
    cursor.execute("""\
        SELECT id, uploaded
          FROM emailer_job
      ORDER BY id""")
    rows = cursor.fetchall()
    html = """\
<select name='jobId'>
"""
    for row in rows:
        html += """\
 <option value='%s'>%s - Protocol Status and Participant - %s</option>
""" % (row[0], row[0], str(row[1])[:10])
    return html + """\
</select>"""

#----------------------------------------------------------------------
# Put up the request form.
#----------------------------------------------------------------------
now = time.localtime()
then = list(now)
then[2] -= 1
then = time.localtime(time.mktime(then))
form = """\
   <input type='hidden' name='%s' value='%s'>
   <b>1. Enter a date range to view returns to web-based mailers:</b><br><br>
   <table border='0'>
    <tr>
     <td align='right' nowrap><b>Start Date:&nbsp;</b></td>
     <td><input size='10' name='start' value='%s'>&nbsp;</td>
     <td rowspan='2'>(use format YYYY-MM-DD for dates, e.g. 2004-01-01)</td>
    </tr>
    <tr>
     <td align='right' nowrap><b>End Date:&nbsp;</b></td>
     <td><input size='10' name='end' value='%s'></td>
    </tr>
   </table>
   <br>
   <b>or select:</b>
   <br><br>
   <b>Mailer Job ID:&nbsp;</b>%s

   <br><br>
   <b>2. Select report you want to view:</b><br><br>
   <input type='radio' name='repType' value='changed'>
   Updates with changes<br>
   <input type='radio' name='repType' value='unchanged'>
   Updates without changes<br>
   <input type='radio' name='repType' value='rts'>
   Returned to sender
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session,
       time.strftime("%Y-%m-%d", then),
       time.strftime("%Y-%m-%d", now),
       makeJobList())
cdrcgi.sendPage(header + form)
