#----------------------------------------------------------------------
#
# $Id: ProtocolReports.py,v 1.2 2002-05-25 02:39:13 bkline Exp $
#
# Submenu for protocol reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/05/24 20:37:31  bkline
# New Report Menu structure implemented.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Protocol Reports"
SUBMENU = "Reports Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "Reports.py", buttons)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

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
    <H3>QC Reports</H3>
    [Note that most of these are stubbed because they were
     originally intended to be invoked directly from XMetaL
     for the currently open document, so we still need to
     implement a page for specifying which document the
     QC report is to be launched for.
     The Advanced Protocol Search form uses the Health
     Professional Protocol QC Report, so that choice below
     works now.
    <OL>
""" % (cdrcgi.SESSION, session)
reports = [
           ('Stub.py', 'Administrative Protocol QC Report'),
           ('Stub.py', 'Full Protocol QC Report'),
           ('ProtSearch.py', 'Health Professional Protocol QC Report'),
           ('Stub.py', 'Patient Protocol QC Report'),
           ('Stub.py', 'Protocol Citation QC Report')
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
           ('Stub.py', 'Approved Protocols'),
           ('NewlyPublishedTrials.py', 'Newly Published Protocols'),
           ('Stub.py', 'Published Protocol Count')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
