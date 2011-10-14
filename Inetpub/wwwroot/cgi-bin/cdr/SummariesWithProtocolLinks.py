#----------------------------------------------------------------------
#
# $Id: SummariesWithProtocolLinks.py
#
# Report on lists of summaries.
#
# BZIssue::4744 - Modify Summaries with Protocol Links/Refs report
# BZIssue::4865 - Summaries with Protocol Links/Refs report bug 
# BZIssue::5120 - Missing Text from protocol ref report
#
#----------------------------------------------------------------------
import sys, cgi, cdr, cdrcgi, re, string, cdrdb, time, ExcelWriter
import xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
if not session: session = 'CdrGuest'
lang        = fields and fields.getvalue("lang")             or ''
groups      = fields and fields.getvalue("grp")              or []
statuses    = fields and fields.getvalue("status")           or []
submit      = fields and fields.getvalue("SubmitButton")     or None
cdrId       = fields and fields.getvalue("cdrid")            or ''
docTitle    = fields and fields.getvalue("title")            or None
revFrom     = fields and fields.getvalue("reviewedfrom")     or None
revTo       = fields and fields.getvalue("reviewedto")       or None
excludeDate = fields and fields.getvalue("exclude")          or 'Yes'
displayAll  = fields and fields.getvalue("displayall")       or 'Yes'
doExcel     = fields and fields.getvalue("doexcel")          or 'No'
request     = cdrcgi.getRequest(fields)
title       = "CDR Administration"
instr       = "Summaries With Protocol Links/Refs Report"
script      = "SummariesWithProtocolLinks.py"
SUBMENU     = "Report Menu"
buttons     = (SUBMENU, cdrcgi.MAINMENU)

#---------------------------
# DEBUG SETTINGS
#---------------------------
# lang = 'English'
# groups.append('Genetics')
# statuses.append('Completed')
# statuses.append('Closed')
# session   = 'guest'
# docId = 62855
#----------------------------------------------------------------------
# Class to collect all information related to a single ProtocolRef/Link
# element.
# ----------------------------------------------------------------------
class dataRow:
    def __init__(self, cdrid, summaryTitle, summarySecTitle, ref, protCDRID,
                 status, excelOutput = 'No'):
        self.cdrid = cdrid
        self.summaryTitle = summaryTitle
        self.summarySecTitle = summarySecTitle
        self.ref = ref
        self.protCDRID = protCDRID
        self.linkcdrid = cdr.normalize(protCDRID)
        self.status = status
        self.linkComment      = ''
        self.linkDate         = ''
        self.linkStatus       = ''
        self.protocolLink     = ''
        self.fullProtocolLink = ''
        self.text             = ''
        self.refTextStart     = 0
        self.refTextSize      = 0
        if excelOutput == 'Yes':
            self.excelOutput = True
        else:
            self.excelOutput = False
    
    def addProtocolLink(self,parentElem):
        self.text = ''
        self.addText(parentElem,0)
        self.fullProtocolLink = self.text
        self.protocolLink = self.reduceTo(self.fullProtocolLink,200)

    def addText(self,parentElem,bInLink):
        binlink = 0
        for parentChildNode in parentElem.childNodes:
            if parentChildNode.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
                if parentChildNode.attributes.length > 0:
                    for (name,value) in parentChildNode.attributes.items():
                        href = ''
                        if self.ref == 'LINK':
                            if name == 'cdr:ref':
                                if value == self.linkcdrid:
                                    binlink = 1
                                    # Don't display the link in Excel format
                                    if not self.excelOutput:
                                        href = "<a target='_blank' href = %s/QcReport.py?DocId=%s&Session=%s>" % (cdrcgi.BASE,self.linkcdrid,session)
                                    self.refTextStart = len(self.text)
                                    self.refTextSize = len(href)
                                    self.text += href
                        elif self.ref == 'REF':
                            if name == 'cdr:href':
                                if value == self.linkcdrid:
                                    binlink = 1
                                    # Don't display the link in Excel format
                                    if not self.excelOutput:
                                        href = "<a target='_blank' href = %s/QcReport.py?DocId=%s&Session=%s>" % (cdrcgi.BASE,self.linkcdrid,session)
                                    self.refTextStart = len(self.text)
                                    self.refTextSize = len(href)
                                    self.text += href
                                
            if parentChildNode.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                self.text += parentChildNode.nodeValue + " "
                if bInLink == 1:
                    bInLink = 0
                    self.refTextSize += len(parentChildNode.nodeValue)
                    # Don't display the link in Excel format
                    if not self.excelOutput:
                        self.text += "</a>"
            self.addText(parentChildNode,binlink)
            binlink = 0

    # Reduce the text to display on the report to a certain number of 
    # characters.  The number is passed as a parameter 
    # ---------------------------------------------------------------
    def reduceTo(self,text,count):
        startIndex = self.refTextStart - count
        if startIndex < 0:
            startIndex = 0;
        endIndex = self.refTextStart + self.refTextSize + count
        if endIndex > len(text) - 1:
            endIndex = len(text) - 1

        returnText = ''
        if startIndex > 0:
           returnText = '...'
        returnText += text[startIndex:endIndex]
        if endIndex < len(text) - 1:
            returnText += '...'

        return returnText


