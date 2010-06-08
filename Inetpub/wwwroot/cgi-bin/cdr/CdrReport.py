#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for CDR reporting/formatting web wrapper.
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2002/08/15 19:17:46  bkline
# Fixed report name; replaced hardcoded credentials.
#
# Revision 1.6  2002/06/07 13:32:12  bkline
# Issue #255: changed report title at Margaret's request.
#
# Revision 1.5  2002/02/21 15:22:02  bkline
# Added navigation buttons.
#
# Revision 1.4  2001/12/01 17:56:26  bkline
# Changed FilterDoc() call to match new return value type.
#
# Revision 1.3  2001/04/08 22:53:54  bkline
# First working version for inactive documents report.
#
# Revision 1.2  2001/03/27 21:17:40  bkline
# Extracted some common functionality out to cdrcgi.py.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
days    = fields and fields.getvalue("Days") or None
SUBMENU = "Report Menu"

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Do the report if we have a request.
#----------------------------------------------------------------------
if request and days:
    diff    = "0000-00-%02d" % string.atoi(days)
    parms   = (('InactivityLength', diff),)
    name    = 'Inactive Checked Out Documents'
    report  = cdr.report(session, name, parms)
    report  = re.sub("<!\[CDATA\[", "", report)
    report  = re.sub("\]\]>", "", report)
    html    = cdr.filterDoc(session, ['name:Inactivity Report Filter'], 
                            doc=report)[0]
    html    = unicode(html, 'utf-8').encode('latin-1')
    html    = re.sub('@@DAYS@@', days, html)
    cdrcgi.sendPage(u"".join(html))

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
else:
    title   = "CDR Administration"
    instr   = "Checked Out Documents With No Activity"
    buttons = ("Submit Request", SUBMENU, cdrcgi.MAINMENU)
    header  = cdrcgi.header(title, title, instr, "CdrReport.py", buttons)
    form    = u"""\
        <INPUT TYPE='hidden' NAME='%s' VALUE='%s'
        <TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>
        <TR>
          <TD ALIGN='right'><B>Days of Inactivity&nbsp;</B></TD>
          <TD><INPUT NAME='Days' VALUE='10'></TD>
        </TR>
       </TABLE>
      </FORM>
     </BODY>
    </HTML>
    """ % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)
