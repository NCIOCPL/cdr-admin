#----------------------------------------------------------------------
#
# $Id$
#
# Interface for forcing the import of a trial from ClinicalTrials.gov
# when none of the search terms for the trial match the criteria for
# our import search request.
#
# BZIssue::2065
# BZIssue::3110
# BZIssue::4661
# BZIssue::4700
# BZIssue::4718 (fixed typo in SELECT query)
#
#----------------------------------------------------------------------
import cgi, cdrcgi, cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
nctId   = fields.getvalue('nctid') or None
title   = "CDR Administration"
section = "Force Download of a Trial"
SUBMENU = "CTGov Protocols"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "ForceCtgovImport.py", buttons)
extra   = u""

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("CTGov.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Construct a string describing the result of the last action.
#----------------------------------------------------------------------
def describeResult(result, nctId, color):
    return u"<span style='color: %s'><b>%s %s</b></span><br><br>" % (color,
                                                                     nctId,
                                                                     result)

#----------------------------------------------------------------------
# Get the disposition code for 'import requested'.
#----------------------------------------------------------------------
def getImportRequestedCode(cursor):
    cursor.execute("""\
        SELECT id
          FROM ctgov_disposition
         WHERE name = 'import requested'""")
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Failure fetching disposition code for 'import requested'")
    return rows[0][0]

#----------------------------------------------------------------------
# If we have an ID, process it.
#----------------------------------------------------------------------
if nctId:
    conn = cdrdb.connect()
    cursor = conn.cursor()
    dispositionCode = getImportRequestedCode(cursor)
    cursor.execute("""\
        SELECT c.force, d.name
          FROM ctgov_import c
          JOIN ctgov_disposition d
            ON d.id = c.disposition
         WHERE nlm_id = ?""", nctId)
    rows = cursor.fetchall()
    if not rows:
        cursor.execute("""\
            INSERT INTO ctgov_import (nlm_id, disposition, dt, force)
                 VALUES (?, ?, GETDATE(), 'Y')""", (nctId, dispositionCode))
        conn.commit()
        extra = describeResult(u"added to table and marked for forced download",
                               nctId, u"green")
    elif rows[0][0] == 'Y':
        extra = describeResult(u"already marked for forced download", nctId,
                               u"red")
    elif rows[0][1] == 'duplicate':
        extra = describeResult(u"is marked as a duplicate; you must first "
                               u"use the 'Mark/Remove Protocols as Duplicates' "
                               u"Administrative Menu Page to back out the "
                               u"'duplcate' status for this document",
                               nctId, u"red")
    else:
        cursor.execute("""\
            UPDATE ctgov_import
               SET force = 'Y',
                   disposition = %d
             WHERE nlm_id = ?""" % dispositionCode, nctId)
        conn.commit()
        extra = describeResult(u"marked for forced download", nctId, u"green")

form = u"""\
    <input type='hidden' name='%s' value='%s'>
    %s
    <b>NCT ID:&nbsp;</b>
    <input name='nctid'>&nbsp;
    <input type='submit' value='Mark Trial for Forced Download'>
""" % (cdrcgi.SESSION, session, extra)
cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
