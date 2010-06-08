#----------------------------------------------------------------------
#
# $Id$
#
# Reports on documents which have been changed since a previously 
# publishable version without a new publishable version have been
# created.
#
# $Log: not supported by cvs2svn $
# Revision 1.8  2006/06/19 21:30:33  bkline
# Python upgrade broke mungeDate() function.  Installed workaround.
#
# Revision 1.7  2003/12/24 00:09:36  venglisc
# If a record existed in the audit_trail table with a latest record that did
# not have a status of "MODIFY DOCUMENT" or "ADD DOCUMENT" the document would
# not be listed on the report.
# Modified the inner select to fix this.
#
# Revision 1.6  2002/09/23 20:38:08  bkline
# Fixed bug in first SQL query.
#
# Revision 1.5  2002/09/23 14:42:41  bkline
# Added code to replace the ISO format with Mmm. dd, yyyy at Lakshmi's
# request.
#
# Revision 1.4  2002/09/12 13:03:35  bkline
# Added longer timeout values.
#
# Revision 1.3  2002/09/12 11:49:04  bkline
# Fixed bug in first SQL query.
#
# Revision 1.2  2002/09/12 01:07:36  bkline
# Broken down SQL query into manageable chunks.
#
# Revision 1.1  2002/09/11 23:30:14  bkline
# New report on documents modified since their last publishable version.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time, xml.dom.minidom, datetime

#----------------------------------------------------------------------
# Change date from ISO format to US-centric form.
#----------------------------------------------------------------------
def mungeDate(d):
    if not d: return "None"
    d = str(d)
    if len(d) < 10: return "Invalid date (%s)" % d
    pieces = d[:10].split('-')
    if len(pieces) != 3: return "Invalid date (%s)" % d
    try:
        year     = int(pieces[0])
        month    = int(pieces[1])
        day      = int(pieces[2])
        dateObj  = datetime.date(year, month, day)
        return dateObj.strftime("%b. %d, %Y")
    except:
        return "Invalid date (%s)" % d
    
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
        then[2] -= 6
        then     = time.localtime(time.mktime(then))
        fromDate = time.strftime("%Y-%m-%d", then)
    docTypes = cdr.getDoctypes(session)
    if type(docTypes) in [type(""), type(u"")]:
        cdrcgi.bail(docTypes)
    form = u"""\
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
        form += u"""\
      <option value='%s'>%s &nbsp;</option>
""" % (docType, docType)
    form += u"""\
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
    conn.setAutoCommit(1)
    cursor.execute("""\
            SELECT t.name      doc_type,
                   d.id        doc_id,
                   u.fullname  user_name,
                   a.dt        mod_date
              INTO #last_mod
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
              JOIN audit_trail a
                ON a.document = d.id
              JOIN usr u
                ON u.id = a.usr
              JOIN action
                ON action.id = a.action
             WHERE a.dt BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
               AND d.active_status = 'A'
               AND u.name LIKE '%s'
               AND action.name IN ('ADD DOCUMENT', 'MODIFY DOCUMENT')
               AND a.dt = (SELECT MAX(dt)
                             FROM audit_trail a
                             JOIN action
                               ON action.id = a.action
                            WHERE document = d.id
                              AND action.name IN ('ADD DOCUMENT', 
                                                  'MODIFY DOCUMENT'))
               %s""" % (fromDate, toDate, modUser, dtQual), timeout = 120)
    cursor.execute("""\
            SELECT v.id              doc_id, 
                   MAX(v.updated_dt) pub_ver_date
              INTO #last_publishable_version
              FROM doc_version v
              JOIN #last_mod m
                ON m.doc_id = v.id
             WHERE v.publishable = 'Y'
          GROUP BY v.id""", timeout = 120)
    cursor.execute("""\
            SELECT v.id              doc_id, 
                   MAX(v.updated_dt) unpub_ver_date
              INTO #last_unpublishable_version
              FROM doc_version v
              JOIN #last_mod m
                ON m.doc_id = v.id
             WHERE v.publishable = 'N'
          GROUP BY v.id""", timeout = 120)
    cursor.execute("""
   SELECT DISTINCT d.doc_type,
                   d.doc_id,
                   p.pub_ver_date,
                   d.user_name,
                   d.mod_date,
                   u.unpub_ver_date
              FROM #last_mod d
              JOIN #last_publishable_version p
                ON d.doc_id = p.doc_id
   LEFT OUTER JOIN #last_unpublishable_version u
                ON u.doc_id = d.doc_id
             WHERE p.pub_ver_date < d.mod_date
          ORDER BY d.doc_type,
                   d.mod_date,
                   d.user_name""", timeout = 120)
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
   <br />
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
    cdrcgi.sendPage(html + u"""\
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
    <td align='center' nowrap='1'><font size='3'>%s</font></td>
    <td align='center'><font size='3'>%s</font></td>
    <td align='center'><font size='3'>%s</font></td>
   </tr>
""" % (docId, mungeDate(pubDate), modBy, mungeDate(modDate), 
       mungeDate(nonPubVerDate))

#----------------------------------------------------------------------
# Finish and send the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + u"""\
  </table>
 </body>
</html>
""")
