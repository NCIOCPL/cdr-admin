#----------------------------------------------------------------------
#
# $Id$
#
# Report listing all document that link to Media documents
#
# BZIssue::4394  Modified report to adjust for new Glossary document structure.
# BZIssue::3226  Initial version of report.
# OCECDR-3619    Optimized query that was timing out.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
docTypes = fields and fields.getvalue('DocType')  or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "MediaLinks.py"
title   = "CDR Administration"
section = "Documents that Link to Media Documents"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()

# ---------------------------------------------------------------------
# Select all document types that contain a MediaLink element
# Note: The SQL query is very slow (due to the like condition) and 
#       needs to be tweaked.  It takes > 15 sec to return.  Until this
#       has been improved we have to hard-code the document types.
#
# Note: Tweaking of the SQL has been done, and we get the results
#       immediately now.  However, since the comment above was written,
#       the requirements for the report have moved on, and the
#       current implementation is dependent on a hard-code list
#       of document types anyway.  I've left in the optimized SQL
#       to illustrate how to work around the limitations of SQL Server's
#       query optimizer, but that code is never reached.
# ---------------------------------------------------------------------
def getMediaDocTypes():
    return [['GlossaryTerm'], ['Summary']]
    cursor.execute("CREATE TABLE #mediadocs (id INT)")
    cursor.execute("CREATE TABLE #medialinks (i INT, p VARCHAR(255))")
    cursor.execute("""\
   INSERT INTO #mediadocs
        SELECT d.id
          FROM document d
          JOIN doc_type t
            ON t.id = d.doc_type
         WHERE t.name = 'Media'""")
    cursor.execute("""\
   INSERT INTO #medialinks
        SELECT q.doc_id, q.path
          FROM query_term q
          JOIN #mediadocs m
            ON m.id = q.int_val
         WHERE q.value LIKE 'CDR00%'""")
    cursor.execute("""\
        SELECT DISTINCT t.name
                   FROM doc_type t
                   JOIN document d
                     ON t.id = d.doc_type
                   JOIN #medialinks m
                     ON m.i = d.id
                  WHERE m.p LIKE '%/MediaLink/MediaID/@cdr:ref'""")
    return cursor.fetchall()

# ---------------------------------------------------------------------
# This function accepts a GlossaryTermConcept ID and returns all 
# GlossaryTermNames related to this concept as follows
#    [CDR-ID of TermName, English Term Name, Spanish Term Name].
# ---------------------------------------------------------------------
def getTermName(id):
    try:
        cursor.execute("""\
            SELECT q.doc_id, e.value, s.value
              FROM query_term q
              JOIN query_term e
                ON e.doc_id = q.doc_id
               AND e.path = '/GlossaryTermName/TermName/TermNameString'
   LEFT OUTER JOIN query_term s
                ON s.doc_id = q.doc_id
               AND s.path = '/GlossaryTermName/TranslatedName/TermNameString'
             WHERE q.int_val = ?
               AND q.path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'
             ORDER BY e.value""", id)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database connection failure in getTermName: %s' % 
                                                                 info[1][0])
    return rows


# ---------------------------------------------------------------------
# Construct the cell content for the GlossaryTermConcept table to 
# display all GlossaryTermNames of a group and the GTN CDR-ID.
# ---------------------------------------------------------------------
def getTermString(id):
    termNames = getTermName(id)
    enTermString = esTermString = ''

    for cdrId, enName, esName in termNames:
        enTermString += "%s (<a href='/cgi-bin/cdr/Filter.py?" % enName
        enTermString += "DocId=CDR%s&amp;Filter=set:QC+" % cdrId
        enTermString += "GlossaryTermName+with+Concept+set'>"
        enTermString += "<span id='termLink'>CDR%s</span></a>)<br/>" % cdrId
        enTermString += "\n       "
        esTermString +=  "%s<br/>\n" % (esName and esName 
                                               or '*** No Spanish Name ***')

    return (enTermString, esTermString)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not docTypes:
    docTypes = getMediaDocTypes()
    if type(docTypes) in [type(""), type(u"")]:
        cdrcgi.bail(docTypes)
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <H3>Documents with Media Link</H3>
   <TABLE BORDER='0'>
    <TR>
     <TD colspan='2'><B>Select Document Type:&nbsp;</B></TD>
    </TR>
""" % (cdrcgi.SESSION, session)
    for docType in docTypes:
        form += """\
    <TR>
     <TD>&nbsp;</TD>
     <TD class="cellitem">
      <LABEL for='%s' accesskey='%s'>
       <INPUT TYPE='checkbox' NAME='DocType' value='%s' 
              ID='%s' CHECKED>%s</LABEL>
     </TD>
    </TR>
