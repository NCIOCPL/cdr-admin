#----------------------------------------------------------------------
#
# $Id: MediaLinks.py,v 1.2 2007-05-18 21:34:55 venglisc Exp $
#
# Report listing all document that link to Media documents
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2007/05/18 21:19:45  venglisc
# Initial version of MediaLinks report listing Summaries and/or Glossaries
# that are linking to a Media document. (Bug 3226)
#
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

def getMediaDocTypes():
    return ([['GlossaryTerm'], ['Summary']])
    try:
        conn   = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT DISTINCT SUBSTRING(path, 2, CHARINDEX('/', path, 2) - 2)
              FROM query_term_pub
             WHERE path like '%MediaID/@cdr:ref'
               AND SUBSTRING(path, 2, 5) != 'Media'
             ORDER BY 1""")
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database connection failure: %s' % info[1][0])

    return (rows)


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
   TD.header      { font-weight: bold;
                    font-size: medium;
                    align: center; }
   TD.text        { font-size: medium; }
   .tableheading  { font-weight: bold;
                    font-size: large; }
   .time          { font-weight: bold;
                    font-size: medium; }
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
titlePath = {'GlossaryTerm':'/GlossaryTerm/TermName',
             'Summary'     :'/Summary/SummaryTitle'}

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
        conn   = cdrdb.connect()
        cursor = conn.cursor()
        dtQual = docType and ("doc_type = '%s'" % docType) or ""
        cursor.execute("""\
           SELECT doc_id, value as GlossaryTerm
             FROM  query_term_pub
            WHERE doc_id IN 
                  (
                  SELECT DISTINCT doc_id
                    FROM query_term_pub
                   WHERE path LIKE '%%MediaID/@cdr:ref'
                  )
              AND path = '%s'
            ORDER BY value""" % titlePath[docType])
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
       <TD  class='header' valign='top'>CDR ID</TD>
       <TD class='header' valign='top'>DocTitle</TD>
      </TR>
""" % (docType, len(rows))

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
        # List the rows
        # --------------------------------------------
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
  <BR>
  %s
 </BODY>
</HTML>
""" % cdrcgi.getFullUserName(session, conn))
