#----------------------------------------------------------------------
#
# $Id: QcReport.py,v 1.42 2005-02-23 20:00:35 venglisc Exp $
#
# Transform a CDR document using a QC XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.41  2004/12/01 23:56:12  venglisc
# So far, a list of glossary terms used throughout a summary could only be
# displayed at the end of a document for patient summaries.  These
# modifications allow to have the list of glossary terms be available for
# HP summaries as well. (Bug 1415)
#
# Revision 1.40  2004/10/22 20:20:49  venglisc
# The BoardMember QC report failed if a person was not linked to a summary.
# This has been fixed by setting a bogus batch job ID to query the database.
#
# Revision 1.39  2004/07/13 19:43:40  venglisc
# Modified label from "Date Received" to "Date Response Received" (Bug 1054).
#
# Revision 1.38  2004/04/28 16:01:20  venglisc
# Modified SQL statement to eliminate picking up the value of the PDQKey
# instead of an organization cdr:ref ID. (Bug 1119)
#
# Revision 1.37  2004/04/16 22:06:51  venglisc
# Modified program to achieve the following:
# a)  Create user interface to run the QC report from the menus (Bug 1059)
# b)  Update the @@...@@ parameters of the BoardMember QC report to
#     populate these with the output from database queries. (Bug 1054).
#
# Revision 1.36  2004/04/02 19:46:20  venglisc
# Included function to populate the active/closed protocol link variables
# for the Organization QC report.
#
# Revision 1.35  2004/03/06 23:23:37  bkline
# Added code to replace @@CTGOV_PROTOCOLS@@.
#
# Revision 1.34  2004/01/14 18:45:22  venglisc
# Modified user input form to allow Reformatted Patient Summaries to use the
# Comment element as well as Redline/Strikeout and Bold/Under reports.
#
# Revision 1.33  2003/12/16 15:49:13  bkline
# Modifed report to drop PDQ indexing section if first attempt to filter
# a CTGovProtocol document fails.
#
# Revision 1.32  2003/11/25 12:48:34  bkline
# Added code to plug in information about latest mods to document.
#
# Revision 1.31  2003/11/20 21:36:04  bkline
# Plugged in support for CTGovProtocol documents.
#
# Revision 1.30  2003/11/12 19:58:47  bkline
# Modified Person QC report to reflect use in external_map table.
#
# Revision 1.29  2003/09/16 21:15:39  bkline
# Changed test for Summary docType to take into account suffixes that
# may have been added to the string to indicate which flavor of report
# has been requested.
#
# Revision 1.28  2003/09/05 21:05:43  bkline
# Tweaks for "Display Comments" checkbox requested by Margaret.
#
# Revision 1.27  2003/09/04 21:31:01  bkline
# Added checkbox for DisplayComments (summary reports).
#
# Revision 1.26  2003/08/27 16:39:28  venglisc
# Modified code to include the report type but (bold/underline test)
# to pass the additional parameter just as report type bu (bold/underline)
# does.
#
# Revision 1.25  2003/08/25 20:27:30  bkline
# Plugged in support for displaying StandardWording markup in patient
# summary QC report.
#
# Revision 1.24  2003/08/11 21:57:19  venglisc
# Modified code to pass an additional parameter named delRefLevels to the
# summary QC reports to handle insertion/deletion markup properly.
# The parameter revLevels has been renamed to insRevLevels.
#
# Revision 1.23  2003/08/01 21:01:43  bkline
# Added code to create subtitle dynamically based on report subtype;
# added separate CGI variables for deletion markup settings.
#
# Revision 1.22  2003/07/29 12:45:35  bkline
# Checked in modifications made by Peter before he left the project.
#
# Revision 1.21  2003/06/13 20:27:26  bkline
# Added interface for choosing whether to include glossary terms list
# at the bottom of the patient summary report.
#
# Revision 1.20  2003/05/22 13:25:39  bkline
# Checked 'approved' option by default at Margaret's request.
#
# Revision 1.19  2003/05/09 20:41:20  pzhang
# Added Summary:pat to filter sets.
#
# Revision 1.18  2003/05/08 20:25:24  bkline
# User now allowed to specify revision level.
#
# Revision 1.17  2003/04/10 21:34:23  pzhang
# Added Insertion/Deletion revision level feature.
# Used filter set names for all filter sets.
#
# Revision 1.16  2003/04/02 21:21:15  pzhang
# Added the filter to sort OrganizationName.
#
# Revision 1.15  2002/12/30 15:15:47  bkline
# Fixed a typo.
#
# Revision 1.14  2002/12/26 21:54:40  bkline
# Added doc id to new screen for multiple matching titles.
#
# Revision 1.13  2002/12/26 21:50:24  bkline
# Changes implemented for issue #545.
#
# Revision 1.12  2002/09/26 15:31:17  bkline
# New filters for summary QC reports.
#
# Revision 1.11  2002/09/19 15:14:26  bkline
# Added filters at Cheryl's request.
#
# Revision 1.10  2002/08/14 17:26:16  bkline
# Added new denormalization filters for summaries.
#
# Revision 1.9  2002/06/26 20:38:52  bkline
# Plugged in mailer info for Organization QC reports.
#
# Revision 1.8  2002/06/26 18:30:48  bkline
# Fixed bug in mailer query logic.
#
# Revision 1.7  2002/06/26 16:35:17  bkline
# Implmented report of audit_trail activity.
#
# Revision 1.6  2002/06/24 17:15:24  bkline
# Added documents linking to Person.
#
# Revision 1.5  2002/06/06 15:01:06  bkline
# Switched to GET HTTP method so "Edit with Microsoft Word" will work in IE.
#
# Revision 1.4  2002/06/06 12:01:08  bkline
# Custom handling for Person and Summary QC reports.
#
# Revision 1.3  2002/05/08 17:41:53  bkline
# Updated to reflect Volker's new filter names.
#
# Revision 1.2  2002/05/03 20:30:22  bkline
# New filters and filter names.
#
# Revision 1.1  2002/04/22 13:54:07  bkline
# New QC reports.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, sys

