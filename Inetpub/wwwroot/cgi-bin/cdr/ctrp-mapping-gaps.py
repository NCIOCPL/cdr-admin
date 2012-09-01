#----------------------------------------------------------------------
#
# $Id$
#
# Interface for reviewing the missing mappings for persons, orgs, etc.
# in the CTRP trials queued to be imported.
#
# BZIssue::4942
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, cgi, ctrp, cdr, cdrcgi, sys

POID = 'CTRP_PO_ID'

def fix(me):
    if not me:
        return ''
    return cgi.escape(me)

class MappingProblem:
    def __init__(self, docType, value, ctrpId=None):
        self.docType = docType
        self.value = value
        self.ctrpId = ctrpId

def extractPerson(node):
    values = []
    ctrpId = None
    for child in node.findall('po_id'):
        ctrpId = child.text
    for path in ('first_name', 'middle_initial', 'last_name',
                 'address/street', 'address/city', 'address/state',
                 'address/zip', 'address/country'):
        for child in node.findall(path):
            values.append(child.text)
    return ctrpId, u" ".join(values)

def extractOrg(node):
    values = []
    ctrpId = None
    for child in node.findall('po_id'):
        ctrpId = child.text
    for path in ('name', 'address/street', 'address/city', 'address/state',
                 'address/zip', 'address/country'):
        for child in node.findall(path):
            values.append(child.text)
    return ctrpId, u" ".join(values)

def findMappingProblems(session, docXml, poIds, geoMappings):
    problems = {}
    title = ''
    tree = etree.XML(docXml)
    for node in tree.findall('official_title'):
        title = node.text
    docType = 'Organization'
    for org in tree.findall('location/facility'):
        ctrpId, value = extractOrg(org)
        cdrId = poIds.get(ctrpId)
        if not cdrId:
            key = (docType, ctrpId)
            problems[key] = MappingProblem(docType, value, ctrpId)
            if ctrpId not in poIds:
                cdr.addExternalMapping(session, POID, ctrpId)
                poIds[ctrpId] = None
    docType = 'Person'
    for path in ('location/contact', 'location/investigator'):
        for person in tree.findall(path):
            ctrpId, value = extractPerson(person)
            cdrId = poIds.get(ctrpId)
            if not cdrId:
                key = (docType, ctrpId)
                problems[key] = MappingProblem(docType, value, ctrpId)
                if ctrpId not in poIds:
                    cdr.addExternalMapping(session, POID, ctrpId)
                    poIds[ctrpId] = None
    for node in tree.xpath("//address"):
        country = state = ''
        for child in node.findall('state'):
            state = child.text.strip()
        for child in node.findall('country'):
            country = child.text.strip()
        if geoMappings.lookupCountryId(country) is None:
            problems[('Country', country)] = MappingProblem('Country', country)
        if geoMappings.lookupStateId(state, country) is None:
            value = u"%s|%s" % (state, country)
            key = ('State/Province', value)
            problems[key] = MappingProblem('State/Province', value)
    return title, problems

def addNewDoc(session, docType, trialId, poId, poidUsage):
    conn = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""\
SELECT doc_id
  FROM external_map
 WHERE usage = ?
   AND value = ?""", (poidUsage, poId))
    rows = cursor.fetchall()
    originalRow = rows and rows[0] or None
    if originalRow and originalRow[0]:
        raise Exception("CTRP po_id %s already mapped to CDR%d" %
                        (poId, originalRow[0]))
    cursor.execute("SELECT doc_xml FROM ctrp_import WHERE ctrp_id = ?", trialId)
    rows = cursor.fetchall()
    if not rows or not rows[0][0]:
        raise Exception("trial document for %s not found" % trialId)
    docXml = rows[0][0]
    tree = etree.XML(docXml.encode('utf-8'))
    doc = None
    for node in tree.xpath("//*[po_id='%s']" % poId):
        if docType == 'Organization':
            org = ctrp.Protocol.Org(node)
            doc = cdr.makeCdrDoc(org.createCdrDocXml(), docType)
        elif docType == 'Person':
            person = ctrp.Person(node)
            doc = cdr.makeCdrDoc(person.createCdrDocXml(), docType)
        else:
            raise Exception("unexpected document type '%s'" % docType)
        comment = 'filling CTRP mapping gap'
        response = cdr.addDoc(session, doc=doc, comment=comment, reason=comment,
                              checkIn='Y', ver='Y', verPublishable='N')
        err = cdr.checkErr(response)
        if err:
            raise Exception(err)
        cdrId = cdr.exNormalize(response)[1]
        if originalRow:
            cursor.execute("""\
