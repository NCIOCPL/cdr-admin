#----------------------------------------------------------------------
# $Id: CdrReport.py,v 1.1 2001-03-26 12:21:03 bkline Exp $
#
# Prototype for CDR reporting/formatting web wrapper.
#----------------------------------------------------------------------
import cgi

#----------------------------------------------------------------------
# Set some string variables.
#----------------------------------------------------------------------
title = "CDR Reporting and Printing"
instr = "Select Options and Submit Request"
hdr   = cdrcgi.header(title, banner, instr, "CdrReport.py", buttons)
form  = """Content-type: text/html
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML><HEAD><TITLE>%s</TITLE></HEAD>
<BASEFONT FACE='Arial, Helvetica, sans-serif'>
<LINK REL='STYLESHEET' HREF='/stylesheets/dataform.css'>
<BODY BACKGROUND='/images/back.jpg' BGCOLOR='#2F5E5E'>
<FORM ACTION='/cgi-bin/cdr/CdrReport.py' METHOD='POST'>
<TABLE WIDTH=100%% CELLSPACING='0' CELLPADDING='0' BORDER='0'>
  <TR>
    <TH NOWRAP BGCOLOR='silver' ALIGN='left'
        BACKGROUND='/images/nav1.jpg'>
        <FONT SIZE='6' COLOR='white'>&nbsp;%s</FONT>
    </TH>
    <TD BGCOLOR='silver' VALIGN='middle' ALIGN='right' WIDTH='100%%'
        BACKGROUND='/images/nav1.jpg'>
        <INPUT TYPE='hidden' NAME='FormMode' VALUE='View'>&nbsp;
        <INPUT TYPE='submit' NAME='NewQuery'
               VALUE='Submit Request'>&nbsp;
    </TD>
  </TR>
  <TR>
    <TD BGCOLOR=#FFFFCC COLSPAN=3>
        <FONT SIZE=-1 color='navy'>&nbsp;&nbsp;%s<BR>
        </FONT>
    </TD>
  </TR>
</TABLE>
<BR><BR>
<CENTER>
<TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>
  <!--
  <TR>
    <TH>Setting</TH>
    <TH>Value</TH>
  </TR>
   -->
  <TR>
    <TD ALIGN='right'><B>CDR User Name&nbsp;</B></TD>
    <TD><INPUT NAME='UserName'></TD>
  </TR>
  <TR>
    <TD ALIGN='right'><B>CDR Password&nbsp;</B></TD>
    <TD><INPUT TYPE='password' NAME='Password'></TD>
  </TR>
  <TR>
    <TD ALIGN='right'><B>CDR Document ID&nbsp;</B></TD>
    <TD><INPUT NAME='DocID'></TD>
  </TR>
  <TR>
    <TD ALIGN='right'><B>XSL/T Filter&nbsp;</B></TD>
    <TD VALIGN='top'>
      <SELECT NAME='Filter'>
        <OPTION VALUE='CDR190703' SELECTED>Fancy Filter&nbsp;</OPTION>
        <OPTION VALUE='CDR190703'>Plain Filter&nbsp;</OPTION>
      </SELECT>
    </TD>
  </TR>
</TABLE>
</CENTER>
</FORM>
</BODY>
</HTML>""" % (title, title, instr)

#----------------------------------------------------------------------
# Get the form variables and decide what to do.
#----------------------------------------------------------------------
fields = cgi.FieldStorage()

if not fields.has_key("FormMode"):
    # This is the first call: just put up the form.
    print form
else:
    import cdr
    print "Content-type: text/html\n"
    if fields.has_key("session"):
        credentials = fields["session"].value
    else:
        credentials = (fields["UserName"].value, fields["Password"].value)
    print cdr.filterDoc(credentials, fields["DocID"].value,
                                     fields["Filter"].value)
