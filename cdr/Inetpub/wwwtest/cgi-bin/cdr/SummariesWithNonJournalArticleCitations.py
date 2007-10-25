#----------------------------------------------------------------------
#
# $Id: SummariesWithProtocolLinks.py
#
# Report on lists of summaries.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, time, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
#boolOp    = fields and fields.getvalue("Boolean")          or "AND"
lang      = fields and fields.getvalue("lang")             or None
groups    = fields and fields.getvalue("grp")              or []
types    = fields and fields.getvalue("type")         or []
submit    = fields and fields.getvalue("SubmitButton")     or None
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Summaries With Non-Journal Article Citations Report"
script    = "SummariesWithNonJournalArticleCitations.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

#---------------------------
# DEBUG SETTINGS
#---------------------------
#lang = 'English'
#groups.append('Adult Treatment')
#groups.append('All English')
#types.append('All Types')
#types.append('Book chapter')
#session   = '4720787A-8DADE2-248-85OFI8XFV1G1'
#---------------------------

class dataRow:
    def __init__(self,cdrid,summaryTitle,summarySecTitle,citationType,citCDRID,citationTitle):
        self.cdrid = cdrid
        self.summaryTitle = summaryTitle
        self.summarySecTitle = summarySecTitle
        self.citationType = citationType
        self.citCDRID = citCDRID
        self.linkcdrid = cdr.normalize(citCDRID)
        self.citationTitle = citationTitle
        self.pubDetails = ''
    
    def addPubDetails(self,pubDetails):
        self.pubDetails = pubDetails

#----------------------------------------------------------------------
# If the user only picked one summary group, put it into a list so we
# can deal with the same data structure whether one or more were
# selected. Ditto for statuses.
#----------------------------------------------------------------------
if type(groups) in (type(""), type(u"")):
    groups = [groups]
