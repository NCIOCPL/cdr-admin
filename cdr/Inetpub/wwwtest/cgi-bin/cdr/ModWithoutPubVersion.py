#----------------------------------------------------------------------
#
# $Id: ModWithoutPubVersion.py,v 1.1 2002-09-11 23:30:14 bkline Exp $
#
# Reports on documents which have been changed since a previously 
# publishable version without a new publishable version have been
# created.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
modUser  = fields and fields.getvalue('ModUser')  or None
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate')   or None
docType  = fields and fields.getvalue('DocType')  or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "ModWithoutPubVersion.py"
title   = "CDR Administration"
section = "Documents Modified Since Last Publishable Version"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not request:
    if not toDate: toDate = time.strftime("%Y-%m-%d", now)
    if not fromDate:
        then     = list(now)
        then[1] -= 1
        then[2] += 1
        then     = time.localtime(time.mktime(then))
        fromDate = time.strftime("%Y-%m-%d", then)
    docTypes = cdr.getDoctypes(session)
    if type(docTypes) in [type(""), type(u"")]:
        cdrcgi.bail(docTypes)
    form = """\
   <input type='hidden' name='%s' value='%s'>
   <table border='0'>
    <tr>
     <td><b>User:&nbsp;</b></td>
     <td><input name='ModUser' value='%s'></td>
    </tr>
    <tr>
     <td><b>Document Type:&nbsp;</b></td>
     <td>
      <select name='DocType'>
      <option value='' selected>All Types</option>
""" % (cdrcgi.SESSION, session, modUser or '')
    for docType in docTypes:
        form += """\
      <option value='%s'>%s &nbsp;</option>
""" % (docType, docType)
    form += """\
    </tr>
    <tr>
     <td><b>Start Date:&nbsp;</b></td>
     <td><input name='FromDate' value='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2002-01-01)</td>
    </tr>
    <tr>
     <td><b>End Date:&nbsp;</b></td>
     <td><input name='ToDate' value='%s'>&nbsp;</td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (fromDate, toDate)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# We have a request; do it.
#----------------------------------------------------------------------
headerDocType = docType and ("%s Documents" % docType) or "Documents"
dtQual        = docType and ("AND t.name = '%s'" % docType) or ""
if not toDate  : toDate = time.strftime("%Y-%m-%d", now)
if not fromDate: fromDate = cdr.URDATE
if not modUser : modUser = '%'
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""\
            SELECT t.name,
                   d.id,
                   p.updated_dt,
                   u.fullname,
                   m.dt,
                   n.updated_dt
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
              JOIN audit_trail m
                ON m.document = d.id
              JOIN usr u
                ON u.id = m.usr
              JOIN doc_version p
                ON p.id = d.id
        LEFT OUTER JOIN doc_version n
                ON n.id = d.id
               AND n.updated_dt = (SELECT MAX(updated_dt)
                                     FROM doc_version
                                    WHERE id = d.id
                                      AND publishable = 'N')
             WHERE m.dt BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
               AND u.name LIKE '%s'
               AND p.updated_dt = (SELECT MAX(updated_dt)
                                     FROM doc_version
                                    WHERE id = d.id
                                      AND publishable = 'Y'
                                      AND updated_dt < m.dt)
               %s
          ORDER BY t.name,
                   m.dt,
                   u.fullname""" % (fromDate, toDate, modUser, dtQual))
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])


#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>List of Modified %s That Were Previously Publishable
         But Without a New Publishable Version From %s To %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>
     List of Modified %s That Were Previously Publishable
    </font>
   </b>
   <br />
   <b>
    <font size='4'>
     But Without a New Publishable Version
    </font>
   </b>
   <b>
    <font size='4'>From: %s&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;To: %s</font>
   </b>
   <br />
  </center>
  <br />
  <br />
""" % (headerDocType, fromDate, toDate, headerDocType, fromDate, toDate)

#----------------------------------------------------------------------
# Handle case for no data.
#----------------------------------------------------------------------
if not rows:
    cdrcgi.sendPage(html + """\
  <b><font size='4'>No matching documents found</font></b>
 </body>
</html>""")

#----------------------------------------------------------------------
# Fill out the report.
#----------------------------------------------------------------------
curDocType = None
for row in rows:
    docType, docId, pubDate, modBy, modDate, nonPubVerDate = row
    if docType != curDocType:
        if curDocType:
            html += """\
  </table>
  <br />
"""
        html += """\
  <b>
   <font size = '4'>Document Type:&nbsp;&nbsp;&nbsp;&nbsp;%s</font>
  </b>
  <br />
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>CDR DocId</font>
     </b>
    </td>
    <td align='center'>
     <b>
      <font size='3'>Latest Publishable Version Date</font>
     </b>
    </td>
    <td align='center'>
     <b>
      <font size='3'>Modified By</font>
     </b>
    </td>
    <td align='center'>
     <b>
      <font size='3'>Modified Date</font>
     </b>
    </td>
    <td align='center'>
     <b>
      <font size='3'>Latest Non-publishable version date?</font>
     </b>
    </td>
   </tr>
""" % docType
        curDocType = docType
   
    html += """\
   <tr>
    <td align='center'><font size='3'>CDR%010d</font></td>
    <td align='center'><font size='3'>%s</font></td>
    <td align='center'><font size='3'>%s</font></td>
    <td align='center'><font size='3'>%s</font></td>
    <td align='center'><font size='3'>%s</font></td>
   </tr>
""" % (docId, pubDate, modBy, modDate, nonPubVerDate or "None")

#----------------------------------------------------------------------
# Finish and send the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
