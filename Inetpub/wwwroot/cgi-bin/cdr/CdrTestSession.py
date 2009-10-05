#----------------------------------------------------------------------
#
# $Id: CdrTestSession.py,v 1.1 2006-05-04 14:42:07 bkline Exp $
#
# Stub login/logout to support testing of CDR Loader without access to
# port 2019.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Import required modules.
#----------------------------------------------------------------------
import cgi, cdr

#----------------------------------------------------------------------
#----------------------------------------------------------------------
# Load the fields from the form.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = fields and fields.getvalue("Session") or None
action     = fields and fields.getvalue("action")  or None
uid        = fields and fields.getvalue("uid")     or None
pwd        = fields and fields.getvalue("pwd")     or None

#----------------------------------------------------------------------
# Reply to the client.
#----------------------------------------------------------------------
def reply(message):
    print """\
Content-type: text/plain

%s""" % message
    
#----------------------------------------------------------------------
# Log in if we have uid and pwd.
#----------------------------------------------------------------------
if uid and pwd and action == 'login':
    reply(cdr.login(uid, pwd))
    
#----------------------------------------------------------------------
# Otherwise, logout.
#----------------------------------------------------------------------
elif session and action == 'logout':
    reply(cdr.logout(session) or "OK")
    
#----------------------------------------------------------------------
# Something's wrong.
#----------------------------------------------------------------------
else:
    reply("Expected logout (with session) or login (with user ID/password).")