# ---------------------------------------------------------------------
# Function to determine if the LastReviewed date of the current 
# ProtocolRef/Link is within the given date range and needs to be 
# displayed or not.
# ---------------------------------------------------------------------
def displayRow(startdate, enddate, linkDate, exclude = 'Yes'):
    # If no linkDate exists print this row
    if not linkDate: 
        return False

    # Test if the date format is correct.  Return if it isn't
    # -------------------------------------------------------
    try:
        dateTest = time.strptime(linkDate, '%Y-%m-%d')
    except:
        return False
        

    # If the linkDate is within the date range and the exclude flag has
    # been set to 'Yes' -- don't print the row
    # If the linkDate is within the date range and the exclude flag has 
    # been set to 'No'  -- print the row
    # -----------------------------------------------------------------
    if exclude == 'Yes':
        if (time.strptime(startdate, '%Y-%m-%d') <= 
                time.strptime(linkDate, '%Y-%m-%d')
            and
            time.strptime(enddate, '%Y-%m-%d')   >= 
                time.strptime(linkDate, '%Y-%m-%d')):
            return True
        else:
            return False
    else:
        if (time.strptime(startdate, '%Y-%m-%d') <= 
                time.strptime(linkDate, '%Y-%m-%d')
            and
            time.strptime(enddate, '%Y-%m-%d')   >= 
                time.strptime(linkDate, '%Y-%m-%d')):
            return False
        else:
            return True

    return False


# ---------------------------------------------------------------------
# Function to determine if the current status has changed compared 
# with the last status.  We want to suppress displaying records for 
# which the protocol status has not changed.
# ---------------------------------------------------------------------
def hasStatusChanged(currentStatus, lastStatus):
    # Check if the current Protocol status has changed
    if not string.upper(currentStatus) == string.upper(lastStatus):
        return True
    else:
        return False

    return False


# -------------------------------------------------
# Create the table row for the table output
# -------------------------------------------------
def addExcelTableRow(row):
    """Return the Excel code to display a row of the report"""

    exRow.addCell(1, row.cdrid)
    exRow.addCell(2, row.summaryTitle)
    exRow.addCell(3, row.summarySecTitle)
    exRow.addCell(4, row.ref + ': ' + row.protocolLink)
    exRow.addCell(5, row.protCDRID)
    exRow.addCell(6, row.status)
    exRow.addCell(7, row.linkComment)
    exRow.addCell(8, row.linkDate)
    exRow.addCell(9, row.linkStatus)

    return


#----------------------------------------------------------------------
# If the user only picked one summary group, put it into a list so we
# can deal with the same data structure whether one or more were
# selected. Ditto for statuses.
#----------------------------------------------------------------------
if type(groups) in (type(""), type(u"")):
    groups = [groups]
if type(statuses) in (type(""), type(u"")):
    statuses = [statuses]

if docTitle and docTitle.startswith('Enter'): docTitle = None
if cdrId    and cdrId.startswith('Enter'):    cdrId    = None
if revFrom  and revFrom.startswith('Select'): revFrom  = None
if revTo    and revTo.startswith('Select'):   revTo    = None

if cdrId:
    try:
        docId = cdr.exNormalize(cdrId)[1]
    except ValueError:
        docId = None
else:
    docId = None

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y")

jscript = """
<style type="text/css">
body {
    font-family: sans-serif;
    font-size: 11pt;
    }
legend  {
    font-weight: bold;
    color: teal;
    font-family: sans-serif;
    }
fieldset {
    width: 500px;
    margin-left: auto;
    margin-right: auto;
    display: block;
    }
p.title {
    font-family: sans-serif;
    font-size: 11pt;
    font-weight: bold;
    }
*.tablecenter {
    margin-left: auto;
    margin-right: auto;
    }
*.CdrDateField {
    width: 100px;
    }
*.mittich {
    width: 50px; 
    margin-left: auto;
    margin-right: auto;
    display: block;
    }
td.top {
    vertical-align: text-top;
    }
</style>

<link   type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
<script type='text/javascript' language='JavaScript' src='/js/CdrCalendar.js'></script>

<script type='text/javascript' language='JavaScript' src='/js/scriptaculous/prototype.js'></script>
<script type='text/javascript' language='JavaScript' src='/js/scriptaculous/scriptaculous.js'></script>
<script type='text/javascript'>

Event.observe(window, 'load', function(){
    checkAllEnglish(0);
    checkAllSpanish(0);
    checkAllStatus(0);
    $('All English').checked = 1;
    $('All Status').checked = 1;
    $('English').checked = 1;
});

function isEnglishItemChecked(){
    return ($('All English').checked ||
    $('Adult Treatment').checked ||
    $('Genetics').checked ||
    $('Complementary and Alternative Medicine').checked  ||
    $('Pediatric Treatment').checked ||
    $('Screening and Prevention').checked ||
    $('Supportive Care').checked);
}

function isSpanishItemChecked(){
    return($('All Spanish').checked ||
    $('Spanish Adult Treatment').checked ||
    $('Spanish Pediatric Treatment').checked ||
    $('Spanish Supportive Care').checked);
}

function isStatusItemChecked(){
    return($('All Status').checked ||
    $('Active').checked ||
    $('Approved-not yet active').checked ||
    $('Enrolling by invitation').checked ||
    $('Temporarily closed').checked ||
    $('Closed').checked ||
    $('Completed').checked ||
    $('Withdrawn').checked ||
    $('Withdrawn from PDQ').checked);
}

function checkAllEnglish(checked){
    $('All English').checked = checked;
    $('Adult Treatment').checked = checked;
    $('Genetics').checked = checked;
    $('Complementary and Alternative Medicine').checked = checked;
    $('Pediatric Treatment').checked = checked;
    $('Screening and Prevention').checked = checked;
    $('Supportive Care').checked = checked;    
}

function checkAllSpanish(checked){
    $('All Spanish').checked = checked;
    $('Spanish Adult Treatment').checked = checked;
    $('Spanish Pediatric Treatment').checked = checked;
    $('Spanish Supportive Care').checked = checked;
}

function checkAllStatus(checked){
    $('All Status').checked = checked;
    $('Active').checked = checked;
    $('Approved-not yet active').checked = checked;
    $('Enrolling by invitation').checked = checked;
    $('Temporarily closed').checked = checked;
    $('Closed').checked = checked;
    $('Completed').checked = checked;
    $('Withdrawn').checked = checked;
    $('Withdrawn from PDQ').checked = checked;
}

function englishItemClicked(){
    $('All English').checked = 0;
    $('English').checked = 1;
    $('Spanish').checked = 0;
    checkAllSpanish(0);
    if (!isEnglishItemChecked())
        $('All English').checked = 1;
}

function spanishItemClicked(){
    $('All Spanish').checked = 0;
    $('Spanish').checked = 1;
    $('English').checked = 0;
    checkAllEnglish(0);
    if (!isSpanishItemChecked())
        $('All Spanish').checked = 1;
}

function statusItemClicked(){
    $('All Status').checked = 0;
    if (!isStatusItemChecked())
        $('All Status').checked = 1;
}

function langClicked(lang){
    checkAllEnglish(0);
    checkAllSpanish(0);
    if (lang == 'English'){
        $('All English').disabled = 0;
        $('All English').checked = 1;
    }
    else{
        $('All Spanish').disabled = 0;
        $('All Spanish').checked = 1;
    }
}

function allEnglishClicked(){
    checkAllEnglish(0);
    checkAllSpanish(0);
    $('English').checked = 1;
    $('All English').checked = 1;
}

function allSpanishClicked(){
    checkAllEnglish(0);
    checkAllSpanish(0);
    $('Spanish').checked = 1;
    $('All Spanish').checked = 1;
}

function allStatusClicked(){
    checkAllStatus(0);
    $('All Status').checked = 1;
}

</script>
"""
header = cdrcgi.header(title, title, instr + ' - ' + dateString, 
                           script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1,stylesheet = jscript)

