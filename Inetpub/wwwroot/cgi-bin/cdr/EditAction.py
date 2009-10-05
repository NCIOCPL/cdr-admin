#----------------------------------------------------------------------
#
# $Id: EditAction.py,v 1.2 2002-02-21 15:22:02 bkline Exp $
#
# Prototype for editing a CDR action.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
actName = fields and fields.getvalue("action") or None
SUBMENU = "Action Menu"

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("EditActions.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Handle request to delete the action.
#----------------------------------------------------------------------
if request == "Delete Action":
    error = cdr.delAction(session, actName)
    if error: cdrcgi.bail(error)
    cdrcgi.mainMenu(session, "Action %s Deleted Successfully" % actName)

#----------------------------------------------------------------------
# Handle request to store changes to the action.
#----------------------------------------------------------------------
if request == "Save Changes":
    name     = fields and fields.getvalue("name") or ""
    flag     = fields and fields.getvalue("doctypeSpecific") and "Y" or "N"
    comment  = fields.getvalue("comment")
    action   = cdr.Action(name, flag)
    if comment  != "None": action.comment = comment
    error = cdr.putAction(session, actName, action)
    if error: cdrcgi.bail(error)
    actName = name

#----------------------------------------------------------------------
# Retrieve and display the action information.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Manage Action Information"
buttons = ["Save Changes", "Delete Action", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "EditAction.py"
#script  = "DumpParams.pl"
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Retrieve the action's information from the server.
#----------------------------------------------------------------------
if not actName: action = cdr.Action("", "N")
else:           action = cdr.getAction(session, actName)
if type(action) == type(""): cdrcgi.bail(action)

#----------------------------------------------------------------------
# Display the information for the action.
#----------------------------------------------------------------------
flag = action.doctypeSpecific == 'Y' and "CHECKED" or ""
form = """\
<H2>%s</H2>%s
<B>Action Name:&nbsp;<INPUT NAME='name' VALUE='%s'><BR>
<INPUT TYPE='checkbox' NAME='doctypeSpecific' %s>
Action Authorized For Individual Document Types?<BR>
<H3>Description</H3>
<TEXTAREA COLS='80' ROWS='8' NAME='comment'>%s</TEXTAREA>
""" % (action.name, 
       request == "Save Changes" and "\n<H4>(Successfully Updated)</H4>" or "",
       action.name, flag, action.comment)

#----------------------------------------------------------------------
# Add the session key and send back the form.
#----------------------------------------------------------------------
form += """\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
<INPUT TYPE='hidden' NAME='action' VALUE='%s' >
""" % (cdrcgi.SESSION, session, action.name)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
