#----------------------------------------------------------------------
# Initiate a new CDR Session using the user's NIH domain account login
# and redirects to the top level CDR Admin menu.
# JIRA::OCECDR-3849
# JIRA::OCECDR-4092
#----------------------------------------------------------------------
import cgi
import os
import cdrlite
import datetime

fields = cgi.FieldStorage()
target = fields.getvalue("target") or "cgi-bin/cdr/admin.py"
session = None
auth_user = os.environ.get("AUTH_USER")
webserver = os.environ.get("SERVER_NAME")
if auth_user:
    domain, name = auth_user.split("\\")
    if domain.upper() == "NIH":
        try:
            session = cdrlite.login(name)
        except:
            session = False
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
try:
    strings = (now, repr(auth_user), repr(session), target)
    fp = open("d:/cdr/log/admin-login.log", "a")
    fp.write("%s admin.py %s %s %s\n" % strings)
    fp.close()
except:
    pass
if session:
    if "//" not in target:
        target = "https://%s/%s" % (webserver, target.lstrip("/"))
    delimiter = ("?" in target) and "&" or "?"
    url = "%s%sSession=%s" % (target, delimiter, session)
    print "Location: %s\n" % url
else:
    print "Status: 401 Unauthorized\n"
