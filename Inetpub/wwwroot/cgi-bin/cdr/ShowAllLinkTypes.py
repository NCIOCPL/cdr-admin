#----------------------------------------------------------------------
# Displays a table containing information about all link types.
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
SUBMENU = "Link Menu"

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
    cdrcgi.navigateTo("EditLinkControl.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Retrieve and display the user information.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Show All Link Types"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
#script  = "DumpParams.pl"
script  = "ShowAllLinkTypes.py"
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Retrieve the information directly from the database.
#----------------------------------------------------------------------
try:
    conn = db.connect(user='CdrGuest')
except Exception as e:
    cdrcgi.bail('Database failure: %s' % e)
cursor = conn.cursor()
query  = """\
SELECT DISTINCT link_type.name,
                source.name,
                link_xml.element,
                target.name,
                link_type.chk_type
           FROM link_xml,
                link_type,
                link_target,
                doc_type source,
                doc_type target
          WHERE link_xml.link_id = link_type.id
            AND link_target.source_link_type = link_type.id
            AND link_xml.doc_type = source.id
            AND link_target.target_doc_type = target.id
"""
try:
    cursor.execute(query)
except Exception as e:
    cdrcgi.bail('Database query failure: %s' % e)

#----------------------------------------------------------------------
# Display the information in a table.
#----------------------------------------------------------------------
form = """\
<H2>All Available Linking Element Combinations</H2>
<TABLE BORDER='2'>
 <TR>
  <TD><B>Link Type</TD>
  <TD><B>Source Doctype</TD>
  <TD><B>Linking Element</TD>
  <TD><B>Target Doctype</TD>
  <TD><B>Pub/Ver/Cwd</TD>
 </TR>
"""
try:
    for rec in cursor.fetchall():
        form += " <TR>\n"
        for col in rec:
            form += "  <TD>%s</TD>\n" % col
except Exception as e:
    cdrcgi.bail('Failure fetching query results: %s' % e)

form += "</TABLE>\n"

#----------------------------------------------------------------------
# Add the session key and send back the form.
#----------------------------------------------------------------------
form += """\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
