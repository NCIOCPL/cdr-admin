#----------------------------------------------------------------------
#
# $Id: MenuHierarchy.py,v 1.1 2003-05-08 20:27:27 bkline Exp $
#
# Enables users to review the entire menu hierarchy for a given menu type.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import xml.dom.minidom, cgi, socket, struct, re, cdr, cdrcgi, cdrdb, time

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = fields and cdrcgi.getSession(fields)   or None
request  = fields and cdrcgi.getRequest(fields)   or None
menuType = fields and fields.getvalue("MenuType") or None
script   = "MenuHierarchy.py"
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
title    = "CDR Administration"
section  = "Menu Hierarchy Report"
header   = cdrcgi.header(title, title, section, script, buttons)

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
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

class MenuItem:
    def __init__(self, id, menuTypeName, name, status):
        self.id           = id
        self.menuTypeName = menuTypeName
        self.name         = name
        self.status       = status
        self.parents      = []
        self.children     = []
    def __cmp__(self, other):
        x = cmp(self.id, other.id)
        if x: return x
        x = cmp(self.menuTypeName, other.menuTypeName)
        if x: return x
        return cmp(self.name, other.name)

class MenuType:
    def __init__(self, name):
        self.name     = name
        self.topTerms = []
    def __cmp__(self, other):
        return cmp(self.name, other.name)

def loadMenuItems(menuType):
    global menuItems
    global menuTypes
    global findIndex
    parms = (("MenuType", menuType))
    response = cdr.report('guest', 'Menu Term Tree', parms)
    dom = xml.dom.minidom.parseString(response.replace("<![CDATA[", "")
                                              .replace("]]>", ""))
    tempIndex = {}
    for elem in dom.documentElement.childNodes:
        #print "node name:", elem.nodeName
        if elem.nodeName == "MenuItem":
            termId       = None
            termName     = None
            menuTypeName = None
            menuStatus   = None
            displayName  = None
            parentId     = None
            for child in elem.childNodes:
                if child.nodeName == "TermId":
                    termId = int(cdr.getTextContent(child))
                elif child.nodeName == "TermName":
                    termName = cdr.getTextContent(child)
                elif child.nodeName == "MenuType":
                    menuTypeName = cdr.getTextContent(child)
                elif child.nodeName == "MenuStatus":
                    menuStatus = cdr.getTextContent(child)
                elif child.nodeName == "DisplayName":
                    displayName = cdr.getTextContent(child)
                elif child.nodeName == "ParentId":
                    parentId = int(cdr.getTextContent(child))
            if termId and termName and menuTypeName:
                if menuTypeName not in menuTypes:
                    menuTypes[menuTypeName] = MenuType(menuTypeName)
                name = displayName or termName
                key = (termId, name, menuTypeName)
                if key in menuItems:
                    menuItem = menuItems[key]
                else:
                    menuItem = MenuItem(termId, menuTypeName, name, menuStatus)
                    menuItems[key] = menuItem
                if parentId:
                    menuItem.parents.append(parentId)
                tempIndex.setdefault((termId, menuTypeName), []).append(key)
    for key in menuItems:
        menuItem = menuItems[key]
        if not menuItem.parents:
            menuType = menuTypes[menuItem.menuTypeName]
            if key not in menuType.topTerms:
                menuType.topTerms.append(key)
        for parentId in menuItem.parents:
            key2 = (parentId, menuItem.menuTypeName)
            if key2 not in tempIndex:
                print "key (%d, %s) not found in tempIndex" % key2
                continue
            for parentKey in tempIndex[key2]:
                parent = menuItems[parentKey]
                if key not in parent.children:
                    parent.children.append(key)

#----------------------------------------------------------------------
# Put up a selection list from which the user can select a menu type.
#----------------------------------------------------------------------
def showMenuTypes(rows):
    selected = " SELECTED='1'"
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <H2>Select the menu type for the report.</H2>
   <SELECT NAME='MenuType'>
""" % (cdrcgi.SESSION, session)
    for row in rows:
        form += """
    <OPTION%s>%s</OPTION>
""" % (selected, cgi.escape(row[0], 1))
        selected = ""
    form += """
   </SELECT>
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(header + form)

if not menuType:
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
        SELECT DISTINCT value
                   FROM query_term
                  WHERE path = '/Term/MenuInformation/MenuItem/MenuType'""")
        rows = cursor.fetchall()
    except:
        cdrcgi.bail("Failure fetching list of menu types from database")
    if not rows:
        cdrcgi.bail("No menu types found in CDR terminology documents.")
    if len(rows) == 1:
        menuType = rows[0][0]
    else:
        showMenuTypes(rows)

#----------------------------------------------------------------------
# Display a term and its children.
#----------------------------------------------------------------------
def displayMenuItem(item, level):
    b1 = level == 1 and "<b>" or ""
    b2 = level == 1 and "</b>" or ""
    html = "&nbsp;" * level * 5 + b1 + cgi.escape(item.name) + b2 + "<br>\n"
    item.children.sort(lambda a,b: cmp(menuItems[a].name, menuItems[b].name))
    if level < 2:
        for child in item.children:
            html += displayMenuItem(menuItems[child], level + 1)
    return html
    
menuItems = {}
menuTypes = {}
loadMenuItems(menuType)
if not menuTypes.has_key(menuType):
    cdrcgi.bail("INTERNAL ERROR: No terms for menu type '%s' found" % menuType)
topItems = menuTypes[menuType].topTerms
topItems.sort(lambda a,b: cmp(menuItems[a].name, menuItems[b].name))
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Menu Hierarchy Report -- %s</title>
  <style type='text/css'>
   h2 { text-align: center; font-size: 16pt; font-weight: bold; }
   body { font-size: 12pt; }
  </style>
 </head>
 <body>
  <h2>Menu Hierarchy Report<br>%s<br>%s</h2>
  <br>
""" % (menuType, menuType, time.strftime("%B %d, %Y"))

for key in topItems:
    html += displayMenuItem(menuItems[key], 0)
cdrcgi.sendPage(html + """\
 </body>
</html>
""")
