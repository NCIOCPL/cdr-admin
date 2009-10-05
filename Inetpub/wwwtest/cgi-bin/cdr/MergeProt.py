#----------------------------------------------------------------------
#
# $Id: MergeProt.py,v 1.3 2004-02-05 13:33:05 bkline Exp $
#
# Merge ScientificProtocolInfo document into InScopeProtocol document.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/02/21 22:34:00  bkline
# Added navigation buttons.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
sourceId = fields and fields.getvalue("SourceId") or None
targetId = fields and fields.getvalue("TargetId") or None
title    = "CDR Administration"
section  = "Merge Protocol Documents"
buttons  = ["Merge", cdrcgi.MAINMENU, "Log Out"]
#script  = "DumpParams.pl"
script   = "MergeProt.py"

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
# Return to the main menu if requested.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Handle request to delete the user.
#----------------------------------------------------------------------
if request == "Merge":
    if not sourceId or not targetId:
        cdrcgi.bail("Both document IDs are required.")
    cmd = """\
<CdrMergeProt>
 <SourceDoc>%s</SourceDoc>
 <TargetDoc>%s</TargetDoc>
</CdrMergeProt>
""" % (cdr.normalize(sourceId), cdr.normalize(targetId))
    rsp = cdr.sendCommands(cdr.wrapCommand(cmd, session))
    err = cdr.checkErr(rsp)
    if err: cdrcgi.bail(err)
    section = "Protocol successfully merged"

#----------------------------------------------------------------------
# Display the form for merging two protocol documents.
#----------------------------------------------------------------------
header  = cdrcgi.header(title, title, section, script, buttons)
form = """\
<H2>Specify Protocol Documents to be Merged</H2>
<TABLE>
 <TR>
  <TD ALIGN='right' NOWRAP><B>InScopeProtocol ID:</B></TD>
  <TD><INPUT NAME='TargetId'><TD>
 </TR>
 <TR>
  <TD ALIGN='right' NOWRAP><B>ScientificProtocolInfo ID:</B></TD>
  <TD><INPUT NAME='SourceId'><TD>
 </TR>
</TABLE>
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
