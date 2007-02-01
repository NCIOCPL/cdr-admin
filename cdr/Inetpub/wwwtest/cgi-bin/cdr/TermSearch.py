#----------------------------------------------------------------------
#
# $Id: TermSearch.py,v 1.8 2007-02-01 13:32:13 bkline Exp $
#
# Prototype for duplicate-checking interface for Term documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2005/09/09 20:11:20  bkline
# More fixes to mapping strings.
#
# Revision 1.6  2005/09/01 11:50:53  bkline
# Corrected values incorrectly set in the mapping spec document.
#
# Revision 1.5  2005/08/29 17:07:40  bkline
# Added code to import new Term document from NCI thesaurus concept.
#
# Revision 1.4  2003/08/25 20:25:54  bkline
# Plugged in named filter set.
#
# Revision 1.3  2002/02/20 03:57:33  bkline
# Fixed bail() -> cdrcgi.bail().
#
# Revision 1.2  2002/02/14 19:34:52  bkline
# Replaced hardwired filter ID with filter name.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb, xml.dom.minidom, urllib, time

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
boolOp      = fields and fields.getvalue("Boolean")         or "AND"
prefTerm    = fields and fields.getvalue("PrefTerm")        or None
otherName   = fields and fields.getvalue("OtherName")       or None
termType    = fields and fields.getvalue("TermType")        or None
semType     = fields and fields.getvalue("SemType")         or None
submit      = fields and fields.getvalue("SubmitButton")    or None
impReq      = fields and fields.getvalue("ImportButton")    or None
help        = fields and fields.getvalue("HelpButton")      or None
srchThes    = fields and fields.getvalue("SearchThesaurus") or None
conceptCode = fields and fields.getvalue("ConceptCode")     or None
subtitle    = "Term"
replaceId   = None
valErrors   = None

if help: 
    cdrcgi.bail("Sorry, help for this interface has not yet "
                "been developed.")

#----------------------------------------------------------------------
# Redirect to Thesaurus searching if requested (in a different window).
#----------------------------------------------------------------------
thesaurusSearchUrl = ("http://nciterms.nci.nih.gov/NCIBrowser"
                      "/ConceptReport.jsp?"
                      "dictionary=PRE_NCI_Thesaurus&code=C1908")
if srchThes and False:
    print ("Location:http://nciterms.nci.nih.gov"
           #"/NCIBrowser/Connect.do"
           #"?dictionary=PRE_NCI_Thesaurus&bookmarktag=1\n")
           "/NCIBrowser/ConceptReport.jsp?"
           "dictionary=PRE_NCI_Thesaurus&code=C1908")
    sys.exit(0)

#----------------------------------------------------------------------
# Prepare string for living in an XML document.
#----------------------------------------------------------------------
def fix(s):
    return s and cgi.escape(s) or u''

def extractError(node):
    return node.toxml()

def mapType(nciThesaurusType):
    return {
        "PT"               : "Synonym", # "Preferred term",
        "AB"               : "Abbreviation",
        "AQ"               : "Obsolete name",
        "BR"               : "US brand name",
        "CN"               : "Code name",
        "FB"               : "Foreign brand name",
        "SN"               : "Chemical structure name",
        "SY"               : "Synonym",
        "INDCode"          : "IND code",
        "NscCode"          : "NSC code",
        "CAS_Registry_Name": "CAS Registry name" 
    }.get(nciThesaurusType, "????")

def makeOtherName(name, termType, sourceTermType, code = None):
    xmlFrag = u"""\
 <OtherName>
  <OtherTermName>%s</OtherTermName>
  <OtherNameType>%s</OtherNameType>
  <SourceInformation>
   <VocabularySource>
    <SourceCode>NCI Thesaurus</SourceCode>
    <SourceTermType>%s</SourceTermType>
""" % (fix(name), fix(termType), fix(sourceTermType))
    if code:
        xmlFrag += """\
    <SourceTermId>%s</SourceTermId>
""" % fix(code)
    xmlFrag += """\
   </VocabularySource>
  </SourceInformation>
  <ReviewStatus>Reviewed</ReviewStatus>
 </OtherName>
"""
    return xmlFrag