UPDATE external_map
   SET doc_id = ?
 WHERE value = ?
   AND usage = ?""", (cdrId, poId, poidUsage))
            conn.commit()
        else:
            cdr.addExternalMapping(session, POID, poId, cdrId)
        return cdrId
    raise Exception("po_id %s not found in %s" % (poId, trialId))

def main():
    fields = cgi.FieldStorage()
    docType = fields.getvalue('type')
    trialId = fields.getvalue('trial')
    poId = fields.getvalue('poid')
    cdrId = fields.getvalue('cdrid')
    msg = fields.getvalue('msg')
    session = cdrcgi.getSession(fields)
    cursor = cdrdb.connect('CdrGuest').cursor()
    #cursor.execute("SELECT id FROM external_map_usage WHERE name = ?", POID)
    #poidUsage = cursor.fetchall()[0][0]
    poidUsage = ctrp.getPoidUsage()
    status = ""
    if cdrId:
        msg = "Saved CTRP %s %s as CDR%s" % (docType.lower(), poId, cdrId)
        status = "<p class='status'>%s</p>" % msg
    if docType and trialId and poId:
        try:
            cdrId = addNewDoc(session, docType, trialId, poId, poidUsage)
            url = ("http://%s%s/ctrp-mapping-gaps.py?%s=%s&cdrid=%s"
                   "&type=%s&poid=%s" %
                   (cdrcgi.WEBSERVER, cdrcgi.BASE, cdrcgi.SESSION, session,
                    cdrId, docType, poId))
            header = "Location: %s" % url
            status = u"<p>header: %s; doc saved as %s" % (header, cdrId)
            print header + "\n"
            sys.exit(0)
        except Exception, e:
            status = u"<p class='err'>%s</p>" % cgi.escape(unicode(e))
        trialId = None
    poIds = ctrp.getPoidMappings()
    geoMap = ctrp.GeographicalMappings()
    html = [u"""\
<html>
 <head>
  <title>CTRP Mapping Gaps</title>
  <meta http-equiv='Content-Type' content='text/html;charset=utf-8' />
  <style type="text/css">
   * { font-family: Arial, sans-serif }
   h1 { color: maroon }
   table { border-collapse: collapse }
   .err { color: red; font-weight: bold }
   .status { color: green; font-weight: bold }
   tr.trial { color: green; font-weight: bold; }
   tr.trial td { border-top: solid black 1px; }
   td.add { width: 100px; }
  </style>
 </head>
 <body>
  <h1>CTRP Mapping Gaps</h1>
  <!--<h2>%s</h2>-->
  <h2>@@QUEUED@@ Trials Queued For Site Import (@@GAPS@@ With Mapping Gaps)</h2>
  %s
  <table width="100%%">
""" % (session, status)]
    if trialId:
        cursor.execute("""\
  SELECT ctrp_id, cdr_id, nct_id, doc_xml
    FROM ctrp_import
   WHERE ctrp_id = ?""", trialId)
    else:
        cursor.execute("""\
  SELECT i.ctrp_id, i.cdr_id, i.nct_id, i.doc_xml
    FROM ctrp_import i
    JOIN ctrp_import_disposition d
      ON d.disp_id = i.disposition
   WHERE d.disp_name = 'import requested'
ORDER BY i.ctrp_id""")
    queued = withGaps = 0
    findMappingProblems = ctrp.MappingProblem.findMappingProblems
    for ctrpId, cdrId, nctId, docXml in cursor.fetchall():
        queued += 1
        try:
            tree = etree.XML(docXml.encode('utf-8'))
            title = ctrp.MappingProblem.getChildText(tree, 'official_title')
            problems = findMappingProblems(session, tree, poIds, geoMap)
##             title, problems = findMappingProblems(session,
##                                                   docXml.encode('utf-8'),
##                                                   poIds, geoMap)
        except Exception, e:
            html.append(u"""\
<tr><td colspan='4' class='err'>Trial %s: %s</td></tr>
""" % (ctrpId, e))
            #raise
            continue
        if not problems:
            continue
        withGaps += 1
        html.append(u"""\
   <tr><td>&nbsp;</td></tr>
   <tr class="trial">
    <td colspan="2" valign="top">%s</td><td colspan='2'>%s</td>
   </tr>
""" % (fix(ctrpId), fix(title)))
        for docType in ('Organization', 'Person', 'Country', 'State/Province'):
            for key in problems:
                if key[0] != docType:
                    continue
                problem = problems[key]
                if problem.ctrpId:
                    url = ("ctrp-mapping-gaps.py?%s=%s&type=%s&trial=%s&"
                           "poid=%s" % (cdrcgi.SESSION, session,
                                        docType, ctrpId, problem.ctrpId))
                    add = '<a href="%s">Add Doc</a>' % url
                else:
                    add = "&nbsp;"
                html.append(u"""\
   <tr>
    <td valign="top" class="add">%s</td>
    <td valign="top">%s</td>
    <td valign="top">%s</td>
    <td>%s</td>
   </tr>
""" % (add, problem.docType,
       problem.ctrpId and cgi.escape(problem.ctrpId) or u"&nbsp;",
       problem.value and cgi.escape(problem.value) or "None"))
    html.append(u"""\
  </table>
 </body>
</html>""")
    html = u"".join(html)
    html = html.replace(u"@@QUEUED@@", unicode(queued))
    html = html.replace(u"@@GAPS@@", unicode(withGaps))
    print "Content-type: text/html; charset=utf-8\n"
    print html.encode("utf-8")

if __name__ == "__main__":
    main()
