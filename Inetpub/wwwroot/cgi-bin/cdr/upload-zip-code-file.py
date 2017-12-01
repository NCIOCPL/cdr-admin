#----------------------------------------------------------------------
# Script to copy the ZIP code zip-archive file to the CDR server and
# load to the zip_code database table.
# ---------------------------------------------------------------------
# OCECDR-3848: Automate Quarterly ZIP Code Updates
#----------------------------------------------------------------------
import sys
import cdr
import cgi
import cdrcgi
import datetime
import zipfile

try: # Windows needs stdio set for binary mode.
    import msvcrt
    import os
    msvcrt.setmode (0, os.O_BINARY) # stdin  = 0
    msvcrt.setmode (1, os.O_BINARY) # stdout = 1
except ImportError:
    pass

fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
if not session or not cdr.canDo(session, "UPLOAD ZIP CODES"):
    cdrcgi.bail("You are not authorized to post ZIP code files")
request = fields.getvalue("Request")

# Display the upload page
# -----------------------
if "codes" in fields.keys():
    codes = fields["codes"]
else:
    cdrcgi.sendPage(u"""\
<!DOCTYPE html>
<html>
  <head>
    <title>ZIP Codes</title>
    <style>
* { font-family: Arial, sans-serif; }
fieldset { width: 350px; margin: 5px auto; }
legend { color: green; }
h1 { font-size: 20px; text-align: center; color: maroon; }
input { display: block; }
#submit { margin-top: 10px; }
    </style>
  </head>
  <body>
    <h1>Upload ZIP Codes</h1>
    <form action="upload-zip-code-file.py" method="post"
          enctype="multipart/form-data">
      <input type="hidden" name="Session" value="%s">
      <fieldset>
        <legend>File Selection</legend>
        <input type="file" name="codes">
        <input type="submit" value="Submit" name="Request" id="submit">
        <hr>
        <p><strong>Note</strong>:<br>The load will take several minutes. 
           Don't press <em>Submit</em> twice.</p>
      </fieldset>
    </form>
  </body>
</html>""" % session)

# Read the zip file
# -----------------
if codes.file:
    bytes = []
    while True:
        more_bytes = codes.file.read()
        if not more_bytes:
            break
        bytes.append(more_bytes)
else:
    bytes = [codes.value]

# We don't like empty files
# -------------------------
if not bytes:
    cdrcgi.bail("Empty file")

# Save a copy of the uploaded files in the uploads directory
# ----------------------------------------------------------
now  = datetime.datetime.now()
name = now.strftime(cdr.BASEDIR + "/uploads/zipcodes-%Y%m%d%H%M%S.zip")
ziptxt  = now.strftime('/tmp/zip-%Y%m%d%H%M%S.txt')
# ziptxt  = now.strftime('/tmp/zip.txt')
zipload = '%s/utilities/bin/LoadZipCodes.py' % cdr.BASEDIR
cmd = '%s %s %s' % (cdr.PYTHON, zipload, ziptxt)

# Saving the ZIP file to disk
# ---------------------------
try:
    fp = open(name, "wb")
    for segment in bytes:
        fp.write(segment)
    fp.close()
except Exception, e:
    cdrcgi.bail("failure storing %s: %s" % (name, e))

# Access the saved ZIP file and read the ZIP Code archive
# -------------------------------------------------------
try:
    zf = zipfile.ZipFile(name)
    names = zf.namelist()
    if "z5max.txt" in names:
        payload = zf.read("z5max.txt")
        fzip = open("%s" % ziptxt, "w")
        fzip.write(payload)
        fzip.close()

        # Now that we have the data file on the server we're ready
        # to run the load script
        # --------------------------------------------------------
        try:
            result = cdr.runCommand(cmd)
            # print "Content-type: text/plain\n\n%s" % result.output
        except Exception, e:
            print "Content-type: text/plain\n\n%s\n%s" % (cmd, repr(e))
        # sys.exit(0)
        
    else:
        payload = u"\n".join(names)
except Exception, e:
    cdrcgi.bail("failure opening %s: %s" % (name, e))

#-----------------------------------------------
# Final report listing the number of rows loaded
#-----------------------------------------------
cdrcgi.sendPage(u"""\
<!DOCTYPE html>
<html>
  <head>
   <title>Update zipcode DB table</title>
  </head>
  <body>
    <h3>Success:  zipcode table updated!</h3>
    <p>
    Log messages below:
    </p>
    <pre>%s</pre>
  </body>
</html>""" % result.output)
