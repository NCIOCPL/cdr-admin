#----------------------------------------------------------------------
#
# $Id: CiteSearch.py 9295 2009-10-20 21:13:25Z bkline $
#
# Prototype for duplicate-checking interface for Citation documents.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb, urllib, sys

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields and fields.getvalue("Boolean")          or "AND"
title     = fields and fields.getvalue("Title")            or None
author    = fields and fields.getvalue("Author")           or None
journal   = fields and fields.getvalue("Journal")          or None
year      = fields and fields.getvalue("Year")             or None
volume    = fields and fields.getvalue("Volume")           or None
issue     = fields and fields.getvalue("Issue")            or None
importID  = fields and fields.getvalue("ImportID")         or None
replaceID = fields and fields.getvalue("ReplaceID")        or None
submit    = fields and fields.getvalue("SubmitButton")     or None
help      = fields and fields.getvalue("HelpButton")       or None
impReq    = fields and fields.getvalue("ImportButton")     or None
srchPmed  = fields and fields.getvalue("SearchPubMed")     or None
subtitle  = "Citation"
valErrors = ""

userPair  = cdr.idSessionUser(session, session)
userInfo  = cdr.getUser((userPair[0], userPair[1]), userPair[0])

#----------------------------------------------------------------------
# Redirect to PubMed searching if requested (in a different window).
#----------------------------------------------------------------------
if srchPmed:
    print "Location:http://www.ncbi.nlm.nih.gov/entrez/\n"
    sys.exit(0)

#----------------------------------------------------------------------
# Show help screen for advanced search.
#----------------------------------------------------------------------
if help: 
    cdrcgi.bail("Sorry, help for this interface has not yet been developed.")

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
except cdrdb.Error, info:
    cdrcgi.bail('Failure connecting to CDR: %s' % info[1][0])

#----------------------------------------------------------------------
# Parse out the errors for display.
#----------------------------------------------------------------------
def formatErrors(errorsString):
    result = ""
    for error in cdr.getErrors(errorsString, errorsExpected = False,
                               asSequence = True):
        result += (cgi.escape("%s") % error) + "<br />\n"
    return result
    
#----------------------------------------------------------------------
# See if citation already exists.
#----------------------------------------------------------------------
def findExistingCitation(pmid):
    try:
        cursor = conn.cursor()
        cursor.execute("""\
                SELECT doc_id
                  FROM query_term
                 WHERE path LIKE '/Citation/PubmedArticle/%/PMID'
                   AND value = ?""", pmid)
        rows = cursor.fetchall()
        if not rows: return None
        return rows[0][0]
    except cdrdb.Error, info:
        cdrcgi.bail('Failure checking for existing document: %s' % info[1][0])

#----------------------------------------------------------------------
# Replace PubmedArticle element in document with new version.
#----------------------------------------------------------------------
def replacePubmedArticle(doc, newPubmedArticle):
    endTag = "</PubmedArticle>"
    start = doc.find("<PubmedArticle>")
    if start == -1:
        cdrcgi.bail("Unable to find PubmedArticle in existing document")
    end = doc.find(endTag, start + 1)
    return doc[:start] + newPubmedArticle + doc[end + len(endTag) : ]
    
#----------------------------------------------------------------------
# Extract the PubmedArticle element from the document.
#----------------------------------------------------------------------
def getPubmedArticle(doc):
    endTag = "</PubmedArticle>"
    start = doc.find("<PubmedArticle>")
    if start == -1:
        return None
    end = doc.find(endTag, start + 1)
    if end == -1:
        return None
    return doc[start : end + len(endTag)]
    
#----------------------------------------------------------------------
# Extract the text content of the ArticleTitle element.
#----------------------------------------------------------------------
def getArticleTitle(article):
    startTag = "<ArticleTitle>"
    start = article.find(startTag)
    if start == -1:
        return None
    end = article.find("</ArticleTitle>", start + 1)
    if end == -1:
        return None
    return article[start + len(startTag) : end]

