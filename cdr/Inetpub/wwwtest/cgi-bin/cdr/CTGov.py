#----------------------------------------------------------------------
#
# $Id: CTGov.py,v 1.3 2003-11-25 12:44:48 bkline Exp $
#
# Submenu for ClinicalTrials.gov activities.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2003/11/10 17:54:58  bkline
# Split interface for reviewing new protocols into two, separating out
# those waiting for CIPS feedback.  Plugged in reports for import
# statistics and external map failures.
#
# Revision 1.1  2003/11/03 16:09:03  bkline
# Menu of actions for ClinicalTrials.gov protocols.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
qcFlag  = fields and fields.getvalue("qc") or 0
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
# Handle request for QC report.
#----------------------------------------------------------------------
if qcFlag:
    header = cdrcgi.header(title, title, "CTGovProtocol QC Report",
                           "QcReport.py", buttons)
    form = """\
   <input type='hidden' name='%s' value='%s'>
   <b>Document ID:&nbsp;</b>
   <input name='DocId'>&nbsp;
   <input type='submit' name='Generate Report'>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
  </form>
 </body>
</html>
""")
    
#----------------------------------------------------------------------
# Display available report choices.
#----------------------------------------------------------------------
form = """\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <H3>Review/Import Protocols</H3>
    <OL>
""" % (cdrcgi.SESSION, session)
reports = [
           ('CTGovImport.py?which=new', 'Review New Protocols'),
           ('CTGovImport.py?which=cips', 'Review Protocols Sent to CIPS')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s&%s=%s'>%s</LI>\n" % (
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
           ('CTGov.py?qc=1', 'CTGov Protocol QC Report')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s&%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Management Reports</H3>
    <OL>
"""
reports = [
           ('Stub.py', 'Download Statistics Report'),
           ('CTGovImportReport.py', 'Import Statistics Report'),
           ('ExternMapFailures.py', 'External Map Failures Report'),
           ('Stub.py', 'Records Marked Out of Scope'),
           ('Stub.py', 'Records Marked Duplicate'),
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
