import cgi
fields = cgi.FieldStorage()
output = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>Parameter Dump from Python Script</TITLE>
 </HEAD>
 <BASEFONT FACE='Arial, Helvetica, sans-serif'>
 <BODY>
  <TABLE BORDER='1'>
   <TR>
    <TH>Name</TH>
    <TH>Value</TH>
   </TR>
"""
for field in fields.keys():
    output += """\
   <TR>
    <TD>%s</TD>
    <TD>%s</TD>
   </TR>
""" % (field, fields[field].value)
output += """\
  </TABLE>
 </BODY>
</HTML>
"""
print output
