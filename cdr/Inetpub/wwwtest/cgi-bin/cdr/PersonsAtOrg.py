#----------------------------------------------------------------------
#
# $Id: PersonsAtOrg.py,v 1.1 2002-03-21 20:00:28 bkline Exp $
#
# Identifieds all person documents which are linked to a specified
# organization document.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import cdr, cdrdb, cdrcgi, cgi, re, string, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
name    = fields and fields.getvalue('Name') or None
id      = fields and fields.getvalue('Id')   or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "PersonsAtOrg.py"
title   = "CDR Administration"
section = "Persons Linked to Organization Report"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())

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
if not name and not id:
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD ALIGN='right'><B>Document ID:&nbsp;</B></TD>
     <TD><INPUT NAME='Id'></TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>Organization Name:&nbsp;</B></TD>
     <TD><INPUT NAME='Name'></TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Generate HTML for persons at a specific location.
#----------------------------------------------------------------------
def personsAtLocation(cursor, id, fragId):
    path = "/Person/PersonLocations/OtherPracticeLocation/"\
           "OrganizationLocation/@cdr:ref"
    fragLink = "CDR%010d#%s" % (id, fragId)
    parms = [["fragLink", fragLink]]
    personPos = 0
    #cdrcgi.bail("value should be CDR%010d#%s" % (id, fragId))
    try:
        cursor.execute("""\
            SELECT DISTINCT query_term.doc_id,
                            document.title
                       FROM query_term
                       JOIN document
                         ON document.id = query_term.doc_id
                      WHERE path = '%s'
                        AND value = '%s'
                   ORDER BY document.title""" % (path, fragLink))
        row = cursor.fetchone()
        if not row:
            return "None"
        table = """\
   <table border='0' cellspacing='0' cellpadding='0'>
"""
        while row:
            personPos += 1
            resp = cdr.filterDoc(session, ['name:Person at Org Location'], 
                                 row[0], parm = parms)
            if type(resp) in (type(''), type(u'')):
                cdrcgi.bail(resp)
            table += """
    <tr>
     <td valign='top' align='right'>
      <b>
       <font size='3'>%d.&nbsp;&nbsp;</font>
      </b>
     </td>
     <td>%s</td>
    </tr>
    <tr>
     <td colspan="2">&nbsp;</td>
    </tr>
""" % (personPos, cdrcgi.decode(resp[0]))
            row = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail('Failure collecting person document IDs: %s' % info[1][0])
    return table + """\
  </table>
"""

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the document ID.
#----------------------------------------------------------------------
if id:
    digits = re.sub('[^\d]', '', id)
    id     = string.atoi(digits)
else:
    pathPattern = '/Organization/OrganizationNameInformation/%Name/Name'
    try:
        cursor.execute("""\
                SELECT DISTINCT doc_id
                           FROM query_term
                          WHERE path LIKE '%s'
                            AND value = ?""" % pathPattern, name)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure looking up glossary term '%s': %s" % (name,
                                                                   info[1][0]))
    if len(rows) > 1: cdrcgi.bail("Ambiguous organization name '%s'" % name)
    if len(rows) < 1: cdrcgi.bail("Unknown organization '%s'" % name)
    id = rows[0][0]

#----------------------------------------------------------------------
# Get all the names for the orgnization.
#----------------------------------------------------------------------
try:
    path = '/Organization/OrganizationNameInformation/OfficialName/Name'
    cursor.execute("""\
            SELECT DISTINCT value
                       FROM query_term
                      WHERE path = '%s'
                        AND doc_id = ?""" % path, id)
    rows = cursor.fetchall()
    if len(rows) > 1: cdrcgi.bail("Multiple 'official' names for org %d" % id)
    if len(rows) < 1: cdrcgi.bail("Can't find official name for org %d" % id)
    officialName = rows[0][0]

    path = '/Organization/OrganizationNameInformation/ShortName/Name'
    cursor.execute("""\
            SELECT DISTINCT value
                       FROM query_term
                      WHERE path = '%s'
                        AND doc_id = ?""" % path, id)
    shortNames = []
    for row in cursor.fetchall():
        shortNames.append(row[0])

    path = '/Organization/OrganizationNameInformation/AlternateName/Name'
    cursor.execute("""\
            SELECT DISTINCT value
                       FROM query_term
                      WHERE path = '%s'
                        AND doc_id = ?""" % path, id)
    alternateNames = []
    for row in cursor.fetchall():
        alternateNames.append(row[0])
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching organization names: %s' % info[1][0])

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
ellipsis = '.' * 30
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR%010d - %s - %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>Persons Linked to Organization Report</font>
   </b>
   <br />
   <br />
  </center>
  <b>
   <font size='4'>Name</font>
  </b>
  <br />
  <table border='0'>
   <tr>
    <td valign='top' nowrap='1'>
     <b>
      <font size='3'>Official Name</font>
     </b>
    </td>
    <td valign='top' nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (id, officialName, time.strftime("%B %d, %Y", now), ellipsis, 
       officialName)