#----------------------------------------------------------------------
# Import a citation document from PubMed.
#----------------------------------------------------------------------
if impReq:
    if not session: cdrcgi.bail("User not logged in")
    if replaceID:
        oldDoc = cdr.getDoc(session, replaceID, 'Y')
        if oldDoc.startswith("<Errors"):
            cdrcgi.bail("Unable to retrieve %s" % replaceID)
        if not getPubmedArticle(oldDoc):
            cdrcgi.bail("Document %s is not a PubMed Citation" % replaceID)
    else:
        docId = findExistingCitation(importID)
        if docId:
            cdrcgi.bail("Citation has already been imported as CDR%010d" %
                        docId)
    host    = 'www.ncbi.nlm.nih.gov'
    app     = '/entrez/utils/pmfetch.fcgi'
    base    = 'http://' + host + app + '?db=PubMed&report=sgml&mode=text&id='
    url     = base + importID
    try:
        uobj    = urllib.urlopen(url)
    except:
        cdrcgi.bail("NLM server unavailable; please try again later");
    page    = uobj.read()
    article = getPubmedArticle(page)
    if not article: cdrcgi.bail("Article Not Found")
    if not replaceID:
        title   = getArticleTitle(article) 
        if not title: cdrcgi.bail("Unable to find article title")
        title   = title[:255]
        doc     = """\
<CdrDoc Type='Citation' Id=''>
 <CdrDocCtl>
  <DocType>Citation</DocType>
  <DocTitle>%s</DocTitle>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[<Citation>
   <VerificationDetails>
    <Verified>Yes</Verified>
    <VerifiedIn>PubMed</VerifiedIn>
   </VerificationDetails>
   %s
  </Citation>]]></CdrDocXml>
</CdrDoc>
"""
        doc = doc % (title, article)
        resp = cdr.addDoc(session, doc = doc, val = 'Y', showWarnings = 1)
    else:
        doc = replacePubmedArticle(oldDoc, article)
        resp = cdr.repDoc(session, doc = doc, val = 'Y', showWarnings = 1)
    if not resp[0]:
        cdrcgi.bail("Failure adding PubMed citation %s: %s" %
                    (title, cdr.checkErr(resp[1])))
    if resp[1]:
        valErrors = formatErrors(resp[1])
    if valErrors:
        pubVerNote = "(with validation errors)"
    else:
        doc = cdr.getDoc(session, resp[0], 'Y')
        if doc.startswith("<Errors"):
            cdrcgi.bail("Unable to retrieve %s" % resp[0])
        resp2 = cdr.repDoc(session, doc = doc, val = 'Y', ver = 'Y',
                          checkIn = 'Y', showWarnings = 1)
        if not resp2[0]:
            cdrcgi.bail("Failure creating publishable version for %s:<br />%s" %
                        (resp[0], formatErrors(resp2[1])))
        pubVerNote = "(with publishable version)"
    if not replaceID:
        subtitle = "Citation added as %s %s" % (resp[0], pubVerNote)
    else:
        subtitle = "Citation %s updated %s" % (resp[0], pubVerNote)
    # FALL THROUGH TO FORM DISPLAY

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Title',                        'Title'),
              ('Author',                       'Author'),
              ('Published In',                 'Journal'),
              ('Publication Year',             'Year'),
              ('Volume',                       'Volume'),
              ('Issue',                        'Issue'))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'),
               ('submit', 'SearchPubMed', 'Search Pub Med'))
    errors = ""
    if valErrors:
        errors = """\
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
                                          "Citation Search Form",
                                          "CiteSearch.py",
                                          fields,
                                          buttons,
                                          subtitle, # 'Citation',
                                          conn,
                                          errors)
    pubMedImport = """\
   <CENTER>
    <TABLE>
     <TR>
      <TD ALIGN='right'>
       <INPUT      TYPE        = "submit"
                   NAME        = "ImportButton"
                   VALUE       = "Import">
       <SPAN       CLASS       = "Page">
        &nbsp;PubMed Citation ID to Import:&nbsp;&nbsp;
       </SPAN>
      </TD>
      <TD>
       <INPUT      NAME        = "ImportID">
      </TD>
     </TR>
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
    </TABLE>
   </CENTER>
"""

    footer = """\
  </FORM>
 </BODY>
</HTML>
"""
    # Suppress the display for PubMed Import for Guest accounts
    # ---------------------------------------------------------
    if 'GUEST' in userInfo.groups and len(userInfo.groups) < 2:
        html = page + footer
    else:
        html = page + pubMedImport + footer

    # sendPage() expects unicode: decoding page string
    # ------------------------------------------------
    html = html.decode('utf-8')
    cdrcgi.sendPage(html)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
searchFields = (cdrcgi.SearchField(title,
                        ("/Citation/PubmedArticle/%/Article/%Title",
                         "/Citation/PDQCitation/CitationTitle")),
                cdrcgi.SearchField(author,
                        ("/Citation/PDQCitation/AuthorList/Author/%Name",
                         "/Citation/PubmedArticle/%/AuthorList/Author/%Name")),
                cdrcgi.SearchField(journal,
                            ("/Citation/PubmedArticle/MedlineCitation"
                             "/MedlineJournalInfo/MedlineTA",
                             "/Citation/PDQCitation/PublicationDetails"
                             "/PublishedIn/@cdr:ref[int_val]")),
                cdrcgi.SearchField(year,
                            ("/Citation/PDQCitation/PublicationDetails"
                             "/PublicationYear",
                             #"/Citation/PubmedArticle/PubmedData/History"
                             #"/PubMedPubDate/Year")),
                             "/Citation/PubmedArticle/MedlineCitation"
                             "/Article/Journal/JournalIssue/PubDate/Year")),
                cdrcgi.SearchField(volume,
                            ("/Citation/PubmedArticle/MedlineCitation"
                             "/Article/Journal/JournalIssue/Volume",)),
                cdrcgi.SearchField(issue,
                            ("/Citation/PubMedArticle/MedlineCitation"
                             "/Article/Journal/JournalIssue/Issue",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                       "Citation")
if not query:
    cdrcgi.bail('No query criteria specified')
#cdrcgi.bail("QUERY: [%s]" % query)
#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query, timeout = 300)
    rows = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Citation documents: %s' % 
                info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Citation", rows, strings, 
                                        "set:QC Citation Set")

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
