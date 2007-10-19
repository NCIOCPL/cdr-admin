#----------------------------------------------------------------------
#
# $Id: TermNCITDrugUpdateAll.py
#
# Check all Drug/Agent terms and update with data from the NCI
# Thesaurus
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, time, NCIThes, random

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
#submit    = fields and fields.getvalue("Submit")     or None
request   = cdrcgi.getRequest(fields)
getThingsToUpdate = fields and fields.getvalue("GetThingsToUpdate") or None
parm_doc_id  = fields and fields.getvalue("Doc_id") or None
parm_concept  = fields and fields.getvalue("Concept") or None
doUpdate   = fields and fields.getvalue("DoUpdate") or 0
title     = "CDR Administration"
instr     = "Update all Drug/Agent Terms from NCI Thesaurus"
script    = "TermNCITDrugUpdateAll.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

#submit = 0
doUpdate = int(doUpdate)
#if request:
#    submit = (request == "Submit")

#--------DEBUG-------------
#getThingsToUpdate = 1
#session='47174BCF-B730E4-248-DC5VIFXHGDQV'
#parm_concept = 'C2203'
#parm_row = 8
#parm_doc_id = 37776
#--------------------------

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

class docConceptPair:
    def __init__(self,doc_id,concept):
        self.doc_id = doc_id
        self.concept = concept

if getThingsToUpdate:
    #first, get a list of all the drug/agent concept codes
    query="""SELECT distinct qt.doc_id,qt.value
               FROM query_term qt
               JOIN query_term semantic
                 ON semantic.doc_id = qt.doc_id
              WHERE qt.path = '/Term/OtherName/SourceInformation/VocabularySource/SourceTermId'
                AND semantic.path = '/Term/SemanticType/@cdr:ref'
                AND semantic.int_val = 256166
           ORDER BY qt.doc_id"""

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

    docConceptPairs = []

    for doc_id,value in rows:
        value = value.strip()
        if value[0] == 'C':
            docConceptPairs.append(docConceptPair(doc_id,value))

    cursor.close()
    cursor = None

    json = "["
    for docConceptPair in docConceptPairs:
        json += "['%s','%s']," % (docConceptPair.doc_id,docConceptPair.concept)
    json = json[:len(json)-1]
    json += "]"
    cdrcgi.sendPage(json)

if parm_concept and parm_doc_id:
    if doUpdate == 1:
        result = NCIThes.updateTerm(session,parm_doc_id,parm_concept,doUpdate=1)
    else:
        result = NCIThes.updateTerm(session,parm_doc_id,parm_concept,doUpdate=0)

    result = result.replace("""'""","""&quot""");
    
    col1href = """%s/QcReport.py?DocId=%s&Session=%s""" % (cdrcgi.BASE,cdr.normalize(parm_doc_id),session)
    col1val = """%s""" % parm_doc_id
    col2href = """http://nciterms.nci.nih.gov/NCIBrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=%s&bookmarktag=2""" % parm_concept
    col2val = """%s""" % parm_concept
    col3 = result

    json = """[['Col1href','%s'],""" % col1href
    json += """['Col1val','%s'],""" % col1val
    json += """['Col2href','%s'],""" % col2href
    json += """['Col2val','%s'],""" % col2val
    json += """['Col3','%s']]""" % col3
    f = open("d:\\cdr\\output\\debug.txt","a")
    f.write(json)
    f.write("\n\n\n")
    f.close()
    cdrcgi.sendPage(json)