#----------------------------------------------------------------------
# Dynamically create the title of the menu section (request #809).
#----------------------------------------------------------------------
def getSectionTitle(repType):
    if not repType:
        return "QC Report"
    elif repType == "bu":
        return "Bold/Underline QC Report"
    elif repType == "but":
        return "Bold/Underline QC Report (Test)"
    elif repType == "rs":
        return "Redline/Strikeout QC Report"
    elif repType == "rst":
        return "Redline/Strikeout QC Report (Test)"
    elif repType == "nm":
        return "QC Report (No Markup)"
    elif repType == "pat":
        return "Patient QC Report"
    elif repType == "pp":
        return "Publish Preview Report"
    else:
        return "QC Report (Unrecognized Type)"

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "CDR QC Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
repType  = fields.getvalue("ReportType") or None
section  = "QC Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, getSectionTitle(repType),
                         "QcReport.py", buttons, method = 'GET')
docId    = fields.getvalue(cdrcgi.DOCID) or None
docType  = fields.getvalue("DocType")    or None
docTitle = fields.getvalue("DocTitle")   or None
version  = fields.getvalue("DocVersion") or None
glossary = fields.getvalue("Glossary")   or None
standardWording = fields.getvalue("ShowStandardWording") or None
displayComments = fields.getvalue("DisplayCommentElements") or None
insRevLvls  = fields.getvalue("revLevels")  or None
delRevLvls  = fields.getvalue("delRevLevels")  or None
if not insRevLvls:
    insRevLvls = fields.getvalue('publish') and 'publish|' or '' 
    insRevLvls += fields.getvalue('approved') and 'approved|' or ''
    insRevLvls += fields.getvalue('proposed') and 'proposed' or '' 
 
if not docId and not docType:
    cdrcgi.bail("No document specified", repTitle)
