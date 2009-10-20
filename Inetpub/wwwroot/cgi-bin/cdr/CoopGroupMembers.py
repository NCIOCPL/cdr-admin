#----------------------------------------------------------------------
#
# $Id$
#
# Generates a report on member organizations and their principal
# investigators for a selected cooperative group.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2004/03/08 17:48:12  venglisc
# Modified length of organization picklist field and added field to allow
# entering a single organization ID. (Bug 1094)
#
# Revision 1.1  2002/06/04 20:16:45  bkline
# New report for member orgs and PIs of cooperative groups.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, time, re

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
coopGroup  = fields and fields.getvalue('CoopGroup') or None
coopGrpId  = fields and fields.getvalue('CoopGroupId') or None
SUBMENU   = "Report Menu"
buttons   = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = "CoopGroupMembers.py"
title     = "CDR Administration"
section   = "Coop Group Member Orgs &amp; Investigators Report"
now       = time.localtime(time.time())

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

#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Gather the list of trial groups from the database.
#----------------------------------------------------------------------
def getGroups():
    try:
        cursor.execute("""\
SELECT DISTINCT d.id,
                d.title
           FROM document d
           JOIN query_term q
             ON q.doc_id = d.id
          WHERE q.path = '/Organization/OrganizationType'
            AND q.value IN ('US clinical trials group',
                            'Non-US clinical trials group')
       ORDER BY d.title""")
        return cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Failure fetching trial group information: %s' % 
                    info[1][0])

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not coopGroup and not coopGrpId:
    header = cdrcgi.header(title, title, section, script, buttons)
    form   = """\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <TABLE>
     <TR>
      <TD align='right'>Organization ID:</TD>
      <TD><INPUT size='20' NAME='CoopGroupId'></TD>
     </TR>
     <TR>
      <TD>or</TD>
     </TR>
     <TR>
      <TD>Organization:</TD>
      <TD>
       <SELECT NAME='CoopGroup'>
""" % (cdrcgi.SESSION, session)

    for grp in getGroups():
        form += """\
        <OPTION VALUE='%d'>[CDR%d] %s</OPTION>
""" % (grp[0], grp[0], grp[1][:80])

    cdrcgi.sendPage(header + form + """\
       </SELECT>
      </TD>
     </TR>
     <TR>
      <TD></TD>
      <TD>
       <font size="-1">
        <B>Note: Org Name truncated at 80 chars</B>
       </font>
      </TD>
     </TR>
    </TABLE>
  </FORM>
 </BODY>
</HTML>
""")

#----------------------------------------------------------------------
# Get the full name for the requesting user.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT fullname
              FROM usr
              JOIN session
                ON session.usr = usr.id
             WHERE session.name = ?""", session)
    usr = cursor.fetchone()[0]
except:
    cdrcgi.bail("Unable to find current user name")

#----------------------------------------------------------------------
# We have a request; do it.
#----------------------------------------------------------------------
# If a Org ID has been entered manually format it and use it.
# Otherwise use the selected Org from the pick list.
# -----------------------------------------------------------
if coopGrpId:
   if coopGrpId == re.sub('[\d+]', '', coopGrpId):
      cdrcgi.bail("Invalid CDR ID entered: %s" % coopGrpId)

   docId = int(re.sub('[\D+]', '', coopGrpId))
else:
   docId = int(coopGroup)

html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR%010d - %s</title>
  <basefont face='Arial, Helvetica, sans-serif'>
 </head>
 <body>
  <center>
   <font size='5'>Coop Group Member Orgs &amp; Investigators Report</font>
  </center>
  <br />
  <br />
  <br />
""" % (docId, time.strftime("%m/%d/%Y", now))

#----------------------------------------------------------------------
# Extract the group's names from the database.
#----------------------------------------------------------------------
fnPath = '/Organization/OrganizationNameInformation/OfficialName/Name'
snPath = '/Organization/OrganizationNameInformation/ShortName/Name'
try:
    cursor.execute("""\
            SELECT TOP 1 value
              FROM query_term
             WHERE doc_id = ?
               AND path = '%s'""" % fnPath, docId)
    row = cursor.fetchone()
    if not row:
        cdrcgi.bail("Unable to find group official name")
    officialName = row[0]
    shortNames = []
    cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE doc_id = ?
               AND path = '%s'""" % snPath, docId)
    for row in cursor.fetchall():
        shortNames.append(row[0])
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching group names: %s' % info[1][0])

html += """\
  <table border='0' width='100%%'>
   <tr>
    <td width='50%%'>
     <b>
      <font size='4'>Organization Name</font>
     </b>
    </td>
    <td>
     <font size='4'>%s</font>
    </td>
   </tr>
   <tr>
    <td>&nbsp;</td>
   </tr>
""" % officialName

for name in shortNames:
    html += """\
   <tr>
    <td width='50%%'>
     <b>
      <font size='4'>Organization Short Name</font>
     </b>
    </td>
    <td>
     <font size='4'>%s</font>
    </td>
   </tr>
   <tr>
    <td>&nbsp;</td>
   </tr>
""" % name

html += """\
  </table>
