#----------------------------------------------------------------------
#
# $Id$
#
# Transform a CDR document using a QC XSL/T filter and send it back to
# the browser.
#
# BZIssue::4751 - Modify BU Report to display LOERef
# BZIssue::4672 - Changes to LinkedDoc Report
# BZIssue::4781 - Have certain links to unpublished docs ignored
#
# Revision 1.69  2009/05/28 20:38:26  venglisc
# Added checkbox to suppress display of Reference sections. (Bug 4562)
#
# Revision 1.68  2009/03/23 15:48:10  venglisc
# Modified DocType coming in from Drug Summaries to be the CDR doctype
# 'DrugInformationSummary' instead of 'DIS' allowing for comparison with the
# database value.
#
# Revision 1.67  2009/03/10 21:49:38  bkline
# Cosmetic cleanup.
#
# Revision 1.66  2009/03/10 21:35:05  bkline
# Suppressed version choice page for "Glossary Term Name with Concept"
# QC report at William's request (see comment #3 in issue #4478); also
# (same comment) added code to distinguish between errors caused by
# entering a CDR for a document of the wrong type, and errors caused by
# entering a CDR ID for which no document can be found.
#
# Revision 1.65  2009/03/03 18:34:50  venglisc
# Modified program to use filter set for GlossaryTermName instead of single
# filter.
#
# Revision 1.64  2009/02/10 22:40:45  bkline
# Added Glossary Term Name with Concept QC Report (request #4478).
#
# Revision 1.63  2009/02/10 21:29:13  bkline
# Added ability to search for glossary term concept documents by
# definition substring.
#
# Revision 1.62  2009/01/06 21:38:12  ameyer
# Fixed my fix to a Unicode bug.  Added documentation to make clearer
# what the sequence of encodings is.
#
# Revision 1.61  2008/12/16 22:10:39  ameyer
# Fixed encoding so that final sendPage sends Unicode instead of UTF-8.
#
# Revision 1.60  2008/12/11 20:18:49  venglisc
# Modified program to allow to selectively display images or a placeholder in
# the Summary QC reports. (Bug 4395)
#
# Revision 1.59  2008/11/07 17:13:27  venglisc
# Modified report to allow users to run the Redline/strikeout report for
# the old GlossaryTerm documents after the switch to GlossaryTermNames.
# (Bug 3035)
#
# Revision 1.58  2008/11/04 21:12:30  venglisc
# Minor changes to allow GlossaryTermName publish preview reports to be
# submitted from the Admin interface.
#
# Revision 1.57  2008/10/21 20:24:10  venglisc
# The user interface failed if no comment existed for a version. (Bug 4329)
#
# Revision 1.56  2008/09/30 21:10:36  venglisc
# Limiting display of version comment to first 150 characters. (Bug 4248)
#
# Revision 1.55  2008/09/30 20:44:46  venglisc
# Modifications to call an intermediate page for DrugInfoSummaries. (Bug 4248)
#
# Revision 1.54  2008/01/23 22:59:57  venglisc
# Added filter sets for GlossaryTermName and GlossaryTermConcept to run
# QC reports. (Bug 3699)
#
# Revision 1.53  2007/04/09 20:47:45  venglisc
# Modified to allow insertion/deletion markup for DrugInfoSummaries.
# (Bug 3067)
#
# Revision 1.52  2007/02/23 22:48:51  venglisc
# Modifications to display comments as internal and external comments within
# the summaries. (Bug 2920)
#
# Revision 1.51  2006/05/16 20:50:28  venglisc
# Adding filter set for DrugInfoSummary documents. (Bug 2053)
#
# Revision 1.50  2005/12/28 21:14:08  venglisc
# Adding code to allow Miscellaneous Document QC reports to be displayed with
# Redline/Strikeout markup. (Bug 1939)
#
# Revision 1.49  2005/10/20 20:54:29  venglisc
# Modified to include creating of GlossaryTerm Redline/Strikeout reports
# that allow the user to limit the output to a specified audience type
# (Health professional or Patient).  Bug 1868
#
# Revision 1.48  2005/07/01 19:29:45  venglisc
# Added new report type (repType) patbu for patient summary (bold/underline)
# and added patrs for patient summary (redline/strikeout).  The latter is
# identical to the repType 'pat' but has been added for consitend naming
# between the two report types. (Bug 1744)
#
# Revision 1.47  2005/06/02 19:48:20  venglisc
# Fixed code to pass a default for the displayBoard variable for patient
# summaries. (Bug 1707)
#
# Revision 1.46  2005/05/25 16:18:02  venglisc
# Added code to allow summary QC reports to be run with Editorial Board or
# Advisory Board mark-up. (Bug 1657)
# Modifications to CDR Admin Interface to allow specification of the
# individual board mark-up. (Bug 1555)
#
# Revision 1.45  2005/05/04 18:04:06  venglisc
# Added option for Media QC Report. (Bug 1653)
#
# Revision 1.44  2005/04/21 21:24:37  venglisc
# Modifications to allow PublishPreview QC reports. (Bug 1531)
#
# Revision 1.43  2005/02/24 21:06:55  venglisc
# Added coded to replace @@SESSION@@ string with the session id.  This
# allows to create a link in the Person QC documents to the Organization QC
# report or a particular org. (Bug 1545)
#
# Revision 1.42  2005/02/23 20:00:35  venglisc
# Made changes to replace two @@..@@ strings with results from database
# queries for the Organization QC report. (Bug 1516)
# Some additional changes are included to address PublishPreview changes
# which do not affect the Org reports.
#
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
    elif repType == "patrs":
        return "Patient Redline/Strikeout QC Report"
    elif repType == "patbu":
        return "Patient Bold/Underline QC Report"
    elif repType == "pp":
        return "Publish Preview Report"
    elif repType == "img":
        return "Media QC Report"
    elif repType == "gtnwc":
        return "Glossary Term Name With Concept Report"
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
images   = fields.getvalue("Images")     or None
citation = fields.getvalue("Citations")  or None
loe      = fields.getvalue("LOEs")       or None
standardWording = fields.getvalue("ShowStandardWording") or None
displayInternComments = fields.getvalue("DisplayInternalComments") or None
displayExternComments = fields.getvalue("DisplayExternalComments") or None
displayBoard    = fields.getvalue('Editorial-board') and 'editorial-board_' or ''
displayBoard   += fields.getvalue('Advisory-board')  and 'advisory-board'   or ''
displayAudience = fields.getvalue('Patient') and 'patient_' or ''
displayAudience +=fields.getvalue('HP')      and 'hp'       or ''
glossaryDefinition = fields.getvalue('GlossaryDefinition')