if docId:
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we have a document type but no doc ID or title, ask for the title.
#----------------------------------------------------------------------
if not docId and not docTitle:
    extra = ""
    if docType:
        extra += "<INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>" % docType
        if docType == 'PDQBoardMemberInfo':
           label = ['Board Member Name',
                    'Board Member CDR ID']
        else:
           label = ['Document Title',
                    'Document CDR ID']

    if repType:
        extra += "<INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>" % repType
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  %s
  <TABLE>
   <TR>
    <TD ALIGN='right'><B>%s:&nbsp;</B><BR/>(use %% as wildcard)</TD>
    <TD><INPUT SIZE='60' NAME='DocTitle'></TD>
   </TR>
   <TR>
    <TD> </TD>
    <TD>... or ...</TD>
   </TR>
   <TR>
    <TD ALIGN='right'><B>%s:&nbsp;</B></TD>
    <TD><INPUT SIZE='60' NAME='DocId'></TD>
   </TR>
  </TABLE>
""" % (cdrcgi.SESSION, session, extra, label[0], label[1])
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# More than one matching title; let the user choose one.
#----------------------------------------------------------------------
def showTitleChoices(choices):
    form = """\
   <H3>More than one matching document found; please choose one.</H3>
"""
    for choice in choices:
        form += """\
   <INPUT TYPE='radio' NAME='DocId' VALUE='CDR%010d'>[CDR%d] %s<BR>
""" % (choice[0], choice[0], cgi.escape(choice[1]))
    cdrcgi.sendPage(header + form + """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, docType or '', repType or ''))
                    
#----------------------------------------------------------------------
# If we have a document title but not a document ID, find the ID.
#----------------------------------------------------------------------
if docTitle and not docId:
    try:
        if docType:
            cursor.execute("""\
                SELECT document.id, document.title
                  FROM document
                  JOIN doc_type
                    ON doc_type.id = document.doc_type
                 WHERE doc_type.name = ?
                   AND document.title LIKE ?""", (docType, docTitle + '%'))
        else:
            cursor.execute("""\
                SELECT id
                  FROM document
                 WHERE title LIKE ?""", docTitle + '%')
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find document with title '%s'" % docTitle)
        if len(rows) > 1:
            showTitleChoices(rows)
        intId = rows[0][0]
        docId = "CDR%010d" % intId
    except cdrdb.Error, info:
        cdrcgi.bail('Failure looking up document title: %s' % info[1][0])

#----------------------------------------------------------------------
# Let the user pick the version for most Summary reports.
#----------------------------------------------------------------------
if docType == 'Summary' and repType and repType != 'pp' and not version:
    try:
        cursor.execute("""\
            SELECT num,
                   comment,
                   dt
              FROM doc_version
             WHERE id = ?
          ORDER BY num DESC""", intId)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving document versions: %s' % info[1][0])
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='DocType' VALUE='Summary'>
  <INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='DocId' VALUE='CDR%010d'>
  Select document version:&nbsp;
  <SELECT NAME='DocVersion'>
   <OPTION VALUE='-1' SELECTED='1'>Current Working Version</OPTION>
""" % (cdrcgi.SESSION, session, repType, intId)
    for row in rows:
        form += """\
   <OPTION VALUE='%d'>[V%d %s] %s</OPTION>
""" % (row[0], row[0], row[2][:10], row[1] or "[No comment]")
        selected = ""
    form += "</SELECT>"
    form += """
  <BR><BR>
  Select Insertion/Deletion markup to be displayed in the report (one or more):
  <BR>
  <INPUT TYPE="checkbox" NAME="publish">&nbsp;&nbsp; With publish attribute<BR>
  <INPUT TYPE="checkbox" NAME="approved"
                         CHECKED='1'>&nbsp;&nbsp; With approved attribute<BR>
  <INPUT TYPE="checkbox" NAME="proposed">&nbsp;&nbsp; With proposed attribute
  <BR><BR>
  <INPUT TYPE='checkbox' NAME='DisplayCommentElements' CHECKED='1'>&nbsp;&nbsp;
  Display Comments?
"""
#if repType == "pat":
    form += """\
  <BR><BR>
  <INPUT TYPE='checkbox' NAME='Glossary'>&nbsp;&nbsp;
  Include glossary terms at end of report?<BR>
"""

    if repType == "pat":
        form += """\
  <BR>
  <INPUT TYPE='checkbox' NAME='ShowStandardWording'>&nbsp;&nbsp;
  Show standard wording with mark-up?<BR>
