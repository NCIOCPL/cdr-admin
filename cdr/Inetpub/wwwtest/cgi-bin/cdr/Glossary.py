#----------------------------------------------------------------------
# $Id: Glossary.py,v 1.3 2001-04-08 22:57:41 bkline Exp $
#
# Displays CDR glossary term.
# 
# $Log: not supported by cvs2svn $
# Revision 1.2  2001/03/27 21:12:36  bkline
# Fixed comment (no longer stub version); added RCS Log keyword.
#
#----------------------------------------------------------------------
import cgi, cdrcgi, cdr

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Glossary"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Term Found", title)
term    = fields.getvalue('Term') or cdrcgi.bail("No Term Found", title)
session = cdr.login('rmk', '***REDACTED***') or cdrcgi.bail("Not Authorized", title)
doc     = cdr.filterDoc(session, 'CDR0000190704', docId = term)

#----------------------------------------------------------------------
# Output the document.
#----------------------------------------------------------------------
cdrcgi.sendPage(cdrcgi.decode(doc))
