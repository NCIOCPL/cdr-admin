#-----------------------------------------------------------------------------
#
# $Id$
#
# Transform a CDR document using a QC XSL/T filter and send it back to
# the browser.
#
# BZIssue::4751 - Modify BU Report to display LOERef
# BZIssue::4672 - Changes to LinkedDoc Report
# BZIssue::4781 - Have certain links to unpublished docs ignored
# BZIssue::4967 - [Summary] Modification to QC Reports to Show/Hide 
#                 Certain Comments
# BZIssue::5006 - Minor Revisions to QC Report Interfaces - Comments Options
# BZIssue::5065 - [Summaries] 2 More Patient Summary QC Report Display Options
# BZIssue::5159 - [Summaries] Changes to HP & Patient QC Report Interfaces 
#                 and Display Options
# BZIssue::5229 - [CTGov] Missing Information In CTGov Protocol Full QC Report
# BZIssue::5249 - Standard wording in Patient QC report not displaying in green
# BZIssue::OCECDR-3630 - Patient Summary QC Reports Missing Reference Section
#
# ----------------------------------------------------------------------------
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
# Map for finding the filters for a given document type.
#----------------------------------------------------------------------
filters = cdr.FILTERS

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "CDR QC Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
docId    = fields.getvalue(cdrcgi.DOCID) or None ###'CDR360620' or None
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in") ### 'guest'
action   = cdrcgi.getRequest(fields)
qcParams = fields.getvalue('paramset') or '0'
title    = "CDR Administration"
repType  = fields.getvalue("ReportType") or None
section  = "QC Report"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, getSectionTitle(repType),
                         "QcReport.py", buttons, method = 'GET',
                         stylesheet = """
  <style type = 'text/css'>
    fieldset            { margin-bottom: 10px; }
    /* fieldset.docversion { width: 860px; */
    fieldset.docversion { width: 75%;
                          margin-left: auto;
                          margin-right: auto;
                          margin-bottom: 0; 
                          display: block; }
    fieldset.wrapper    { width: 520px;
                          margin-left: auto;
                          margin-right: auto;
                          display: block; }
    *.gogreen         { width: 95%;
                        border: 1px solid green;
                          background: #99FF66; }
    *.gg              { border: 1px solid green; 
                        background: #99FF66; 
                        color: #006600; }
    *.comgroup          { background: #C9C9C9; 
                          margin-bottom: 8px; }
  </style>

  <script language = 'JavaScript'>
     function dispInternal() {
         var checks  = ['ext', 'adv', 'allcomment', 'nocomment']
         if (document.getElementById('int').checked &&
             !document.getElementById('perm').checked) {
             var optionson = ['ai', 'se', 'sa', 'dr']
             var optionsoff = ['ae', 'dp']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (document.getElementById('int').checked &&
                  document.getElementById('perm').checked) {
             var optionson = ['ai', 'se', 'sa', 'dr', 'dp']
             var optionsoff = ['ae']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }

             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (!document.getElementById('int').checked &&
                  document.getElementById('perm').checked) {
             var optionson = ['ai', 'ae', 'se', 'sa', 'dp']
             var optionsoff = ['dr']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }

             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }


     function dispPermanent() {
         var checks  = ['ext', 'adv', 'allcomment', 'nocomment']
         if (document.getElementById('perm').checked &&
             !document.getElementById('int').checked) {
             var optionson = ['ai', 'ae', 'se', 'sa', 'dp']
             var optionsoff = ['dr']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (document.getElementById('perm').checked &&
                  document.getElementById('int').checked) {
             var optionson = ['ai', 'se', 'sa', 'dr', 'dp']
             var optionsoff = ['ae']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }

             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (!document.getElementById('perm').checked &&
                  document.getElementById('int').checked) {
             var optionson = ['ai', 'se', 'sa', 'dr']
             var optionsoff = ['ae', 'dp']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }

             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }


     function dispExternal() {
         var checks  = ['int', 'perm', 'allcomment', 'nocomment']
         if (document.getElementById('ext').checked &&
             !document.getElementById('adv').checked) {
             var optionson = ['ae', 'se', 'dp', 'dr']
             var optionsoff = ['ai', 'sa']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (document.getElementById('ext').checked &&
                  document.getElementById('adv').checked) {
             var optionson = ['ae', 'se', 'dp', 'dr']
             var optionsoff = ['ai', 'sa']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (!document.getElementById('ext').checked &&
                  document.getElementById('adv').checked) {
             var optionson = ['ai', 'ae', 'sa', 'dp', 'dr']
             var optionsoff = ['se']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }


     function dispAdvisory() {
         var checks  = ['int', 'perm', 'allcomment', 'nocomment']
         if (document.getElementById('adv').checked &&
             !document.getElementById('ext').checked) {
             var optionson = ['ai', 'ae', 'sa', 'dp', 'dr']
             var optionsoff = ['se']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (document.getElementById('adv').checked &&
                  document.getElementById('ext').checked) {
             var optionson = ['ae', 'se', 'sa', 'dp', 'dr']
             var optionsoff = ['ai']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (!document.getElementById('adv').checked &&
                  document.getElementById('ext').checked) {
             var optionson = ['ae', 'se', 'dp', 'dr']
             var optionsoff = ['ai', 'sa']
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var i in optionsoff) {
                 document.getElementById(optionsoff[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }


     function dispAll() {
         var optionson = ['ai', 'ae', 'se', 'sa', 'dp', 'dr']
         var checks  = ['int', 'perm', 'ext', 'adv', 'nocomment']
         if (document.getElementById('allcomment').checked) {
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = true;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }
     function dispNone() {
         var optionson = ['ai', 'ae', 'se', 'sa', 'dp', 'dr']
         var checks  = ['int', 'perm', 'ext', 'adv', 'allcomment']
         if (document.getElementById('nocomment').checked) {
             for (var i in optionson) {
                 document.getElementById(optionson[i]).checked = false;
             }
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }
     function showOptions(obj) {
         var el = document.getElementById(obj);
         if (el.style.display == 'none') {
             el.style.display = '';
         }
         else {
             el.style.display = 'none';
         }
     }
     function checkGreen() {
         var optgreen = ['dispImg', 'dispKP', 'dispLearnMore']
         for (var k in optgreen) {
           //  if (document.getElementById(optgreen[k]).checked == false) 
             if (document.getElementById('allGreen').checked == false) {
                 document.getElementById(optgreen[k]).checked = false;
             }
             else {
                 document.getElementById(optgreen[k]).checked = true;
             }
         }
     }
  </script>
""")
docType  = fields.getvalue("DocType")    or None
docTitle = fields.getvalue("DocTitle")   or None
version  = fields.getvalue("DocVersion") or None
glossary = fields.getvalue("Glossaries") or None
images   = fields.getvalue("Images")     or None
citation = fields.getvalue("CitationsHP") \
             or fields.getvalue("CitationsPat") or None
