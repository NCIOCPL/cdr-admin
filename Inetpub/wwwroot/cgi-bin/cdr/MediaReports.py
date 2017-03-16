#----------------------------------------------------------------------
# Admin menu for reports on CDR Media documents.
#
# BZIssue::1653
# BZIssue::2135
# BZIssue::3226
# BZIssue::3704
#----------------------------------------------------------------------
import cgi, cdrcgi

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
page    = cdrcgi.Page(title, subtitle=section, action="Reports.py",
                      buttons=buttons, session=session,
                      body_classes="admin-menu")

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
# QC reports.
#----------------------------------------------------------------------
session = "%s=%s" % (cdrcgi.SESSION, session)
B = cdrcgi.Page.B
page.add(B.H3("QC Reports"))
page.add("<ol>")
url = "MediaSearch.py?%s" % session
page.add(B.LI(B.A("Advanced Search", href=url)))
url = "%s/QcReport.py?DocType=Media&ReportType=img&%s" % (cdrcgi.BASE, session)
page.add(B.LI(B.A("Media Doc QC Report", href=url)))
page.add("</ol>")

#----------------------------------------------------------------------
# Management reports.
#----------------------------------------------------------------------
page.add(B.H3("Management Reports"))
page.add("<ol>")
for script, label in(
    ("ocecdr-4038.py?", "Media (Images) Processing Status Report"),
    ('RecordingTrackingReport.py?', 'Board Meeting Recording Tracking Report'),
    ('MediaLists.py?',              'Media Lists'),
    ('ocecdr-3704.py?',             'Media Permissions Report'),
    ('MediaCaptionContent.py?',     'Media Caption and Content Report'),
    ('PubStatsByDate.py?VOL=Y&',    'Media Doc Publishing Report'),
    ('MediaLinks.py?',              'Linked Media Documents'),
):
    url = "%s/%s%s" % (cdrcgi.BASE, script, session)
    page.add(B.LI(B.A(label, href=url)))
page.add("</ol>")

#----------------------------------------------------------------------
# Other reports.
#----------------------------------------------------------------------
page.add(B.H3("Other Reports"))
page.add("<ol>")
for script, label in (
    ('PronunciationRecordings.py?',
     'Audio Pronunciation Recordings Tracking Report'),
    ('GlossaryTermAudioReviewReport.py?',
     'Audio Pronunciation Review Statistics Report'),
):
    url = "%s/%s%s" % (cdrcgi.BASE, script, session)
    page.add(B.LI(B.A(label, href=url)))
page.add("</ol>")

#----------------------------------------------------------------------
# Display the menu.
#----------------------------------------------------------------------
page.send()