for shortName in shortNames:
    html += """\
   <tr>
    <td valign='top' nowrap='1'>
     <b>
      <font size='3'>Short Name</font>
     </b>
    </td>
    <td valign='top' nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (ellipsis, shortName)

for alternateName in alternateNames:
    html += """\
   <tr>
    <td valign='top' nowrap='1'>
     <b>
      <font size='3'>Alternate Name</font>
     </b>
    </td>
    <td valign='top' nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (ellipsis, alternateName)

html += """\
  </table>
  <br />
  <br />
  <b>
   <font size='4'>Locations</font>
  </b>
  <br />
  <table border='0'>
"""

resp = cdr.filterDoc(session, ['name:Org Locations for Linking Persons'], id)
if type(resp) in (type(''), type(u'')):
    cdrcgi.bail(resp)
expr1 = re.compile(u"<Location>(.*?)</Location>", re.DOTALL)
expr2 = re.compile(u"(<table.*</table>)", re.DOTALL)
expr3 = re.compile(u"<FragmentId>(.*)</FragmentId>")
locations = expr1.findall(cdrcgi.decode(resp[0]))
locPos = 0
for location in locations:
    #cdrcgi.bail(location)
    locPos += 1
    table  = expr2.search(location)
    fragId = expr3.search(location)
    if not table: cdrcgi.bail("failure extracting address information")
    html += """\
   <tr>
    <td colspan='2'>&nbsp;</td>
   </tr>
   <tr>
    <td colspan='2'>
     <b>
      <font size='3'>Location</font>
     </b>
    </td>
   </tr>
   <tr>
    <td colspan='2'>&nbsp;</td>
   </tr>
   <tr>
    <td valign='top'>
     <font size='3'>%s.&nbsp;&nbsp;&nbsp;</font>
    </td>
    <td>%s</td>
   </tr>
   <tr>
    <td colspan='2'>&nbsp;</td>
   </tr>
   <tr>
    <td>&nbsp;</td>
    <td>
     <b>
      <font size='3'>Persons at Location</font>
     </b>
    </td>
   </tr>
   <tr>
    <td colspan='2'>&nbsp;</td>
   </tr>
   <tr>
    <td>&nbsp;</td>
    <td>%s</td>
   </tr>
""" % (cdrcgi.int_to_roman(locPos), cdrcgi.decode(table.group(1)),
       personsAtLocation(cursor, id, fragId.group(1)))

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
    
html += resp[0]
row = cursor.fetchone()

#----------------------------------------------------------------------
# Get the list of documents which link to this glossary term.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT DISTINCT query_term.doc_id,
                            document.title,
                            doc_type.name
                       FROM query_term
                       JOIN document
                         ON document.id = query_term.doc_id
                       JOIN doc_type
                         ON doc_type.id = document.doc_type
                      WHERE query_term.value = 'CDR%010d'
                   ORDER BY doc_type.name,
                            query_term.doc_id""" % id)
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching list of linking documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Display the report rows.
#----------------------------------------------------------------------
filterParms = [['linkTarget', 'CDR%010d' % id]]
try:
    row = cursor.fetchone()
    currentDoctype = None
    while row:
        (docId, docTitle, docType) = row
        if docType != currentDoctype:
            if currentDoctype:
                html += """\
  </table>
"""
    """
            currentDoctype = docType
            html += "x""\
  <br />
  <br />
  <b>
   <font size='3'>%s</font>
  </b>
  <br />
  <table border='1' cellspacing='0' cellpadding='1' width='100%%'>
   <tr>
    <td>
     <b>
      <font size='3'>DocID</font>
     </b>
    </td>
    <td>
     <b>
      <font size='3'>DocTitle</font>
     </b>
    </td>
    <td>
     <b>
      <font size='3'>ElementName</font>
     </b>
    </td>
    <td>
     <b>
      <font size='3'>FragmentID</font>
     </b>
    </td>
   </tr>
"x"" % currentDoctype

        resp = cdr.filterDoc(session, ['name:Glossary Link Report Filter'],
                             docId, parm = filterParms)
        #cdrcgi.bail(resp[0])
        if type(resp) in (type(''), type(u'')):
            cdrcgi.bail(resp)
        html += resp[0]
        row = cursor.fetchone()

except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching linking document: %s' % info[1][0])

if currentDoctype:
    html += "x""\
  </table>
"x""
cdrcgi.sendPage(html + "x""\
 </body>
</html>
"x"")
"""
except: pass
