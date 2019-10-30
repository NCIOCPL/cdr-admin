#----------------------------------------------------------------------
# Report on menu information added to Term documents to support the
# genetics directory.
#
# BZIssue::4696
#----------------------------------------------------------------------
import cdrcgi, cgi, lxml.etree as etree, cdr
from cdrapi import db
from html import escape as html_escape

#----------------------------------------------------------------------
# Constant values we look for in the MenuType element.
#----------------------------------------------------------------------
GP_GS = "Genetics Professionals--GeneticSyndrome"
GP_CT = "Genetics Professionals--CancerType"
GP_CS = "Genetics Professionals--CancerSite"

#----------------------------------------------------------------------
# Base class for the two term types; understands sorting order.
#----------------------------------------------------------------------
class Term:
    def __lt__(self, other):
        return self.sortkey < other.sortkey
    @property
    def sortkey(self):
        if not hasattr(self, "_sortkey"):
            name = self.preferredName.upper() if self.preferredName else ""
            self._sortkey = name, self.cdrId
        return self._sortkey

#----------------------------------------------------------------------
# Term document representing what the genprof DB calls a "cancer site."
#----------------------------------------------------------------------
class RelatedTerm(Term):
    __terms = {}
    @classmethod
    def find(cls, cdrId):
        if cdrId not in cls.__terms:
            cls.__terms[cdrId] = RelatedTerm(cdrId)
        return cls.__terms[cdrId]
    def __init__(self, cdrId):
        self.cdrId = cdrId
        self.preferredName = None
        self.cancerSite = self.cancerType = None
        self.syndromes = set()
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml)
        for node in tree.findall('PreferredName'):
            self.preferredName = node.text
        for node in tree.findall('TermRelationship/RelatedTerm'):
            relationshipType = termId = None
            for child in node.iterchildren():
                if child.tag == 'TermId':
                    childId = child.get('{cips.nci.nih.gov/cdr}ref')
                    try:
                        termId = cdr.exNormalize(childId)[1]
                    except:
                        pass
                elif child.tag == 'RelationshipType':
                    relationshipType = child.text
            if relationshipType == 'Associated genetic condition' and termId:
                self.syndromes.add(termId)
        for node in tree.findall('MenuInformation/MenuItem'):
            menuType = displayName = None
            for child in node.iterchildren():
                if child.tag == 'MenuType':
                    menuType = child.text
                elif child.tag == 'DisplayName':
                    displayName = child.text
            if displayName is not None and menuType == GP_CT:
                self.cancerType = displayName
            elif displayName is not None and menuType == GP_CS:
                self.cancerSite = displayName
    def toHtml(self):
        pn = self.preferredName and html_escape(self.preferredName) or "&nbsp;"
        cs = self.cancerSite and html_escape(self.cancerSite) or "&nbsp;"
        ct = self.cancerType and html_escape(self.cancerType) or "&nbsp;"
        return """\
    <td>%s</td>
    <td>CDR%d</td>
    <td>%s</td>
    <td>%s</td>""" % (pn, self.cdrId, cs, ct)

#----------------------------------------------------------------------
# Term document representing conditions in which genetics professionals
# specialize.
#----------------------------------------------------------------------
class GeneticCondition(Term):
    def __init__(self, cdrId):
        self.cdrId = cdrId
        self.preferredName = None
        self.displayName = None
        self.relatedTerms = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml)
        for node in tree.findall('PreferredName'):
            self.preferredName = node.text
        for node in tree.findall('MenuInformation/MenuItem'):
            menuType = displayName = None
            for child in node.iterchildren():
                if child.tag == 'MenuType':
                    menuType = child.text
                elif child.tag == 'DisplayName':
                    displayName = child.text
            if displayName is not None and menuType == GP_GS:
                self.displayName = displayName
        cursor.execute("""\
            SELECT DISTINCT doc_id
                       FROM query_term
                      WHERE path = '/Term/TermRelationship/RelatedTerm'
                                 + '/TermId/@cdr:ref'
                        AND int_val = ?""", cdrId)
        rows = cursor.fetchall()
        for row in rows:
            relatedTerm = RelatedTerm.find(row[0])
            if cdrId in relatedTerm.syndromes:
                self.relatedTerms.append(relatedTerm)
        self.relatedTerms.sort()
    def toHtml(self):
        rowspan = ""
        if len(self.relatedTerms) > 1:
            rowspan = " rowspan='%d'" % len(self.relatedTerms)
        html = ["""\
   <tr>
    <td%s>%s (CDR%d)</td>
    <td%s>%s</td>
""" % (rowspan,
       self.preferredName and html_escape(self.preferredName) or "&nbsp;",
       self.cdrId, rowspan,
       self.displayName and html_escape(self.displayName) or "&nbsp;")]
        if self.relatedTerms:
            html.append(self.relatedTerms[0].toHtml())
        else:
            html.append("""\
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
""")
        html.append("""
   </tr>
""")
        for rt in self.relatedTerms[1:]:
            html.append("""\
    <tr>
%s
    </tr>
""" % rt.toHtml())
        return "".join(html)

#----------------------------------------------------------------------
# Construct the head of the report.
#----------------------------------------------------------------------
html = ["""\
<html>
 <head>
  <title>Genetic Condition Menu Mapping Report</title>
  <style type='text/css'>
   h1 { color: maroon; text-align: center }
   th { color: blue }
  </style>
 </head>
 <body>
  <h1>Genetic Condition Menu Mapping Report</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Genetic Condition Preferred Term</th>
    <th>Menu Information (Genetic Syndrome)</th>
<!--<th>Parent Term</th>-->
    <th>Related Term</th>
    <th>Related Term ID</th>
    <th>Menu Information (Cancer Site)</th>
    <th>Menu Information (Cancer Type)</th>
   </tr>
"""]

#----------------------------------------------------------------------
# Collect all the terms with semantic type of "Genetic condition."
#----------------------------------------------------------------------
cursor = db.connect(user='CdrGuest').cursor()
cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/Term/SemanticType/@cdr:ref'
                AND int_val IN (SELECT doc_id
                                  FROM query_term
                                 WHERE path = '/Term/PreferredName'
                                   AND value = 'Genetic condition')""")
rows = cursor.fetchall()
conditions = []
for row in rows:
    conditions.append(GeneticCondition(row[0]))
conditions.sort()

#----------------------------------------------------------------------
# Populate the body of the report and send it off.
#----------------------------------------------------------------------
for gc in conditions:
    html.append(gc.toHtml())
html.append("""\
  </table>
 </body>
</html>
""")
cdrcgi.sendPage("".join(html))
