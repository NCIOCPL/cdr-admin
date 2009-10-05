#----------------------------------------------------------------------
#
# $Id: EditGroup.py,v 1.3 2002-07-31 19:03:10 bkline Exp $
#
# Prototype for editing a CDR group.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/02/21 15:22:02  bkline
# Added navigation buttons.
#
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
grpName = fields and fields.getvalue("grp") or None
SUBMENU = "Group Menu"

#----------------------------------------------------------------------
# Make sure we have an active session.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("EditGroups.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Handle request to delete the group.
#----------------------------------------------------------------------
if request == "Delete Group":
    error = cdr.delGroup(session, grpName)
    if error: cdrcgi.bail(error)
    cdrcgi.mainMenu(session, "Group %s Deleted Successfully" % grpName)

#----------------------------------------------------------------------
# Handle request to store changes to the group.
#----------------------------------------------------------------------
if request == "Save Changes":
    name  = fields and fields.getvalue("name") or ""
    group = cdr.Group(name)
    users = fields and fields.getvalue("users") or []
    if type(users) == type([]): group.users = users
    else:                       group.users = [users]
    comment = fields.getvalue("comment")
    if comment != "None": group.comment = comment
    actions = fields.getvalue("actions")
    if actions:
        if type(actions) == type(""): actions = [actions]
        for action in actions:
            pair = action.split("::")
            if len(pair) == 2: (action, doctype) = pair
            else:              (action, doctype) = (pair[0], None)
            if not group.actions.has_key(action): group.actions[action] = []
            if doctype: group.actions[action].append(doctype)
    error = cdr.putGroup(session, grpName, group)
    if error: cdrcgi.bail(error)
    grpName = name

#----------------------------------------------------------------------
# Retrieve and display the group information.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Edit Group Information"
buttons = ["Save Changes", "Delete Group", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "EditGroup.py"
#script  = "DumpParams.pl"
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Populate the group object.
#----------------------------------------------------------------------
if not grpName: group = cdr.Group("")
else:           group = cdr.getGroup(session, grpName)
    
#----------------------------------------------------------------------
# Retrieve the related information we need from the server.
#----------------------------------------------------------------------
actions  = cdr.getActions(session)
users    = cdr.getUsers(session)
doctypes = cdr.getDoctypes(session)
if type(group)    == type(""): cdrcgi.bail(group)
if type(actions)  == type(""): cdrcgi.bail(actions)
if type(users)    == type(""): cdrcgi.bail(users)
if type(doctypes) == type(""): cdrcgi.bail(doctypes)

#----------------------------------------------------------------------
# Display the information for the group.
#----------------------------------------------------------------------
form = """\
<H2>%s</H2>%s
<H3>Group Name</H3>
<INPUT NAME='name' SIZE='40' VALUE='%s'>
<H3>Description</H3>
<TEXTAREA NAME='comment' COLS='80' ROWS='4'>%s</TEXTAREA>
""" % (group.name, 
       request == "Save Changes" and "\n<H4>(Successfully Updated)</H4>" or "",
       group.name, group.comment)

#----------------------------------------------------------------------
# List the users which can be assigned to the group.
#----------------------------------------------------------------------
form += "<H3>Users</H3>\n<TABLE>\n"
nUsers = 0
USERS_PER_ROW = 6
for user in users:
    if nUsers % USERS_PER_ROW == 0:
        form += "<TR><TD>&nbsp;&nbsp;</TD>"
    flag = user in group.users and "CHECKED\n" or ""
    url = "%s/EditUser.py?usr=%s&%s=%s" % (cdrcgi.BASE, 
                                           user,
                                           cdrcgi.SESSION,
                                           session)
    form += """\
<TD><INPUT TYPE='checkbox' 
           VALUE='%s' 
           %sNAME='users'><A HREF="%s">%s</A></INPUT></TD>
""" % (user, flag, url, user)
    nUsers += 1
    if nUsers % USERS_PER_ROW == 0: form += "</TR>\n"
form += "</TABLE>\n"

#----------------------------------------------------------------------
# Add the actions for which the group can be authorized.
#----------------------------------------------------------------------
form += "<H3>Actions</H3>\n"

#----------------------------------------------------------------------
# Add the actions independent of specific document types.
#----------------------------------------------------------------------
form += """\
<H4>Not Specific To Any Document Type</H4>
<TABLE>
"""
nActions = 0
ACTIONS_PER_ROW = 5
actionKeys = list(actions.keys())
actionKeys.sort()
for actionKey in actionKeys:
    if actions[actionKey] != 'Y':
        if nActions % ACTIONS_PER_ROW == 0:
            form += "<TR><TD>&nbsp;&nbsp;</TD>"
        flag = group.actions.has_key(actionKey) and "CHECKED\n" or ""
        form += """\
<TD><INPUT TYPE='checkbox'
           VALUE='%s'
           %sNAME='actions'>%s</INPUT></TD>
""" % (actionKey, flag, actionKey)
        nActions += 1
        if nActions % ACTIONS_PER_ROW == 0: form += "</TR>\n"
form += "</TABLE>\n"

#----------------------------------------------------------------------
# Add the actions specific to individual document types.
#----------------------------------------------------------------------
DOCTYPES_PER_ROW = 7
for actionKey in actionKeys:
    if actions[actionKey] == 'Y':
        grpAction = None
        if group.actions.has_key(actionKey):
            grpAction = group.actions[actionKey]
        form += "<H4>%s</H4>\n<TABLE>\n" % actionKey
        nDoctypes = 0
        for doctype in doctypes:
            if doctype == "ProtocolSourceDoc": continue
            if nDoctypes % DOCTYPES_PER_ROW == 0:
                form += "<TR><TD>&nbsp;&nbsp;</TD>"
            flag = ""
            if grpAction and doctype in grpAction:
                flag = "CHECKED\n"
            form += """\
<TD><INPUT TYPE='checkbox'
           VALUE='%s::%s'
           %sNAME='actions'>%s</INPUT></TD>
""" % (actionKey, doctype, flag, doctype)
            nDoctypes += 1
            if nDoctypes % DOCTYPES_PER_ROW == 0: form += "</TR>\n"
        form += "</TABLE>\n"

#----------------------------------------------------------------------
# Add the session key and send back the form.
#----------------------------------------------------------------------
form += """\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
<INPUT TYPE='hidden' NAME='grp' VALUE='%s'>
""" % (cdrcgi.SESSION, session, group.name)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
