#----------------------------------------------------------------------
#
# $Id: GeneticsProfUploadFiles.py,v 1.1 2009-03-09 16:49:31 venglisc Exp $
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, time, os, cdrdb, glob, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
zipFile = fields and fields.getvalue('ZipFile') or None
title   = "CDR Administration"
section = "Genetics Professional File Upload List"
buttons = [cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.rptHeader(title, section,
            stylesheet = """\
 <style type='text/css'>
    table     { border-style: solid; 
                border-width: thin; 
                border-collapse: collapse; }
    td, th    { padding: 5px; 
                border-style: solid; 
                border-width: thin; }
    *.center  { text-align: center; }
 </style>""")

myProg  = 'GeneticsProfUploadFiles.py'
GENPROFDIR = 'D:/cdr/uploads'

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

os.chdir(GENPROFDIR)

# The user selected a file name and wants to download the ZIP file
# ----------------------------------------------------------------
if zipFile:
    print "Content-type: application/zip"
    print "Content-Disposition: attachment; filename=%s" % zipFile

    print

    try:
        import msvcrt
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        myZip = open(zipFile, 'rb')
        bytes = myZip.read()
        myZip.close()

        sys.stdout.write(bytes)
    except Exception, e:
        print "Content-type: text/plain\n"
        print "FAILURE: error writing\n%s" % str(e)


    sys.exit(0)

# Select all of the uploaded files and sort them in reverse order
# ---------------------------------------------------------------
gpFiles = glob.glob('genprof-2*.zip')
gpFiles.sort()
gpFiles.reverse()


# Build the HTML page to display the list of ZIP files previously
# uploaded to the server.
# ---------------------------------------------------------------
body = u"""\
  <h2>Genetics Professional Files Uploaded</h2>
  <table>
   <tr>
    <th>File Name</th>
    <th>Date</th>
    <th>Time</th>
    <th>File Size</th>
   </tr>"""

# Create the table rows and links for the files to access
# -------------------------------------------------------
count = 0
for file in gpFiles:
    count += 1
    bytes = os.path.getsize(file)
    if count % 2 == 0:
        body += """
   <tr class="even">"""
    else:
        body += """
   <tr class="odd">"""

    body += u"""
    <td><a href="%s?%s=guest&ZipFile=%s">%s</a></td>
    <td>%s-%s-%s</td>
    <td>%s:%sh</td>
    <td class="center">%s KB</td>
   </tr>""" % (myProg, cdrcgi.SESSION, file, file, 
               file[8:12], file[12:14], file[14:16],
               file[16:18], file[18:20],
               str(bytes)[:3])

body += u"""
  </table>
 </body>
</html>
"""
cdrcgi.sendPage(header + body)
