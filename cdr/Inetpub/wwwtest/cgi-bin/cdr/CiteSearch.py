#----------------------------------------------------------------------
#
# $Id: CiteSearch.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Prototype for duplicate-checking interface for Citation documents.
#
# $Log: not supported by cvs2svn $
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
submit    = fields and fields.getvalue("SubmitButton")     or None
help      = fields and fields.getvalue("HelpButton")       or None
impReq    = fields and fields.getvalue("ImportButton")     or None
srchPmed  = fields and fields.getvalue("SearchPubMed")     or None
subtitle  = "Citation"

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
# Import a citation document from PubMed.
#----------------------------------------------------------------------
if impReq:
    if not session: cdrcgi.bail("User not logged in")
    host    = 'www.ncbi.nlm.nih.gov'
    app     = '/entrez/utils/pmfetch.fcgi'
    base    = 'http://' + host + app + '?db=PubMed&report=sgml&mode=text&id='
    url     = base + importID
    uobj    = urllib.urlopen(url)
    page    = uobj.read()
    exp1    = re.compile("<PubmedArticle>.*?</PubmedArticle>", re.DOTALL)
    exp2    = re.compile("<ArticleTitle>(.*?)</ArticleTitle>", re.DOTALL)
    article = exp1.findall(page)
    if not article: cdrcgi.bail("Article Not Found")
    title   = exp2.findall(article[0]) 
    if not title: cdrcgi.bail("Unable to find article title")
    title   = title[0] or "NO TITLE FOUND"
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
    <VerifiedIn>PUBMED</VerifiedIn>
    <ModifiedRecord>No</ModifiedRecord>
   </VerificationDetails>
   %s
  </Citation>]]></CdrDocXml>
</CdrDoc>
"""
    id = cdr.addDoc(session, doc = doc % (title, article[0]))
    if id.find("<Err") != -1:
        cdrcgi.bail("Failure adding PubMed citation %s: %s" % (
                    title, cdr.checkErr(id)))
    subtitle = "Citation added as %s" % id
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
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Citation Search Form",
                                          "CiteSearch.py",
                                          fields,
                                          buttons,
                                          subtitle, # 'Citation',
                                          conn)
    page += """\
   <CENTER>
    <INPUT      TYPE        = "submit"
                NAME        = "ImportButton"
                VALUE       = "Import">
    &nbsp;PubMed Citation ID TO Import:&nbsp;&nbsp;
    <INPUT      NAME        = "ImportID">
   </CENTER>
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(page)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
searchFields = (cdrcgi.SearchField(title,
                            ("/Citation/PubMedArticle/MedlineCitation"
                             "/Article/ArticleTitle",
                             "/Citation/PDQCitation/CitationTitle")),
                cdrcgi.SearchField(author,
                            ("/Citation/PubMedArticle/MedlineCitation"
                             "/Article/AuthorList/Author/PersonalName"
                             "/LastName",
                             "/Citation/PubMedArticle/MedlineCitation"
                             "/Article/AuthorList/Author/PersonalName"
                             "/FirstName",
                             "/Citation/PubMedArticle/MedlineCitation"
                             "/Article/AuthorList/Author/CollectiveName")),
                cdrcgi.SearchField(journal,
                            ("/Citation/PubMedArticle/MedlineCitation"
                             "/MedlineJournalInformation/MedlineTA",
                             "/Citation/PDQCitation/PublicationDetails"
                             "/PublishedIn")),
                cdrcgi.SearchField(year,
                            ("/Citation/PDQCitation/PublicationDetails"
                             "/PublicationYear",
                             "/Citation/PubMedArticle/PubMedData/History"
                             "/PubMedPubDate/Year")),
                cdrcgi.SearchField(volume,
                            ("/Citation/PubMedArticle/MedlineCitation"
                             "/Article/Journal/JournalIssue/Volume",)),
                cdrcgi.SearchField(journal,
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
    cursor.execute(query)
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
                                        "CDR266311")

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