"""
    cdrcgi.sendPage(header + form + """  
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Map for finding the filters for a given document type.
#----------------------------------------------------------------------
filters = {
    'Summary':        
        ["set:QC Summary Set"],
    'Summary:bu': # Bold/Underline
        ["set:QC Summary Set (Bold/Underline)"],
    'Summary:rs': # Redline/Strikeout
        ["set:QC Summary Set"],
    'Summary:but': # Bold/Underline
        ["set:QC Summary Test Set (Bold/Underline)"],
    'Summary:rst': # Redline/Strikeout
        ["set:QC Summary Test Set"],
    'Summary:nm': # No markup
        ["set:QC Summary Set"],
    'Summary:pat': # Patient
        ["set:QC Summary Patient Set"],
    'GlossaryTerm':         
        ["set:QC GlossaryTerm Set"],
    'Citation':         
        ["set:QC Citation Set"],
    'Organization':     
        ["set:QC Organization Set"],
    'Person':           
        ["set:QC Person Set"],
    'PDQBoardMemberInfo':           
        ["set:QC PDQBoardMemberInfo Set"],
    'InScopeProtocol':  
        ["set:QC InScopeProtocol Set"],
    'Term':             
        ["set:QC Term Set"],
    'MiscellaneousDocument':
        ["set:QC MiscellaneousDocument Set"],
    'CTGovProtocol':
        ["set:QC CTGovProtocol Set"]
}

#----------------------------------------------------------------------
# Determine the document type.
#----------------------------------------------------------------------
if not docType:
    try:
        cursor.execute("""\
            SELECT name
              FROM doc_type
              JOIN document
                ON document.doc_type = doc_type.id
             WHERE document.id = ?""", (intId,))
        row = cursor.fetchone()
        if not row:
            cdrcgi.bail("Unable to find document type for %s" % docId)
        docType = row[0]
    except cdrdb.Error, info:    
            cdrcgi.bail('Unable to find document type for %s: %s' % (docId, 
                                                                 info[1][0]))

#----------------------------------------------------------------------
# Get count of links to a person document from protocols and summaries.
# Returns a list of 4 numbers:
#  * Count of linking active, approved, or temporarily closed protocols
#  * Count of linking closed or completed protocols
#  * Count of linking health professional summaries
#  * Count of linking patient summaries
#----------------------------------------------------------------------
def getDocsLinkingToPerson(docId):
    counts = [0, 0, 0, 0, 0]
    statusValues = [ ('Active',
                      'Approved-not yet active', 
                      'Temporarily Closed'),
                     ('Closed',
                      'Completed')
                   ]

    try:
        cursor.callproc('cdr_get_count_of_links_to_persons', docId)
        for row in cursor.fetchall():
            if row[1] in statusValues[0]:        counts[0] += row[0]
            if row[1] in statusValues[1]:        counts[1] += row[0]
        cursor.nextset()
        for row in cursor.fetchall():
            if row[1] == 'Health professionals': counts[2] += row[0]
            if row[1] == 'Patients':             counts[3] += row[0]

        # Test for CTGov documents linking here
        # -------------------------------------
        cursor.execute("""\
            SELECT COUNT(DISTINCT doc_id)
              FROM query_term
             WHERE int_val = ?
               AND path LIKE '/CTGovProtocol/%/@cdr:ref'""", docId)
        counts[4] = cursor.fetchall()[0][0]

    except cdrdb.Error, info:    
        cdrcgi.bail('Failure retrieving link counts: %s' % info[1][0])
    return counts