loe      = fields.getvalue("LOEs")       or None
qd       = fields.getvalue("QD")         or None
kpbox    = fields.getvalue("Keypoints")  or None
learnmore= fields.getvalue("LearnMore")  or None

standardWording      = fields.getvalue("StandardWording") or None
audInternComments    = fields.getvalue("AudInternalComments")  or None
audExternComments    = fields.getvalue("AudExternalComments")  or None
durPermanentComments = fields.getvalue("DurPermanentComments") or None
durRegularComments   = fields.getvalue("DurRegularComments")   or None
srcAdvisoryComments  = fields.getvalue("SrcAdvisoryComments")  or None
srcEditorComments    = fields.getvalue("SrcEditorComments")    or None

grp1Internal         = fields.getvalue("internal") or None
grp1Permanent        = fields.getvalue("permanent") or None
grp2External         = fields.getvalue("external") or None
grp2Advisory         = fields.getvalue("advisory") or None

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
# internal, external, all, or none of the audience comments 
# should be displayed.
# ---------------------------------------------------------------
if not audInternComments and not audExternComments:
    audienceComments = 'N'  # No comments
elif audInternComments and not audExternComments:
    audienceComments = 'I'  # Internal comments only
elif not audInternComments and audExternComments:
    audienceComments = 'E'  # External comments only (default)
else:
    audienceComments = 'A'  # All comments

# ---------------------------------------------------------------
# The source of a comment can be editorial or advisory
# ---------------------------------------------------------------
if not srcAdvisoryComments and not srcEditorComments:
    sourceComments = 'N'  # No comments
elif srcAdvisoryComments and not srcEditorComments:
    sourceComments = 'V'  # Advisory board comments only
elif not srcAdvisoryComments and srcEditorComments:
    sourceComments = 'E'  # Editorial board comments only (default)
else:
    sourceComments = 'A'  # All comments

