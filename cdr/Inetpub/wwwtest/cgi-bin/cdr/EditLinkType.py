#----------------------------------------------------------------------
#
# $Id: EditLinkType.py,v 1.4 2002-02-21 20:09:47 ameyer Exp $
#
# Prototype for editing a CDR link type.
#
# Script is run twice - first to create a form on screen, then
# to read the values on the form.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/02/21 15:22:02  bkline
# Added navigation buttons.
#
# Revision 1.2  2002/02/15 06:50:11  ameyer
# Handling add/edit differences in both uses of this module - to
# put up an edit form and to process the form after the user fills it in.
#
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
#
#----------------------------------------------------------------------

import cgi, cdr, cdrcgi, re, string, sys

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
name    = fields and fields.getvalue("name") or None
linkForm= fields and fields.getvalue("linkform") or None
extra   = ""
SUBMENU = "Link Menu"

#----------------------------------------------------------------------
# If no linkForm, this is first time through, setup subsequent action.
# Initialize linkAct to value from form variable or URL parameter.
#----------------------------------------------------------------------
linkAct = linkForm
if linkForm is None:
    linkAct = fields and fields.getvalue("linkact") or None;
    if (linkAct != "addlink" and linkAct != "modlink"):
        cdrcgi.bail("Invalid form linkact='%s' - can't happen" % linkAct)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("EditLinkControl.py", session)

#----------------------------------------------------------------------
# Handle request to delete the link type - Future.
#----------------------------------------------------------------------
if request == "Delete Link Type":
    cdrcgi.bail("Delete Link Type command not yet implemented")
    unused_code = """ - MODEL FROM delUser\
    error = cdr.delUser(session, usrName)
    if error:
        if error.upper().find("COLUMN REFERENCE CONSTRAINT"):
            error = "Cannot delete user %s.  "\
                    "System actions have already been recorded for this user."\
                  % usrName
        cdrcgi.bail(error)
    cdrcgi.mainMenu(session, "Group %s Deleted Successfully" % usrName)
    """

#----------------------------------------------------------------------
# Gather together the fields in the form name-number.
#----------------------------------------------------------------------
def getArrayFields(baseNames):
    arrayFields = {}
    for baseName in baseNames:
        arrayFields[baseName] = {}
    for fieldName in fields.keys():
        nameParts = fieldName.split("-")
        if len(nameParts) == 2:
            name = nameParts[0]
            num  = int(nameParts[1])
            if name in baseNames:
                arrayFields[name][num] = fields.getvalue(fieldName)
    return arrayFields

#----------------------------------------------------------------------
# Handle request to store changes to the link type.
#----------------------------------------------------------------------
if request == "Save Changes":
    linkTypeName = fields and fields.getvalue("name") or ""
    linkType     = cdr.LinkType(linkTypeName)
    comment      = fields.getvalue("comment")
    if comment: linkType.comment = comment

    # So much for the easy fields; now get the multi-occurence values.
    arrayFields = getArrayFields(("src_sel", "src_dt", "src_elem",
                                  "dst_sel", "dst_dt",
                                  "prop_sel", "prop_name", "prop_value",
                                  "prop_comment"))
    srcKeys = arrayFields["src_sel"].keys()
    srcKeys.sort()
    for srcKey in srcKeys:
        if arrayFields["src_sel"][srcKey] == "on":
            srcDocType = arrayFields["src_dt"][srcKey]
            if srcDocType == "Select Document Type":
                cdrcgi.bail("Document type must be selected for link source")
                break
            if not arrayFields["src_elem"].has_key(srcKey):
                cdrcgi.bail("Missing required source field")
                break
            srcField   = arrayFields["src_elem"][srcKey]
            if not srcField:
                cdrcgi.bail("Required source field empty")
                break
            linkType.linkSources.append((srcDocType, srcField))
    dstKeys = arrayFields["dst_sel"].keys()
    dstKeys.sort()
    for dstKey in dstKeys:
        if arrayFields["dst_sel"][dstKey] == "on":
            dstDocType = arrayFields["dst_dt"][dstKey]
            if dstDocType == "Select Document Type":
                cdrcgi.bail("Document type must be selected for link target")
                break
            linkType.linkTargets.append(dstDocType)
    propKeys = arrayFields["prop_sel"].keys()
    propKeys.sort()
    for propKey in propKeys:
        if arrayFields["prop_sel"][propKey] == "on":
            propValue   = ""
            propComment = ""
            propName    = arrayFields["prop_name"][propKey]
            if propName == "Select Property":
                cdrcgi.bail("Property name not selected")
                break
            if arrayFields["prop_value"].has_key(propKey):
                propValue   = arrayFields["prop_value"][propKey]
                if propValue == "None": propValue = ""
            if arrayFields["prop_comment"].has_key(propKey):
                propComment = arrayFields["prop_comment"][propKey]
                if propComment == "None": propComment = ""
            linkType.linkProps.append((propName, propValue, propComment))
    error = cdr.putLinkType(session, name, linkType, linkForm)
    if error: cdrcgi.bail(error)
    name = linkTypeName
    extra = "\n<H4>(Successfully Updated)</H4>"

