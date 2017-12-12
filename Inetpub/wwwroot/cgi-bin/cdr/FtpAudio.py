# *********************************************************************
# Download Audio files from the Cancerinfo server from the ciat/qa/Audio 
# directory # and place them on the CDR server.
#
# Program based on similar program written earlier for image files.
# ---------------------------------------------------------------------
# Created:          2011-04-06        Volker Englisch
#
# BZIssue::5013 - [Glossary Audio] Create Audio Download Tool
#
# *********************************************************************
import cgi, cdr, cdrcgi, os, paramiko
import glob
from cdrapi.settings import Tier

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
LOGNAME   = "FtpAudio.log"
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields) or "guest"
request   = cdrcgi.getRequest(fields) # or "Get Audio"
testMode  = fields and fields.getvalue("TestMode") or False

USER      = "cdroperator"
SSH_KEY   = "\etc\cdroperator_rsa"

TIER      = Tier()
HOMEDIR   = "/sftp/sftphome/cdrstaging"
AUDIOPATH = "%s/ciat/%s/Audio" % (HOMEDIR, TIER.name.lower())

WIN_DIR   = "Audio_from_CIPSFTP"
NIX_DIR   = "Term_Audio"
CIAT_DIR  = "Audio_Transferred"
IN_DIR    = "%s/%s" % (AUDIOPATH, NIX_DIR)
MV_DIR    = "%s/%s" % (AUDIOPATH, CIAT_DIR)

# For testing
# testMode = False
# request  = "Get Audio"

title     = "CDR Administration"
section   = "FTP Audio from CIPSFTP"
buttons   = ["Get Audio", cdrcgi.MAINMENU, "Log Out"]
script    = "FtpAudio.py"

ftpDone   = ''

# ---------------------------------------------------------------------
# Instantiate the Log class
# ---------------------------------------------------------------------
l   = cdr.Log(LOGNAME)
l.write("FtpAudio - Started")
if testMode:
    l.write("Running in testmode")
else:
    l.write("Running in livemode")

# Open the SFTP connection and login
# ----------------------------------
FTPSERVER  = TIER.hosts['SFTP'].split(".")[0]
PORT = 22

# Establishing a ssh connection to the server
# -------------------------------------------
c = paramiko.Transport((FTPSERVER, PORT))
keyFile = paramiko.RSAKey.from_private_key_file(SSH_KEY)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

l.write("Connecting to %s ..." % FTPSERVER)
c.connect(hostname = FTPSERVER, username = USER, pkey = keyFile)
l.write("Connected")

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session or not cdr.canDo(session, "AUDIO DOWNLOAD"):
    cdrcgi.bail("You are not authorized to download audio files")

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Copy the files from the FTP Server to the local network
#----------------------------------------------------------------------
if testMode:
    l.write(request)

