#----------------------------------------------------------------------
#
# $Id: DocVersionHistory.py,v 1.16 2004-07-27 16:03:16 venglisc Exp $
#
# Show version history of document.
#
# $Log: not supported by cvs2svn $
# Revision 1.15  2004/07/13 19:20:21  venglisc
# Added code to display information on why the removal date of a document
# can not be displayed, i.e. blocked via full-load, not versioned yet
# (Bug #216).
#
# Revision 1.14  2004/05/11 17:32:03  bkline
# Plugged in information about publication blocks and removals.
#
# Revision 1.13  2004/03/23 22:43:46  venglisc
# Modified to display an "R " in front of version if document has been
# removed from Cancer.gov display.
#
# Revision 1.12  2004/02/05 13:36:47  bkline
# Changed title bar from "QC Reports" to "Document Version History" (request
# #1096).
#
# Revision 1.11  2003/02/12 16:19:10  pzhang
# Showed Vendor or CG job suffix with publication dates.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, sys, time

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "Document Version History Report"
fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Document Version History"
SUBMENU  = "Reports Menu"
buttons  = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "DocVersionHistory.py"
header   = cdrcgi.header(title, title, section, script, buttons, method = 'GET')
docId    = fields.getvalue(cdrcgi.DOCID) or None
docTitle = fields.getvalue("DocTitle")   or None
now      = time.localtime()
if docId:
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)

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
# If we have a document type but no doc ID or title, ask for the title.
#----------------------------------------------------------------------
if not docId and not docTitle:
    form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <TABLE>
   <TR>
    <TD>Document ID:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocId'></TD>
   </TR>
   <TR>
    <TD>Document title:&nbsp;</TD>
    <TD><INPUT SIZE='60' NAME='DocTitle'></TD>
   </TR>
  </TABLE>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + """\
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# If we have a document title but not a document ID, find the ID.
#----------------------------------------------------------------------
if docTitle and not docId:
    try:
        cursor.execute("""\
            SELECT id
              FROM document
             WHERE title LIKE ?""", docTitle + '%')
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find document with title '%s'" % docTitle)
        if len(rows) > 1:
            cdrcgi.bail("Ambiguous title '%s'" % docTitle)
        intId = rows[0][0]
        docId = "CDR%010d" % intId
    except cdrdb.Error, info:
        cdrcgi.bail('Failure looking up document title: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the document information we need.
#----------------------------------------------------------------------
try:
    cursor.execute("""SELECT doc_title,
                             doc_type,
                             doc_status,
                             created_by,
                             created_date,
                             mod_by,
                             mod_date
                        FROM doc_info 
                       WHERE doc_id = ?""", intId)
    row = cursor.fetchone()
    if not row:
        cdrcgi.bail("Unable to find document information for %s" % docId)
    docTitle, docType, docStatus, createdBy, createdDate, modBy, modDate = row
except cdrdb.Error, info:    
        cdrcgi.bail('Unable to find document information for %s: %s' % (docId, 
                                                                 info[1][0]))

#----------------------------------------------------------------------
# Build the report header.
# If a document has been blocked for publication display the date that
# the document had been removed from Cancer.gov.
# The date itself will be selected from the database in a later query.
# Put in a placeholder first at this point.
# Note:  The date will only be displayed if the docStatus has been set
#        to 'I'.
#        Also, if a document is blocked from publication it can happen
#        that the document version does not display a removed='Y'
#        entry.  In this case the document was dropped due to a full
#        data load.  
#----------------------------------------------------------------------
if docStatus == 'I':
    docStatusLine = """
   <tr>
    <b>
     <td valign = 'top' align='right' nowrap='1'>
      <font size='3'>Document Status:&nbsp;</font>
     </td>
    <b>
    <b>
     <td colspan='1'>
      <b>BLOCKED FOR PUBLICATION</b>
     </td>
    </b>
    <td align='right'>
     <b>Removal Date:&nbsp;</b>
    </td>
    <td>
     <b>@@REMOVAL_DATE@@</b>
    </td>
   </tr>"""
elif docStatus == 'A':
    docStatusLine = ""

html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR%010d - %s</title>
  <basefont face='Arial, Helvetica, sans-serif'>
 </head>
 <body>
  <center>
   <b>
    <font size='4'>Document Version History Report</font>
   </b>
   <br />
   <font size='4'>%s</font>
  </center>
  <br />
  <br />
  <table border = '0' width = '100%%'>
   <tr>
    <b>
     <td align='right' nowrap='1'>
      <font size='3'>Document Id:&nbsp;</font>
     </td>
    <b>
    <b>
     <td nowrap='1'>
      <font size='3'>CDR%010d</font>
     </td>
    <b>
    <b>
     <td align='right' nowrap='1'>
      <font size='3'>Document Type:&nbsp;</font>
     </td>
    <b>
    <b>
     <td nowrap='1'>
      <font size='3'>%s</font>
     </td>
    <b>
   </tr>
   <tr>
    <b>
     <td valign = 'top' align='right' nowrap='1'>
      <font size='3'>Document Title:&nbsp;</font>
     </td>
    <b>
    <b>
     <td colspan='3'>
      <font size='3'>%s</font>
     </td>
    </b>
   </tr>
   %s
   <tr>
    <b>
     <td align='right' nowrap='1'>
      <font size='3'>Created By:&nbsp;</font>
     </td>
    <b>
    <b>
     <td nowrap='1'>
      <font size='3'>%s</font>
     </td>
    <b>
    <b>
     <td align='right' nowrap='1'>
      <font size='3'>Date:&nbsp;</font>
     </td>
    <b>
    <b>
     <td nowrap='1'>
      <font size='3'>%s</font>
     </td>
    <b>
   </tr>
   <tr>
    <b>
     <td align='right' nowrap='1'>
      <font size='3'>Last Updated By:&nbsp;</font>
     </td>
    <b>
    <b>
     <td nowrap='1'>
      <font size='3'>%s</font>
     </td>
    <b>
    <b>
     <td align='right' nowrap='1'>
      <font size='3'>Date:&nbsp;</font>
     </td>
    <b>
    <b>
     <td nowrap='1'>
      <font size='3'>%s</font>
     </td>
    <b>
   </tr>
  </table>
  <br />
  <table border='1' width='100%%' cellspacing='0' cellpadding='2'>
   <tr>
    <td align='center' valign='top'>
     <b>
      <font size='3'>VERSION #</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>COMMENT</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>DATE</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>USER</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>VALIDITY</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>PUBLISHABLE?</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>PUBLICATION DATE(S)</font>
     </b>
    </td>
   </tr>
""" % (intId, 
       time.strftime("%m/%d/%Y", now), 
       time.strftime("%B %d, %Y", now),
       intId,
       docType,
       docTitle,
       docStatusLine,
       createdBy or "[Conversion]",
       createdDate and createdDate[:10] or "2002-06-22",
       modBy or "N/A",
       modDate and modDate[:10] or "N/A")