#----------------------------------------------------------------------
# Object for a thesaurus concept definition.
#----------------------------------------------------------------------
class Definition:
    pattern = re.compile(u"(<def-source>(.*)</def-source>)?"
                         u"(<def-definition>(.*)</def-definition>)?",
                         re.DOTALL)
    def __init__(self, value):
        match = Definition.pattern.search(value)
        self.source = None
        self.text   = None
        if match:
            self.source = match.group(2)
            self.text   = match.group(4)
    def toXml(self):
        return """\
 <Definition>
  <DefinitionText>%s</DefinitionText>
  <DefinitionType>Health professional</DefinitionType>
  <DefinitionSource>
   <DefinitionSourceName>NCI Thesaurus</DefinitionSourceName>
  </DefinitionSource>
  <ReviewStatus>Reviewed</ReviewStatus>
 </Definition>
""" % fix(self.text or u'')

#----------------------------------------------------------------------
# Object for an articulated synonym from the NCI thesaurus.
#----------------------------------------------------------------------
class FullSynonym:
    pattern = re.compile(u"(<term-name>(.*)</term-name>)?"
                         u"(<term-group>(.*)</term-group>)?"
                         u"(<term-source>(.*)</term-source>)?"
                         u"(<source-code>(.*)</source-code>)?",
                         re.DOTALL)
    def __init__(self, value):
        match = FullSynonym.pattern.search(value)
        self.termName   = None
        self.termGroup  = None
        self.termSource = None
        self.sourceCode = None
        if match:
            self.termName   = match.group(2)
            self.termGroup  = match.group(4)
            self.termSource = match.group(6)
            self.sourceCode = match.group(8)

#----------------------------------------------------------------------
# Object for a NCI Thesaurus concept.
#----------------------------------------------------------------------
class Concept:
    def __init__(self, node):
        if node.nodeName != 'Concept':
            cdrcgi.bail(extractError(node))
        self.code          = node.getAttribute('code')
        self.preferredName = None
        self.semanticType  = None
        self.fullSyn       = []
        self.definitions   = []
        self.synonyms      = []
        self.casCodes      = []
        self.nscCodes      = []
        self.indCodes      = []
        for child in node.childNodes:
            if child.nodeName == 'Property':
                name = None
                value = None
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'Name':
                        name = cdr.getTextContent(grandchild)
                    elif grandchild.nodeName == 'Value':
                        value= cdr.getTextContent(grandchild)
                if name == 'Preferred_Name':
                    self.preferredName = value
                elif name == 'Semantic_Type':
                    self.semanticType = value
                elif name == 'Synonym':
                    self.synonyms.append(value)
                elif name == 'CAS_Registry':
                    self.casCodes.append(value)
                elif name == 'NSC_Code':
                    self.nscCodes.append(value)
                elif name == 'IND_Code':
                    self.indCodes.append(value)
                elif name == 'DEFINITION':
                    self.definitions.append(Definition(value))
                elif name == 'FULL_SYN':
                    self.fullSyn.append(FullSynonym(value))

#----------------------------------------------------------------------
# Retrieve a concept document from the NCI Thesaurus.
#----------------------------------------------------------------------
def fetchConcept(code):
    #cmd = ("java -classpath d:/cdr/lib;d:/usr/lib/evs-client.jar;"
    #       "d:/usr/lib/log4j.jar "
    #       "RetrieveConceptFromEvs %s" % code)
    #result = cdr.runCommand(cmd)
    #if result.code:
    #    cdrcgi.bail("Failure fetching concept: %s" %
    #                (result.output or "unknown failure"))
    url = ("http://cabio-qa.nci.nih.gov/cacore32/GetXML?"
           "query=DescLogicConcept&DescLogicConcept[@code=%s]" % code)
    tries = 3
    code = code.strip()
    while tries:
        try:
            urlObj = urllib.urlopen(url)
            docXml = urlObj.read()
            break
        except Exception, e:
            tries -= 1
            if not tries:
                cdrcgi.bail("EVS server unavailable: %s" % e)
    filt = ["name:EVS Concept Filter"]
    result = cdr.filterDoc('guest', filt, doc = docXml)
    if type(result) in (str, unicode):
        now = time.strftime("%Y%m%d%H%M%S")
        f = open("d:/tmp/ConceptDoc-%s-%s.xml" % (code, now), "wb")
        f.write(docXml)
        f.close()
        cdrcgi.bail("Error in EVS response: %s" % result)
    docXml = result[0]
    try:
        #docXml = result.output
        #open("d:/tmp/ConceptDocs.xml", "a").write(docXml)
        dom = xml.dom.minidom.parseString(docXml)
        return Concept(dom.documentElement)
    except Exception, e:
        cdrcgi.bail("Failure parsing concept: %s" % str(e))