if request == "Get Audio" and ftpDone != 'Y':
    # Create directory path and check if directory exists.
    # If it does not exist, create it
    # This doesn't work because we don't have permissions to
    # access a network drive.
    # ----------------------------------------------------
    if not os.path.exists(os.path.join('d:\\cdr', WIN_DIR)):
       os.mkdir(os.path.join('d:\\cdr', WIN_DIR))

    try:
        l.write(AUDIOPATH)
        l.write(WIN_DIR)
        l.write(NIX_DIR)
        l.write(CIAT_DIR)

        # Checking if any zip files are available to be downloaded
        #  -------------------------------------------------------
        cmd = "ls %s" % IN_DIR
        l.write("Checking for files in FTP-dir:")
        l.write("%s" % IN_DIR)
        stdin, stdout, stderr = c.exec_command(cmd)

        # Read the files and clean up file names
        if not stderr.read():
            zipFiles = stdout.readlines()
            zipFiles = [str(x.strip()) for x in zipFiles]
        else:
            cdrcgi.bail(sterr.read())

        # Count the number of ZIP files found
        # -----------------------------------
        nZipFiles = 0
        for zipFile in zipFiles:
            if zipFile.endswith('.zip'): nZipFiles += 1
        if not nZipFiles:
            l.write("No zip files found.")
            l.write("Ftp done!")
            cdrcgi.bail('No Audio zip file(s) to download')

        l.write("Found %d zip files:" % nZipFiles)
        l.write("%s" % zipFiles)

        # Checking which zip files have already been downloaded earlier
        # -------------------------------------------------------------
        os.chdir('/cdr/%s' % WIN_DIR)
        oldFiles = glob.glob('*.[zZ][iI][pP]')
        l.write("Old files in /cdr/%s:\n%s" % (WIN_DIR, oldFiles))

        # Download and move/rename all available Zip files
        # ------------------------------------------------
        newFiles = []

        ### for name in sftp.listdir():
        for name in zipFiles:
            # First download the ZIP files...
            # -------------------------------
            if name.endswith('.zip'):
                l.write("Zip file found: %s" % name)

                # Don't overwrite files previously copied (unless in test mode)
                # -------------------------------------------------------------
                if name in oldFiles and not testMode:
                    cdrcgi.bail('Error:  Local File %s already exists!' % name)

                targetFile = '/cdr/%s/%s' % (WIN_DIR, name)
                l.write("Copy from: .../Audio/%s/%s" % (NIX_DIR, name))
                l.write("       to: %s" % targetFile)

                sftp = c.open_sftp()
                sftp.get("%s/%s"      % (IN_DIR, name),
                         "/cdr/%s/%s" % (WIN_DIR, name))
                sftp.close()
                newFiles.append(name)
            else:
                l.write("No zip file: %s" % name)

            # ... then copy the file to the 'transferred' directory
            # This way we won't copy the file again the next time
            # around.
            #
            # Copy files in testmode, move in live mode
            # ----------------------------------------------------
            if testMode:
                cmd = "cp %s/%s %s/%s" % (IN_DIR, name, MV_DIR, name)
                stdin, stdout, stderr = c.exec_command(cmd)

                if stderr.read():
                    l.write( "Error copying file in test mode!!!")
                    l.write(stderr.read())
                    cdrcgi.bail("Unable to copy file: %s" % cmd)
            else:
                cmd = "mv %s/%s %s/%s" % (IN_DIR, name, MV_DIR, name)
                stdin, stdout, stderr = c.exec_command(cmd)

                if stderr.read():
                    l.write( "Error moving file to CIAT directory!!!")
                    l.write(stderr.read())
                    cdrcgi.bail("Unable to move file: %s" % cmd)

        ftpDone = 'Y'
        c.close()
        l.write("Ftp download completed!")
    except Exception, info:
        cdrcgi.bail(u"FTP Error: %s" % info)


#----------------------------------------------------------------------
# Display confirmation message when FTP is done.
#----------------------------------------------------------------------
if ftpDone == 'Y':
   header  = cdrcgi.header(title, title, section, script, buttons)
   form = u"""\
<input type='hidden' name='%s' value='%s' >
""" % (cdrcgi.SESSION, session)
   form += u"""\
<table>
 <tr>
  <th>Files Retrieved:</th>
 </tr>
"""
   for newFile in newFiles:
       form += u"""
 <tr>
  <td>%s</td>
 </tr>
""" % newFile

   if testMode:
       testString = u'Test '
   else:
       testString = u''

   form += u"""
</table>
<H4>Download %sCompleted</H4>
""" % testString

   cdrcgi.sendPage(header + form + u"</body></html>")


#----------------------------------------------------------------------
# Display the form for merging two protocol documents.
#----------------------------------------------------------------------
header = cdrcgi.header(title, title, section, script, buttons)
form = u"""\
<fieldset>
 <legend>Download Term Audio Files from FTP server</legend>
   <b>Directory on FTP Server: </b> %s
   <br>
   <b>Directory on CDR Server: </b> %s

   <br><br>
   Click the "Get Audio" button to start the download from
   cancerinfo.nci.nih.gov
   <br><br>

   <input type='checkbox' name='TestMode'>Test Mode
   <input type='hidden' name='%s' value='%s' >
</fieldset>
""" % (NIX_DIR, WIN_DIR, cdrcgi.SESSION, session)

cdrcgi.sendPage(header + form + u"</form></body></html>")
