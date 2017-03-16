#----------------------------------------------------------------------
# Prototype for CDR admin main menu.
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Get the form variables and call the logout function.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
cdrcgi.logout(session)
