# *********************************************************************
#
# File Name: $RCSFile:$
#            ======================
# 
# Ftp Audio files from the CIPSFTP server from the ciat/qa/Audio directory
# and place them on the OCE network.
#
# Program based on similar program written earlier for image files.
#
# ---------------------------------------------------------------------
# $Author: venglisc $
# Created:          2011-04-06        Volker Englisch
# Last Modified:    $
# 
# $Source: /usr/local/cvsroot/cdr/Publishing/CheckCTGovTransfer.py,v $
# $Revision: 1.9 $
#
# BZIssue::5013 - [Glossary Audio] Create Audio Download Tool
#
# *********************************************************************
import cgi, cdr, cdrcgi, re, string, os, time, optparse, shutil, paramiko
import glob#, ftplib

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
LOGNAME   = "FtpAudio.log"
defTarget = "Audio_from_CIPSFTP"
CiatTarget= "Audio_Transferred"
defSource = "Term_Audio"
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields) or "guest"
request   = cdrcgi.getRequest(fields) # or "Get Audio"
ftpRoot   = '/u/ftp/cdr'
baseDir   = '/qa/ciat/Audio/'
audioPath = ftpRoot + baseDir
sourceDir = fields and fields.getvalue("SourceDir") or defSource
targetDir = fields and fields.getvalue("TargetDir") or defTarget
testMode  = fields and fields.getvalue("TestMode") or False

# For testing
# sourceDir = "Term_Audio"
# targetDir = "Audio_from_CIPSFTP"
# testMode = True
# request  = "Get Audio"

title     = "CDR Administration"
section   = "FTP Audio from CIPSFTP"
buttons   = ["Get Audio", cdrcgi.MAINMENU, "Log Out"]
script    = "FtpAudio.py"

ftpDone   = None

# ---------------------------------------------------------------------
# Instantiate the Log class
# ---------------------------------------------------------------------
l   = cdr.Log(LOGNAME)
l.write("FtpAudio - Started")

# Running program in Test mode
# ----------------------------
if testMode:
    audioPath = audioPath.replace('ciat/', 'ciat/test/')
    targetDir = os.path.join('Testing', targetDir)

    # request = "Get Audio"

# Open the SFTP connection and login
# ----------------------------------
FTPSERVER  = cdr.h.host['SFTP'][0]  #or '***REMOVED***-m'
PORT = 22
transport = paramiko.Transport((FTPSERVER, PORT))
FTPLOCK    = 'sending'
username = "cdroperator"
password = "***REMOVED***"
transport.connect(username = username, password = password)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

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
if request == "Get Audio" and ftpDone != 'Y':
    if not sourceDir or not targetDir:
        cdrcgi.bail("Both, source and target are required.")
    # Create directory path and check if directory exists. 
    # If it does not exist, create it
    # This doesn't work because we don't have permissions to
    # access a network drive.
    # ----------------------------------------------------
    if not os.path.exists(os.path.join('d:\\cdr', targetDir)):
       os.mkdir(os.path.join('d:\\cdr', targetDir))

    # ftp = ftplib.FTP(ftphost)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try: 
       ftpDir = audioPath + sourceDir
       sftp.chdir(ftpDir)
       l.write("ftpDir: %s" % ftpDir)

       # Checking if any zip files are available to be downloaded
       #  -------------------------------------------------------
       zipFiles = sftp.listdir()
       nZipFiles = 0
       for zipFile in zipFiles:
           if zipFile.endswith('.zip'): nZipFiles += 1
       if not nZipFiles:
           l.write("No zip files found.")
           l.write("Ftp done!")
           cdrcgi.bail('No Audio zip files to download')

       l.write("Found files:\n%s" % zipFiles)

       # Checking which zip files have already been downloaded earlier
       # -------------------------------------------------------------
       os.chdir('/cdr/%s' % targetDir)
       oldFiles = glob.glob('*.[zZ][iI][pP]')
       l.write("Old files in .../%s:\n%s" % (targetDir, oldFiles))

       # Download and move/rename all available Zip files
       # ------------------------------------------------
       newFiles = []
       dbgmsg = []

       for name in sftp.listdir():
           dbgmsg.append("testing %s (%s)" % (repr(name),
                                              cgi.escape(str(type(name)))))
           if name.endswith('.zip'):
               l.write("Zip file found: %s" % name)

               # Don't overwrite files previously copied (unless in test mode)
               # -------------------------------------------------------------
               if name in oldFiles and not testMode:
                   cdrcgi.bail('Error:  Local File %s already exists!' % name)

               bytes = []
               targetFile = '/cdr/%s/%s' % (targetDir, name)
               l.write("Copy from: %s/%s" % (ftpDir, name))
               l.write("       to: %s" % targetFile)

               sftp.get('%s/%s' % (ftpDir, name), '%s' % (targetFile))
               newFiles.append(name)
           else:
               l.write("No zip file: %s" % name)

           # Copy the file to 'transferred' directory if it was 
           # transferred from the default directory
           # This way we won't copy the file again the next time
           # around.
           # ----------------------------------------------------
           dbgmsg.append("sourceDir is %s" % sourceDir)
           # l.write(sourceDir)
           # l.write(audioPath)
           # l.write(CiatTarget)
           if sourceDir == 'Term_Audio':
               # ciatFile = '../' + CiatTarget + '/' + name
               # Do nothing in testmode, move the files in live mode
               # ---------------------------------------------------
               if testMode:
                   sftp.rename(name, audioPath + name + 'x')
                   sftp.rename(audioPath + name + 'x', name)
               else:
                   dbgmsg.append("renaming %s to %s" % (name, audioPath +
                                                        "%s/%s" %
                                                        (CiatTarget, name)))
                   sftp.rename(name, audioPath + '%s/%s' %
                                               (CiatTarget, name))
                   dbgmsg.append("rename complete")
               l.write("File %s moved to Term_Audio" % name)
               l.write("-----")

       ftpDone = 'Y'
       l.write("Ftp done!")
    except Exception, info:
       cdrcgi.bail(u"FTP Error: %s (DEBUG INFO FOLLOWS)<br />%s)" %
                   (info, "<br />".join(dbgmsg)))
    
#----------------------------------------------------------------------
# Display confirmation message when FTP is done.
#----------------------------------------------------------------------
if ftpDone == 'Y':
   header  = cdrcgi.header(title, title, section, script, buttons)
   form = u"""\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
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

   cdrcgi.sendPage(header + form + u"</BODY></HTML>")


#----------------------------------------------------------------------
# Display the form for merging two protocol documents.
#----------------------------------------------------------------------
header = cdrcgi.header(title, title, section, script, buttons)
form = u"""\
<H2>FTP Term Audio Files from CANCERINFO</H2>
<TABLE border='0'>
 <TR>
  <TD NOWRAP>
   <B>Directory on FTP Server</B>
   </BR>Default: /qa/ciat/Audio/Term_Audio
  </TD>
  <TD>&nbsp;&nbsp;</TD>
  <TD NOWRAP>
   <B>Directory on CDR Server</B>
   </BR>Default: /cdr/Audio_from_CIPSFTP
  </TD>
 </TR>
 <TR>
  <TD><INPUT NAME='SourceDir' size='40' value='%s'></TD>
  <TD>&nbsp;&nbsp;</TD>
  <TD><INPUT NAME='TargetDir' size='40' value='%s'></TD>
 </TR>
 <tr>
  <td colspan='3'><input type='checkbox' name='TestMode'>Test Mode</td>
 </tr>
</TABLE>
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
""" % (defSource, defTarget, cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + u"</FORM></BODY></HTML>")
