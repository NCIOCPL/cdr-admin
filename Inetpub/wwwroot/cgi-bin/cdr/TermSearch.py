#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for duplicate-checking interface for Term documents.
#
# BZIssue::4714 (change URL and label for searching Thesaurus)
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb, xml.dom.minidom, httplib, time, NCIThes

ISSUES_WITH_THIS_CODE = """\
Alan:

I'm beginning to suspect that I should have scheduled more code
walkthroughs for projects we assigned to [name redacted].  As part of
my work on issue #4916 (failure of the thesaurus import command) I was
examining his implementation of the Term update code and it took me a
good while to figure out what he was doing (not a comment in sight).
From what I can figure out, it looks as if he's doing something like
the following:

  set a global retval JavaScript variable to true
  if the user clicks the Import button:
    create an XML HTTP Request (AJAX) object
    assign an asynchronous callback function for the object
    use the object to send a synchronous request to the same Python script
    return the value of retval to the handler for the submit (Import) button

  if the callback function is invoked:
    if the AJAX response is longer than 10 characters:
      display the contents of the response in a dialog box
      set the global retval JavaScript variable to false

  in the Python script, if this is an invocation by the AJAX request:
    retrieve the concept document for the user-specified concept code
    extract the preferred name from the document
    retrieve the CDR document for the user-specified CDR ID
    extract the preferred name from that document
    if the normalized names do not match:
      return a string describing the mismatch
    otherwise:
      return an empty string
  otherwise, if the user has requested an import:
    retrieve the concept document for the user-specified concept code
    import it

Ignoring minor sillinesses (like checking for 11 or more characters in
the AJAX response when his own code ensures that the response will
contain either an empty string or an error message, or why he thought
it was better to use lstrip().rstrip() instead of just strip() in a
number of places), I can't see the benefit of using AJAX at all,
unless he was deliberately trying to obfuscate the code, since it
results in retrieving the same concept twice from the thesaurus
service (and retrieving the same CDR term document twice).  And
relying on the asynchronous callback to change the value of a global
variable so that the return value from the callAjax() function will
cause the handling of the Import button to abort processing makes my
skin crawl.

So my question for you is: should we leave this code alone (since it
actually works, at least as far as I can tell - I'm not 100% certain
that the asynchronous callback function will always be invoked if he's
submitting the AJAX request synchronously) or is it so outrageous that
we should take the trouble to rewrite it?

--
Bob Kline
http://www.rksystems.com
mailto:***REMOVED***

If it works and the performance is acceptable for current and
anticipated uses, my inclination would be to leave it alone but add
comments explaining 1) how it works and 2) what needs to be done if it
is refactored.

A good and easy way to do that might just be to add your email message
above as a long comment in the code.  That way the analysis you did
will be kept right with the code - if we ever need it.  For example:

ISSUES_WITH_THIS_CODE = '''
<email here>
'''

Alternatively, we could add a low priority task for it if you think
it's justified, though I'd guess that the users would want us doing
other things as long as we didn't think it was going to cause
problems.  Let's discuss it tomorrow.

--
Alan Meyer
AM Systems, Inc.
Randallstown, MD USA
***REMOVED***
"""

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
updateDefinition    = fields and fields.getvalue("UpdateDefinition")  or None
importTerms    = fields and fields.getvalue("ImportTerms")  or None
subtitle    = "Term"
updateCDRID = fields and fields.getvalue("UpdateCDRID")     or None
valErrors   = None
userPair    = cdr.idSessionUser(session, session)
userInfo    = cdr.getUser(session, userPair[0])

if importTerms:
    importTerms = int(importTerms)
else:
    importTerms = 0

if updateDefinition:
    updateDefinition = int(updateDefinition)
else:
    updateDefinition = 0

#----FOR DEBUGGING -------------------
#session = '472F1902-706FCE-248-I179PKDICJPG'
#impReq = 1
#updateDefinition = 1
#importTerms = 1
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
#-----------------------------------

if help:
    cdrcgi.bail("Sorry, help for this interface has not yet "
                "been developed.")

#----------------------------------------------------------------------
# Redirect to Thesaurus searching if requested (in a different window).
#----------------------------------------------------------------------
thesaurusSearchUrl = "http://nciterms.nci.nih.gov"

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
                    cdrcgi.sendPage(u"""Import cannot be completed since preferred names do not match. (CDR: '%s' and NCIT: '%s')""" % (CDRPrefName.upper(),NCIPrefName.upper()) )
                else:
                    cdrcgi.sendPage(u"")

#----------------------------------------------------------------------
# Import a citation document from NCI Thesaurus.
#----------------------------------------------------------------------
if impReq:
    if not conceptCode:
        cdrcgi.bail("No concept code provided")
    if not session:
        cdrcgi.bail("User not logged in")
    if updateCDRID:
        result = NCIThes.updateTerm(session,updateCDRID,conceptCode,doUpdate=1,doUpdateDefinition=updateDefinition,doImportTerms=importTerms)
    else:
        result = NCIThes.addNewTerm(session,conceptCode,updateDefinition=updateDefinition,importTerms=importTerms)

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
""" % (thesaurusSearchUrl,cdrcgi.BASE)

    ccImport = """\
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
        &nbsp;CDR ID of Document to Update:&nbsp;&nbsp;
       </SPAN>
      </TD>
      <TD>
       <INPUT      NAME        = "UpdateCDRID"
                   ID          = "UpdateCDRID">
      </TD>
     </TR>
     <TR>
         <TD>
             <SPAN STYLE="font-size: 10pt; font-family:
                Arial; font-weight: Normal">
             (Concept Code also required to Update)
             </SPAN>
         </TD>
     </TR>
     <TR>
         <TD>
         </TD>
         <TD>
         <input type='checkbox' id='UpdateDefinition' name='UpdateDefinition' value='1' CHECKED>
           Update Definition</input><br>
         </TD>
    </TR>
    <TR>
       <TD>
       </TD>
         <TD>
         <input type='checkbox' id='ImportTerms' name='ImportTerms' value='1' CHECKED>
           Import Terms</input><br>
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
"""

    footer = """\
  </FORM>
 </BODY>
</HTML>
"""
    # Suppress the display for Concept Code Import for Guest accounts
    # ---------------------------------------------------------------
    if 'GUEST' in userInfo.groups and len(userInfo.groups) < 2:
        html = page + footer
    else:
        html = page + ccImport + footer

    cdrcgi.sendPage(html)

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
