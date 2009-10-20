#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import os, cgi, cdr, cdrcgi, sys

script   = 'ViewCTGovExports.py'
basedir  = cdr.BASEDIR + '/Output/NLMExport'
fields   = cgi.FieldStorage()
jobName  = fields and fields.getvalue('job')      or None
docName  = fields and fields.getvalue('doc')      or None
manifest = fields and fields.getvalue('manifest') or None
dropped  = fields and fields.getvalue('dropped')  or None
asXml    = fields and fields.getvalue('xml')      or True

if asXml == 'false':
    asXml = False

def showDoc(jobName, docName, asXml = True):
    path = "%s/%s/%s" % (basedir, jobName, docName)
    inFile = file(path, 'rb')
    docBytes = inFile.read()
    inFile.close()
    if asXml:
        sys.stdout.write("""\
Content-type: text/xml

%s
""" % docBytes)
    else:
        print """\
Content-type: text/html

<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <h1>%s</h1>
  <pre>%s</pre>
 </body>
</html>""" % (docName, docName, cgi.escape(docBytes.replace('\r', '')))

def showJob(jobName):
    path = "%s/%s" % (basedir, jobName)
    names = []
    for name in os.listdir(path):
        lowerName = name.lower()
        if lowerName.endswith('.xml') and lowerName.startswith('cdr'):
            names.append(name)
    names.sort()
    output = ["""\
Content-type: text/html

<html>
 <head>
  <title>CTGov Export Job %s</title>
 </head>
 <body>
  <h1>CTGov Export Job %s</h1>
  <a href='ShowCTGovLog.py?job=%s'>Log File For Export Job</a><br><br>
""" % (jobName, jobName, jobName)]
    if os.path.isfile('%s/%s/manifest.txt' % (basedir, jobName)):
        output.append("""\
  <a href='ViewCTGovExports.py?job=%s&manifest=true'>Manifest File For Export
  Job</a><br><br>
""" % jobName)
    if os.path.isfile('%s/%s/WithdrawnFromPDQ.txt' % (basedir, jobName)):
        output.append("""\
  <a href='ViewCTGovExports.py?job=%s&dropped=true'>'Withdrawn from PDQ' List
  For Export Job</a><br><br>
""" % jobName)
    for name in names:
        url = '%s?job=%s&doc=%s' % (script, jobName, name)
        output.append("""\
  <a href='%s'>%s</a> (<a href='%s&xml=false'>with layout preserved</a>)<br>
""" % (url, name, url))
    output.append("""\
 </body>
</html>""")
    print "".join(output)

def nameSorter(a, b):
    if not a: return -1
    if not b: return 1
    if not a[0].isdigit(): a = a[1:]
    if not b[0].isdigit(): b = b[1:]
    if not a[0].isdigit() and b[0].isdigit():
        return 1
    if not b[0].isdigit() and a[0].isdigit():
        return -1
    return cmp(b, a)

def showJobs():
    names = []
    for name in os.listdir(basedir):
        if os.path.isdir("%s/%s" % (basedir, name)):
            names.append(name)
    names.sort(nameSorter)
    output = ["""\
Content-type: text/html

<html>
 <head>
  <title>CTGov Export Jobs</title>
 </head>
 <body>
  <h1>CTGov Export Jobs</h1>
"""]
    for name in names:
        output.append("""\
  <a href='%s?job=%s'>%s</a><br>
""" % (script, name, name))
    output.append("""\
 </body>
</html>""")
    print "".join(output)

def main():
    if jobName:
        if manifest:
            showDoc(jobName, 'manifest.txt', False)
        elif dropped:
            showDoc(jobName, 'WithdrawnFromPDQ.txt', False)
        elif docName:
            showDoc(jobName, docName, asXml)
        else:
            showJob(jobName)
    else:
        showJobs()
try:
    main()
except Exception, e:
    cdrcgi.bail(e)
