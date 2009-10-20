#----------------------------------------------------------------------
#
# $Id$
#
# CGI interface for reviewing trials NLM stopped sending us for which
# we don't yet have an explanation for the drop.  Can be used for
# supplying the reason for storage in the reason_dropped column of
# the ctgov_import table when CIAT determines what that explanation is.
#
# BZIssue::4575
#
#----------------------------------------------------------------------
import cgi, cdrdb, cdrcgi

fields = cgi.FieldStorage()
nlmId  = fields.getvalue('nlmid')
reason = fields.getvalue('reason')
conn   = cdrdb.connect()
cursor = conn.cursor()
def showReport(extra):
    cursor.execute("""\
        SELECT nlm_id, cdr_id, title
          FROM ctgov_import
         WHERE reason_dropped IS NULL
           AND dropped = 'Y'
      ORDER BY nlm_id""")
    report = [u"""\
<html>
 <head>
  <title>Trials Dropped by NLM</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif }
   h1 { color: maroon; font-size: 16pt }
   th { color: green }
  </style>
  <script type='text/javascript'>
   function addReason(nlmId) {
       var form = document.forms[0];
       form.nlmid.value = nlmId;
       form.submit();
   }
  </script>
 </head>
 <body>
  %s
  <h1>Trials Dropped by NLM</h1>
  <form action='DroppedByNlm.py' method='post'>
  <input type='hidden' name='nlmid' value='' />
   <table border='1' cellpadding='2' cellspacing='0'>
    <tr>
     <th>NCT ID</th>
     <th>CDR ID</th>
     <th>Title</th>
     <th>Action</th>
    </tr>
""" % extra]
    for nlmId, cdrId, title in cursor.fetchall():
        report.append(u"""\
    <tr>
     <td>%s</td>
     <td>%s</td>
     <td>%s</td>
     <td><input type='button' onclick='javascript:addReason("%s");'
                value='Add Reason' /></td>
    </tr>
""" % (nlmId, cdrId and (u"CDR%d" % cdrId) or u"&nbsp;",
       title and cgi.escape(title) or u"&nbsp;", nlmId))
    report.append(u"""\
   </table>
  </form>
 </body>
</html>
""")
    cdrcgi.sendPage(u"".join(report))

def addReason(nlmId, reason):
    cursor.execute("""\
        UPDATE ctgov_import
           SET reason_dropped = ?
         WHERE nlm_id = ?""", (reason, nlmId))
    conn.commit()
    showReport(u"<div style='color:green'>Reason set for %s</div>" % nlmId)

def showForm(nlmId):
    cdrcgi.sendPage(u"""\
<html>
 <head>
  <title>Trials Dropped by NLM</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif }
   h1 { color: maroon; font-size: 16pt }
   th { color: green }
  </style>
 </head>
 <body>
  <h1>Trial %s</h1>
  <form method='post' action='DroppedByNlm.py'>
   <input type='hidden' value='%s' name='nlmid' />
   <b>Enter the reason NLM dropped this trial</b>
   <input name='reason' size='80' />
   <input type='submit' value='Submit Reason' />
  </form>
 </body>
</html>""" % (nlmId, nlmId))

if nlmId:
    if reason:
        addReason(nlmId, reason)
    else:
        showForm(nlmId)
else:
    showReport(u"")
