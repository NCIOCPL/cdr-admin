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
import re
from datetime import datetime as dt
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
AUDIOPATH = "{}/ciat/{}/Audio".format(HOMEDIR, TIER.name.lower())

WIN_DIR   = "Audio_from_CIPSFTP"
NIX_DIR   = "Term_Audio"
CIAT_DIR  = "Audio_Transferred"
IN_DIR    = "{}/{}".format(AUDIOPATH, NIX_DIR)
MV_DIR    = "{}/{}".format(AUDIOPATH, CIAT_DIR)

# For testing
# testMode = False
# request  = "Get Audio"

title     = "CDR Administration"
section   = "FTP Audio from CIPSFTP"
stdButtons   = [cdrcgi.MAINMENU, "Log Out"]
getButtons   = ["Get Audio"] + stdButtons
script    = "FtpAudio.py"
now       = dt.now().strftime("%Y-%m-%d_%H:%M:%S")

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

l.write("Connecting to {} ...".format(FTPSERVER))
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
        l.write('Directory locations')
        l.write('   {}'.format(AUDIOPATH))
        l.write('   {}'.format(WIN_DIR))
        l.write('   {}'.format(NIX_DIR))
        l.write('   {}'.format(CIAT_DIR))

        # Listing all available files in the directory
        # --------------------------------------------
        cmd = "ls {}/*".format(IN_DIR)
        l.write("Checking for files in FTP-dir:")
        l.write("{}".format(IN_DIR))
        stdin, stdout, stderr = c.exec_command(cmd)
        files = stdout.readlines()

        zipFiles = []
        badNames = []

        # We need to follow a specific naming convention with the
        # file names.  If the file name doesn't follow the file
        # name format we're capturing the name in the badNames list.
        # File names with the following format are getting copied:
        #  - Week_NNN.zip or
        #  - Week_NNN_RevN.zip
        # File names include the full path and need to be stripped.
        # --------------------------------------------------------
        for audioFile in files:
            zipFile = audioFile.replace('{}/'.format(IN_DIR), '')
            # l.write(zipFile)
            if re.match('Week_\d\d\d(_Rev\d)?.zip', zipFile):
                zipFiles.append(zipFile.strip())
            else:
                badNames.append(zipFile.strip())

        # Exit if no file is available for download
        # -----------------------------------------
        if not zipFiles:
            cdrcgi.bail("No files available for download!")

        l.write('')
        l.write('Zip file(s) found:')
        for zipFile in zipFiles:
            l.write(zipFile)

        l.write('')
        l.write('Bad file names(s) found:')
        l.write(repr(badNames))

        # Count the number of ZIP files found
        # -----------------------------------
        if not zipFiles:
            l.write("No zip files found.")
            l.write("Ftp done!")
            cdrcgi.bail('No Audio zip file(s) to download')

        l.write('')
        l.write("Found %d zip files:" % len(zipFiles))
        l.write("{}".format(zipFiles))
        l.write('')

        # Checking which zip files have already been downloaded earlier
        # -------------------------------------------------------------
        os.chdir("/cdr/{}".format(WIN_DIR))
        oldFiles = glob.glob('*.[zZ][iI][pP]')
        l.write("Old files in /cdr/{}:\n{}".format(WIN_DIR, oldFiles))

        # Download and move/rename all available Zip files
        # ------------------------------------------------
        newFiles = []

        ### for name in sftp.listdir():
        for name in zipFiles:
            # First download the ZIP files...
            # -------------------------------
            if name.endswith('.zip'):
                l.write("Zip file found: {}".format(name))

                # Don't overwrite files previously copied (unless in test mode)
                # -------------------------------------------------------------
                if name in oldFiles and not testMode:
                    msg = 'Error:  Download file {} already exists on CDR server!'
                    cdrcgi.bail(msg.format(name))

                targetFile = "/cdr/{}/{}".format(WIN_DIR, name)
                l.write("Copy from: .../Audio/{}/{}".format(NIX_DIR, name))
                l.write("       to: {}".format(targetFile))

                if not testMode:
                    sftp = c.open_sftp()
                    sftp.get("{}/{}".format(IN_DIR, name),
                             "/cdr/{}/{}".format(WIN_DIR, name))
                    sftp.close()
                else:
                    l.write("*** Test mode: file not downloaded")

                newFiles.append(name)
            else:
                l.write("No zip file: {}".format(name))

            # ... then copy the file to the 'transferred' directory
            # This way we won't copy the file again the next time
            # around.
            #
            # Copy files in testmode, move in live mode
            # ----------------------------------------------------
            if testMode:
                cmd = "cp {}/{} {}/{}".format(IN_DIR, name, MV_DIR, name)
                stdin, stdout, stderr = c.exec_command(cmd)

                if stderr.readlines():
                    l.write( "Error copying file in test mode!!!")
                    l.write(stderr.readlines())
                    cdrcgi.bail("Unable to copy file: {}".format(cmd))

                # In test mode move the copied files or a 'live' run will fail
                # ------------------------------------------------------------
                newName = "{}.{}".format(name, now)
                cmd = "mv {}/{} {}/{}".format(MV_DIR, name, MV_DIR, newName)
                stdin, stdout, stderr = c.exec_command(cmd)

                if stderr.readlines():
                    l.write( "Error moving test files in test mode!!!")
                    l.write(stderr.readlines())
                    cdrcgi.bail("Unable to move file: {}".format(cmd))
            else:
                cmd = "mv {}/{} {}/{}".format(IN_DIR, name, MV_DIR, name)
                stdin, stdout, stderr = c.exec_command(cmd)

                if stderr.readlines():
                    l.write( "Error moving file to CIAT directory!!!")
                    l.write(stderr.readlines())
                    cdrcgi.bail("Unable to move file: {}".format(cmd))

        ftpDone = 'Y'
        c.close()
        l.write("Ftp download completed!")
    except Exception as info:
        cdrcgi.bail(u"FTP Error: {}".format(info))