# insRevLvls  = fields.getvalue("revLevels")  or None
insRevLvls  = fields.getvalue("insRevLevels")  or None
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

# ---------------------------------------------------------------
# Passing a single parameter to the filter to decide if only the
# internal, external, all, or none of the comments should be
# displayed.
# ---------------------------------------------------------------
if not displayInternComments and not displayExternComments:
    displayComments = 'N'  # No comments
elif displayInternComments and not displayExternComments:
    displayComments = 'I'  # Internal comments only
elif not displayInternComments and displayExternComments:
    displayComments = 'E'  # External comments only (default)
else:
    displayComments = 'A'  # All comments

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
if not docId and not docTitle and not glossaryDefinition:
    extra = ""
    fieldName = 'DocTitle'
    if docType:
        extra += "<INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>" % docType
        if docType == 'PDQBoardMemberInfo':
           label = ['Board Member Name',
                    'Board Member CDR ID']
        elif docType == 'GlossaryTermConcept':
           label = ('Glossary Definition', 'CDR ID')
           fieldName = 'GlossaryDefinition'
        else:
           label = ['Document Title',
                    'Document CDR ID']

    if repType:
        extra += "\n   "
        extra += "<INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>" % repType
    form = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   %s
   <TABLE>
    <TR>
     <TD ALIGN='right'><B>%s:&nbsp;</B><BR/>(use %% as wildcard)</TD>
     <TD><INPUT SIZE='60' NAME='%s'></TD>
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
""" % (cdrcgi.SESSION, session, extra, label[0], fieldName, label[1])
    cdrcgi.sendPage(header + form + u"""\
  </FORM>
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
    form = u"""\
   <H3>More than one matching document found; please choose one.</H3>
"""
    for choice in choices:
        form += u"""\
   <INPUT TYPE='radio' NAME='DocId' VALUE='CDR%010d'>[CDR%d] %s<BR>
""" % (choice[0], choice[0], cgi.escape(choice[1]))
    cdrcgi.sendPage(header + form + u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, docType or '', repType or ''))

