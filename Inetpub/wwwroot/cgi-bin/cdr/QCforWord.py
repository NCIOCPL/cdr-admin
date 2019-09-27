#-----------------------------------------------------------------------------
# When the users are converting a QC report to MS-Word the report is
# rerun using a GET with the URL.  However, the length of the URL that
# Word can handle is limited to around 300 characters - not enough if
# many parameters have been selected.
# This program will retrieve the parameters from a database table to
# circumvent Word's limitation.
#
# BZIssue::5178 - [Summaries] Shorter URLS Needed For Successful
#                 Conversion of QC Reports into Word
# ----------------------------------------------------------------------------
import cgi
import sys
import cdr
import cdrcgi
from cdrapi import db

# ----------------------------------------------------------------
# Retrieve row of parameters from DB table to pass to filter a
# document.
# ----------------------------------------------------------------
def getParms(id):
    try:
        cursor.execute("""\
     SELECT longURL from url_parm_set
      WHERE id = ?""", id)
        rows = cursor.fetchall()
    except Exception as e:
        cdrcgi.bail(f"Failure selecting parms: {e}")

    return eval(rows[0][0])

def sendPage(page, textType='html', location='', docType=''):
    """
    Send a completed page of text to stdout, assumed to be piped by a
    webserver to a web browser.

    Pass:
        page     - Text to send, assumed to be 16 bit unicode.
        textType - HTTP Content-type, assumed to be html.

    Return:
        No return.  After writing to the browser, the process exits.
    """
    sys.stdout.buffer.write(f"""\
Content-type: text/{textType};charset=utf-8

{page}""".encode("utf-8"))
    sys.exit(0)


#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
repTitle = "CDR QC Report"
fields   = cgi.FieldStorage()
docId    = fields.getvalue(cdrcgi.DOCID) or None
session  = cdrcgi.getSession(fields) or "guest"
qcParms  = fields.getvalue('parmstring') or 'no'
qcParmId = fields.getvalue('parmid') or '-1'


SUBMENU  = "Reports Menu"
docType  = fields.getvalue("DocType")    or None
version  = fields.getvalue("DocVersion") or None

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = db.connect(user='CdrGuest')
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail(f"Database connection failure: {e}")

if qcParms == 'yes':
    myParm = getParms(int(qcParmId))
    doc = cdr.filterDoc(session, cdr.FILTERS[docType], docId = docId,
                    docVer = version or None, parm = myParm)
    sendPage(doc[0])
else:
    cdrcgi.bail('No parameters found for qcParmId=%s' % qcParmId)

sys.exit(0)
