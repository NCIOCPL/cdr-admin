#----------------------------------------------------------------------
#
# $Id: ProtSearch.py,v 1.19 2009-07-01 21:13:54 bkline Exp $
#
# Prototype for duplicate-checking interface for Protocol documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.18  2009/05/11 17:51:30  venglisc
# Converted string to unicode before passing to sendPage(). (Bug 4560)
#
# Revision 1.17  2009/05/01 02:07:10  ameyer
# Forced input form sent to sendPage into unicode to silence warning.
# Also checking in debugging code that Bob added some time ago.
#
# Revision 1.16  2006/06/06 22:10:37  bkline
# Added ability to enter CDR ID directly.
#
# Revision 1.15  2004/04/09 12:17:32  bkline
# Added SecondaryID to list of CTGovProtocol elements to be searched
# (see Sheri's comment #10 for request #1165).
#
# Revision 1.14  2004/04/06 18:52:37  bkline
# Implemented enhancements for request #1165.
#
# Revision 1.13  2003/12/17 01:21:33  bkline
# Added code to pass session to results page function (to support
# CTGovProtocol report).
#
# Revision 1.12  2003/12/17 01:06:00  bkline
# Added support for CTGovProtocol documents.
#
# Revision 1.11  2003/12/16 15:45:42  bkline
# Added TitleText to path for out of scope protocol searches.
#
# Revision 1.10  2003/12/08 18:46:08  bkline
# Increased query timeout.
#
# Revision 1.9  2003/03/04 22:46:58  bkline
# Modifications for CDR enhancement request #301.
#
# Revision 1.8  2002/07/11 20:50:18  bkline
# Caught up with changed filter title.
#
# Revision 1.7  2002/05/30 17:06:41  bkline
# Corrected CVS log comment for previous version.
#
# Revision 1.6  2002/05/30 17:01:05  bkline
# New protocol filters from Cheryl.
#
# Revision 1.5  2002/05/08 17:41:51  bkline
# Updated to reflect Volker's new filter names.
#
# Revision 1.4  2002/04/12 20:01:55  bkline
# Plugged in new filters for InScopeProtocol documents.
#
# Revision 1.3  2002/02/20 03:58:55  bkline
# Modified search paths to match modified schemas.
#
# Revision 1.2  2002/02/14 19:35:51  bkline
# Replaced hardwired filter ID with filter name.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
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
       ORDER BY value""" % STATUS_PATH
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
