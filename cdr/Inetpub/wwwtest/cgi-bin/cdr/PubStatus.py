#----------------------------------------------------------------------
#
# $Id: PubStatus.py,v 1.5 2002-08-19 22:04:23 pzhang Exp $
#
# Status of a publishing job.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2002/08/19 16:23:34  pzhang
# Added dispFilterFailures().
#
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
session  = fields and fields.getvalue("Session") or None

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
    setting = """[<A href="pubstatus.py?id=%d&type=Setting">Job settings
                 </A>]""" % jobId
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
         <TD><FONT COLOR='black'>%s %s</FONT></TD>
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
    """ % (pubSystem, subset, setting, name, 
           (no_output == 'Y' and "None") or dir,
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
    <td valign='top'><FONT COLOR='black'>%s</FONT></td>
    <td valign='top'><FONT COLOR='black'>%s</FONT></td>
    <td valign='top'><FONT COLOR='black'>%s</FONT></td>   
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

#----------------------------------------------------------------------
# Display the job parameters.
#----------------------------------------------------------------------
def dispJobSetting(jobId):

    #----------------------------------------------------------------------
    # Find some interesting information.
    #----------------------------------------------------------------------  
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT ppp.parm_name,
                   ppp.parm_value,                  
                   pp.pub_subset,
                   u.name                   
              FROM pub_proc_parm ppp                        
              JOIN pub_proc pp
                ON ppp.pub_proc = pp.id
              JOIN usr u
                ON u.id = pp.usr              
             WHERE ppp.pub_proc = ?             
          ORDER BY ppp.parm_name
    """, (jobId,))
        row = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving job information: %s" % info[1][0])

    title   = "CDR Publishing Job Settings"
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
              """ % (row[2], row[3])

    html   += "<BR><TABLE BORDER=1>"
    html   += """\
               <tr>    
                <td valign='top'><B>ParamName</B></td>   
                <td valign='top'><B>ParamValue</B></td>  
                </tr>
              """ 
    ROW     = "<tr><td>%s</td><td>%s</td></tr>\n"  
   
    html   += ROW % (row[0], row[1])
    
    row = cursor.fetchone()
    while row:
        html += ROW % (row[0], row[1])
        row   = cursor.fetchone()

    html  += "</TABLE></BODY></HTML>"       
    
    cdrcgi.sendPage(header + html)

#----------------------------------------------------------------------
# Display the job control page.
#----------------------------------------------------------------------
def dispJobControl(jobId, session):

    # Get a list of jobs to be killed or resumed.
    jobs = fields and fields.getvalue("Jobs") or []
    if jobs and type(jobs) != type([]):
        jobs = [jobs]        

    # Kill or resume?
    action = fields and fields.getvalue("Kill") or \
             fields and fields.getvalue("Resume") or None

    # Go ahead and do it!
    conn = cdrdb.connect('CdrPublishing')
    conn.setAutoCommit(1)
    cursor = conn.cursor()
    msg = ""
    if action and jobs:            
        msg += " [Jobs just "
        if action == "Kill checked jobs":
            msg += "killed:"
            status = "Failure"
        else:
            msg += "resumed:"  
            status = "In process" 
        for job in jobs: 
            msg += "%s, " % job          
            try:        
                cursor.execute("""\
                    UPDATE pub_proc                  
                       SET status = ?                    
                     WHERE id = ? 
                               """, (status, job))
            except cdrdb.Error, info:
                cdrcgi.bail("Failure killing or resuming: %s" % info[1][0])
        msg = msg[:-2] + "]"

    # Get user name.
    try:        
        cursor.execute("""\
            SELECT TOP 1 u.name                  
              FROM usr u       
              JOIN session s
                ON s.usr = u.id                          
             WHERE s.name = ? 
                       """, (session,))
        row = cursor.fetchone()
        name = row and row[0] or 'Unknown'
        cursor.close()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting user name: %s" % info[1][0])

    # Get jobs waiting for user approval.
    try:        
        cursor.execute("""\
            SELECT pp.id,                       
                   pp.pub_subset,                   
                   pp.started,
                   pp.status                                 
              FROM pub_proc pp 
              JOIN usr u
                ON u.id = pp.usr                        
              JOIN session s
                ON s.usr = u.id
             WHERE s.name = ?
               AND pp.status = 'Waiting user approval'    
          ORDER BY pp.started
                       """, (session,))
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting pending job: %s" % info[1][0])

    title   = "CDR Publishing Job Controller"
    script  = "PubStatus.py"
    instr   = "User Name %s" % name
    buttons = []
    header  = cdrcgi.header(title, title, instr, script, buttons)
        
    HEADER  = """\
               <BR><FONT COLOR="RED">Jobs waiting for user approval%s:</FONT>
               <BR><BR><TABLE BORDER=1>
                <tr>    
                <td valign='top'></td>   
                <td valign='top'><B>JobId</B></td>  
                <td valign='top'><B>JobName</B></td>                 
                <td valign='top'><B>Started</B></td>  
                <td valign='top'><B>Status</B></td>  
                </tr> 
              """ % msg
    ROW     = """<tr><td><INPUT TYPE='CHECKBOX' NAME='Jobs' VALUE='%d'></td>
                     <td><FONT COLOR='black'>%d</FONT></td>
                     <td><FONT COLOR='black'>%s</FONT></td>
                     <td><FONT COLOR='black'>%s</FONT></td>
                     <td><FONT COLOR='black'>%s</FONT></td></tr>
              """  

    if not len(rows):
        html = "User %s doesn't have any job waiting for approval." % name
    else:
        html = """<CENTER>
            <INPUT TYPE='SUBMIT' NAME='Kill' VALUE='Kill checked jobs'>
            <INPUT TYPE='SUBMIT' NAME='Resume' VALUE='Resume checked jobs'>
            </CENTER>"""
        html += """
            <INPUT TYPE='HIDDEN' NAME='id' VALUE='%d'>
            <INPUT TYPE='HIDDEN' NAME='Session' VALUE='%s'>
            <INPUT TYPE='HIDDEN' NAME='type' VALUE='Manage'>
                """ % (jobId, session)
     
        html += HEADER
        for row in rows:
            html += ROW % (row[0], row[0], row[1], row[2], row[3])
        html  += "</TABLE>"
        
  
    html  += "</BODY></HTML>"       
    
    cdrcgi.sendPage(header + html)

#----------------------------------------------------------------------
# Display the pub_proc_cg_work table info.
#----------------------------------------------------------------------
def dispCgWork(jobId):
    
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()

    #----------------------------------------------------------------------
    # Find vendor and push jobs.
    #----------------------------------------------------------------------  
    try:      
        cursor.execute("""\
            SELECT ppv.pub_subset, ppp.pub_subset               
              FROM pub_proc_cg_work ppcw 
              JOIN pub_proc ppv
                ON ppv.id = ppcw.vendor_job
              JOIN pub_proc ppp
                ON ppp.id = ppcw.cg_job             
                       """)
        (vendor, push) = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting vendor and push job info from PPCW.")

    #----------------------------------------------------------------------
    # Find removed document information.
    #----------------------------------------------------------------------  
    try:      
        cursor.execute("""\
            SELECT ppcw.id, ppcw.doc_type, d.title               
              FROM pub_proc_cg_work ppcw 
              JOIN document d
                ON d.id = ppcw.id
             WHERE ppcw.xml IS NULL             
          ORDER BY ppcw.doc_type, d.title
                       """)
        rowsRemoved = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting removed info from PPCW.")

    #----------------------------------------------------------------------
    # Find updated document information.
    #----------------------------------------------------------------------  
    try:      
        cursor.execute("""\
            SELECT ppcw.id, ppcw.doc_type, d.title               
              FROM pub_proc_cg_work ppcw 
              JOIN document d
                ON d.id = ppcw.id
              JOIN pub_proc_cg ppc
                ON ppcw.id = ppc.id
             WHERE NOT ppcw.xml IS NULL             
          ORDER BY ppcw.doc_type, d.title
                       """)
        rowsUpdated = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting updated info from PPCW.")

    #----------------------------------------------------------------------
    # Find added document information.
    #----------------------------------------------------------------------  
    try:      
        cursor.execute("""\
            SELECT ppcw.id, ppcw.doc_type, d.title               
              FROM pub_proc_cg_work ppcw 
              JOIN document d
                ON d.id = ppcw.id
             WHERE NOT ppcw.xml IS NULL   
               AND NOT EXISTS (
                       SELECT * 
                         FROM pub_proc_cg ppc
                        WHERE ppc.id = ppcw.id
                              )         
          ORDER BY ppcw.doc_type, d.title
                       """)
        rowsAdded = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure getting added info from PPCW.")

    # Create links when appropriate.
    nRemoved = len(rowsRemoved)
    nUpdated = len(rowsUpdated)
    nAdded   = len(rowsAdded)
    LINK     = "<A href='#%s'>%d</A>"
    lRemoved = nRemoved and LINK % ('Removed', nRemoved) or '%d' % nRemoved
    lUpdated = nUpdated and LINK % ('Updated', nUpdated) or '%d' % nUpdated
    lAdded   = nAdded and LINK % ('Added', nAdded) or '%d' % nAdded

    title   = "CDR Document Pushing Information"
    instr   = "Job Number %d" % jobId
    buttons = []
    header  = cdrcgi.header(title, title, instr, None, buttons)
    html    = """\
        <TABLE>   
           <TR>
             <TD ALIGN='right' NOWRAP><B>Vendor Job Name: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Pushing Job Name: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>      
            <TR>
             <TD ALIGN='right' NOWRAP><B>Removed Documents: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>
            <TR>
             <TD ALIGN='right' NOWRAP><B>Updated Documents: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR> 
            <TR>
             <TD ALIGN='right' NOWRAP><B>Added Documents: &nbsp;</B></TD>
             <TD>%s</TD>
            </TR>        
           </TABLE>    
              """ % (vendor, push, lRemoved, lUpdated, lAdded)

    HEADER  = """\
               <BR><FONT COLOR="RED">Documents %s:</FONT><BR><BR>
               <TABLE BORDER=1 NAME='%s'>
                <tr>    
                <td valign='top'><B>DocId</B></td>   
                <td valign='top'><B>DocType</B></td>  
                <td valign='top'><B>DocTitle</B></td>  
                </tr>
              """ 
    ROW     = """<tr><td><FONT COLOR='black'>%s</FONT></td>
                     <td><FONT COLOR='black'>%s</FONT></td>
                     <td><FONT COLOR='black'>%s</FONT></td></tr>"""  

    if nRemoved:       
        html   += HEADER % ('Removed', 'Removed')  
   
        for row in rowsRemoved:
            html += ROW % (row[0], row[1], row[2])
      
        html  += "</TABLE>"  

    if nUpdated:
        html   += HEADER % ('Updated', 'Updated')  
   
        for row in rowsUpdated:
            html += ROW % (row[0], row[1], row[2])
      
        html  += "</TABLE>" 

    if nAdded:
        html   += HEADER % ('Added', 'Added')   
   
        for row in rowsAdded:
            html += ROW % (row[0], row[1], row[2])
      
        html  += "</TABLE>"   
    
    html  += "</BODY></HTML>"  
    
    cdrcgi.sendPage(header + html)

if not jobId:
    cdrcgi.bail("Job ID not supplied")

jobId = int(jobId)
if not dispType:
    dispJobStatus(jobId)
elif dispType == "FilterFailure":
    dispFilterFailures(jobId)
elif dispType == "Setting":
    dispJobSetting(jobId)
elif dispType == "CgWork":
    dispCgWork(jobId)
elif dispType == "Manage":
    if not session:
        cdrcgi.bail("A session ID must be provided for this page.")    
    dispJobControl(jobId, session)
else:
    cdrcgi.bail("Display type: %s not supported." % dispType)
    