#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Failure connecting to database: %s' % info[1][0])
     
#----------------------------------------------------------------------
# If we have a title string but no ID, find the matching summary.
#----------------------------------------------------------------------
if docTitle and not docId:
    try:
        cursor.execute("""\
            SELECT d.id, d.title
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE t.name = 'Summary'
               AND d.title LIKE ?
          ORDER BY d.title""", '%' + docTitle + '%')
        rows = cursor.fetchall()
    except Exception, info:
        cdrcgi.bail("Database failure looking up title %s: %s" %
                    (docTitle, str(info)))
    if not rows:
        cdrcgi.bail("No summaries found containing the string %s" % docTitle)
    elif len(rows) == 1:
        docId = str(rows[0][0])
    else:
        form = """\
   <input type='hidden' name ='%s' value='%s'>
   Select Summary:&nbsp;&nbsp;
   <select name='cdrid'>
""" % (cdrcgi.SESSION, session)
        for row in rows:
            form += """\
    <option value='%d'>%s</option>
""" % (row[0], row[1])
        form += """\
   </select>
"""

        for s in statuses:
             form += """
   <input id='status' name='status' type='hidden' value='%s'>""" % s

        if revFrom and revTo:
            form += """
   <input id='revfrom' name='reviewedfrom' type='hidden' value='%s'>
   <input id='revto'   name='reviewedto'   type='hidden' value='%s'>
   <input id='exclude' name='exclude'      type='hidden' value='%s'>
""" % (revFrom, revTo, excludeDate)

        form += """
   <input id='doexcel' name='doexcel'      type='hidden' value='%s'>
   <input id='displayall' name='displayall' type='hidden' value='%s'>
""" % (doExcel, displayAll)

        form += """
  </form>
 </body>
</html>
"""
        cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not lang and not cdrId:
    form   = """\
   <input type='hidden' name='%s' value='%s'>
 
    <fieldset>
     <legend>&nbsp;Enter CDR-ID or Summary Title&nbsp;</legend>
   <table border = '0' width="100%%">
    <tr>
     <td align='right' width="25%%">
      <label for="cdrid"><b>Summary by ID:&nbsp;</b></label>
     </td>
     <td width="75%%">
      <input type="text" name='cdrid' id="cdrid" size="40"
             value="Enter CDR-ID (i.e. CDR123456)"
             onfocus="this.value=''">
     </td>
    </tr>
   </table>
   <div class="mittich">
    <b>... or ...</b>
   </div>
   <table border = '0' width="100%%">
    <tr>
     <td align='right' width="25%%">
      <label for="title"><b>Summary by Title:&nbsp;</b></label>
     </td>
     <td width="75%%">
      <input type="text" name='title' id="title" size="40"
             value="Enter Summary Title"
             onfocus="this.value=''">
     </td>
    </tr>
   </table>
   </fieldset>

   <p/>

   <fieldset>
    <legend>&nbsp;Select Language and PDQ Summaries&nbsp;</legend>
    <table>
   <tr>
     <td width=100>
      <input id='English' name='lang' type='radio' 
             value='English' onClick="langClicked('English');" CHECKED>
       <b>English</b>
      </input>
     </td>
     <td>
      <b>Select PDQ Summaries: (one or more)</b>
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <label>
       <input type='checkbox' id='All English' name='grp' 
              value='All English' onClick="allEnglishClicked();" CHECKED>
        <b>All English</b>
       </input>
      </label>
      <br>
      <label>
       <input type='checkbox' id='Adult Treatment' name='grp' 
       value='Adult Treatment' onClick="englishItemClicked();">
       <b>Adult Treatment</b></input>
      </label><br>
      <label>
       <input type='checkbox' id='Genetics' name='grp' 
       value='Genetics' onClick="englishItemClicked();">
       <b>Cancer Genetics</b></input>
      </label><br>
      <label>
       <input type='checkbox' name='grp' 
       id='Complementary and Alternative Medicine' onClick="englishItemClicked();"
       value='Complementary and Alternative Medicine'>
       <b>Complementary and Alternative Medicine</b></input>
      </label><br>
      <label>
       <input type='checkbox' id='Pediatric Treatment' name='grp' 
       value='Pediatric Treatment' onClick="englishItemClicked();">
       <b>Pediatric Treatment</b></input>
      </label><br>
      <label>
       <input type='checkbox' id='Screening and Prevention' name='grp' 
       value='Screening and Prevention' onClick="englishItemClicked();">
       <b>Screening and Prevention</b></input>
      </label><br>
      <label>
       <input type='checkbox' id='Supportive Care' name='grp' 
       value='Supportive Care' onClick="englishItemClicked();">
       <b>Supportive and Palliative Care</b><br></input>
      </label>
     </td>
    </tr>
    </table>
    <hr/>
    <table>
    <tr>
     <td width=100>
      <label>
       <input id='Spanish' name='lang' type='radio' 
       value='Spanish' onClick="langClicked('Spanish');"><b>Spanish</b></input>
      </label>
     </td>
     <td>
      <b>Select PDQ Summaries: (one or more)</b>
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <label>
       <input type='checkbox' id='All Spanish' name='grp' 
       value='All Spanish' onClick="allSpanishClicked();">
       <b>All Spanish</b></input>
      </label><br>
      <label>
       <input type='checkbox' id='Spanish Adult Treatment' name='grp' 
       value='Spanish Adult Treatment' onClick="spanishItemClicked();">
       <b>Adult Treatment</b></input>
      </label><br>
      <label>
       <input type='checkbox' id='Spanish Pediatric Treatment' name='grp' 
       value='Spanish Pediatric Treatment' onClick="spanishItemClicked();">
       <b>Pediatric Treatment</b></input>
      </label><br>
      <label>
       <input type='checkbox' id='Spanish Supportive Care' name='grp' 
       value='Spanish Supportive Care' onClick="spanishItemClicked();">
       <b>Supportive and Palliative Care</b></input>
      </label><br>
     </td>
    </tr>
    </table>
    </fieldset>

    <p/>

    <fieldset>
     <legend>&nbsp;Include/Exclude ProtocolLink/Ref Elements 
             for this Date Range&nbsp;</legend>

    <table class="tablecenter" border="0">
     <tr>
      <td align="right">
       <label for="reviewedfrom">From: </label>
      </td>
      <td>
       <input id="reviewedfrom" name="reviewedfrom" 
                value="Select start date"
                class="CdrDateField">
      </td>
     </tr>
     <tr>
      <td align="right">
       <label for="reviewedto">To: </label>
      </td>
      <td>
       <input id="reviewedto" name="reviewedto" 
                value="Select end date"
                class="CdrDateField">
      </td>
     </tr>
     <tr>
      <td colspan="2">
        <label for="includedate">
         <input type="radio" name="exclude" id="includedate"
                value="No">
         <b>Include&nbsp;&nbsp;&nbsp;&nbsp;</b>
         </input>
        </label>
        <label for="excludedate">
         <input type="radio" name="exclude" id="excludedate" 
                value="Yes" checked="checked">
         <b>Exclude</b>
         </input>
        </label>
      </td>
     </tr>
    </table>
    </fieldset>

    <p/>

    <fieldset>
    <legend>&nbsp;Select Trial Status (one or more)&nbsp;</legend>
    <table>
    <tr>
     <td width=100></td>
     <td>
      <label>
       <input type='checkbox' id='All Status' name='status' 
              value='All Status' onClick="allStatusClicked();" CHECKED>
        <b>All Status</b>
       </input>
      </label>
      <br>
      <label>
       <input type='checkbox' id='Active' name='status' 
              value='Active' onClick="statusItemClicked();">
        <b>Active</b>
       </input>
      </label>
      <br>
      <label>
       <input type='checkbox' id='Approved-not yet active' name='status' 
              value='Approved-not yet active' onClick="statusItemClicked();">
        <b>Approved-not yet active</b>
       </input>
      </label>
      <br>
      <label>
       <input type='checkbox' id='Enrolling by invitation' name='status' 
              value='Enrolling by invitation' onClick="statusItemClicked();">
        <b>Enrolling by invitation</b>
       </input>
      </label>
      <br>
      <label>
       <input type='checkbox' id='Temporarily closed' name='status' 
              value='Temporarily closed' onClick="statusItemClicked();">
        <b>Temporarily closed</b>
       </input>
      </label>
      <br>
      <label>
       <input type='checkbox' id='Closed' name='status' 
               value='Closed' onClick="statusItemClicked();">
        <b>Closed</b>
       </input>
      </label>
      <br>
      <label>
       <input type='checkbox' id='Completed' name='status' 
               value='Completed' onClick="statusItemClicked();">
        <b>Completed</b>
       </input>
      </label>
      <br>
      <label>
       <input type='checkbox' id='Withdrawn' name='status' 
               value='Withdrawn' onClick="statusItemClicked();">
        <b>Withdrawn</b>
       </input>
      </label>
      <br>
      <label>
        <input type='checkbox' id='Withdrawn from PDQ' name='status' 
               value='Withdrawn from PDQ' onClick="statusItemClicked();">
         <b>Withdrawn from PDQ</b>
        </input>
      </label>
      <br>
      <br>
     </td>
    </tr>    
    <tr>
     <td align="right"><b>Include:</b></td>
     <td>
      <label>
       <input type="radio" id="displayall" name="displayall" 
                value="Yes" checked="checked">
                <b>All</b>
      &nbsp; &nbsp; &nbsp; &nbsp;
      </label>
      <label>
       <input type="radio" id="displayall" name="displayall" 
                value="No">
                <b>Changed Status Only</b>
      </label>
     </td>
    </tr>
   </table>
   </fieldset>

    <p/>

    <fieldset>
     <legend>&nbsp;Specify Output Format&nbsp;</legend>

    <table class="tablecenter" width="50%%" border="0">
    <tr>
     <td>
      <label>
       <input type="radio" id="doexcel" name="doexcel" 
                value="Yes"> 
        <b>Excel</b> 
       </input>
      </label>
     <td>
      <label>
       <input type="radio" id="dohtml" name="doexcel"
                value="No" checked="checked"> 
        <b>HTML</b> 
       </input>
      </label>
     </td>
    </tr>
   </table>
    </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)


# ---------------------------------------------------------------------
# If we have a cdrId (either a title or ID has been entered) we need 
# to get the summary language
# ---------------------------------------------------------------------
if not lang and cdrId:
    try:
        cursor.execute("""\
            SELECT d.id, q.value, b.value
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
              JOIN query_term q
                ON q.doc_id = d.id
               AND q.path = '/Summary/SummaryMetaData/SummaryLanguage'
              JOIN query_term b
                ON b.doc_id = d.id
               AND b.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
             WHERE d.id = %s""" % cdrId)
        rows = cursor.fetchall()
    except Exception, info:
        cdrcgi.bail("Database failure looking up summary language for %s: %s" %
                    (cdrId, str(info)))
    if not rows:
        cdrcgi.bail("No document found: CDR%d" % cdrId)
    else:
        docId = int(rows[0][0])
        lang  = str(rows[0][1])
        board = ''
        for i in range(len(rows)):
            board += "'" + str(rows[i][2]) + "',"


boardPick = ''
if not docId:
    #----------------------------------------------------------------------
    # Create the selection criteria based on the groups picked by the user
    # But the decision will be based on the content of the board instead
    # of the SummaryType.
    # Based on the SummaryType selected on the form the boardPick list is
    # being created including the Editorial and Advisory board for each
    # type.  These board IDs can then be decoded into the proper 
    # heading to be used for each selected summary type.
    # --------------------------------------------------------------------
    for i in range(len(groups)):
      if groups[i] == 'Adult Treatment' and lang == 'English':
          boardPick += """'CDR0000028327', 'CDR0000035049', """
      elif groups[i] == 'Spanish Adult Treatment' and lang == 'Spanish':
          boardPick += """'CDR0000028327', 'CDR0000035049', """
      elif groups[i] == 'Complementary and Alternative Medicine':
          boardPick += """'CDR0000256158', """
      elif groups[i] == 'Genetics':
          boardPick += """'CDR0000032120', 'CDR0000257061', """
      elif groups[i] == 'Screening and Prevention':
          boardPick += """'CDR0000028536', 'CDR0000028537', """
      elif groups[i] == 'Pediatric Treatment' and lang == 'English':
          boardPick += """'CDR0000028557', 'CDR0000028558', """
      elif groups[i] == 'Spanish Pediatric Treatment' and lang == 'Spanish':
          boardPick += """'CDR0000028557', 'CDR0000028558', """
      elif groups[i] == 'Supportive Care' and lang == 'English':
          boardPick += """'CDR0000028579', 'CDR0000029837', """
      elif groups[i] == 'Spanish Supportive Care' and lang == 'Spanish':
          boardPick += """'CDR0000028579', 'CDR0000029837', """
      else:
          boardPick += """'""" + groups[i] + """', """
#else:
#    boardPick = """%s,""" % board

statusPick=''
for i in range(len(statuses)):
    statusPick += "'" + statuses[i] + "',"

#------------------------------------
# build the query
#------------------------------------
def getQuerySegment(lang, ref):
    query = [u"""SELECT qt.doc_id as cdrid, title.value as summaryTitle, \
                 secTitle.value as summarySecTitle,'"""]

    query.append(ref)
    
    query.append(u"""' as ref, qt.int_val as protCDRID, qstatus.value as status,
      secTitle.node_loc as TitleNodeLoc,
      len(secTitle.node_loc) as TitleNodeLocLen,qt.node_loc as LinkNodeLoc 
      FROM query_term qt
      JOIN query_term title    ON qt.doc_id  = title.doc_id
      JOIN query_term qstatus  ON qt.int_val = qstatus.doc_id
      JOIN query_term secTitle ON qt.doc_id  = secTitle.doc_id """)

    if not docId:
        query.append(u"""
      JOIN query_term lang     ON qt.doc_id  = lang.doc_id """)
    
        if lang == 'English':
            query.append(u"""
      JOIN query_term board    ON qt.doc_id = board.doc_id """)
        else:
            query.append(u"""
      JOIN query_term qtrans   ON qtrans.doc_id = qt.doc_id
      JOIN query_term board    ON qtrans.int_val = board.doc_id """)

    if ref == 'LINK':
        query.append(u"""
     WHERE qt.path like '/summary/%ProtocolLink/@cdr:ref' """)
    else:
        query.append(u"""
     WHERE qt.path like '/summary/%ProtocolRef/@cdr:href' """)

    if lang == 'Spanish':
        query.append(u"""
       AND qtrans.path = '/Summary/TranslationOf/@cdr:ref' """)

    query.append(u"""\
    AND title.path = '/Summary/SummaryTitle'
    AND (qstatus.path = 
                  '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus' 
         OR
         qstatus.path = 
                  '/CTGovProtocol/OverallStatus'
        )
    AND secTitle.path like '/Summary/%SummarySection/Title' 
    AND LEFT(secTitle.node_loc,len(secTitle.node_loc)-4) =  LEFT(qt.node_loc,len(secTitle.node_loc)-4) """)
    
    if statusPick.find("All Status") == -1:
        query.append(u""" AND qstatus.value in (""")
        query.append(statusPick[:-1])
        query.append(u""") """)
    
    if not docId:
        query.append(u"""
    AND board.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref' """)

        allStr = "All " + lang
        if boardPick.find(allStr) == -1:
            query.append(u""" AND board.value in (""")
            query.append(boardPick[:-2])
            query.append(u""") """)

        query.append(u"""
    AND lang.path = '/Summary/SummaryMetaData/SummaryLanguage'
    AND lang.value = '""")

        query.append(lang + "'")
    else:
        query.append(u"""
    AND qt.doc_id = %s
    """ % docId)
    
    query.append(u"""
    AND EXISTS (SELECT 'x'
                   FROM doc_version v
                  WHERE v.id = qt.doc_id AND v.val_status = 'V' 
                    AND v.publishable = 'Y') 
     AND qt.doc_id not in (select doc_id 
                             from doc_info 
                            where doc_status = 'I' 
                              and doc_type = 'Summary')
    """)

    query = u"".join(query)
    return query
      
