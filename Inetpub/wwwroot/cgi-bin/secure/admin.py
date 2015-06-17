#----------------------------------------------------------------------
# $Id$
# Initiate a new CDR Session using the user's NIH domain account login
# and redirects to the top level CDR Admin menu.
# JIRA::OCECDR-3849
#----------------------------------------------------------------------
import os
import cdrlite
import datetime

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
    fp = open("d:/cdr/log/admin-login.log", "a")
    fp.write("%s admin.py %s %s\n" % (now, repr(auth_user), repr(session)))
    fp.close()
except:
    pass
if session:
    url = "https://%s/cgi-bin/cdr/admin.py?Session=%s" % (webserver, session)
    print "Location: %s\n" % url
else:
    print "Status: 401 Unauthorized\n"
