#----------------------------------------------------------------------
# Duplicate-checking interface for Help (Documentation) documents.
#----------------------------------------------------------------------
import cgi, cdrcgi, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
boolOp    = fields and fields.getvalue("Boolean")         or "AND"
docType   = fields and fields.getvalue("DocType")         or None
function  = fields and fields.getvalue("Function")        or None
keyword   = fields and fields.getvalue("Keyword")         or None
infoType  = fields and fields.getvalue("InfoType")        or None
submit    = fields and fields.getvalue("SubmitButton")    or None
help      = fields and fields.getvalue("HelpButton")      or None

if help:
    cdrcgi.bail("Sorry, help for this interface has not yet been developed.")

#----------------------------------------------------------------------
# Get values for validation or for generating a picklist
#----------------------------------------------------------------------
def queryForList(fName, conn=None):
    """
    Query the database for a list of query term values to use both
    in populating an HTML selection list, and in subsequent validation of
    a selection.

    Pass:
        fname - Field name, see "fields" definition later in main.
        conn  - Optional connection object.

    Return:
        List of values.
    """
    # Dictionary of fName->query term path
    fNamePath = { 'DocType':  '/Documentation/Metadata/DocType',
                  'Function': '/Documentation/Metadata/Function',
                  'InfoType': '/Documentation/@InfoType' }

    # Specify the query
    qry = """\
        SELECT DISTINCT value
          FROM query_term
         WHERE path = '%s'
      ORDER BY value
""" % fNamePath[fName]

    # Search
    try:
        cursor = conn.cursor()
        cursor.execute(qry)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error as info:
        cdrcgi.bail('Failure retrieving %s list from CDR: %s' %
                    (fName, info[1][0]))

    # Return flat list of found values
    return [row[0] for row in rows]

#----------------------------------------------------------------------
# Generate picklist for any of our types
#----------------------------------------------------------------------
def genSelectList(conn, fName):
    """
    Generate a populated HTML selection list.

    Pass:
        conn  - Initialized connection object.
        fName - The selection field.

    Return:
        HTML fragment for execution as a callback by
        cdrcgi.startAdvancedSearchPage().
    """
    # Get the values to use in populating the list
    valueList = queryForList(fName, conn)

    html = """\
      <SELECT NAME='%s'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
""" % fName
    for value in valueList:
        html += """\
       <OPTION VALUE='%s'>%s &nbsp;</OPTION>
""" % (value, value)
    html += """\
      </SELECT>
"""
    return html

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
except cdrdb.Error as info:
    cdrcgi.bail('Failure connecting to CDR: %s' % info[1][0])

#----------------------------------------------------------------------
# Validate parameters
#----------------------------------------------------------------------
if boolOp:   cdrcgi.valParmVal(boolOp, valList=('AND', 'OR'))
if docType:  pass # LEFT OFF HERE

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Doc Type',                'DocType', genSelectList),
              ('Function',                'Function', genSelectList),
              ('Keyword',                 'Keyword'),
              ('Info Type',               'InfoType', genSelectList))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Documentation Search Form",
                                          "HelpSearch.py",
                                          fields,
                                          buttons,
                                          'Documentation',
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
searchFields = (cdrcgi.SearchField(docType,
                            ("/Documentation/Metadata/DocType",)),
                cdrcgi.SearchField(function,
                            ("/Documentation/Metadata/Function",)),
                cdrcgi.SearchField(keyword,
                            ("/Documentation/Metadata/Subject",
                             "/Documentation/Body/DocumentationTitle",)),
                cdrcgi.SearchField(infoType,
                            ("/Documentation/@InfoType",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp,
                                                       "Documentation")
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
except cdrdb.Error as info:
    cdrcgi.bail('Failure retrieving Documentation documents: %s' %
                info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Documentation", rows, strings,
                                    'name:Documentation Help Screens Filter')

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