# -------------------------------------------------------------
# Put all the pieces together for the SELECT statement
# -------------------------------------------------------------

query = getQuerySegment(lang, 'LINK') + \
        " UNION "                     + \
        getQuerySegment(lang, 'REF')  + \
        " ORDER BY cdrid, LinkNodeLoc, TitleNodeLocLen desc, status"

if not query:
    cdrcgi.bail('No query criteria specified')

dataRows = []
cdrids = []

# Identify if the element is a link or ref element
# Populate the instance attributes with the data from the 
# ProtocolRef/Link attributes
# Note:  Currently, if the same ProtocolRef is listed multiple times
#        within a single section only the information for the last
#        ProtocolRef is picked up and displayed for all of the elements.
# ----------------------------------------------------------------------
def checkElement(cdrid,node,parentElem,ref,lastSECTitle):
    for dataRow in dataRows:
        if dataRow.cdrid == cdrid:
            if dataRow.summarySecTitle == lastSECTitle:
                Linkcdrid = cdr.normalize(dataRow.protCDRID)
                if node.attributes.length > 0:
                    for (name,value) in node.attributes.items():
                        if ref == 'LINK':
                            if name == 'cdr:ref':
                                if value == Linkcdrid:
                                    # We need to ensure that we only pick up
                                    # these attributes for the same record of
                                    # this protocol ID (Linkcdrid), so we'll
                                    # iterate over the attributes again once
                                    # we identified the correct element for this
                                    # section.
                                    #
                                    # There is a caveat:
                                    # If we find a link to a protocol multiple
                                    # times in the same section we need to 
                                    # ensure that we don't overwrite the 
                                    # 1st, 2nd, 3rd,... object with the 
                                    # information from this node.  We are 
                                    # therefore testing if none of the elements
                                    # (comment, status, date) have been 
                                    # populated yet - meaning this is a new
                                    # occurrence of the link.
                                    # ------------------------------------------
                                    if not dataRow.linkComment and \
                                       not dataRow.linkDate    and \
                                       not dataRow.linkStatus:
                                        for (name,value) in        \
                                                  node.attributes.items():
                                            if name == 'comment':
                                                dataRow.linkComment = value 
                                            if name == 'LastReviewedDate':
                                                dataRow.linkDate = value
                                            if name == 'LastReviewedStatus':
                                                dataRow.linkStatus = value
                                    if node.childNodes:
                                        for nodeChild in node.childNodes:
                                            if nodeChild ==        \
                                               xml.dom.minidom.Node.TEXT_NODE:
                                                if len(nodeChild.Value) == 0:
                                                    nodeChild.Value = \
                                                                'Protocol Link'
                                    else:
                                        textNode = \
                                             dom.createTextNode('Protocol Link')
                                        node.appendChild(textNode)
                                    if len(dataRow.protocolLink) == 0:
                                        dataRow.addProtocolLink(parentElem)
                                        return
                        elif ref == 'REF':
                            if name == 'cdr:href':
                                if value == Linkcdrid:
                                    # We need to ensure that we only pick up
                                    # these attributes for the same record of
                                    # this protocol ID (Linkcdrid), so we'll
                                    # iterate over the attributes again once
                                    # we identified the correct element for this
                                    # section.
                                    #
                                    # There is a caveat:
                                    # If we find a link to a protocol multiple
                                    # times in the same section we need to 
                                    # ensure that we don't overwrite the 
                                    # 1st, 2nd, 3rd,... object with the 
                                    # information from this node.  We are 
                                    # therefore testing if none of the elements
                                    # (comment, status, date) have been 
                                    # populated yet - meaning this is a new
                                    # occurrence of the link.
                                    # ------------------------------------------
                                    if not dataRow.linkComment and \
                                       not dataRow.linkDate    and \
                                       not dataRow.linkStatus:
                                        for (name,value) in        \
                                                  node.attributes.items():
                                            if name == 'comment':
                                                dataRow.linkComment = value
                                            if name == 'LastReviewedDate':
                                                dataRow.linkDate = value
                                            if name == 'LastReviewedStatus':
                                                dataRow.linkStatus = value
                                    if node.childNodes:
                                        for nodeChild in node.childNodes:
                                            if nodeChild ==        \
                                               xml.dom.minidom.Node.TEXT_NODE:
                                                if len(nodeChild.Value) == 0:
                                                    nodeChild.Value = \
                                                                'Protocol Ref'
                                    else:
                                        textNode = \
                                             dom.createTextNode('Protocol Ref')
                                        node.appendChild(textNode)
                                    if len(dataRow.protocolLink) == 0:
                                        dataRow.addProtocolLink(parentElem)
                                        return
    return


