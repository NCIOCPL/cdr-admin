#----------------------------------------------------------------------
#
# $Id: DirectoryMailerReqForm.py,v 1.1 2002-03-19 23:39:06 ameyer Exp $
#
# Request form for all directory mailers.
#
# This program is invoked twice to  create a mailer job.
#
# The first invocation is made by a high level mailer menu from which
# a user selected directory mailers.  In the first invocation, the program
# detects that no specific mailer has been requested ("if not request")
# and returns an input form to the web browser to gather information
# needed to start a specific mailer job.
#
# When a user responds to the form, we get the input here in a second
# invocation.  We then validate the input and setup the requested mailer
# publication job for the publishing daemon to find and initiate.
#
# Based on an original request form for new physician initial mailers by
# Bob Kline.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, cdrpub

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
docId   = fields and fields.getvalue("DocId")    or None
email   = fields and fields.getvalue("Email")    or None
dirType = fields and fields.getvalue("dirType")  or None
mailType= fields and fields.getvalue("mailType") or None
title   = "CDR Administration"
section = "Directory Mailer Request Form"
buttons = ["Submit", "Log Out"]
script  = 'DirectoryMailerReqForm.py'
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Put up the form if we don't have a request yet.
#----------------------------------------------------------------------
if not request:
    form = """\
   <h2>Enter request parameters</h2>
   <h5>Document ID and email notification address are both optional.
       If document ID is specified, only a mailer for that document
       will be generated; otherwise all eligible documents for which
       mailers have not yet been sent will have mailers generated.</h5>
   <table>
    <tr>
     <th align='right' nowrap>
      <b>Directory document CDR ID: &nbsp;</b>
     </TD>
     <td><input name='DocId' /></td>
    </tr>
    <tr>
     <th align='right' nowrap>
      <b>Notification email address: &nbsp;</b>
     </TD>
     <td><input name='Email' /></td>
    </tr>
    <tr><td>&nbsp;</td></tr>
   </table>
   <p><p><h5>
   Select the type of directory and type of mailer for which mailers
   are to be generated.  Both are required.</h5>
   <table>
    <tr>
     <th align='right'><B>Directory type: &nbsp;</B></th>
     <td>
       <label><input type='radio' name='dirType'
          value='Physician'>Physician</label>
     </td><td>
       <label><input type='radio' name='dirType'
          value='Organization'>Organization</label>
     </td>
    </tr>
    <tr><td>&nbsp;</td></tr>
    <th align='right'><b>Mailer type: &nbsp;</B></th>
     <td>
       <label><input type='radio' name='mailType'
          value='Initial'>Initial</label>
     </td><td>
       <label><input type='radio' name='mailType'
          value='Update'>Update</label>
     </td><td>
       <label><input type='radio' name='mailType'
          value='Remail'>Remailer</label>
     </td>
    </tr>
   </table>
   <input type='hidden' name='%s' value='%s' />
  </form>
""" % (cdrcgi.SESSION, session)
    #------------------------------------------------------------------
    # cdrcgi.sendPage exits after sending page.
    # If we sent a page, we're done for this invocation.
    # We'll be back if the user fills in the form and submits it.
    #------------------------------------------------------------------
    cdrcgi.sendPage(header + form + "</BODY></HTML>")



#----------------------------------------------------------------------
# Validate that all required info is received
# We only get here on the second invocation - user filled in form
#----------------------------------------------------------------------
if (dirType == None or mailType == None):
    cdrcgi.bail ('Directory type and Mailer type must be selected')

#----------------------------------------------------------------------
# Set variables based on the form
#----------------------------------------------------------------------
docType = dirType
if doctype == 'Physician':
    # Organization directory name and doc_type are the same, but
    #   Physician and Person are different
    docType = 'Person'
subset  = dirType + ' ' + mailType + ' Mailers'

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrPublishing')
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Find the publishing system control document.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute("""\
        SELECT d.id
          FROM document d
          JOIN doc_type t
            ON t.id    = d.doc_type
         WHERE t.name  = 'PublishingSystem'
           AND d.title = 'Mailers'
""")
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database failure looking up control document: %s' %
                info[1][0])
if len(rows) < 1:
    cdrcgi.bail('Unable to find control document for Mailers')
