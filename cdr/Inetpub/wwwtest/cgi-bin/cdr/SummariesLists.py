#----------------------------------------------------------------------
#
# $Id: SummariesLists.py,v 1.1 2003-12-19 18:30:00 bkline Exp $
#
# Report on lists of summaries.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdrcgi, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
audience  = fields and fields.getvalue("audience")  or None
lang      = fields and fields.getvalue("lang")      or None
showId    = fields and fields.getvalue("showId")    or "N"
groups    = fields and fields.getvalue("grp")       or []
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
instr     = "Summaries Lists"
script    = "DumpParams.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)

#----------------------------------------------------------------------
# If the user only picked one summary group, put it into a list so we
# can deal with the same data structure whether one or more were
# selected.
#----------------------------------------------------------------------
if type(groups) in (type(""), type(u"")):
    groups = [groups]

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y")

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not lang:
    header = cdrcgi.header(title, title, instr, 'DumpParams.py',
                           ("Submit",
                            SUBMENU,
                            cdrcgi.MAINMENU),
                           numBreaks = 1)
    form   = """\
   <input type='hidden' name='%s' value='%s'>
   <table border='0'>
    <tr>
     <td colspan='3'>
      %s<br><br><br>
      Link from <u>Summaries Lists</u> on menu above:<br>&nbsp;
     </td>
    </tr>
    <tr>
     <td width='150'>
      <input name='lang' type='radio' value='English'><b>English</b>
     </td>
     <td width='150'>
      <input name='audience' type='radio' value='HP'><b>Health Professional</b>
     </td>
     <td width='150'>
      <input name='showId' type='radio' value='Y'><b>With CDR ID</b>
     </td>
    </tr>
    <tr>
     <td width='200'>
      <input name='lang' type='radio' value='Spanish'><b>Spanish</b>
     </td>
     <td width='200'>
      <input name='audience' type='radio' value='Patient'><b>Patient</b>
     </td>
     <td width='200'>
      <input name='showId' type='radio' value='N'><b>Without CDR ID</b>
     </td>
    </tr>
   </table>
   <br>
   <table border = '0'>
    <tr>
     <td colspan='2'>If <u>English</u> is selected above:<br>&nbsp;</td>
    </tr>
    <tr>
     <td width='300' valign='top'>
      <b>Select PDQ Summaries:<br>(one or more)</b>
     </td>
     <td>
      <input type='checkbox' name='grp' value='Adult Treatment'>
       <b>Adult Treatment</b><br>
      <input type='checkbox' name='grp' value='Pediatric Treatment'>
       <b>Pediatric Treatment</b><br>
      <input type='checkbox' name='grp' value='Screening and Prevention'>
       <b>Screening and Prevention</b><br>
      <input type='checkbox' name='grp' value='Supportive Care'>
       <b>Supportive Care</b><br>
      <input type='checkbox' name='grp' value='Cancer Genetics'>
       <b>Cancer Genetics</b><br>
      <input type='checkbox' name='grp'
             value='Complementary and Alternative Medicine'>
       <b>Complementary and Alternative Medicine</b><br>
      <input type='checkbox' name='grp' value='All English'>
       <b>All English</b><br>&nbsp;
     </td>
    </tr>
    <tr>
     <td colspan='2'>If <u>Spanish</u> is selected above:<br>&nbsp;</td>
    </tr>
    <tr>
     <td width='300' valign='top'>
      <b>Select PDQ Summaries:<br>(one or more)</b>
     </td>
     <td>
      <input type='checkbox' name='grp' value='Spanish Adult Treatment'>
       <b>Spanish Adult Treatment</b><br>
      <input type='checkbox' name='grp' value='Spanish Pediatric Treatment'>
       <b>Spanish Pediatric Treatment</b><br>
      <input type='checkbox' name='grp' value='Spanish Supportive Care'>
       <b>Spanish Supportive Care</b><br>
      <input type='checkbox' name='grp' value='All Spanish'>
       <b>All Spanish</b><br>
     </td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, dateString)
    cdrcgi.sendPage(header + form)