# ----------------------------------------------------------
# Identify all protocolLinks/Refs, and SummarySection titles
# For the link/ref retrieve the attribute information
# ----------------------------------------------------------
def checkChildren(cdrid,parentElem,lastSECTitle):
    parentNodeName = parentElem.nodeName
    for node in parentElem.childNodes:
        nodeValue = node.nodeValue
        nodeName = node.nodeName
        if node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
            if nodeName == 'ProtocolLink':
                checkElement(cdrid,node,parentElem,'LINK',lastSECTitle)
            elif nodeName == 'ProtocolRef':
                checkElement(cdrid,node,parentElem,'REF',lastSECTitle)
            elif nodeName == 'Title':
                if parentNodeName == 'SummarySection':
                    for chNode in node.childNodes:
                        lastSECTitle = getTitleText(node.childNodes)
            
        checkChildren(cdrid,node,lastSECTitle)
    return


# -------------------------------------------------------------------------
# Extract the text content of the node and concatenate as a single string
# This only gets the text of the next element but that's OK since the title
# does not have a deeper node structure:
#   <Title><GeneName>BRCA1</GeneName> works well with 
#          <GeneName>BRC2</GeneName></Title>
# But this will not work:
#   <Title><GeneName>BRCA<sup>1</sup></GeneName> works well with 
#          <GeneName>BRC<sup>2</sup></GeneName></Title>
# -------------------------------------------------------------------------
def getTitleText(nodelist):
    rc = u""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
        elif node.nodeType == node.ELEMENT_NODE:
            rc = getText(node.childNodes)
    return rc


