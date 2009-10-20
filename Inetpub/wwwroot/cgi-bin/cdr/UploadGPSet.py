#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, time, os, cdrdb

try: # Windows needs stdio set for binary mode.
    import msvcrt
    msvcrt.setmode (0, os.O_BINARY) # stdin  = 0
    msvcrt.setmode (1, os.O_BINARY) # stdout = 1
except ImportError:
    pass

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
#gpFile  = fields.has_key('gpset') and fields['gpset'] or None
title   = "CDR Administration"
section = "Upload Genetics Professional Documents"
buttons = [cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "UploadGPSet.py", buttons,
                        formExtra = " enctype='multipart/form-data'")

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Make sure the user is authorized to upload GP documents.
#----------------------------------------------------------------------
if not cdr.canDo(session, 'IMPORT GP DOC'):
    cdrcgi.bail("You are not authorized to import "
                "GENETICSPROFESSIONAL document sets")

#----------------------------------------------------------------------
# Save the uploaded set.
#----------------------------------------------------------------------
def saveSet(gpFile):
    if gpFile.file:
        bytes = gpFile.file.read()
    else:
        bytes = gpFile.value
    if not bytes:
        cdrcgi.bail("Empty file")
    name = time.strftime('d:/cdr/uploads/genprof-%Y%m%d%H%M%S.zip')
    try:
        f = open(name, 'wb')
        f.write(bytes)
        f.close()
    except Exception, e:
        cdrcgi.bail("Failure storing %s: %s" % (name, e))
    return name

try:
    gpFile = fields['gpset']
except:
    gpFile = None
if gpFile is not None:
    conn = cdrdb.connect()
    cursor = conn.cursor()
    name = saveSet(gpFile)
    try:
        # ADO/DB bug: SQL placeholder syntax (with "?") doesn't work here.
        cursor.execute("""\
            INSERT INTO gp_import_set (submitted_by, path, uploaded)
                 SELECT usr, '%s', GETDATE()
                   FROM session
                  WHERE name = '%s'""" % (name, session))
        conn.commit()
    except Exception, e:
        cdrcgi.bail("Failure recording %s: %s" % (name, e))
    extra = ("<h3>Genetics Professional file has been queued for uploading.  "
             "Thank you.</h3>")
else:
    extra = ''

body = u"""\
  <input type='hidden' name='%s' value='%s'>
  %s
  <p>Enter a file name or browse to select a file to upload:<br>
  <input type='file' name='gpset' size='60' maxsize='10000000' /></p>
 &nbsp; &nbsp; <input type='submit' value='Submit' />
</form>
</body>
</html>
""" % (cdrcgi.SESSION, session, extra)
cdrcgi.sendPage(header + body)
