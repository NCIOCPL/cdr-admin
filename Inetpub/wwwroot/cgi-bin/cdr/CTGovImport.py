#----------------------------------------------------------------------
#
# $Id: CTGovImport.py,v 1.8 2007-03-23 16:40:29 bkline Exp $
#
# User interface for selecting Protocols to be imported from
# ClinicalTrials.gov.
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2007/03/22 17:53:13  bkline
# Changes for Sheri (see Bugzilla request #3015).
#
# Revision 1.6  2004/02/23 15:31:20  bkline
# Added check to make sure there are errors before we start to report them.
#
# Revision 1.5  2004/02/16 23:40:57  bkline
# Rewrote interface to allow user to specify the CDR document ID for
# duplicate trials (enhancement request #1104).
#
# Revision 1.4  2003/12/16 15:41:18  bkline
# Modified code to open NLM document in a separate window so that it
# uses a different window for each document.
#
# Revision 1.3  2003/12/08 19:23:23  bkline
# Modified code to show most recent trials first.
#
# Revision 1.2  2003/11/25 12:45:47  bkline
# Opened NLM display of document in separate window at Lakshmi's request.
#
# Revision 1.1  2003/11/10 17:57:34  bkline
# User interface for reviewing protocol documents downloaded from
# ClinicalTrials.gov to determine their disposition.
#
#----------------------------------------------------------------------
import cdr, cdrbatch, cgi, cdrcgi, cdrdb, time

# Parse form variables
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
submit   = fields and fields.getvalue("Apply") or ""
which    = fields and fields.getvalue("which") or "new"
numRows  = fields and fields.getvalue("numRows") or "0"

if fields and fields.getvalue ("cancel", None):
    # Cancel button pressed.  Return user to admin screen
    cdrcgi.navigateTo ("Admin.py", session)

if not session and False:
    cdrcgi.bail ("Unknown or expired CDR session.")

# One of these for each CT.gov trial document.
class CTGovProtocol:
    def __init__(self, nlmId, title, received, phase):
        self.nlmId    = nlmId
        self.title    = title
        self.received = str(received)[:10]
        self.phase    = phase
    def __cmp__(self, other):
        diff = cmp(self.received, other.received)
        if diff:
            return diff
        return cmp(other.phase, self.phase)

