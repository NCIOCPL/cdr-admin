#----------------------------------------------------------------------
#
# $Id: DocVersionHistory.py,v 1.1 2002-06-28 13:38:07 bkline Exp $
#
# Show version history of document.
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
section  = "QC Report"
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
    """
    cursor.execute(" " "\
            SELECT d.title,
                   t.name,
                   u1.fullname,
                   a1.dt,
                   u2.fullname,
                   a2.dt
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
              JOIN audit_trail a1
                ON a1.document = d.id
              JOIN usr u1
                ON u1.id = a1.usr
              JOIN audit_trail a2
                ON a2.document = d.id
              JOIN usr u2
                ON u2.id = a2.usr
             WHERE d.id = 50000
               AND a1.dt = (SELECT MIN(audit_trail.dt)
                              FROM audit_trail
                              JOIN action
                                ON action.id = audit_trail.action
                             WHERE audit_trail.document = d.id
                               AND action.name = 'ADD DOCUMENT')
               AND a2.dt = (SELECT MAX(audit_trail.dt)
                              FROM audit_trail
                              JOIN action
                                ON action.id = audit_trail.action
                             WHERE audit_trail.document = d.id
                               AND action.name = 'MODIFY DOCUMENT')" " ", intId)
    """
    cursor.execute("""SELECT doc_title,
                             doc_type,
                             created_by,
                             created_date,
                             mod_by,
                             mod_date
                        FROM doc_info 
                       WHERE doc_id = ?""", intId)
    row = cursor.fetchone()
    if not row:
        cdrcgi.bail("Unable to find document information for %s" % docId)
    docTitle, docType, createdBy, createdDate, modBy, modDate = row
except cdrdb.Error, info:    
        cdrcgi.bail('Unable to find document information for %s: %s' % (docId, 
                                                                 info[1][0]))

    
#----------------------------------------------------------------------
# Build the report header.
#----------------------------------------------------------------------
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
      <font size='3'>PUBLISHABLE?</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>PUBLICATION DATE</font>
     </b>
    </td>
   </tr>
""" % (intId, 
       time.strftime("%m/%d/%Y", now), 
       time.strftime("%B %d, %Y", now),
       intId,
       docType,
       docTitle,
       createdBy,
       createdDate,
       modBy,
       modDate)

#----------------------------------------------------------------------
# Build the report body.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
         SELECT v.num, 
                v.comment,
                u.fullname,
                v.dt,
                v.publishable,
                p.completed
           FROM doc_version v
           JOIN usr u
             ON u.id = v.usr
LEFT OUTER JOIN pub_proc_doc d
             ON d.doc_id = v.id
            AND d.doc_version = v.num
            AND d.failure IS NULL OR d.failure <> 'Y'
LEFT OUTER JOIN pub_proc p
             ON p.id = d.pub_proc
            AND p.status = 'success'
          WHERE v.id = ?
       ORDER BY v.num DESC,
                p.completed""", intId)

    lastVer = None
    row = cursor.fetchone()
    while row:
        verNum, verComment, verUser, verDate, verPublishable, pubDate = row
        if verNum != lastVer:
            lastVer = verNum
            html += """\
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
""" % (verNum,
       verComment or "&nbsp;",
       verDate[:10],
       verUser,
       verPublishable == 'Y' and 'Y' or 'N')
        else:
            html += """\
   <tr>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
"""
        html += """
    <td align = 'center' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
   </tr>
""" % (pubDate and str(pubDate) or "&nbsp;")
        row = cursor.fetchone()

except cdrdb.Error, info:
    cdrcgi.bail('Failure extracting version information: %s' % info[1][0])

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
