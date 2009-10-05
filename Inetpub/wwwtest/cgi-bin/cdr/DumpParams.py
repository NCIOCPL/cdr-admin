import cgi
fields = cgi.FieldStorage()
output = \
"""Content-type: text/html

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
if not fields:
    import os, sys
    for key in os.environ:
        output += """\
   <tr>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (key, os.environ[key])
    output += """\
   <tr>
    <td>cwd</td>
    <td>%s</td>
   </tr>
   <tr>
    <td>argv[0]</td>
    <td>%s</td>
   </tr>
""" % (os.getcwd(), sys.argv[0])
for field in fields.keys():
    if type(fields[field]) == type([]):
        for f in fields[field]:
            output += """\
   <TR>
    <TD>%s</TD>
    <TD>%s</TD>
   </TR>
""" % (field, f.value)
    else:
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
