#----------------------------------------------------------------------
#
# $Id: EditQueryTermDefs.py,v 1.3 2002-02-21 15:22:03 bkline Exp $
#
# Prototype for editing CDR query term definitions.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2001/12/01 18:02:48  bkline
# Enlarged path field size.
#
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, urllib

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
title   = "CDR Administration"
section = "Manage Query Term Definitions"
buttons = [cdrcgi.MAINMENU, "Log Out"]
script  = "EditQueryTermDefs.py"
#script  = "DumpParams.py"
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Process an action if the user requested one.
#----------------------------------------------------------------------
deleteKey  = None
addCommand = None
pathDict   = {}
ruleDict   = {}
for field in fields.keys():
    val  = fields[field].value
    name = fields[field].name
    if val == "None": val = None
    if name.startswith("path-")  : pathDict[name.split("-", 1)[1]] = val
    if name.startswith("rule-")  : ruleDict[name.split("-", 1)[1]] = val
    if name.startswith("delete-"): deleteKey = name.split("-", 1)[1]
    if name == 'add'             : addCommand = name

if addCommand:
    path = pathDict.has_key("0") and pathDict["0"] or None
    rule = ruleDict.has_key("0") and ruleDict["0"] or None
    if not path: cdrcgi.bail("Missing required path value")
    err = cdr.addQueryTermDef(session, path, rule)
    if err: cdrcgi.bail(err)

if deleteKey:
    path = pathDict.has_key(deleteKey) and pathDict[deleteKey] or None
    rule = ruleDict.has_key(deleteKey) and ruleDict[deleteKey] or None
    if not path: cdrcgi.bail("Missing required path value")
    err = cdr.delQueryTermDef(session, path, rule)
    if err: cdrcgi.bail(err)
request = fields.getvalue(cdrcgi.REQUEST)
if request == "Log Out": cdrcgi.logout(session)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Retrieve the lists of rules and query term definitions from the server.
#----------------------------------------------------------------------
rules = cdr.listQueryTermRules(session)
if type(rules) == type(""): cdrcgi.bail(rules)
defs  = cdr.listQueryTermDefs(session)
if type(defs) == type(""): cdrcgi.bail(defs)

#----------------------------------------------------------------------
# Routines to make data entry fields.
#----------------------------------------------------------------------
def makePathField(val, row):
    return "<INPUT NAME='path-%d' SIZE='80' VALUE='%s'>" % (row, val)

def makeRuleField(val, row):
    selected = " SELECTED"
    if val: selected = ""
    field = "<SELECT NAME='rule-%d'><OPTION%s>None</OPTION>" % (row, selected)
    for rule in rules:
        selected = val == rule and " SELECTED" or ""
        field += "<OPTION%s>%s</OPTION>" % (selected, rule)
    return field + "</SELECT>"
        
def makeDeleteButton(row):
    return ("<INPUT TYPE='submit' NAME='delete-%d' VALUE='Delete Definition'>"
            % row)

def makeAddButton():
    return "<INPUT TYPE='submit' NAME='add' VALUE='Add New Definition'>"

#----------------------------------------------------------------------
# Display the existing definitions.
#----------------------------------------------------------------------
row = 1
menu = """\
  <FORM>
   <TABLE>
    <TR>
     <TH>Path</TH>
     <TH>Rule</TH>
     <TH>Action</TH>
    </TR>
    <TR>
     <TD>%s</TD>
     <TD>%s</TD>
     <TD ALIGN='center'>%s</TD>
    </TR>
""" % (makePathField("", 0),
       makeRuleField("", 0),
       makeAddButton())
for definition in defs:
    menu += """\
    <TR>
     <TD>%s</TD>
     <TD>%s</TD>
     <TD ALIGN='center'>%s</TD>
    </TR>
""" % (makePathField(definition[0], row),
       makeRuleField(definition[1], row),
       makeDeleteButton(row))
    row += 1
menu += """\
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
<HTML>
""" % (cdrcgi.SESSION, session)

cdrcgi.sendPage(header + menu)
