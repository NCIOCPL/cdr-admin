#----------------------------------------------------------------------
#
# $Id: QcReport.py,v 1.4 2002-06-06 12:01:08 bkline Exp $
#
# Transform a CDR document using a QC XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
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
import cgi, cdr, cdrcgi, cdrdb, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "CDR QC Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "QC Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, section, "QcReport.py", buttons)
docId    = fields.getvalue(cdrcgi.DOCID) or None
docType  = fields.getvalue("DocType")    or None
repType  = fields.getvalue("ReportType") or None
docTitle = fields.getvalue("DocTitle")   or None
version  = fields.getvalue("DocVersion") or None
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
    <TD>Document title:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocTitle'></TD>
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
# If we have a document title but not a document ID, find the ID.
#----------------------------------------------------------------------
if docTitle and not docId:
    try:
        if docType:
            cursor.execute("""\
                SELECT document.id
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
            cdrcgi.bail("Ambiguous title '%s'" % docTitle)
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
    cdrcgi.sendPage(header + form + """\
  </SELECT>
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Map for finding the filters for a given document type.
#----------------------------------------------------------------------
summaryDenormalizationFilters = [
         "name:Denormalization Filter (1/5): Summary",
         "name:Denormalization Filter (2/5): Summary",
         "name:Denormalization Filter (3/5): Summary",
         "name:Denormalization Filter (4/5): Summary",
         "name:Denormalization Filter (5/5): Summary"]
filters = {
    'Summary':
        summaryDenormalizationFilters +
        ["name:Health Professional Summary Report"],
    'Summary:bu': # Bold/Underline
        summaryDenormalizationFilters +
        ["name:Health Professional Summary Report-Bold/Underline"],
    'Summary:rs': # Redline/Strikeout
        summaryDenormalizationFilters +
        ["name:Health Professional Summary Report"],
    'Summary:nm': # No markup
        summaryDenormalizationFilters +
        ["name:Health Professional Summary Report"],
    'GlossaryTerm':         
        ["name:Glossary Term QC Report Filter"],
    'Citation':         
        ["name:Citation QC Report"],
    'Organization':     
        ["name:Denormalization Filter (1/1): Organization",
         "name:Organization QC Report Filter"],
    'Person':           
        ["name:Denormalization Filter (1/1): Person",
         "name:Person QC Report Filter"],
    'InScopeProtocol':  
        ["name:Denormalization Filter (1/1): InScope Protocol",
         "name:Create InScope Protocol XML for Full Protocol QC Report",
         "name:InScope Protocol Full QC Report"],
    'Term':             
        ["name:Denormalization Filter (1/1): Terminology",
         "name:Terminology QC Report Filter"],
    'MiscellaneousDocument':
        ["name:Miscellaneous Document Report Filter"]
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
# Plug in pieces that XSL/T can't get to for a Person QC report.
#----------------------------------------------------------------------
def fixPersonReport(doc):
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
        if row:
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
# Filter the document.
#----------------------------------------------------------------------
if repType: docType += ":%s" % repType
if version == "-1": version = None
if not filters.has_key(docType):
    cdrcgi.bail("Don't have filters set up for %s documents yet" % docType)
doc = cdr.filterDoc(session, filters[docType], docId = docId,
                                               docVer = version or None)
if type(doc) == type(()):
    doc = doc[0]

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)
if docType == 'Person':
    doc = fixPersonReport(doc)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
