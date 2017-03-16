#----------------------------------------------------------------------
# User interface for requesting republication of documents to be
# sent to Cancer.gov.
# BZIssue::4855 - Add GKTarget Parameter to Re-publishing Job Interface
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, RepublishDocs

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
docList = fields.getvalue('DocList')    or ''
jobList = fields.getvalue('JobList')    or ''
docType = fields.getvalue('DocType')    or None
allType = fields.getvalue('AllType')    and True or False
newDocs = fields.getvalue('NewDocs')    and True or False
gkHost  = fields.getvalue('GKHost')     or ''
gkPubTarget= fields.getvalue('GKTarget')   or ''
if not gkPubTarget.lower() in ('', 'gatekeeper', 'preview', 'live'):
    cdrcgi.bail(u'Invalid value for GKTarget: %s. Allowed values are:'
                u'GateKeeper, Preview, Live' % gkPubTarget)
email   = fields.getvalue('Email')      or ''
failed  = fields.getvalue('FailedOnly') and True or False
SUBMENU = "Developer Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "Republish.py"
title   = "CDR Administration"
section = "Republish"
extra   = ""
header  = cdrcgi.header(title, title, section, script, buttons, stylesheet =
"""\
  <style type='text/css'>
   body    { font-size: 10pt; font-family: Arial; }
   body    { background: #fdfdfd; }
   h1      { font-size: 14pt; color: maroon; text-align: center; }
   .field  { width: 500px; }
   .extra  { color: green; font-size: 11pt; }
   .error  { color: red; font-size: 12pt; }
   th, td  { font-size: 10pt; }
   p       { border: 1px solid blue; padding: 5px; font-size: 10pt; }
   b, th   { color: green }
   h1, p   { width: 650px }
   p.error { border: 1px solid red; }
  </style>
""", numBreaks = 1)

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
    cdrcgi.navigateTo("DevSA.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Create a picklist for document types published to Cancer.gov.
#----------------------------------------------------------------------
def makeDoctypePicklist():
    cursor = cdrdb.connect('CdrGuest').cursor()
    cursor.execute("""\
        SELECT DISTINCT t.name
          FROM doc_type t
          JOIN document d
            ON d.doc_type = t.id
          JOIN pub_proc_cg c
            ON c.id = d.id
      ORDER BY t.name""", timeout = 300)
    html = ["""\
      <select name='DocType' class='field'>
       <option value='' selected>&nbsp;</option>
"""]
    for row in cursor.fetchall():
        # Skip types we no longer push to Cancer.gov
        docType = row[0]
        if docType not in ('Country', 'Person'):
            html.append("""\
       <option value='%s'>%s</option>
""" % (row[0], row[0]))
    html.append("""\
      </select>""")
    return "".join(html)

#----------------------------------------------------------------------
# Put up the request form.
#----------------------------------------------------------------------
def showForm(extra):
    form = """\
   <h1>Re-publish CDR Documents to Cancer.gov</h1>
   <br>
   <p>
    This page can be used to request re-publishing of CDR documents
    which have already been sent to Cancer.gov, in a way which
    bypasses the optimization which normally prevents sending of
    an unchanged document to the Cancer.gov GateKeeper program.
    <br><br>
    You may enter one or more CDR <b>Document IDs</b>, and/or one or
    more publishing <b>Job IDs</b>.  Separate multiple ID values with
    spaces.  You may also select a <b>Document Type</b>.
    If you select a document type you may indicate that all
    publishable documents of that type are to be included;
    otherwise, only those documents which are already in the
    pub_proc_cg table will be published.  If a document type
    is not selected this flag is ignored.  You may also indicate
    that in addition to those documents selected for the document
    IDs, job IDs, and document type provided, the new publishing
    document should also identify and include documents which are
    the target of links from the base set of documents to be published,
    and are not already on Cancer.gov.  Finally, when you specify
    one or more job IDs you can indicate that only documents from
    those jobs marked as '<i>Failed</i>' are to be included.
    If no job IDs are entered, this flag is ignored.
    <br><br>
    An export job will be created for generating the
    output suitable for publishing.  This job, if successful,
    will in turn create a second job for pushing the
    exported jobs to the GateKeeper at Cancer.gov.
    <br><br>
    You may optionally add an <b>Email Address</b> to which
    status notifications for the progress of the new publishing
    jobs will be sent, with links to pages with additional
    information about the status for the jobs.
    <br><br>
    Specify the fully qualified domain name or IP address for
    the GateKeeper host to which the republishing job is to be
    directed if it is not the default host for the CDR server
    from which the request originates.
   </p>
   <br>
   <input type='hidden' name='%s' value='%s'>%s
   <table border='0'>
    <tr>
     <th align='right'>Document IDs:&nbsp;</th>
     <td><input name='DocList' class='field'></td>
    </tr>
    <tr>
     <th align='right'>Job IDs:&nbsp;</th>
     <td><input name='JobList' class='field'></td>
    </tr>
    <tr>
     <th align='right'>Document Type:&nbsp;</th>
     <td>
%s
     </td>
    </tr>
    <tr>
     <th align='right'>Email Address:&nbsp;</th>
     <td><input name='Email' class='field'
                value='NCIPDQoperator@mail.nih.gov'></td>
    </tr>
    <tr>
     <th align='right'>GateKeeper Host:&nbsp;</th>
     <td><input name='GKHost' class='field'></td>
    </tr>
    <tr>
     <th align='right'>GateKeeper Target:&nbsp;</th>
     <td><input name='GKTarget' class='field' value='Preview'></td>
    </tr>
    <tr>
     <td>&nbsp;</td>
     <td>
      <br>
      <input type='checkbox' name='AllType' >
      Include all documents for type
     </td>
    </tr>
    <tr>
     <td>&nbsp;</td>
     <td>
      <input type='checkbox' name='NewDocs'>
      Include linked documents not on Cancer.gov
     </td>
    </tr>
    <tr>
     <td>&nbsp;</td>
     <td>
      <input type='checkbox' name='FailedOnly' checked>
      Only include failed documents from specified publishing jobs
     </td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, extra, makeDoctypePicklist())
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# If we have a request, take care of it.
#----------------------------------------------------------------------
if (docList or jobList or docType):
    try:
        cr      = RepublishDocs.CdrRepublisher(session)
        docList = [cdr.exNormalize(d)[1] for d in docList.split()]
        jobList = [int(job) for job in jobList.split()]
        jobId   = cr.republish(newDocs, docList, jobList, docType, allType,
                               failed, email, gkHost, gkPubTarget)
        extra = """
   <p>Export job %d created successfully</p><br>""" % jobId
    except Exception, e:
        extra = """
   <p class='error'>Failure: %s</p><br>""" % e

showForm(extra)
