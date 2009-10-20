#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for duplicate-checking interface for Summary documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.5  2002/07/15 20:19:51  bkline
# XML paths altered to match changed schemas.
#
# Revision 1.4  2002/05/03 20:31:02  bkline
# New filter added.
#
# Revision 1.3  2002/02/20 03:58:19  bkline
# Truncated long pulldown list strings at users' request.
#
# Revision 1.2  2002/02/14 19:35:24  bkline
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
boolOp    = fields and fields.getvalue("Boolean")          or "AND"
title     = fields and fields.getvalue("Title")            or None
sectType  = fields and fields.getvalue("SectionType")      or None
diagnosis = fields and fields.getvalue("Diagnosis")        or None
audience  = fields and fields.getvalue("Audience")         or None
topic     = fields and fields.getvalue("Topic")            or None
status    = fields and fields.getvalue("Status")           or None
submit    = fields and fields.getvalue("SubmitButton")     or None
help      = fields and fields.getvalue("HelpButton")       or None

if help: 
    cdrcgi.bail("Sorry, help for this interface has not yet been developed.")

#----------------------------------------------------------------------
# Generate picklist for summary section type list.
#----------------------------------------------------------------------
def sectionTypeList(conn, fName):
    try:
        cursor = conn.cursor()
        query  = """\
SELECT DISTINCT value
           FROM query_term
          WHERE path LIKE '/Summary/SummarySection%SectMetaData/SectionType'
       ORDER BY value
"""
        cursor.execute(query, timeout=120)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving summary section types from CDR: %s' 
                % info[1][0])
    html = """\
      <SELECT NAME='%s'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
""" % fName
    for row in rows:
        if row:
            html += """\
       <OPTION VALUE='%s'>%s &nbsp;</OPTION>
""" % (row[0], row[0])
    html += """\
      </SELECT>
"""
    return html
        
#----------------------------------------------------------------------
# Generate picklist for section diagnosis list.
#----------------------------------------------------------------------
def sectionDiagList(conn, fName):
    try:
        cursor = conn.cursor()
        query  = """\
   SELECT d.id, d.title
     FROM document d
    WHERE EXISTS (SELECT *
                    FROM query_term q
                   WHERE q.int_val = d.id
                     AND q.path LIKE '/Summary/SummarySection/%' +
                                     'SectMetaData/Diagnosis/@cdr:ref')
 ORDER BY d.title
"""
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving diagnosis list from CDR: %s' 
                    % info[1][0])
    html = """\
      <SELECT NAME='%s'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
""" % fName
    for row in rows:
        semi = row[1].find(';')
        if semi != -1:
            diag = row[1][:semi]
        else:
            diag = row[1]
        html += """\
       <OPTION VALUE='CDR%010d'>%s &nbsp;</OPTION>
""" % (row[0], diag)
    html += """\
      </SELECT>
"""
    return html

#----------------------------------------------------------------------
# Generate picklist for summary topic list.
#----------------------------------------------------------------------
def topicList(conn, fName):
    try:
        cursor = conn.cursor()
        query  = """\
   SELECT d.id, d.title
     FROM document d
    WHERE EXISTS (SELECT *
                    FROM query_term q
                   WHERE q.int_val = d.id
                     AND q.path LIKE '/Summary/SummaryMetaData/%Topics' +
                                     '/Term/@cdr:ref')
 ORDER BY d.title
"""
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving diagnosis list from CDR: %s' 
                % info[1][0])
    html = """\
      <SELECT NAME='%s'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
""" % fName
    for row in rows:
        semi = row[1].find(';')
        if semi != -1:
            topic = row[1][:semi]
        else:
            topic = row[1]
        html += """\
       <OPTION VALUE='CDR%010d'>%s &nbsp;</OPTION>
""" % (row[0], topic)
    html += """\
      </SELECT>
"""
    return html

#----------------------------------------------------------------------
# Generate picklist for summary audience list.
#----------------------------------------------------------------------
def audienceList(conn, fName):
    try:
        cursor = conn.cursor()
        query  = """\
SELECT DISTINCT value
           FROM query_term
          WHERE path = '/Summary/SummaryMetaData/SummaryAudience'
       ORDER BY value
"""
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
    except cdrdb.Error, info:
        cdrcgi.bail('Failure retrieving summary section types from CDR: %s' 
                % info[1][0])
    html = """\
      <SELECT NAME='%s'>
       <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
""" % fName
    for row in rows:
        if row:
            html += """\
       <OPTION VALUE='%s'>%s &nbsp;</OPTION>
""" % (row[0], row[0])
    html += """\
      </SELECT>
"""
    return html
        
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
    fields = (('Title',                        'Title'),
              ('Section Type',                 'SectionType', sectionTypeList),
              ('Diagnosis',                    'Diagnosis', sectionDiagList),
              ('Audience',                     'Audience', audienceList),
              ('Topic',                        'Topic', topicList),
              ('Publication Status',           'Status', 
                                                cdrcgi.pubStatusList))
    buttons = (('submit', 'SubmitButton', 'Search'),
               ('submit', 'HelpButton',   'Help'),
               ('reset',  'CancelButton', 'Clear'))
    page = cdrcgi.startAdvancedSearchPage(session,
                                          "Summary Search Form",
                                          "SummarySearch.py",
                                          fields,
                                          buttons,
                                          'Summary',
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
                            ("/Summary/SummaryTitle",)),
                cdrcgi.SearchField(sectType,
                            ("/Summary/SummarySection/%SectMetaData"
                             "/SectionType",)),
                cdrcgi.SearchField(diagnosis,
                            ("/Summary/SummarySection/%SectMetaData"
                             "/Diagnosis/@cdr:ref",)),
                cdrcgi.SearchField(audience,
                            ("/Summary/SummaryMetaData/SummaryAudience",)),
                cdrcgi.SearchField(topic,
                            ("/Summary/SummaryMetaData/%Topics"
                             "/Term/@cdr:ref",)),
                cdrcgi.SearchField(status, "active_status"))

#----------------------------------------------------------------------
# Construct the query.
#----------------------------------------------------------------------
(query, strings) = cdrcgi.constructAdvancedSearchQuery(searchFields, boolOp, 
                                                       "Summary")
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
    cdrcgi.bail('Failure retrieving Summary documents: %s' % 
                info[1][0])

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
html = cdrcgi.advancedSearchResultsPage("Summary", rows, strings, None,
                                        session)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
