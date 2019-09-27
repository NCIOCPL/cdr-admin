#----------------------------------------------------------------------
#
# Web front end for document deletion.  The documents aren't actually
# deleted, but instead their active_status column is set to 'D'.
#
# BZIssue::5296
#
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, re
from cdrapi import db
from html import escape as html_escape

LOGNAME = "del-some-docs"
LOGFILE = f"{cdr.DEFAULT_LOGDIR}/{LOGNAME}.log"
LOGGER = cdr.Logging.get_logger(LOGNAME)

def getUserName(session):
    cursor = db.connect(user="CdrGuest").cursor()
    cursor.execute("""\
SELECT u.name
  FROM usr u
  JOIN session s
    ON s.usr = u.id
 WHERE s.name = ?""", session)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Can't find session user name")
    return rows[0][0]

fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
ids = fields.getvalue("ids")
reason = fields.getvalue("reason")
validate = fields.getvalue("validate")
if not session: cdrcgi.bail("Unknown or expired CDR session.")
html = ["""\
<!DOCTYPE html>
<html>
 <head>
  <title>CDR Document Deletion</title>
  <style type="text/css">
   h1 { font-family: Arial, sans-serif; }
   p { font-size: 12pt; }
   label { float: left; font-weight: bold; width: 150px; text-align: right;
   padding-right: 10px; }
   textarea { width: 600px; height: 100px; }
   #submit { margin-left: 160px; }
   .warning, .warning a { font-style: italic; color: #d22; }
  </style>
 </head>
 <body>
  <h1>Delete CDR Documents</h1>
  <p>Enter document IDs separated by spaces and/or line breaks.
  If you check the "Validate" box below, documents which would introduce
  link validation errors if deleted will not be deleted.  If you do not
  check this box, the validation errors will still be displayed, but
  the document deletion will be processed.
  <span class="warning">It is recommended that you run the
  <a href="LinkedDocs.py">report</a> to check for
  links to the documents you plan to delete.</span></p>
"""]
if ids:
    reason = reason or None
    validate = validate and "Y" or "N"
    userName = getUserName(session)
    LOGGER.info("del-some-docs.py: session %r", session)
    LOGGER.info("del-some-docs.py: user name: %r" % userName)
    LOGGER.info("del-some-docs.py: validate: %s" % validate)
    LOGGER.info("del-some-docs.py: reason: %r" % reason)
    html.append("<p>Deletions:<ul>")
    #html.append("<p>reason: %s; validate: %s</p><ul>" % (reason, validate))
    ids = re.split("\\s+", ids.strip())
    for i in ids:
        try:
            docId = cdr.normalize(i)
        except Exception as e:
            html.append("<li>%s: %r</li>" % (html_escape(i), e))
            LOGGER.exception("Bad ID: %r", i)
            continue
        try:
            opts = dict(validate=validate, reason=reason)
            result = cdr.delDoc(session, docId, **opts)
        except Exception as e:
            html.append("<li>%s: %s</li>" % (docId, e))
            LOGGER.exception("Failure deleting %r", docId)
            continue
        if result == docId:
            html.append("<li>%s: OK</li>" % docId)
            LOGGER.info("%s: deleted", docId)
        elif type(result) is list:
            html.append("<li>%s:<ul>" % docId)
            for error in result:
                html.append("<li>%s</li>" % html_escape(error))
                LOGGER.error("%s: %s", docId, error)
            html.append("</ul></li>")
        else:
            html.append("<li>%s: %r</li>" % (docId, result))
            LOGGER.info("%s: %r", docId, result)
    html.append("</ul>")
html.append("""\
<form method="POST" action="del-some-docs.py" accept-charset="utf-8">
<input type="hidden" name="Session" value="%s" />
<label for="ids">Document IDs</label>
<textarea id="ids" name="ids"></textarea><br />
<label for="reason">Reason (optional)</label>
<textarea id="reason" name="reason"></textarea><br />
<label for="validate">Validate?</label>
<input id="validate" name="validate" type="checkbox" />
(please read the instructions above)
<br />
<br />
<input id="submit" type="Submit" value="Delete Documents" />
</form>
""" % session)
html.append("</body></html>")
cdrcgi.sendPage("\n".join(html))
