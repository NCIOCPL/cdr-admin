#----------------------------------------------------------------------
# Dump the server environment variables as json. Requires permission.
#----------------------------------------------------------------------
import cgi
import json
import os
import cdr
import cdrcgi

fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
if not session or not cdr.canDo(session, "GET SYS CONFIG"):
    cdrcgi.bail("go away")
environ = dict(os.environ)
print "Content-type: application/json\n\n%s" % json.dumps(environ, indent=2)
