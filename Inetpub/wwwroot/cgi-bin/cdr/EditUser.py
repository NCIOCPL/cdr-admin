#----------------------------------------------------------------------
# Administrative interface for creating or modifying a CDR user account.
# JIRA::OCECDR-3849 - Integrate CDR login with NIH Active Directory
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
usrName = fields.getvalue("usr")
SUBMENU = "User Menu"

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail("Unknown or expired CDR session.")

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("EditUsers.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Handle request to retire the user account.
#----------------------------------------------------------------------
if request == "Inactivate User":
    error = cdr.delUser(session, usrName)
    if error:
        cdrcgi.bail(error)
    cdrcgi.navigateTo("EditUsers.py", session)

#----------------------------------------------------------------------
# Handle request to store changes to the user.
#----------------------------------------------------------------------
if request == "Save Changes":
    name     = fields.getvalue("name") or ""
    password = fields.getvalue("password") or ""
    password2= fields.getvalue("password2") or ""
    comment  = fields.getvalue("comment")
    fullname = fields.getvalue("fullname")
    office   = fields.getvalue("office")
    email    = fields.getvalue("email")
    phone    = fields.getvalue("phone")
    authMode = fields.getvalue("auth_mode")
    groups   = fields.getlist("groups")
    if authMode == "network":
        password = password2 = ""
    elif not password:
        if not usrName:
            cdrcgi.bail("Password is required for local accounts")
    elif password != password2:
        cdrcgi.bail("Passwords do not match")

    # Store the values.
    user = cdr.User(name, password, fullname, office, email, phone,
                    groups, comment, authMode)
    error = cdr.putUser(session, usrName, user)

    if error: cdrcgi.bail(error)
    usrName = name

#----------------------------------------------------------------------
# Retrieve the group's information from the server.
#----------------------------------------------------------------------
if not usrName: user = cdr.User("", "")
else:           user = cdr.getUser(session, usrName)
groups = cdr.getGroups(session)
if type(user)   == type(""): cdrcgi.bail(user)
if type(groups) == type(""): cdrcgi.bail(groups)
networkAuth = user.authMode == "network"
localAuth = not networkAuth

#----------------------------------------------------------------------
# Display the information for the user.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Edit User Information"
buttons = ["Save Changes", "Inactivate User", SUBMENU, cdrcgi.MAINMENU,
           "Log Out"]
script  = "EditUser.py"
if request == "Save Changes":
    section = "User Information Successfully Updated"
form = cdrcgi.Page(title, banner=title, subtitle=section, buttons=buttons,
                   action=script, session=session)
form.add(form.B.INPUT(name="usr", value=user.name, type="hidden"))
form.add("<fieldset>")
form.add(form.B.LEGEND("User Account Settings"))
form.add_text_field("name", "Name", value=user.name or "")
form.add_text_field("fullname", "Full Name", value=user.fullname or "")
form.add_text_field("office", "Office", value=user.office or "")
form.add_text_field("email", "Email", value=user.email or "")
form.add_text_field("phone", "Phone", value=user.phone or "")
form.add_textarea_field("comment", "Comment", value=user.comment or "")
form.add_radio("auth_mode", "Normal CDR User", "network",
               tooltip="User who logs in using NIH domain account",
               wrapper=None, checked=networkAuth)
form.add_radio("auth_mode", "Local System Account", "local",
               tooltip="Account used for scheduled jobs on localhost",
               wrapper=None, checked=localAuth)
form.add("</fieldset>")
if localAuth:
    form.add('<fieldset id="password-block">')
else:
    form.add('<fieldset id="password-block" class="hidden">')
if user.name and localAuth:
    legend = "Change password (leave blank to keep existing password)"
else:
    legend = "Password (required for local accounts)"
form.add(form.B.LEGEND(legend))
form.add_text_field("password", "Password", password=True)
form.add_text_field("password2", "Confirm", password=True)
form.add("</fieldset>")
form.add("<fieldset>")
form.add(form.B.LEGEND("Group Membership for User"))
for group in sorted(groups, key=unicode.lower):
    checked = group in user.groups
    form.add_checkbox("groups", group, group, checked=checked)
form.add("</fieldset>")
form.add_script("""\
function check_auth_mode(mode) {
    switch (mode) {
        case 'local':
            jQuery('#password-block').show();
            break;
        case 'network':
            jQuery('#password-block').hide();
            break;
    }
}
""")
form.send()