#----------------------------------------------------------------------
# Show the page
#----------------------------------------------------------------------
jscript = """
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
}
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
}
a:hover 
{
    color: white; 
    background-color:red; 
    text-decoration: underline;
    font-weight: bold;
}
a.selected:link 
{
    color: purple;
    font-style:italic;
    text-decoration: none;
    font-weight: bold;
}
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
}
a.selected:hover 
{
    color: white; 
    background-color:purple;
    font-style:italic;
    text-decoration: underline;
    font-weight: bold;
}
</style>
<script language='JavaScript' src='/js/scriptaculous/prototype.js'></script>
<script language='JavaScript' src='/js/scriptaculous/scriptaculous.js'></script>
<script type="text/javascript">

var ajaxResponse = '';
var rowNum = 0;
var totalCount = 0;
var className = 'cdrTableEven';
var errorOccurred = false;
var beginBlock = 0;
var endBlock = 0;
var blockSize = 10;
var pairs;
var numErrorMsgs = 0;

Event.observe(window, 'load', function(){
    new Effect.Highlight(statusTxt);
});

function checkUpdate(){
    errorOccurred = false;
    row=0;
    numErrorMsgs = 0
    updateStatus('Getting a list of document IDs and concept pairs.');
    getListOfThingsToUpdate();
    pairs = eval("(" + ajaxResponse + ")");
    totalCount = pairs.length;
    updateStatus('Done obtaining a list of document IDs and concept pairs. ' + totalCount + ' found.');
    $('resultTable').style.visibility='visible';
    $('spinImage').style.visibility='visible';
    $('checkUpdateButton').style.visibility='hidden';
    
    endBlock = beginBlock + blockSize;
    if ( endBlock > totalCount )
        endBlock = totalCount

    runNextBlock();
}

function runNextBlock(){
    for (var i=beginBlock; i<endBlock; i++)
        doUpdate(pairs[i][0],pairs[i][1]);
}

function doUpdate(doc_id,concept){
    url = "%s/TermNCITDrugUpdateAll.py?DoUpdate=0&Doc_id=" + doc_id + "&Concept=" + concept + "&random=%s&Session=%s";
    doAjaxForRow(url);
}

function updateStatus(text){
status = text
$('statusTxt').innerHTML = text;
}

function getListOfThingsToUpdate(){
    url = "%s/TermNCITDrugUpdateAll.py?GetThingsToUpdate=1&rand=%s";
    doAjaxForList(url);
}

function doAjaxForList(url){
    new Ajax.Request(url,{method:'get',onComplete:handleAjaxResponseForList,onFailure:handleAjaxFailure,onException:handleAjaxException,asynchronous:false});
}

function doAjaxForRow(url){
    new Ajax.Request(url,{method:'get',onComplete:handleAjaxResponseForRow,onFailure:handleAjaxFailure,onException:handleAjaxException,asynchronous:true});
}
   
function handleAjaxResponseForList(resultObj){
    ajaxResponse = resultObj.responseText;
}

function handleAjaxResponseForRow(resultObj){
    AddDataRow(resultObj.responseText);
}

function handleAjaxFailure(resultObj){
    numErrorMsgs++;
    if (errorOccurred == false)
        alert('Ajax Failure' + resultObj.responseText);
    errorOccurred = true;
}

function handleAjaxException(instance,ex){
    numErrorMsgs++;
    if (errorOccurred == false)
        alert('Exception: ' + ex.name + ' ' + ex.message);
    errorOccurred = true;
}

function AddDataRow(jsonText){
    var elemPairs = eval("(" + jsonText + ")");
    rowNum = rowNum+1;
    if (className == 'cdrTableEven')
        className = 'cdrTableOdd';
    else
        className = 'cdrTableEven';

    stsTxt = 'Updated row ' + rowNum + ' of ' + totalCount;
    updateStatus(stsTxt);
    
    var tbodyElem = $('resultTable').getElementsByTagName('TBODY')[0];
    var row = document.createElement("TR");
    var td1 = document.createElement("TD");
    var td1a = document.createElement("A");
    var td2 = document.createElement("TD");
    var td2a = document.createElement("A");
    var td3 = document.createElement("TD");
    //td1.setAttribute((document.all ? 'className' : 'class'),className);
    //td2.setAttribute((document.all ? 'className' : 'class'),className);
    //td3.setAttribute((document.all ? 'className' : 'class'),className);
    td1.className = className;
    td2.className = className;
    td3.className = className;

    for (var i=0; i<elemPairs.length; i++){
        if ( elemPairs[i][0] == 'Col1href' )
            td1a.setAttribute('href',elemPairs[i][1]);
        else if ( elemPairs[i][0] == 'Col1val' )
            td1a.appendChild(document.createTextNode(elemPairs[i][1]));
        else if ( elemPairs[i][0] == 'Col2href' )
            td2a.setAttribute('href',pairs[i][1]);
        else if ( elemPairs[i][0] == 'Col2val' )
            td2a.appendChild(document.createTextNode(elemPairs[i][1]));
        else if ( elemPairs[i][0] == 'Col3' )
            td3.appendChild(document.createTextNode(elemPairs[i][1]));
    }

    td1a.setAttribute('target','_blank');
    td2a.setAttribute('target','_blank');
            
    td1.appendChild(td1a);
    row.appendChild(td1);
    td2.appendChild(td2a);
    row.appendChild(td2);
    row.appendChild(td3);
    tbodyElem.appendChild(row);

    if (rowNum + numErrorMsgs == totalCount)
    {
        updateStatus('Done. Updated ' + rowNum + ' of ' + totalCount + ' (' + numErrorMsgs + ' errors)');
        $('checkUpdateButton').style.visibility='visible';
        $('spinImage').style.visibility='hidden';
    }
    else if (rowNum + numErrorMsgs == endBlock-1)
    {
        beginBlock = endBlock;
        endBlock = beginBlock + blockSize;
        if ( endBlock > totalCount )
            endBlock = totalCount
        runNextBlock();
    }
}
</script>
""" % (cdrcgi.BASE,random.randint(1,99999999),session,cdrcgi.BASE,random.randint(1,99999999))

header = cdrcgi.header(title, title, instr, script,
                           (SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1,stylesheet = jscript)

form   = """\
   <input type='hidden' name='%s' value='%s'>
   
<table align=center>
<tr>
<td width=5%%>
<IMG SRC="/images/spin.gif" id='spinImage' style="visibility:hidden">
</td>
<td width = 95%%>
   <p id = 'statusTxt' align = center>
   Press the check update button to see what will be updated.
   </p>
</td>
</tr>
<tr>
<td></td>
<td align=center>
   <button id='checkUpdateButton' onClick='checkUpdate();return false;'>Check Update</button>
</td>
</tr>

<table id='resultTable' style="visibility:hidden">
   <tr>
   <th  class="cdrTable">Doc ID</th>
   <th  class="cdrTable">NCIT Concept</th>
   <th  class="cdrTable">Results</th>
   </tr>
</table>
   
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form)
