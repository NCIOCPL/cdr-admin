#----------------------------------------------------------------------
#
# $Id$
#
# Enables users to review the entire menu hierarchy for a given menu type.
#
# In order to sort the children of a term based on the SortOrder attribute
# value the sortString was introduced.  The sortString is equal to the
# TermName if the SortOrder attribute does not exist, otherwise it is the
# SortOrder value itself.  Sort the children of a term by the sortString but
# display the term name.
#
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb
import cgi
import lxml.etree as etree
import time

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Please log in")
request  = cdrcgi.getRequest(fields)
menuType = fields.getvalue("MenuType")
script   = "MenuHierarchy.py"
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
title    = "CDR Administration"
section  = "Menu Hierarchy Report"

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Collect the menu type names. Make sure any selected value is valid.
# If not, we have a hacker, in which case we avoid showing any helpful
# information.
#----------------------------------------------------------------------
query = cdrdb.Query("query_term", "value").unique().order(1)
query.where("path = '/Term/MenuInformation/MenuItem/MenuType'")
menuTypes = [row[0] for row in query.execute().fetchall()]
if not menuTypes:
    cdrcgi.bail("No menu types found in CDR terminology documents.")
if len(menuTypes) == 1:
    menuType = menuTypes[0]
elif menuType and menuType not in menuTypes:
    cdrcgi.bail("Corrupted form data")

class MenuItem:
    def __init__(self, id, sortString, menuTypeName, name, status):
        self.id           = id
        self.menuTypeName = menuTypeName
        self.name         = name
        self.status       = status
	self.sortString   = sortString
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
    docXml = response.replace("<![CDATA[", "").replace("]]>", "")
    tree = etree.XML(docXml)
    tempIndex = {}
    for node in tree:
        if node.tag == "MenuItem":
            termId       = None
            termName     = None
            menuTypeName = None
            menuStatus   = None
            displayName  = None
            parentId     = None
	    sortString   = None
            for child in node:
                if child.tag == "TermId":
                    termId = int(child.text)
                elif child.tag == "TermName":
                    termName = child.text
                elif child.tag == "MenuType":
                    menuTypeName = child.text
                elif child.tag == "MenuStatus":
                    menuStatus = child.text
                elif child.tag == "DisplayName":
                    displayName = child.text
                elif child.tag == "ParentId":
                    parentId = int(child.text)
		elif child.tag == "SortString":
		    sortString = child.text

            if termId and termName and menuTypeName:
                if menuTypeName not in menuTypes:
                    menuTypes[menuTypeName] = MenuType(menuTypeName)
                name = displayName or termName
                key = (termId, sortString, name, menuTypeName)
                if key in menuItems:
                    menuItem = menuItems[key]
                else:
                    menuItem = MenuItem(termId, sortString, menuTypeName,
                                        name, menuStatus)
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
                continue
            for parentKey in tempIndex[key2]:
                parent = menuItems[parentKey]
                if key not in parent.children:
                    parent.children.append(key)

#----------------------------------------------------------------------
# Put up a selection list from which the user can select a menu type.
#----------------------------------------------------------------------
def showMenuTypes(rows):
    page = cdrcgi.Page(title, subtitle=section, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select Menu Type For Report"))
    page.add_select("MenuType", "Type", rows)
    page.add("</fieldset>")
    page.send()

if not menuType:
        showMenuTypes(menuTypes)

#----------------------------------------------------------------------
# Display a term and its children.
#----------------------------------------------------------------------
def displayMenuItem(item, level=0):
    b1 = level == 1 and "<b>" or ""
    b2 = level == 1 and "</b>" or ""
    html = " " * level * 5 + b1 + cgi.escape(item.name) + b2 + "\n"

    # Sort the children of the terms by the sortString not the terms itself
    # ---------------------------------------------------------------------
    if level == 1:
        item.children.sort(lambda a,b: cmp(menuItems[a].sortString,
                                           menuItems[b].sortString))
    else:
        item.children.sort(lambda a,b: cmp(menuItems[a].name,
                                           menuItems[b].name))

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
html = u"""\
<!DOCTYPE html>
<html>
 <head>
  <title>Menu Hierarchy Report -- %s</title>
  <link rel="stylesheet" href="/stylesheets/dataform.css">
  <style type='text/css'>
   *, pre.sans-serif { font-family: Arial, Helvetica, sans-serif; }
   h2 { text-align: center; font-size: 16pt; font-weight: bold; }
   body { font-size: 12pt; }
  </style>
 </head>
 <body>
  <h2>Menu Hierarchy Report<br>%s<br>%s</h2>
  <pre class="sans-serif">
""" % (menuType, menuType, time.strftime("%B %d, %Y"))

for key in topItems:
    html += displayMenuItem(menuItems[key])
cdrcgi.sendPage(html + u"""\
  </pre>
 </body>
</html>
""")