#----------------------------------------------------------------------
# Object to hold info for a single version.
#----------------------------------------------------------------------
class DocVersion:
    def __init__(self, row):
        self.num            = row[0]
        # If a version has been removed from C.gov, mark it
        # -------------------------------------------------
        if row[9] == 'Y':
           removeDate = row[1][:10]
	else:
	   removeDate = 'Full-load removal'
        whichJob            = row[7] and '(V-' or '(C-' 
        whichJob           += row[8] and "%d)" % row[8] or ')'
        self.pubDates       = row[1] and [row[1][:10] + whichJob] or []
        self.comment        = row[2]
        self.user           = row[3]
        self.date           = row[4][:10]
        self.valStatus      = row[5]
        self.publishable    = row[6]
 
    def display(self):
        return """\
   <tr>
    <td align = 'center' valign = 'top'>
     <font size = '3'>%d</font>
    </td>
    <td valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td align = 'center' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td align = 'center' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td align = 'center' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td align = 'center' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
   </tr>
""" % (self.num,
       self.comment or "&nbsp;",
       self.date,
       self.user,
       self.valStatus,
       self.publishable == 'Y' and 'Y' or 'N',
       self.pubDates and "<br>".join(self.pubDates) or "&nbsp;")
        
#----------------------------------------------------------------------
# Build the report body.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
         SELECT v.num, 
                d.started,
                v.comment,
                u.fullname,
                v.dt,
                v.val_status,
                v.publishable,
                d.output_dir,
                d.pub_proc,
                d.removed
           FROM doc_version v
           JOIN usr u
             ON u.id = v.usr