#----------------------------------------------------------------------
# Display confirmation message when FTP is done.
#----------------------------------------------------------------------
if ftpDone == 'Y':
   header  = cdrcgi.header(title, title, section, script, stdButtons)
   form = u"""\
<input type='hidden' name='{}' value='{}' >
""".format(cdrcgi.SESSION, session)
   form += u"""\
<table style="margin-bottom: 10pt;">
 <tr>
  <th style="font-size: 14pt;">Files Retrieved:</th>
 </tr>
"""
   for newFile in newFiles:
       form += u"""
 <tr>
  <td>{}</td>
 </tr>
""".format(newFile)

   if testMode:
       testString = u'Test '
   else:
       testString = u''

   form += u"""
</table>"""

   # Display files with bad file name format if those exist
   # ------------------------------------------------------
   if badNames:
       form += u"""\
<table>
 <tr>
  <th style="font-size: 14pt;">Files NOT Retrieved:</th>
 </tr>
"""
       for badName in badNames:
           form += u"""
 <tr>
  <td>{}</td>
 </tr>
""".format(badName)

   if testMode:
       testString = u'Test '
   else:
       testString = u''

   form += u"""
</table>"""

   form += u"""
<H4>Download {}Completed</H4>
""".format(testString)

   cdrcgi.sendPage(header + form + u"</body></html>")


#----------------------------------------------------------------------
# Display the form for downloading audio files
#----------------------------------------------------------------------
header = cdrcgi.header(title, title, section, script, getButtons)
form = u"""\
<fieldset>
 <legend>Download Term Audio Files from FTP server</legend>
   <b>Directory on FTP Server: </b> {}
   <br>
   <b>Directory on CDR Server: </b> {}

   <br><br>
   Click the "Get Audio" button to start the download from
   cancerinfo.nci.nih.gov
   <br><br>

   <input type='checkbox' name='TestMode'>Test Mode
   <input type='hidden' name='{}' value='{}' >
</fieldset>
""".format(NIX_DIR, WIN_DIR, cdrcgi.SESSION, session)

cdrcgi.sendPage(header + form + u"</form></body></html>")
