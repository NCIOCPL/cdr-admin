#----------------------------------------------------------------------
# $Id$
#
# Ftp files from the CIPSFTP server from the ciat/qa/Images directory
# and place them on the CIPS network.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2005/06/01 21:22:00  venglisc
# Modified program to create a copy for CIAT in the Images_for_CIAT
# directory before deleting the files from the CDR_Images directory.
# (Bug 1699)
#
# Revision 1.2  2005/01/19 23:48:33  venglisc
# Modified Error message when error ftplib.error_perm is being raised.
# (Bug 1465).
#
# Revision 1.1  2004/11/01 21:29:48  venglisc
# Initial version of script allowing to ftp image files from the CIPSFTP
# server and copy to the CDR server. (Bug 1365)
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, os, ftplib, shutil

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
defTarget = "Images_from_Cipsftp"
CiatTarget= "Images_for_CIAT"
defSource = "CDR_Images"
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields) or "guest"
request   = cdrcgi.getRequest(fields) # or "Get Images"
baseDir   = 'qa/ciat/Images/'
sourceDir = fields and fields.getvalue("SourceDir") or defSource
targetDir = fields and fields.getvalue("TargetDir") or defTarget
title     = "CDR Administration"
section   = "FTP Images from CIPSFTP"
buttons   = ["Get Images", cdrcgi.MAINMENU, "Log Out"]
script    = "FtpImages.py"
ftphost   = "cipsftp.nci.nih.gov"
ftpuser   = "cdrdev"
ftppwd    = "***REMOVED***"
ftpDone   = None

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
if request == "Get Images" and ftpDone != 'Y':
    if not sourceDir or not targetDir:
        cdrcgi.bail("Both document IDs are required.")
    ### # Create directory path and check if directory exists. 
    ### # If it does not exist, create it
    ### # This doesn't work because we don't have permissions to
    ### # access a network drive.
    ### # ----------------------------------------------------
    ### netwkDir  = "\\\\imbncipf01\\public\\CDR Images\\" + targetDir
    ### if not os.path.exists(netwkDir):
    ###    os.chdir('\\\\imbncipf01\\public\\CDR Images\\')
    ###    os.mkdir(netwkDir)
    if not os.path.exists(os.path.join('d:\\cdr', targetDir)):
       os.mkdir(os.path.join('d:\\cdr', targetDir))

    ftp = ftplib.FTP(ftphost)
    try: 
       ftp.login(ftpuser, ftppwd)
       ftp.cwd(baseDir + sourceDir)
       for name in ftp.nlst():
           if name.endswith('.jpg') or name.endswith('.gif') \
                                    or name.endswith('.psd'):
               bytes = []
               ftp.retrbinary('RETR ' + name, lambda a: bytes.append(a))
               targetFile = os.path.join('d:\\cdr', targetDir, name)
               f = open(targetFile, 'wb')
               # f = open(os.path.join(netwkDir, name), 'wb')
               f.write("".join(bytes))
               f.close()

           # Copy the file to the CIAT review directory if it was 
           # transferred from the default directory
           # We do this so that Margaret isn't dependend on CIAT
           # to download the data before she has access to the 
           # Images.
           # ----------------------------------------------------
           if sourceDir == 'CDR_Images':
               ciatFile = '../' + CiatTarget + '/' + name
               ftp.storbinary('STOR ' + ciatFile, open(targetFile, 'rb')) 

           # Delete the file if it was transferred from default directory
           # ------------------------------------------------------------
           if sourceDir == 'CDR_Images':
               ftp.delete(name)
               #print "%d chunks for %s" % (len(bytes), name)
       ftp.quit()
       ftpDone = 'Y'
    except ftplib.error_reply, info:
       cdrcgi.bail("Unexpected Error: %s" % info)
    except ftplib.error_perm, info:
       cdrcgi.bail("File or User Permission Error: %s" % info)
    except ftplib.error_proto, info:
       cdrcgi.bail("Server Error: %s" % info)
    #except:
    #   cdrcgi.bail("Notify Programming staff")
    

#----------------------------------------------------------------------
# Display confirmation message when FTP is done.
#----------------------------------------------------------------------
if ftpDone == 'Y':
   header  = cdrcgi.header(title, title, section, script, buttons)
   form = """\
<H3>FTP Completed</H3>
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
""" % (cdrcgi.SESSION, session)
   cdrcgi.sendPage(header + form + "</BODY></HTML>")


#----------------------------------------------------------------------
# Display the form for merging two protocol documents.
#----------------------------------------------------------------------
header  = cdrcgi.header(title, title, section, script, buttons)
form = """\
<H2>FTP Image (jpg, gif) or Photoshop Files from CIPSFTP</H2>
<TABLE border='0'>
 <TR>
  <TD NOWRAP>
   <B>Directory on FTP Server</B>
   </BR>Default: /qa/ciat/Images/CDR_Images
  </TD>
  <TD>&nbsp;&nbsp;</TD>
  <TD NOWRAP>
   <B>Directory on CDR Server</B>
   </BR>Default: /cdr/Images_from_CIPSFTP
  </TD>
 </TR>
 <TR>
  <TD><INPUT NAME='SourceDir' size='40' value='CDR_Images'></TD>
  <TD>&nbsp;&nbsp;</TD>
  <TD><INPUT NAME='TargetDir' size='40' value='Images_from_CIPSFTP'></TD>
 </TR>
</TABLE>
<INPUT TYPE='hidden' NAME='%s' VALUE='%s' >
""" % (cdrcgi.SESSION, session)
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