#----------------------------------------------------------------------
# If we have a document title (or glossary definition) but not a
# document ID, find the ID.
#----------------------------------------------------------------------
if not docId:
    lookingFor = 'title'
    try:
        if docType == 'GlossaryTermConcept':
            lookingFor = 'definition'
            cursor.execute("""\
                SELECT d.id, d.title
                  FROM document d
                  JOIN query_term q
                    ON d.id = q.doc_id
                 WHERE q.path IN ('/GlossaryTermConcept/TermDefinition' +
                                  '/DefinitionText',
                                  '/GlossaryTermConcept' +
                                  '/TranslatedTermDefinition/DefinitionText')
                   AND q.value LIKE ?""", u"%" + glossaryDefinition + u"%",
                           timeout = 300)
        elif docType:
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
            cdrcgi.bail("Unable to find document with %s '%s'" % (lookingFor,
                                                                  docTitle))
        if len(rows) > 1:
            showTitleChoices(rows)
        intId = rows[0][0]
        docId = "CDR%010d" % intId
    except cdrdb.Error, info:
        cdrcgi.bail('Failure looking up document %s: %s' % (lookingFor,
                                                            info[1][0]))

#----------------------------------------------------------------------
# We have a document ID.  Check added at William's request.
#----------------------------------------------------------------------
elif docType:
    cursor.execute(u"""\
        SELECT t.name
          FROM doc_type t
          JOIN document d
            ON d.doc_type = t.id
         WHERE d.id = ?""", intId)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("CDR%d not found" % intId)
    elif rows[0][0].upper() != docType.upper():
        cdrcgi.bail("CDR%d has document type %s" % (intId, rows[0][0]))
    
#----------------------------------------------------------------------
# Let the user pick the version for most Summary or Glossary reports.
#----------------------------------------------------------------------
letUserPickVersion = False
if not version:
    if docType in ('Summary', 'GlossaryTermName'):
        if repType and repType not in ('pp', 'gtnwc'):
            letUserPickVersion = True
    ### if docType in ('DIS', 'DrugInformationSummary'):
    if docType == 'DrugInformationSummary':
        letUserPickVersion = True
if letUserPickVersion:
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
    form = u"""\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='DocId' VALUE='CDR%010d'>
""" % (cdrcgi.SESSION, session, docType, intId)

    ### if docType != 'DIS':
    if docType != 'DrugInformationSummary':
        form += u"""\
  <INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>
""" % (repType)

    form += u"""\
  Select document version:&nbsp;<br>
  <SELECT NAME='DocVersion'>
   <OPTION VALUE='-1' SELECTED='1'>Current Working Version</OPTION>
"""

    # Limit display of version comment to 150 chars (if exists)
    # ---------------------------------------------------------
    for row in rows:
        form += u"""\
   <OPTION VALUE='%d'>[V%d %s] %s</OPTION>
""" % (row[0], row[0], row[2][:10],
       not row[1] and "[No comment]" or row[1][:150])
        selected = ""
    form += u"</SELECT>"
    form += u"""
  <BR><BR>
  Select Insertion/Deletion markup to be displayed in the report (one or more):
  <BR>
  <table width="60%" border="0">
   <tr>
"""
    # The Board Markup does not apply to the Patient Version Summaries
    # or the GlossaryTerm reports
    # ----------------------------------------------------------------
    if docType == 'Summary':
        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
    <td valign="top">
     <table>
      <tr>
       <td class="colheading">Board Markup</td>
      </tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "Editorial-board"
               CHECKED>&nbsp;&nbsp; Editorial board markup
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "Advisory-board">&nbsp;&nbsp; Advisory board markup
       </td>
      </tr>
     </table>
    </td>
"""
    # Display the check boxed for the Revision-level Markup
    # -----------------------------------------------------
    form += u"""\
    <td valign="top">
     <table>
      <tr>
       <td class="colheading">Revision-level Markup</td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE="checkbox" NAME="publish">&nbsp;&nbsp; With publish attribute
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE="checkbox" NAME="approved"
                         CHECKED='1'>&nbsp;&nbsp; With approved attribute<BR>
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE="checkbox" NAME="proposed">&nbsp;&nbsp; With proposed attribute
       </td>
      </tr>
     </table>
    </td>
   </tr>
  </table>
"""

    # Display the check boxes for the HP or Patient version sections
    # --------------------------------------------------------------
    if docType == 'GlossaryTermName':
        form += u"""\
     <table>
      <tr>
       <td class="colheading">Display Audience Definition</td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE="checkbox" NAME="HP"
                         CHECKED='1'>&nbsp;&nbsp; Health Professional
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE="checkbox" NAME="Patient"
                         CHECKED='1'>&nbsp;&nbsp; Patient<BR>
       </td>
      </tr>
    </table>
"""

    # Display the Comment display checkbox
    # Summaries display the External Comments by default
    # --------------------------------------------------
    if docType == 'Summary':
        form += u"""\
     <table>
      <tr>
       <td class="colheading">Display Comments and Responses</td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "DisplayInternalComments"
                            >&nbsp;&nbsp; Display Internal Comments
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "DisplayExternalComments"
               CHECKED = '1'>&nbsp;&nbsp; Display External Comments
       </td>
      </tr>
     </table>
