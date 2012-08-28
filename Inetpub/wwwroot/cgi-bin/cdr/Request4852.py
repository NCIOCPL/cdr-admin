#----------------------------------------------------------------------
#
# $Id$
#
# Here's the email trail for the request:
#
# ===============================================================
# From: Lakshmi
# Date: 2010-05-23 23:12
# ===============================================================
# Hi Bob
#
# I am so sorry to bother you, but I have been asked to produce an
# urgent report by 9 am tomorrow.  - Trials that we first registered in
# NLM between Jan 2010 and May 2010 with primary protocol ID, NCTID and
# source. I know you don't have dates for NLM registration, but you can
# take use the published to Cancer.gov date to determine this since our
# registration should have happened soon after that date.
#
# I will probably need some more reports later tomorrow based on a 9 am
# call that I need to have with some key folks
# Lakshmi
#
# ===============================================================
# From: Bob
# Date: 2010-05-24 00:17
# ===============================================================
# http://bach.nci.nih.gov/cgi-bin/cdr/Report20100523.py
#
# I had to go back to the latest version of the document whose type was
# InScopeProtocol, because some have since become CTGovProtocol docs.
#
# ===============================================================
# From: Lakshmi
# Date: 2010-05-24 06:34
# ===============================================================
# Thanks Bob for responding so quickly. As always, your effort is truly
# appreciated. I do have a couple of tweaks - would it be possible to
# highlight documents that have since become CTGOV protocol docs or docs
# that we have transferred ownership for. Also, could you give me total
# number for each source
#
# Thanks
#
# ===============================================================
# From: Bob
# Date: 2010-05-24 08:41
# ===============================================================
# New column added for current doc type.  Docs with
# CTGovOwnershipTransferInfo block shown in red.  Source counts at the
# bottom.
#
# http://bach.nci.nih.gov/cgi-bin/cdr/Report20100523.py
#
# BZIssue::4852
#
#----------------------------------------------------------------------
import cdrdb, lxml.etree as etree, cgi

def fix(me):
    if not me:
        return u""
    return cgi.escape(me)

class Trial:
    def __init__(self, cursor, cdrId):
        self.cdrId = cdrId
        self.primaryId = self.source = self.nctId = None
        self.transferred = False
        self.docType = None
        sources = []
        cursor.execute("""\
            SELECT t.name
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
             WHERE d.id = ?""", cdrId)
        self.docType = cursor.fetchall()[0][0]
        cursor.execute("""\
            SELECT xml
              FROM doc_version
             WHERE id = %d
               AND num = (SELECT MAX(num)
                            FROM doc_version
                           WHERE id = %d
                             AND doc_type = 18)""" % (cdrId, cdrId))
        #cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        for node in tree.findall('ProtocolIDs/PrimaryID/IDString'):
            self.primaryId = node.text
        for node in tree.findall('ProtocolIDs/OtherID'):
            idType = idString = None
            for child in node:
                if child.tag == 'IDType':
                    idType = child.text
                elif child.tag == 'IDString':
                    idString = child.text
            if idType == 'ClinicalTrials.gov ID':
                self.nctId = idString
        for node in tree.findall('ProtocolSources/ProtocolSource/SourceName'):
            sources.append(node.text)
        for node in tree.findall('.//CTGovOwnershipTransferInfo'):
            self.transferred = True
        self.source = "; ".join(sources)

cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
  SELECT n.id, MIN(p.completed)
    FROM pub_proc_nlm n
    JOIN pub_proc_doc d
      ON d.doc_id = n.id
    JOIN pub_proc p
      ON d.pub_proc = p.id
   WHERE d.failure IS NULL
     AND p.status = 'Success'
     AND p.pub_system = 178
  GROUP BY n.id
  HAVING MIN(p.completed) BETWEEN '2010-01-01' AND '2010-06-01'
ORDER BY MIN(p.completed)""")
report = [u"""\
<html>
 <head>
  <title>Registered in NLM Between Jan 2010 and May 2010</title>
  <style type='text/css'>
   * { font-family: Arial, sans-serif; font-size: 10pt; }
   h1 { font-size: 14pt; color: maroon; }
   th { color: green; }
   .transferred { color: red; }
  </style>
 </head>
 <body>
  <h1>Registered in NLM Between Jan 2010 and May 2010</h1>
  <table border='1' cellspacing='0' cellpadding='4'>
   <tr>
    <th>CDR ID</th>
    <th>Primary ID</th>
    <th>NCT ID</th>
    <th>Source</th>
    <th>Current Doc Type</th>
   </tr>
"""]
rows = cursor.fetchall()
sources = {}
for cdrId, firstPub in rows:
    trial = Trial(cursor, cdrId)
    sources[trial.source] = sources.get(trial.source, 0) + 1
    cls = trial.transferred and 'transferred' or 'pdq'
    report.append(u"""\
   <tr class='%s'>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (cls, trial.cdrId, fix(trial.primaryId), fix(trial.nctId),
       fix(trial.source), trial.docType))
report.append(u"""\
  </table>
  <ul>
""")
for source in sources:
    report.append(u"""\
   <li>%s (%d)</li>
""" % (fix(source), sources[source]))
report.append(u"""\
  </ul>
 </body>
</html>""")
print "Content-type: text/html; charset=utf-8\n"
print u"".join(report).encode('utf-8')

