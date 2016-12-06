#----------------------------------------------------------------------
#
# $Id$
#
# Report of thesaurus concept IDs for concepts which are marked as
# not yet public.
#
# JIRA::OCECDR-3588
#
#----------------------------------------------------------------------
import cdrdb, requests, lxml.etree as etree, lxml.html as H
from lxml.html import builder as B

#----------------------------------------------------------------------
# Macros used for parsing the NCIt concept document.
#----------------------------------------------------------------------
CONCEPTS = "org.LexGrid.concepts"
COMMON   = "org.LexGrid.commonTypes"
ENTITY   = "%s.Entity" % CONCEPTS
PRES     = "%s.Presentation" % CONCEPTS
DEF      = "%s.Definition" % CONCEPTS
TEXT     = "%s.Text" % COMMON
SOURCE   = "%s.Source" % COMMON
PROPERTY = "%s.Property" % COMMON
CDRNS    = "cips.nci.nih.gov/cdr"
NSMAP    = { "cdr" : CDRNS }

#----------------------------------------------------------------------
# Find out when the term was last modified.
#----------------------------------------------------------------------
def getDateLastModified(cursor, cdrId):
    cursor.execute("""\
SELECT value
  FROM query_term
 WHERE doc_id = ?
   AND path = '/Term/DateLastModified'""", cdrId)
    for row in cursor.fetchall():
        return row[0]
    return u"\xa0"

#----------------------------------------------------------------------
# Get the semantic types for this term.
#----------------------------------------------------------------------
def getSemanticTypes(cursor, cdrId):
    cursor.execute("""\
SELECT DISTINCT n.value
  FROM query_term n
  JOIN query_term t
    ON t.int_val = n.doc_id
 WHERE n.path = '/Term/PreferredName'
   AND t.path = '/Term/SemanticType/@cdr:ref'
   AND t.doc_id = ?""", cdrId)
    types = u"; ".join([row[0] for row in cursor.fetchall()])
    return types or u"\xA0"

#----------------------------------------------------------------------
# Extract a named field from a node block.
#----------------------------------------------------------------------
def getFieldValue(node, name):
    for child in node.findall("field[@name='%s']" % name):
        return child.text
    return None

#----------------------------------------------------------------------
# Determine whether a concept code is available publicly.
#----------------------------------------------------------------------
def checkConcept(code):
    code  = code.strip()
    host  = "lexevsapi60.nci.nih.gov"
    app   = "/lexevsapi60/GetXML"
    parms = "query=org.LexGrid.concepts.Entity[@_entityCode=%s]" % code
    url   = "http://%s/%s?%s" % (host, app, parms)
    resp  = requests.get(url)
    doc   = resp.content
    tree  = etree.XML(doc)
    for entity in tree.findall("queryResponse/class[@name='%s']" % ENTITY):
        if getFieldValue(entity, '_entityCode') == code:
            return True
    return False

cursor = cdrdb.connect("CdrGuest").cursor()
cursor.execute("""\
         SELECT c.doc_id, c.value
           FROM query_term c
LEFT OUTER JOIN query_term p
             ON p.doc_id = c.doc_id
            AND p.node_loc = c.node_loc
            AND p.path = '/Term/NCIThesaurusConcept/@Public'
          WHERE c.path = '/Term/NCIThesaurusConcept'
            AND (p.value IS NULL OR p.value <> 'Yes')
       ORDER BY c.doc_id, c.value""")
title = "NCI Thesaurus Links Not Marked Public"
style = """
th, td { background-color: #ecf1ef; margin: 3px; padding: 3px; }
th { background-color: maroon; color: white; }
tr.odd td { background-color: #eff7f2; }
* { font-family: Arial, sans-serif; font-size: 11pt; }
h1 { color: maroon; font-size: 12pt; }
.flag { text-align: center; }
.frag-id { text-align: right; }
"""
html = H.Element("html")
html.append(
    B.HEAD(
        B.TITLE(title),
        B.STYLE(style)
    )
)
body = H.Element("body")
body.append(B.H1(title))
table = H.Element("table")
table.append(B.TR(B.TH("CDR ID"), B.TH("Concept ID"), B.TH("Available?"),
                  B.TH("Date Last Modified"), B.TH("Semantic Types")))
count = 1
for docId, conceptId in cursor.fetchall():
    rowClass = count % 2 == 1 and "odd" or "even"
    count += 1
    row = H.Element("tr", B.CLASS(rowClass))
    row.append(B.TD(u"CDR%d" % docId))
    row.append(B.TD(conceptId))
    row.append(B.TD(checkConcept(conceptId) and "Yes" or "No"))
    row.append(B.TD(getDateLastModified(cursor, docId)))
    row.append(B.TD(getSemanticTypes(cursor, docId)))
    table.append(row)
body.append(B.DIV(table))
html.append(body)
print "Content-type: text/html\n"
print "<!DOCTYPE html>"
print H.tostring(html, pretty_print=True)