if len(rows) > 1:
    cdrcgi.bail('Multiple Mailer control documents found')
ctrlDocId = rows[0][0]

#----------------------------------------------------------------------
# Determine which documents are to be published.
#----------------------------------------------------------------------
if docId:
    # Simple case - user submitted single document id
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)
    try:
        cursor.execute("""\
            SELECT MAX(num)
              FROM doc_version
             WHERE id = ?""", (intId,))
        row = cursor.fetchone()
        docList = ((intId, row[0]),)
    except cdrdb.Error, info:
        cdrcgi.bail("No version found for document %d: %s" % (intId,
                                                              info[1][0]))

    # Validate that the document is the right type
    # We'll allow user to print a 'wrong' mailer type, he's probably doing
    #   a single document either as a test or as a result of a printer error
    try:
        cursor.execute ("""\
            SELECT name
              FROM docType t, document d
             WHERE t.id = d.doc_type
               AND d.id = %d""" % intId)
        row = cursor.fetchone
        if (row[0] != docType):
            cdrcgi.bail ("Document %d is of type %s, expecting type %s" %
                         (intId, row[0], docType))
    except cdrdb.Error, info:
        cdrcgi.bail("Unable to find document type for id = %s" % (intId,
                                                                  info[1][0]))


else:
    #------------------------------------------------------------------
    # Create a query for the correct document and mailer type
    # A different query is required for each of the three mailer types.
    # Document types are passed in to the query creation and do not
    #   change the structure of the query.
    #------------------------------------------------------------------
    if mailType == 'Initial':
        qry = """
            SELECT DISTINCT document.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN ready_for_review
                         ON ready_for_review.doc_id = doc_version.id
                       JOIN document document
                         ON document.id = ready_for_review.doc_id
                       JOIN doc_type
                         ON doc_type.id = document.doc_type
                      WHERE doc_type.name = '%s'
                        AND NOT EXISTS (SELECT *
                                          FROM pub_proc p
                                          JOIN pub_proc_doc pd
                                            ON p.id = pd.pub_proc
                                         WHERE pd.doc_id = document.id
                                           AND p.pub_subset = '%s'
                                           AND (p.status = 'Success'
                                            OR p.completed IS NULL))
                   GROUP BY document.id""" % (docType, subset)
    elif mailType == 'Update':
        qry = """
            SELECT DISTINCT doc.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN document doc
                         ON doc_version.id = doc.id
                       JOIN doc_type
                         ON doc_type.id = doc.doc_type
                       JOIN pub_proc_doc pd1
                         ON doc.id = pd1.doc_id
                       JOIN pub_proc p1
                         ON pd1.pub_proc = p1.id
                      WHERE doc_type.name = '%s'
                        AND p1.pub_subset LIKE '%s %% Mailers'
                        AND doc.id NOT IN (
                            SELECT pd2.doc_id
                              FROM pub_proc_doc pd2
                              JOIN pub_proc p2
                                ON p2.id = pd2.pub_proc
                             WHERE pd2.doc_id = doc.id
                               AND p2.pub_subset LIKE '%s %% Mailers'
                               AND p2.completed > DATEADD(year,-1,GETDATE())
                               AND (p2.status = 'Success'
                                OR p2.completed IS NULL))
                   GROUP BY doc.id""" % (docType, docType, docType)
    elif mailType == 'Remailer':
        qry = """
            XXXX - NOT YET WRITTEN - XXXX
            """
    else:
        cdrcgi.bail("Impossible value: %s in mailer type" % mailType)

    # Execute the query to find all matching documents
    try:
        cursor.execute(qry)
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

# Drop the job into the queue.
result = cdrpub.initNewJob(ctrlDocId, subset, session, docList, [], email)
if type(result) == type(""):
    cdrcgi.bail(result)
elif type(result) == type(u""):
    cdrcgi.bail(result.encode('latin-1'))
header  = cdrcgi.header(title, title, section, None, [])
html = """\
    <H3>Job Number %d Submitted</H3>
    <B>
     <FONT COLOR='black'>Use
      <A HREF='%s/PubStatus.py?id=%d'>this link</A> to view job status.
     </FONT>
    </B>
   </FORM>
  </BODY>
 </HTML>
""" % (result[0], cdrcgi.BASE, result[0])

cdrcgi.sendPage(header + html)
