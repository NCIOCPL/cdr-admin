#----------------------------------------------------------------------
#
# $Id: PubStatus.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Status of a publishing job.
#
# $Log: not supported by cvs2svn $
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
               p.messages
          FROM document d
          JOIN pub_proc p
            ON p.pub_system = d.id
          JOIN usr u
            ON u.id = p.usr
         WHERE p.id = ?
""", (jobId,))
    row = cursor.fetchone()
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
""" % (jobId, row[0], row[1], row[2], row[3], row[4], row[5] and row[5] or
    "No", row[6], row[7])
cdrcgi.sendPage(header + html)
