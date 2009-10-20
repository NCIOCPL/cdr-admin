#----------------------------------------------------------------------
#
# $Id$
#
# Duplicate-checking interface for Political SubUnit documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2003/07/29 12:42:23  bkline
# Plugged in filter set instead of single named filter.
#
# Revision 1.1  2002/02/14 19:36:35  bkline
# Broken out from original GeographicEntity search pages.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
state   = fields and fields.getvalue("State")           or None
submit  = fields and fields.getvalue("SubmitButton")    or None
help    = fields and fields.getvalue("HelpButton")      or None

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
    fields = (('Political SubUnit Name',            'State'),)
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Political SubUnit Search Form",
                                          "PoliticalSubUnitSearch.py",
                                          fields,
                                          buttons,
                                          'State',
                                          conn)
    page += """\
  </FORM>
 </BODY>
</HTML>
"""
    # Need to send a unicode string to sendPage()
    # -------------------------------------------
    page = page.decode('utf-8')

    cdrcgi.sendPage(page)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
searchFields = (cdrcgi.SearchField(state,
                        ("/PoliticalSubUnit/PoliticalSubUnitFullName",
                         "/PoliticalSubUnit/PoliticalSubUnitShortName",
                         "/PoliticalSubUnit/PoliticalSubUnitAlternateName")),)

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, None, 
                                                       "PoliticalSubUnit")
#cdrcgi.bail(query)
if not query:
    cdrcgi.bail('No query criteria specified')

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
    cdrcgi.bail('Failure retrieving PoliticalSubUnit documents: %s' % 
            info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("PoliticalSubUnit", rows, strings, 
                                        'set:QC PoliticalSubUnit Set')

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
