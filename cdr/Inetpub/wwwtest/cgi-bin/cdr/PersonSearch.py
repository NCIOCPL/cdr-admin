#----------------------------------------------------------------------
#
# $Id: PersonSearch.py,v 1.9 2003-02-13 13:36:20 bkline Exp $
#
# Prototype for duplicate-checking interface for Person documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.8  2002/11/14 13:53:41  bkline
# Adjusted paths to match schema changes.
#
# Revision 1.7  2002/06/26 20:05:25  bkline
# Modified advanced Person search forms to use QcReport.py for doc display.
#
# Revision 1.6  2002/06/06 12:01:27  bkline
# Added calls to cdrcgi.unicodeToLatin1().
#
# Revision 1.5  2002/06/04 20:19:35  bkline
# Fixed typos in query_term paths.
#
# Revision 1.4  2002/05/08 17:41:51  bkline
# Updated to reflect Volker's new filter names.
#
# Revision 1.3  2002/04/12 19:57:19  bkline
# Installed new filters.
#
# Revision 1.2  2002/02/14 19:38:41  bkline
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
boolOp    = fields and fields.getvalue("Boolean")         or "AND"
surname   = fields and fields.getvalue("Surname")         or None
givenName = fields and fields.getvalue("GivenName")       or None
initials  = fields and fields.getvalue("Initials")        or None
street    = fields and fields.getvalue("Street")          or None
city      = fields and fields.getvalue("City")            or None
state     = fields and fields.getvalue("State")           or None
zip       = fields and fields.getvalue("ZipCode")         or None
country   = fields and fields.getvalue("Country")         or None
submit    = fields and fields.getvalue("SubmitButton")    or None
help      = fields and fields.getvalue("HelpButton")      or None

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
    fields = (('Surname',                 'Surname'),
              ('Given Name',              'GivenName'),
              ('Initials',                'Initials'),
              ('Street',                  'Street'),
              ('City',                    'City'),
              ('State',                   'State', cdrcgi.stateList),
              ('ZIP Code',                'ZipCode'),
              ('Country',                 'Country', cdrcgi.countryList))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Person Search Form",
                                          "PersonSearch.py",
                                          fields,
                                          buttons,
                                          'Person',
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
searchFields = (cdrcgi.SearchField(surname,
                            ("/Person/PersonNameInformation/SurName",)),
                cdrcgi.SearchField(givenName,
                            ("/Person/PersonNameInformation/GivenName",)),
                cdrcgi.SearchField(initials,
                            ("/Person/PersonNameInformation/MiddleInitial",)),
                cdrcgi.SearchField(street,
                            ("/Person/PersonLocations/Home/PostalAddress/"
                             "Street",
                             "/Person/PersonLocations/PrivatePractice/"
                             "PrivatePracticeLocation/PostalAddress/Street",
                             "/Person/PersonLocations/OtherPracticeLocation/"
                             "SpecificPostalAddress/Street")),
                cdrcgi.SearchField(city,
                            ("/Person/PersonLocations/Home/PostalAddress/"
                             "City",
                             "/Person/PersonLocations/PrivatePractice/"
                             "PrivatePracticeLocation/PostalAddress/City",
                             "/Person/PersonLocations/OtherPracticeLocation/"
                             "SpecificPostalAddress/City")),
                cdrcgi.SearchField(state,
                            ("/Person/PersonLocations/Home/PostalAddress/"
                             "PoliticalSubUnit_State/@cdr:ref",
                             "/Person/PersonLocations/PrivatePractice/"
                             "PrivatePracticeLocation/"
                             "PostalAddress/PoliticalSubUnit_State/@cdr:ref",
                             "/Person/PersonLocations/OtherPracticeLocation/"
                             "SpecificPostalAddress/"
                             "PoliticalSubUnit_State/@cdr:ref")),
                cdrcgi.SearchField(zip,
                            ("/Person/PersonLocations/Home/PostalAddress/"
                             "PostalCode_ZIP",
                             "/Person/PersonLocations/PrivatePractice/"
                             "PrivatePracticeLocation/"
                             "PostalAddress/PostalCode_ZIP",
                             "/Person/PersonLocations/OtherPracticeLocation/"
                             "SpecificPostalAddress/PostalCode_ZIP")),
                cdrcgi.SearchField(country,
                            ("/Person/PersonLocations/Home/PostalAddress/"
                             "Country/@cdr:ref",
                             "/Person/PersonLocations/PrivatePractice/"
                             "PrivatePracticeLocation/"
                             "PostalAddress/Country/@cdr:ref",
                             "/Person/PersonLocations/OtherPracticeLocation/"
                             "SpecificPostalAddress/"
                             "Country/@cdr:ref")))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                       "Person")
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
    cdrcgi.bail('Failure retrieving Person documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Person", rows, strings, None, session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(cdrcgi.unicodeToLatin1(html))
