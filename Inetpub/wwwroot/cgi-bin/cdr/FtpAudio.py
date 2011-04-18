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
import cgi, cdr, cdrcgi, re, string, os, time, optparse, ftplib, shutil
import glob

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
defTarget = "Audio_from_CIPSFTP"
CiatTarget= "Audio_Transferred"
defSource = "Term_Audio"
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields) or "guest"
request   = cdrcgi.getRequest(fields) # or "Get Audio"
ftpRoot   = '/u/ftp'
baseDir   = '/qa/ciat/Audio/'
audioPath = ftpRoot + baseDir
sourceDir = fields and fields.getvalue("SourceDir") or defSource
targetDir = fields and fields.getvalue("TargetDir") or defTarget
testMode  = fields and fields.getvalue("TestMode") or False
title     = "CDR Administration"
section   = "FTP Audio from CIPSFTP"
buttons   = ["Get Audio", cdrcgi.MAINMENU, "Log Out"]
script    = "FtpAudio.py"
ftphost   = "cipsftp.nci.nih.gov"
ftpuser   = "cdrdev"
ftppwd    = "***REMOVED***"

ftpDone   = None

# Running program in Test mode
# ----------------------------
if testMode:
    audioPath = audioPath.replace('ciat/', 'ciat/test/')
    targetDir = os.path.join('Testing', defTarget)

    # request = "Get Audio"



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

    ftp = ftplib.FTP(ftphost)
    try: 
       ftp.login(ftpuser, ftppwd)
       
       ftp.cwd(audioPath + sourceDir)
       ftp.set_debuglevel(0)

       # Checking if any zip files are available to be downloaded
       #  -------------------------------------------------------
       zipFiles = ftp.nlst()
       nZipFiles = 0
       for zipFile in zipFiles:
           if zipFile.endswith('.zip'): nZipFiles += 1
       if not nZipFiles:
           cdrcgi.bail('No Audio zip files to download')

       # Checking which zip files have already been downloaded earlier
       # -------------------------------------------------------------
       os.chdir('d:\\cdr\%s' % targetDir)
       oldFiles = glob.glob('*.[zZ][iI][pP]')

       # Download and move/rename all available Zip files
       # ------------------------------------------------
       newFiles = []
       for name in ftp.nlst():
           if name.endswith('.zip'):
               # Don't overwrite files previously copied (unless in test mode)
               # -------------------------------------------------------------
               if name in oldFiles and not testMode:
                   cdrcgi.bail('Error:  Local File %s already exists!' % name)

               bytes = []
               ftp.retrbinary('RETR ' + name, lambda a: bytes.append(a))
               targetFile = os.path.join('d:\\cdr', targetDir, name)
               f = open(targetFile, 'wb')
               f.write("".join(bytes))
               f.close()
               newFiles.append(name)

           # Copy the file to 'transferred' directory if it was 
           # transferred from the default directory
           # This way we won't copy the file again the next time
           # around.
           # ----------------------------------------------------
           if sourceDir == 'Term_Audio':
               # ciatFile = '../' + CiatTarget + '/' + name
               # Do nothing in testmode, move the files in live mode
               # ---------------------------------------------------
               if testMode:
                   ftp.rename(name, audioPath + name + 'x')
                   ftp.rename(audioPath + name + 'x', name)
                   #ftp.storbinary('STOR ' + ciatFile, open(targetFile, 'rb')) 
                   #ftp.sendcmd('RNFR %s' % name)
                   #ftp.sendcmd('RNTO %s' % ciatFile)
               else:
                   ftp.rename(name, audioPath + '%s/%s' %
                                               (CiatTarget, name))
                   # ftp.storbinary('STOR ' + ciatFile, open(targetFile, 'rb')) 

           ### # Delete the file if it was transferred from default directory
           ### # ------------------------------------------------------------
           ### if sourceDir == 'Term_Audio':
           ###     if not testMode:
           ###         pp = ftp.pwd()
           ###         cdrcgi.bail('%s/%s' % (pp, name))
           ###         ftp.delete(name)
           ###     #print "%d chunks for %s" % (len(bytes), name)

       ftp.quit()
       ftpDone = 'Y'
    except ftplib.error_reply, info:
       cdrcgi.bail(u"FTP Unexpected Error: %s" % info)
    except ftplib.error_perm, info:
       cdrcgi.bail(u"FTP File or User Permission Error: %s" % info)
    except ftplib.error_proto, info:
       cdrcgi.bail(u"FTP Server Error: %s" % info)
    

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
<H3>FTP %sCompleted</H3>
""" % testString

   cdrcgi.sendPage(header + form + u"</BODY></HTML>")


#----------------------------------------------------------------------
# Display the form for merging two protocol documents.
#----------------------------------------------------------------------
header = cdrcgi.header(title, title, section, script, buttons)
form = u"""\
<H2>FTP Term Audio Files from CIPSFTP</H2>
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
