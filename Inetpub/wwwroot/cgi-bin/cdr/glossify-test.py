#----------------------------------------------------------------------
#
# Tool for checking the health of the glossifier service.  The most common
# cause of failure is someone at cancer.gov trying to connect using a
# temporary URL (on Verdi) I set up for Bryan for a one-time test.
# The correct URL for the service is:
#
#     http://pdqupdate.cancer.gov/u/glossify
#
#----------------------------------------------------------------------
import sys, cdrutil
def bail(out):
    print """\
Content-type: text/html

<pre style='color: red'>%s</pre>""" % out
    sys.exit(0)

try:
    import suds.client, cgi
except Exception, e:
    bail("import: %s" % e)
env = cdrutil.getEnvironment()
if env == "CBIIT":
    hosts = cdrutil.AppHost(env, cdrutil.getTier())
    host = hosts.getHostNames("GLOSSIFIERWEB").name
    URL = "http://%s/cgi-bin/glossify" % host
else:
    URL = 'http://pdqupdate.cancer.gov/u/glossify'
FRAGMENT = (u"<p>Gerota\u2019s capsule breast cancer and mammography "
            u"as well as invasive breast cancer, too</p>")

try:
    fields = cgi.FieldStorage()
    frag = fields.getvalue('frag') or FRAGMENT
    lang = fields.getlist('lang')
    client = suds.client.Client(URL)
    dictionaries = client.factory.create('ArrayOfString')
    dictionaries.string.append(u'Cancer.gov')
    languages = client.factory.create('ArrayOfString')
    languages.string = lang
    if type(frag) is not unicode:
        frag = unicode(frag, 'utf-8')
    result = client.service.glossify(frag, dictionaries, languages)
    html = u"""\
<html>
 <head>
  <title>Glossifier Test</title>
  <meta http-equiv='Content-Type' content='text/html;charset=utf-8'></meta>
  <style type='text/css'>
   * { font-family: Verdana, Arial, sans-serif }
   legend { color: maroon }
   fieldset { border: 1px maroon solid; width: 750px; }
   textarea { width: 600px; height: 300px; }
   label { float: left; width: 100px; clear: both; text-align: right; padding-right: 10px; }
   select, textarea { float: left; }
   select { width: 600px; }
   input { clear: both; }
   pre { width: 500px; border: green 1px solid; padding: 5px; }
  </style>
 </head>
 <body>
  <form method='POST' action='glossify-test.py'>
   <fieldset>
    <legend>Glossifier Test</legend>
    <label for='lang'>Languages</label>
    <select name='lang' multiple='multiple'>
     <option value='en'>English</option>
     <option value='es'>Spanish</option>
    </select>
    <label for='frag'>Fragment</label>
    <textarea name='frag'>%s</textarea>
   </fieldset>
   <br />
   <input type='submit' />
  </form>
  <pre>%s</pre>
 </body>
</html>""" % (frag, result)
    print "Content-type: text/html; charset=utf-8\n"
    print html.encode('utf-8')
except Exception, e:
    bail("oops: %s" % e)
