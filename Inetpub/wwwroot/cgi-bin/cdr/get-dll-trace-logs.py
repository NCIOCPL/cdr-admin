#----------------------------------------------------------------------
# Return json-encoded dump of the client DLL trace logs, used to
# track down what might be causing XMetaL to lock up or crash.
#----------------------------------------------------------------------
import json
import cdrdb2 as cdrdb

fields = "log_id", "log_saved", "cdr_user", "session_id", "log_data"
rows = cdrdb.Query("dll_trace_log", *fields).execute().fetchall()
logs = []
for log_id, log_saved, cdr_user, session_id, log_data in rows:
    logs.append((log_id, str(log_saved), cdr_user, session_id, log_data))
print "Content-type: text/json\n\n" + json.dumps(logs)
