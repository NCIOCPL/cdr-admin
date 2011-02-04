#----------------------------------------------------------------------
#
# $Id: $
#
# Report listing summaries containing specified markup.
#
# BZIssue::4756 - Summary Comments Report
# BZIssue::4908 - Editing Summary Comments Report in MS Word
#
# Note:
# This report has been adapted from the SummariesLists report.
# It is very likely that some parts/variables/etc. are a leftover
# from that report and haven't been deleted.
# I will take care of this with the next round of updates. VE.
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, time, cdrdb, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
audience  = fields and fields.getvalue("audience")         or None
lang      = fields and fields.getvalue("lang")             or None 
groups    = fields and fields.getvalue("grp")              or []
submit    = fields and fields.getvalue("SubmitButton")     or None
columns   = fields and fields.getvalue("showCol")          or []
comments  = fields and fields.getvalue("showComment")      or []
cdrId     = fields and fields.getvalue("cdrid")            or ' '
docTitle  = fields and fields.getvalue("title")            or None
SUBMENU     = "Report Menu"
buttons     = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = "SummaryComments.py"
title       = "CDR Administration"
section     = "Summary Comments Report"
header      = cdrcgi.header(title, title, section, script, buttons,
                            method = 'GET')

userCol   = False
blankCol  = False
displayComment = { 'internal':False,
                   'external':False,
                   'response':False,
                   'permanent':False,
                   'advisory':False}
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Summary Comments Report"
script    = "SummaryComments.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

if type(columns) == type(""):
    columns = [columns]
if type(comments) == type(""):
    comments = [comments]
if docTitle and docTitle.startswith('Enter'): docTitle = None

try:
    docId = int(cdrId)
except ValueError:
    docId = None

# Display extra columns
# ---------------------
if 'showUser' in columns:
    userCol = True
if 'showBlank' in columns:
    blankCol = True

# Display which comment types?
# ----------------------------
if 'internal' in comments or 'all' in comments:  
    displayComment['internal'] = True
if 'external' in comments or 'all' in comments:
    displayComment['external'] = True
if 'permanent' in comments or 'all' in comments:
    displayComment['permanent'] = True
if 'advisory' in comments or 'all' in comments:
    displayComment['advisory'] = True

# Response is set individually
# ----------------------------
if 'response' in comments:
    displayComment['response'] = True

# ---------------------------------------------------
# Selecting the title of the section
# ---------------------------------------------------
def getTitle(nodes):
    summarySection = 'No Section Title'
    children = nodes
    for child in children:
        if child.nodeName == 'Title':
            summarySection = cdr.getTextContent(child).strip()
    return summarySection


# ----------------------------------------------------------
# Function to return True or False to indicate which of the
# rows of comments are selected to be printed on the report.
# Note:  For the ResponseToComment element it had been 
#        decided that these will never be listed as Internal
#        or External comments, so the audience has been 
#        overloaded and is set to 'Response' for these 
#        elements.  For Comment elements the audience is set
#        to 'Internal' or 'External'.
# ----------------------------------------------------------
def printThisRow(audience, displayType, duration, source):
    # If internal and external are both selected we want to
    # display all comments but we still need to check if 
    # the Response should be included in the list.
    # ------------------------------------------------------
    if displayType['internal'] and displayType['external']:
        if audience == 'Response':
            if displayType['response']:
                return True
            else:
                return False
            return True
        return True

    if duration == 'permanent' and displayType['permanent']: return True
    if source == 'advisory-board' and displayType['advisory']: return True

    # Only Internal or external are selected
    # --------------------------------------
    if audience == 'Internal' and displayType['internal']:
        if duration and not displayType[duration.lower()]:
            return False
        return True
    elif audience == 'External' and displayType['external']: 
        if source and not displayType['advisory']:
            return False
        return True


    # If the comment is a 'Response' we need to check this
    # separately.
    # -----------------------------------------------------
    if audience == 'Response' and displayType['response']: 
        return True

    return False

    
    
