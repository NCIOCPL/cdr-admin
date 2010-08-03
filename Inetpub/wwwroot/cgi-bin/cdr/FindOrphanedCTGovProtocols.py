#----------------------------------------------------------------------
#
# $Id$
#
# Report to identify trials NLM is no longer sending us.
#
# BZIssue::4879
#
#----------------------------------------------------------------------
import cdrdb, glob, os, re, urllib2, cStringIO, zipfile, lxml.etree as etree
import sys, cdrcgi

def getFiles():
    pattern = re.compile('CTGovDownload-(\\d+).zip')
    dirs = glob.glob('d:/cdr/Utilities/CTGovDownloads/CTGovDownload-20*.zip')
    dirs.sort()
    while dirs:
        d = dirs.pop()
        match = pattern.search(d)
        workDir = 'd:/cdr/Utilities/CTGovDownloads/work-%s' % match.group(1)
        files = glob.glob("%s/*.xml" % workDir)
        if len(files) > 25000:
            return workDir, [os.path.basename(n).lower() for n in files]
    
def getNlmXml(nctId):
    import httplib
    conn = httplib.HTTPConnection("clinicaltrials.gov")
    method = "/ct2/results?term=%s&studyxml=true" % nctId
    conn.request("GET", method)
    response = conn.getresponse()
    if response.status != 200:
        return None
    page = response.read()
    response.close()
    response = None
    try:
        fp = cStringIO.StringIO(page)
        zf = zipfile.ZipFile(fp)
        for name in zf.namelist():
            if name.lower().endswith('.xml'):
                docXml = zf.read(name)
                zf = None
                fp = None
                return docXml
    except Exception, e:
        return None

def getNlmStatus(nctId):
    docXml = getNlmXml(nctId)
    if not docXml:
        return u"Failure retrieving trial document from NLM"
    try:
        tree = etree.XML(docXml)
    except Exception, e:
        return u"Unable to parse trial document from NLM"
    for e in tree.findall('overall_status'):
        return e.text
    return u"Unable to find status in NLM's document"

def getPdqStatus(cdrId, cursor):
    cursor.execute("""\
        SELECT value
          FROM query_term
         WHERE path = '/CTGovProtocol/OverallStatus'
           AND doc_id = ?""", cdrId)
    rows = cursor.fetchall()
    return rows and rows[0][0] or None

def isBlocked(cdrId, cursor):
    cursor.execute("""\
        SELECT active_status
          FROM all_docs
         WHERE id = ?""", cdrId)
    rows = cursor.fetchall()
    if not rows:
        return True
    return rows[0][0].upper() != 'A'

class Trial:
    def __init__(self, nctId, cdrId, cursor):
        self.nctId = nctId
        self.cdrId = cdrId
        self.nlmStatus = getNlmStatus(nctId)
        self.pdqStatus = getPdqStatus(cdrId, cursor)
        self.isBlocked = isBlocked(cdrId, cursor)
    def __cmp__(self, other):
        diff = cmp(self.nlmStatus, other.nlmStatus)
        if diff:
            return diff
        diff = cmp(self.pdqStatus, other.pdqStatus)
        if diff:
            return diff
        return cmp(self.nctId, other.nctId)

def main():
    workDir, files = getFiles()
    names = set([f[:-4] for f in files])
    html = [u"""\
<html>
 <head>
  <title>Orphaned CTGovProtocol Documents</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; font-size: 10pt }
   h1 { color: maroon; font-size: 14pt }
   h2 { color: blue; font-size: 12pt }
   th { color: green }
  </style>
 </head>
 <body>
  <h1>Orphaned CTGovProtocol Documents</h1>
  <h2>Last Download in %s</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>NCT ID</th>
    <th>CDR ID</th>
    <th>NLM Status</th>
    <th>PDQ Status</th>
    <th>Blocked?</th>
   </tr>
""" % workDir]
    orphaned = []
    done = 0
    cursor = cdrdb.connect('CdrGuest').cursor()
    cursor.execute("""\
        SELECT cdr_id, nlm_id
          FROM ctgov_import
         WHERE disposition = 6
      ORDER BY nlm_id""")
    rows = cursor.fetchall()
    for cdrId, nlmId in rows:
        if nlmId.lower() not in names:
            orphaned.append(Trial(nlmId, cdrId, cursor))
        done += 1
    orphaned.sort()
    for trial in orphaned:
        html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (trial.nctId.upper(), trial.cdrId, trial.nlmStatus, trial.pdqStatus,
       trial.isBlocked and u"Yes" or u"No"))
    html.append(u"""\
  </table>
 </body>
</html>""")
    cdrcgi.sendPage(u"".join(html))

if __name__ == '__main__':
    main()
