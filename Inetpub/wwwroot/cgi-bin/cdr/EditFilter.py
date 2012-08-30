#----------------------------------------------------------------------
#
# $Id$
#
# Original interface for editing CDR filter documents.  Now used for
# viewing and comparing filters only.
#
# BZIssue::2561
# BZIssue::3716
#
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Import required modules.
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, os, re, cdrcgi, time

#----------------------------------------------------------------------
# Set some initial values.
#----------------------------------------------------------------------
banner   = "View CDR Filter"
title    = "View CDR Filter"

#----------------------------------------------------------------------
# Load the fields from the form.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
if not fields: cdrcgi.bail("Unable to read form fields", banner)
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
version    = fields.getvalue('version')
logName    = "%s/view-filter.log" % cdr.DEFAULT_LOGDIR
debugging  = True
if not session: cdrcgi.bail("Unable to log into CDR Server", banner)
if not request: cdrcgi.bail("No request submitted", banner)

#----------------------------------------------------------------------
# Logging to keep an eye on problems.
#----------------------------------------------------------------------
def debugLog(what):
    if debugging:
        try:
            f = open(logName, "a")
            f.write("%s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), what))
            f.close()
        except Exception, info:
            cdrcgi.bail("Failure writing to %s: %s" % (logName, str(info)))

#----------------------------------------------------------------------
# Display the CDR document form.
#----------------------------------------------------------------------
def showForm(doc):
    hdr = cdrcgi.header(title, banner, banner, "EditFilter.py", (),
                        numBreaks = 1)
    html = hdr + u"""\
   <br>
   <textarea name='Doc' rows='40' cols='80'>%s</textarea>
   <input type='hidden' name='%s' value='%s'>
   <br>
   <br>
   <input type='submit' name='%s' value='Compare With'>&nbsp;&nbsp;
   <input name='DiffWith' value='bach'>
  </form>
 </body>
</html>
""" % (doc.replace('\r', ''),
       cdrcgi.SESSION,
       session,
       cdrcgi.REQUEST)
    cdrcgi.sendPage(html)

#----------------------------------------------------------------------
# Don't leave dross around if we can help it.
#----------------------------------------------------------------------
def cleanup(abspath):
    debugLog("cleaning up %s" % abspath)
    try:
        os.chdir("..")
        runCommand("rm -rf %s" % abspath)
    except:
        pass

#----------------------------------------------------------------------
# Fetch a document by title for a specified server.
#----------------------------------------------------------------------
def getFilterXml(title, server = 'localhost'):
    filters = ['name:Fast Denormalization Filter With Indent']
    try:
        conn = cdrdb.connect('CdrGuest', server)
        cursor = conn.cursor()
        cursor.execute("""\
                SELECT d.xml
                  FROM document d
                  JOIN doc_type t
                    ON t.id = d.doc_type
                 WHERE t.name = 'Filter'
                   AND d.title = ?""", title)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Cannot find filter '%s' on %s" %
                    (cgi.escape(title), server))
        if len(rows) > 1:
            cdrcgi.bail("Ambiguous filter document title '%s' on %s" %
                    (cgi.escape(title), server))
        return rows[0][0].replace('\r', '')

    except Exception, info:
        cdrcgi.bail("Failure retrieving '%s' from %s: %s" %
                    (cgi.escape(title), server, str(info)))

#----------------------------------------------------------------------
# Object for results of an external command.
#----------------------------------------------------------------------
class CommandResult:
    def __init__(self, code, output):
        self.code   = code
        self.output = output

#----------------------------------------------------------------------
# Run an external command.
#----------------------------------------------------------------------
def runCommand(command):
    debugLog("runCommand(%s)" % command)
    try:
        commandStream = os.popen('%s 2>&1' % command)
        output = commandStream.read()
        code = commandStream.close()
        return CommandResult(code, output)
    except Exception, info:
        debugLog("failure running command: %s" % str(info))

#----------------------------------------------------------------------
# Load an existing document.
#----------------------------------------------------------------------
if request == "View":
    if not fields.has_key(cdrcgi.DOCID):
        cdrcgi.bail("No document ID specified")
    doc = cdr.getDoc(session, fields[cdrcgi.DOCID].value)
    doc = cdrcgi.decode(doc)
    if doc.find("<Errors>") >= 0:
        cdrcgi.bail(doc)
    showForm(cgi.escape(doc))

#--------------------------------------------------------------------
# Show the differences with a copy of the filter on another server.
#--------------------------------------------------------------------
elif request == 'Compare With':
    if not fields.has_key("Doc"):
        cdrcgi.bail("No document found to compare")
    if not fields.has_key("DiffWith"):
        cdrcgi.bail("No server specified for comparison")
    doc = fields["Doc"].value
    server = fields["DiffWith"].value
    pattern = re.compile(r"<DocTitle[^>]*>([^<]+)</DocTitle>", re.DOTALL)
    match = pattern.search(doc)
    if not match: cdrcgi.bail("No DocTitle found")
    title = match.group(1)
    doc1 = getFilterXml(title, 'localhost')
    doc2 = getFilterXml(title, server)
    name1 = "localhost-copy.xml"
    name2 = "%s-copy.xml" % server
    cmd = "/cygwin/bin/diff -au %s %s" % (name1, name2)
    try:
        workDir = cdr.makeTempDir('diff')
    except Exception, args:
        cdrcgi.bail("%s: %s" % (args[0], args[1]))
    f1 = open(name1, "w")
    f1.write(doc1.encode('utf-8'))
    f1.close()
    f2 = open(name2, "w")
    f2.write(doc2.encode('utf-8'))
    f2.close()
    result = cdr.runCommand(cmd)
    cleanup(workDir)
    report = cgi.escape(result.output)
    if report.strip():
        title = "Differences between %s and %s" % (name1, name2)
    else:
        title = "%s and %s are identical" % (name1, name2)
    cdrcgi.sendPage(u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <h3>%s</h3>
  <pre>%s</pre>
 </body>
</html>""" % (title, title, report.replace('\r', '')))

#----------------------------------------------------------------------
# Tell the user we don't know how to do what he asked.
#----------------------------------------------------------------------
else: cdrcgi.bail("Request not yet implemented: " + request)