# -------------------------------------------------
# Create the table row for the English table output
# -------------------------------------------------
def htmlCommentRow(info, displayType, addUserCol = True, 
                                      addBlankCol = True, first = True):
    """Return the HTML code to display a Comment row"""
    #cdrcgi.bail(displayType)
    html = ''
    if first:
        section = info[0]
    else:
        section = ''
    comment  = info[1]
    audience = info[2] or ''
    duration = info[3] or ''
    source   = info[4] or ''
    user     = info[5] or '&nbsp;'
    date     = info[6] or '&nbsp;'


    # Do we print this row based on the content and the options
    # checked?
    # ---------------------------------------------------------
    if not printThisRow(audience, displayType, duration, source): return html

    label = audience and audience[0].upper() or '-'
    if duration:
        label += ' ' + duration[0].upper()
    if source:
        label += ' ' + source[0].upper()

    # Create the table row display
    # If a markup type hasn't been checked the table cell will be
    # displayed with the class="nodisplay" style otherwise the 
    # count of the markup type is being displayed.
    # ------------------------------------------------------
    html = """\
   <TR>
    <TD class="report cdrid" width = "25%%">%s</TD>
    <TD class="%s" width="40%%">[%s] %s</TD>
""" % (section, audience and audience.lower() or ' ', 
                label, comment)

    if addUserCol:
        html += """\
    <TD class="s" width="15%%">%s / %s</TD>
""" % (user, date)

    if addBlankCol:
        html += """\
    <TD class="s" width="20%">&nbsp;</TD>
"""

    html += """\
   </TR>
"""

    return html


#----------------------------------------------------------------------
# Function to get the title of the current SummarySection
#----------------------------------------------------------------------
def getSummarySectionName(parentNode, lastSECTitle):
    parentNodeName = parentNode.nodeName
    if parentNodeName == 'SummarySection':
        return getTitle(parentNode.childNodes)
    else:
        lastSECTitle = getSummarySectionName(parentNode.parentNode, 
                                              lastSECTitle)
    return lastSECTitle


# =====================================================================
# If the user only picked one summary group, put it into a list so we
# can deal with the same data structure whether one or more were
# selected.
#----------------------------------------------------------------------
if type(groups) in (type(""), type(u"")):
    groups = [groups]

if groups:
    if lang == 'English':
       groups = [groups[0]]
    else:
       groups = [groups[1]]

# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])


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
   </select>"""

        if displayComment['internal']:
            form += """
     <input id='int' name='showComment' type='hidden' value='internal'>
    """
        if displayComment['external']:
            form += """
     <input id='ext' name='showComment' type='hidden' value='external'>
    """
        if displayComment['response']:
            form += """
     <input id='resp' name='showComment' type='hidden' value='response'>
    """
        if displayComment['permanent']:
            form += """
     <input id='perm' name='showComment' type='hidden' value='permanent'>
    """
        if displayComment['advisory']:
            form += """
     <input id='adv' name='showComment' type='hidden' value='advisory'>
    """

        if userCol:
            form += """
            <input id='user'  name='showCol' type='hidden' value='showUser'>
    """
        if blankCol:
            form += """
            <input id='blank' name='showCol' type='hidden' value='showBlank'>
    """
        form += """\
  </form>
 </body>
