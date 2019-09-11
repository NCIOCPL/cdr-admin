#----------------------------------------------------------------------
#
# Prototype for duplicate-checking interface for GlossaryTerm documents.
#
# BZIssue::1335 - populate TermStatus picklist from database
# BZIssue::4381 - adjust for split of GlossaryTerm documents
# BZIssue::4473 - added definition status fields at William's request
#
#----------------------------------------------------------------------
import cgi, cdrcgi, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
boolOp     = fields.getvalue("Boolean")          or "AND"
nameEn     = fields.getvalue("NameEn")           or None
nameEs     = fields.getvalue("NameEs")           or None
statusEn   = fields.getvalue("StatusEn")         or None
statusEs   = fields.getvalue("StatusEs")         or None
definition = fields.getvalue("Definition")       or None
audience   = fields.getvalue("Audience")         or None
dictionary = fields.getvalue("Dictionary")       or None
defStatEn  = fields.getvalue("DefStatEn")        or None
defStatEs  = fields.getvalue("DefStatEs")        or None
submit     = fields.getvalue("SubmitButton")     or None
help       = fields.getvalue("HelpButton")       or None
typeName   = fields.getvalue("TypeName")         or None
statusList = cdrcgi.glossaryTermStatusList
audiences  = cdrcgi.glossaryAudienceList
dictionaries = cdrcgi.glossaryTermDictionaryList
subTitle   = { 'GlossaryTermName'   : 'Glossary Term Name',
               'GlossaryTermConcept': 'Glossary Term Concept' }

if help:
    cdrcgi.bail("Sorry, help for this interface has not yet been developed.")

#----------------------------------------------------------------------
# Input validation
#----------------------------------------------------------------------
if boolOp not in ('AND', 'OR'):
    cdrcgi.bail("Invalid search connector, internal error")

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
except cdrdb.Error as info:
    cdrcgi.bail('Failure connecting to CDR: %s' % info[1][0])


def spanishNameStatusList(conn, fName):
    path = '/GlossaryTermName/TranslatedName/TranslatedNameStatus'
    return cdrcgi.glossaryTermStatusList(conn, fName, path)
def englishDefinitionStatusList(conn, fName):
    path = '/GlossaryTermConcept/TermDefinition/DefinitionStatus'
    return cdrcgi.glossaryTermStatusList(conn, fName, path)
def spanishDefinitionStatusList(conn, fName):
    path = '/GlossaryTermConcept/TranslatedTermDefinition/TranslatedStatus'
    return cdrcgi.glossaryTermStatusList(conn, fName, path)

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields1= (('Name [en]',              'NameEn'                ),
              ('Status [en]',            'StatusEn',   statusList),
              ('Name [es]',              'NameEs'                ),
              ('Status [es]',            'StatusEs',   spanishNameStatusList))
    fields2= (('Term Concept',           'Definition'            ),
              ('Audience',               'Audience',   audiences),
              ('Dictionary',             'Dictionary', dictionaries),
              ('Definition Status [en]', 'DefStatEn',
               englishDefinitionStatusList),
              ('Definition Status [es]', 'DefStatEs',
               spanishDefinitionStatusList))

    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Glossary Term Search Form",
                                          "GlossaryTermSearch.py",
                                          fields1,
                                          buttons,
                                          'Glossary Term Name',
                                          conn)

    # The constructAdvancedSearchQuery() function needs to know the
    # document type, so we're passing this as an extra parameter
    # -------------------------------------------------------------
    page += """\
   <input type='hidden' name='TypeName' value='GlossaryTermName'>
  </FORM>\n"""

    # We need to have two forms for the Glossary search, one for the
    # Term Name and one for the Term Concept.  We're closing the
    # default form (above) and creating a new one here
    # --------------------------------------------------------------
    page += cdrcgi.addNewFormOnPage(session,
                                          "GlossaryTermSearch.py",
                                          fields2,
                                          buttons,
                                          'Glossary Term Concept',
                                          conn)

    # Again, we need to pass the document type to create the query
    # and therefore we need to pass this additional parameter
    # -------------------------------------------------------------
    page += """\
   <input type='hidden' name='TypeName' value='GlossaryTermConcept'>
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(page)

#----------------------------------------------------------------------
# Define the search fields used for the query.
#----------------------------------------------------------------------
searchFields = (cdrcgi.SearchField(nameEn,
                        ("/GlossaryTermName/TermName/TermNameString",)),
                cdrcgi.SearchField(nameEs,
                        ("/GlossaryTermName/TranslatedName/TermNameString",)),
                cdrcgi.SearchField(statusEn,
                        ("/GlossaryTermName/TermNameStatus",)),
                cdrcgi.SearchField(statusEs,
                        ("/GlossaryTermName/TranslatedName/TranslatedNameStatus",)),
                cdrcgi.SearchField(definition,
                        ("/GlossaryTermConcept/TermDefinition/DefinitionText",
                         "/GlossaryTermConcept/TranslatedTermDefinition/DefinitionText")),
                cdrcgi.SearchField(audience,
                        ("/GlossaryTermConcept/TermDefinition/Audience",
                         "/GlossaryTermConcept/TranslatedTermDefinition/Audience")),
                cdrcgi.SearchField(dictionary,
                        ("/GlossaryTermConcept/TermDefinition/Dictionary",
                         "/GlossaryTermConcept/TranslatedTermDefinition/Dictionary")),
                cdrcgi.SearchField(defStatEn,
                                   ("/GlossaryTermConcept/TermDefinition"
                                    "/DefinitionStatus",)),
                cdrcgi.SearchField(defStatEs,
                                   ("/GlossaryTermConcept"
                                    "/TranslatedTermDefinition"
                                    "/TranslatedStatus",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp,
                                                       typeName)
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
except cdrdb.Error as info:
    cdrcgi.bail('Failure retrieving GlossaryTermName documents: %s' %
                info[1][0])

#----------------------------------------------------------------------
# Create the results page. Filter argument is ignored.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage(subTitle[typeName], rows, strings,
                                        "ignore", session = session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