#----------------------------------------------------------------------
# Plug in mailer information from database.
#----------------------------------------------------------------------
def fixMailerInfo(doc):
    mailerDateSent         = "No mailers sent for this document"
    mailerResponseReceived = "N/A"
    mailerTypeOfChange     = "N/A"
    try:
        cursor.execute("""\
            SELECT MAX(doc_id)
              FROM query_term
             WHERE path = '/Mailer/Document/@cdr:ref'
               AND int_val = ?""", intId)
        row = cursor.fetchone()
        if row and row[0]:
            mailerId = row[0]
            cursor.execute("""\
                SELECT date_sent.value,
                       response_received.value,
                       change_type.value
                  FROM query_term date_sent
       LEFT OUTER JOIN query_term response_received
                    ON response_received.doc_id = date_sent.doc_id
                   AND response_received.path = '/Mailer/Response/Received'
       LEFT OUTER JOIN query_term change_type
                    ON change_type.doc_id = date_sent.doc_id
                   AND change_type.path = '/Mailer/Response/ChangesCategory'
                 WHERE date_sent.path = '/Mailer/Sent'
                   AND date_sent.doc_id = ?""", mailerId)
            row = cursor.fetchone()
            if not row:
                mailerDateSent = "Unable to retrieve date mailer was sent"
            else:
                mailerDateSent = row[0]
                if row[1]:
                    mailerResponseReceived = row[1]
                    if row[2]:
                        mailerTypeOfChange = row[2]
                    else:
                        mailerTypeOfChange = "Unable to retrieve change type"
                else:
                    mailerResponseReceived = "Response not yet received"
    except cdrdb.Error, info:    
        cdrcgi.bail('Failure retrieving mailer info for %s: %s' % (docId, 
                                                                   info[1][0]))
    doc = re.sub("@@MAILER_DATE_SENT@@",         mailerDateSent,         doc)
    doc = re.sub("@@MAILER_RESPONSE_RECEIVED@@", mailerResponseReceived, doc)
    doc = re.sub("@@MAILER_TYPE_OF_CHANGE@@",    mailerTypeOfChange,     doc)
    return doc

#----------------------------------------------------------------------
# Plug in pieces that XSL/T can't get to for a Person QC report.
#----------------------------------------------------------------------
def fixPersonReport(doc):
    cursor.execute("SELECT COUNT(*) FROM external_map WHERE doc_id = ?",
                   intId)
    row    = cursor.fetchone()
    doc    = fixMailerInfo(doc)
    counts = getDocsLinkingToPerson(intId)
    #cdrcgi.bail("doctype = %s" % docType)
    # ---------------------------------------------------------
    # Suppress replacing the strings if this function is called
    # for the Organization docType
    # ---------------------------------------------------------
    if docType != 'Organization':
       doc    = re.sub("@@ACTIVE_APPR0VED_TEMPORARILY_CLOSED_PROTOCOLS@@",
                    counts[0] and "Yes" or "No", doc)
       doc    = re.sub("@@CLOSED_COMPLETED_PROTOCOLS@@",
                    counts[1] and "Yes" or "No", doc)

    doc    = re.sub("@@HEALTH_PROFESSIONAL_SUMMARIES@@",
                    counts[2] and "Yes" or "No", doc)
    doc    = re.sub("@@PATIENT_SUMMARIES@@",
                    counts[3] and "Yes" or "No", doc)
    doc    = re.sub("@@IN_EXTERNAL_MAP_TABLE@@",
                    (row[0] > 0) and "Yes" or "No", doc)
    doc    = re.sub("@@CTGOV_PROTOCOLS@@",
                    (counts[4]) and "Yes" or "No", doc)
    return doc

#----------------------------------------------------------------------
# Plug in last update info for CTGovProtocol.
#----------------------------------------------------------------------
def fixCTGovProtocol(doc):
    cursor.execute("""\
    SELECT TOP 1 t.dt, u.name
      FROM audit_trail t
      JOIN action a
        ON a.id = t.action
      JOIN usr u
        ON u.id = t.usr
     WHERE a.name = 'MODIFY DOCUMENT'
       AND u.name <> 'CTGovImport'
       AND t.document = ?
  ORDER BY t.dt DESC""", intId)
    row = cursor.fetchone()
    if row:
        doc = doc.replace("@@UPDATEDBY@@", row[1])
        doc = doc.replace("@@UPDATEDDATE@@", row[0][:10])
    else:
        doc = doc.replace("@@UPDATEDBY@@", "&nbsp;")
        doc = doc.replace("@@UPDATEDDATE@@", "&nbsp;")
    #cdrcgi.bail("NPI=" + noPdqIndexing)
    return doc.replace("@@NOPDQINDEXING@@", noPdqIndexing)
        

