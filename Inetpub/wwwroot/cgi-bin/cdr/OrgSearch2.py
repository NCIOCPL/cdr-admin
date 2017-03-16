#----------------------------------------------------------------------
# Duplicate-checking interface for Organization documents.
#----------------------------------------------------------------------
import cgi, cdrcgi, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
boolOp  = fields and fields.getvalue("Boolean")         or "AND"
orgName = fields and fields.getvalue("OrgName")         or None
orgType = fields and fields.getvalue("OrgType")         or None
street  = fields and fields.getvalue("Street")          or None
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
# Validate parameters that can be validated
#----------------------------------------------------------------------
cdrcgi.valParmVal(boolOp, valList=('AND', 'OR'))
if orgType:
    orgTypes = cdrcgi.organizationTypeList(conn, 'OrgType', valCol=0)
    cdrcgi.valParmVal(orgType, valList=orgTypes)
if submit:
    cdrcgi.valParmVal(submit, valList='Search')
if help:
    cdrcgi.valParmVal(submit, valList='Help')
if state:
    cdrcgi.valParmVal(state,
                      valList=cdrcgi.stateList(conn, 'State', valCol=0))
if country:
    cdrcgi.valParmVal(country,
                      valList=cdrcgi.countryList(conn, 'Country', valCol=0))
if zip and country in ('U.S.A', 'United States'):
    cdrcgi.valParmVal(zip, cdrcgi.VP_US_ZIPCODE)

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Organization Name',       'OrgName'),
              ('Organization Type',       'OrgType',
                                           cdrcgi.organizationTypeList),
              ('Street',                  'Street'),
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
                             "AlternateName",
                             "/Organization/OrganizationNameInformation/"
                             "FormerName")),
                cdrcgi.SearchField(orgType,
                            ("/Organization/OrganizationType",)),
                cdrcgi.SearchField(street,
                            ("/Organization/OrganizationLocations/"
                             "OrganizationLocation/Location/PostalAddress/"
                             "Street",)),
                cdrcgi.SearchField(city,
                            ("/Organization/OrganizationLocations/"
                             "OrganizationLocation/Location/PostalAddress/"
                             "City",)),
                cdrcgi.SearchField(state,
                            ("/Organization/OrganizationLocations/"
                             "OrganizationLocation/Location/PostalAddress/"
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
    cursor.execute(query, timeout = 300)
    rows = cursor.fetchall()
    cursor.close()
    cursor = None
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Organization documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Organization", rows, strings,
                                        None, session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
