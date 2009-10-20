#----------------------------------------------------------------------
#
# $Id$
#
# Advanced search interface for CDR Media documents.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
op        = fields and fields.getvalue("op")              or "AND"
title     = fields and fields.getvalue("title")           or None
desc      = fields and fields.getvalue("desc")            or None
category  = fields and fields.getvalue("cat")             or None
diag      = fields and fields.getvalue("diag")            or None
use       = fields and fields.getvalue("use")             or None
imageType = fields and fields.getvalue("type")            or None
lang      = fields and fields.getvalue("lang")            or None
submit    = fields and fields.getvalue("SubmitButton")    or None
help      = fields and fields.getvalue("HelpButton")      or None
docType   = cdr.getDoctype('guest', 'Media')
validVals = dict(docType.vvLists)
#cdrcgi.bail(str(validVals))
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
# Generate picklist for countries.
#----------------------------------------------------------------------
def diagList(conn, fName):
    query  = """\
SELECT DISTINCT d.doc_id, d.value
           FROM query_term d
           JOIN query_term m
             ON m.int_val = d.doc_id
          WHERE m.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'
            AND d.path = '/Term/PreferredName'
       ORDER BY d.value"""
    pattern = "<option value='CDR%010d'>%s &nbsp;</option>"
    return cdrcgi.generateHtmlPicklist(conn, fName, query, pattern)

#----------------------------------------------------------------------
# Generic HTML picklist generator.
#
# Note: this only works if the query generates exactly as many
# columns for each row as are needed by the % conversion placeholders
# in the pattern argument, and in the correct order.
#
# For example invocations, see stateList and countryList above.
#----------------------------------------------------------------------
def generateHtmlPicklist(vvList, fieldName):
    html = ["""\
      <select name='%s'>
       <option value='' selected>&nbsp;</option>""" % fieldName]
    for vv in vvList:
        html.append("""\
       <option value="%s">%s &nbsp;</option>""" % (vv, vv))
    html.append("""\
      </select>
""")
    return "\n".join(html)

def catList(conn, fName):
    return generateHtmlPicklist(validVals['Category'], fName)

def typeList(conn, fName):
    return generateHtmlPicklist(validVals['ImageType'], fName)

def langList(conn, fName):
    return generateHtmlPicklist(validVals['MediaCaption@language'], fName)

def diagList(conn, fName):
    query  = """\
    SELECT DISTINCT t.doc_id, t.value
               FROM query_term t
               JOIN query_term m
                 ON m.int_val = t.doc_id
              WHERE m.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'
                AND t.path = '/Term/PreferredName'
           ORDER BY t.value"""
    pattern = u"<option value='CDR%010d'>%s &nbsp;</option>"
    return cdrcgi.generateHtmlPicklist(conn, fName, query, pattern)

def useList(conn, fName):
    query  = """\
    SELECT DISTINCT t.doc_id, t.value
               FROM query_term t
               JOIN query_term m
                 ON m.int_val = t.doc_id
              WHERE m.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'
                AND t.path = '/Term/PreferredName'
           ORDER BY t.value"""
    pattern = u"<option value='CDR%010d'>%s &nbsp;</option>"
    return cdrcgi.generateHtmlPicklist(conn, fName, query, pattern)
    values = ('Users', 'Still', 'Figuring', 'This', 'Out')
    return generateHtmlPicklist(values, fName)

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Title',                   'title'),
              ('Content Description',     'desc'),
              ('Category',                'cat',  catList),
              ('Diagnosis',               'diag', diagList),
              ('Proposed Use',            'use'),  #useList),
              ('Image Type',              'type', typeList),
              ('Language',                'lang', langList))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Media Search Form",
                                          "MediaSearch.py",
                                          fields,
                                          buttons,
                                          'Media',
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
                            ("/Media/MediaTitle",)),
                cdrcgi.SearchField(desc,
                            ("/Media/MediaContent/ContentDescriptions"
                             "/ContentDescription",)),
                cdrcgi.SearchField(category,
                            ("/Media/MediaContent/Categories/Category",)),
                cdrcgi.SearchField(diag,
                            ("/Media/MediaContent/Diagnoses"
                             "/Diagnosis/@cdr:ref",)),
                cdrcgi.SearchField(use,
                            ("/Media/ProposedUse/Summary/@cdr:ref[int_val]",
                             "/Media/ProposedUse/Glossary/@cdr:ref[int_val]")),
                cdrcgi.SearchField(imageType,
                            ("/Media/PhysicalMedia/ImageData/ImageType",)),
                cdrcgi.SearchField(lang,
                            ("/Media/MediaContent/Captions"
                             "/MediaCaption/@language",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, op, 
                                                       "Media")
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
    cdrcgi.bail('Failure retrieving Media documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
filt = "set:QC+Media+Set"
html = cdrcgi.advancedSearchResultsPage("Media", rows, strings, filt, session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
