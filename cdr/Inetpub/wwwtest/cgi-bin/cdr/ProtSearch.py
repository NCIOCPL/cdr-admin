#----------------------------------------------------------------------
#
# $Id: ProtSearch.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Prototype for duplicate-checking interface for Protocol documents.
#
# $Log: not supported by cvs2svn $
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
loPers    = fields and fields.getvalue("LeadOrgPersonnel") or None
submit    = fields and fields.getvalue("SubmitButton")     or None
help      = fields and fields.getvalue("HelpButton")       or None

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
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Title',                        'Title'),
              ('Protocol ID Numbers',          'IdNums'),
              ('Lead Organization Personnel',  'LeadOrgPersonnel'))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Protocol Search Form",
                                          "ProtSearch.py",
                                          fields,
                                          buttons,
                                          'Protocol',
                                          conn)
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
                             "/OutOfScopeProtocol/ProtocolTitle",
                             "/ScientificProtocolInfo/ProtocolTitle")),
                cdrcgi.SearchField(idNums,
                            ("/InScopeProtocol/IdentificationInfo"
                             "/ProtocolPDQID",
                             "/InScopeProtocol/IdentificationInfo"
                             "/ProtocolIDs/PrimaryID/IDstring",
                             "/InScopeProtocol/IdentificationInfo"
                             "/ProtocolIDs/OtherID/IDstring",
                             "/OutOfScopeProtocol/IdentificationInfo"
                             "/ProtocolPDQID",
                             "/OutOfScopeProtocol/IdentificationInfo"
                             "/ProtocolIDs/PrimaryID/IDstring",
                             "/OutOfScopeProtocol/IdentificationInfo"
                             "/ProtocolIDs/OtherID/IDstring",
                             "/ScientificProtocolInfo/IdentificationInfo"
                             "/ProtocolPDQID",
                             "/ScientificProtocolInfo/IdentificationInfo"
                             "/ProtocolIDs/PrimaryID/IDstring",
                             "/ScientificProtocolInfo/IdentificationInfo"
                             "/ProtocolIDs/OtherID/IDstring")),
                cdrcgi.SearchField(loPers,
                            ("/InScopeProtocol/ProtocolAdminInfo"
                             "/ProtocolLeadOrg/LeadOrgPersonnel/Person",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                   ("InScopeProtocol",
                                                    "OutOfScopeProtocol",
                                                    "ScientificProtocolInfo"))
if not query:
    cdrcgi.bail('No query criteria specified')
#cdrcgi.bail("QUERY: [%s]" % query)
#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute(query)
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
                                        {'InScopeProtocol':'CDR266310',
                                         'OutOfScopeProtocol':'CDR266310',
                                         'ScientificProtocolInfo':'CDR266310'})

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