LEFT OUTER JOIN primary_pub_doc d
             ON d.doc_id = v.id
            AND d.doc_version = v.num
            AND d.failure is null
          WHERE v.id = ?
       ORDER BY v.num DESC,
                d.started""", intId)

    currentVer = None
    row = cursor.fetchone()
    removeDate = ''
    while row:
        if currentVer:
            if currentVer.num == row[0]:
                if row[1]:
                    # If a version has been removed from C.gov, extract
		    # the removal date for later display
                    # -------------------------------------------------
                    if row[9] == 'Y' and docStatus == 'I':
                       removeDate = row[1][:10]
                    whichJob = (row[7] and '(V-' or '(C-') + "%d)" % row[8]
                    currentVer.pubDates.append(row[1][:10] + whichJob)
            else:
                html += currentVer.display()
                currentVer = DocVersion(row)
        else:
            currentVer = DocVersion(row)
	lastJob = row[8]
        row = cursor.fetchone()
    
    # A document has been blocked but none of the document versions 
    # indicate the removal.  This could have two reasons:
    # a) the document has been blocked since the last publication
    #    (and will be removed as part of the next publication)
    #    However, only a versioned document can be removed.  We also
    #    need to check if the document exists with a newer version
    #    or not.
    # b) the document got removed as part of a full load
    # -------------------------------------------------------------
    if docStatus == 'I' and not removeDate:
       try:
          cursor.execute("""\
             SELECT * from pub_proc_cg
	     WHERE  id = ?""", intId)
          rowcg = cursor.fetchone()
	  if rowcg:             # Doc currently exists on Cancer.gov
	     try:
	        cursor.execute("""\
		   SELECT * 
		   FROM  pub_proc_doc ppd, doc_version dv, 
		         pub_proc_cg ppc, pub_proc pp
		   WHERE ppc.pub_proc = pp.id
		     AND ppc.id = dv.id
		     AND ppc.id = ppd.doc_id
		     AND dv.id  = ?
		     AND ppc.pub_proc    = ppd.pub_proc
		     AND ppd.doc_version = dv.num
		     AND updated_dt < started
		     AND NOT EXISTS (SELECT 'x'
		                     FROM  doc_version i 
				     WHERE i.id  = ppd.doc_id
				     AND   i.num > ppd.doc_version
		                    )
		   ORDER BY ppd.pub_proc""", intId)
		rowVer = cursor.fetchone()
		if rowVer:
                   removeDate = 'Needs Versioning'
		else:
		   removeDate = 'Not yet removed'
             except cdrdb.Error, info:
                cdrcgi.bail('Failure getting document version date')
	     
	  else:                 # Doc does not exist on Cancer.gov
	     try:
	        cursor.execute("""\
		   SELECT MIN(o.id), o.started 
		   FROM pub_proc o
		   JOIN pub_proc i
		     ON i.status = o.status
		    AND i.pub_subset = o.pub_subset
		    AND i.started < o.started
		  WHERE o.pub_subset = 'Full-Load'
		    AND o.status = 'Success'
		    AND o.id > ?
		  GROUP BY o.started""", lastJob)
		rowcg = cursor.fetchone()
	        removeDate = rowcg[1][:10]
             except cdrdb.Error, info:
		# No Version of this document ever got published
                removeDate = 'Never Published'
                # cdrcgi.bail('Failure getting following Full-Load date')

       except cdrdb.Error, info:
          cdrcgi.bail('Failure query pub_prog_cg')
    if currentVer:
        html += currentVer.display()

except cdrdb.Error, info:
    cdrcgi.bail('Failure extracting version information: %s' % info[1][0])

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
html += """\
  </table>
 </body>
</html>"""

# -------------------------------------------------------
# Substitute the removal date once we've got is assigned.
# -------------------------------------------------------
html = re.sub("@@REMOVAL_DATE@@", removeDate, html)
cdrcgi.sendPage(html)
