#----------------------------------------------------------------------
#
# $Id: PubStatus.py,v 1.4 2002-08-19 16:23:34 pzhang Exp $
#
# Status of a publishing job.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/04/25 21:12:22  bkline
# Fixed bug which was overwriting name of publishing system.
#
# Revision 1.2  2002/02/14 21:46:52  mruben
# Added support for no_output flag [bkline for mruben].
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
jobId    = fields and fields.getvalue("id") or None
dispType = fields and fields.getvalue("type") or None

#----------------------------------------------------------------------
# Display the publishing overall job status.
#----------------------------------------------------------------------
def dispJobStatus(jobId):

    #----------------------------------------------------------------------
    # Find some interesting information.
    #----------------------------------------------------------------------   
    try:
        conn = cdrdb.connect('CdrGuest')
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
        (pubSystem, subset, name, dir, started, completed, status,
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
    """ % (pubSystem, subset, name, (no_output == 'Y' and "None") or dir,
           started, completed and completed or "No", status, messages)
    cdrcgi.sendPage(header + html)

#----------------------------------------------------------------------
# Add a table row for an published documents.
#----------------------------------------------------------------------
def addRow(row):  
    return """\
   <tr>
    <td valign='top'><FONT COLOR='black'>%d</FONT></td>   
    <td valign='top'><FONT COLOR='black'>%d</FONT></td>   
    <td valign='top' align='left'><FONT COLOR='black'>%s</FONT></td>
    <td valign='top' align='left'><FONT COLOR='black'>%s</FONT></td>
    <td valign='top' align='left'><FONT COLOR='black'>%s</FONT></td>   
   </tr>
""" % (row[0], row[1], row[2], row[3], row[4])

#----------------------------------------------------------------------
# Display the filter failures: docId, docVer, docType, docTitle, Message.
#----------------------------------------------------------------------
def dispFilterFailures(jobId):

    #----------------------------------------------------------------------
    # Find some interesting information.
    #----------------------------------------------------------------------  
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT ppd.doc_id,
                   ppd.doc_version,
                   t.name,
                   d.title,
                   ppd.messages,
                   pp.pub_subset,
                   u.name                   
              FROM pub_proc_doc ppd
              JOIN document d
                ON ppd.doc_id = d.id             
              JOIN pub_proc pp
                ON ppd.pub_proc = pp.id
              JOIN usr u
                ON u.id = pp.usr
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE ppd.pub_proc = ?
               AND ppd.failure = 'Y'
          ORDER BY t.name, d.title
    """, (jobId,))
        row = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving job information: %s" % info[1][0])

    title   = "CDR Publishing Filter Failures"
    instr   = "Job Number %d" % jobId
    buttons = []
    header  = cdrcgi.header(title, title, instr, None, buttons)
    html    = """\
       <TABLE>        
        <TR>
         <TD ALIGN='right' NOWRAP><B>System Subset: &nbsp;</B></TD>
         <TD><FONT COLOR='black'>%s</FONT></TD>
        </TR>
        <TR>
         <TD ALIGN='right' NOWRAP><B>User Name: &nbsp;</B></TD>
         <TD><FONT COLOR='black'>%s</FONT></TD>
        </TR>      
       </TABLE>    
    """ % (row[5], row[6])

    html   += "<BR><TABLE BORDER=1>"
    html   += """\
   <tr>    
    <td valign='top'><B>Id</B></td>   
    <td valign='top'><B>Ver</B></td>   
    <td valign='top' align='right'><B>Type</B></td>
    <td valign='top' align='right'><B>Title</B></td>
    <td valign='top' align='right'><B>Message</B></td> 
    </tr>
""" 
    html   += addRow(row)
    
    row = cursor.fetchone()
    while row:
        html += addRow(row)
        row   = cursor.fetchone()

    html  += "</TABLE></BODY></HTML>"       
    
    cdrcgi.sendPage(header + html.encode('latin-1'))

if not jobId:
    cdrcgi.bail("Job ID not supplied")

jobId = int(jobId)
if not dispType:
    dispJobStatus(jobId)
elif dispType == "FilterFailure":
    dispFilterFailures(jobId)
else:
    cdrcgi.bail("Display type: %s not supported." % dispType)
    