#----------------------------------------------------------------------
# Retrieve and display the link type information.
#----------------------------------------------------------------------
title   = "CDR Administration"
if linkAct == "addlink":
    section = "Add Link Type"
else:
    section = "Edit Link Type"

buttons = ["Save Changes", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
#script  = "DumpParams.pl"
script  = "EditLinkType.py"
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Retrieve the link types's information from the server.
#----------------------------------------------------------------------
if not name: linkType = cdr.LinkType("")
else:        linkType = cdr.getLinkType(session, name)
doctypes              = cdr.getDoctypes(session)
props                 = cdr.getLinkProps(session)

#print "Content-type: text/plain\n\n"
#print str(linkType)
#sys.exit(0)

#----------------------------------------------------------------------
# Any strings returned by those functions are error messages.
#----------------------------------------------------------------------
if type(linkType) == type(""): cdrcgi.bail(linkType)
if type(doctypes) == type(""): cdrcgi.bail(doctypes)
if type(props)    == type(""): cdrcgi.bail(props)

#----------------------------------------------------------------------
# Create a flag field to indicate whether this row is enabled.
#----------------------------------------------------------------------
def checkbox(nameBase, rowNum, selected):
    flag = selected and " CHECKED" or ""
    return "<INPUT TYPE='checkbox' NAME='%s-%d'%s>" % (nameBase,
                                                       rowNum,
                                                       flag)

#----------------------------------------------------------------------
# Create a dropdown list of document types, possibly with one selected.
#----------------------------------------------------------------------
def dtList(doctype, nameBase, rowNum):
    str = "<SELECT NAME='%s-%d'>\n" % (nameBase, rowNum)
    str += "<OPTION>Select Document Type</OPTION>\n"
    for dt in doctypes:
        str += "<OPTION%s>%s</OPTION>\n" % (dt == doctype and " SELECTED" or "",
                                            dt)
    return str + "</SELECT>\n"

#----------------------------------------------------------------------
# Create a dropdown list of link properties, possibly with one selected.
#----------------------------------------------------------------------
def propList(prop, nameBase, rowNum):
    str = "<SELECT NAME='%s-%d'>\n" % (nameBase, rowNum)
    str += "<OPTION>Select Property</OPTION>\n"
    for p in props:
        n = p.name
        str += "<OPTION%s>%s</OPTION>\n" % (n == prop and " SELECTED" or "", n)
    return str + "</SELECT>\n"

#----------------------------------------------------------------------
# Create a text data entry field.
#----------------------------------------------------------------------
def textField(elemName, nameBase, rowNum):
    return "<INPUT NAME='%s-%d' VALUE='%s' SIZE='45'>" % (nameBase,
                                                          rowNum,
                                                          elemName)

#----------------------------------------------------------------------
# Create a text area entry field.
#----------------------------------------------------------------------
def textArea(value, nameBase, rowNum):
    return "<TEXTAREA COLS='60' ROWS='3' NAME='%s-%d'>%s</TEXTAREA>" % (
            nameBase,
            rowNum,
            value)

#----------------------------------------------------------------------
# Create a form with a hidden field to indicate add or modify
#----------------------------------------------------------------------
form = """<INPUT type='hidden' name='linkform' value='%s' />""" % linkAct

#----------------------------------------------------------------------
# Display the information for the user.
#----------------------------------------------------------------------
form += """\
<H2>%s</H2>%s
<TABLE>
<TR>
<TD ALIGN='right' NOWRAP><B>Link Type Name:</B></TD>
<TD><INPUT NAME='name' VALUE='%s' SIZE='80'><TD>
</TR>
""" % (name, extra, name)

#----------------------------------------------------------------------
# List the document types and elements from which links of this type
# can be made.
#----------------------------------------------------------------------
leftCol = "<TD ALIGN='right' NOWRAP><B>Can Link From:</B></TD>"
rowNum = 1
for linkSource in linkType.linkSources:
    form += """\
    <TR>%s
    <TD><TABLE><TR><TD>%s</TD><TD>%s</TD><TD>%s</TD></TR></TABLE></TD>
    </TR>""" % (
            leftCol,
            checkbox("src_sel", rowNum, 1),
            dtList(linkSource[0], "src_dt", rowNum),
            textField(linkSource[1], "src_elem", rowNum))
    leftCol = "<TD>&nbsp;</TD>"
    rowNum += 1

#----------------------------------------------------------------------
# Add rows for additional link sources.
#----------------------------------------------------------------------
for i in range(3):
    form += """\
    <TR>%s
    <TD><TABLE><TR><TD>%s</TD><TD>%s</TD><TD>%s</TD></TR></TABLE></TD>
    </TR>
    """ % (
            leftCol,
            checkbox("src_sel", rowNum, 0),
            dtList("", "src_dt", rowNum),
            textField("", "src_elem", rowNum))
    rowNum += 1

#----------------------------------------------------------------------
# List the document types to which links of this type can be made.
#----------------------------------------------------------------------
leftCol = "<TD ALIGN='right' NOWRAP><B>Can Link To:</B></TD>"
rowNum = 1
for linkTarget in linkType.linkTargets:
    form += """\
    <TR>%s
    <TD><TABLE><TR><TD>%s</TD><TD>%s</TD></TR></TABLE>
    </TR>""" % (
            leftCol,
            checkbox("dst_sel", rowNum, 1),
            dtList(linkTarget, "dst_dt", rowNum))
    leftCol = "<TD>&nbsp;</TD>"
    rowNum += 1

#----------------------------------------------------------------------
# Add rows for additional link targets.
#----------------------------------------------------------------------
for i in range(3):
    form += """\
    <TR>%s
    <TD><TABLE><TR><TD>%s</TD><TD>%s</TD></TR></TABLE></TD>
    </TR>""" % (
            leftCol,
            checkbox("dst_sel", rowNum, 0),
            dtList("", "dst_dt", rowNum))
    rowNum += 1

#----------------------------------------------------------------------
# List the properties attached to this link type.
#----------------------------------------------------------------------
rowNum = 1
for prop in linkType.linkProps:
    form += """\
    <TR>
     <TD ALIGN='right' NOWRAP><B>Property:</B></TD>
     <TD><TABLE><TR><TD>%s</TD><TD>%s</TD></TR></TABLE></TD>
    </TR>
    <TR>
     <TD ALIGN='right' VALIGN='top'><B>Property Value:</B></TD>
     <TD>%s</TD>
    </TR>
    <TR>
     <TD ALIGN='right' VALIGN='top'><B>Property Comment:</B></TD>
     <TD>%s</TD>
    </TR>
""" % ( checkbox("prop_sel", rowNum, 1),
        propList(prop[0], "prop_name", rowNum),
        textArea(prop[1], "prop_value", rowNum),
        textArea(prop[2], "prop_comment", rowNum))
    rowNum += 1

#----------------------------------------------------------------------
# Add an empty slot for the user to add a new property.
#----------------------------------------------------------------------
form += """\
    <TR>
     <TD ALIGN='right' NOWRAP><B>Property:</B></TD>
     <TD><TABLE><TR><TD>%s</TD><TD>%s</TD></TR></TABLE></TD>
    </TR>
    <TR>
     <TD ALIGN='right' VALIGN='top'><B>Property Value:</B></TD>
     <TD>%s</TD>
    </TR>
    <TR>
     <TD ALIGN='right' VALIGN='top'><B>Property Comment:</B></TD>
     <TD>%s</TD>
    </TR>
""" % ( checkbox("prop_sel", rowNum, 0),
        propList("", "prop_name", rowNum),
        textArea("", "prop_value", rowNum),
        textArea("", "prop_comment", rowNum))

#----------------------------------------------------------------------
# Add the text box for the comment.
#----------------------------------------------------------------------
form += """\
<TR>
<TD ALIGN='right' NOWRAP VALIGN='top'><B>Description:</B></TD>
<TD><TEXTAREA COLS='60' ROWS='4' NAME='comment'>%s</TEXTAREA></TD>
</TR>
</TABLE>
""" % linkType.comment

#----------------------------------------------------------------------
# Add the session key and send back the form.
#----------------------------------------------------------------------
form += """\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