#----------------------------------------------------------------------
# Plug in pieces that XSL/T can't get to for an Organization QC report.
#----------------------------------------------------------------------
def fixOrgReport(doc):
    counts = [0, 0, 0, 0]
    # -----------------------------------------------------------------
    # Database query to count all protocols that link to this 
    # organization split by Active and Closed protocol status.
    # -----------------------------------------------------------------
    try:
        cursor.execute("""\
        SELECT count(prot.doc_id) AS prot_count, 
               CASE WHEN prot.value = 'Completed'               THEN 'Closed'
                    WHEN prot.value = 'Temporarily closed'      THEN 'Active'
                    WHEN prot.value = 'Approved-not yet active' THEN 'Active'
                    ELSE prot.value END as status
          FROM query_term prot
          JOIN query_term org
            ON prot.doc_id = org.doc_id
         WHERE prot.path ='/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
           AND prot.value in ('Active', 'Temporarily closed', 
                              'Approved-not yet active', 'Closed', 'Completed') 
           AND org.int_val = ?
           AND org.path like '%@cdr:ref'
         GROUP BY prot.value""", intId)
    except cdrdb.Error, info:    
        cdrcgi.bail('Failure retrieving Protocol info for %s: %s' % (intId, 
                                                                   info[1][0]))

    # -------------------------------------------------------
    # Assign protocol count to counts list items
    # -------------------------------------------------------
    rows = cursor.fetchall()
    for row in rows:
        if row[1] == 'Active':        counts[0] += row[0]
        if row[1] == 'Closed':        counts[1] += row[0]

    # Test for Person documents linking here
    # --------------------------------------
    cursor.execute("""\
        SELECT COUNT(DISTINCT doc_id)
          FROM query_term
         WHERE int_val = ?
           AND path LIKE '/Person/%/@cdr:ref'""", intId)
    counts[2] = cursor.fetchall()[0][0]

    # Test for Organization documents linking here
    # --------------------------------------------
    cursor.execute("""\
        SELECT COUNT(DISTINCT doc_id)
          FROM query_term
         WHERE int_val = ?
           AND path LIKE '/Organization/%/@cdr:ref'""", intId)
    counts[3] = cursor.fetchall()[0][0]

    # -----------------------------------------------------------------
    # Substitute @@...@@ strings with Yes/No based on the count
    # from the query.  If counts[] = 0 ==> "No", "Yes" otherwise
    # -----------------------------------------------------------------
    doc    = re.sub("@@ACTIVE_APPR0VED_TEMPORARILY_CLOSED_PROTOCOLS@@",
                    counts[0] and "Yes" or "No", doc)
    doc    = re.sub("@@CLOSED_COMPLETED_PROTOCOLS@@",
                    counts[1] and "Yes" or "No", doc)
    doc    = re.sub("@@PERSON_DOC_LINKS@@",
                    counts[2] and "Yes" or "No", doc)
    doc    = re.sub("@@ORG_DOC_LINKS@@",
                    counts[3] and "Yes" or "No", doc)

    return doc

