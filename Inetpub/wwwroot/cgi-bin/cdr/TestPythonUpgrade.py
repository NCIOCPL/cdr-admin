#----------------------------------------------------------------------
# Smoke test following an upgrade of Python on a CDR Windows server.
# Shows versions of everything.
#----------------------------------------------------------------------
def sendPage(what):
    print("""\
Content-type: text/html

%s""" % what)

def show(component, version):
    html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (cgi.escape(component), cgi.escape(version)))
html = ["""\
<html>
 <head>
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
    import sys
    import cgi
    import MySQLdb
    import pip
    from PIL import Image
    import lxml.etree
    import xlrd
    import xlwt
    import cdr
    import cdrdb
    import requests
    import apns
    import pymssql
    import cdrmailcommon
    conn = cdrmailcommon.emailerConn('dropbox')
    show("Python", sys.version)
    show("pip", pip.__version__)
    show("lxml", "%d.%d.%d.%d" % lxml.etree.LXML_VERSION[:4])
    show("Image", Image.VERSION)
    show("xlrd", xlrd.__VERSION__)
    show("xlwt", xlwt.__VERSION__)
    show("requests", requests.__version__)
    show("pymssql", pymssql.__version__)
    show("MySQLdb", "%s.%s.%s" % MySQLdb.version_info[:3])
    show("MySQL Server", "%s.%s" % conn._server_version[:2])
    distros = pip.get_installed_distributions()
    distros = sorted(distros, key=lambda d: str(d).lower())
    packages = "".join("<li>%s</li>" % d for d in distros)
    html.append("""\
  </table>
  <ul>%s</ul>
 </body>
</html>""" % packages)
    sendPage("".join(html))
except Exception as e:
    sendPage("<pre>%s</pre>" % e)
