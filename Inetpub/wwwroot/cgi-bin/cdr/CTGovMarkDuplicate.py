#----------------------------------------------------------------------
#
# $Id$
#
# Interface to allow users to mark a CTGov protocol as a duplicate in
# the system.  The protocol will be updated in the ctgov_import table
# with the CDR-ID of the InScopeProtocol that the CTGov protocol is
# a duplicate of.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2004/07/13 15:46:26  venglisc
# Modified so that document for which the CDR-ID has been removed will
# set the disposition from "duplicate" to "import requested".
# With this change the trial will not appear on the report listing all
# duplicates.
#
# Revision 1.1  2004/04/26 20:37:17  venglisc
# Initial version for user interface allowing to update the CDRID of the
# ctgov_import table.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
cdrId     = fields and fields.getvalue("CdrId") or None
nctId     = fields and fields.getvalue("NctId") or None
unmarkCdr = fields and fields.getvalue("UnmarkCdr") or None
usrCmt    = fields and fields.getvalue("UserComment") or None
title     = "CDR Administration"
section   = "Mark/Remove Duplicate CTGov Protocol"
buttons   = ["Update", cdrcgi.MAINMENU, "Log Out"]
script    = "CTGovMarkDuplicate.py"

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
    # Test proper entry of input data
    # -------------------------------
    if not usrCmt:
        cdrcgi.bail("Comment required to update Protocol")

    if not cdrId or not nctId:
        if not unmarkCdr:
             cdrcgi.bail("Both document IDs are required.")
    elif unmarkCdr and not nctId:
        cdrcgi.bail("NCT ID required.")
    elif unmarkCdr and not usrCmt:
        cdrcgi.bail("Comment is required to remove CDR ID")
    else:
        if unmarkCdr and cdrId:
            cdrcgi.bail("CDR ID not allowed when unmarking NCT ID")

    # ----------------------------------------------------------
    # Find out if the NCTID exists
    # ----------------------------------------------------------
    try:
        query = """
            SELECT nlm_id, cdr_id, comment
            FROM   ctgov_import
            WHERE  nlm_id = '%s'
""" % nctId
        cursor.execute(query)
        row = cursor.fetchone()

        if row == None:
            cdrcgi.bail("No record found: " + nctId)

    except cdrdb.Error, info:
        cdrcgi.bail("Invalid NCT ID entered: %s - %s" % (nctId, info[1][0]))
    
    # ----------------------------------------------------------
    # If the second element is None the CDRID is Null in the 
    # table for this NCTID.
    # Set the section display accordingly.
    # ----------------------------------------------------------
    if row and row[1] == None and not unmarkCdr:
        section = "Entered CDRID: %s for CTGov Protocol: %s" % (cdrId, nctId)
    elif unmarkCdr:
        section = "Removed CDRID for CTGov Protocol: %s" % nctId
    else:
        section = "Corrected CDRID: %s for CTGov Protocol: %s" % (cdrId, nctId)

    # Unmarking the duplicate record 
    # ------------------------------
    if unmarkCdr:
        if not row[2]:
                dbmarkCmt = usrCmt
        else:
                dbmarkCmt = row[2] + "; REMOVE CDR-ID:" + usrCmt

        query = """\
                UPDATE ctgov_import
                   SET cdr_id = null, 
                       dt = GETDATE(), 
                       disposition = (SELECT id
                                        FROM ctgov_disposition
                                       WHERE name = 'import requested'
                                     ),
                       comment = '%s'
                 WHERE nlm_id = '%s'
""" % (dbmarkCmt, nctId )
    # Updating a duplicate record 
    # ----------------------------
    else:
        if not row[2]:
                dbmarkCmt = usrCmt
        else:
                dbmarkCmt = row[2] + "; MARK DUPLICATE:" + usrCmt

        query = """\
                UPDATE ctgov_import
                   SET cdr_id = %s, 
                       dt = GETDATE(), 
                       disposition = (SELECT id
                                        FROM ctgov_disposition
                                       WHERE name = 'duplicate'
                                     ),
                       comment = '%s'
                 WHERE nlm_id = '%s'
""" % (cdr.normalize(cdrId)[3:], dbmarkCmt, nctId)
    try:
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
<H2>CTGov Protocol to be Marked/Removed as Duplicate</H2>
<TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>
 <TR>
  <TD ALIGN='left' NOWRAP>
   <FONT SIZE='3'>
   <B>CDR ID: </B>
   </FONT>
  </TD>
  <TD>
   <INPUT NAME='CdrId'>
  <TD>
  <TD VALIGN='bottom'>
   <INPUT TYPE='checkbox' NAME='UnmarkCdr'>
   <B>Select Checkbox to Remove CDR-ID</B>
  <TD>
 </TR>
 <TR>
  <TD ALIGN='left' NOWRAP VALIGN='top'>
   <FONT SIZE='3'>
   <B>NCT ID: </B>
   </FONT>
  </TD>
  <TD VALIGN='top'>
   <INPUT NAME='NctId'>
  <TD>
 </TR>
</TABLE>
<BR/>
<B>Comment<B><BR/>
<TEXTAREA ROWS=8 COLS=60 NAME='UserComment'></TEXTAREA>
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
