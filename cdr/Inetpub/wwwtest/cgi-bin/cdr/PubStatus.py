#----------------------------------------------------------------------
#
# $Id: PubStatus.py,v 1.2 2002-02-14 21:46:52 mruben Exp $
#
# Status of a publishing job.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
jobId   = fields and fields.getvalue("id") or None

if not jobId:
    cdrcgi.bail("Job ID not supplied")

#----------------------------------------------------------------------
# Find some interesting information.
#----------------------------------------------------------------------
jobId   = int(jobId)
try:
    conn = cdrdb.connect('CdrPublishing')
    cursor = conn.cursor()
    cursor.execute("""\
        SELECT d.title,
               p.pub_subset,
               u.name,
               p.output_dir,
               p.started,
               p.completed,
               p.status,
               p.messages,
               p.no_output
          FROM document d
          JOIN pub_proc p
            ON p.pub_system = d.id
          JOIN usr u
            ON u.id = p.usr
         WHERE p.id = ?
""", (jobId,))
    (title, subset, name, dir, started, completed, status,
     messages, no_output) = cursor.fetchone()
except cdrdb.Error, info:
    cdrcgi.bail("Failure retrieving job information: %s" % info[1][0])

title   = "CDR Publishing Job Status"
instr   = "Job Number %d" % jobId
buttons = []
header  = cdrcgi.header(title, title, instr, None, buttons)
html    = """\
   <TABLE>
    <TR>
     <TD ALIGN='right' NOWRAP><B>Job Number: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%d</FONT></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP><B>Publishing System: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%s</FONT></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP><B>System Subset: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%s</FONT></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP><B>User Name: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%s</FONT></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP><B>Output Location: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%s</FONT></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP><B>Started: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%s</FONT></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP><B>Completed: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%s</FONT></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP><B>Status: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%s</FONT></TD>
    </TR>
    <TR>
     <TD ALIGN='right' NOWRAP><B>Messages: &nbsp;</B></TD>
     <TD><FONT COLOR='black'>%s</FONT></TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (jobId, title, subset, name, (no_output == 'Y' and "None") or dir,
       started, completed and completed or "No", status, messages)
cdrcgi.sendPage(header + html)