# ------------------------------------------------------
# Process the root node of the document (a.k.a. Summary)
# ------------------------------------------------------
def updateRefs(cdrid,dom):
    docElem = dom.documentElement
    checkChildren(cdrid,docElem,'')
    
    return


#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    #conn = cdrdb.connect('CdrGuest')
    #cursor = conn.cursor()
    cursor.execute(query, timeout=300)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Summary documents: %s' % info[1][0])
     
if not rows:
    cdrcgi.bail('No Records Found for Selection')

LastLinkNodeLoc = ''

# Create a list of instances containing the content for each row
# populated with the information from the SQL query
# Also, create a list of Summary CDR-IDs along the way.
# ------------------------------------------------------------
for cdrid, summaryTitle, summarySecTitle, ref, protCDRID, status, \
    TitleNodeLoc, TitleNodeLocLen, LinkNodeLoc in rows:
    if LinkNodeLoc != LastLinkNodeLoc:
        dataRows.append(dataRow(cdrid, summaryTitle, summarySecTitle, ref, 
                                protCDRID, status, doExcel))
        if cdrid not in cdrids:
            cdrids.append(cdrid)
    LastLinkNodeLoc = LinkNodeLoc

# Extract each summary document from the DB and create the DOM tree
# Then populate the missing attributes from the XML data.
# -----------------------------------------------------------------
#cdrids = [62675]
for cdrid in cdrids:
    docId = cdr.normalize(cdrid)
    doc = cdr.getDoc(session, docId, checkout = 'N')
    if doc.startswith("<Errors"):
        cdrcgi.bail("<error>Unable to retrieve %s : %s" % (cdrid, doc))
    filter = ['name:Revision Markup Filter']
    doc = cdr.filterDoc(session,filter,docId=docId)
    dom = xml.dom.minidom.parseString(doc[0])
    updateRefs(cdrid,dom)

