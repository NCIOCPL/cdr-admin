#----------------------------------------------------------------------
#
# $Id: GlossaryTermSearch.py,v 1.6 2004-10-20 21:19:58 bkline Exp $
#
# Prototype for duplicate-checking interface for GlossaryTerm documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.5  2004/10/06 21:07:19  bkline
# Fixed paths for definition text.
#
# Revision 1.4  2004/09/17 17:42:06  venglisc
# Creating drop-down TermStatus list populated from the database (Bug 1335).
#
# Revision 1.3  2004/01/08 17:47:56  venglisc
# Modified GlossaryTerm Advanced Search Screen to allow searching on the
# Audience field.
#
# Revision 1.2  2002/02/28 15:51:32  bkline
# Changed title of display filter.
#
# Revision 1.1  2002/02/19 13:39:05  bkline
# Advanced search screen for Glossary Term documents.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
boolOp     = fields and fields.getvalue("Boolean")          or "AND"
name       = fields and fields.getvalue("Name")             or None
spanish    = fields and fields.getvalue("Spanish")          or None
definition = fields and fields.getvalue("Definition")       or None
status     = fields and fields.getvalue("Status")           or None
audience   = fields and fields.getvalue("Audience")         or None
submit     = fields and fields.getvalue("SubmitButton")     or None
help       = fields and fields.getvalue("HelpButton")       or None

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
    fields = (('Term Name',                    'Name'),
              ('Spanish Name',                 'Spanish'),
              ('Term Definition',              'Definition'),
              ('Audience',                     'Audience', 
                                                 cdrcgi.glossaryAudienceList),
              ('Term Status',                  'Status', 
	                                         cdrcgi.glossaryTermStatusList))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Glossary Term Search Form",
                                          "GlossaryTermSearch.py",
                                          fields,
                                          buttons,
                                          'Glossary Term',
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
searchFields = (cdrcgi.SearchField(name,
                            ("/GlossaryTerm/TermName",)),
                cdrcgi.SearchField(spanish,
                            ("/GlossaryTerm/SpanishTermName",)),
                cdrcgi.SearchField(definition,
                            ("/GlossaryTerm/TermDefinition/DefinitionText",
                             "/GlossaryTerm/SpanishTermDefinition"
                             "/DefinitionText")),
                cdrcgi.SearchField(status,
                            ("/GlossaryTerm/TermStatus",
                             "/GlossaryTerm/StatusDate")),
                cdrcgi.SearchField(audience,
                            ("/GlossaryTerm/TermDefinition/Audience",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                       "GlossaryTerm")
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
    cdrcgi.bail('Failure retrieving GlossaryTerm documents: %s' % 
                info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Glossary Term", rows, strings, 
        "name:Glossary Term Advanced Search Display", session = session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)

