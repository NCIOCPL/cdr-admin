#!/usr/bin/env python

# ----------------------------------------------------------------------
# Determine whether an account is allowed to perform a CDR action.
# JIRA::OCECDR-4107 - require authorization for viewing GP emailer list
# ----------------------------------------------------------------------

import cdr
from cdrapi import db
from cdrcgi import FieldStorage

LOGNAME = "check-auth"
LOGFILE = f"{cdr.DEFAULT_LOGDIR}/{LOGNAME}.log"
LOGGER = cdr.Logging.get_logger(LOGNAME)


def answer(yn):
    print(f"""\
Content-type: text/plain

{yn}""")


fields = FieldStorage()
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
except Exception:
    try:
        LOGGER.exception("check-auth failure")
    finally:
        answer("N")