cursor.close()
cursor = None

if doExcel == 'Yes':
    # Create the spreadsheet and define default style, etc.
    # -----------------------------------------------------
    wsTitle = u'Summaries With Protocol Links'
    wb      = ExcelWriter.Workbook()
    b       = ExcelWriter.Border()
    borders = ExcelWriter.Borders(b, b, b, b)
    font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
    align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
    alignS  = ExcelWriter.Alignment('Left', 'Top', wrap = False)
    style1  = wb.addStyle(alignment = align, font = font)
    urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
    style4  = wb.addStyle(alignment = align, font = urlFont)
    style2  = wb.addStyle(alignment = align, font = font, 
                             numFormat = 'YYYY-mm-dd')
    alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
    alignT  = ExcelWriter.Alignment('Left', 'Bottom', wrap = False)
    headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                size = 12)
    titleFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                size = 14)
    boldFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                size = 11)
    styleH  = wb.addStyle(alignment = alignH, font = headFont)
    styleT  = wb.addStyle(alignment = alignT, font = titleFont)
    style1b = wb.addStyle(alignment = align,  font = boldFont)
    styleS  = wb.addStyle(alignment = alignS, font = boldFont)
    styleR  = wb.addStyle(alignment = alignS, font = font)

    ws      = wb.addWorksheet(wsTitle, style1, 45, 1)
    
    # CIAT wants a title row
    # ----------------------------------------------------------
    titleTime = time.strftime("%Y-%m-%d %H:%M:%S")
    rowCount = 0
    rowNum = 1
    exRow = ws.addRow(rowNum, styleT)

    rowNum = 1
    exRow = ws.addRow(rowNum, styleS)
    exRow.addCell(1,  'Report created: %s' % titleTime)


    # Set the column width
    # --------------------
    ws.addCol( 1,  60)
    ws.addCol( 2, 120)
    ws.addCol( 3, 150)
    ws.addCol( 4, 300)
    ws.addCol( 5,  60)
    ws.addCol( 6,  80)
    ws.addCol( 7, 100)
    ws.addCol( 8,  60)

    # Create selection criteria for English/Spanish
    # and the boards
    # ---------------------------------------------
    rowNum += 2
    exRow = ws.addRow(rowNum, styleT)
    exRow.addCell(1, 'Summaries with Protocol Links/Refs Report')
    rowNum += 1
    if revFrom and revTo:
        exRow = ws.addRow(rowNum, styleR)
        if excludeDate == 'Yes':
            exRow.addCell(1, 'Links shown if not reviewed between %s and %s' % 
                                                             (revFrom, revTo))
        elif excludeDate == 'No':
            exRow.addCell(1, 'Links shown if reviewed between %s and %s' % 
                                                             (revFrom, revTo))
        else:
            cdrcgi.bail("Don't know if date range is inclusive or exclusive!")

    rowNum += 1

    exRow = ws.addRow(rowNum, styleH)
    exRow.addCell(1, 'CDR-ID')
    exRow.addCell(2, 'Summary Title')
    exRow.addCell(3, 'Summary Section Title')
    exRow.addCell(4, 'Protocol Link/Ref')
    exRow.addCell(5, 'CDR-ID')
    exRow.addCell(6, 'Current Protocol Status')
    exRow.addCell(7, 'Comment')
    exRow.addCell(8, 'Last Reviewed Date')
    exRow.addCell(9, 'Last Reviewed Status')

    # Submit the query to the database.
    #---------------------------------------------------
    for dataRow in dataRows:
        if revFrom and revTo:
            if displayRow(revFrom, revTo, dataRow.linkDate, excludeDate): 
                continue

        if displayAll == 'No':
            if not hasStatusChanged(dataRow.status, dataRow.linkStatus): 
                continue

        rowCount += 1
        rowNum += 1
        exRow = ws.addRow(rowNum, styleR)
        addExcelTableRow(dataRow)


    rowNum += 1
    exRow = ws.addRow(rowNum, style1b)
    exRow.addCell(1, 'Count: %d' % rowCount)

    t = time.strftime("%Y%m%d%H%M%S")                                               
    # Save the report.
    # ----------------
    name = '/SummariesWithProtocolLinksReport-%s.xls' % t
    REPORTS_BASE = 'd:/cdr/reports'
    f = open(REPORTS_BASE + name, 'wb')
    wb.write(f, True)
    f.close()

    if sys.platform == "win32":
        import os, msvcrt
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=%s" % name
    print
    wb.write(sys.stdout, True)

