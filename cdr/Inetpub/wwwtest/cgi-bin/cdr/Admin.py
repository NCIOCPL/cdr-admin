#----------------------------------------------------------------------
#
# $Id: Admin.py,v 1.1 2001-06-13 22:16:32 bkline Exp $
#
# Prototype for CDR admin main menu.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)

#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown user id or password.')

#----------------------------------------------------------------------
# Put up the main menu.
#----------------------------------------------------------------------
cdrcgi.mainMenu(session)