""" % (docType[0], docType[0][0], docType[0], docType[0], docType[0])
    form += """\
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" 
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Start the result page.
#----------------------------------------------------------------------
now = time.strftime("%Y-%m-%d %H:%M:%S")
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>Links to Media Report</TITLE>
  <BASEFONT face='Arial, Helvetica, sans-serif'>
  <LINK type='text/css' rel='stylesheet' href='/stylesheets/dataform.css'>
   <STYLE type='text/css'>
   TD.idColumn    { width: 7%%; 
                    text-align: center; }
   TD.idHeader, TD.txtHeader
                  { font-weight: bold;
                    font-size: medium; }
   TD.text        { font-size: medium; 
                    vertical-align: top; }
   .tableheading  { font-weight: bold;
                    font-size: large; }
   .time          { font-weight: bold;
                    font-size: medium; }
   #name          { font-size: 12pt; }
   #termLink      { text-decoration: underline;
                    color: blue; }
   </STYLE>
 </HEAD>
 <BODY>
  <CENTER>
   <SPAN class='tableheading'>Documents with Links to Media Report</SPAN>
   <BR>
   <SPAN class='time'>%s</SPAN>
  </CENTER>
  <P>
  <TABLE>
""" % now
   
#----------------------------------------------------------------------
# Create a dictionary listing the path to use for the title information
#----------------------------------------------------------------------
titlePath = {'GlossaryTermXXX':
               '/GlossaryTerm/TermName',
             'GlossaryTerm': 
               '/GlossaryTermConcept/TermDefinition/DefinitionText',
             'Summary'     :
               '/Summary/SummaryTitle'}

innerSQL  = {"GlossaryTerm":"""SELECT DISTINCT doc_id
                               FROM query_term_pub
                              WHERE int_val IN 
                                    (
                                     SELECT doc_id
                                       FROM query_term_pub
                                      WHERE path LIKE '%%MediaID/@cdr:ref'
                                    )""",
             "Summary"     :"""SELECT DISTINCT doc_id
                               FROM query_term_pub
                              WHERE path LIKE '%%MediaID/@cdr:ref'"""}

sortSQL   = {"GlossaryTerm":       "ORDER BY value",
             "GlossaryTermConcept":"ORDER BY doc_id",
             "Summary":            "ORDER BY value"}

# ---------------------------------------------------------------------
# If the user picked only one summary, put it into a list to we
# can deal with the same object.
# ---------------------------------------------------------------------
if type(docTypes) in (type(""), type(u"")):
    docTypes = [docTypes]

# Run the database query individually for each document type
# ----------------------------------------------------------
for docType in docTypes:
    try:
        # Optimize very slow query for links from glossary terms.
        # This version takes about 3 seconds (compared to 6-7 minutes for
        # the nested queries).
        if docType == "GlossaryTerm":
            cursor.execute("""\
SELECT DISTINCT q1.doc_id, q1.value
           FROM query_term_pub q1
           JOIN query_term_pub q2
             ON q1.doc_id = q2.doc_id
           JOIN query_term_pub q3
             ON q2.int_val = q3.doc_id
          WHERE q1.path = '/GlossaryTermConcept/TermDefinition/DefinitionText'
            AND q3.path LIKE '%MediaID/@cdr:ref'
       ORDER BY q1.value""")
        else:
            cursor.execute("""\
           SELECT doc_id, value
             FROM  query_term_pub
            WHERE doc_id IN 
                  ( %s )
                  AND path = '%s'
                  %s""" % (innerSQL[docType], titlePath[docType],
                                 sortSQL[docType]), timeout = 300)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database connection failure: %s' % info[1][0])

    # Once we have all of the records per document type start 
    # returning the result in a table format
    # -------------------------------------------------------
    curDocType = docType
    html += """\
   <TR>
    <TD><SPAN class='tableheading'>%s (%s)</SPAN>
     <TABLE border='1' width='100%%' cellspacing='0' cellpadding='2'>
      <TR class='head'>
""" % (docType, len(rows))
    
    if docType == 'GlossaryTermConcept':
        html += """\
       <TD class='idHeader idColumn'  valign='top'>CDR ID</TD>
       <TD class='txtHeader' valign='top'>Term Name</TD>
       <TD class='txtHeader' valign='top'>Spanish Term Name</TD>
      </TR>
"""
    else:
        html += """\
       <TD class='idHeader idColumn'  valign='top'>CDR ID</TD>
       <TD class='txtHeader' valign='top'>Doc Title</TD>
      </TR>
"""

    # Make is easier to read the table rows by using alternate colors
    # ---------------------------------------------------------------
    count = 0
    for row in rows:
        count += 1
        if count % 2 == 0:
            html += """\
      <TR class='even'>
"""
        else:
            html += """\
      <TR class='odd'>
"""
        # Here is the data returned from the SQL query
        # For the GlossaryTermConcept we need to display all of the 
        # GlossaryTermNames of a Concept group along with the 
        # TermName CDR-ID.
        # -----------------------------------------------------------
        if docType == 'GlossaryTermConcept':
            enName, esName = getTermString(row[0])
            html += """\
       <TD class='text' align='right'>%d</TD>
       <TD class='text'>%s</TD>
       <TD class='text'>%s</TD>
      </TR>
""" % (row[0], enName, esName)
        else:
            html += """\
       <TD class='text' align='right'>%d</TD>
       <TD class='text'>%s</TD>
      </TR>
""" % (row[0], row[1])

    # Done with the document type.  Pick up the next one.
    # ---------------------------------------------------
    if curDocType:
        html += """\
     </TABLE>
     <BR>
    </TD>
   </TR>
"""

cdrcgi.sendPage(html + """\
  </TABLE>
  <span id="name">%s</span>
 </BODY>
</HTML>
""" % cdrcgi.getFullUserName(session, conn))
