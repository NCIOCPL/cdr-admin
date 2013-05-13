#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for duplicate-checking interface for Protocol documents.
#
# BZIssue::301
# BZIssue::1165
# BZIssue::4560
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb, os

STATUS_PATH = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
DEBUGGING = False
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields and fields.getvalue("Boolean")          or "AND"
title     = fields and fields.getvalue("Title")            or None
idNums    = fields and fields.getvalue("IdNums")           or None
cdrIds    = fields and fields.getvalue("CdrIds")           or None
submit    = fields and fields.getvalue("SubmitButton")     or None
help      = fields and fields.getvalue("HelpButton")       or None
pstat     = fields.getvalue('pstat')
dispFmt   = fields and fields.getvalue("DispFormat")       or 'fu'
docType   = fields and fields.getvalue("DocType")          or 'All'
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
# Accomodate multiple display formats.
#----------------------------------------------------------------------
class DisplayFormat:
    def __init__(self, pos, display, filterSet):
        self.pos       = pos
        self.display   = display
        self.filterSet = filterSet
    def __cmp__(self, other):
        return cmp(self.pos, other.pos)

fmts = {
    'fu': DisplayFormat(1, 'Full',     'QC InScopeProtocol Full Set'),
    'ad': DisplayFormat(2, 'Admin',    'QC InScopeProtocol Admin Set'),
    'hp': DisplayFormat(3, 'HP',       'QC InScopeProtocol HP Set'),
    'pa': DisplayFormat(4, 'Patient',  'QC InScopeProtocol Patient Set'),
    'ci': DisplayFormat(5, 'Citation', 'QC InScopeProtocol Citation Set'),
    'ex': DisplayFormat(6, 'Excel',    None)
}

def makeDispFormat(fieldName):
    field = "<br>"
    keys = fmts.keys()
    keys.sort(lambda a,b: cmp(fmts[a], fmts[b]))
    checked = " checked='1'"
    for key in keys:
        if key == 'ex':
            label = "Excel Workbook Report Format"
        else:
            label = "Protocol %s Report Format" % fmts[key].display
        field += """
    <input type='radio' name='%s' value='%s'%s>%s<br>""" % (fieldName, key,
                                                            checked, label)
        checked = ""
    return field

def makeDoctypePicklist():
    return """\
      <BR>
      <SELECT   NAME        = "DocType"
                SIZE        = "1">
       <OPTION  SELECTED>All</OPTION>
       <OPTION>CTGovProtocol</OPTION>
       <OPTION>InScopeProtocol</OPTION>
       <OPTION>OutOfScopeProtocol</OPTION>
      </SELECT>
"""

#----------------------------------------------------------------------
# Generate picklist for protocol status.
#----------------------------------------------------------------------
def protocolStatusList(conn, fName):
    defaultOpt = "<option value='' selected>Select a status...</option>\n"
    query  = """\
SELECT DISTINCT value, value
           FROM query_term
          WHERE path = '%s'
       ORDER BY 1""" % STATUS_PATH
    pattern = "<option value='%s'>%s&nbsp;</option>"
    return cdrcgi.generateHtmlPicklist(conn, fName, query, pattern,
                                       firstOpt = defaultOpt)


#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('CDR ID(s)',                    'CdrIds'),
              ('Title',                        'Title'),
              ('Protocol ID Numbers',          'IdNums'),
              ('Protocol Status',              'pstat',
               protocolStatusList))
    extraFields = (('<br>Display Format', makeDispFormat('DispFormat')),
                   ('<br>Document Type', makeDoctypePicklist()))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Protocol Search Form",
                                          "ProtSearch.py",
                                          fields,
                                          buttons,
                                          'Protocol',
                                          conn,
                                          extraField = extraFields)
    page += u"""\
  </FORM>
 </BODY>
</HTML>
"""
    page = page.decode('utf-8')
    cdrcgi.sendPage(page)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
def selectPaths(docType, paths):
    if docType == 'All':
        return paths
    p = []
    for path in paths:
        if path.startswith("/%s/" % docType):
            p.append(path)
    return p