# If new request or no input parms, we need to output a form
def showList(cursor, errors = None):

    # Handle new docs and those waiting for CIPS feedback differently.
    if which == 'new':
        subtitle = "Review and select new documents for import"
        disposition = 'not yet reviewed'
    else:
        subtitle = "Review and select documents awaiting OCCM feedback"
        disposition = 'reviewed - need CIPS feedback'
        
    # Construct display headers in standard format
    timeStr = str(time.time()).replace(".", "")
    chars   = [c for c in timeStr]
    chars.reverse()
    timeStr = ''.join(chars)
    html = [cdrcgi.header ("CDR Import from ClinicalTrials.gov",
                          "Import CTGov Documents",
                          subtitle,
                          "CTGovImport.py",
                          stylesheet = """\
  <script>
    <!--
    function openWindow(id) {
        var url        = "http://clinicaltrials.gov/ct/show/" + id;
        var wn         = "ctg" + id + "%s"; // + id;
        // alert(wn);
        windowName = window.open(url, wn); //url,wn);
    }
    -->
  </script>
  <style type='text/css'>
   body { font-family: Arial; }
   h3   { font-size: 13pt; }
   .err { font-family: Arial; color: red; font-size: 14pt; font-weight: bold; }
  </style>
""" % timeStr)]
    # Add saved session
    html.append(u"""
   <input type='hidden' name='%s' value='%s' />
   <input type='hidden' name='which' value='%s' />
""" % (cdrcgi.SESSION, session, which))

    if errors:
        for error in errors:
            html.append(u"""\
   <span class='err'>%s</span><br>
""" % error)
        html.append(u"""\
   <br />
""")
    try:
        cursor.execute("""\
    SELECT c.nlm_id, c.title, c.downloaded, c.phase
      FROM ctgov_import c
      JOIN ctgov_disposition d
        ON d.id = c.disposition
       AND d.name = '%s'""" % disposition)
        rows = cursor.fetchall()
        
    except Exception, info:
        cdrcgi.bail("Failure retrieving documents for review: %s" % str(info))

    if not rows:
        cdrcgi.bail("No documents awaiting review")
    protocols = []
    for row in rows:
        protocol = CTGovProtocol(row[0], row[1], row[2], row[3])
        protocols.append(protocol)
    protocols.sort()
    
    html.append(u"""
   <input type='hidden' name='numRows' value='%d'>
   <h3>Trials to be reviewed: %d</h3>
   <table border='1' cellspacing='0' cellpadding='2'>
""" % (len(rows), len(rows)))

    n = 0
    for protocol in protocols:
        href = u'javascript:openWindow("%s")' % protocol.nlmId
        inputFields = u"""
      <input type='hidden' name='id-%d' value='%s'>
      <input type='radio' name='disp-%d' value='1'>&nbsp;
      Import&nbsp;&nbsp;
      <input type='radio' name='disp-%d' value='2'>&nbsp;
      Out of scope<br />
      <input type='radio' name='disp-%d' value='3'>&nbsp;
      Duplicate of CDR ID <input name='cdrid-%d'>
""" % (n, protocol.nlmId, n, n, n, n)
        if which == 'new':
            inputFields += u"""\
      <br />
      <input type='radio' name='disp-%d' value='4'>&nbsp;
      Reviewed - Need OCCM Feedback
""" % n
        html.append(u"""\
    <tr>
     <td><b><a href='%s'>%s</a></b></td>
     <td><i>%s</i></td>
     <td>%s</td>
     <td>%s</td>
     <td width='300'>
%s
     </td>
    </tr>
""" % (href, protocol.nlmId, cgi.escape(protocol.title),
       protocol.phase or u"No phase specified",
       protocol.received, inputFields))
        n += 1

    html.append(u"""\
   </table>
   <br />
   <center><input type='submit' name='Apply' value='Apply' />
  </form>
 </body>
</html>
""")
    # Display the page and exit
    cdrcgi.sendPage(u"".join(html))

def applyChoices(cursor, conn):
    n = int(numRows)
    errors = []
    for i in range(n):
        id    = fields.getvalue("id-%d" % i) or ""
        disp  = fields.getvalue("disp-%d" % i) or ""
        cdrId = fields.getvalue("cdrid-%d" % i) or ""
        #cdrcgi.bail("i=%d id=%s disp=%s" % (i, id, disp))
        if not disp:
            disp = "not yet reviewed"
        elif disp == "1":
            disp = "import requested"
        elif disp == "2":
            disp = "out of scope"
        elif disp == "3":
            disp = "duplicate"
        elif disp == "4":
            disp = "reviewed - need CIPS feedback"
        else:
            cdrcgi.bail("Invalid disposition code: %s" % disp)
        if disp == "duplicate":
            if not cdrId:
                errors.append(u"%s: 'duplicate' disposition requires CDR ID" %
                              id)
                continue
            normalizedId = cdr.exNormalize(cdrId)
            intId = normalizedId[1]
            cursor.execute("SELECT id FROM document WHERE id = %d" % intId)
            if len(cursor.fetchall()) != 1:
                errors.append(u"CDR%010d not found for %s" % (intId, id))
                continue
            cursor.execute("""\
                UPDATE ctgov_import
                   SET disposition = (SELECT id
                                        FROM ctgov_disposition
                                       WHERE name = '%s'),
                       cdr_id = %d
                 WHERE nlm_id = '%s'""" % (disp, intId, id))
        else:
            if cdrId:
                errors.append(u"CDR ID '%s' ignored for %s because "
                              u"disposition is not 'duplicate'" % (cdrId,
                                                                   id))
            cursor.execute("""\
                UPDATE ctgov_import
                   SET disposition = (SELECT id
                                        FROM ctgov_disposition
                                       WHERE name = '%s')
                 WHERE nlm_id = '%s'""" % (disp, id))
        conn.commit()
    return errors
conn = cdrdb.connect()
cursor = conn.cursor()
errors = applyChoices(cursor, conn)
showList(cursor, errors)
