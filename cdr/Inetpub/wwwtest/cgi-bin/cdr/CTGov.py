#----------------------------------------------------------------------
#
# $Id: CTGov.py,v 1.1 2003-11-03 16:09:03 bkline Exp $
#
# Submenu for ClinicalTrials.gov activities.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "ClinicalTrials.Gov Protocols"
buttons = [cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "CTGov.py", buttons)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Display available report choices.
#----------------------------------------------------------------------
form = """\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <H3>Review/Import Protocols</H3>
    <OL>
""" % (cdrcgi.SESSION, session)
reports = [
           ('CTGovImport.py', 'Review New Protocols'),
           ('Stub.py', 'Review Protocols Sent to CIPS')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Mapping table</H3>
    <OL>
"""
reports = [
           ('Stub.py', 'Update Mapping Table')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>QC Reports</H3>
    <OL>
"""
reports = [
           ('Stub.py', 'CTGov Protocol QC Report')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Management Reports</H3>
    <OL>
"""
reports = [
           ('Stub.py', 'Download Statistics Report'),
           ('Stub.py', 'Import Statistics Report'),
           ('Stub.py', 'External Map Failures Report'),
           ('Stub.py', 'Records Marked Out of Scope'),
           ('Stub.py', 'Records Marked Duplicate'),
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
