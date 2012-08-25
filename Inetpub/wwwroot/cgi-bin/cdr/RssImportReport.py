#----------------------------------------------------------------------
#
# $Id$
#
# Reports on import/update of RSS protocol site information.
#
# BZIssue::1669
# BZIssue::1730
# BZIssue::1830
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Look up source if missing.
#----------------------------------------------------------------------
def lookupSource(jobId, cursor):
    if not jobId:
        return 'RSS'
    cursor.execute("""\
        SELECT s.name
          FROM import_source s
          JOIN import_job j
            ON j.source = s.id
         WHERE j.id = %s""" % jobId)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Unable to find source for import job %s" % jobId)
    return rows[0][0]

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
jobId   = fields and fields.getvalue('id') or None
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()
source  = fields and fields.getvalue('source') or lookupSource(jobId, cursor)
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "RssImportReport.py"
title   = "CDR Administration"
section = "%s Import Report" % source
header  = cdrcgi.header(title, title, section, script, buttons)

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
def addTable(docs, header, sourceUpdateModeCol = True):
    html = u"""\
  <span class='sub'>%s - %d</span>
  <br>
""" % (header, len(docs))
    if docs:
        keys = docs.keys()
        keys.sort()
        if source in ('Oncore', 'NCIC'):
            html += u"""\
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>CDR DocId</th>
    <th>Primary ID</th>
    <th>Other IDs</th>
    <th>Pub Ver?</th>
"""
        else:
            html += u"""\
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>CDR DocId</th>
    <th>DocTitle</th>
    <th>Pub Ver?</th>
"""
        if sourceUpdateModeCol:
            html += u"""\
    <th>%s Mode?</th>
""" % source
        html += u"""\
    <th>Protocol Status</th>
   </tr>
"""
        for key in keys:
            html += docs[key].toHtml(sourceUpdateModeCol)
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
        self.cdrId            = cdrId
        self.locked           = locked
        self.pubVer           = pubVer
        self.new              = new
        self.title            = None
        self.sourceUpdateMode = False
        self.needDate         = False
        self.status           = None
        self.primaryId        = None
        self.otherIds         = ()
        if cdrId:
            cursor.execute("SELECT title FROM document WHERE id = ?", cdrId)
            self.title = cursor.fetchall()[0][0]
            cursor.execute("""\
                SELECT COUNT(*)
                  FROM query_term
                 WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                            + '/ProtocolLeadOrg/UpdateMode'
                   AND value = '%s'
                   AND doc_id = ?""" % source, cdrId)
            self.sourceUpdateMode = cursor.fetchall()[0][0] > 0
            cursor.execute("""\
                SELECT value
                  FROM query_term
                 WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                            + '/CurrentProtocolStatus'
                   AND doc_id = ?""", cdrId)
            rows = cursor.fetchall()
            if rows:
                self.status = rows[0][0]
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
            if source in ('Oncore', 'NCIC'):
                cursor.execute("""\
                    SELECT value
                      FROM query_term
                     WHERE path = '/InScopeProtocol/ProtocolIDs'
                                + '/PrimaryID/IDString'
                       AND doc_id = ?""", cdrId)
                rows = cursor.fetchall()
                if rows:
                    self.primaryId = rows[0][0]
                cursor.execute("""\
                    SELECT t.value, i.value
                      FROM query_term t
                      JOIN query_term i
                        ON t.doc_id = i.doc_id
                       AND LEFT(t.node_loc, 8) = LEFT(i.node_loc, 8)
                     WHERE t.path = '/InScopeProtocol/ProtocolIDs'
                                  + '/OtherID/IDType'
                       AND i.path = '/InScopeProtocol/ProtocolIDs'
                                  + '/OtherID/IDString'
                       AND t.doc_id = ?""", cdrId)
                self.otherIds = cursor.fetchall()

    def toHtml(self, sourceUpdateModeCol = True):
        if source in ('Oncore', 'NCIC'):
            primaryId = (self.primaryId and cgi.escape(self.primaryId)
                         or u"&nbsp;")
            otherIds = (self.otherIds and
                        u"; ".join([u"<b>%s</b> - %s" % (cgi.escape(o[0]),
                                                         cgi.escape(o[1]))
                                    for o in self.otherIds])
                        or u"&nbsp;")
            html = u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
""" % (self.cdrId, primaryId, otherIds, self.pubVer or "N")
        else:
            html = u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
""" % (self.cdrId, self.title.replace(";", "; "), self.pubVer or "N")
        if sourceUpdateModeCol:
            html += u"""\
    <td>%s</td>
""" % (self.sourceUpdateMode and "Y" or "N")
        html += u"""\
    <td>%s</td>
   </tr>
""" % (self.status or u"&nbsp;")
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
         WHERE s.name = '%s'
           AND j.status = 'Success'
      ORDER BY j.dt DESC""" % source)
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
   <span class='ti'>%s Import/Update Statistics Report</span>
   <br />
   <span class='sub'>Import run on %s</span>
  </center>
  <br />
  <br />
""" % (jobDate, source, jobDate)
cursor.execute("""\
    SELECT d.cdr_id, e.locked, e.pub_version, e.new
      FROM import_doc d
      JOIN import_source s
        ON s.id = d.source
      JOIN import_event e
        ON e.doc = d.id
     WHERE e.job = ?
       AND s.name = ?""", (jobId, source))
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
