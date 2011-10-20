#----------------------------------------------------------------------
#
# $Id$
#
# Summary list of published clinical trial results by CTEP ID or by
# PubMed ID.  Can be invoked with one of two parameters, named ctepid
# and pmid.  For example:
#
# http://bach.nci.nih.gov/cgi-bin/cdr/GetPubResults.py?ctepid=17
# http://bach.nci.nih.gov/cgi-bin/cdr/GetPubResults.py?pmid=11685731
#
# In either case the response will contain an XML document whose top
# level element is PubmedArticleSet, with zero or more PubmedArticle
# child elements, using the structures specified in NLM's PUBMED DTD.
# If the ctepid parameter is used and no trial is found with that ID
# the service will return an XML document with a single Failure element
# whose text content is "No trial found for CTEP ID <parameter value>."
# Similarly if the pmid parameter is supplied with a value for which
# a Citation document cannot be found, a Failure element will be
# returned with the text content "No citation found for PMID <value>."
#
# This is one of a set of three services implemented for CTEP.  See
# also:
#   TrialsWithResults.py
#   LookupNctId.py
#
# BZIssue::1408
# BZIssue::1579
#
#----------------------------------------------------------------------
import cdr, cdrdb, cgi, re, time, os, xml.dom.minidom, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields = cgi.FieldStorage()
ctepid = fields and fields.getvalue('ctepid') or None
pmid   = fields and fields.getvalue('pmid')   or None

#----------------------------------------------------------------------
# Object with information needed for a single citation.
#----------------------------------------------------------------------
class Citation:
    def __init__(self, id):
        self.cdrId      = id
        self.pmid       = None
        self.date       = None
        self.articleXml = None
        lastVersions    = cdr.lastVersions('guest', 'CDR%d' % id)
        lastPub         = lastVersions[1]
        if lastPub == -1:
            raise Exception('no publishable versions for citation CDR%d' % id)
        doc = cdr.getDoc('guest', id, version = lastPub, getObject = True)
        if type(doc) in (str, unicode):
            errors = cdr.getErrors(doc)
            raise Exception(errors)
        cursor.execute("""\
            SELECT dt
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (id, lastPub))
        rows = cursor.fetchall()
        self.date = str(rows[0][0])[:10]
        dom = xml.dom.minidom.parseString(doc.xml)
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'PubmedArticle':
                sink = cdr.StringSink()
                node.writexml(sink)
                self.articleXml = sink.s.encode('utf-8')
                self.pmid = Citation.extractPmid(node)
        if not self.pmid:
            raise Exception("CDR%d: no PMID found" % id)

    def extractPmid(node):
        for child in node.childNodes:
            for grandchild in child.childNodes:
                if grandchild.nodeName == 'PMID':
                    return cdr.getTextContent(grandchild)
    extractPmid = staticmethod(extractPmid)

#----------------------------------------------------------------------
# Send failure message back to client.
#----------------------------------------------------------------------
def bail(error):
    print """\
Content-type: text/xml

<Failure>%s</Failure>""" % error
    sys.exit(0)
    
#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

#----------------------------------------------------------------------
# If a trial ID is provided, find the pubmed citations in it.
#----------------------------------------------------------------------
if ctepid:

    # Try an exact match first.
    cdrId = None
    pattern = re.compile(r"[-\s]")
    normalizedId = pattern.sub("", ctepid).upper()
    cursor.execute("""\
   SELECT DISTINCT c.doc_id
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'CTEP ID'
               AND c.value = ?""", normalizedId)
    rows = cursor.fetchall()
    if rows:
        cdrId = rows[0][0]
    else:
        cursor.execute("""\
   SELECT DISTINCT c.doc_id, c.value
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'CTEP ID'""")
        rows = cursor.fetchall()
        for row in rows:
            if pattern.sub("", row[1]).upper() == normalizedId:
                cdrId = row[0]
                break
    if not cdrId:
        bail("No trial found for CTEP ID %s" % ctepid)
    
    cursor.execute("""\
            SELECT int_val
              FROM query_term
             WHERE path IN ('/InScopeProtocol/PublishedResults' +
                            '/Citation/@cdr:ref',
                            '/InScopeProtocol/RelatedPublications' +
                            '/RelatedCitation/@cdr:ref')
               AND doc_id = ?""", cdrId)
    rows = cursor.fetchall()
    cites = {}
    for row in rows:
        try:
            cite = Citation(row[0])
            cites[cite.pmid] = cite
        except Exception, e:
            # bail(e)
            pass
    citations = []
    keys = cites.keys()
    keys.sort()
    for key in keys:
        citations.append(cites[key])
   

#----------------------------------------------------------------------
# Otherwise the must be a pubmed citation ID supplied.
#----------------------------------------------------------------------
elif pmid:
    cursor.execute("""\
             SELECT doc_id
               FROM query_term
              WHERE path = '/Citation/PubmedArticle/MedlineCitation/PMID'
                AND value = ?""", pmid.strip())
    rows = cursor.fetchall()
    if not rows:
        bail("No citation found for PMID %s" % pmid.strip())
    try:
        citations = [Citation(rows[0][0])]
    except Exception, e:
        bail(str(e))

#----------------------------------------------------------------------
# Remind the client which parameters are accepted.
#----------------------------------------------------------------------
else:
    bail("Missing required ctepid or pmid parameter")


print """\
Content-type: text/xml

<PubmedArticleSet>"""
for citation in citations:
    sys.stdout.write(citation.articleXml)
    print ""
print "</PubmedArticleSet>"
