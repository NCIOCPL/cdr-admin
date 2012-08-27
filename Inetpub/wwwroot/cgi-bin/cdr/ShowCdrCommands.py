#----------------------------------------------------------------------
# $Id$
#
# Show CDR summary of commands submitted during a specified time period.
#
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
buttons = ["Submit"]
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
        self.info = u"???"
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
        query = u"???"
        for child in node.childNodes:
            if child.nodeName == "Query":
                query = cdr.getTextContent(child)
                maxDocsAttr = child.getAttribute("MaxDocs")
                if maxDocsAttr: maxDocs = maxDocsAttr
        self.info = u"CdrSearch(query=%s" % query
        if maxDocs: self.info += u",maxDocs=%s" % maxDocs
        self.info += u")"

    def cdrGetDocType(self, node):
        docType = u"???"
        typeAttr = node.getAttribute("Type")
        if typeAttr: docType = typeAttr
        omitDtd = node.getAttribute("OmitDtd")
        getEnumValues = node.getAttribute("GetEnumValues")
        self.info = u"CdrGetDocType(type=%s" % docType
        if omitDtd: self.info += u",omitDtd=%s" % omitDtd
        if getEnumValues: self.info += u",getEnumValues=%s" % getEnumValues
        self.info += u")"

    def cdrAddDoc(self, node):
        docType = u"???"
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
        self.info = u"CdrAddDoc(type=%s" % docType
        if checkIn: self.info += u",checkIn=%s" % checkIn
        if validate: self.info += u",validate=%s" % validate
        if version: self.info += u",version=%s" % version
        if publishable: self.info += u",publishable=%s" % publishable
        if setLinks: self.info += u",setLinks=%s" % setLinks
        if reason: self.info += u",reason=%s" % reason
        self.info += u")"

    def cdrRepDoc(self, node):
        id = u"???"
        docType = u"???"
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
        self.info = u"CdrRepDoc(id=%s,type=%s" % (id, docType)
        if checkIn: self.info += u",checkIn=%s" % checkIn
        if validate: self.info += u",validate=%s" % validate
        if version: self.info += u",version=%s" % version
        if publishable: self.info += u",publishable=%s" % publishable
        if setLinks: self.info += u",setLinks=%s" % setLinks
        if reason: self.info += u",reason=%s" % reason
        self.info += u")"

    def cdrGetDoc(self, node):
        id = u"???"
        lock = None
        ver = None
        for child in node.childNodes:
            if child.nodeName == "DocId":
                id = cdr.getTextContent(child)
            elif child.nodeName == "Lock":
                lock = cdr.getTextContent(child)
            elif child.nodeName == "DocVersion":
                ver = cdr.getTextContent(child)
        self.info = u"CdrGetDoc(id=%s" % id
        if lock:
            self.info += u",%s" % lock
        if ver:
            self.info += u",%s" % ver
        self.info += u")"

    def cdrLogon(self, node):
        uid = u"???"
        pwd = u"???"
        for child in node.childNodes:
            if child.nodeName == "UserName":
                uid = cdr.getTextContent(child)
            elif child.nodeName == "Password":
                pwd = cdr.getTextContent(child)
        self.info = u"CdrLogon(uid=%s,pwd=%s)" % (uid, u"$$$$$$$$$")

    def cdrFilter(self, node):
        filters = []
        params  = []
        doc = u"???"
        for child in node.childNodes:
            if child.nodeName == "Filter":
                href = child.getAttribute("href")
                name = child.getAttribute("Name")
                if href:
                    filters.append(href)
                elif name:
                    filters.append(name)
                else:
                    filters.append(u"<inline>")
            elif child.nodeName == "Document":
                href = child.getAttribute("href")
                ver  = child.getAttribute("version")
                if href:
                    doc = href
                    if ver:
                        doc += (u"/%s" % ver)
                else:
                    doc = u"<inline>"
            elif child.nodeName == "Parms":
                for parm in child.childNodes:
                    if parm.nodeName == "Parm":
                        name = u"???"
                        val  = u"???"
                        for parmChild in parm.childNodes:
                            if parmChild.nodeName == "Name":
                                name = cdr.getTextContent(parmChild)
                            elif parmChild.nodeName == "Value":
                                val = cdr.getTextContent(parmChild)
                        params.append("%s=%s" % (name, val))
        self.info = u"CdrFilter(filters=[%s],doc=%s" % (u",".join(filters),
                                                        doc)
        if params: self.info += u",params=[%s]" % u";".join(params)
        self.info += u")"

    def cdrLastVersions(self, node):
        for child in node.childNodes:
            if child.nodeName == "DocId":
                self.info = u"CdrLastVersions(docId=%s)" % \
                            cdr.getTextContent(child)
                return
        self.info = u"CdrLastVersions(docId=???)"

    def __repr__(self): return self.info

title = u"CDR Commands between %s and %s" % (start, end)
html = u"""\
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
    dom = xml.dom.minidom.parseString(commandSet.encode('utf-8'))
    for cmdNode in dom.documentElement.childNodes:
        if cmdNode.nodeName == "CdrCommand":
            cmd = CdrCommand(cmdNode)
            html += u"""\
   <tr>
    <td valign='top'>%d</td>
    <td nowrap='1' valign='top'>%s</td>
    <td nowrap='1'>%s</td>
   </tr>
""" % (thread, received, cmd)
    row = cursor.fetchone()
cdrcgi.sendPage(html + u"""\
  </table>
 </body>
</html>
""")
