#----------------------------------------------------------------------
#
# $Id: CTGovMarkDuplicate.py,v 1.1 2004-04-26 20:37:17 venglisc Exp $
#
# Interface to allow users to mark a CTGov protocol as a duplicate in
# the system.  The protocol will be updated in the ctgov_import table
# with the CDR-ID of the InScopeProtocol that the CTGov protocol is
# a duplicate of.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
cdrId    = fields and fields.getvalue("Cdr_Id") or None
nctId    = fields and fields.getvalue("Nctid") or None
title    = "CDR Administration"
section  = "Mark Duplicate CTGov Protocol"
buttons  = ["Update", cdrcgi.MAINMENU, "Log Out"]
script   = "CTGovMarkDuplicate.py"

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()  
except cdrdb.Error, info:   
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Handle request to update ctgov_import table.
#----------------------------------------------------------------------
if request == "Update":
    if not cdrId or not nctId:
        cdrcgi.bail("Both document IDs are required.")
    # ----------------------------------------------------------
    # Find out if the NCTID exists
    # ----------------------------------------------------------
    try:
        query = """
            SELECT nlm_id, cdr_id 
            FROM   ctgov_import
            WHERE  nlm_id = '%s'
""" % nctId
        cursor.execute(query)
        row = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail("Invalid NCT ID entered: %s - %s" % (nctId, info[1][0]))
    
    # ----------------------------------------------------------
    # If the second element is None the CDRID is Null in the 
    # table for this NCTID.
    # Set the section display accordingly.
    # ----------------------------------------------------------
    if row and row[1] == None:
        section = "Entered CDRID for CTGov Protocol: %s" % nctId
    else:
        section = "Corrected CDRID for CTGov Protocol: %s" % nctId

    try:
        query = """\
            UPDATE ctgov_import
               SET cdr_id = %s, 
                   dt = GETDATE(), 
                   disposition = (SELECT id
                                    FROM ctgov_disposition
                                   WHERE name = 'duplicate'
                                 )
             WHERE nlm_id = '%s'
""" % (cdr.normalize(cdrId)[3:], nctId)
        cursor.execute(query)

        # -------------------------------------------------------
        # If the NCI ID doesn't exist the UPDATE will return with
        # a record count of zero.  Catch it and display message
        # -------------------------------------------------------
        if cursor.rowcount == 0:
            cdrcgi.bail("NCT ID does not exist: %s" % nctId)

        conn.commit()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure updating CTGov Protocol %s with %s: %s" % 
                                               (nctId, cdrId, info[1][0]))

#----------------------------------------------------------------------
# Display the form for updating ctgov_import table with CDRID 
#----------------------------------------------------------------------
header  = cdrcgi.header(title, title, section, script, buttons)
form = """\
<H2>Specify CTGov Protocol to be Marked as Duplicate</H2>
<TABLE>
 <TR>
  <TD ALIGN='right' NOWRAP><B>CDR ID:</B></TD>
  <TD><INPUT NAME='Cdr_Id'><TD>
 </TR>
 <TR>
  <TD ALIGN='right' NOWRAP><B>NCT ID:</B></TD>
  <TD><INPUT NAME='Nctid'><TD>
 </TR>
</TABLE>
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
