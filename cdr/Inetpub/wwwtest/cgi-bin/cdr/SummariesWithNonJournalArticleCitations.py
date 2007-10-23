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
#types.append('Book')
#types.append('Book chapter')
#session   = '4713A376-6D965A-248-VRORIB5JL0KP'
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
        self.pubDetails = 'pub Details'
    
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
    header = cdrcgi.header(title, title, instr, script,
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1)
    form   = """\
   <input type='hidden' name='%s' value='%s'>
   <table border='0'>
    <tr>
     <td colspan='3'>
      %s<br><br>
     </td>
    </tr>
   </table>
 
   <table border = '0'>
    <tr>
     <td width=100>
      <input name='lang' type='radio' value='English' CHECKED><b>English</b>
     </td>
     <td>
      <b>Select PDQ Summaries: (one or more)</b>
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <input type='checkbox' name='grp' value='All English' CHECKED>
       <b>All English</b><br>
      <input type='checkbox' name='grp' value='Adult Treatment'>
       <b>Adult Treatment</b><br>
      <input type='checkbox' name='grp' value='Genetics'>
       <b>Cancer Genetics</b><br>
      <input type='checkbox' name='grp'
             value='Complementary and Alternative Medicine'>
       <b>Complementary and Alternative Medicine</b><br>
      <input type='checkbox' name='grp' value='Pediatric Treatment'>
       <b>Pediatric Treatment</b><br>
      <input type='checkbox' name='grp' value='Screening and Prevention'>
       <b>Screening and Prevention</b><br>
      <input type='checkbox' name='grp' value='Supportive Care'>
       <b>Supportive Care</b><br><br>
     </td>
    </tr>
    <tr>
     <td width=100>
      <input name='lang' type='radio' value='Spanish'><b>Spanish</b>
     </td>
     <td>
      <b>Select PDQ Summaries: (one or more)</b>
     </td>
    </tr>
    <tr>
     <td></td>
     <td>
      <input type='checkbox' name='grp' value='All Spanish'>
       <b>All Spanish</b><br>
      <input type='checkbox' name='grp' value='Spanish Adult Treatment'>
       <b>Adult Treatment</b><br>
      <input type='checkbox' name='grp' value='Spanish Pediatric Treatment'>
       <b>Pediatric Treatment</b><br>
      <input type='checkbox' name='grp' value='Spanish Supportive Care'>
       <b>Supportive Care</b><br><br>
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
      <input type='checkbox' name='type' value='All Types' CHECKED>
       <b>All Types</b><br>
      <input type='checkbox' name='type' value='Book'>
       <b>Book</b><br>
      <input type='checkbox' name='type' value='Book [Internet]'>
       <b>Book [Internet]</b><br>
      <input type='checkbox' name='type' value='Book chapter'>
       <b>Book chapter</b><br>
       <input type='checkbox' name='type' value='Book chapter [Internet]'>
       <b>Book chapter [Internet]</b><br>
       <input type='checkbox' name='type' value='Abstract'>
       <b>Abstract</b><br>
       <input type='checkbox' name='type' value='Abstract [Internet]'>
       <b>Abstract [Internet]</b><br>
       <input type='checkbox' name='type' value='Database'>
       <b>Database</b><br>
       <input type='checkbox' name='type' value='Database entry'>
       <b>Database entry</b><br>
       <input type='checkbox' name='type' value='Internet'>
       <b>Internet</b><br>
       <input type='checkbox' name='type' value='Meeting Paper'>
       <b>Meeting Paper</b><br>
       <input type='checkbox' name='type' value='Meeting Paper [Internet]'>
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

def getPubDetails(citcdrid,dom):
    pubDetails = ''
    docElem = dom.documentElement
    
    elems = docElem.getElementsByTagName('CollectiveName')
    for elem in elems:
        for child in elem.childNodes:
            if child.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                pubDetails += child.nodeValue
                pubDetails += ':'
    elems = docElem.getElementsByTagName('CitationTitle')
    for elem in elems:
        for child in elem.childNodes:
            if child.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                pubDetails += child.nodeValue
                pubDetails += '.'
    elems = docElem.getElementsByTagName('PublicationInformation')
    for elem in elems:
        for child in elem.childNodes:
            if child.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                pubDetails += child.nodeValue
                pubDetails += '.'

    for datarow in dataRows:
        if datarow.citCDRID == citcdrid:
            datarow.addPubDetails(pubDetails)
    return
      
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
    doc = cdr.getDoc(session, citdocId, checkout = 'N')
    if doc.startswith("<Errors"):
        cdrcgi.bail("<error>Unable to retrieve %s : %s" % cdrid,doc)
    doc = cdr.getDoc(session, citdocId, checkout = 'N', getObject=1)
    dom = xml.dom.minidom.parseString(doc.xml)
    getPubDetails(citcdrid,dom)

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
    form.append(u"""<td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td>"""
                % (cssClass,dataRow.citationType,cssClass,dataRow.citCDRID,cssClass,dataRow.citationTitle,cssClass,dataRow.pubDetails))
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