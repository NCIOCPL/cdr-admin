#----------------------------------------------------------------------
# Search for citations, and optionally import them from NLM.
#
# BZIssue::4724
# BZIssue::5174
# JIRA::OCECDR-3456
# JIRA::OCECDR-4201
# JIRA::OCECDR-4434
# JIRA::OCECDR-4463
# JIRA::OCECDR-4561
#----------------------------------------------------------------------
import cgi
from lxml import etree
import requests
import cdr
import cdrcgi
from cdrapi import db
from cdrapi.users import Session

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields.getvalue("Boolean")      or "AND"
title     = fields.getvalue("Title")        or None
author    = fields.getvalue("Author")       or None
journal   = fields.getvalue("Journal")      or None
year      = fields.getvalue("Year")         or None
volume    = fields.getvalue("Volume")       or None
issue     = fields.getvalue("Issue")        or None
importID  = fields.getvalue("ImportID")     or ""
replaceID = fields.getvalue("ReplaceID")    or None
submit    = fields.getvalue("SubmitButton") or None
help      = fields.getvalue("HelpButton")   or None
impReq    = fields.getvalue("ImportButton") or None
srchPmed  = fields.getvalue("SearchPubMed") or None
subtitle  = "Citation"
valErrors = ""

# Use the user's name to get info about his groups
userInfo  = cdr.getUser(session, Session(session).user_name)

#----------------------------------------------------------------------
# Redirect to PubMed searching if requested (in a different window).
#----------------------------------------------------------------------
if srchPmed:
    print("Location:https://www.ncbi.nlm.nih.gov/entrez/\n")
    exit(0)

#----------------------------------------------------------------------
# Show help screen for advanced search.
#----------------------------------------------------------------------
if help:
    cdrcgi.bail("Sorry, help for this interface has not yet been developed.")

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = db.connect(user="CdrGuest", timeout=300)
except Exception as e:
    cdrcgi.bail("Failure connecting to CDR: {}".format(e))

#----------------------------------------------------------------------
# Parse out the errors for display.
#----------------------------------------------------------------------
def parseErrors(errorString):
    opts = dict(errorsExpected=False, asSequence=True, asUtf8=False)
    return cdr.getErrors(errorString, **opts)

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
    except Exception as e:
        cdrcgi.bail("Failure checking for existing document: {}".format(e))

#----------------------------------------------------------------------
# Replace PubmedArticle element in document with new version.
#----------------------------------------------------------------------
def replacePubmedArticle(doc, article):
    tree = etree.XML(doc.xml)
    for node in tree.findall("PubmedArticle"):
        tree.replace(node, article)
        doc.xml = etree.tostring(tree)
        return doc

#----------------------------------------------------------------------
# Extract the PubmedArticle element from the document.
#----------------------------------------------------------------------
def getPubmedArticle(doc):
    try:
        root = etree.XML(doc)
    except:
        cdrcgi.bail("unable to parse document from NLM")
    for node in root.findall("PubmedArticle"):
        return cdr.prepare_pubmed_article_for_import(node)
    return None

#----------------------------------------------------------------------
# Extract the text content of the ArticleTitle element.
#----------------------------------------------------------------------
def getArticleTitle(article):
    for node in article.findall("MedlineCitation/Article/ArticleTitle"):
        return cdr.get_text(node)

#----------------------------------------------------------------------
# Retrieve an XML document for a Pubmed article from NLM.
#----------------------------------------------------------------------
def fetchCitation(pmid):
    host = "eutils.ncbi.nlm.nih.gov"
    app  = "/entrez/eutils/efetch.fcgi"
    url  = "https://" + host + app + "?db=pubmed&retmode=xml&id=" + pmid
    try:
        response = requests.get(url)
    except:
        cdrcgi.bail("NLM server unavailable; please try again later")
    article = getPubmedArticle(response.content)
    if article is None: cdrcgi.bail("Article Not Found")
    return article

