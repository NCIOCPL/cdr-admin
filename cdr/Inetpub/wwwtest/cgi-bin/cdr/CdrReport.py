#----------------------------------------------------------------------
#
# $Id: CdrReport.py,v 1.3 2001-04-08 22:53:54 bkline Exp $
#
# Prototype for CDR reporting/formatting web wrapper.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2001/03/27 21:17:40  bkline
# Extracted some common functionality out to cdrcgi.py.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
days    = fields and fields.getvalue("Days") or None

#----------------------------------------------------------------------
# Do the report if we have a request.
#----------------------------------------------------------------------
if days:
    diff    = "0000-00-%02d" % string.atoi(days)
    parms   = (('InactivityLength', diff),)
    logon   = ('rmk','***REDACTED***')
    name    = 'Inactive Checked Out Documents'
    report  = cdr.report(logon, name, parms)
    report  = re.sub("<!\[CDATA\[", "", report)
    report  = re.sub("\]\]>", "", report)
    html    = cdr.filterDoc(logon, 'CDR0000190706', doc=report)
    html    = unicode(html, 'utf-8').encode('latin-1')
    html    = re.sub('@@DAYS@@', days, html)
    cdrcgi.sendPage(html)

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
else:
    title   = "Inactive Documents"
    instr   = "Select Options and Submit Request"
    buttons = ("Submit Request",)
    header  = cdrcgi.header(title, title, instr, "CdrReport.py", buttons)
    form    = """\
        <TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>
        <TR>
          <TD ALIGN='right'><B>Days of Inactivity&nbsp;</B></TD>
          <TD><INPUT NAME='Days' VALUE='2'></TD>
        </TR>
       </TABLE>
      </FORM>
     </BODY>
    </HTML>
    """
    cdrcgi.sendPage(header + form)
