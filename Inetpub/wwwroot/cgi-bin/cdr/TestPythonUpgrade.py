#----------------------------------------------------------------------
# Smoke test following an upgrade of Python on a CDR Windows server.
# Shows versions of everything.
#----------------------------------------------------------------------
def sendPage(what):
    sys.stdout.buffer.write(f"""\
Content-type: text/html

{what}""".encode("utf-8"))

def show(component, version):
    html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (html_escape(component), html_escape(version)))
html = ["""\
<html>
 <head>
  <meta charset="utf-8">
  <title>Python Upgrade Information</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   th { color: blue; }
   h1 { font-size: 14pt; color: maroon; }
  </style>
 </head>
 <body>
  <h1>Python Upgrade Information</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Component</th>
    <th>Version</th>
   </tr>
"""]
try:
    from html import escape as html_escape
    import pkg_resources
    import sys
    import cgi
    import pip
    from PIL import Image
    import lxml.etree
    import xlrd
    import xlwt
    import cdr
    import requests
    import apscheduler
    import tornado
    import pyodbc
    #import pymssql
    from cdrapi import db
    from cdrapi import docs
    from cdrapi import publishing
    from cdrapi import reports
    from cdrapi import searches
    from cdrapi import settings
    from cdrapi import users
    show("Python", sys.version)
    show("pip", pip.__version__)
    show("lxml", "%d.%d.%d.%d" % lxml.etree.LXML_VERSION[:4])
    show("Image", Image.__version__)
    show("xlrd", xlrd.__VERSION__)
    show("xlwt", xlwt.__VERSION__)
    show("requests", requests.__version__)
    #show("pymssql", pymssql.__version__)
    show("pyodbc", pyodbc.version)
    show("apscheduler", apscheduler.version)
    show("tornado", tornado.version)
    env = pkg_resources.Environment()
    packages = []
    for name in sorted(env, key=str.lower):
        for package in env[name]:
            packages.append(f"<li>{package}</li>")
    html.append("""\
  </table>
  <ul>%s</ul>
 </body>
</html>""" % "\n".join(packages))
    sendPage("".join(html))
except Exception as e:
    sendPage("<pre>%s</pre>" % e)