</html>
"""
        cdrcgi.sendPage(header + form)


#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y")

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not lang and not docId:
    header = cdrcgi.header(title, title, instr + ' - ' + dateString, 
                           script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1,
                           method = 'GET',
                           stylesheet = """
   <style type="text/css">
    TD      { font-size:  12pt; }
    LI.none { list-style-type: none }
    DL      { margin-left: 0; padding-left: 0 }
    P.title { font-size: 12pt;
              font-style: italic; 
              font-weight: bold; }
    *.comone   { margin-bottom: 8px; }
    *.comgroup { background: #C9C9C9; 
                 margin-bottom: 8px; }
   </style>

   <script type='text/javascript'>
     function dispInternal() {
         var checks  = ['ext', 'adv', 'all']
         if (document.getElementById('int').checked &&
             !document.getElementById('perm').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (document.getElementById('int').checked &&
                  document.getElementById('perm').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (!document.getElementById('int').checked &&
                  document.getElementById('perm').checked) {

             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }

     function dispPermanent() {
         var checks  = ['ext', 'adv', 'all']
         if (document.getElementById('perm').checked &&
             !document.getElementById('int').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (document.getElementById('perm').checked &&
                  document.getElementById('int').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (!document.getElementById('perm').checked &&
                  document.getElementById('int').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }


     function dispExternal() {
         var checks  = ['int', 'perm', 'all']
         if (document.getElementById('ext').checked &&
             !document.getElementById('adv').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (document.getElementById('ext').checked &&
                  document.getElementById('adv').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (!document.getElementById('ext').checked &&
                  document.getElementById('adv').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }


     function dispAdvisory() {
         var checks  = ['int', 'perm', 'all']
         if (document.getElementById('adv').checked &&
             !document.getElementById('ext').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (document.getElementById('adv').checked &&
                  document.getElementById('ext').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
         else if (!document.getElementById('adv').checked &&
                  document.getElementById('ext').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }


     function dispAll() {
         var checks  = ['int', 'perm', 'ext', 'adv']
         if (document.getElementById('all').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = true;
             }
         }
         else if (!document.getElementById('all').checked) {
             for (var j in checks) {
                 document.getElementById(checks[j]).checked = false;
             }
         }
     }

   </script>

"""                           )
    form   = """\
   <input type='hidden' name='%s' value='%s'>
 
   <fieldset>
    <legend>&nbsp;Select Summary Audience&nbsp;</legend>
    <input name='audience' type='radio' id="byHp"
           value='Health Professional' CHECKED>
    <label for="byHp">Health Professional</label>
    <br>
    <input name='audience' type='radio' id="byPat"
           value='Patient'>
    <label for="byPat">Patient</label>
   </fieldset>

   <fieldset>
    <legend>&nbsp;Select Summary Language and Summary Type&nbsp;</legend>
   <p class="title">Summaries by Board</p>
   <table border = '0' width="100%%">
    <tr>
     <td width=100>
      <input name='lang' type='radio' id="en" value='English' CHECKED>
      <label for="en">English</label>
     </td>
     <td valign='top'>
      <select name='grp'>
       <option>Adult Treatment</option>
       <option>Cancer Genetics</option>
       <option>Complementary and Alternative Medicine</option>
       <option>Pediatric Treatment</option>
       <option>Screening and Prevention</option>
       <option>Supportive and Palliative Care</option>
       <option selected="SELECTED">Please select a summary type ...</option>
      </select>
     </td>
    </tr>
    <tr>
     <td width=100>
      <input name='lang' type='radio' id="es" value='Spanish'>
      <label for="es">Spanish</label>
     </td>
     <td valign='top'>
      <select name='grp'>
       <option>Adult Treatment</option>
       <option>Pediatric Treatment</option>
       <option>Supportive and Palliative Care</option>
       <option selected="SELECTED">Please select a summary type ...</option>
      </select>
     </td>
    </tr>
   </table>

   <p class="title">Summary by ID</p>
   <table border = '0' width="100%%">
    <tr>
     <td align='right' width="25%%">
      <label for="cdrid">Document ID:&nbsp;</label>
     </td>
     <td width="75%%">
      <input type="text" name='cdrid' id="cdrid" size="40"
             value="Enter CDR-ID (i.e. CDR123456)"
             onfocus="this.value=''">
     </td>
    </tr>
   </table>

   <p class="title">Summary by Title</p>
   <table border = '0' width="100%%">
    <tr>
     <td align='right' width="25%%">
      <label for="title">Summary Title:&nbsp;</label>
     </td>
     <td width="75%%">
      <input type="text" name='title' id="title" size="40"
             value="Enter Summary Title"
             onfocus="this.value=''">
     </td>
    </tr>
   </table>
   </fieldset>

   <p>
   <fieldset>
    <legend>&nbsp;Select Comment Types to be displayed&nbsp;</legend>
    <div class='comgroup'>
     <input name='showComment' type='checkbox' id='int'
             value='internal'
                   onclick='javascript:dispInternal()'>
     <label for='int'>I - Internal Comments (excluding permanent comments)</label>
     <br>
     <input name='showComment' type='checkbox' id='perm'
             value='permanent' 
             onclick='javascript:dispPermanent()'>
     <label for='perm'>P - Permanent Comments (internal & external)</label>
    </div>
    <div class='comgroup'>
     <input name='showComment' type='checkbox' id='ext'
             value='external' checked='CHECKED'
                   onclick='javascript:dispExternal()'>
     <label for='ext'>E - External Comments (excluding advisory comments)</label>
     <br>
     <input name='showComment' type='checkbox' id='adv'
             value='advisory' 
             onclick='javascript:dispAdvisory()'>
     <label for='adv'>A - Advisory Board Comments (internal & external)</label>
    </div>
    <div class='comone'>
     <input name='showComment' type='checkbox' id='all'
             value='all'
                   onclick='javascript:dispAll()'>
     <label for='all'>All Comments</label>
    </div>
    <div class='comone'>
     <input name='showComment' type='checkbox' id="resp" 
            value='response' checked='CHECKED'>
     <label for='resp'>R - Response to Comments</label>
    </div>
   </fieldset>

   <fieldset>
    <legend>&nbsp;Add Columns to Report&nbsp;</legend>
    <label for="user">
    <input id='user' name='showCol' type='checkbox' 
           value='showUser'>
    Display UserID / Date</label>
    <br>
    <label for='blank'>
    <input id='blank' name='showCol' type='checkbox' 
           value='showBlank' CHECKED>
    Display Blank Column</label>
   </fieldset>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Language variable has been selected
# Building individual Queries
# - English, HP, with CDR ID
# - English, HP, without CDR ID
# - English, Patient, with CDR ID ...
#----------------------------------------------------------------------

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
      # if i+1 == len(groups):
      if groups[i] == 'Adult Treatment' and lang == 'English':
          boardPick += """'CDR0000028327', 'CDR0000035049', """
      elif groups[i] == 'Adult Treatment' and lang == 'Spanish':
          boardPick += """'CDR0000028327', 'CDR0000035049', """
      elif groups[i] == 'Complementary and Alternative Medicine':
          boardPick += """'CDR0000256158', 'CDR0000423294', """
      elif groups[i] == 'Cancer Genetics':
          boardPick += """'CDR0000032120', 'CDR0000257061', """
      elif groups[i] == 'Screening and Prevention':
          boardPick += """'CDR0000028536', 'CDR0000028537', """
      elif groups[i] == 'Pediatric Treatment' and lang == 'English':
          boardPick += """'CDR0000028557', 'CDR0000028558', """
      elif groups[i] == 'Pediatric Treatment' and lang == 'Spanish':
          boardPick += """'CDR0000028557', 'CDR0000028558', """
      elif groups[i] == 'Supportive and Palliative Care' and lang == 'English':
          boardPick += """'CDR0000028579', 'CDR0000029837', """
      elif groups[i] == 'Supportive and Palliative Care' and lang == 'Spanish':
          boardPick += """'CDR0000028579', 'CDR0000029837', """
      else:
          boardPick += """'""" + groups[i] + """', """
          cdrcgi.bail('Invalid summary type selected: %s' % boardPick)

# Define the Headings under which the summaries should be listed
# --------------------------------------------------------------
q_case = """\
       CASE WHEN board.value = 'CDR0000028327'  
                 THEN 'Adult Treatment'
            WHEN board.value = 'CDR0000035049'  
                 THEN 'Adult Treatment'
            WHEN board.value = 'CDR0000032120'  
                 THEN 'Cancer Genetics'
            WHEN board.value = 'CDR0000257061'  
                 THEN 'Cancer Genetics'
            WHEN board.value = 'CDR0000256158'  
                 THEN 'Complementary and Alternative Medicine'
            WHEN board.value = 'CDR0000423294'  
                 THEN 'Complementary and Alternative Medicine'
            WHEN board.value = 'CDR0000028557'  
                 THEN 'Pediatric Treatment'
            WHEN board.value = 'CDR0000028558'  
                 THEN 'Pediatric Treatment'
            WHEN board.value = 'CDR0000028536'  
                 THEN 'Screening and Prevention'
            WHEN board.value = 'CDR0000028537'  
                 THEN 'Screening and Prevention'
            WHEN board.value = 'CDR0000028579'  
                 THEN 'Supportive and Palliative Care'
            WHEN board.value = 'CDR0000029837'  
                 THEN 'Supportive and Palliative Care'
            ELSE board.value END
"""

# Create the selection criteria for the summary language (English/Spanish)
# ------------------------------------------------------------------------
q_lang = """\
AND    lang.path = '/Summary/SummaryMetaData/SummaryLanguage'
AND    lang.value = '%s'
""" % lang

# Define the selection criteria parts that are different for English or
# Spanish documents:
# q_fields:  Fields to be selected, i.e. the Spanish version needs to 
#            display the English translation
# q_join:    The Spanish version has to evaluate the board and language
#            elements differently
# q_board:   Don't restrict on selected boards if All English/Spanish
#            has been selected as well
# --------------------------------------------------------------------
if lang == 'English': 
    q_fields = """
                'dummy1', 'dummy2', title.value EnglTitle, 
"""
    q_join = """
JOIN  query_term board
ON    qt.doc_id = board.doc_id
JOIN  query_term lang
ON    qt.doc_id    = lang.doc_id
"""
    q_trans = ''
    if groups.count('All English'):
        q_board = ''
    else:
        q_board = """\
AND    board.value in (%s)
""" % boardPick[:-2]
else:
    q_fields = """
                qt.value CDRID, qt.int_val ID, translation.value EnglTitle, 
"""
    q_join = """
JOIN  query_term board
ON    qt.int_val = board.doc_id
JOIN  query_term translation
ON    qt.int_val = translation.doc_id
JOIN  query_term lang
ON    qt.doc_id    = lang.doc_id
"""
    q_trans = """
AND   translation.path = '/Summary/SummaryTitle'
AND   qt.path          = '/Summary/TranslationOf/@cdr:ref'
"""
    if groups.count('All Spanish'):
        q_board = ''
    else:
        q_board = """\
AND    board.value in (%s)
""" % boardPick[:-2]

# Create selection criteria for HP or Patient version
# ---------------------------------------------------
if audience == 'Patient':
    q_audience = """\
AND audience.value = 'Patients'
"""
else:
    q_audience = """\
AND audience.value = 'Health professionals'
"""

# Put all the pieces together for the SELECT statement
# (If we have a docId we just need to get the summary title)
# -------------------------------------------------------------
if docId:
    query = """\
        SELECT DISTINCT qt.doc_id, title.value DocTitle,
                        aud.value 
          FROM query_term qt
          JOIN query_term title
            ON qt.doc_id    = title.doc_id
          JOIN query_term aud
            ON qt.doc_id = aud.doc_id
           AND aud.path  = '/Summary/SummaryMetaData/SummaryAudience'
         WHERE qt.doc_id = %s 
           AND title.path   = '/Summary/SummaryTitle'
           AND qt.doc_id not in (select doc_id 
                               from doc_info 
                               where doc_status = 'I' 
                               and doc_type = 'Summary')
    """ % (docId) 
else:
    query = """\
        SELECT DISTINCT qt.doc_id, title.value DocTitle, 
        %s
        %s
        FROM  query_term qt
        %s
        JOIN  query_term title
        ON    qt.doc_id    = title.doc_id
        JOIN  query_term audience
        ON    qt.doc_id    = audience.doc_id
        WHERE title.path   = '/Summary/SummaryTitle'
        %s
        AND   board.path   = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'
        %s
        AND   audience.path = '/Summary/SummaryMetaData/SummaryAudience'
        %s
        %s
        AND EXISTS (SELECT 'x' FROM doc_version v
                    WHERE  v.id = qt.doc_id
                    AND    v.val_status = 'V'
                    AND    v.publishable = 'Y')
        AND qt.doc_id not in (select doc_id 
                               from doc_info 
                               where doc_status = 'I' 
                               and doc_type = 'Summary')
        ORDER BY 6, 2
        """ % (q_fields, q_case, q_join, q_trans, q_board, q_audience, q_lang)

if not query:
    cdrcgi.bail('No query criteria specified')   

# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Summary documents: %s' %
                info[1][0])
     
if not rows:
    cdrcgi.bail('No Records Found for Selection: %s ' % lang+"; "+audience+"; "+groups[0] )

# Counting the number of summaries per board
# ------------------------------------------
boardCount = {}
allSummaries = {}

for summary in rows:
    summaryTitle= summary[1]
    if not audience: audience = summary[2]
    doc = cdr.getDoc('guest', summary[0], getObject = 1)

    dom = xml.dom.minidom.parseString(doc.xml)
    
    allElements      = dom.getElementsByTagName('*')  

    # If the summary doesn't contain any Comments or Responses we can
    # quit here
    # ---------------------------------------------------------------
    commentElements  = dom.getElementsByTagName('Comment')  
    rCommentElements = dom.getElementsByTagName('ResponseToComment')  
    if not commentElements and not rCommentElements: continue

    allComments = []
    
    for obj in allElements:
        if obj.nodeName == 'Comment' or obj.nodeName == 'ResponseToComment':
            thisComment = cdr.getTextContent(obj).strip()
            if obj.nodeName == 'Comment':
                atAudience  = obj.getAttribute('audience')
                atDuration  = obj.getAttribute('duration') or ''
                atSource    = obj.getAttribute('source') or ''
            else:
                atAudience  = u'Response'
                atDuration = atSource = ''

            atUser      = obj.getAttribute('user')
            atDate      = obj.getAttribute('date')

            # Need to find the SummarySection title of each comment
            # Walking the tree backwards until I find the section title
            # ---------------------------------------------------------
            if obj.parentNode.nodeName == 'SummarySection':
                sectionNodes = obj.parentNode.childNodes
                summarySection = getTitle(sectionNodes)
            elif obj.parentNode.nodeName == 'Summary' or \
                 obj.parentNode.parentNode.nodeName == 'Summary':
                summarySection = 'No Section Title'
            else:
                secParentNode = obj.parentNode.parentNode
                summarySection = getSummarySectionName(secParentNode, '')

            allComments.append([summarySection, thisComment, atAudience,
                                atDuration, atSource, atUser, atDate])

    allSummaries[summaryTitle] = allComments


# Create the results page.
# 
# Note: Since the users want to be able to convert the HTML output 
#       to a Word document we need to specify the CSS class selectors
#       without an asterix '*'.  MS-Word doesn't recognize
#          *.dada { color: blue; }
#       as a valid selector but does accept
#           .dada { color: blue; }
#----------------------------------------------------------------------
instr     = '%s Summaries List -- %s.' % (lang, dateString)
header    = cdrcgi.rptHeader(title, instr, 
                          stylesheet = """\
   <STYLE type="text/css">
    DL             { margin-left:    0; 
                     padding-left:   0;
                     margin-top:    10px;
                     margin-bottom: 30px; }
    TABLE          { margin-top:    10px; 
                     margin-bottom: 30px; } 

    .date          { font-size: 12pt; }
    .boardHdr      { font-size: 12pt;
                     font-weight: bold;
                     text-decoration: underline; }
    .sectionHdr    { font-size: 12pt;
                     font-weight: bold; 
                     font-style: italic; }
    td.report      { font-size: 11pt;
                     padding-right: 15px; 
                     vertical-align: top; }
    td.nodisplay   { background-color: grey; }
    td.display     { background-color: white; 
                     font-weight: bold;
                     text-align: center; }
    .cdrid         { text-align: right }
    LI             { list-style-type: none }
    li.report      { font-size: 11pt;
                     font-weight: normal; }
    div.es          { height: 10px; }
    .internal      { font-weight: bold;
                     color: blue; }
    .external      { font-weight: bold;
                     color: green; }
    .response      { font-weight: bold;
                     color: brown; }
   </STYLE>
""")

# -------------------------
# Display the Report Title
# -------------------------
if lang == 'English' or not lang:
    hdrLang = ''
else:
    hdrLang = lang

#  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
# """ % (cdrcgi.SESSION, session, hdrLang, audience, dateString)
report    = """\
  <H3>PDQ %s %s Summaries<br>
  <span class="date">(%s)</span>
  </H3>
""" % (hdrLang, audience, dateString)

if not docId: board_type = rows[0][5]

# ------------------------------------------------------------------------
# Display data
# The columns for the section title and comment are always displayed.  
# The display of the user/date column and blank column depends on 
# the user input.
# ------------------------------------------------------------------------
if not docId:
    report += """\
  <span class="boardHdr">Board: %s</span><br>
""" % (board_type)

# Iterate over each summary
# -------------------------
for title, allComments in allSummaries.items():
    report += """\
      <span class="sectionHdr">Summary: %s</span>
      <TABLE border="1" width = "90%%">
       <tr>
        <th>Summary Section Title</th>
        <th>[I, E, or R] Comments</th>
    """ % (title)

    if userCol:
        report += """\
        <th>UserID / Date</th>
"""
    if blankCol:
        report += """\
        <th>Blank</th>
"""
    report += """\
       </tr>
"""
    # Iterate over all comments found
    # -------------------------------
    first      = True
    allRows    = 0
    sectionTitle = ''
    #cdrcgi.bail(displayComment)
    #cdrcgi.bail(allComments[0:7])
    for commentInfo in allComments:
        # We only want to display a section title if it differs from
        # the previous one but we need to account for the fact that
        # some of the comment types might not get displayed so we
        # need to keep track of when we've printed the first section
        # heading.
        # ----------------------------------------------------------
        allRows += 1
        if allRows > 1 and sectionTitle == commentInfo[0]:
            first = False
        #else:
        #    allRows = 0
            
        addHtmlRow = htmlCommentRow(commentInfo, displayComment,
                                     userCol, blankCol, first)
        if addHtmlRow:
            report += addHtmlRow
            first = False
            allRows += 1
            sectionTitle = commentInfo[0]
        else:
            if allRows == 1: allRows = 0

        first = True

    report += """
      </TABLE>
    """

footer = """\
 </BODY>
</HTML> 
"""     

# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + report + footer)