# ---------------------------------------------------------------
# The duration of a comment can be normal or permanent
# ---------------------------------------------------------------
if not durPermanentComments and not durRegularComments:
    durationComments = 'N'  # No comments
elif durPermanentComments and not durRegularComments:
    durationComments = 'P'  # Permanent comments only
elif not durPermanentComments and durRegularComments:
    durationComments = 'R'  # External comments only (default)
else:
    durationComments = 'A'  # All comments

# ---------------------------------------------------------------
# In the case that two comment types should be combined (internal
# and permanent/external and advisory) we need to submit an 
# additional parameter to the filters.
# ---------------------------------------------------------------
if grp1Internal and grp1Permanent:
    includeExtPerm = 'Y'
else:
    includeExtPerm = 'N'

if grp2External and grp2Advisory:
    includeIntAdv  = 'Y'
else:
    includeIntAdv  = 'N'

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

# ---------------------------------------------------------------------
#
# ---------------------------------------------------------------------
def addCheckbox(inputLabels, inputName, inputID='', checked=0):
    if checked == 0:
       isChecked = ''
    else:
       isChecked = "checked='1'"

    cbHtml = u"""\
      <input name='%s' type='checkbox' id='%s'
             %s>&nbsp;
      <label for='%s'>%s</label>
      <br>
""" % (inputName, inputID, isChecked, inputID, inputLabels[inputName])
    return cbHtml

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
  <fieldset class='docversion'>
   <legend>&nbsp;Select document version&nbsp;</legend>
  <div style="width: 100%; text-align: center;">
  <div style="margin: 0 auto;">
  <SELECT NAME='DocVersion'>
   <OPTION VALUE='-1' SELECTED='1'>Current Working Version</OPTION>
"""

    # Limit display of version comment to 120 chars (if exists)
    # ---------------------------------------------------------
    for row in rows:
        form += u"""\
   <OPTION VALUE='%d'>[V%d %s] %s</OPTION>
""" % (row[0], row[0], row[2][:10],
       not row[1] and "[No comment]" or row[1][:120])
        selected = ""
    form += u"</SELECT></div></div>"
    form += u"""
  </fieldset>
  <BR>
  <fieldset class="wrapper">
   <legend>&nbsp;Select Insertion/Deletion markup to be displayed 
           (one or more)&nbsp;</legend>
"""
    # The Board Markup does not apply to the Patient Version Summaries
    # or the GlossaryTerm reports
    # ----------------------------------------------------------------
    if docType == 'Summary':
        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
     <fieldset>
      <legend>&nbsp;Board Markup&nbsp;</legend>
      <input name='Editorial-board' type='checkbox' id='eBoard'
                   checked='1'>
      <label for='eBoard'>Editorial board markup</label>
      <br>
      <input name='Advisory-board' type='checkbox' id='aBoard'>
      <label for='aBoard'>Advisory board markup</label>
     </fieldset>
"""
    # Display the check boxed for the Revision-level Markup
    # -----------------------------------------------------
    form += u"""\
    <td valign="top">
     <fieldset>
      <legend>&nbsp;Revision-level Markup&nbsp;</legend>
      <input name='publish' type='checkbox' id='pup'>
      <label for='pup'>With publish attribute</label>
      <br>
      <input name='approved' type='checkbox' id='app'
                   checked='1'>
      <label for='app'>With approved attribute</label>
      <br>
      <input name='proposed' type='checkbox' id='prop'>
      <label for='prop'>With proposed attribute</label>
     </fieldset>
  </fieldset>
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

# Start - Misc Print Options block
# ------------------------------------
    checkboxLabels = { 'CitationsPat':'Display Reference section',
                       'CitationsHP':'Display HP Reference section',
                       'Glossaries':'Display glossary terms at end of report',
                       'Images':'Display images',
                       'Keypoints':'Display Key Point boxes',
                       'LearnMore':
                            'Display To Learn More section',
                       'LOEs':
                            'Display Level of Evidence terms',
                       'StandardWording':
                            'Display standard wording with mark-up'
                 }

    # Display the Misc. Print Options check boxes for Patients
    # --------------------------------------------------------
    if docType == 'Summary':
        if repType == 'pat' or repType == 'patbu' or repType == 'patrs':
            form += u"""\
         <p>
         <fieldset>
          <legend>&nbsp;Misc Print Options&nbsp;</legend>
    """

            form += addCheckbox(checkboxLabels, 'Glossaries', 
                                inputID='displayGlossaries')
            form += addCheckbox(checkboxLabels, 'Images', 
                                inputID='displayImages', checked=0)
            form += addCheckbox(checkboxLabels, 'Keypoints', 
                                inputID='displayKeypoints', checked=1)
            form += addCheckbox(checkboxLabels, 'StandardWording', 
                                inputID='displayStandardWording')
            form += addCheckbox(checkboxLabels, 'CitationsPat', 
                                inputID='displayCitations', checked=1)
            form += addCheckbox(checkboxLabels, 'LearnMore', 
                                inputID='displayLearnMore', checked=1)

        # End - Misc Print Options block
        # ------------------------------
            form += u"""\
             </fieldset>
        """

    # Display the Comment display checkbox
    # Patient Summaries display the Internal Comments by default
    # Internal Option Grid:  X  X  O
    #                        O  X  X
    # HP Summaries display the External Comments by default
    # External Option Grid:  O  X  X
    #                        X  O  X
    # -----------------------------------------------------------
    if docType == 'Summary':
        form += u"""\
     <p>
     <fieldset>
      <legend>&nbsp;Select Comment Types to be displayed&nbsp;</legend>
      <div class='comgroup'>
      <input name='internal' type='checkbox' id='int'
