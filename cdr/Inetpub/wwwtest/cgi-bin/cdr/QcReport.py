#----------------------------------------------------------------------
#
# $Id: QcReport.py,v 1.24 2003-08-11 21:57:19 venglisc Exp $
#
# Transform a CDR document using a QC XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
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
    if repType:
        extra += "<INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>" % repType
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  %s
  <TABLE>
   <TR>
    <TD ALIGN='right'>Document title:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocTitle'></TD>
   </TR>
   <TR>
    <TD ALIGN='right'>Document ID:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocId'></TD>
   </TR>
  </TABLE>
""" % (cdrcgi.SESSION, session, extra)
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
   <INPUT TYPE='radio' NAME='DocId' VALUE='CDR%010d'>[CDR%010d] %s<BR>
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
if docType == 'Summary' and repType and not version:
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
"""
    if repType == "pat":
        form += """\
  <BR><BR>
  <INPUT TYPE='checkbox' NAME='Glossary'>&nbsp;&nbsp;
  Include glossary terms at end of report?<BR>
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
    'InScopeProtocol':  
        ["set:QC InScopeProtocol Set"],
    'Term':             
        ["set:QC Term Set"],
    'MiscellaneousDocument':
        ["set:QC MiscellaneousDocument Set"]
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
    counts = [0, 0, 0, 0]
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
    doc    = fixMailerInfo(doc)
    counts = getDocsLinkingToPerson(intId)
    doc    = re.sub("@@ACTIVE_APPR0VED_TEMPORARILY_CLOSED_PROTOCOLS@@",
                    counts[0] and "Yes" or "No", doc)
    doc    = re.sub("@@CLOSED_COMPLETED_PROTOCOLS@@",
                    counts[1] and "Yes" or "No", doc)
    doc    = re.sub("@@HEALTH_PROFESSIONAL_SUMMARIES@@",
                    counts[2] and "Yes" or "No", doc)
    doc    = re.sub("@@PATIENT_SUMMARIES@@",
                    counts[3] and "Yes" or "No", doc)
    return doc

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
if repType == "bu":
    filterParm.append(['delRevLevels', 'Y'])
if repType == "pat":
    filterParm.append(['DisplayGlossaryTermList',
                       glossary and "Y" or "N"])
doc = cdr.filterDoc(session, filters[docType], docId = docId,
                    docVer = version or None, parm = filterParm)
if type(doc) == type(()):
    doc = doc[0]

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)
if docType == 'Person':
    doc = fixPersonReport(doc)
elif docType == 'Organization':
    doc = fixPersonReport(doc)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
