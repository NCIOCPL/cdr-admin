#----------------------------------------------------------------------
# Compare filters between the current tier and the production tier.
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, os, tempfile, re, shutil, glob
from cdrapi import db
from cdrapi.settings import Tier
from html import escape as html_escape

#----------------------------------------------------------------------
# Make sure we're not on the production server.
#----------------------------------------------------------------------
if cdr.isProdHost():
    cdrcgi.bail("Can't compare the production server to itself")
tier_name = Tier().name

#----------------------------------------------------------------------
# Create a temporary working area.
#----------------------------------------------------------------------
def makeTempDir():
    tempfile.tempdir = "d:\\tmp"
    where = tempfile.mktemp("diff")
    abspath = os.path.abspath(where)
    print(abspath)
    try: os.mkdir(abspath)
    except: cdrcgi.bail("Cannot create directory %s" % abspath)
    try: os.chdir(abspath)
    except:
        cleanup(abspath)
        cdrcgi.bail("Cannot cd to %s" % abspath)
    return abspath

#----------------------------------------------------------------------
# Get the filters from the local tier.
#----------------------------------------------------------------------
def getLocalFilters(tmpDir):
    try: os.mkdir(tier_name)
    except:
        cleanup(tmpDir)
        cdrcgi.bail("Cannot create directory %s" % tier_name)
    try:
        conn = db.connect(user='CdrGuest')
        curs = conn.cursor()
        curs.execute("""\
            SELECT d.title, d.xml
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE t.name = 'Filter'""")
        rows = curs.fetchall()
    except Exception as e:
        cleanup(tmpDir)
        cdrcgi.bail('Database failure: %s' % e)
    for row in rows:
        try:
            title = row[0].strip()
            title = title.replace(" ", "@@SPACE@@") \
                         .replace(":", "@@COLON@@") \
                         .replace("/", "@@SLASH@@") \
                         .replace("*", "@@STAR@@")
            xml = row[1].replace("\r", "")
            filename = "%s/@@MARK@@%s@@MARK@@" % (tier_name, title)
            open(filename, "w").write(xml.encode('utf-8'))
        except:
            cleanup(tmpDir)
            cdrcgi.bail("Failure writing %s" % filename);

#----------------------------------------------------------------------
# Make a copy of the filters on the production server.
#----------------------------------------------------------------------
def getProdFilters(tmpDir):
    try:
        os.mkdir("PROD")
    except:
        cleanup(tmpDir)
        cdrcgi.bail("Cannot create directory PROD")
    for oldpath in glob.glob("d:/cdr/prod-filters/*"):
        try:
            newpath = "PROD/%s" % os.path.basename(oldpath)
            shutil.copy(oldpath, newpath)
        except:
            cleanup(tmpDir)
            cdrcgi.bail("Failure writing %s" % newpath)

#----------------------------------------------------------------------
# Don't leave dross around if we can help it.
#----------------------------------------------------------------------
def cleanup(abspath):
    try:
        os.chdir("..")
        cdr.runCommand("rm -rf %s" % abspath)
    except:
        pass

#----------------------------------------------------------------------
# Undo our homemade encoding.
#----------------------------------------------------------------------
def unEncode(str):
    return str.replace("@@SPACE@@", " ") \
              .replace("@@COLON@@", ":") \
              .replace("@@SLASH@@", "/") \
              .replace("@@STAR@@", "*")  \
              .replace("@@MARK@@", "")

#----------------------------------------------------------------------
# Create a banner for the report on a single filter.
#----------------------------------------------------------------------
def makeBanner(name):
    line = "*" * 79 + "\n"
    name = (" %s " % name).center(79, "*")
    return "\n\n%s%s\n%s\n" % (line * 2, name, line * 2)

#----------------------------------------------------------------------
# Get the filters.
#----------------------------------------------------------------------
workDir = makeTempDir()
getLocalFilters(workDir)
getProdFilters(workDir)

#----------------------------------------------------------------------
# Compare the filters.
#----------------------------------------------------------------------
result  = cdr.runCommand("diff -aur PROD %s" % tier_name)
lines   = result.output.splitlines()
pattern = re.compile("diff -aur PROD/@@MARK@@(.*?)@@MARK@@")
for i in range(len(lines)):
    match = pattern.match(lines[i])
    if match:
        lines[i] = makeBanner(unEncode(match.group(1)))
report = html_escape(unEncode("\n".join(lines)))
cleanup(workDir)

print("""\
Content-type: text/html; charset: utf-8

<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Filter Comparison Results</title>
 </head>
 <body>
  <h3>The following filters differ between PROD and %s</h3>
  <pre>%s</pre>
 </body>
</html>""" % (tier_name, report))
