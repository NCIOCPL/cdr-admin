#----------------------------------------------------------------------
# Report listing all document that link to Media documents
#
# BZIssue::4394  Modified report to adjust for new Glossary document structure.
# BZIssue::3226  Initial version of report.
# OCECDR-3619    Optimized query that was timing out; code cleanup.
#----------------------------------------------------------------------
import cdrcgi, cgi, time
from cdrapi import db
from html import escape as html_escape

#----------------------------------------------------------------------
# Set the form (and other initial) variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
docTypes = fields and fields.getvalue('DocType')  or None
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "MediaLinks.py"
title    = "CDR Administration"
section  = "Documents that Link to Media Documents"
header   = cdrcgi.header(title, title, section, script, buttons)
conn     = db.connect(user='CdrGuest')
cursor   = conn.cursor()

#----------------------------------------------------------------------
# Validate input
#----------------------------------------------------------------------
if docTypes:
    cdrcgi.valParmVal(docTypes, valList=('Summary', 'GlossaryTerm'))
if request:
    cdrcgi.valParmVal(request, valList=buttons)

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
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <H3>Documents with Media Link</H3>
   <TABLE BORDER='0'>
    <TR>
     <TD colspan='2'><B>Select Document Type:&nbsp;</B></TD>
    </TR>
""" % (cdrcgi.SESSION, session)
    for docType in ('GlossaryTerm', 'Summary'):
        form += """\
    <TR>
     <TD>&nbsp;</TD>
     <TD class="cellitem">
      <LABEL for='%s' accesskey='%s'>
       <INPUT TYPE='checkbox' NAME='DocType' value='%s'
              ID='%s' CHECKED>%s</LABEL>
     </TD>
    </TR>
""" % (docType, docType[0], docType, docType, docType)
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
html = ["""\
<!DOCTYPE html>
<html>
 <head>
  <title>Links to Media Report</title>
  <link type='text/css' rel='stylesheet' href='/stylesheets/dataform.css'>
   <style>
   *              { font-family: Arial, Helvetica, sans-serif; }
   td.idColumn    { width: 7%%;
                    text-align: center; }
   td.idHeader, td.txtHeader
                  { font-weight: bold;
                    font-size: medium; }
   td.text        { font-size: medium;
                    vertical-align: top; }
   .tableheading  { font-weight: bold;
                    font-size: large; }
   .time          { font-weight: bold;
                    font-size: medium; }
   #name          { font-size: 12pt; }
   #termLink      { text-decoration: underline;
                    color: blue; }
   </style>
 </head>
 <body>
  <center>
   <span class='tableheading'>Documents with Links to Media Report</span>
   <br>
   <span class='time'>%s</span>
  </center>
  <br>
  <table>
""" % now]

# ---------------------------------------------------------------------
# If the user picked only one summary, put it into a list to we
# can deal with the same object.
# ---------------------------------------------------------------------
if isinstance(docTypes, basestring):
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
            # Query for links from summaries
            cursor.execute("""\
SELECT DISTINCT q1.doc_id, q1.value
           FROM query_term_pub q1
           JOIN query_term_pub q2
             ON q2.doc_id = q1.doc_id
          WHERE q1.path = '/Summary/SummaryTitle'
            AND q2.path LIKE '%MediaID/@cdr:ref'
       ORDER BY q1.value""")
        rows = cursor.fetchall()
    except Exception as e:
        cdrcgi.bail('Database connection failure: %s' % e)

    # Once we have all of the records per document type start
    # returning the result in a table format
    # -------------------------------------------------------
    html.append("""\
   <tr>
    <td><span class='tableheading'>%s (%s)</span>
     <table border='1' width='100%%' cellspacing='0' cellpadding='2'>
      <tr class='head'>
       <td class='idHeader idColumn'  valign='top'>CDR ID</td>
       <td class='txtHeader' valign='top'>Doc Title</td>
      </tr>
""" % (docType, len(rows)))

    # Make is easier to read the table rows by using alternate colors
    # ---------------------------------------------------------------
    count = 0
    for row in rows:
        count += 1
        rowClass = count % 2 == 0 and "even" or "odd"

        # Here is the data returned from the SQL query
        # -----------------------------------------------------------
        html.append("""\
      <tr class='%s'>
       <td class='text' align='right'>%d</td>
       <td class='text'>%s</td>
      </tr>
""" % (rowClass, row[0], html_escape(row[1])))

    # Done with the document type.  Pick up the next one.
    # ---------------------------------------------------
    html.append("""\
     </table>
     <br>
    </td>
   </tr>
""")

# All done.
html.append("""\
  </table>
  <span id="name">%s</span>
 </body>
</html>
""" % cdrcgi.getFullUserName(session, conn))
cdrcgi.sendPage("".join(html))
