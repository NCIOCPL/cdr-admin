#----------------------------------------------------------------------
# Prototype for CDR reporting/formatting web wrapper.
# BZIssue::255 - change report title at Margaret's request
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