"""

    # Display the Glossary appendix checkbox
    # --------------------------------------
    if docType == 'Summary':
        form += u"""\
  <BR>
     <table>
      <tr>
       <td class="colheading">Misc Print Options</td>
      </tr>
      <tr>
       <td>
  <INPUT TYPE='checkbox' NAME='Glossary'>&nbsp;&nbsp;
  Include glossary terms at end of report<BR>
       </td>
      </tr>
      <tr>
       <td>
  <INPUT TYPE='checkbox' NAME='Images'>&nbsp;&nbsp;
  Display images instead of placeholder<BR>
       </td>
      </tr>
      <tr>
       <td>
  <INPUT TYPE='checkbox' NAME='Citations' CHECKED>&nbsp;&nbsp;
  Display the HP Reference Section<BR>
       </td>
      </tr>
      <tr>
       <td>
  <INPUT TYPE='checkbox' NAME='LOEs'>&nbsp;&nbsp;
  Display Level of Evidence terms at end of report<BR>
       </td>
      </tr>
"""

    # Display the checkbox to display standard wording
    # ------------------------------------------------
    if repType == 'pat' or repType == 'patbu' or repType == 'patrs':
        form += u"""\
      <tr>
       <td>
  <INPUT TYPE='checkbox' NAME='ShowStandardWording'>&nbsp;&nbsp;
  Show standard wording with mark-up<BR>
       </td>
      </tr>
