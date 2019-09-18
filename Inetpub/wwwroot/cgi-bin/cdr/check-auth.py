#----------------------------------------------------------------------
# Determine whether an account is allowed to perform a CDR action.
# JIRA::OCECDR-4107 - require authorization for viewing GP emailer list
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
from cdrapi import db

LOGFILE = cdr.DEFAULT_LOGDIR + "/check-auth.log"

def answer(yn):
    print("""\
Content-type: text/plain

%s""" % yn)

fields = cgi.FieldStorage()
try:
    session = fields.getvalue("Session")
    action = fields.getvalue("action")
    doctype = fields.getvalue("doctype", "")
    query = db.Query("action", "name")
    actions = set([row[0] for row in query.execute().fetchall()])
    if action in actions and cdr.canDo(session, action, doctype):
        answer("Y")
    else:
        answer("N")
except Exception as e:
    try:
        cdr.logwrite("failure: %s" % e, LOGFILE, True, True)
    except:
        answer("N")
