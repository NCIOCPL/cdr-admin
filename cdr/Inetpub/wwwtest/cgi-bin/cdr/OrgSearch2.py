#----------------------------------------------------------------------
#
# $Id: OrgSearch2.py,v 1.2 2002-02-14 19:37:23 bkline Exp $
#
# Prototype for duplicate-checking interface for Organization documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
# Revision 1.1  2001/07/17 19:17:43  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
boolOp  = fields and fields.getvalue("Boolean")         or "AND"
orgName = fields and fields.getvalue("OrgName")         or None
city    = fields and fields.getvalue("City")            or None
state   = fields and fields.getvalue("State")           or None
country = fields and fields.getvalue("Country")         or None
zip     = fields and fields.getvalue("ZipCode")         or None
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
    fields = (('Organization Name',       'OrgName'),
              ('City',                    'City'),
              ('State',                   'State', cdrcgi.stateList),
              ('Country',                 'Country', cdrcgi.countryList),
              ('ZIP Code',                'ZipCode'))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Organization Search Form",
                                          "OrgSearch2.py",
                                          fields,
                                          buttons,
                                          'Organization',
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
searchFields = (cdrcgi.SearchField(orgName,
                            ("/Organization/OrganizationNameInformation/"
                             "OfficialName/Name",
                             "/Organization/OrganizationNameInformation/"
                             "ShortName/Name",
                             "/Organization/OrganizationNameInformation/"
                             "AlternateName")),
                cdrcgi.SearchField(city,
                            ("/Organization/OrganizationLocations/"
                             "OrganizationLocation/Location/PostalAddress/"
                             "City",)),
                cdrcgi.SearchField(state,
                            ("/Organization/OrganizationLocations/"
                             "OrgzniationLocation/Location/PostalAddress/"
                             "PoliticalSubUnit_State/@cdr:ref",)),
                cdrcgi.SearchField(country,
                            ("/Organization/OrganizationLocations/"
                             "OrganizationLocation/Location/PostalAddress/"
                             "Country/@cdr:ref",)),
                cdrcgi.SearchField(zip,
                            ("/Organization/OrganizationLocations/"
                             "OrganizationLocation/Location/PostalAddress/"
                             "PostalCode_ZIP",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                       "Organization")
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
    cdrcgi.bail('Failure retrieving Organization documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Organization", rows, strings, 
                    'name:Organization Denormalized XML filter&Filter1='
                    'name:Organization QC Report Filter')

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
