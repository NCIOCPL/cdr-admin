#----------------------------------------------------------------------
#
# $Id: ProtSearch.py,v 1.13 2003-12-17 01:21:33 bkline Exp $
#
# Prototype for duplicate-checking interface for Protocol documents.
#
# $Log: not supported by cvs2svn $
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
import cgi, cdr, cdrcgi, re, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields and fields.getvalue("Boolean")          or "AND"
title     = fields and fields.getvalue("Title")            or None
idNums    = fields and fields.getvalue("IdNums")           or None
submit    = fields and fields.getvalue("SubmitButton")     or None
help      = fields and fields.getvalue("HelpButton")       or None
dispFmt   = fields and fields.getvalue("DispFormat")       or 'fu'
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

fmts = {}
fmts['fu'] = DisplayFormat(1, 'Full',     'QC InScopeProtocol Full Set')
fmts['ad'] = DisplayFormat(2, 'Admin',    'QC InScopeProtocol Admin Set')
fmts['hp'] = DisplayFormat(3, 'HP',       'QC InScopeProtocol HP Set')
fmts['pa'] = DisplayFormat(4, 'Patient',  'QC InScopeProtocol Patient Set')
fmts['ci'] = DisplayFormat(5, 'Citation', 'QC InScopeProtocol Citation Set')

def makeDispFormat(fieldName):
    field = "<br>"
    keys = fmts.keys()
    keys.sort(lambda a,b: cmp(fmts[a], fmts[b]))
    checked = " checked='1'"
    for key in keys:
        fmt = fmts[key]
        field += """
    <input type='radio' name='%s' value='%s'%s>
     Protocol %s QC Report Format<br>
""" % (fieldName, key, checked, fmt.display)
        checked = ""
    return field

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Title',                        'Title'),
              ('Protocol ID Numbers',          'IdNums'))
    extraField = ('<br>Display Format', makeDispFormat('DispFormat'))
              #('Diaplay Format:',               'DispFormat', makeDispFormat))
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
                                          extraField = extraField)
    page += """\
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(page)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
searchFields = (cdrcgi.SearchField(title,
                            ("/InScopeProtocol/ProtocolTitle",
                             "/OutOfScopeProtocol/ProtocolTitle/TitleText",
                             "/ScientificProtocolInfo/ProtocolTitle",
                             "/CTGovProtocol/BriefTitle",
                             "/CTGovProtocol/OfficialTitle")),
                cdrcgi.SearchField(idNums,
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
                             "/CTGovProtocol/IDInfo/OrgStudyID")))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                   ("InScopeProtocol",
                                                    "OutOfScopeProtocol",
                                                    "ScientificProtocolInfo",
                                                    "CTGovProtocol"))
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
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Protocol documents: %s' % 
                info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Protocol", rows, strings, 
    {'InScopeProtocol':'set:%s' % fmts[dispFmt].filterSet,
     'OutOfScopeProtocol':'name:Health Professional QC Content Report',
     'ScientificProtocolInfo':'name:Health Professional QC Content Report',
     'CTGovProtocol':'name:CTGovProtocol QC Report'}, session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