else:
    # out put the results table
    header = cdrcgi.rptHeader(title, instr) 
    form   = [u"""\
     <style type="text/css">
    table
    {
        font-family: Verdana, Tahoma, sans-serif;
        font-size: 8pt;
        text-align: top;
    }
    th.cdrTable
    {
        font-family: Verdana, Tahoma, sans-serif;
        font-size: 8pt;
        text-align: top;
        color: white;
        background: #664;
    }
    td.cdrTableEven
    {
        font-family: Verdana, Tahoma, sans-serif;
        font-size: 8pt;
        text-align: top;
        color: black;
        background: #FFC;
    }
    td.cdrTableOdd
    {
        font-family: Verdana, Tahoma, sans-serif;
        font-size: 8pt;
        text-align: top;
        color: #220;
        background: #FFE;
    }
    td.top {
        vertical-align: text-top;
        }
    a:link 
    {
        color: red; 
        text-decoration: none;
        font-weight: bold;
    } /* unvisited link */
    a:active 
    {
        color: red; 
        text-decoration: none;
        font-weight: bold;
    }
    a:visited 
    {
        color: red;
        text-decoration: none;
        font-weight: bold;
    } /* visited link */
    a:hover 
    {
        color: white; 
        background-color:red; 
        text-decoration: underline;
        font-weight: bold;
    } /* mouse over link */

    a.selected:link 
    {
        color: purple;
        font-style:italic;
        text-decoration: none;
        font-weight: bold;
    } /* unvisited link */
    a.selected:active 
    {
        color: blue;
        font-style:italic;
        text-decoration: none;
        font-weight: bold;
    }
    a.selected:visited 
    {
        color: purple;
        font-style:italic;
        text-decoration: none;
        font-weight: bold;
    } /* visited link */
    a.selected:hover 
    {
        color: white; 
        background-color:purple;
        font-style:italic;
        text-decoration: underline;
        font-weight: bold;
    } /* mouse over link */

      </style>
      
       <input type='hidden' name='%s' value='%s'>
        <p style="text-align: center; font-family: Verdana, Tahoma, sans-serif; font-size: 12pt; font-weight: bold; color: #553;">
        Summaries with Protocol Links/Refs Report<br>
        <span style="text-align: center; 
                     font-family: Verdana, Tahoma, sans-serif; 
                     font-size: 11pt; 
                     font-weight: normal; 
                     color: #553;">
       """ % (cdrcgi.SESSION, session)]

    if revFrom and revTo:
        if excludeDate == 'Yes':
            form.append(u"""
    Links shown if not reviewed between %s and %s<br>
    """ % (revFrom, revTo))
        elif excludeDate == 'No':
            form.append(u"""
    Links shown if reviewed between %s and %s<br>
    """ % (revFrom, revTo))

    form.append(u"""
        %s</span>
        </p>
       
       <table>
       <tr>
       <th  class="cdrTable">CDR-ID</th>
       <th  class="cdrTable">Summary Title</th>
       <th  class="cdrTable">Summary Sec Title</th>
       <th  class="cdrTable">Protocol Link/Ref</th>
       <th  class="cdrTable">CDR-ID</th>
       <th  class="cdrTable">Current Protocol Status</th>
       <th  class="cdrTable">Comment</th>
       <th  class="cdrTable">Last Reviewed Date</th>
       <th  class="cdrTable">Last Reviewed Status</th>
       </tr>
       """ % dateString)

    cssClass = 'cdrTableEven'
    for dataRow in dataRows:
        if revFrom and revTo:
            if displayRow(revFrom, revTo, dataRow.linkDate, excludeDate): 
                continue

        if displayAll == 'No':
            if not hasStatusChanged(dataRow.status, dataRow.linkStatus): 
                continue

        form.append(u"<tr>")
        form.append(u"""<td class="%s top">%s</td>""" %
                                            (cssClass, dataRow.cdrid))
        form.append(u"""<td class="%s top">%s</td>""" %
                                            (cssClass, dataRow.summaryTitle))
        form.append(u"""<td class="%s top">%s</td>""" %
                                            (cssClass, dataRow.summarySecTitle))
        form.append(u"""<td class="%s top"><b>%s :</b> %s</td>""" % 
                                 (cssClass,dataRow.ref,dataRow.protocolLink))
        form.append(u"""<td class="%s top">%s</td>""" % 
                                            (cssClass, dataRow.protCDRID))
        form.append(u"""<td class="%s top">%s</td>""" % 
                                            (cssClass,dataRow.status))
        form.append(u"""<td class="%s top">%s</td>""" % 
                                            (cssClass,dataRow.linkComment))
        form.append(u"""<td class="%s top">%s</td>""" % 
                                            (cssClass,dataRow.linkDate))
        form.append(u"""<td class="%s top">%s</td>""" % 
                                            (cssClass,dataRow.linkStatus))
        form.append(u"</tr>")
        if cssClass == 'cdrTableEven':
            cssClass = 'cdrTableOdd'
        else:
            cssClass = 'cdrTableEven'
        
    form.append(u"""</table>
      </form>
     </body>
    </html>
    """)
    form = u"".join(form)
    cdrcgi.sendPage(header + form)
