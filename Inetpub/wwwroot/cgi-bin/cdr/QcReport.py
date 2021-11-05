#-----------------------------------------------------------------------------
#
# Transform a CDR document using a QC XSL/T filter and send it back to
# the browser.
#
# BZIssue::545
# BZIssue::1119 - Query mod to avoid picking up PDQKey for orgs
# BZIssue::1054 - @@..@@ parameters for BoardMember QC report
# BZIssue::1050 - UI for running QC report from the menus
# BZIssue::1054 - Label change ("Date Received" -> "Date Response Received")
# BZIssue::1415 - Support list of glossary terms for HP summaries
# BZIssue::1516 - @@..@@ parameters for Org QC report
# BZIssue::1531 - Modifications to allow PublishPreview QC reports
# BZIssue::1545 - Enhance org links in person QC reports
# BZIssue::1555 - Form enhancement for controlling board markup selection
# BZIssue::1653 - Added option for Media QC Report
# BZIssue::1657 - Support Editorial Board/Advisory Board markup (summaries)
# BZIssue::1707 - Default displayBoard variable for patient summaries
# BZIssue::1744 - Added new summary report types (patbu and patrs)
# BZIssue::1868 - Audience filtering for GlossaryTerm redline/strikeout reports
# BZIssue::1939 - Redline/strikeout in Miscellaneous doc QA reports
# BZIssue::2053 - Added filter set for DrugInfoSummary (DIS) docs
# BZIssue::2920 - Internal/external comment display in summaries
# BZIssue::3067 - Support insertion/deletion markup for DIS docs
# BZIssue::3699 - Support new glossary term document types (concept and name)
# BZIssue::4248 - Truncate long version comments; DIS report mods
# BZIssue::4329 - Handle case where no comment exists for a version
# BZIssue::3035 - Redline/strikeout report for old GlossaryTerm docs
# BZIssue::4395 - Control image display in Summary QC report
# BZIssue;:4478 - Glossary Term Name with Concept QC report
# BZIssue::4562 - Added checkbox to suppress display of Reference sections
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
# JIRA::OCECDR-3800 - Address security vulnerabilities
# JIRA::OCECDR-3919 - Repair the ability to run publish preview for
#                     DrugInformationSummary. Turn off document version
#                     selection for DrugInformationSummary.
# JIRA::OCECDR-4191 - Summary Publish Preview should use current working doc
# JIRA::OCECDR-4190 - Let user pick version for DIS QC report
#
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
import os
import re
from cdrapi import db
from cdrapi.users import Session
from html import escape as html_escape

#----------------------------------------------------------------------
# Dynamically create the title of the menu section (request #809).
#----------------------------------------------------------------------
def getSectionTitle(repType):
    if not repType:
        return "QC Report"
    elif repType == "bu":
        return "HP Bold/Underline QC Report"
    elif repType == "but":
        return "HP Bold/Underline QC Report (Test)"
    elif repType == "rs":
        return "HP Redline/Strikeout QC Report"
    elif repType == "rst":
        return "HP Redline/Strikeout QC Report (Test)"
    elif repType == "nm":
        return "QC Report (No Markup)"
    elif repType == "pat":
        return "PT Redline/Strikeout QC Report"
    elif repType == "patrs":
        return "PT Redline/Strikeout QC Report"
    elif repType == "patbu":
        return "PT Bold/Underline QC Report"
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
debug    = fields.getvalue("debug") and True or False
if debug:
    os.environ["CDR_LOGGING_LEVEL"] = "DEBUG"
    cdr.LOGGER.setLevel("DEBUG")
