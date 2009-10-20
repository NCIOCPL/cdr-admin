#----------------------------------------------------------------------
#
# $Id$
#
# Identifieds all person documents which are linked to a specified
# organization document.
#
# $Log: not supported by cvs2svn $
# Revision 1.5  2004/02/24 12:44:59  bkline
# Added person document IDs at Sheri's request (request #1107).
#
# Revision 1.4  2003/08/25 20:29:55  bkline
# Eliminated dross left over from clone of another report.
#
# Revision 1.3  2003/03/10 21:05:30  bkline
# Added support for ambiguous organization name pattern.
#
# Revision 1.2  2003/02/24 21:16:49  bkline
# Added support for wildcards in org name.
#
# Revision 1.1  2002/03/21 20:00:28  bkline
# Report for persons practicing at a designated organizaiton.
#
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
section = "Persons Practicing at Organization Report"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())

#----------------------------------------------------------------------
# Put up a list of possible choices if the name is not unique.
#----------------------------------------------------------------------
def showChoices(pathPattern, name):
    global buttons
    try:
        cursor.execute("""\
                SELECT DISTINCT doc_id, value
                           FROM query_term
                          WHERE path LIKE '%s'
                            AND value LIKE ?
                       ORDER BY value""" % pathPattern, name)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure looking up organization name '%s': %s" % (name,
                                                                   info[1][0]))
    buttons = buttons[1:]
    header = cdrcgi.header(title, title, section, script, buttons)
    form = """\
   <H3>Select Organization for Report</H3>
   <UL>
"""
    for row in rows:
        form += """\
    <LI>
     <A HREF="%s?%s=%s&Id=%d">%s (CDR%010d)</A>
    </LI>
""" % (script, cdrcgi.SESSION, session, row[0], cgi.escape(row[1], 1), row[0])
    cdrcgi.sendPage(header + form + """\
   </UL>
  </FORM>
 </BODY>
</HTML>
""")
    
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
    path1 = "/Person/PersonLocations/OtherPracticeLocation/"\
           "OrganizationLocation/@cdr:ref"
    path2 = "/Person/PersonLocations/OtherPracticeLocation/@cdr:id"
    fragLink = "CDR%010d#%s" % (id, fragId)
    parms = [["fragLink", fragLink]]
    personPos = 0
    #cdrcgi.bail("value should be CDR%010d#%s" % (id, fragId))
    try:
        cursor.execute("""\
	    SELECT q1.doc_id, d.title, q2.value
	      FROM query_term q1
	      JOIN document d
	        ON d.id = q1.doc_id
	      JOIN query_term q2
	        ON d.id = q2.doc_id
	     WHERE q1.path = '%s'
	       AND q2.path = '%s'
	       AND q1.value = '%s'
	       AND LEFT(q1.node_loc, 8) = q2.node_loc
	     ORDER BY d.title""" % (path1, path2, fragLink))
        row = cursor.fetchone()
        if not row:
            return "None"
        personsList = """\
        <ol>
"""
        while row:
            personPos += 1
            locparms = [["location", row[2]]]
            resp = cdr.filterDoc(session, ['set:Denormalization Person Set',
	                                 'name:Copy XML for Person 2',
			                'name:Person at Org - Person Location'],
	                                  row[0], parm = locparms) 
            if type(resp) in (type(''), type(u'')):
                cdrcgi.bail(resp)
            personsList += """
    <li>%s</li>
""" % (cdrcgi.decode(resp[0].replace("@@DOCID@@", "(%d)" % row[0])))
            row = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail('Failure collecting person document IDs: %s' % info[1][0])
    return personsList + """\
  </ol>
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
                            AND value LIKE ?""" % pathPattern, name)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure looking up organization name '%s': %s" % (name,
                                                                   info[1][0]))
    if len(rows) > 1: showChoices(pathPattern, name)
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
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR%d: %s - %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>Persons Practicing at Organization<br/>Report</font>
    <br/>%s
   </b>
   <br />
   <br />
  </center>
  <b>
   <font size='4'>CDR%d</font>
  </b>
  <br/><br/>
  <b>
   <font size='4'>Name</font>
  </b>
  <br />
  <table border='0' width="100%%" cellspacing='0' cellpadding='0'>
   <tr>
    <td valign='top' nowrap='1'>
     <b>Official Name</b>
    </td>
    <td>
     %s
    </td>
   </tr>
""" % (id, officialName, time.strftime("%B %d, %Y", now), 
       time.strftime("%B %d, %Y", now), id, officialName)

for shortName in shortNames:
    html += """\
   <tr>
    <td valign='top' nowrap='1'>
     <b>Short Name</b>
    </td>
    <td>
     %s
    </td>
   </tr>
""" % (shortName)

for alternateName in alternateNames:
    html += """\
   <tr>
    <td valign='top' nowrap='1'>
     <b>Alternate Name</b>
    </td>
    <td>
     %s
    </td>
   </tr>
""" % (alternateName)

html += """\
  </table>
  <br />
"""

resp = cdr.filterDoc(session, ['set:Denormalization Organization Set', 
                               'name:Person at Org - Org Location'], id)
if type(resp) in (type(''), type(u'')):
    cdrcgi.bail(resp)
expr1 = re.compile(u"<Location>(.*?)</Location>", re.DOTALL)
expr2 = re.compile(u"(<table.*</table>)", re.DOTALL)
expr3 = re.compile(u"<FragmentId>(.*)</FragmentId>")
locations = expr1.findall(cdrcgi.decode(resp[0]))
locPos = 0
for location in locations:
    locPos += 1
    table  = expr2.search(location)
    fragId = expr3.search(location)
    if not table: cdrcgi.bail("Failure extracting address information")
    html += """\
     <b>
      <font size='4'>%s. Location</font>
     </b>
     %s
     <br/>
     <b>Persons at Location</b>
     %s
""" % (cdrcgi.int_to_roman(locPos), cdrcgi.decode(table.group(1)),
       personsAtLocation(cursor, id, fragId.group(1)))

cdrcgi.sendPage(html + """\
 </body>
</html>
""")
