#----------------------------------------------------------------------
#
# $Id: NewPhysicianInitMailerReqForm.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Request form for initial physician mailers.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
title   = "CDR Administration"
section = "New Physician Initial Mailer"
buttons = []
header  = cdrcgi.header(title, title, section, "", buttons)

#----------------------------------------------------------------------
# Put out a stub for now.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + 
                "<H3>Form not implemented yet" + 
                "</FORM></BODY></HTML>")
