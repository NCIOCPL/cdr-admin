#----------------------------------------------------------------------
# Advanced search interface for CDR DrugInformationSummary documents.
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
op        = fields.getvalue("op")              or "AND"
title     = fields.getvalue("title")           or None
fdaAppr   = fields.getvalue("fdaAppr")         or None
apprInd   = fields.getvalue("apprInd")         or None
drugRef   = fields.getvalue("drugRef")         or None
lastMod   = fields.getvalue("lastMod")         or None
submit    = fields.getvalue("SubmitButton")    or None
help      = fields.getvalue("HelpButton")      or None
typeName  = "DrugInformationSummary"
docType   = cdr.getDoctype('guest', typeName)
script    = "DISSearch.py"
validVals = dict(docType.vvLists)

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
# Create an HTML picklist from a valid values list.
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

def fdaApprovedList(conn, fName):
    return generateHtmlPicklist(validVals['FDAApproved'], fName)

def drugRefList(conn, fName):
    return generateHtmlPicklist(validVals['DrugReferenceType'], fName)

def apprIndList(conn, fName):
    query  = """\
    SELECT DISTINCT t.doc_id, t.value
               FROM query_term t
               JOIN query_term a
                 ON a.int_val = t.doc_id
              WHERE a.path = '/DrugInformationSummary/DrugInfoMetaData'
                           + '/ApprovedIndication/@cdr:ref'
                AND t.path = '/Term/PreferredName'
           ORDER BY t.value"""
    pattern = u"<option value='CDR%010d'>%s &nbsp;</option>"
    return cdrcgi.generateHtmlPicklist(conn, fName, query, pattern)

#----------------------------------------------------------------------
# Display the search form.
#----------------------------------------------------------------------
if not submit:
    fields = (('Title',                   'title'),
              ('FDA Approved',            'fdaAppr', fdaApprovedList),
              ('Date Last Modified',      'lastMod'),
              ('Approved Indication',     'apprInd', apprIndList),
              ('Drug Reference',          'drugRef', drugRefList))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    pageTitle = "Drug Information Summary Search Form"
    page = cdrcgi.startAdvancedSearchPage(session, pageTitle, script, fields,
                                          buttons, typeName, conn)
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
                            ("/DrugInformationSummary/Title",)),
                cdrcgi.SearchField(fdaAppr,
                            ("/DrugInformationSummary/DrugInfoMetaData"
                             "/FDAApproved",)),
                cdrcgi.SearchField(apprInd,
                            ("/DrugInformationSummary/DrugInfoMetaData"
                             "/ApprovedIndication/@cdr:ref",)),
                cdrcgi.SearchField(drugRef,
                            ("/DrugInformationSummary/DrugReference"
                             "/DrugReferenceType",)),
                cdrcgi.SearchField(lastMod,
                            ("/DrugInformationSummary/DateLastModified",)))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, op, 
                                                       "DrugInformationSummary")
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
    cdrcgi.bail('Failure retrieving Drug documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
filt = "set:QC+DrugInfoSummary+Set"
html = cdrcgi.advancedSearchResultsPage(typeName, rows, strings, filt, session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