"""

#----------------------------------------------------------------------
# Some useful types.
#----------------------------------------------------------------------
class MemberOrg:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.piList = []
class PrincipalInvestigator:
    def __init__(self, id, name):
        self.id = id
        self.name = name

#----------------------------------------------------------------------
# Get the main member organizations.
#----------------------------------------------------------------------
mainMembers   = []
mainMemberIds = {}
try:
    cursor.callproc("cdr_coop_group_report", docId)
    cursor.nextset()
    for row in cursor.fetchall():
        org = MemberOrg(row[0], row[1])
        org.amList = []
        mainMembers.append(org)
        mainMemberIds[row[0]] = org
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching main member organizations: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the principal investigators for the main member organizations.
#----------------------------------------------------------------------
try:
    cursor.nextset()
    for row in cursor.fetchall():
        pi = PrincipalInvestigator(row[1], row[2])
        mainMemberIds[row[0]].piList.append(pi)
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching main member PIs: %s' % info[1][0])
   
#----------------------------------------------------------------------
# Get the affiliate members of the group.
#----------------------------------------------------------------------
def makeAmKey(mmId, amId):
    if mmId: return "%d:%d" % (mmId, amId)
    else: return "0:%d" % amId
amKeys   = {}
orphans  = []
try:
    cursor.nextset()
    cursor.nextset()
    for row in cursor.fetchall():
        org = MemberOrg(row[1], row[2])
        if row[0]:
            mainMemberIds[row[0]].amList.append(org)
        else:
            orphans.append(org)
        amKeys[makeAmKey(row[0], row[1])] = org

except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching affiliate members: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the principal investigators for the affiliate member organizations.
#----------------------------------------------------------------------
try:
    cursor.nextset()
    for row in cursor.fetchall():
        pi = PrincipalInvestigator(row[2], row[3])
        amKeys[makeAmKey(row[0], row[1])].piList.append(pi)
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching affiliate member PIs: %s' % info[1][0])

#----------------------------------------------------------------------
# Put together the body of the report.
#
# NOTE: The use of a single table as the format of this report distorts
#       the information.  In particular, the alignment of affiliate
#       members with specific main member PIs implies a relationship
#       which does not exist in the data.  Furthermore, the affiliate
#       members which have no connection with a main member for this
#       group appears after those which do have such a connection,
#       making it appear that the last affiliate members are connected
#       to the last main member.  Nevertheless, Lakshmi insists that
#       the users of this report will know how to interpret it.
#       Another problem caused by the report layout is that it will
#       be difficult to print, because long words will force the 
#       table columns to be too wide even for landscape format.
#----------------------------------------------------------------------
html += """\
  <table border='1' width='100%' cellspacing='0' cellpadding='2'>
   <tr>
    <td align='center' valign='top'>
     <b>
      <font size='3'>Main Member</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>Principal Investigator</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>Affiliate Member</font>
     </b>
    </td>
    <td align='center' valign='top'>
     <b>
      <font size='3'>Affiliate Principal Investigator</font>
     </b>
    </td>
   </tr>
"""

#----------------------------------------------------------------------
# Useful functions for creating rows in the report.
#----------------------------------------------------------------------
def makeCell(obj): return "%s (CDR%010d)" % (obj.name, obj.id)
def flushCells(cells):
    global html 
    html += """\
   <tr>
"""
    for cell in cells:
        html += """\
    <td valign='top'>
     <font size='3'>%s</font>
    </td>
""" % cell

#----------------------------------------------------------------------
# Loop through the group's main members.
#----------------------------------------------------------------------
cells = ["&nbsp;", "&nbsp;", "&nbsp;", "&nbsp;"]
for mm in mainMembers:

    # The unnatural format for the report causes some awkward loop processing.
    piIndex = 0
    amIndex = 0
    cells = [makeCell(mm), "&nbsp;", "&nbsp;", "&nbsp;"]
    if not mm.piList and not mm.amList:
        flushCells(cells)
    while piIndex < len(mm.piList) or amIndex < len(mm.amList):
        if piIndex < len(mm.piList):
            cells[1] = makeCell(mm.piList[piIndex])
            piIndex += 1
        else:
            cells[1] = "&nbsp;"
        if amIndex < len(mm.amList):
            am = mm.amList[amIndex]
            amIndex += 1
            cells[2] = makeCell(am)
            if not am.piList:
                cells[3] = "&nbsp;"
                flushCells(cells)
            else:
                first = 1
                for pi in am.piList:
                    cells[3] = makeCell(pi)
                    if first:
                        first = 0
                    else:
                        if piIndex < len(mm.piList):
                            cells[1] = makeCell(mm.piList[piIndex])
                            piIndex += 1
                        else:
                            cells[1] = "&nbsp;"
                    flushCells(cells)
                    cells[0] = "&nbsp;"
                    cells[2] = "&nbsp;"
        else:
            cells[2] = "&nbsp;"
            cells[3] = "&nbsp;"
            flushCells(cells)
        cells[0] = "&nbsp;"

#----------------------------------------------------------------------
# Now add the rows for affiliate members not connected with a main
# member.
#----------------------------------------------------------------------
cells[0] = "&nbsp;"
cells[1] = "&nbsp;"
for o in orphans:
    cells[2] = makeCell(o)
    if not o.piList:
        cells[3] = "&nbsp;"
        flushCells(cells)
    else:
        for pi in o.piList:
            cells[3] = makeCell(pi)
            flushCells(cells)
            cells[2] = "&nbsp;"

#----------------------------------------------------------------------
# We're done.  Send the user the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(cdrcgi.unicodeToLatin1(html + """\
  </table>
  <br />
  <br />
  <i>
   <font size='3'>%s</font>
  </i>
 </body>
</html>
""" % usr))
