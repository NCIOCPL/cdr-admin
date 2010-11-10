#----------------------------------------------------------------------
#
# $Id$
#
# Interface to allow users to mark a CTGov protocol as a duplicate in
# the system.  The protocol will be updated in the ctgov_import table
# with the CDR-ID of the InScopeProtocol that the CTGov protocol is
# a duplicate of.
#
# BZIssue::4763 (restrict use of script)
# BZIssue::4702 Modify to use SQL placeholders
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
# Make sure the current user is allowed to use this script.
#----------------------------------------------------------------------
if not cdr.canDo(session, 'MARK NLM DUPLICATES'):
    cdrcgi.bail("User not authorized to use this script")

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
    if not usrCmt or not nctId:
        cdrcgi.bail("Comment and NCT ID are both required fields")
    if unmarkCdr and cdrId:
        cdrcgi.bail("CDR ID not allowed when unmarking duplicate setting")
    if not unmarkCdr and not cdrId:
        cdrcgi.bail("CDR ID is required when marking duplicate")

    # ----------------------------------------------------------
    # Find out if the NCTID exists
    # ----------------------------------------------------------
    try:
        query = """
            SELECT nlm_id, cdr_id, comment
            FROM   ctgov_import
            WHERE  nlm_id = ?
"""
        cursor.execute(query, nctId)
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

        preQuery = """\
                SELECT id
                  FROM ctgov_disposition
                 WHERE name = 'import requested'
"""
        query = """\
                UPDATE ctgov_import
                   SET cdr_id = null, 
                       dt = GETDATE(), 
                       disposition = ?,  -- Value of preQuery
                       comment = ?
                 WHERE nlm_id  = ?
"""
    # Updating a duplicate record 
    # ----------------------------
    else:
        if not row[2]:
                dbmarkCmt = usrCmt
        else:
                dbmarkCmt = row[2] + "; MARK DUPLICATE:" + usrCmt

        preQuery = """\
                SELECT id
                  FROM ctgov_disposition
                 WHERE name = 'duplicate'
"""
        query = """\
                UPDATE ctgov_import
                   SET cdr_id = ?, 
                       dt = GETDATE(), 
                       disposition = ?,  -- Value of preQuery
                       comment = ?
                 WHERE nlm_id  = ?
"""
    #cdrcgi.bail(query)
    try:
        # We can't select the disposition ID with a sub-query since
        # we wouldn't be able to use the parameter substitution for 
        # the query but we also can't use Python's string substitution
        # because that would fail if comments with a quote (') are 
        # submitted.
        # Performing the selection of the disposition separately.
        # ------------------------------------------------------------
        cursor.execute(preQuery)
        thisDispo = cursor.fetchone()
        cursor.close()

        if unmarkCdr:
            cursor.execute(query, (thisDispo[0], dbmarkCmt, nctId))
        else:
            cursor.execute(query, (thisDispo[0], cdr.exNormalize(cdrId)[1], 
                                   dbmarkCmt, nctId))

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
