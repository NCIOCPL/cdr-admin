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
import time
import os

FIX_PERMISSIONS = os.path.join(cdr.BASEDIR, "Bin", "fix-permissions.cmd")
FIX_PERMISSIONS = FIX_PERMISSIONS.replace("/", os.path.sep)

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
    cdrcgi.sendPage("""\
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
    filebytes = []
    while True:
        more_bytes = codes.file.read()
        if not more_bytes:
            break
        filebytes.append(more_bytes)
else:
    filebytes = [codes.value]

# We don't like empty files
# -------------------------
if not filebytes:
    cdrcgi.bail("Empty file")

# Save a copy of the uploaded files in the uploads directory
# ----------------------------------------------------------
now  = datetime.datetime.now()
name = now.strftime(f"{cdr.BASEDIR}/uploads/zipcodes-%Y%m%d%H%M%S.zip")
ziptxt  = now.strftime("/tmp/zip-%Y%m%d%H%M%S.txt")
zipload = f"{cdr.BASEDIR}/utilities/bin/LoadZipCodes.py"
cmd = f"{cdr.PYTHON} {zipload} {ziptxt}"

# Saving the ZIP file to disk
# ---------------------------
try:
    with open(name, "wb") as fp:
        for segment in filebytes:
            fp.write(segment)
except Exception as e:
    cdrcgi.bail(f"failure storing {name}: {e}")

# Access the saved ZIP file and read the ZIP Code archive
# -------------------------------------------------------
time.sleep(2)
native_name = name.replace("/", os.path.sep)
command = f"{FIX_PERMISSIONS} {native_name}"
process = cdr.run_command(command, merge_output=True)
if process.returncode:
    print(f"""\
Content-type: text/plain

Unable to set permissions on {name}.
Command: {command}
Output: {process.stdout}""")
    sys.exit(0)

try:
    zf = zipfile.ZipFile(name)
    names = zf.namelist()
except Exception as e:
    cdrcgi.bail(f"failure loading {name}: {e}")
if "z5max.txt" not in names:
    names = "\n".join(names)
    print(f"""\
Content-type: text/plain

The file z5max.txt is not contained in the zipfile.
Archive contents:
{names}
""")
    sys.exit(0)

try:
    payload = zf.read("z5max.txt")
    with open(ziptxt, "wb") as fzip:
        fzip.write(payload)
except Exception as e:
    cdrcgi.bail(f"unable to write csv file: {e}")

# Now that we have the data file on the server we're ready
# to run the load script
# --------------------------------------------------------
try:
    process = cdr.run_command(cmd, merge_output=True)
except Exception as e:
    print(f"Content-type: text/plain\n\n{cmd}\n{e!r}")
    sys.exit(0)


#-----------------------------------------------
# Final report listing the number of rows loaded
#-----------------------------------------------
cdrcgi.sendPage(f"""\
<!DOCTYPE html>
<html>
  <head>
   <title>Update zipcode DB table</title>
  </head>
  <body>
    <h3>Success: zipcode table updated!</h3>
    <p>
    Log messages below:
    </p>
    <pre>{process.stdout}</pre>
  </body>
</html>""")