#----------------------------------------------------------------------
# Generate picklist for term types.
#----------------------------------------------------------------------
def termTypeList(conn, fName):
    try:
        cursor = conn.cursor()
        query  = """\
        SELECT DISTINCT value
          FROM query_term
         WHERE path = '/Term/TermType/TermTypeName'
"""
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving term type list from CDR: %s' % 
                    info[1][0])
    html = """\
      <SELECT NAME='%s'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
""" % fName
    for row in rows:
        html += """\
       <OPTION VALUE='%s'>%s &nbsp;</OPTION>
""" % (row[0], row[0])
    html += """\
      </SELECT>
"""
    return html

#----------------------------------------------------------------------
# Generate picklist for semantic types.
#----------------------------------------------------------------------
def semanticTypeList(conn, fName):
    try:
        cursor = conn.cursor()
        query  = """\
        SELECT d.id, d.title
          FROM document d
         WHERE EXISTS (SELECT *
                         FROM query_term q
                        WHERE q.int_val = d.id
                          AND q.path = '/Term/SemanticType/@cdr:ref')
      ORDER BY d.title
"""
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving semantic type list from CDR: %s'
                    % info[1][0])
    html = """\
      <SELECT NAME='%s'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
""" % fName
    for row in rows:
        html += """\
       <OPTION VALUE='CDR%010d'>%s &nbsp;</OPTION>
""" % (row[0], row[1])
    html += """\
      </SELECT>
"""
    return html

#----------------------------------------------------------------------
# Parse out the errors for display.
#----------------------------------------------------------------------
def formatErrors(str):
    result = ""
    for error in re.findall("<Err>(.*?)</Err>", str):
        result += (cgi.escape("%s") % error) + "<br>\n"
    if type(result) != unicode:
        result = unicode(result, "utf-8")
    return result
    
#----------------------------------------------------------------------
# See if citation already exists.
#----------------------------------------------------------------------
def findExistingConcept(code):
    try:
        cursor = conn.cursor()
        cursor.execute("""\
                SELECT c.doc_id
                  FROM query_term c
                  JOIN query_term t
                    ON c.doc_id = t.doc_id
                   AND LEFT(c.node_loc, 8) = LEFT(t.node_loc, 8)
                 WHERE c.path = '/Term/OtherName/SourceInformation'
                              + '/VocabularySource/SourceTermId'
                   AND t.path = '/Term/OtherName/SourceInformation'
                              + '/VocabularySource/SourceCode'
                   AND t.value = 'NCI'
                   AND c.value = ?""", code)
        rows = cursor.fetchall()
        if not rows: return None
        return rows[0][0]
    except cdrdb.Error, info:
        cdrcgi.bail('Failure checking for existing document: %s' % info[1][0])

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
except cdrdb.Error, info:
    cdrcgi.bail('Failure connecting to CDR: %s' % info[1][0])

