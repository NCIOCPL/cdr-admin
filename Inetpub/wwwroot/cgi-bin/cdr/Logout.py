#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for CDR admin main menu.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Get the form variables and call the logout function.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
cdrcgi.logout(session)