if type(types) in (type(""), type(u"")):
    types = [types]

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

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not lang:
    jscript = """
<style type="text/css">
</style>

<script language='JavaScript' src='/js/scriptaculous/prototype.js'></script>
<script language='JavaScript' src='/js/scriptaculous/scriptaculous.js'></script>
<script type="text/javascript">

Event.observe(window, 'load', function(){
    checkAllEnglish(0);
    checkAllSpanish(0);
    checkAllTypes(0);
    disableAllEnglish(1);
    disableAllSpanish(1);
    disableAllTypes(1);
    $('All English').disabled = 0;
    $('All English').checked = 1;
    $('All Types').disabled = 0;
    $('All Types').checked = 1;
    $('English').checked = 1;
});

function checkAllEnglish(checked){
    $('All English').checked = checked;
    $('Adult Treatment').checked = checked;
    $('Genetics').checked = checked;
    $('Complementary and Alternative Medicine').checked = checked;
    $('Pediatric Treatment').checked = checked;
    $('Screening and Prevention').checked = checked;
    $('Supportive Care').checked = checked;    
}

function disableAllEnglish(disabled){
    $('All English').disabled = disabled;
    $('Adult Treatment').disabled = disabled;
    $('Genetics').disabled = disabled;
    $('Complementary and Alternative Medicine').disabled = disabled;
    $('Pediatric Treatment').disabled = disabled;
    $('Screening and Prevention').disabled = disabled;
    $('Supportive Care').disabled = disabled;
}

function disableAllSpanish(disabled){
    $('All Spanish').disabled = disabled;
    $('Spanish Adult Treatment').disabled = disabled;
    $('Spanish Pediatric Treatment').disabled = disabled;
    $('Spanish Supportive Care').disabled = disabled;
}

function checkAllSpanish(checked){
    $('All Spanish').checked = checked;
    $('Spanish Adult Treatment').checked = checked;
    $('Spanish Pediatric Treatment').checked = checked;
    $('Spanish Supportive Care').checked = checked;
}

function disableAllTypes(disabled){
    $('All Types').disabled = disabled;
    $('Book').disabled = disabled;
    $('Book [Internet]').disabled = disabled;
    $('Book chapter').disabled = disabled;
    $('Book chapter [Internet]').disabled = disabled;
    $('Abstract').disabled = disabled;
    $('Abstract [Internet]').disabled = disabled;
    $('Database').disabled = disabled;
    $('Database entry').disabled = disabled;
    $('Internet').disabled = disabled;
    $('Meeting Paper').disabled = disabled;
    $('Meeting Paper [Internet]').disabled = disabled;
}

function checkAllTypes(checked){
    $('All Types').checked = checked;
    $('Book').checked = checked;
    $('Book [Internet]').checked = checked;
    $('Book chapter').checked = checked;
    $('Book chapter [Internet]').checked = checked;
    $('Abstract').checked = checked;
    $('Abstract [Internet]').checked = checked;
    $('Database').checked = checked;
    $('Database entry').checked = checked;
    $('Internet').checked = checked;
    $('Meeting Paper').checked = checked;
    $('Meeting Paper [Internet]').checked = checked;
}

function langClicked(lang){
    disableAllEnglish(1);
    disableAllSpanish(1);
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
    elem = $('All English')
    if (elem.checked){
        disableAllEnglish(1);
        elem.disabled = false;
        checkAllEnglish(0);
        elem.checked = 1;
    }else{
        disableAllEnglish(0);
        elem.checked = 0;
    }
}

function allSpanishClicked(){
    elem = $('All Spanish')
    if (elem.checked){
        disableAllSpanish(1);
        elem.disabled = false;
        checkAllSpanish(0);
        elem.checked = 1;
    }else{
        disableAllSpanish(0);
        elem.checked = 0;
    }
}

function allTypesClicked(){
    elem = $('All Types')
    if (elem.checked){
        disableAllTypes(1);
        elem.disabled = false;
        checkAllTypes(0);
        elem.checked = 1;
    }else{
        disableAllTypes(0);
        elem.checked = 0;
    }
}

</script>
"""
    header = cdrcgi.header(title, title, instr, script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1,stylesheet = jscript)
    form   = """\
   <input type='hidden' name='%s' value='%s'>
   <table border='0'>
    <tr>
     <td colspan='3'>
      %s<br><br>
     </td>
    </tr>
   </table>
 
    <table>
   <tr>
     <td width=100>
      <input id='English' name='lang' type='radio' value='English' onClick="langClicked('English');" CHECKED><b>English</b></input>
     </td>
     <td>
      <b>Select PDQ Summaries: (one or more)</b>
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <input type='checkbox' id='All English' name='grp' value='All English' onClick="allEnglishClicked();" CHECKED>
       <b>All English</b></input><br>
      <input type='checkbox' id='Adult Treatment' name='grp' value='Adult Treatment'>
       <b>Adult Treatment</b></input><br>
      <input type='checkbox' id='Genetics' name='grp' value='Genetics'>
       <b>Cancer Genetics</b></input><br>
      <input type='checkbox' name='grp' id='Complementary and Alternative Medicine'
             value='Complementary and Alternative Medicine'>
       <b>Complementary and Alternative Medicine</b></input><br>
      <input type='checkbox' id='Pediatric Treatment' name='grp' value='Pediatric Treatment'>
       <b>Pediatric Treatment</b></input><br>
      <input type='checkbox' id='Screening and Prevention' name='grp' value='Screening and Prevention'>
       <b>Screening and Prevention</b></input><br>
      <input type='checkbox' id='Supportive Care' name='grp' value='Supportive Care'>
       <b>Supportive Care</b><br></input><br>
     </td>
    </tr>
    <tr>
     <td width=100>
      <input id='Spanish' name='lang' type='radio' value='Spanish' onClick="langClicked('Spanish');"><b>Spanish</b></input>
     </td>
     <td>
      <b>Select PDQ Summaries: (one or more)</b>
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <input type='checkbox' id='All Spanish' name='grp' value='All Spanish' onClick="allSpanishClicked();">
       <b>All Spanish</b></input><br>
      <input type='checkbox' id='Spanish Adult Treatment' name='grp' value='Spanish Adult Treatment'>
       <b>Adult Treatment</b></input><br>
      <input type='checkbox' id='Spanish Pediatric Treatment' name='grp' value='Spanish Pediatric Treatment'>
       <b>Pediatric Treatment</b></input><br>
      <input type='checkbox' id='Spanish Supportive Care' name='grp' value='Spanish Supportive Care'>
       <b>Supportive Care</b></input><br><br>
     </td>
    </tr>

    <tr>
     <td colspan=2>
      <b>Select Citation Type: (one or more)</b>
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <input id='All Types' type='checkbox' name='type' value='All Types' onClick="allTypesClicked();" CHECKED>
       <b>All Types</b><br>
      <input id='Book' type='checkbox' name='type' value='Book'>
       <b>Book</b><br>
      <input id='Book [Internet]' type='checkbox' name='type' value='Book [Internet]'>
       <b>Book [Internet]</b><br>
      <input id='Book chapter' type='checkbox' name='type' value='Book chapter'>
       <b>Book chapter</b><br>
       <input id='Book chapter [Internet]' type='checkbox' name='type' value='Book chapter [Internet]'>
       <b>Book chapter [Internet]</b><br>
       <input id='Abstract' type='checkbox' name='type' value='Abstract'>
       <b>Abstract</b><br>
       <input id='Abstract [Internet]' type='checkbox' name='type' value='Abstract [Internet]'>
       <b>Abstract [Internet]</b><br>
       <input id='Database' type='checkbox' name='type' value='Database'>
       <b>Database</b><br>
       <input id='Database entry' type='checkbox' name='type' value='Database entry'>
       <b>Database entry</b><br>
       <input id='Internet' type='checkbox' name='type' value='Internet'>
       <b>Internet</b><br>
       <input id='Meeting Paper' type='checkbox' name='type' value='Meeting Paper'>
       <b>Meeting Paper</b><br>
       <input id='Meeting Paper [Internet]' type='checkbox' name='type' value='Meeting Paper [Internet]'>
       <b>Meeting Paper [Internet]</b><br>
     </td>
    </tr>    
   </table>

  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, dateString)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Create the selection criteria based on the groups picked by the user
# But the decision will be based on the content of the board instead
# of the SummaryType.
# Based on the SummaryType selected on the form the boardPick list is
# being created including the Editorial and Advisory board for each
# type.  These board IDs can then be decoded into the proper 
# heading to be used for each selected summary type.
# --------------------------------------------------------------------
boardPick = ''
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

typesPick=''
for i in range(len(types)):
    typesPick += "'" + types[i] + "',"

#------------------------------------
# build the query
#------------------------------------
def getQuery(lang):
    query = [u"""SELECT distinct qt.doc_id as cdrid, title.value as summaryTitle, secTitle.value as summarySecTitle,"""]
    query.append(u"""qcitationtype.value as citationType, qt.int_val as citCDRID, qcitationtitle.value as citationTitle
      FROM query_term qt
      JOIN query_term title ON qt.doc_id = title.doc_id
      JOIN query_term qcitationtype ON qt.int_val = qcitationtype.doc_id
      JOIN query_term qcitationtitle ON qt.int_val = qcitationtitle.doc_id
      JOIN query_term secTitle ON qt.doc_id = secTitle.doc_id
      JOIN query_term lang ON qt.doc_id = lang.doc_id """)
    
    if lang == 'English':
        query.append(u""" JOIN query_term board ON qt.doc_id = board.doc_id """)
    else:
        query.append(u""" JOIN query_term qtrans ON qtrans.doc_id = qt.doc_id
                     JOIN query_term board ON qtrans.int_val = board.doc_id """)
    
    query.append(u""" WHERE qt.path like '%CitationLink/@cdr:ref' """)

    if lang == 'Spanish':
        query.append(u""" AND qtrans.path = '/Summary/TranslationOf/@cdr:ref' """)

    query.append(u"""\
    AND title.path = '/Summary/SummaryTitle'
    AND qcitationtype.path = '/Citation/PDQCitation/CitationType'
    AND qcitationtitle.path = '/Citation/PDQCitation/CitationTitle' 
    AND secTitle.path like '/Summary/%SummarySection/Title' 
    AND LEFT(secTitle.node_loc,len(secTitle.node_loc)-4) =  LEFT(qt.node_loc,len(secTitle.node_loc)-4) 
    AND board.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref' """)

    allStr = "All " + lang
    if boardPick.find(allStr) == -1:
        query.append(u""" AND board.value in (""")
        query.append(boardPick[:-2])
        query.append(u""") """)

    if typesPick.find("All Types") == -1:
        query.append(u""" AND qcitationtype.value in (""")
        query.append(typesPick[:-1])
        query.append(u""") """)
    else:
        query.append(u""" AND qcitationtype.value not like 'Journal%' AND qcitationtype.value not like 'Proceeding%'""")
    
    query.append(u"""
    AND lang.path = '/Summary/SummaryMetaData/SummaryLanguage'
    AND lang.value = '""")

    query.append(lang)
    
    query.append(u"""'
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

dataRows = []
citcdrids = []

# -------------------------------------------------------------
# Put all the pieces together for the SELECT statement
# -------------------------------------------------------------

query = getQuery(lang) + " ORDER BY cdrid"

#cdrcgi.bail(query)

if not query:
    cdrcgi.bail('No query criteria specified')

#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    cursor.execute(query,timeout=300)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Summary documents: %s' % info[1][0])
     
if not rows:
    cdrcgi.bail('No Records Found for Selection')

for cdrid,summaryTitle,summarySecTitle,citationType,citCDRID,citationTitle in rows:
    dataRows.append(dataRow(cdrid,summaryTitle,summarySecTitle,citationType,citCDRID,citationTitle))
    if citCDRID not in citcdrids:
        citcdrids.append(citCDRID)

for citcdrid in citcdrids:
    citdocId = cdr.normalize(citcdrid)
    filter = ['set:Denormalization Citation Set',
              'name:Copy XML for Citation QC Report']
    doc = cdr.filterDoc(session,filter,docId=citdocId)
    filterResult = doc[0]
    dom = xml.dom.minidom.parseString(filterResult)
    docElem = dom.documentElement
    elems = docElem.getElementsByTagName('FormattedReference')
    for elem in elems:
        for child in elem.childNodes:
            if child.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                formattedReference = child.nodeValue
    
    for datarow in dataRows:
        if datarow.citCDRID == citcdrid:
            datarow.addPubDetails(formattedReference)

cursor.close()
cursor = None

# out put the results table
header = cdrcgi.header(title, title, instr, script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1)
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
    Summaries with Non-Journal Article Citations Report</br>
    <div style="text-align: center; font-family: Verdana, Tahoma, sans-serif; font-size: 11pt; font-weight: normal; color: #553;">%s</div>
    </p>
   
   <table>
   <tr>
   <th  class="cdrTable">cdrid</th>
   <th  class="cdrTable">Summary Title</th>
   <th  class="cdrTable">Summary Sec Title</th>
   <th  class="cdrTable">Citation Type</th>
   <th  class="cdrTable">Citation CDRID</th>
   <th  class="cdrTable">Doc Title</th>
   <th  class="cdrTable">Publication Details/Other Publication Info</th>
   </tr>
   """ % (cdrcgi.SESSION, session, dateString)]
cssClass = 'cdrTableEven'
for dataRow in dataRows:
    form.append(u"<tr>")
    form.append(u"""<td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td>"""
                %(cssClass,dataRow.cdrid,cssClass,dataRow.summaryTitle,cssClass,dataRow.summarySecTitle))
    form.append(u"""<td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td>"""
                % (cssClass,dataRow.citationType,cssClass,dataRow.citCDRID,cssClass,dataRow.citationTitle))
    form.append(u"""<td class="%s">%s</td>"""
                % (cssClass,dataRow.pubDetails))
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