#----------------------------------------------------------------------
# Interface for editing a CDR group.
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
grpName = fields.getvalue("grp") or None
SUBMENU = "Group Menu"

#----------------------------------------------------------------------
# Make sure we have an active session.
#----------------------------------------------------------------------
if not session: cdrcgi.bail("Unknown or expired CDR session.")

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
    if type(users) is list: group.users = users
    else:                   group.users = [users]
    comment = fields.getvalue("comment")
    if comment != "None": group.comment = comment
    actions = fields.getvalue("actions")
    if actions:
        if isinstance(actions, basestring): actions = [actions]
        for action in actions:
            pair = action.split("::")
            if len(pair) == 2: (action, doctype) = pair
            else:              (action, doctype) = (pair[0], None)
            if action not in group.actions: group.actions[action] = []
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
page    = cdrcgi.Page(title, subtitle=section, action=script, buttons=buttons,
                      session=session, body_classes="checkbox-form")

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
if isinstance(group,    basestring): cdrcgi.bail(group)
if isinstance(actions,  basestring): cdrcgi.bail(actions)
if isinstance(users,    basestring): cdrcgi.bail(users)
if isinstance(doctypes, basestring): cdrcgi.bail(doctypes)

#----------------------------------------------------------------------
# Display the information for the group.
#----------------------------------------------------------------------
B = page.B
page.add(B.INPUT(type="hidden", name="grp", value=group.name))
page.add(B.H2(group.name, style="font: 20pt Arial bold;"))
if request == "Save Changes":
    page.add(B.H4("(Successfully Updated)"))
page.add(B.H3("Group Name"))
page.add(B.INPUT(name="name", value=group.name, style="width: 200px;"))
page.add(B.H3("Description"))
page.add(B.TEXTAREA(group.comment or "", name="comment", rows="4", cols="80"))

#----------------------------------------------------------------------
# List the users which can be assigned to the group.
#----------------------------------------------------------------------
session = "%s=%s" % (cdrcgi.SESSION, session)
page.add(B.H3("Users"))
page.add("<table class='checkboxes'>")
nUsers = 0
USERS_PER_ROW = 6
for user in users:
    if nUsers % USERS_PER_ROW == 0: page.add("<tr>")
    field = B.INPUT(type="checkbox", value=user, name="users")
    if user in group.users:
        field.set("checked", "checked")
    url = "%s/EditUser.py?usr=%s&%s" % (cdrcgi.BASE, user, session)
    page.add(B.TD(field, B.A(user, href=url)))
    nUsers += 1
    if nUsers % USERS_PER_ROW == 0: page.add("</tr>")
if nUsers and nUsers % USERS_PER_ROW != 0: page.add("</tr>")
page.add("</table>")

#----------------------------------------------------------------------
# Add the actions for which the group can be authorized.
#----------------------------------------------------------------------
page.add(B.H3("Actions"))

#----------------------------------------------------------------------
# Add the actions independent of specific document types.
#----------------------------------------------------------------------
page.add(B.H4("Not Specific To Any Document Type"))
page.add("<table class='checkboxes'>")
nActions = 0
ACTIONS_PER_ROW = 5
for name in sorted(actions.keys()):
    if actions[name] != 'Y':
        if nActions % ACTIONS_PER_ROW == 0: page.add("<tr>")
        field_id = "action-%s" % name.replace(" ", "_")
        field = B.INPUT(type="checkbox", value=name, name="actions",
                        id=field_id)
        if name in group.actions:
            field.set("checked", "checked")
        label = B.LABEL(name, B.FOR(field_id))
        page.add(B.TD(field, label))
        nActions += 1
        if nActions % ACTIONS_PER_ROW == 0: page.add("</tr>")
if nActions and nActions % ACTIONS_PER_ROW != 0: page.add("</tr>")
page.add("</table>")

#----------------------------------------------------------------------
# Add the actions specific to individual document types.
#----------------------------------------------------------------------
DOCTYPES_PER_ROW = 7
for name in sorted(actions.keys()):
    if actions[name] == 'Y':
        grpAction = group.actions.get(name)
        page.add(B.H4(name))
        page.add("<table class='checkboxes'>")
        nDoctypes = 0
        for doctype in doctypes:
            if doctype == "ProtocolSourceDoc": continue
            if nDoctypes % DOCTYPES_PER_ROW == 0: page.add("<tr>")
            field_id = ("action-%s-%s" % (name, doctype)).replace(" ", "_")
            value = "%s::%s" % (name, doctype)
            field = B.INPUT(type="checkbox", value=value, name="actions",
                            id=field_id)
            if grpAction and doctype in grpAction:
                field.set("checked", "checked")
            label = B.LABEL(doctype, B.FOR(field_id))
            page.add(B.TD(field, label))
            nDoctypes += 1
            if nDoctypes % DOCTYPES_PER_ROW == 0: page.add("</tr>")
        if nDoctypes and nDoctypes % DOCTYPES_PER_ROW != 0: page.add("</tr>")
        page.add("</table>")

#----------------------------------------------------------------------
# Show the form.
#----------------------------------------------------------------------
page.send()