cdr.LOGGER.debug("QcReport.py called with %s", dict(fields))
# cdrcgi.log_fields(fields, program='QcReport.py')
docId    = fields.getvalue(cdrcgi.DOCID) or None
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
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
    *.radio-button    { margin-left: 40px; }
    label:hover       { background-color: lightyellow; }
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
             el.style.display = 'block';
         }
         else {
             el.style.display = 'none';
         }
     }
     function selectImageVersion(obj) {
         // Display the radio button for selecting the version of image
         // to use if the checkbox gets selected.

         var checkBox = document.getElementById(obj);
         var radioBtn = document.getElementById('pub-image');
         if (checkBox.checked == true) {
             radioBtn.style.display = 'block';
         }
         else {
             radioBtn.style.display = 'none';
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
if docType: cdrcgi.valParmVal(docType, val_list=cdr.getDoctypes(session))
docTitle = fields.getvalue("DocTitle")   or None
version  = fields.getvalue("DocVersion") or None
if version: cdrcgi.valParmVal(version, regex=cdrcgi.VP_SIGNED_INT)
glossary = fields.getvalue("Glossaries") or None
images   = fields.getvalue("Images")     or None
pubImages = fields.getvalue("PubImages") or 'Y'
citation = fields.getvalue("CitationsHP") \
             or fields.getvalue("CitationsPat") or None
loe      = fields.getvalue("LOEs")       or None
qd       = fields.getvalue("QD")         or None
kpbox    = fields.getvalue("Keypoints")  or None
learnmore= fields.getvalue("LearnMore")  or None
modMarkup= fields.getvalue("ModuleMarkup")     or None
qcOnly   = fields.getvalue("QCOnlyMod")  or None

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

displayBoard  = fields.getvalue('Editorial-board') and 'editorial-board_' or ''
displayBoard += fields.getvalue('Advisory-board')  and 'advisory-board'   or ''
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

#----------------------------------------------------------------------
# Do some parameter scrubbing for OCECDR-3800.
#----------------------------------------------------------------------
if docType and re.search("\\W", docType):
    cdrcgi.bail("Invalid document type parameter")
if repType and re.search("\\W", repType):
    cdrcgi.bail("Invalid report type parameter")
# The version number -1 for the CWD is deprecated
if version and re.search("\\W", version) and int(version) not in (-1, 0):
    cdrcgi.bail("Invalid document version parameter")

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
    label = ["", ""]
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
    form = """\
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
    cdrcgi.sendPage(header + form + """\
  </FORM>
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = db.connect(user='CdrGuest', timeout=300)
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail(f"Database connection failure: {e}")

#----------------------------------------------------------------------
# More than one matching title; let the user choose one.
#----------------------------------------------------------------------
def showTitleChoices(choices):
    form = """\
   <H3>More than one matching document found; please choose one.</H3>
"""
    for choice in choices:
        form += """\
   <INPUT TYPE="radio" id="%d" NAME="DocId" VALUE="CDR%010d">
   <label for="%d">[CDR%06d] %s</label><BR>
""" % (choice[0], choice[0], choice[0], choice[0], 
       html_escape(choice[1]))
    cdrcgi.sendPage(header + form + """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, docType or '', repType or ''))

# ---------------------------------------------------------------------
# Adding a line to add on/off checkbox options
# ---------------------------------------------------------------------
def addCheckbox(inputLabels, inputName, inputID='', checked=0):
    isChecked = checked and "checked='1'" or ""
    showImages = ''

    # Adding on-click trigger when 'Images' are selected so that the
    # user can decide to include publishable versions of images or
    # non-publishable versions.
    # ---------------------------------------------------------------
    if inputName == 'Images':
       showImages = 'onclick="selectImageVersion(\'displayImages\')"'

    cbHtml = """\
      <input name='%s' type='checkbox' id='%s' %s
             %s>&nbsp;
      <label for='%s'>%s</label>
      <br>
""" % (inputName, inputID, showImages, isChecked, inputID,
       inputLabels[inputName])
    return cbHtml

# ---------------------------------------------------------------------
# Adding a set of radio buttons
# Users want to be able to display either the last publishable version
# of an image or the last version (if exists).
# The default is to display the last publishable version of the image.
# ---------------------------------------------------------------------
def addImageRadioBtn(inputLabels, inputName, inputID=''):
    id1 = 'pubYes'
    id2 = 'pubNo'
    cbHtml = """\
      <div id="pub-image" class="radio-button" style="display:none;">
       <input type='radio' name='%s' id='%s'
              value="Y" checked>&nbsp;
       <label for='%s'>%s</label>
       <br>
       <input type='radio' name='%s' id='%s'
              value="N" >&nbsp;
       <label for='%s'>%s</label>
       <br>
      </div>
""" % (inputName, id1, id1, inputLabels['PubImages'][id1],
       inputName, id2, id2, inputLabels['PubImages'][id2])
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
                   AND q.value LIKE ?""", "%" + glossaryDefinition + "%")
        elif docType:
            cursor.execute("""\
                SELECT document.id, document.title
                  FROM document
                  JOIN doc_type
                    ON doc_type.id = document.doc_type
                 WHERE doc_type.name = ?
                   AND document.title LIKE ?""", (docType, docTitle + '%'))
        else:
            # How can we get here???
            cursor.execute("""\
                SELECT id, title
                  FROM document
                 WHERE title LIKE ?""", docTitle + '%')
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find document with %s %s" %
                        (lookingFor, repr(docTitle)))
        if len(rows) > 1:
            showTitleChoices(rows)
        intId = rows[0][0]
        docId = "CDR%010d" % intId
    except Exception as e:
        cdrcgi.bail(f"Failure looking up document {lookingFor}: {e}")

#----------------------------------------------------------------------
# We have a document ID.  Check added at William's request.
#----------------------------------------------------------------------
elif docType:
    cursor.execute("""\
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
# OCECDR-4190: let the user pick the version for drug information summaries.
#
# Note: The QC report "Glossary Term Name with Concept" called from 
#       within XMetaL is running Filter.py instead of QcReport.py!!!
#       The CDR Admin interface is calling QcReport.py. This affects
#       the reportType "GlossaryTermName:gtnwc"
#----------------------------------------------------------------------
letUserPickVersion = False
if not version:
    if docType in ('Summary', 'GlossaryTermName'):
        if repType and repType not in ('pp', 'gtnwc'):
            letUserPickVersion = True
    if docType == "DrugInformationSummary":
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
    except Exception as e:
        cdrcgi.bail(f"Failure retrieving document versions: {e}")
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='DocType' VALUE='%s'>
  <INPUT TYPE='hidden' NAME='DocId' VALUE='CDR%010d'>
""" % (cdrcgi.SESSION, session, docType, intId)

    if debug:
        form += '  <input type="hidden" name="debug" value="yes, please">\n'

    # Include the ReportType so the "DocumentVersion" screen can differentiate
    # the specific report type to run.
    form += """\
  <INPUT TYPE='hidden' NAME='ReportType' VALUE='%s'>
""" % (repType or "")

    form += """\
  <fieldset class='docversion'>
   <legend>&nbsp;Select document version&nbsp;</legend>
  <div style="width: 100%; text-align: center;">
  <div style="margin: 0 auto;">
  <SELECT NAME='DocVersion'>
   <OPTION VALUE='0' SELECTED='1'>Current Working Version</OPTION>
"""

    # Limit display of version comment to 120 chars (if exists)
    # ---------------------------------------------------------
    for row in rows:
        form += """\
   <OPTION VALUE='%d'>[V%d %s] %s</OPTION>
""" % (row[0], row[0], str(row[2])[:10],
       not row[1] and "[No comment]" or html_escape(row[1][:120]))
        selected = ""
    form += "</SELECT></div></div>"
    form += """
  </fieldset>
"""
    if docType in ("Summary", "DrugInformationSummary", "GlossaryTermName"):
        form += """\
  <BR>
  <fieldset class="wrapper">
   <legend>&nbsp;Select Insertion/Deletion markup to be displayed
           (one or more)&nbsp;</legend>
"""
        # The Board Markup does not apply to the Patient Version Summaries
        # or the DrugInfoSummary or GlossaryTerm reports
        # ----------------------------------------------------------------
        if docType == 'Summary':
            if repType not in ("pat", "patbu", "patrs"):
                form += """\
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
        # XXX WHAT IS THIS <TD> TAG DOING???
        # -----------------------------------------------------
    ### <td valign="top">
        form += """\
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
        form += """\
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
                       'Images':'Display images ...',
                       'Keypoints':'Display Key Point boxes',
                       'LearnMore':
                            'Display To Learn More section',
                       'LOEs':
                            'Display Level of Evidence terms',
                       'StandardWording':
                            'Display standard wording with mark-up',
                       'ModuleMarkup':
                            'Display Modules Shaded',
                       'QCOnlyMod':
                            'Display QC-only Modules'
                 }

    radioBtnLabels = { 'PubImages':{'pubYes':'... use publishable version',
                                    'pubNo':'... use non-publishable version'}
                 }

    # Display the Misc. Print Options check boxes for Patients
    # --------------------------------------------------------
    if docType == 'Summary':
        if repType == 'pat' or repType == 'patbu' or repType == 'patrs':
            form += """\
         <p>
         <fieldset>
          <legend>&nbsp;Misc Print Options&nbsp;</legend>
    """

            form += addCheckbox(checkboxLabels, 'Glossaries',
                                inputID='displayGlossaries')
            form += addCheckbox(checkboxLabels, 'Images',
                                inputID='displayImages', checked=0)
            form += addImageRadioBtn(radioBtnLabels, 'PubImages',
                                inputID='displayPubImages')
            form += addCheckbox(checkboxLabels, 'Keypoints',
                                inputID='displayKeypoints', checked=1)
            form += addCheckbox(checkboxLabels, 'StandardWording',
                                inputID='displayStandardWording')
            form += addCheckbox(checkboxLabels, 'CitationsPat',
                                inputID='displayCitations', checked=1)
            form += addCheckbox(checkboxLabels, 'LearnMore',
                                inputID='displayLearnMore', checked=1)
            form += addCheckbox(checkboxLabels, 'ModuleMarkup',
                                inputID='displayModuleMarkup')
            form += addCheckbox(checkboxLabels, 'QCOnlyMod',
                                inputID='displayQCOnlyMod', checked=0)

        # End - Misc Print Options block
        # ------------------------------
            form += """\
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
        form += """\
     <p>
     <fieldset>
      <legend>&nbsp;Select Comment Types to be displayed&nbsp;</legend>
      <div class='comgroup'>
      <input name='internal' type='checkbox' id='int'
"""
        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += """\
"""
        else:
            form += """\
                   CHECKED="1"
"""
        form += """\
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
            form += """\
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
            form += """\
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

        form += """\
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
            form += """\
"""
        else:
            form += """\
               CHECKED = "1"
"""

        form += """\
               ID      = "ai">&nbsp; Internal
       </td>
      </tr>
      <tr>
       <td>
        <INPUT TYPE    = "checkbox"
               NAME    = "AudExternalComments"
"""

        if repType != 'pat' and repType != 'patbu' and repType != 'patrs':
            form += """\
               CHECKED = "1"
"""
        else:
            form += """\
"""

        form += """\
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
            form += """\
"""
        else:
            form += """\
               CHECKED = "1"
"""

        form += """\
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
            form += """\
               CHECKED = "1"
"""
        else:
            form += """\
"""

        form += """\
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
            form += """\
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
            form += addImageRadioBtn(radioBtnLabels, 'PubImages',
                                inputID='displayPubImages')
            form += addCheckbox(checkboxLabels, 'LOEs',
                                inputID='displayLOEs')
            form += addCheckbox(checkboxLabels, 'ModuleMarkup',
                                inputID='displayModuleMarkup', checked=0)
            form += addCheckbox(checkboxLabels, 'QCOnlyMod',
                                inputID='displayQCOnlyMod', checked=0)

        # End - Misc Print Options block
        # ------------------------------
            form += """\
             </fieldset>
        """

    # Display the Quick&Dirty option checkbox
    # ---------------------------------------
    if docType == 'Summary':
        form += """\
  <p>
     <fieldset>
      <legend>&nbsp;911 Options&nbsp;</legend>
      &nbsp;<input name='QD' type='checkbox' id='dispQD'>&nbsp;
      <label for='dispQD'>Run Quick &amp; Dirty report</label>
      <br>
     </fieldset>"""
#    form += """
#     </table>"""

    cdrcgi.sendPage(header + form + """
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
    except Exception as e:
            cdrcgi.bail(f"Unable to find document type for {docId}: {e}")

    #----------------------------------------------------------------------
    # Determine the report type if the document is a summary.
    # The resulting text output is given as a string similar to this:
    #      "Treatment Patients KeyPoint KeyPoint KeyPoint"
    # which will be used to set the propper report type for patient or HP
    #
    # In the past there used to be new (including KeyPoints) and old (not
    # including KeyPoints) summaries and the old versions had to use HP
    # QC report filters.
    #----------------------------------------------------------------------
    if docType == 'Summary':
        inspectSummary = cdr.filterDoc(session,
                  """<?xml version="1.0" ?>
<xsl:transform version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
 <xsl:template          match = "Summary">
  <xsl:apply-templates select = "SummaryMetaData/SummaryAudience"/>
 </xsl:template>

 <xsl:template          match = "SummaryAudience">
  <xsl:value-of        select = "."/>
  <xsl:text> </xsl:text>
 </xsl:template>
</xsl:transform>""", inline = 1, docId = docId, docVer = version or None)

        if "Patients" in inspectSummary[0]:
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
        #cursor.callproc('cdr_get_count_of_links_to_persons', docId)
        parms = (docId,)
        cursor.execute("{CALL cdr_get_count_of_links_to_persons (?)}", parms)
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

    except Exception as e:
        cdrcgi.bail(f"Failure retrieving link counts: {e}")
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
    except Exception as e:
        cdrcgi.bail(f"Failure retrieving mailer info for {docId}: {e}")

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

# #----------------------------------------------------------------------
# # Plug in last update info for CTGovProtocol.
# #----------------------------------------------------------------------
# def fixCTGovProtocol(doc):
#     cursor.execute("""\
#     SELECT TOP 1 t.dt, u.name
#       FROM audit_trail t
#       JOIN action a
#         ON a.id = t.action
#       JOIN usr u
#         ON u.id = t.usr
#      WHERE a.name = 'MODIFY DOCUMENT'
#        AND u.name <> 'CTGovImport'
#        AND t.document = ?
#   ORDER BY t.dt DESC""", intId)
#     row = cursor.fetchone()
#     if row:
#         doc = doc.replace("@@UPDATEDBY@@", row[1])
#         doc = doc.replace("@@UPDATEDDATE@@", row[0][:10])
#     else:
#         doc = doc.replace("@@UPDATEDBY@@", "&nbsp;")
#         doc = doc.replace("@@UPDATEDDATE@@", "&nbsp;")
#     #cdrcgi.bail("NPI=" + noPdqIndexing)
#     return doc.replace("@@NOPDQINDEXING@@", noPdqIndexing)


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
    except Exception as e:
        cdrcgi.bail(f"Failure retrieving Protocol info for {intId:d}: {e}")

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

    except Exception as e:
        cdrcgi.bail(f"Failure retrieving Person ID for {intId:d}: {e}")

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

    except Exception as e:
        cdrcgi.bail(f"Failure retrieving Summary info for CDR{intId:d}: {e}")

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

    # XXX Where's the path clause for query_term summary???
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
    except Exception as e:
        message = f"Failure retrieving Mailer info for batch ID {batchId}: {e}"
        cdrcgi.bail(message)

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
""" % (html_escape(row[4]), row[3])
    doc = re.sub("@@SUMMARY_MAILER_SENT@@", html, doc)

    # -----------------------------------------------------------------
    # Database query to select the time of the mailers send
    # -----------------------------------------------------------------
    try:
        query = """\
SELECT completed
  FROM pub_proc
 WHERE id = %d""" % batchId
        cursor.execute(query)

    except Exception as e:
        message = f"Failure retrieving Mailer Date for batch {batchId:d}: {e}"
        cdrcgi.bail(message)

    row = cursor.fetchone()
    # -----------------------------------------------------------------
    # Substitute @@...@@ strings for job ID and date send
    # If the person is not linked to a summary we won't find an entry
    # in the pub_proc table.  The batchId will have been set to zero
    # in this case.
    # -----------------------------------------------------------------
    if row:
       dateSent = str(row[0])[:10]
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
# OCECDR-4191: Summary Publish Preview should always show CWD
# --------------------------------------------------------------------
if repType == "pp":
    args = { "ReportType": "pp", "DocId": docId }
    if docType == "Summary":
        args["Version"] = "cwd"
    cdrcgi.navigateTo("PublishPreview.py", session, **args)

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

# -1 is deprecated but some scripts may still use it
if version in ("-1", "0"): version = None

# Display error message if no filter exist for current docType
# ------------------------------------------------------------
if docType not in filters:
    user_name = Session(session).user_name
    message = "QcReport - Filter for document type '%s' does not exist (%s)."
    cdr.LOGGER.info(message, docType, user_name)
    doc = cdr.getDoc(session, docId, version = version or "Current",
                     getObject = 1)
    if isinstance(doc, (str, bytes)):
        cdrcgi.bail(doc)
    html = """\
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <h3 style="color: red;">Filter for document type
    <b>'%s'</b> does not exist.</h3>
  <p>Document follows (view source to preview XML!):</p>
  <pre>%s</pre>
 </body>
</html>""" % (html_escape(doc.ctrl['DocTitle'].decode("utf-8")), docType,
              html_escape(doc.xml.decode('utf-8')))
    cdrcgi.sendPage(html)

filterParm = []

# Setting the markup display level based on the selected check
# boxes.
# # The DrugInfoSummaries are displayed without having to select the
# # display type, therefore we need to set the revision level manually
# ------------------------------------------------------------------
if insRevLvls:
    filterParm = [['insRevLevels', insRevLvls]]
# else:
#     if docType == 'DrugInformationSummary':
#         filterParm = [['insRevLevels', 'publish|approved|proposed']]

# Allow certain QC reports to succeed even without valid GlossaryLink
# -------------------------------------------------------------------
if docType == 'DrugInformationSummary' or docType == 'Media:img':
    filterParm.append(['isQC', 'Y'])

# Force the display of comments for DIS.  All comments should be
# displayed and all attributes should be ignored.
# ---------------------------------------------------------------
if docType == 'DrugInformationSummary':
    filterParm.append(['DisplayComments', 'A' ])

# Supply the summary comments and board display parameters
# --------------------------------------------------------
if docType.startswith('Summary'):
    filterParm.append(['isQC', 'Y'])
    filterParm.append(['DisplayComments', audienceComments ])
    filterParm.append(['DurationComments', durationComments ])
    filterParm.append(['SourceComments', sourceComments ])
    filterParm.append(['IncludeExtPerm', includeExtPerm ])
    filterParm.append(['IncludeIntAdv', includeIntAdv ])
    filterParm.append(['DisplayModuleMarkup', modMarkup and 'Y' or 'N'])
    filterParm.append(['DisplayQcOnlyMod', qcOnly and 'Y' or 'N'])

    # Patient Summaries are displayed like editorial board markup
    # -----------------------------------------------------------
    if repType == 'pat' or repType == 'patrs' or repType == 'patbu':
        displayBoard += 'editorial-board_'
    filterParm.append(['displayBoard', displayBoard])

# Need to set the displayBoard parameter or all markup will be dropped
# --------------------------------------------------------------------
if docType.startswith('GlossaryTerm'):
    filterParm.append(['isQC', 'Y'])
    filterParm.append(['DisplayComments', audienceComments ])
                       # audienceComments and 'Y' or 'N'])
    filterParm.append(['displayBoard', 'editorial-board_'])
    filterParm.append(['displayAudience', displayAudience])

# Need to set the displayBoard and revision level parameter or all
# markup will be dropped
# --------------------------------------------------------------------
if docType.startswith('MiscellaneousDocument'):
    filterParm.append(['isQC', 'Y'])
    filterParm.append(['insRevLevels', 'approved|'])
    filterParm.append(['displayBoard', 'editorial-board_'])

if repType == "bu" or repType == "but":
    filterParm.append(['delRevLevels', 'Y'])

# Added GlossaryTermList to HP documents, not just patient.
filterParm.append(['DisplayGlossaryTermList',
                       glossary and "Y" or "N"])
filterParm.append(['DisplayImages',
                       images and "Y" or "N"])
if images:
    filterParm.append(['DisplayPubImages', pubImages ])
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

    except Exception as e:
        cdrcgi.bail(f"Failure inserting parms: {e}")

    return row[0]


# Before filtering the document write the parameters to a DB
# table to access parameters for Word converstion
# ----------------------------------------------------------------
parmId = saveParms(filterParm)

docParms = ""
if docType.startswith('Summary'):
    docParms = "parmstring=yes&parmid=%s" % parmId

try:
    doc = cdr.filterDoc(session, filters[docType], docId = docId,
                        docVer = version or None, parm = filterParm)
except Exception as e:
    cdrcgi.bail("filtering error: {}".format(e))

if isinstance(doc, (str, bytes)):
    cdrcgi.bail(doc)
doc = doc[0]

if docType == "CTGovProtocol":
    if isinstance(doc, bytes):
        doc = str(doc, "utf-8")
    if isinstance(doc, str) and "undefined/lastp" in doc:
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
# elif docType == 'CTGovProtocol':
#     doc = fixCTGovProtocol(doc)
elif docType == 'PDQBoardMemberInfo':
    doc = fixBoardMemberReport(doc)
# cdrcgi.bail("docType = %s" % docType)

# If not already changed to unicode by a fix.. routine, change it
if isinstance(doc, bytes):
    doc = str(doc, 'utf-8')

# cdrcgi.bail('%s - %s' % (docParms, type(docParms)))
#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
args = docId, version, docType, docParms
cdr.LOGGER.info("QC for %s version %s type %s with parms %s", *args)
cdrcgi.sendPage(doc, parms=docParms, docId=docId,
                     docType=docType, docVer=version)