#----------------------------------------------------------------------
# Create a new CDR Doc object, using the information retrieved from NLM.
#----------------------------------------------------------------------
def createNewCitationDoc(article):
    title = getArticleTitle(article)
    if not title: cdrcgi.bail("Unable to find article title")
    ctrl = dict(DocType="Citation", DocTitle=title[:255].encode("utf-8"))
    root = etree.Element("Citation")
    details = etree.SubElement(root, "VerificationDetails")
    etree.SubElement(details, "Verified").text = "Yes"
    etree.SubElement(details, "VerifiedIn").text = "PubMed"
    root.append(article)
    docXml = etree.tostring(root, encoding="utf-8")
    return cdr.Doc(docXml, doctype="Citation", ctrl=ctrl)

#----------------------------------------------------------------------
# Handle a request to import a citation document from PubMed.
#----------------------------------------------------------------------
if impReq:
    importID = importID.strip()
    if not session: cdrcgi.bail("User not logged in")
    article = fetchCitation(importID)
    if replaceID:
        try:
            oldDoc = cdr.getDoc(session, replaceID, "Y", getObject=True)
        except:
            cdrcgi.bail("Unable to check out CDR document {}".format(replaceID))
        doc = replacePubmedArticle(oldDoc, article)
        if doc is None:
            cdr.unlock(session, replaceID)
            cdrcgi.bail("{} is not a Citation document".format(replaceID))
        resp = cdr.repDoc(session, doc=str(doc), val="Y", showWarnings=True)
    else:
        docId = findExistingCitation(importID)
        if docId:
            cdrcgi.bail("Citation already imported as CDR{:010d}".format(docId))
        doc = createNewCitationDoc(article)
        resp = cdr.addDoc(session, doc=str(doc), val="Y", showWarnings=True)
    docId, errors = resp
    if not docId:
        with open("d:/tmp/{}.xml".format(importID), "w") as fp:
            fp.write(str(doc))
        args = importID, cdr.checkErr(errors)
        cdrcgi.bail("Failure saving PubMed citation {}: {}".format(*args))
    if errors:
        valErrors = parseErrors(errors)
    if valErrors:
        pubVerNote = "(with validation errors)"
    else:
        doc = cdr.getDoc(session, docId, "Y")
        if doc.startswith("<Errors"):
            cdrcgi.bail("Unable to retrieve {}".format(docId))
        resp = cdr.repDoc(session, doc=doc, val="Y", ver="Y", checkIn="Y",
                          showWarnings=True, publishable="Y")
        if not resp[0]:
            msg = "Failure creating publishable version for {}".format(docId)
            cdrcgi.bail(msg, extra=parseErrors(resp[1]))
        pubVerNote = "(with publishable version)"
    if replaceID:
        subtitle = "Citation {} updated {}".format(docId, pubVerNote)
    else:
        subtitle = "Citation added as {} {}".format(docId, pubVerNote)
    # Continue with search form display

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (("Title",                        "Title"),
              ("Author",                       "Author"),
              ("Published In",                 "Journal"),
              ("Publication Year",             "Year"),
              ("Volume",                       "Volume"),
              ("Issue",                        "Issue"))
    buttons = (("submit", "SubmitButton", "Search"),
               ("submit", "HelpButton",   "Help"),
               ("reset",  "CancelButton", "Clear"),
               ("submit", "SearchPubMed", "Search Pub Med"))
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
                                          subtitle,
                                          conn,
                                          errors)
    pubMedImport = """\
   <CENTER>
    <TABLE>
     <TR>
      <TD ALIGN="right">
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
      <TD ALIGN="right">
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
    if "GUEST" in userInfo.groups and len(userInfo.groups) < 2:
        html = page + footer
    else:
        html = page + pubMedImport + footer

    # sendPage() expects unicode: decoding page string
    # ------------------------------------------------
    html = html.decode("utf-8")
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
args = searchFields, boolOp, "Citation"
query, strings = cdrcgi.constructAdvancedSearchQuery(*args)
if not query:
    cdrcgi.bail("No query criteria specified")

#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    cursor = None
except Exception as e:
    cdrcgi.bail("Failure retrieving Citation documents: {}".format(e))

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
args = "Citation", rows, strings, "set:QC Citation Set"
html = cdrcgi.advancedSearchResultsPage(*args)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
