#----------------------------------------------------------------------
# Prototype for CDR reporting/formatting web wrapper.
#
# BZIssue::1338
# JIRA::OCECDR-3800
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
from cdrapi import db

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"

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
# Find the table-of-contents documents for the categories of help.
#----------------------------------------------------------------------
def get_help_sections():
    try:
        cursor = db.connect(user="CdrGuest").cursor()
        cursor.execute("""\
  SELECT doc_id, value
    FROM query_term
   WHERE path = '/DocumentationToC/ToCTitle'
ORDER BY value""")
        return cursor.fetchall()
    except Exception as e:
        cdrcgi.bail("Unable to connect to CDR database")

#----------------------------------------------------------------------
# Show the menu of documentation options.
#----------------------------------------------------------------------
title    = "CDR Administration"
subtitle = "CDR Documentation"
buttons  = (SUBMENU, cdrcgi.MAINMENU)
script   = "CdrDocumentation.py"
page = cdrcgi.Page(title, subtitle=subtitle, buttons=buttons, action=script,
                   session=session, body_classes="admin-menu")
page.add("<h3>CDR Documentation Categories</h3>")
page.add("<ol>")
for doc_id, title in get_help_sections():
    url = "Help.py?id=%d" % doc_id
    link = page.B.A(title, href=url)
    list_item = page.B.LI(link)
    page.add(list_item)
page.add("</ol>")
page.send()
