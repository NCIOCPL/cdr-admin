#----------------------------------------------------------------------
# Generate PostScript for a Summary mailer (also has some support for
# protocol mailers).
#----------------------------------------------------------------------
import cdrdb, cdrcgi, re, sys
sys.path.insert(0, "d:\\cdr\\mailers")
import cdr, cdrxmllatex, cgi, cdrcgi, os, tempfile

#----------------------------------------------------------------------
# Object for results of an external command.
#----------------------------------------------------------------------
class CommandResult:
    def __init__(self, code, output, error = None):
        self.code   = code
        self.output = output
        self.error  = error

#----------------------------------------------------------------------
# Run an external command.
#----------------------------------------------------------------------
def runCommand(command):
    commandStream = os.popen('%s 2>&1' % command)
    output = commandStream.read()
    code = commandStream.close()
    return CommandResult(code, output)

LOPTS   = ("-halt-on-error -quiet -interaction batchmode "
           "-include-directory d:/cdr/mailers/style")
#LOPTS   = ("-halt-on-error -interaction batchmode "
#           "-include-directory d:/cdr/mailers/style")
#LOPTS   = ("-interaction batchmode")
fields  = cgi.FieldStorage()
docId   = fields and fields.getvalue("DocId") or cdrcgi.bail("No Doc ID")
digits  = re.sub(r"[^\d]+", "", docId)
version = fields and fields.getvalue("ver") or None
id      = int(digits)
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()
cursor.execute("""\
    SELECT t.name
      FROM doc_type t
      JOIN document d
        ON d.doc_type = t.id
     WHERE d.id = ?""", id)
row     = cursor.fetchone()
if not row:
    cdrcgi.bail("Cannot find document %s" % docId)
typNam  = row[0]
if typNam.upper() == "SUMMARY":
    filters = ["set:Mailer Summary Set"]
    docType = "Summary"
elif typNam.upper() == "INSCOPEPROTOCOL":
    filters = ["set:Mailer InScopeProtocol Set"]
    docType = "Protocol"
resp    = cdr.filterDoc("guest", filters, docId, docVer = version)
if type(resp) in (str, unicode): cdrcgi.bail(resp)
if not resp[0]: cdrcgi.bail(resp[1])
if os.environ.has_key("TMP"):
    tempfile.tempdir = os.environ["TMP"]
where = tempfile.mktemp("mailerwork")
abspath = os.path.abspath(where)
try:
    os.mkdir(abspath)
except Exception, info:
    cdrcgi.bail("Cannot create directory %s" % abspath)
try:
    os.chdir(abspath)
except Exception, info:
    cdrcgi.bail("Cannot cd to %s" % abspath)
latex   = cdrxmllatex.makeLatex (resp[0], docType, "")
filename = docId + ".tex"

try:
    texFile  = open(filename, "wb")
    texFile.write(latex.getLatex())
    texFile.close()
except:
    cdrcgi.bail("Cannot write %s" % filename)

cmd = "latex %s %s" % (LOPTS, filename)
cmd = '"D:\\Program Files\\MiKTeX\\miktex\\bin\\latex.EXE" %s %s' % (LOPTS, filename)

# Accessing /tmp should always work and not result in permission problems
# -----------------------------------------------------------------------
# cmd = '/tmp/latex.exe %s %s' % (LOPTS, filename)
# cmd = "/tmp/test.py"
# cmd = '"D:\\Program Files\\MiKTeX\\miktex\\bin\\test.py" %s %s' % (LOPTS, filename)

for unused in range(3):
    commandResult = runCommand(cmd)
    # cdrcgi.bail(repr(commandResult.output))
    if commandResult.code:
        cdrcgi.bail("Failure running %s: %s" % (cmd, commandResult.output))
    #rc = os.system("latex %s %s" % (LOPTS, filename))
    #if rc:
    #    cdrcgi.bail("Failure running LaTeX processor on %s" % filename)
#rc = os.system("dvips -q %s" % docId)
#if rc:
#    cdrcgi.bail("Failure running dvips processor on %s.dvi" % docId)
cmd = "dvips -q %s" % docId
commandResult = runCommand(cmd)
if commandResult.code:
    cdrcgi.bail("Failure running %s: %s" % (cmd, commandResult.output))
try:
    psFile = open(docId + ".ps")
    psDoc  = psFile.read()
    psFile.close()
except:
    cdrcgi.bail("Failure reading %s.ps" % docId)
print """\
Content-type: application/postscript

%s""" % psDoc
