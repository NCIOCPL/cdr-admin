#----------------------------------------------------------------------
#
# $Id: EditUser.py,v 1.4 2006-10-16 17:59:28 bkline Exp $
#
# Prototype for editing a CDR user.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/10/10 19:16:53  bkline
# Changed user deletion to navigate back to EditUsers.py.
#
# Revision 1.2  2002/02/21 15:22:03  bkline
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
usrName = fields and fields.getvalue("usr") or None
SUBMENU = "User Menu"

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
    cdrcgi.navigateTo("EditUsers.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Handle request to delete the user.
#----------------------------------------------------------------------
if request == "Delete User":
    error = cdr.delUser(session, usrName)
    if error: 
        if error.upper().find("COLUMN REFERENCE CONSTRAINT"):
            error = "Cannot delete user %s.  "\
                    "System actions have already been recorded for this user."\
                  % usrName
        cdrcgi.bail(error)
    cdrcgi.navigateTo("EditUsers.py", session)
    #cdrcgi.mainMenu(session, "User %s Deleted Successfully" % usrName)

def fixVal(v):
    return v and cgi.escape(v, True) or "None"

#----------------------------------------------------------------------
# Handle request to store changes to the user.
#----------------------------------------------------------------------
if request == "Save Changes":
    name     = fields and fields.getvalue("name") or ""
    password = fields and fields.getvalue("password") or ""
    comment  = fields.getvalue("comment")
    fullname = fields.getvalue("fullname")
    office   = fields.getvalue("office")
    email    = fields.getvalue("email")
    phone    = fields.getvalue("phone")
    user     = cdr.User(name, password)
    groups   = fields and fields.getvalue("groups") or []
    if type(groups) == type([]): user.groups = groups
    else:                        user.groups = [groups]
    if comment  != "None": user.comment      = comment
    if fullname != "None": user.fullname     = fullname
    if office   != "None": user.office       = office
    if email    != "None": user.email        = email
    if phone    != "None": user.phone        = phone
    error = cdr.putUser(session, usrName, user)
    if error: cdrcgi.bail(error)
    usrName = name

#----------------------------------------------------------------------
# Retrieve and display the user information.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Edit User Information"
buttons = ["Save Changes", "Delete User", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
#script  = "DumpParams.pl"
script  = "EditUser.py"
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Retrieve the group's information from the server.
#----------------------------------------------------------------------
if not usrName: user = cdr.User("", "")
else:           user = cdr.getUser(session, usrName)
groups = cdr.getGroups(session)
if type(user)   == type(""): cdrcgi.bail(user)
if type(groups) == type(""): cdrcgi.bail(groups)

#----------------------------------------------------------------------
# Display the information for the user.
#----------------------------------------------------------------------
form = """\
<H2>%s</H2>%s
<TABLE>
<TR>
<TD ALIGN='right' NOWRAP><B>User Id:</B></TD>
<TD><INPUT NAME='name' value="%s" SIZE='80'><TD>
</TR>
<TR>
<TD ALIGN='right' NOWRAP><B>Password:</B></TD>
<TD><INPUT NAME='password' value="%s" SIZE='80'><TD>
</TR>
<TR>
<TD ALIGN='right' NOWRAP><B>Full Name:</B></TD>
<TD><INPUT NAME='fullname' value="%s" SIZE='80'><TD>
</TR>
<TR>
<TD ALIGN='right' NOWRAP><B>Office:</B></TD>
<TD><INPUT NAME='office' value="%s" SIZE='80'><TD>
</TR>
<TR>
<TD ALIGN='right' NOWRAP><B>Email:</B></TD>
<TD><INPUT NAME='email' value="%s" SIZE='80'><TD>
</TR>
<TR>
<TD ALIGN='right' NOWRAP><B>Phone:</B></TD>
<TD><INPUT NAME='phone' value="%s" SIZE='80'><TD>
</TR>
<TR>
<TD ALIGN='right' NOWRAP VALIGN='top'><B>Groups:</B></TD>
""" % (user.name, 
       request == "Save Changes" and "\n<H4>(Successfully Updated)</H4>" or "",
       fixVal(user.name), fixVal(user.password),
       fixVal(user.fullname), fixVal(user.office),
       fixVal(user.email), fixVal(user.phone))

#----------------------------------------------------------------------
# List the groups to which the user can be assigned.
#----------------------------------------------------------------------
GROUPS_PER_ROW = 2
nGroups = 0
form += "<TD>\n<TABLE>\n"
for group in groups:
    flag = group in user.groups and "CHECKED\n" or ""
    if nGroups % GROUPS_PER_ROW == 0:
        form += "<TR>"
    url = "%s/EditGroup.py?grp=%s&%s=%s" % (cdrcgi.BASE,
                                            group,
                                            cdrcgi.SESSION,
                                            session)
    form += """\
<TD><INPUT TYPE='checkbox' 
           value="%s" 
           %sNAME='groups'><A HREF="%s">%s</A></INPUT></TD>
""" % (group, flag, url, group)
    nGroups += 1
    if nGroups % GROUPS_PER_ROW == 0: form += "</TR>"
form += "</TABLE>\n</TD>\n</TR>"

#----------------------------------------------------------------------
# Add the text box for the comment.
#----------------------------------------------------------------------
form += """\
<TR>
<TD ALIGN='right' NOWRAP VALIGN='top'><B>Comment:</B></TD>
<TD><TEXTAREA COLS='60' ROWS='4' NAME='comment'>%s</TEXTAREA></TD>
</TR>
</TABLE>
""" % user.comment

#----------------------------------------------------------------------
# Add the session key and send back the form.
#----------------------------------------------------------------------
form += """\
<INPUT TYPE='hidden' NAME='%s' value="%s" >
<INPUT TYPE='hidden' NAME='usr' value="%s" >
""" % (cdrcgi.SESSION, session, user.name)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
