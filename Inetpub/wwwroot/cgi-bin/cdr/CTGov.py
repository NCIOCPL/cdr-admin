#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for ClinicalTrials.gov activities.
#
# BZIssue::4700
# BZIssue::4804
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
           ('ForceCtgovImport.py?', 'Force CTGov Download'),
           ('CTGovImport.py?which=new&', 'Review New Protocols'),
           ('CTGovImport.py?which=cips&', 'Review Protocols Sent to CIPS')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</A></LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Mapping table</H3>
    <OL>
"""
reports = [
           ('EditExternMap.py', 'Update Mapping Table'),
           ('CTGovMarkDuplicate.py', 'Mark/Remove Protocols as Duplicates'),
           ('GlobalChangeCTGovMapping.py',
            'Global Change Protocols to Find Mappings'),
           ('EditNonMappablePatterns.py',
            'Update List of Non-mappable Patterns')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</A></LI>\n" % (
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
    form += "<LI><A HREF='%s/%s&%s=%s'>%s</A></LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Management Reports</H3>
    <OL>
"""

reports = [
           ('CTGovUpdateReport.py', 'CTGovProtocols Imported vs. CWDs'),
           ('CTGovProtocolProcessingStatusReport.py',
            'CTGovProtocols Processing Status Report'),
           ('CTGovUnpublished.py', 'CTGovProtocols Unpublished with Phase'),
           ('CTGovEntryDate.py', 'CTGovProtocols vs. Early EntryDate'),
           ('ExternMapFailures.py', 'External Map Failures Report'),
           ('CTGovDupReport.py', 'Records Marked Duplicate'),
           ('CTGovOutOfScope.py', 'Records Marked Out of Scope'),
           ('CTGovDownloadReport.py', 'Statistics Report - Download'),
           ('CTGovImportReport.py', 'Statistics Report - Import')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</A></LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
