#!/usr/bin/env python

# ----------------------------------------------------------------------
# Return json-encoded dump of the client DLL trace logs, used to
# track down what might be causing XMetaL to lock up or crash.
# ----------------------------------------------------------------------
from json import dumps
from cdrapi import db
from cdrcgi import FieldStorage

FIELDS = "log_id", "log_saved", "cdr_user", "session_id", "log_data"

fields = FieldStorage()
after = fields.getvalue("after")
before = fields.getvalue("before")
query = db.Query("dll_trace_log", *FIELDS).order(2)
if after:
    query.where(query.Condition("log_saved", after, ">="))
if before:
    query.where(query.Condition("log_saved", before, "<"))
rows = query.execute().fetchall()
logs = []
for log_id, log_saved, cdr_user, session_id, log_data in rows:
    logs.append((log_id, str(log_saved), cdr_user, session_id, log_data))
print("Content-type: text/json")
print(f"X-Content-Type-Options: nosniff\n\n{dumps(logs, indent=2)}")