"""
        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
"""
        else:
            form += u"""\
                   CHECKED="1"
"""
        form += u"""\
                   onclick='javascript:dispInternal()'>
      <label for='int'>Internal Comments (excluding permanent comments)</label>
      <br>
      <input name='permanent' type='checkbox' id='perm'
                   onclick='javascript:dispPermanent()'>
      <label for='perm'>Permanent Comments (internal & external)</label>
      </div>
"""
        # The users don't want the option for advisory-board comments
        # displayed for the patient summaries because these summaries 
        # are never reviewed by the advisory board.
        # In order to keep the code unchanged I'm just removing the 
        # option displayed but not those options that are actually
        # being checked by the JavaScript functions.
        # -----------------------------------------------------------
        # XXX
        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
      <div class='comgroup'>
      <input name='external' type='checkbox' id='ext'
                   CHECKED="1"
                   onclick='javascript:dispExternal()'>
      <label for='ext'>External Comments (excluding advisory comments)</label>
      <br>
      <input name='advisory' type='checkbox' id='adv'
                   onclick='javascript:dispAdvisory()'>
      <label for='adv'>Advisory Board Comments (internal & external)</label>
      </div>
"""
        else:
            form += u"""\
      <div class='comgroup'>
      <input name='external' type='checkbox' id='ext'
                   onclick='javascript:dispExternal()'>
      <label for='ext'>External Comments</label>
       <!-- I need the element as a hidden field so that I can use the same
            javascript functions for HP and Patient version -->
       <input name='advisory' type='hidden' id='adv'
                   onclick='javascript:dispAdvisory()'>
       </div>
      </div>
"""

        form += u"""\
      <div class='comgroup'>
      <input name='all' type='checkbox' id='allcomment'
                   onclick='javascript:dispAll()'>
      <label for='allcomment'>All Comments</label>
      <br>
      <input name='no' type='checkbox' id='nocomment'
                   onclick='javascript:dispNone()'>
      <label for='nocomment'>No Comments</label>
     </div>
     Click <a onclick="showOptions('hide');" title='More options'
              style="color: blue; text-decoration: underline;">here</a>
     for individual options ...
     </fieldset>
     <fieldset id='hide' style="display: none;">
     <table>
      <tr>
       <td class="colheading" 
           colspan="3">Display Comments and Responses 
                       (mark comment type to be displayed)</td>
      </tr>
      <tr>
       <td>
        <table>
      <tr>
       <td class="subheading">Audience (txt color)</td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "AudInternalComments"
"""

        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
"""
        else:
            form += u"""\
               CHECKED = "1"
"""

        form += u"""\
               ID      = "ai">&nbsp; Internal 
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "AudExternalComments"
"""

        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
               CHECKED = "1"
"""
        else:
            form += u"""\
