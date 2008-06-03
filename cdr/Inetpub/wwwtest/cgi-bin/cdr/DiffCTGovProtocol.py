#----------------------------------------------------------------------
#
# $Id: DiffCTGovProtocol.py,v 1.10 2008-06-03 21:58:55 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.9  2005/11/01 23:23:04  ameyer
# Changed order of documents in the diff.  Adjusted flags.
#
# Revision 1.8  2005/10/18 15:32:23  ameyer
# Apply textwrap module to word wrapping docs for diff.
#
# Revision 1.7  2005/10/07 03:08:43  ameyer
# Added colorization.
# Using ascii instead of latin-1.  Need to go over this.
#
# Revision 1.6  2005/10/04 18:18:38  ameyer
# Restructured bailouts when inside a try block to keep the bailout from
# triggering the catch clause.
# Reverted to latin-1 from experimental use of ascii encoding.
#
# Revision 1.5  2005/09/30 03:51:02  ameyer
# Modified report to diff different versions from before (Issue 1845).
#
# Revision 1.4  2005/07/22 19:41:20  venglisc
# Removed print statement in code that caused IIS on BACH to trip up.
# (Bug 1779)
#
# Revision 1.3  2003/12/18 22:05:29  bkline
# Moved the line splitting before the invocation of diff and removed
# the visual clues about where extra line breaks have been added.
#
# Revision 1.2  2003/12/17 13:48:32  bkline
# Implemented wrapping of long lines at Lakshmi's request.
#
# Revision 1.1  2003/12/16 16:10:56  bkline
# Script to show the differences between the current working copy of
# a CTGovProtocol document and the latest publishable version (or
# the first version if there are no publishable versions).
#
#----------------------------------------------------------------------
import cdr, cdrcgi, cdrdb, sys, cgi, re, sys, os, textwrap

#----------------------------------------------------------------------
# Load the fields from the form.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
docId      = fields and fields.getvalue('DocId') or sys.argv[1]

#----------------------------------------------------------------------
# Don't leave dross around if we can help it.
#----------------------------------------------------------------------
def cleanup(abspath):
    try:
        os.chdir("..")
        cdr.runCommand("rm -rf %s" % abspath)
    except:
        pass

#--------------------------------------------------------------------
# Wrap long lines in the report.
#--------------------------------------------------------------------
def wrap(report):
    report = report.replace("\r", "")
    oldLines = report.split("\n")
    newLines = []
    for line in oldLines:
        # Wrap, terminate, and begin each line with a space
        newLines.append(" " + "\n ".join(textwrap.wrap(line, 90)))

    # Return them into a unified string
    return ("\n".join(newLines))

#--------------------------------------------------------------------
# Wrap long lines in the report - Obsolete?
#--------------------------------------------------------------------
def wrap_old(report):
    report = report.replace("\r", "")
    oldLines = report.split("\n")
    newLines = []
    for line in oldLines:
        if len(line) <= 80:
            newLines.append(line)
        else:
            while len(line) > 80:
                newLines.append(line[:80])
                line = line[80:]
            if line:
                newLines.append(line)
    return "\n".join(newLines)


#--------------------------------------------------------------------
# Find the last pub version created by CTGovImport, and
# last pub version prior to that.
#
# In query:
#   MAX(v1.num) = Last pub version created by import program.
#   MAX(v2.num) = Previous pub version from before MAX(v1.num).
#--------------------------------------------------------------------
(docIdStr, docIdNum, dontCare) = cdr.exNormalize(docId)
errMsg = None
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    qry    = """
      SELECT MAX(v1.num), MAX(v2.num)
      FROM doc_version v1, doc_version v2
       WHERE v1.id = %d
         AND v1.comment LIKE 'ImportCTGovProtocols: %%'
         AND v1.publishable = 'Y'
         AND v2.id = v1.id
         AND v2.publishable = 'Y'
         AND v2.num < v1.num""" % docIdNum

    # cgi.bail(qry)
    cursor.execute(qry)
    row = cursor.fetchone()
    if not row or not row[0]:
        errMsg = "Could not find any CTGovImport publishable version"
    elif not row[1]:
        errMsg = "Could not find publishable version to compare import against"
    else:
        (verImport, verPrev) = row

except Exception, info:
    cdrcgi.bail("Error retrieving documents: %s" % str(info))
if errMsg:
    cdrcgi.bail(errMsg)

# Get info describing the previous version
try:
    cursor.execute("""
      SELECT v.dt, v.comment, u.name, u.fullname
        FROM doc_version v, usr u
       WHERE v.id = %d
         AND v.num = %d
         AND u.id = v.usr""" % (docIdNum, verPrev))

    row = cursor.fetchone()
    if not row:
        errMsg = "Could not fetch info for prev version - Can't happen!"
    else:
        (prevDate, prevComment, usrName, usrFullName) = row

except Exception, info:
    cdrcgi.bail("Error retrieving version info: %s" % str(info))
if errMsg:
    cdrcgi.bail(errMsg)


#--------------------------------------------------------------------
# Select out the significant fields for comparison
#--------------------------------------------------------------------
filt     = ['name:Extract Significant CTGovProtocol Elements']
response = cdr.filterDoc('guest', filt, docIdStr, docVer=verImport)
if type(response) in (type(""), type(u"")):
    cdrcgi.bail(response)
docImport = unicode(response[0], 'utf-8')

# DEBUG
# verPrev -= 1

response = cdr.filterDoc('guest', filt, docIdStr, docVer=verPrev)
if type(response) in (type(""), type(u"")):
    cdrcgi.bail(response)
docPrev  = unicode(response[0], 'utf-8')

#--------------------------------------------------------------------
# Save and difference docs
#--------------------------------------------------------------------
name1 = "LastImportedPubVersion"
name2 = "PreviousPubVersion"
# doc1  = wrap(docImport.encode('latin-1', 'replace'))
# doc2  = wrap(docPrev.encode('latin-1', 'replace'))
doc1  = wrap(docImport.encode('ascii', 'replace'))
doc2  = wrap(docPrev.encode('ascii', 'replace'))
cmd   = "diff -a -i -B -U 1 %s %s" % (name2, name1)
try:
    workDir = cdr.makeTempDir('diff')
    os.chdir(workDir)
except Exception, args:
    cdrcgi.bail(str(args))
f1 = open(name1, "w")
f1.write(doc1)
f1.close()
f2 = open(name2, "w")
f2.write(doc2)
f2.close()
result = cdr.runCommand(cmd)
cleanup(workDir)
report = result.output

#--------------------------------------------------------------------
# Report to user
#--------------------------------------------------------------------
if report.strip():
    title = "Differences between %s and %s" % (name1, name2)
else:
    title = "%s and %s are identical" % (name1, name2)
description = \
"""
Last CTGovImport version is %d<br /><br />
PreviousPubVersion %d created by %s (%s) on %s<br />
Comment: %s
""" % (verImport, verPrev, usrName, usrFullName, prevDate, prevComment)

cdrcgi.sendPage("""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <h3>%s</h3>
  <font color='blue'><strong>%s</strong></font>
  <pre>%s</pre>
 </body>
</html>""" % (title, title, description,
              cdrcgi.colorDiffs(cgi.escape(report))))
