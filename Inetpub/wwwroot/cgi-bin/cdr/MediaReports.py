#----------------------------------------------------------------------
#
# $Id$
#
# BZIssue::1653
# BZIssue::2135
# BZIssue::3226
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
section = "Media Reports"
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
# Display available menu choices.
#----------------------------------------------------------------------
session = "%s=%s" % (cdrcgi.SESSION, session)
#    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
form = """\
   <H3>QC Reports</H3>
   <OL>
    <LI><a href='MediaSearch.py?%s'>Advanced Search</a></LI>
""" % session

for choice in (
               ('img',  'Media Doc QC Report'   ),
              ):
    form += """\
    <LI><a href='%s/QcReport.py?DocType=Media&ReportType=%s&%s'>%s</a></LI>
""" % (cdrcgi.BASE, choice[0], session, choice[1])
form += """\
   </OL>

   <H3>Management Reports</H3>
   <OL>"""

for choice in(
              ('RecordingTrackingReport.py?',
                                   'Board Meeting Recording Tracking Report'),
              ('MediaLists.py?',          'Media Lists'),
              ('MediaTrackingReport.py?', 'Media Tracking Report'),
              ('MediaCaptionContent.py?', 'Media Caption and Content Report'),
              ('PubStatsByDate.py?VOL=Y',
                                          'Media Doc Publishing Report'),
              ('MediaLinks.py?',          'Linked Media Documents'),
             ):
    form += """
    <LI><a href='%s/%s&%s'>%s</a></LI>""" % (cdrcgi.BASE, choice[0],
                                              session, choice[1])
form += """\
   </OL>

   <H3>Other Reports</H3>
   <OL>"""

for choice in (
    ('GlossaryTermAudioReviewReport.py?',
     'Audio Pronunciation Review Statistics Report'),
    ):
    form += """\
    <LI><a href='%s/%s&%s'>%s</a></LI>""" % (cdrcgi.BASE, choice[0],
                                             session, choice[1])

footer = """
   </OL>
  </FORM>
 </BODY>
</HTML>"""
cdrcgi.sendPage(header + form + footer)
