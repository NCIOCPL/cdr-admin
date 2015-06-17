#----------------------------------------------------------------------
#
# $Id$
#
# Script to adjust the mappings in the ctgov_import table so that an
# NCT document which had been rejected as a duplicate becomes the
# actively imported document, and the NCT document which had been
# the actively imported document is marked as a duplicate.
#
# BZIssue::5141
#
#----------------------------------------------------------------------
import re, glob, cgi, cdrdb, cdrcgi, cdr

#----------------------------------------------------------------------
# Disposition values for the ctgov_import table.
#----------------------------------------------------------------------
DUPLICATE = 4
IMPORT = 5

#----------------------------------------------------------------------
# Get the path for the most recent CTGovProtocol download directory.
#----------------------------------------------------------------------
def findDownloadDirectory():
    # We're moving the downloaded files out of the directory containing code
    CTGovDir = 'd:/cdr/Output/CTGovDownloads'
    if not os.path.exists(CTGovDir):
        CTGovDir = 'd:/cdr/Utilities/CTGovDownloads'

    dirs = glob.glob('%s/work-20*' % CTGovDir)
    if not dirs:
        raise Exception("Unable to find CT.gov download directories")
    dirs.sort()
    return dirs[-1]

#----------------------------------------------------------------------
# Parse the date of the CT.gov download job we're using.
#----------------------------------------------------------------------
def extractDownloadDate(path):
    match = re.search("work-(20\\d\\d)(\\d\\d)(\\d\\d)", path)
    if not match:
        raise Exception("unable to extract download date from %s" % path)
    return "%s-%s-%s" % (match.group(1), match.group(2), match.group(3))

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
request = cdrcgi.getRequest(fields)
session = cdrcgi.getSession(fields)
cdrId   = fields.getvalue('cdrid')
nlmId   = fields.getvalue('nlmid')
dupId   = fields.getvalue('dupid')
comment = fields.getvalue('comment')
SUBMENU = "CTGov Protocols Menu"
buttons = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "Task5141.py"
title   = "CDR Administration"
section = "Swap NCT IDs"
status  = ""
header  = cdrcgi.header(title, title, section, script, buttons,
                        stylesheet = """\
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script language='JavaScript' src='/js/CdrCalendar.js'></script>
   <style type='text/css'>
    .err { width: 100%; text-align: center; font-weight: bold; color: red }
    .status { width: 100%; text-align: center; font-weight: bold; color: green }
    .CdrDateField { width: 100px; }
    #request-form label { float: left; width: 30%; text-align: right;
                          font-family: Arial, sans-serif; }
    #request-form input { width: 65%; margin-left: 5px; }
   </style>
""")

#----------------------------------------------------------------------
# Swap the NCT IDs for a trial.
#----------------------------------------------------------------------
def handleRequest(cdrId, nlmId, dupId, comment):
    directory = findDownloadDirectory()
    downloadDate = extractDownloadDate(directory)
    try:
        path = "%s/%s.xml" % (directory, nlmId)
        fp = open(path, "rb")
        bytes = fp.read()
        fp.close()
    except:
        raise Exception("Unable to find %s in the latest download set" % nlmId)
    conn = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT comment FROM ctgov_import WHERE nlm_id = ?", nlmId)
    rows = cursor.fetchall()
    if rows:
        if rows[0][0]:
            comment += "; %s" % rows[0][0]
        cursor.execute("""\
UPDATE ctgov_import
   SET xml = ?,
       changed = GETDATE(),
       dt = GETDATE(),
       cdr_id = ?,
       comment = ?,
       disposition = ?
 WHERE nlm_id = ?""", (bytes, cdrId, comment, IMPORT, nlmId))
        if cursor.rowcount != 1:
            raise Exception("unable to update row for %s" % nlmId)
    else:
        cursor.execute("""\
INSERT INTO ctgov_import (xml, nlm_id, cdr_id, disposition, dt, comment,
                          downloaded)
     VALUES (?, ?, ?, ?, GETDATE(), ?, ?)""",
                       (bytes, nlmId, cdrId, IMPORT, comment, downloadDate))
    status = "<p class='status'>Marked %s for import as CDR%s" % (nlmId, cdrId)
    if dupId:
        cursor.execute("""\
UPDATE ctgov_import
   SET disposition = ?
 WHERE nlm_id = ?""", (DUPLICATE, dupId))
        if cursor.rowcount == 1:
            status += "; marked %s as duplicate" % dupId
        else:
            raise Exception("Unable to mark %s as duplicate" % dupId)
    conn.commit()
    return status + "</p>"

#----------------------------------------------------------------------
# Make sure we're logged in and are authorized to use this script.
#----------------------------------------------------------------------
if not session:
    cdrcgi.bail('Unknown or expired CDR session.')
if not cdr.canDo(session, 'SWAP NCT IDS'):
    cdrcgi.bail("You are not authorized to use this script")

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("CTGov.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we have a request, handle it.
#----------------------------------------------------------------------
if request and cdrId and nlmId:
    try:
        status = handleRequest(cdrId, nlmId, dupId, comment)
    except Exception, e:
        status = "<p class='err'>%s</p>" % cgi.escape(str(e))

#----------------------------------------------------------------------
# Put up the request form.
#----------------------------------------------------------------------
form = """\
   <input type='hidden' name='%s' value='%s' />
   %s
   <fieldset id='request-form'>
    <legend>Trial To Modify</legend>
    <label for='cdrid'>CDR ID:</label>
    <input name='cdrid' id='cdrid' />
    <br />
    <label for='nlmid'>Active NCT ID:</label>
    <input name='nlmid' id='nlmid' />
    <br />
    <label for='dupid'>Duplicate NCT ID:</label>
    <input name='dupid' id='dupid' />
    <br />
    <label for='comment'>Optional Comment:</label>
    <input name='comment' id='comment' />
   </fieldset>
  </form>
""" % (cdrcgi.SESSION, session, status)
cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")