"""

        form += u"""\
               ID      = "ae">&nbsp; External 
       </td>
       </tr>
       </table>
       </td>
       <td>
        <table>
      <tr>
       <td class="subheading">Source (txt spacing)</td>
      </tr>
         <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "SrcEditorComments"
               CHECKED = "1"
               ID      = "se">&nbsp; Not Advisory 
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "SrcAdvisoryComments"
"""

        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
"""
        else:
            form += u"""\
               CHECKED = "1"
"""

        form += u"""\
               ID      = "sa">&nbsp; Advisory 
       </td>
       </tr>
       </table>
       </td>
       <td>
        <table>
      <tr>
       <td class="subheading">Duration (background)</td>
      </tr>
         <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "DurPermanentComments"
"""

        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
               CHECKED = "1"
"""
        else:
            form += u"""\
"""

        form += u"""\
               ID      = "dp">&nbsp; Permanent 
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "DurRegularComments"
               CHECKED = "1"
               ID      = "dr">&nbsp; Non-permanent 
       </td>
       </tr>
       </table>
       </td>
      </tr>
     </table>
     </fieldset>
"""

    # Display the Misc. Print Options check boxes for HP
    # --------------------------------------------------
    if docType == 'Summary':
        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += u"""\
         <p>
         <fieldset>
          <legend>&nbsp;Misc Print Options&nbsp;</legend>
    """

            form += addCheckbox(checkboxLabels, 'Glossaries', 
                                inputID='displayGlossaries')
            form += addCheckbox(checkboxLabels, 'CitationsHP', 
                                inputID='displayCitations', checked=1)
            form += addCheckbox(checkboxLabels, 'Images', 
                                inputID='displayImages', checked=0)
            form += addCheckbox(checkboxLabels, 'LOEs', 
                                inputID='displayLOEs')

        # End - Misc Print Options block
        # ------------------------------
            form += u"""\
             </fieldset>
        """

    # Display the Quick&Dirty option checkbox
    # ---------------------------------------
    if docType == 'Summary':
        form += u"""\
  <p>
     <fieldset>
      <legend>&nbsp;911 Options&nbsp;</legend>
      &nbsp;<input name='QD' type='checkbox' id='dispQD'>&nbsp;
      <label for='dispQD'>Run Quick &amp; Dirty report</label>
      <br>
     </fieldset>"""
#    form += u"""
#     </table>"""

    cdrcgi.sendPage(header + form + u"""
 </BODY>
</HTML>
""")

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
if qd: docType += 'qd'

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
</html>""" % (doc.ctrl['DocTitle'], doc.xml.decode('utf-8'))
    cdrcgi.sendPage(html.encode('utf-8'))

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

# Supply the summary comments and board display parameters
# --------------------------------------------------------
if docType.startswith('Summary'):
    filterParm.append(['DisplayComments', audienceComments ])
    filterParm.append(['DurationComments', durationComments ])
    filterParm.append(['SourceComments', sourceComments ])
    filterParm.append(['IncludeExtPerm', includeExtPerm ])
    filterParm.append(['IncludeIntAdv', includeIntAdv ])

    # Patient Summaries are displayed like editorial board markup
    # -----------------------------------------------------------
    if repType == 'pat' or repType == 'patrs' or repType == 'patbu':
        displayBoard += 'editorial-board_'
    filterParm.append(['displayBoard', displayBoard])

# Need to set the displayBoard parameter or all markup will be dropped
# --------------------------------------------------------------------
if docType.startswith('GlossaryTerm'):
    filterParm.append(['DisplayComments', audienceComments ])
                       # audienceComments and 'Y' or 'N'])
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
    filterParm.append(['ShowKPBox',
                       kpbox and "Y" or "N"])
    filterParm.append(['ShowLearnMoreSection',
                       learnmore and "Y" or "N"])

# ----------------------------------------------------------------
# Saving QC report parameters in DB table
# ----------------------------------------------------------------
def saveParms(parms):
    parms.sort()
    try:
        cursor.execute("""\
     INSERT INTO url_parm_set( longURL) 
            VALUES (?)""", (repr(parms),))
        conn.commit()
        cursor.execute("""\
     SELECT max(id) from url_parm_set""")
        row = cursor.fetchone()

    except cdrdb.Error, info:
        cdrcgi.bail('Failure inserting parms: %s' % (info[1][0]))

    return row[0]


# Before filtering the document write the parameters to a DB
# table to access parameters for Word converstion
# ----------------------------------------------------------------
parmId = saveParms(filterParm)

docParms = ""
if docType.startswith('Summary'):
    docParms = "parmstring=yes&parmid=%s" % parmId

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

# cdrcgi.bail('%s - %s' % (docParms, type(docParms)))
#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc, parms=docParms, docId=docId, 
                     docType=docType, docVer=version)