#----------------------------------------------------------------------
# Plug in pieces that XSL/T can't get to for an BoardMember QC report.
#----------------------------------------------------------------------
def fixBoardMemberReport(doc):
    counts = [0, 0]
    # -----------------------------------------------------------------
    # Database query to get the person ID for the BoardMember     
    # -----------------------------------------------------------------
    try:
        cursor.execute("""\
SELECT int_val
  FROM query_term
 WHERE doc_id = ?
   AND path = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'""", intId)

    except cdrdb.Error, info:    
        cdrcgi.bail('Failure retrieving Person ID for %s: %s' % (intId, 
                                                                   info[1][0]))

    row = cursor.fetchone()
    if not row:
        cdrcgi.bail('Unable to select Person ID for CDR%s' % intId)
    else:
        personId = row[0]

    # -----------------------------------------------------------------
    # Database query to select all summaries reviewed by this member
    # and the batch job ID of the latest mailer submitted
    # and replace the result with the @@SUMMARIES_REVIEWED@@ parameter.
    # -----------------------------------------------------------------
    try:
        cursor.execute("""\
SELECT person.doc_id, summary.value, audience.value, max(ppd.pub_proc) as jobid
  FROM query_term person
  JOIN query_term summary
    ON person.doc_id = summary.doc_id
  JOIN query_term audience
    ON summary.doc_id = audience.doc_id
  JOIN document doc
    ON person.doc_id = doc.id
  JOIN pub_proc_doc ppd
    ON doc.id = ppd.doc_id
  JOIN pub_proc pp
    ON pp.id = ppd.pub_proc
 WHERE person.int_val = ?
   AND person.path = '/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref'
   AND summary.path = '/Summary/SummaryTitle'
   AND audience.path = '/Summary/SummaryMetaData/SummaryAudience'
   AND doc.active_status = 'A'
   AND pp.status = 'Success'
   AND pp.pub_subset = 'Summary-PDQ Editorial Board'
 GROUP BY summary.value, person.doc_id, audience.value""", personId)

    except cdrdb.Error, info:    
        cdrcgi.bail('Failure retrieving Summary info for CDR%s: %s' % (intId, 
                                                                   info[1][0]))

    # -------------------------------------------------------
    # Display the summaries reviewed by this person.
    # -------------------------------------------------------
    rows = cursor.fetchall()

    if rows:
       html = """
           <DL>"""
       for row in rows:
           html += """
            <LI>%s; %s</LI>""" % (row[1], row[2])
       html += """
           </DL>
"""
    else:
       html = "None"

    # -----------------------------------------------------------------
    # Substitute @@...@@ strings with Yes/No based on the count
    # from the query.  If counts[] = 0 ==> "No", "Yes" otherwise
    # -----------------------------------------------------------------
    doc    = re.sub("@@SUMMARIES_REVIEWED@@", html, doc)

    # ------------------------------------------------------------------
    # Database query to select mailer information
    # From the previous query we know the summary IDs, person ID and 
    # Job ID that containted these mailers.  We are using this 
    # information to build this query to extract the response received
    # from the mailer docs.
    # If the person is not linked to a summary we're setting the batchId
    # to zero, otherwise the query would fail.
    # ------------------------------------------------------------------
    if rows:
       batchId = row[3]
       summaryIds = '('
       for row in rows:
          summaryIds += repr(row[0]) + ', '
       summaryIds = summaryIds[:-2] + ')'
    else:
       batchId = 0
       summaryIds = '(0)'


    query = """
SELECT mailer.doc_id, mailer.int_val, summary.value, response.value,
       title.value
  FROM query_term mailer
  JOIN query_term summary
    ON mailer.doc_id = summary.doc_id
  LEFT OUTER 
  JOIN query_term response
    ON mailer.doc_id = response.doc_id
   AND response.path = '/Mailer/Response/Received'
  JOIN query_term title
    ON title.doc_id = summary.int_val
  JOIN query_term person
    ON mailer.doc_id = person.doc_id
 WHERE mailer.int_val = %d
   AND mailer.path = '/Mailer/JobId'
   AND summary.int_val in %s 
   AND title.path = '/Summary/SummaryTitle'
   AND person.int_val = %s
 ORDER BY title.value""" % (batchId, summaryIds, personId)

    try:
       cursor.execute(query)
    except cdrdb.Error, info:    
       cdrcgi.bail('Failure retrieving Mailer info for batch ID %d: %s' % (batchId,
                                                                   info[1][0]))

    rows = cursor.fetchall()

    # ----------------------------------------------------------------
    # Display the Summary Mailer information
    # ----------------------------------------------------------------
    html = ''
    for row in rows:
        html += """
      <TR>
       <TD xsl:use-attribute-sets = "cell1of2">
        <B>Summary</B>
       </TD>
       <TD xsl:use-attribute-sets = "cell2of2">
        %s
       </TD>
      </TR>
      <TR>
       <TD xsl:use-attribute-sets = "cell1of2">
        <B>Date Response Received</B>
       </TD>
       <TD xsl:use-attribute-sets = "cell2of2">
        %s
       </TD>
      </TR>
""" % (row[4], row[3])
    doc    = re.sub("@@SUMMARY_MAILER_SENT@@", html, doc)

    # -----------------------------------------------------------------
    # Database query to select the time of the mailers send
    # -----------------------------------------------------------------
    try:
	query = """
SELECT completed
  FROM pub_proc
 WHERE id = %d""" % batchId
        cursor.execute(query)

    except cdrdb.Error, info:    
        cdrcgi.bail('Failure retrieving Mailer Date for batch %d: %s' % (batchId, 
                                                                   info[1][0]))
    row = cursor.fetchone()
    # -----------------------------------------------------------------
    # Substitute @@...@@ strings for job ID and date send
    # If the person is not linked to a summary we won't find an entry
    # in the pub_proc table.  The batchId will have been set to zero
    # in this case.
    # -----------------------------------------------------------------
    if row:
       dateSent = row[0][:10]
       html = "%s" % (dateSent)
       doc    = re.sub("@@SUMMARY_DATE_SENT@@", html, doc)
       html = "%s" % (batchId)
       doc    = re.sub("@@SUMMARY_JOB_ID@@", html, doc)
    else:
       doc    = re.sub("@@SUMMARY_DATE_SENT@@", "N/A", doc)
       doc    = re.sub("@@SUMMARY_JOB_ID@@", "N/A", doc)

    return doc

