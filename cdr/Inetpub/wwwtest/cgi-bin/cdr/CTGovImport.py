#----------------------------------------------------------------------
#
# $Id: CTGovImport.py,v 1.5 2004-02-16 23:40:57 bkline Exp $
#
# User interface for selecting Protocols to be imported from
# ClinicalTrials.gov.
#
# $Log: not supported by cvs2svn $
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
skipCur  = fields and fields.getvalue("skipCur") or ""
skipNext = fields and fields.getvalue("skipNext") or ""
nextPage = fields and fields.getvalue("Next") or ""
apply    = fields and fields.getvalue("Apply") or ""
which    = fields and fields.getvalue("which") or "new"
numRows  = fields and fields.getvalue("numRows") or "0"

if fields and fields.getvalue ("cancel", None):
    # Cancel button pressed.  Return user to admin screen
    cdrcgi.navigateTo ("Admin.py", session)

if not session and 0:
    cdrcgi.bail ("Unknown or expired CDR session.")

# If new request or no input parms, we need to output a form
def showList(skipPast, cursor, errors = None):

    # Handle new docs and those waiting for CIPS feedback differently.
    if which == 'new':
        subtitle = "Review and select new documents for import"
        disposition = 'not yet reviewed'
    else:
        subtitle = "Review and select documents awaiting CIPS feedback"
        disposition = 'reviewed - need CIPS feedback'
        
    # Construct display headers in standard format
    timeStr = str(time.time()).replace(".", "")
    timeStr = ''.join([timeStr[-1 - i] for i in xrange(len(timeStr))])
    html = cdrcgi.header ("CDR Import from ClinicalTrials.gov",
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
   .err { font-family: Arial; color: red; font-size: 14pt; font-weight: bold; }
  </style>
""" % timeStr)
    # Add saved session
    html += """
    <input type='hidden' name='%s' value='%s' />
    <input type='hidden' name='which' value='%s' />
""" % (cdrcgi.SESSION, session, which)

    for error in errors:
        html += u"""\
    <span class='err'>%s</span><br>
""" % error
    if errors:
        html += u"""\
    <br>
"""
    where = ""
    if skipPast:
        where = "WHERE c.nlm_id < '%s'" % skipPast
    try:
        cursor.execute("""\
    SELECT TOP 20 c.nlm_id, c.title, d.name
      FROM ctgov_import c
      JOIN ctgov_disposition d
        ON d.id = c.disposition
     %s
       AND d.name = '%s'
  ORDER BY c.nlm_id DESC""" % (where, disposition))
        rows = cursor.fetchall()

        #------------------------------------------------------------
        # If we ran out of rows before the end, get the last 20 rows.
        #------------------------------------------------------------
        if len(rows) < 20:
            cursor.execute("""\
    SELECT TOP 20 c.nlm_id, c.title, d.name
      FROM ctgov_import c
      JOIN ctgov_disposition d
        ON d.id = c.disposition
       AND d.name = '%s'
  ORDER BY c.nlm_id""" % disposition)
            rows = cursor.fetchall()
            if rows:
                rows.reverse()
    except Exception, info:
        cdrcgi.bail("Failure retrieving documents for review: %s" % str(info))

    if not rows:
        cdrcgi.bail("No documents awaiting review")
    html += "<input type='hidden' name='numRows' value='%d'>\n" % len(rows)
    html += "<input type='hidden' name='skipCur' value='%s'>\n" % skipPast
    html += "<input type='hidden' name='skipNext' value='%s'>\n" % rows[-1][0]

    n = 0
    if which == 'new':
        values = ('Import', 'Out of scope', 'Duplicate',
                  'Reviewed - Need CIPS Feedback')
    else:
        values = ('Import', 'Out of scope', 'Duplicate')
    html += "<span style='font-family: arial'>\n"
    for row in rows:
        href = 'javascript:openWindow("%s")' % row[0]
        html += "<b><a href='%s'>%s</a></b> <i>%s</i><br>\n" % (href, #base,
                                                                  #row[0],
                                                                  row[0],
                                                       cgi.escape(row[1]))
        html += "<input type='hidden' name='id-%d' value='%s'>\n" % (n, row[0])
        checked = ""#" checked='1'"
        for i in range(len(values)):
            checked = (values[i] == 'Reviewed - Need CIPS Feedback' and
                       row[2] == 'reviewed - need CIPS feedback' and
                       " checked='1'" or "")
            html += ("&nbsp;&nbsp;<input type='radio' name='disp-%d'"
                     "value='%d'%s>&nbsp;%s\n" % (n, i + 1, checked,
                                                  values[i]))
            if values[i] == 'Duplicate':
                html += "of CDR ID <input name='cdrid-%d'>&nbsp;" % n
        html += "<br><br>\n"
        n += 1

    html += "</span><center><input type='submit' name='Apply' value='Apply' />"
    html += "&nbsp;&nbsp;<input type='submit' name='Next' value='Next' /></center>"

    # Display the page and exit
    cdrcgi.sendPage (html + "</form></body></html>")

def applyChoices(cursor, conn):
    n = int(numRows)
    errors = []
    for i in range(n):
        id    = fields and fields.getvalue("id-%d" % i) or ""
        disp  = fields and fields.getvalue("disp-%d" % i) or ""
        cdrId = fields and fields.getvalue("cdrid-%d" % i) or ""
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
if nextPage:
    showList(skipNext, cursor)
elif apply:
    errors = applyChoices(cursor, conn)
    showList(skipCur, cursor, errors)
else:
    showList("", cursor)
