#----------------------------------------------------------------------
#
# $Id: CdrReport.py,v 1.2 2001-03-27 21:17:40 bkline Exp $
#
# Prototype for CDR reporting/formatting web wrapper.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re


#----------------------------------------------------------------------
# Set some session and form variables.
#----------------------------------------------------------------------
title   = "CDR Reporting and Printing"
instr   = "Select Options and Submit Request"
buttons = ("Submit Request",)
header  = cdrcgi.header(title, title, instr, "CdrReport.py", buttons)
fields  = cgi.FieldStorage()
session = fields and cdrcgi.getSession(fields) or None
request = fields and cdrcgi.getRequest(fields) or None
docId   = fields and fields.getvalue(cdrcgi.DOCID) or 'CDR106085'
filtId  = fields and fields.getvalue(cdrcgi.FILTER) or 'CDR190703'

#----------------------------------------------------------------------
# Build some data-entry fields for a new request.
#----------------------------------------------------------------------
form    = "<TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>\n"
if session:
    form = form + "<INPUT TYPE='hidden' NAME='%s' VALUE='%s'>\n" % (
                  cdrcgi.SESSION, session)
else:
    form = form + """\
        <TR>
         <TD ALIGN='right'><B>CDR User Name&nbsp;</B></TD>
         <TD><INPUT NAME='%s'></TD>
        </TR>
        <TR>
         <TD ALIGN='right'><B>CDR Password&nbsp;</B></TD>
         <TD><INPUT TYPE='password' NAME='%s'></TD>
        </TR>\n""" % (cdrcgi.USERNAME, cdrcgi.PASSWORD)
form = form + """\
        <TR>
          <TD ALIGN='right'><B>Document ID&nbsp;</B></TD>
          <TD><INPUT NAME='%s' VALUE='%s'></TD>
        </TR>
        <TR>
          <TD ALIGN='right'><B>Filter ID&nbsp;</B></TD>
          <TD><INPUT NAME='%s' VALUE='%s'></TD>
        </TR>
       </TABLE>
      </FORM>\n""" % (cdrcgi.DOCID, docId, cdrcgi.FILTER, filtId)

#----------------------------------------------------------------------
# Print what we have so far
#----------------------------------------------------------------------
print header + form

#----------------------------------------------------------------------
# If we have a filter request, do it.
#----------------------------------------------------------------------
if session and docId and filtId and request == "Submit Request":
    print "<HR>"
    doc = cdr.filterDoc(session, docId, filtId)
    doc = re.sub("@@DOCID@@", docId, doc)
    print "<TABLE WIDTH='100%' CELLSPACING='0' CELLPADDING='0' BORDER='0'>" 
    print "<TR><TD>%s</TD></TR></TABLE>" % doc

#----------------------------------------------------------------------
# Wrap up and go home.
#----------------------------------------------------------------------
print "</BODY></HTML>"