# --------------------------------------------------------------------
# If we want to see the publish preview report call the PublishPreview
# script.
# --------------------------------------------------------------------
if repType == "pp":
    cmd = "python d:\\Inetpub\\wwwroot\\cgi-bin\\cdr\\PublishPreview.py %s summary" % docId
    result = cdr.runCommand(cmd)
    cdrcgi.sendPage(result.output)

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
if repType: docType += ":%s" % repType
if version == "-1": version = None
if not filters.has_key(docType):
    doc = cdr.getDoc(session, docId, version = version or "Current",
                     getObject = 1)
    if type(doc) in (type(""), type(u"")):
        cdrcgi.bail(doc)
    html = """\
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <pre>%s</pre>
 </body>
</html>""" % (doc.ctrl['DocTitle'], cgi.escape(doc.xml))
    cdrcgi.sendPage(cdrcgi.unicodeToLatin1(html))

filterParm = []
if insRevLvls:
    filterParm = [['insRevLevels', insRevLvls]]
if docType.startswith('Summary'):
    filterParm.append(['DisplayComments',
                       displayComments and 'Y' or 'N'])
if repType == "bu" or repType == "but":
    filterParm.append(['delRevLevels', 'Y'])

# Added GlossaryTermList to HP documents, not just patient.
filterParm.append(['DisplayGlossaryTermList',
                       glossary and "Y" or "N"])
if repType == "pat":
    filterParm.append(['ShowStandardWording',
                       standardWording and "Y" or "N"])
doc = cdr.filterDoc(session, filters[docType], docId = docId,
                    docVer = version or None, parm = filterParm)
#if (type(doc) in (type(""), type(u"")):
#    cdrcgi.bail("OOPS! %s" % doc)
if docType == "CTGovProtocol":
    if (type(doc) in (type(""), type(u"")) and
        doc.find("undefined/lastp") != -1):
        # cdrcgi.bail("CTGovProtocol QC Report cannot be run until "
        #             "PDQIndexing block has been completed")
        filterParm.append(['skipPdqIndexing', 'Y'])
        doc = cdr.filterDoc(session, filters[docType], docId = docId,
                            docVer = version or None, parm = filterParm)
        noPdqIndexing = """
   <br>
   <br>
   <h1 style='color: red'>*** PDQ INDEXING BLOCK HAS BEEN OMITTED
                              TO AVOID BROKEN LINK FAILURES ***</h1>
"""
    else:
        noPdqIndexing = ""
if type(doc) in (type(""), type(u"")):
    cdrcgi.bail(doc)
if type(doc) == type(()):
    doc = doc[0]

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)
if docType == 'Person':
    doc = fixPersonReport(doc)
elif docType == 'Organization':
    # -----------------------------------------------------
    # We call the fixPersonReport for Organizations too 
    # since Person and Orgs have the Record Info and 
    # Most Recent Mailer Info in common.
    # The resulting document goes through the fixOrgReport
    # module to resolve the protocol link entries
    # -----------------------------------------------------
    doc = fixPersonReport(doc)
    doc = fixOrgReport(doc)
elif docType == 'CTGovProtocol':
    doc = fixCTGovProtocol(doc)
elif docType == 'PDQBoardMemberInfo':
    doc = fixBoardMemberReport(doc)
# cdrcgi.bail("docType = %s" % docType)
    
#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