searchFields = (cdrcgi.SearchField(title, selectPaths(docType,
                            ("/InScopeProtocol/ProtocolTitle",
                             "/OutOfScopeProtocol/ProtocolTitle/TitleText",
                             "/ScientificProtocolInfo/ProtocolTitle",
                             "/CTGovProtocol/BriefTitle",
                             "/CTGovProtocol/OfficialTitle"))),
                cdrcgi.SearchField(idNums, selectPaths(docType,
                            ("/InScopeProtocol/ProtocolIDs/PrimaryID/IDString",
                             "/InScopeProtocol/ProtocolIDs/OtherID/IDString",
                             "/OutOfScopeProtocol"
                             "/ProtocolIDs/PrimaryID/IDString",
                             "/OutOfScopeProtocol"
                             "/ProtocolIDs/OtherID/IDString",
                             "/ScientificProtocolInfo"
                             "/ProtocolIDs/PrimaryID/IDString",
                             "/ScientificProtocolInfo"
                             "/ProtocolIDs/OtherID/IDString",
                             "/CTGovProtocol/IDInfo/OrgStudyID",
                             "/CTGovProtocol/IDInfo/SecondaryID",
                             "/CTGovProtocol/IDInfo/NCTID"))),
                cdrcgi.SearchField(pstat, selectPaths(docType,
                                                      (STATUS_PATH,))))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
if cdrIds:
    pattern = re.compile('[^\\d]+')
    strings = cdrIds.strip()
    cdrIds  = []
    for cdrId in strings.replace(',', ' ').split():
        intId = pattern.sub('', cdrId)
        if intId:
            cdrIds.append(intId)
if cdrIds:
    query = """\
  SELECT d.id, d.title, t.name
    FROM document d
    JOIN doc_type t
      ON t.id = d.doc_type
   WHERE d.id IN (%s)
ORDER BY d.title""" % ",".join(cdrIds)
    docType = 'All'
else:
    docTypes = ("InScopeProtocol",
                "OutOfScopeProtocol",
                "ScientificProtocolInfo",
                "CTGovProtocol")
    if docType != 'All':
        docTypes = docType
    (query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields,
                                                           boolOp, docTypes)
    if query and DEBUGGING:
        f = open('d:/tmp/ProtSearchQuery-%d.sql' % os.getpid(), 'wb')
        f.write(query)
        f.close()
if not query:
    cdrcgi.bail('No query criteria specified')

#cdrcgi.bail("QUERY: [%s]" % query)
#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query, timeout = 300)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Protocol documents: %s' %
                info[1][0])

def getProtocolStatus(docId):
    cursor.execute("""\
        SELECT value
          FROM query_term
         WHERE path = '%s'
           AND doc_id = ?""" % STATUS_PATH, docId)
    rows = cursor.fetchall()
    return rows and rows[0][0] or "None"

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
if dispFmt == 'ex':
    import ExcelWriter, time, sys
    try:
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except:
        pass
    book = ExcelWriter.Workbook()
    sheet = book.addWorksheet("Protocols")
    sheet.addCol(1, 50)
    sheet.addCol(2, 800)
    sheet.addCol(3, 125)
    rowNumber = 0
    for row in rows:
        r = sheet.addRow(rowNumber)
        r.addCell(1, row[0])
        r.addCell(2, row[1])
        r.addCell(3, getProtocolStatus(row[0]))
        rowNumber += 1
    stamp = time.strftime("%Y%m%d%H%M%S")
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=search-%s.xls" % stamp
    print
    book.write(sys.stdout, True)
    sys.exit(0)

filters = {
     'InScopeProtocol':'set:%s' % fmts[dispFmt].filterSet,
     'OutOfScopeProtocol':'name:Health Professional QC Content Report',
     'ScientificProtocolInfo':'name:Health Professional QC Content Report',
     'CTGovProtocol':'name:CTGovProtocol QC Report'}
if docType != 'All':
    filters = filters[docType]
html = cdrcgi.advancedSearchResultsPage("Protocol", rows, strings,
                                        filters, session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
