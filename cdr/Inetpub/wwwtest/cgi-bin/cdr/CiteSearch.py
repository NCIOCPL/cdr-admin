#----------------------------------------------------------------------
#
# $Id: CiteSearch.py,v 1.5 2002-05-10 21:14:12 bkline Exp $
#
# Prototype for duplicate-checking interface for Citation documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2002/02/25 13:47:51  bkline
# Added ability to designate CDR document to be overridden by fresh import
# of PubMed doc (task #57).
#
# Revision 1.3  2002/02/20 04:00:16  bkline
# Modified style of prompt at users' request.
#
# Revision 1.2  2002/02/14 19:38:10  bkline
# Fixed search element paths to match schema changes; replaced hardwired
# filter ID with filter document name.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
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
    exp1    = re.compile("<PubmedArticle>.*?</PubmedArticle>", re.DOTALL)
    exp2    = re.compile("<ArticleTitle>(.*?)</ArticleTitle>", re.DOTALL)
    if replaceID:
        oldDoc = cdr.getDoc(session, replaceID, 'Y')
        if oldDoc.startswith("<Errors"):
            cdrcgi.bail("Unable to retrieve %s" % replaceID)
        if not exp1.findall(oldDoc):
            cdrcgi.bail("Document %s is not a PubMed Citation")
    host    = 'www.ncbi.nlm.nih.gov'
    app     = '/entrez/utils/pmfetch.fcgi'
    base    = 'http://' + host + app + '?db=PubMed&report=sgml&mode=text&id='
    url     = base + importID
    uobj    = urllib.urlopen(url)
    page    = uobj.read()
    article = exp1.findall(page)
    if not article: cdrcgi.bail("Article Not Found")
    if not replaceID:
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
   </VerificationDetails>
   %s
  </Citation>]]></CdrDocXml>
</CdrDoc>
"""
        id = cdr.addDoc(session, doc = doc % (title, article[0]))
    else:
        modifiedDoc = exp1.sub(article[0], oldDoc)
        id = cdr.repDoc(session, doc = modifiedDoc, checkIn = 'Y')
    if id.find("<Err") != -1:
        cdrcgi.bail("Failure adding PubMed citation %s: %s" % (
                    title, cdr.checkErr(id)))
    if not replaceID:
        subtitle = "Citation added as %s" % id
    else:
        subtitle = "Citation %s updated" % id
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
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(page)

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
                             "/PublishedIn")),
                cdrcgi.SearchField(year,
                            ("/Citation/PDQCitation/PublicationDetails"
                             "/PublicationYear",
                             "/Citation/PubmedArticle/PubmedData/History"
                             "/PubMedPubDate/Year")),
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
                                        "name:Citation QC Report")

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
