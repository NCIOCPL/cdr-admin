#----------------------------------------------------------------------
#
# $Id: CitationSearch.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Prototype for duplicate-checking interface for Citation documents.
# *** Obsolete version, based on prototype schema for citations. ***
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb, urllib, sys

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = '/cgi-bin/cdr/Filter.py'

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)                     or ""
boolOp   = fields and fields.getvalue("Boolean")         or "AND"
title    = fields and fields.getvalue("Title")           or None
authors  = fields and fields.getvalue("Authors")         or None
source   = fields and fields.getvalue("Source")          or None
pubInfo  = fields and fields.getvalue("PubInfo")         or None
pmid     = fields and fields.getvalue("PMID")            or None
citeId   = fields and fields.getvalue("CitationID")      or None
importID = fields and fields.getvalue("ImportID")        or None
submit   = fields and fields.getvalue("SubmitButton")    or None
help     = fields and fields.getvalue("HelpButton")      or None
impReq   = fields and fields.getvalue("ImportButton")    or None
srchPmed = fields and fields.getvalue("SearchPubMed")    or None
subtitle = "Citation"

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
# Perform the requested search.
#----------------------------------------------------------------------
if submit:
    cdrcgi.bail("Search hasn't yet been implemented for Citations.")

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
fields = (('Citation Title',          'Title'),
          ('Authors',                 'Authors'),
          ('Source',                  'Source'),
          ('Publication Info',        'PubInfo'),
          ('PMID',                    'PMID'),
          ('Citation ID',             'CitationID'))
buttons = (('submit', 'SubmitButton', 'Search'),
           ('submit', 'HelpButton',   'Help'),
           ('reset',  'CancelButton', 'Clear'),
           ('submit', 'SearchPubMed', 'Search Pub Med'))
page = cdrcgi.startAdvancedSearchPage(session,
                                      "Citation Search Form",
                                      "CitationSearch.py",
                                      fields,
                                      buttons,
                                      subtitle, None)
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
# Determine whether query contains unescaped wildcards.
#----------------------------------------------------------------------
def getQueryOp(query):
    escaped = 0
    for char in query:
        if char == '\\':
            escaped = not escaped
        elif not escaped and char in "_%": return "LIKE"
    return "="

#----------------------------------------------------------------------
# Escape single quotes in string.
#----------------------------------------------------------------------
def getQueryVal(val):
    return val.replace("'", "''")

#----------------------------------------------------------------------
# Query components.
#----------------------------------------------------------------------
class SearchField:
    def __init__(self, var, table, selector):
        self.var      = var
        self.table    = table
        self.selector = selector

searchFields = (SearchField(orgName, "document",   "title"),
                SearchField(city,    "query_term", "/Org/OrgCity"),
                SearchField(state,   "query_term", "/Org/OrgState"),
                SearchField(country, "query_term", "/Org/OrgCountry"),
                SearchField(zip,     "query_term", "/Org/OrgPostalCode"))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
where              = ""
strings            = ""
queryTermTableUses = 0
boolOp             = boolOp == "AND" and " AND " or " OR "
for searchField in searchFields:
    if searchField.var:
        queryOp  = getQueryOp(searchField.var)
        queryVal = getQueryVal(searchField.var)
        if strings: strings += ' '
        strings += queryVal.strip()
        if where:
            where += boolOp
        else:
            where = "WHERE ("
        if searchField.table == 'document':
            where += "document.%s %s '%s'" % (
                    searchField.selector, queryOp, queryVal)
        else:
            queryTermTableUses += 1
            if boolOp == " AND ":
                qtAlias = "q%d" % queryTermTableUses
                where += "(%s.path = '%s' "\
                         "AND %s.value %s '%s' "\
                         "AND %s.doc_id = document.id)" % (
                        qtAlias, searchField.selector, 
                        qtAlias, queryOp, queryVal,
                        qtAlias)
            else:
                where += "(q.path = '%s' AND q.value %s '%s')" % (
                        searchField.selector,
                        queryOp,
                        queryVal)
                    
#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
query = ''
rows = []
if where:
    where += ") AND (document.doc_type = doc_type.id "\
              " AND doc_type.name = 'Org') "
    query = 'SELECT DISTINCT document.id, document.title '\
                       'FROM document, doc_type'
    if queryTermTableUses:
        if boolOp == " AND ":
            for i in range(queryTermTableUses):
                query += ", query_term q%d" % (i + 1)
        else:
            query += ", query_term q"
            where += "AND document.id = q.doc_id "
    query += " " + where + "ORDER BY document.title"
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving Org documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Emit the top of the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>CDR Organization Search Results</TITLE>
  <META   HTTP-EQUIV = "Content-Type" 
             CONTENT = "text/html; charset=iso-8859-1">
  <STYLE        TYPE = "text/css">
   <!--
    .Page { font-family: Arial, Helvetica, sans-serif; color: #000066 }
   -->
  </STYLE>
 </HEAD>
 <BODY       BGCOLOR = "#CCCCFF">
  <TABLE       WIDTH = "100%%" 
              BORDER = "0" 
         CELLSPACING = "0" 
               CLASS = "Page">
   <TR       BGCOLOR = "#6699FF"> 
    <TD       NOWRAP 
              HEIGHT = "26" 
             COLSPAN = "3">
     <FONT      SIZE = "+2" 
               CLASS = "Page">CDR Advanced Search Results</FONT>
    </TD>
   </TR>
   <TR       BGCOLOR = "#FFFFCC"> 
    <TD       NOWRAP 
             COLSPAN = "3">
     <SPAN     CLASS = "Page">
      <FONT     SIZE = "+1">Organization</FONT>
     </SPAN>
    </TD>
   </TR>
   <TR> 
    <TD       NOWRAP 
             COLSPAN = "3"
              HEIGHT = "20">&nbsp;</TD>
   </TR>
   <TR> 
    <TD       NOWRAP
             COLSPAN = "3"
               CLASS = "Page">
     <FONT     COLOR = "#000000">%d documents match '%s'</FONT>
    </TD>
   </TR>
   <TR> 
    <TD       NOWRAP
             COLSPAN = "3"
               CLASS = "Page">&nbsp;</TD>
   </TR>
""" % (len(rows), strings)

for i in range(len(rows)):
    docId = "CDR%010d" % rows[i][0]
    title = rows[i][1]
    html += """\
   <TR>
    <TD       NOWRAP
               WIDTH = "10"
              VALIGN = "top">
     <DIV      ALIGN = "right">%d.</DIV>
    </TD>
    <TD        WIDTH = "20"
              VALIGN = "top">
     <A         HREF = "%s?DocId=%s&Filter=%s">%s</A>
    </TD>
    <TD        WIDTH = "74%%">%s</TD>
   </TR>
""" % (i + 1, SCRIPT, docId, 'CDR210816', docId, cgi.escape(title, 1))

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + "  </TABLE>\n </BODY>\n</HTML>\n")
