#----------------------------------------------------------------------
#
# $Id: GeoSearch.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Prototype for duplicate-checking interface for Geographic Entity documents.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
boolOp  = fields and fields.getvalue("Boolean")         or "AND"
country = fields and fields.getvalue("Country")         or None
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
    fields = (('Country Name',            'Country'),
              ('Political Unit Name',     'State'))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Geographic Entity Search Form",
                                          "GeoSearch.py",
                                          fields,
                                          buttons,
                                          'GeographicEntity',
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
searchFields = (cdrcgi.SearchField(country,
                            ("/GeographicEntity/AlternateName",
                             "/GeographicEntity/CountryFullName",
                             "/GeographicEntity/CountryShortName")),
                cdrcgi.SearchField(state,
                            ("/GeographicEntity/PoliticalUnit"
                             "/PoliticalUnitAlternateName",
                             "/GeographicEntity/PoliticalUnit"
                             "/PoliticalUnitFullName",
                             "/GeographicEntity/PoliticalUnit"
                             "/PoliticalUnitShortName")))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                       "GeographicEntity")
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
    cdrcgi.bail('Failure retrieving Geographic Entity documents: %s' % 
                info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Geographic Entity", rows, strings, 
                                        'CDR266297')

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
