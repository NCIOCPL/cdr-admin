#----------------------------------------------------------------------
#
# $Id: RssImportReport.py,v 1.5 2005-08-29 17:02:50 bkline Exp $
#
# Reports on import/update of RSS protocol site information.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2005/06/23 15:16:32  bkline
# Modifications requested in issue #1730 (tables split).
#
# Revision 1.3  2005/06/09 18:42:41  bkline
# Fixed test for new imports.
#
# Revision 1.2  2005/06/01 12:46:14  bkline
# Fixed bug in reporting whether a publishable version was created.
#
# Revision 1.1  2005/05/11 20:57:24  bkline
# Report created for Sheri (request #1669).
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
jobId    = fields and fields.getvalue('id') or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "RssImportReport.py"
title   = "CDR Administration"
section = "RSS Import Report"
header  = cdrcgi.header(title, title, section, script, buttons)
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()

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

#----------------------------------------------------------------------
# Create a table for a subset of the trials.
#----------------------------------------------------------------------
def addTable(docs, header, rssModeCol = True):
    html = u"""\
  <span class='sub'>%s - %d</span>
  <br>
""" % (header, len(docs))
    if docs:
        keys = docs.keys()
        keys.sort()
        html += u"""\
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>CDR DocId</th>
    <th>DocTitle</th>
    <th>Pub Ver?</th>
"""
        if rssModeCol:
            html += u"""\
    <th>RSS Mode?</th>
"""
        html += u"""\
   </tr>
"""
        for key in keys:
            html += docs[key].toHtml(rssModeCol)
        html += u"""\
  </table>
"""
    return html + u"""\
  <br />
"""

#----------------------------------------------------------------------
# Document for a trial.
#----------------------------------------------------------------------
class Doc:
    def __init__(self, cdrId, locked, pubVer, new):
        self.cdrId      = cdrId
        self.locked     = locked
        self.pubVer     = pubVer
        self.new        = new
        self.title      = None
        self.rssMode    = False
        self.needDate   = False
        if cdrId:
            cursor.execute("SELECT title FROM document WHERE id = ?", cdrId)
            self.title = cursor.fetchall()[0][0]
            cursor.execute("""\
                SELECT COUNT(*)
                  FROM query_term
                 WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                            + '/ProtocolLeadOrg/UpdateMode'
                   AND value = 'RSS'
                   AND doc_id = ?""", cdrId)
            self.rssMode = cursor.fetchall()[0][0] > 0
            cursor.execute("""\
               SELECT COUNT(*)
                 FROM query_term
                WHERE path = '/InScopeProtocol/DateLastModified'
                  AND doc_id = ?""", cdrId)
            if cursor.fetchall()[0][0] == 0:
                cursor.execute("""\
                    SELECT COUNT(*)
                      FROM pub_proc_cg
                     WHERE id = ?""", cdrId)
                if cursor.fetchall()[0][0] > 0:
                    self.needDate = True
    def toHtml(self, rssModeCol = True):
        html = u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
""" % (self.cdrId, self.title.replace(";", "; "), self.pubVer or "N")
        if rssModeCol:
            html += u"""\
    <td>%s</td>
""" % (self.rssMode and "Y" or "N")
        html += u"""\
   </tr>
"""
        return html
    
#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not jobId:
    cursor.execute("""\
        SELECT j.id, j.dt
          FROM import_job j
          JOIN import_source s
            ON s.id = j.source
         WHERE s.name = 'RSS'
           AND j.status = 'Success'
      ORDER BY j.dt DESC""")
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Job:&nbsp;</B></TD>
     <TD>
      <SELECT NAME='id'>
       <OPTION VALUE=''>Select Job</OPTION>
""" % (cdrcgi.SESSION, session)
    for jobId, jobDate in cursor.fetchall():
        form += """\
       <OPTION VALUE='%d'>%s &nbsp;</OPTION>
""" % (jobId, jobDate)
    form += """\
      </SELECT>
     </TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
cursor.execute("SELECT dt FROM import_job WHERE id = ?", jobId)
rows = cursor.fetchall()
if not rows:
    cdrcgi.bail("Invalid job ID %s" % jobId)
jobDate = rows[0][0]
cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/InScopeProtocol/ProtocolDetail/StudyType'
                AND value = 'Research study'""")
researchStudyIds = {}
for row in cursor.fetchall():
    researchStudyIds[row[0]] = True
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Import run on %s</title>
  <style type 'text/css'>
   body     { font-family: Arial, Helvetica, sans-serif }
   span.ti  { font-size: 14pt; font-weight: bold }
   span.sub { font-size: 12pt; font-weight: bold }
   th       { text-align: center; vertical-align: top; 
              font-size: 12pt; font-weight: bold }
   td       { text-align: left; vertical-align: top; 
              font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <span class='ti'>RSS Import/Update Statistics Report</span>
   <br />
   <span class='sub'>Import run on %s</span>
  </center>
  <br />
  <br />
""" % (jobDate, jobDate)
cursor.execute("""\
    SELECT d.cdr_id, e.locked, e.pub_version, e.new
      FROM import_doc d
      JOIN import_event e
        ON e.doc = d.id
     WHERE e.job = ?""", jobId)
rows = cursor.fetchall()
lockedDocs = {}
newDocsPub = {}
newDocsNonPub = {}
updatedDocsPub = {}
updatedDocsNonPub = {}
researchStudies = {}
noDateLastModified = {}
for cdrId, locked, pubVer, new in rows:
    if cdrId:
        doc = Doc(cdrId, locked, pubVer, new)
        if doc.locked == 'Y':
            lockedDocs[cdrId] = doc
        elif cdrId in researchStudyIds:
            researchStudies[cdrId] = doc
        elif doc.new == 'Y':
            if doc.pubVer == 'Y':
                newDocsPub[cdrId] = doc
            else:
                newDocsNonPub[cdrId] = doc
        else:
            if doc.pubVer == 'Y':
                updatedDocsPub[cdrId] = doc
            else:
                updatedDocsNonPub[cdrId] = doc
        if doc.needDate:
            noDateLastModified[cdrId] = doc
html += addTable(newDocsNonPub,
                 'Trials with initial external sites imported with '
                 'Non-Publishable Versions')
html += addTable(newDocsPub,
                 'Trials with initial external sites imported with '
                 'Publishable Versions')
html += addTable(updatedDocsNonPub,
                 'Updated trials with Non-Publishable Versions')
html += addTable(updatedDocsPub,
                 'Updated trials with Publishable Versions')
html += addTable(researchStudies, 'Research Studies')
html += addTable(lockedDocs,
                 'Trials not updated because document was checked out')
html += addTable(noDateLastModified,
                 'Updated trials without DateLastModified', False)
cdrcgi.sendPage(html + """\
 </body>
</html>""")
