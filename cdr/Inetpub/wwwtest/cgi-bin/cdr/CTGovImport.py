#----------------------------------------------------------------------
#
# $Id: CTGovImport.py,v 1.2 2003-11-25 12:45:47 bkline Exp $
#
# User interface for selecting Protocols to be imported from
# ClinicalTrials.gov.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/11/10 17:57:34  bkline
# User interface for reviewing protocol documents downloaded from
# ClinicalTrials.gov to determine their disposition.
#
#----------------------------------------------------------------------
import cdr, cdrbatch, cgi, cdrcgi, cdrdb

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
def showList(skipPast, cursor):

    # Handle new docs and those waiting for CIPS feedback differently.
    if which == 'new':
        subtitle = "Review and select new documents for import"
        disposition = 'not yet reviewed'
    else:
        subtitle = "Review and select documents awaiting CIPS feedback"
        disposition = 'reviewed - need CIPS feedback'
        
    # Construct display headers in standard format
    html = cdrcgi.header ("CDR Import from ClinicalTrials.gov",
                          "Import CTGov Documents",
                          subtitle,
                          "CTGovImport.py",
                          stylesheet = """\
  <script>
	function openWindow(pageURL) {
		windowName=window.open(pageURL,'ctgov')
	}
  </script>
""")
    # Add saved session
    html += """
    <input type='hidden' name='%s' value='%s' />
    <input type='hidden' name='which' value='%s' />
""" % (cdrcgi.SESSION, session, which)

    try:
        cursor.execute("""\
    SELECT TOP 20 c.nlm_id, c.title, d.name
      FROM ctgov_import c
      JOIN ctgov_disposition d
        ON d.id = c.disposition
     WHERE c.nlm_id > '%s'
       AND d.name = '%s'
  ORDER BY c.nlm_id""" % (skipPast, disposition))
        rows = cursor.fetchall()
        if len(rows) < 20:
            cursor.execute("""\
    SELECT TOP 20 c.nlm_id, c.title, d.name
      FROM ctgov_import c
      JOIN ctgov_disposition d
        ON d.id = c.disposition
     WHERE d.name = '%s'
  ORDER BY c.nlm_id DESC""" % disposition)
            rows = cursor.fetchall()
            if rows:
                rows.reverse()
    except Exception, info:
        cdrcgi.bail("Failure retrieving documents for review: %s" % str(info))

    if not rows:
        cdrcgi.bail("No documents awaiting review")
    html += "<input type='hidden' name='numRows' value='%d'>\n" % len(rows)
    html += "<input type='hidden' name='skipCur' value='%s'>\n" % skipCur
    html += "<input type='hidden' name='skipNext' value='%s'>\n" % rows[-1][0]

    n = 0
    if which == 'new':
        values = ('Import', 'Out of scope', 'Duplicate',
                  'Reviewed - Need CIPS Feedback')
    else:
        values = ('Import', 'Out of scope', 'Duplicate')
    html += "<span style='font-family: arial'>\n"
    base = "http://clinicaltrials.gov/ct/show/"
    for row in rows:
        href = 'javascript:openWindow("%s%s")' % (base, row[0])
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
        html += "<br><br>\n"
        n += 1

    html += "</span><center><input type='submit' name='Apply' value='Apply' />"
    html += "&nbsp;&nbsp;<input type='submit' name='Next' value='Next' /></center>"

    # Display the page and exit
    cdrcgi.sendPage (html + "</form></body></html>")

def applyChoices(cursor, conn):
    n = int(numRows)
    for i in range(n):
        id   = fields and fields.getvalue("id-%d" % i) or ""
        disp = fields and fields.getvalue("disp-%d" % i) or ""
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
        cursor.execute("""\
        UPDATE ctgov_import
           SET disposition = (SELECT id
                                FROM ctgov_disposition
                               WHERE name = '%s')
         WHERE nlm_id = '%s'""" % (disp, id))
        conn.commit()
conn = cdrdb.connect()
cursor = conn.cursor()
if nextPage:
    showList(skipNext, cursor)
elif apply:
    applyChoices(cursor, conn)
    showList(skipCur, cursor)
else:
    showList("", cursor)
