#----------------------------------------------------------------------
#
# $Id: TermSearch.py,v 1.15 2007-10-19 12:59:35 kidderc Exp $
#
# Prototype for duplicate-checking interface for Term documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.13  2007/10/11 16:22:36  kidderc
# Moved much of functionality into NCIThes.py. A library module.
#
# Revision 1.12  2007/10/10 19:10:26  kidderc
# Added ajax functionality for prompting if preferred names do not match.
#
# Revision 1.11  2007/10/10 13:28:05  kidderc
# Bug 3037
#
# Revision 1.10  2007/10/01 16:15:41  kidderc
# Bug 3037.
#
# Revision 1.9  2007/09/20 21:18:30  bkline
# Switched to httplib and public server (qa server is broken indefinitely).
#
# Revision 1.8  2007/02/01 13:32:13  bkline
# Replaced Java program for retrieving Concept document from NCIT with
# HTTP API.
#
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
import cgi, cdr, cdrcgi, re, cdrdb, xml.dom.minidom, httplib, time, NCIThes

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
ckPrefNm    = fields and fields.getvalue("CkPrefNm")        or None
subtitle    = "Term"
updateCDRID = fields and fields.getvalue("UpdateCDRID")     or None
valErrors   = None

#----FOR DEBUGGING -------------------
#impReq = 1
#ckPrefNm = 1

#updateCDRID = '37776'
#conceptCode = 'C2203'

#updateCDRID = '37779'
#conceptCode = 'C2237'

#updateCDRID = '38150'
#conceptCode = 'C2608'

#updateCDRID = '38188'
#conceptCode = 'C2614'

#updateCDRID = '355804'
#conceptCode = 'C1888'

#updateCDRID = '38320'
#conceptCode = 'C1869'

#updateCDRID = '38325'
#conceptCode = 'C1795'

#session = '470CFB1D-6BFA7B-248-LNIB7AEB0MB6'
#-----------------------------------

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
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
except cdrdb.Error, info:
    cdrcgi.bail('Failure connecting to CDR: %s' % info[1][0])    

# check to see if the preferred names match
# if they don't return error message to ajax call.
if ckPrefNm:
    if updateCDRID:
        if conceptCode:
            if session:
                NCIPrefName = NCIThes.getNCITPreferredName(conceptCode)
                CDRPrefName = NCIThes.getCDRPreferredName(session,updateCDRID)
                if ( CDRPrefName.upper().rstrip(' ').lstrip(' ') != NCIPrefName.upper().rstrip(' ').lstrip(' ') ):
                    cdrcgi.sendPage("""Import cannot be completed since preferred names do not match. (CDR: '%s' and NCIT: '%s')""" % (CDRPrefName.upper(),NCIPrefName.upper()) )
                else:
                    cdrcgi.sendPage("")

#----------------------------------------------------------------------
# Import a citation document from NCI Thesaurus.
#----------------------------------------------------------------------
if impReq:
    if not conceptCode:
        cdrcgi.bail("No concept code provided")
    if not session:
        cdrcgi.bail("User not logged in")
    if updateCDRID:
        result = NCIThes.updateTerm(session,updateCDRID,conceptCode,doUpdate=1)
    else:
        result = NCIThes.addNewTerm(session,conceptCode)

    if result.startswith("<error>"):
        cdrcgi.bail(result)        
                            
    subtitle = result

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
    var myRequest = getXMLHttpRequest();
    var retval = true;

    function $(id)
    {
        return document.getElementById(id);
    }
    
    function getXMLHttpRequest()
    {
        var request = false;
        try
        {
            request = new XMLHttpRequest();
        }
        catch(err1)
        {
            try
            {
                request = new ActiveXObject("msxml2.XMLHTTP");
            }
            catch(err2)
            {
                try
                {
                    request = new ActiveXObject("Microsoft.XMLHTTP");
                }
                catch(err3)
                {
                    request = false;
                }
            }
        }
        return request;
    }

    function callAjax(e)
    {
        retval = true;
        updateCDRID = $('UpdateCDRID').value;
        conceptCode = $('ConceptCode').value;
        
        if ( updateCDRID.length < 1 )
            return true;

        if ( conceptCode.length < 2 )
            return true;
        
        session = $('Session').value;
        url = '%s/TermSearch.py?Session=' + session +
          '&CkPrefNm=1&UpdateCDRID=' + updateCDRID + '&ConceptCode=' + conceptCode;
        myRequest.open("GET",url,false);
        myRequest.onreadystatechange = handleAjaxResponse;
        myRequest.send(null);
        return retval;
    }

    function handleAjaxResponse()
    {
        if ( myRequest.readyState == 4 )
        {
            if ( myRequest.status == 200 )
            {
                if ( myRequest.responseText.length > 10 )
                {
                  alert(myRequest.responseText);
                  retval = false;
                }
            }
        }
    }
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
       <INPUT      NAME        = "ConceptCode"
                   ID          = "ConceptCode">
      </TD>
     </TR>
     <TR>
      <TD ALIGN='right'>
       <SPAN       CLASS       = "Page">
        &nbsp;CDR ID of Document to Update (Optional):&nbsp;&nbsp;
       </SPAN>
      </TD>
      <TD>
       <INPUT      NAME        = "UpdateCDRID"
                   ID          = "UpdateCDRID">
      </TD>
     </TR>
     <TR>
      <TD>&nbsp;</TD>
      <TD>
       <INPUT      TYPE        = "submit"
                   NAME        = "ImportButton"
                   VALUE       = "Import"
                   ONCLICK     = "return callAjax();">
      </TD>
     </TR>
    </TABLE>
   </CENTER>
  </FORM>
 </BODY>
</HTML>
""" % (thesaurusSearchUrl,cdrcgi.BASE)
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
