#----------------------------------------------------------------------
#
# $Id$
#
# User interface for selecting Protocols to be imported from
# ClinicalTrials.gov.
#
#----------------------------------------------------------------------
import cdr, cdrbatch, cgi, cdrcgi, cdrdb, time

NOT_YET_REVIEWED = 'not yet reviewed'
NEED_CIPS_FEEDBACK = 'reviewed - need CIPS feedback'

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
    def __init__(self, nlmId, title, received, phase, ctrpId, haveCtrp):
        self.nlmId    = nlmId
        self.title    = title
        self.received = str(received)[:10]
        self.phase    = phase
        self.ctrpId   = ctrpId
        self.haveCtrp = haveCtrp
    def __cmp__(self, other):
        diff = cmp(self.received, other.received)
        if diff:
            return diff
        return cmp(other.phase, self.phase)

# If new request or no input parms, we need to output a form
def showList(cursor, errors = None, extra = None):

    # Handle new docs and those waiting for CIPS feedback differently.
    if which == 'new':
        subtitle = "Review and select new documents for import"
        disposition = NOT_YET_REVIEWED
    else:
        subtitle = "Review and select documents awaiting OCCM feedback"
        disposition = NEED_CIPS_FEEDBACK
        
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
   .msg { color: green; font-size: 14pt; font-weight: bold; }
   td a.ctrp { text-decoration: underline; font-weight: bold; color: maroon; }
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
    if extra:
        for message in extra:
            html.append(u"""\
   <span class='msg'>%s</span><br>
""" % message)
        html.append(u"""\
   <br />
""")
    try:
        cursor.execute("""\
         SELECT n.nlm_id, n.title, n.downloaded, n.phase, n.ctrp_id, c.ctrp_id
           FROM ctgov_import n
           JOIN ctgov_disposition d
             ON d.id = n.disposition
            AND d.name = '%s'
LEFT OUTER JOIN ctrp_import c
             ON n.ctrp_id = c.ctrp_id""" % disposition, timeout=300)
        rows = cursor.fetchall()
        
    except Exception, info:
        cdrcgi.bail("Failure retrieving documents for review: %s" % str(info))

    protocols = []
    if rows:
        for row in rows:
            haveCtrp = row[5] is not None
            protocol = CTGovProtocol(row[0], row[1], row[2], row[3], row[4],
                                     haveCtrp)
            protocols.append(protocol)
        protocols.sort()
    
    html.append(u"""
   <input type='hidden' name='numRows' value='%d'>
   <h3>Trials to be reviewed: %d</h3>
   <table border='1' cellspacing='0' cellpadding='2'>
""" % (len(protocols), len(protocols)))

    n = 0
    ctrpTemplate = u'<a class="ctrp" href="%s" target="_blank">%s</a>'
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
        ctrp = u"&nbsp;"
        if protocol.ctrpId:
            if protocol.haveCtrp:
                url = "show-ctrp-doc.py?id=%s" % protocol.ctrpId
                ctrp = ctrpTemplate % (url, protocol.ctrpId)
            else:
                ctrp = protocol.ctrpId
        html.append(u"""\
    <tr>
     <td><b><a href='%s'>%s</a></b></td>
     <td>%s</td>
     <td><i>%s</i></td>
     <td>%s</td>
     <td>%s</td>
     <td width='300'>
%s
     </td>
    </tr>
""" % (href, protocol.nlmId, ctrp, cgi.escape(protocol.title),
       protocol.phase or u"No phase specified",
       protocol.received, inputFields))
        n += 1
    submitButton = u""
    if protocols:
        submitButton = u"<input type='submit' name='Apply' value='Apply' />"
    html.append(u"""\
   </table>
   <br />
   <center>%s</center>
  </form>
 </body>
</html>
""" % submitButton)
    # Display the page and exit
    cdrcgi.sendPage(u"".join(html))

def applyChoices(cursor, conn):
    n = int(numRows)
    errors = []
    extra  = []
    default = (which == 'new') and NOT_YET_REVIEWED or NEED_CIPS_FEEDBACK
    for i in range(n):
        id    = fields.getvalue("id-%d" % i) or ""
        disp  = fields.getvalue("disp-%d" % i) or ""
        cdrId = fields.getvalue("cdrid-%d" % i) or ""
        #cdrcgi.bail("i=%d id=%s disp=%s" % (i, id, disp))
        if not disp:
            disp = default #"not yet reviewed"
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
        if disp == default:
            continue
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
            conn.commit()
            extra.append(u"%s marked as duplicate of CDR%d" % (id, intId))
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
            extra.append(u"%s marked as '%s'" % (id, disp))
    return errors, extra
conn = cdrdb.connect()
cursor = conn.cursor()
errors, extra = applyChoices(cursor, conn)
showList(cursor, errors, extra)
