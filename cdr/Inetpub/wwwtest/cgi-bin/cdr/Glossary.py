#----------------------------------------------------------------------
# $Id: Glossary.py,v 1.1 2001-03-27 21:11:14 bkline Exp $
#
# Displays CDR glossary term (stub version).
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