#----------------------------------------------------------------------
# Import a citation document from PubMed.
#----------------------------------------------------------------------
if impReq:
    if not conceptCode:
        cdrcgi.bail("No concept code provided")
    if not session:
        cdrcgi.bail("User not logged in")
    if replaceId: # Not used; cloned from citation import program
        oldDoc = cdr.getDoc(session, replaceId, 'Y')
        if oldDoc.startswith("<Errors"):
            cdrcgi.bail("Unable to retrieve %s" % replaceId)
        if not getPubmedArticle(oldDoc):
            cdrcgi.bail("Document %s is not a PubMed Citation" % replaceId)
    else:
        docId = findExistingConcept(conceptCode)
        if docId:
            cdrcgi.bail("Concept has already been imported as CDR%010d" %
                        docId)
    concept = fetchConcept(conceptCode)
    #cdrcgi.bail("Under construction...")
    doc = u"""\
<Term xmlns:cdr='cips.nci.nih.gov/cdr'>
 <PreferredName>%s</PreferredName>
""" % fix(concept.preferredName)
    for syn in concept.fullSyn:
        if syn.termSource == 'NCI':
            code = syn.termGroup == 'PT' and conceptCode or None
            termType = mapType(syn.termGroup)
            doc += makeOtherName(syn.termName, termType, syn.termGroup,
                                 code)
    for indCode in concept.indCodes:
        doc += makeOtherName(indCode, 'IND code', 'IND_Code')
    for nscCode in concept.nscCodes:
        doc += makeOtherName(nscCode, 'NSC code', 'NSC_Code')
    for casCode in concept.casCodes:
        doc += makeOtherName(casCode, 'CAS Registry name', 'CAS_Registry')
    for definition in concept.definitions:
        if definition.source == 'NCI':
            doc += definition.toXml()
    doc += u"""\
 <TermType>
  <TermTypeName>Index term</TermTypeName>
 </TermType>
 <TermStatus>Unreviewed</TermStatus>
</Term>
"""
    if not replaceId:
        wrapper = u"""\
<CdrDoc Type='Term' Id=''>
 <CdrDocCtl>
  <DocType>Term</DocType>
  <DocTitle>%s</DocTitle>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[%%s]]></CdrDocXml>
</CdrDoc>
""" % fix(concept.preferredName)
        doc = (wrapper % doc).encode('utf-8')
        resp = cdr.addDoc(session, doc = doc, val = 'Y', showWarnings = 1)
    else: # dead code; cloned from citation import program
        doc = replacePubmedArticle(oldDoc, article)
        resp = cdr.repDoc(session, doc = doc, val = 'Y', showWarnings = 1)
    if not resp[0]:
        cdrcgi.bail("Failure adding concept %s: %s" % (title,
                                                       cdr.checkErr(resp[1])))
    cdr.unlock(session, resp[0])
    if not replaceId:
        subtitle = "Concept added as %s" % resp[0]
    else: # not used
        subtitle = "Citation %s updated %s" % (resp[0], pubVerNote)
    # FALL THROUGH TO FORM DISPLAY

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Preferred Name',          'PrefTerm'),
              ('Other Name',              'OtherName'),
              ('Term Type',               'TermType', termTypeList),
              ('Semantic Type',           'SemType', semanticTypeList))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'),
               ('button', 'javascript:searchThesaurus()',
                          'Search NCI Thesaurus'))
    errors = u""
    if valErrors:
        errors = u"""\
    <SPAN STYLE="color: red; font-size: 14pt; font-family:
                Arial; font-weight: Bold">
     *** IMPORTED WITH ERRORS ***  PUBLISHABLE VERSION NOT CREATED<BR>
    </SPAN>
    <SPAN STYLE="color: red; font-size: 12pt; font-family:
                Arial; font-weight: Normal">
     %s
    </SPAN>
""" % valErrors
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Term Search Form",
                                          "TermSearch.py",
                                          fields,
                                          buttons,
                                          subtitle, #'Term',
                                          conn, 
                                          errors)
    page += """\
   <SCRIPT LANGUAGE='JavaScript'>
    <!--
     function searchThesaurus() {
         var newWindow;
         newWindow = window.open('%s', 'SearchThesaurus');
     }
    // -->
   </SCRIPT>
   <CENTER>
    <TABLE>
     <TR>
      <TD ALIGN='right'>
       <SPAN       CLASS       = "Page">
        &nbsp;Concept Code of Term to Import:&nbsp;&nbsp;
       </SPAN>
      </TD>
      <TD>
       <INPUT      NAME        = "ConceptCode">
      </TD>
     </TR>
<!--
     <TR>
      <TD ALIGN='right'>
       <SPAN       CLASS       = "Page">
        &nbsp;CDR ID of Document to Replace (Optional):&nbsp;&nbsp;
       </SPAN>
      </TD>
      <TD>
       <INPUT      NAME        = "ReplaceID">
      </TD>
     </TR>
-->
     <TR>
      <TD>&nbsp;</TD>
      <TD>
       <INPUT      TYPE        = "submit"
                   NAME        = "ImportButton"
                   VALUE       = "Import">
      </TD>
     </TR>
    </TABLE>
   </CENTER>
  </FORM>
 </BODY>
</HTML>
""" % thesaurusSearchUrl
    cdrcgi.sendPage(page)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
searchFields = (cdrcgi.SearchField(prefTerm,
                            ("/Term/PreferredName",)),
                cdrcgi.SearchField(otherName,
                            ("/Term/OtherName/OtherTermName",)),
                cdrcgi.SearchField(termType,
                            ("/Term/TermType/TermTypeName",)),
                cdrcgi.SearchField(semType,
                            ("/Term/SemanticType/@cdr:ref",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields,
                                                       boolOp, 
                                                       "Term")
if not query:
    cdrcgi.bail('No query criteria specified')

#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Term documents: %s' % 
                info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Term", rows, strings, 
                                        'set:QC Term Set')

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
