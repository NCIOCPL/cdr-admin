#----------------------------------------------------------------------
#
# $Id: ProtSearch.py,v 1.5 2002-05-08 17:41:51 bkline Exp $
#
# Prototype for duplicate-checking interface for Protocol documents.
#
# $Log: not supported by cvs2svn $
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
              ('Protocol ID Numbers',          'IdNums'))
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
                            ("/InScopeProtocol/ProtocolIDs/PrimaryID/IDString",
                             "/InScopeProtocol/ProtocolIDs/OtherID/IDString",
                             "/OutOfScopeProtocol"
                             "/ProtocolIDs/PrimaryID/IDString",
                             "/OutOfScopeProtocol"
                             "/ProtocolIDs/OtherID/IDString",
                             "/ScientificProtocolInfo"
                             "/ProtocolIDs/PrimaryID/IDString",
                             "/ScientificProtocolInfo"
                             "/ProtocolIDs/OtherID/IDString")))

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
    {'InScopeProtocol':'name:Denormalization Filter (1/1): InScope Protocol'
     '&Filter1=name:Health Professional Protocol QC Content Report',
     'OutOfScopeProtocol':'name:Health Professional QC Content Report',
     'ScientificProtocolInfo':'name:Health Professional QC Content Report'})

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