"""
    form += u"""
     </table>"""

    cdrcgi.sendPage(header + form + u"""
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Map for finding the filters for a given document type.
#----------------------------------------------------------------------
filters = {
    'Citation':
        ["set:QC Citation Set"],
    'CTGovProtocol':
        ["set:QC CTGovProtocol Set"],
    'DrugInformationSummary':
        ["set:QC DrugInfoSummary Set"],
    ### 'DIS':
    ###     ["set:QC DrugInfoSummary Set"],
    'GlossaryTerm':
        ["set:QC GlossaryTerm Set"],
    'GlossaryTerm:rs': # Redline/Strikeout
        ["set:QC GlossaryTerm Set (Redline/Strikeout)"],
    'GlossaryTermConcept':
        ["name:Glossary Term Concept QC Report Filter"],
    'GlossaryTermName':
        ["set:QC GlossaryTermName"],
    'GlossaryTermName:gtnwc':
        ["set:QC GlossaryTermName with Concept Set"],
    'InScopeProtocol':
        ["set:QC InScopeProtocol Set"],
    'Media:img':
        ["set:QC Media Set"],
    'MiscellaneousDocument':
        ["set:QC MiscellaneousDocument Set"],
    'MiscellaneousDocument:rs':
        ["set:QC MiscellaneousDocument Set (Redline/Strikeout)"],
    'Organization':
        ["set:QC Organization Set"],
    'Person':
        ["set:QC Person Set"],
    'PDQBoardMemberInfo':
        ["set:QC PDQBoardMemberInfo Set"],
    'Summary':
        ["set:QC Summary Set"],
    'Summary:bu':    # Bold/Underline
        ["set:QC Summary Set (Bold/Underline)"],
    'Summary:rs':    # Redline/Strikeout
        ["set:QC Summary Set"],
    'Summary:but':   # Bold/Underline
        ["set:QC Summary Set (Bold/Underline) Test"],
    'Summary:rst':   # Redline/Strikeout
        ["set:QC Summary Set Test"],
    'Summary:nm':    # No markup
        ["set:QC Summary Set"],
    'Summary:pat':   # Patient
        ["set:QC Summary Patient Set"],
    'Summary:patrs': # Patient
        ["set:QC Summary Patient Set"],
    'Summary:patbu': # Patient
        ["set:QC Summary Patient Set (Bold/Underline)"],
    'Term':
        ["set:QC Term Set"]
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
    # Determine the report type if the document is a summary.
    # Reformatted patient summaries contain a KeyPoint element
    # The element of the list creating the output is given as a string 
    # similar to this:  "Treatment Patients KeyPoint KeyPoint KeyPoint"
    # which will be used to set the propper report type for reformatted
    # patient summaries.
    #----------------------------------------------------------------------
    if docType == 'Summary':
        isPatient = hasKeyPoint = False
        inspectSummary = cdr.filterDoc(session, 
                  """<?xml version="1.0" ?> 
<xsl:transform version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
 <xsl:template          match = "Summary">
  <xsl:apply-templates select = "SummaryMetaData/SummaryAudience | 
                                 SummaryMetaData/SummaryType     |
                                 //KeyPoint"/>
 </xsl:template>

 <xsl:template          match = "SummaryAudience | SummaryType">
  <xsl:value-of        select = "."/>
  <xsl:text> </xsl:text>
 </xsl:template>

 <xsl:template          match = "KeyPoint">
  <xsl:text>KeyPoint</xsl:text>
  <xsl:text> </xsl:text>
 </xsl:template>
</xsl:transform>
                  """, inline = 1, 
                        docId = docId, docVer = version or None)
        if inspectSummary[0].find('Patients') > 0:  isPatient   = True
        if inspectSummary[0].find('KeyPoint') > 0:  hasKeyPoint = True

        if hasKeyPoint and isPatient:
            repType = 'pat'

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
    doc    = re.sub("@@SESSION@@",
                    session, doc)
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
    cdrcgi.navigateTo("PublishPreview.py", session, ReportType='pp',
                                                    DocId=docId)

    cdrcgi.sendPage(result.output)

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
if repType: docType += ":%s" % repType

# ---------------------------------------------------------------------
# The next two lines are needed to run the Media and Miscellaneaous QC
# reports from within XMetaL since the repType argument is not passed
# by the macro
# Note: The Misc. Document report should always be displayed with
#       markup if it exists.
# ---------------------------------------------------------------------
if docType == 'Media':                 docType += ":img"
if docType == 'MiscellaneousDocument': docType += ":rs"

if version == "-1": version = None

if not filters.has_key(docType):
    # cdrcgi.bail(filters)
    doc = cdr.getDoc(session, docId, version = version or "Current",
                     getObject = 1)
    if type(doc) in (type(""), type(u"")):
        cdrcgi.bail(doc)
    html = u"""\
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <pre>%s</pre>
 </body>
</html>""" % (doc.ctrl['DocTitle'], cgi.escape(doc.xml))
    cdrcgi.sendPage(html)
    #cdrcgi.sendPage(cdrcgi.unicodeToLatin1(html))

filterParm = []

# Setting the markup display level based on the selected check
# boxes.
# The DrugInfoSummaries are displayed without having to select the
# display type, therefore we need to set the revision level manually
# ------------------------------------------------------------------
if insRevLvls:
    filterParm = [['insRevLevels', insRevLvls]]
else:
    if docType == 'DrugInformationSummary':
        filterParm = [['insRevLevels', 'publish|approved|proposed']]

# Allow certain QC reports to succeed even without valid GlossaryLink
# -------------------------------------------------------------------
if docType == 'DrugInformationSummary' or docType == 'Media:img':
    filterParm.append(['isQC', 'Y'])

# Patient Summaries are displayed like editorial board markup
# -----------------------------------------------------------
if docType.startswith('Summary'):
    filterParm.append(['DisplayComments', displayComments ])
    if repType == 'pat' or repType == 'patrs' or repType == 'patbu':
        displayBoard += 'editorial-board_'
    filterParm.append(['displayBoard', displayBoard])

# Need to set the displayBoard parameter or all markup will be dropped
# --------------------------------------------------------------------
if docType.startswith('GlossaryTerm'):
    filterParm.append(['DisplayComments', displayComments ])
                       # displayComments and 'Y' or 'N'])
    filterParm.append(['displayBoard', 'editorial-board_'])
    filterParm.append(['displayAudience', displayAudience])

# Need to set the displayBoard and revision level parameter or all
# markup will be dropped
# --------------------------------------------------------------------
if docType.startswith('MiscellaneousDocument'):
    filterParm.append(['insRevLevels', 'approved|'])
    filterParm.append(['displayBoard', 'editorial-board_'])

if repType == "bu" or repType == "but":
    filterParm.append(['delRevLevels', 'Y'])

# Added GlossaryTermList to HP documents, not just patient.
filterParm.append(['DisplayGlossaryTermList',
                       glossary and "Y" or "N"])
filterParm.append(['DisplayImages',
                       images and "Y" or "N"])
filterParm.append(['DisplayCitations',
                       citation and "Y" or "N"])
filterParm.append(['DisplayLOETermList',
                       loe and "Y" or "N"])

if repType == 'pat' or repType == 'patrs' or repType == 'patbu':
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

# Replace all utf-8 unicode chars with &#x...; character entities
# Allows our macro substitutions to work without ascii decode errs
doc = cdrcgi.decode(doc)

# Perform any required macro substitions
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

# If not already changed to unicode by a fix.. routine, change it
if type(doc) != type(u""):
    doc = unicode(doc, 'utf-8')

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
