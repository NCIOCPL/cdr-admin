#----------------------------------------------------------------------
# $Id: Glossary.py,v 1.2 2001-03-27 21:12:36 bkline Exp $
#
# Displays CDR glossary term.
# 
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdrcgi, cdr

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Glossary"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Term Found", title)
term    = fields.getvalue('Term') or cdrcgi.bail("No Term Found", title)
session = cdr.login('rmk', '***REDACTED***') or cdrcgi.bail("Not Authorized", title)
doc     = cdr.filterDoc(session, term, 'CDR0000190704')

#----------------------------------------------------------------------
# Output the document.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
