#----------------------------------------------------------------------
# $Id: ShowCdrCommands.py,v 1.1 2002-09-29 14:03:25 bkline Exp $
#
# Show CDR summary of commands submitted during a specified time period.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrcgi, cdrdb, cgi, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
start   = fields and fields.getvalue('StartTime') or None
end     = fields and fields.getvalue('EndTime')   or None
command = "ShowCdrCommands.py"
title   = "CDR Administration"
section = "Show CDR Commands"
SUBMENU = "Reports Menu"
buttons = ["Submit"] #[SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, command, buttons)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

if not start or not end:
    import time
    now      = time.localtime()
    then     = list(now)
    then[3] -= 1 # move back an hour
    then     = time.localtime(time.mktime(then))
    start    = time.strftime("%Y-%m-%d %H:%M:%S", then)
    end      = time.strftime("%Y-%m-%d %H:%M:%S", now)
    cdrcgi.sendPage(header + """\
   <table border = '0'>
    <tr>
     <td align = 'right'>Start Time:&nbsp;</td>
     <td>
      <input name = 'StartTime' value = '%s' />
     </td>
    </tr>
    <tr>
     <td align = 'right'>End Time:&nbsp;</td>
     <td>
      <input name = 'EndTime' value = '%s' />
     </td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (start, end))

class CdrCommand:
    "Object representing most interesting information about a CDR command."
    def __init__(self, node):
        self.info = "???"
        for child in node.childNodes:
            if child.nodeName == "CdrLastVersions":
                self.cdrLastVersions(child)
            elif child.nodeName == "CdrFilter":
                self.cdrFilter(child)
            elif child.nodeName == "CdrLogon":
                self.cdrLogon(child)
            elif child.nodeName == "CdrGetDoc":
                self.cdrGetDoc(child)
            elif child.nodeName == "CdrRepDoc":
                self.cdrRepDoc(child)
            elif child.nodeName == "CdrAddDoc":
                self.cdrAddDoc(child)
            elif child.nodeName == "CdrGetDocType":
                self.cdrGetDocType(child)
            elif child.nodeName == "CdrSearch":
                self.cdrSearch(child)
            elif child.nodeType == child.ELEMENT_NODE:
                self.info = child.nodeName

    def cdrSearch(self, node):
        maxDocs = None
        query = "???"
        for child in node.childNodes:
            if child.nodeName == "Query":
                query = cdr.getTextContent(child)
                maxDocsAttr = child.getAttribute("MaxDocs")
                if maxDocsAttr: maxDocs = maxDocsAttr
        self.info = "CdrSearch(query=%s" % query
        if maxDocs: self.info += ",maxDocs=%s" % maxDocs
        self.info += ")"

    def cdrGetDocType(self, node):
        docType = "???"
        typeAttr = node.getAttribute("Type")
        if typeAttr: docType = typeAttr
        omitDtd = node.getAttribute("OmitDtd")
        getEnumValues = node.getAttribute("GetEnumValues")
        self.info = "CdrGetDocType(type=%s" % docType
        if omitDtd: self.info += ",omitDtd=%s" % omitDtd
        if getEnumValues: self.info += ",getEnumValues=%s" % getEnumValues
        self.info += ")"

    def cdrAddDoc(self, node):
        docType = "???"
        checkIn = None
        validate = None
        version = None
        publishable = None
        setLinks = None
        reason = None
        for child in node.childNodes:
            if child.nodeName == "CdrDoc":
                docTypeAttr = child.getAttribute("Type")
                if docTypeAttr: docType = docTypeAttr
            elif child.nodeName == "CheckIn":
                checkIn = cdr.getTextContent(child)
            elif child.nodeName == "Validate":
                validate = cdr.getTextContent(child)
            elif child.nodeName == "Version":
                version = cdr.getTextContent(child)
                publishableAttr = child.getAttribute("Publishable")
                if publishableAttr:
                    publishable = publishableAttr
            elif child.nodeName == "SetLinks":
                setLinks = cdr.getTextContent(child)
            elif child.nodeName == "Reason":
                reason = cdr.getTextContent(child)
        self.info = "CdrAddDoc(type=%s" % docType
        if checkIn: self.info += ",checkIn=%s" % checkIn
        if validate: self.info += ",validate=%s" % validate
        if version: self.info += ",version=%s" % version
        if publishable: self.info += ",publishable=%s" % publishable
        if setLinks: self.info += ",setLinks=%s" % setLinks
        if reason: self.info += ",reason=%s" % reason
        self.info += ")"

    def cdrRepDoc(self, node):
        id = "???"
        docType = "???"
        checkIn = None
        validate = None
        version = None
        publishable = None
        setLinks = None
        reason = None
        for child in node.childNodes:
            if child.nodeName == "CdrDoc":
                idAttr = child.getAttribute("Id")
                docTypeAttr = child.getAttribute("Type")
                if idAttr: id = idAttr
                if docTypeAttr: docType = docTypeAttr
            elif child.nodeName == "CheckIn":
                checkIn = cdr.getTextContent(child)
            elif child.nodeName == "Validate":
                validate = cdr.getTextContent(child)
            elif child.nodeName == "Version":
                version = cdr.getTextContent(child)
                publishableAttr = child.getAttribute("Publishable")
                if publishableAttr:
                    publishable = publishableAttr
            elif child.nodeName == "SetLinks":
                setLinks = cdr.getTextContent(child)
            elif child.nodeName == "Reason":
                reason = cdr.getTextContent(child)
        self.info = "CdrRepDoc(id=%s,type=%s" % (id, docType)
        if checkIn: self.info += ",checkIn=%s" % checkIn
        if validate: self.info += ",validate=%s" % validate
        if version: self.info += ",version=%s" % version
        if publishable: self.info += ",publishable=%s" % publishable
        if setLinks: self.info += ",setLinks=%s" % setLinks
        if reason: self.info += ",reason=%s" % reason
        self.info += ")"

    def cdrGetDoc(self, node):
        id = "???"
        lock = None
        ver = None
        for child in node.childNodes:
            if child.nodeName == "DocId":
                id = cdr.getTextContent(child)
            elif child.nodeName == "Lock":
                lock = cdr.getTextContent(child)
            elif child.nodeName == "DocVersion":
                ver = cdr.getTextContent(child)
        self.info = "CdrGetDoc(id=%s" % id
        if lock:
            self.info += ",%s" % lock
        if ver:
            self.info += ",%s" % ver
        self.info += ")"

    def cdrLogon(self, node):
        uid = "???"
        pwd = "???"
        for child in node.childNodes:
            if child.nodeName == "UserName":
                uid = cdr.getTextContent(child)
            elif child.nodeName == "Password":
                pwd = cdr.getTextContent(child)
        self.info = "CdrLogon(uid=%s,pwd=%s)" % (uid, "$$$$$$$$$") #pwd)

    def cdrFilter(self, node):
        filters = []
        params  = []
        doc = "???"
        for child in node.childNodes:
            if child.nodeName == "Filter":
                href = child.getAttribute("href")
                name = child.getAttribute("Name")
                if href:
                    filters.append(href)
                elif name:
                    filters.append(name)
                else:
                    filters.append("<inline>")
            elif child.nodeName == "Document":
                href = child.getAttribute("href")
                ver  = child.getAttribute("version")
                if href:
                    doc = href
                    if ver:
                        doc += ("/%s" % ver)
                else:
                    doc = "<inline>"
            elif child.nodeName == "Parms":
                for parm in child.childNodes:
                    if parm.nodeName == "Parm":
                        name = "???"
                        val  = "???"
                        for parmChild in parm.childNodes:
                            if parmChild.nodeName == "Name":
                                name = cdr.getTextContent(parmChild)
                            elif parmChild.nodeName == "Value":
                                val = cdr.getTextContent(parmChild)
                        params.append("%s=%s" % (name, val))
        self.info = "CdrFilter(filters=[%s],doc=%s" % (",".join(filters), doc)
        if params: self.info += ",params=[%s]" % ";".join(params)
        self.info += ")"

    def cdrLastVersions(self, node):
        for child in node.childNodes:
            if child.nodeName == "DocId":
                self.info = "CdrLastVersions(docId=%s)" % \
                            cdr.getTextContent(child)
                return
        self.info = "CdrLastVersions(docId=???)"

    def __repr__(self): return self.info

title = "CDR Commands between %s and %s" % (start, end)
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <h3>%s</h3>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Thread</th>
    <th>Received</th>
    <th>Command</th>
   </tr>
""" % (title, title)

conn = cdrdb.connect()
cursor = conn.cursor()
cursor.execute("""\
        SELECT command, thread, received
          FROM command_log
         WHERE received BETWEEN '%s' AND '%s'
      ORDER BY received""" % (start, end))
row = cursor.fetchone()
while row:
    commandSet, thread, received = row
    dom = xml.dom.minidom.parseString(commandSet)
    for cmdNode in dom.documentElement.childNodes:
        if cmdNode.nodeName == "CdrCommand":
            cmd = CdrCommand(cmdNode)
            html += """\
   <tr>
    <td valign='top'>%d</td>
    <td nowrap='1' valign='top'>%s</td>
    <td nowrap='1'>%s</td>
   </tr>
""" % (thread, received, cmd)
    row = cursor.fetchone()
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
