#----------------------------------------------------------------------
#
# $Id: Logout.py,v 1.1 2001-06-13 22:16:32 bkline Exp $
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
