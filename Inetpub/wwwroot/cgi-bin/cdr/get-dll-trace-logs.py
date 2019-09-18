#----------------------------------------------------------------------
# Return json-encoded dump of the client DLL trace logs, used to
# track down what might be causing XMetaL to lock up or crash.
#----------------------------------------------------------------------
from json import dumps
from cdrapi import db

fields = "log_id", "log_saved", "cdr_user", "session_id", "log_data"
rows = db.Query("dll_trace_log", *fields).execute().fetchall()
logs = []
for log_id, log_saved, cdr_user, session_id, log_data in rows:
    logs.append((log_id, str(log_saved), cdr_user, session_id, log_data))
print("Content-type: text/json\n\n" + dumps(logs, indent=2))
