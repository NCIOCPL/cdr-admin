#----------------------------------------------------------------------
#
# $Id$
#
# Edit CDR development issue.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/04/16 14:10:26  bkline
# Added code to find earliest unresolved issue on request.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, dbi, cdrdb

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
id          = fields and fields.getvalue("id")          or None
id          = id     and int(id)                        or 0
priority    = fields and fields.getvalue("priority")    or None
logged      = fields and fields.getvalue("logged")      or None
logged_by   = fields and fields.getvalue("logged_by")   or None
assigned    = fields and fields.getvalue("assigned")    or None
assigned_to = fields and fields.getvalue("assigned_to") or None
resolved    = fields and fields.getvalue("resolved")    or None
resolved_by = fields and fields.getvalue("resolved_by") or None
description = fields and fields.getvalue("description") or None
notes       = fields and fields.getvalue("notes")       or None
request     = cdrcgi.getRequest(fields)

if logged_by   == "[Nobody]": logged_by   = None
if assigned_to == "[Nobody]": assigned_to = None
if resolved_by == "[Nobody]": resolved_by = None

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])
cursor = conn.cursor()

#----------------------------------------------------------------------
# Handle any requests from the user.
#----------------------------------------------------------------------
if request == "New":
    id = 0
if request == "Save" or request == "Please Wait...":
    if not priority:
        cdrcgi.bail("Priority field not set")
    if not logged_by:
        cdrcgi.bail("'Logged by' field not set")
    if not description:
        cdrcgi.bail("Description field not set")
    if id:
        assignedVal = 'assigned'
        resolvedVal = 'resolved'
        if not assigned_to:  assignedVal = 'NULL'
        elif not assigned:   assignedVal = 'GETDATE()'
        if not resolved_by:  resolvedVal = 'NULL'
        elif not resolved:   resolvedVal = 'GETDATE()'
        params = (priority,
                 logged_by,
                 assigned_to,
                 resolved_by,
                 description,
                 notes,
                 id)
        query = """\
UPDATE issue
   SET priority = ?,
       logged_by = ?,
       assigned = %s,
       assigned_to = ?,
       resolved = %s,
       resolved_by = ?,
       description = ?,
       notes = ?
 WHERE id = ?
""" % (assignedVal, resolvedVal)
        try:
            cursor.execute(query, params)
            conn.commit()
        except cdrdb.Error, info:
            cdrcgi.bail('Update query failure: %s' % info[1][0])

    else:
        params = (priority,
                  logged_by,
                  assigned_to,
                  resolved_by,
                  description,
                  notes)
        query = """\
INSERT INTO issue
(
    priority,
    logged,
    logged_by,
    assigned,
    assigned_to,
    resolved,
    resolved_by,
    description,
    notes
)
VALUES(?,GETDATE(),?,%s,?,%s,?,?,?)
""" % (assigned_to and "GETDATE()" or "NULL",
       resolved_by and "GETDATE()" or "NULL")
        try:
            cursor.execute(query, params)
            conn.commit()
            cursor.execute("SELECT @@IDENTITY")
            id = cursor.fetchone()[0]
        except cdrdb.Error, info:
            cdrcgi.bail('Insert query failure: %s' % info[1][0])
     

#----------------------------------------------------------------------
# Get what we need from the database.
#----------------------------------------------------------------------
if id == -1:
    # By convention, -1 means show oldest unresolved issue.
    try:
        cursor.execute("""\
            SELECT MIN(id)
              FROM issue
             WHERE resolved IS NULL
               AND priority NOT LIKE 'X%'
               AND priority NOT LIKE '1%'""")
        row = cursor.fetchone()
        id = row and row[0] or 0
    except cdrdb.Error, info:
        cdrcgi.bail('Failure looking up earliest unresolved issue: %s' % 
                    info[1][0])
try:
    if id:
        query  = """\
   SELECT id, priority, logged, logged_by,
          assigned, assigned_to, resolved, resolved_by,
          description, notes
     FROM issue
    WHERE id = ?
"""
        cursor.execute(query, [id])
        rec = cursor.fetchone()
        if not rec: id = 0
    if not id:
        rec = (0, "", None, "", None, "", None, "", "", "")
    cursor.execute("SELECT priority FROM issue_priority ORDER BY priority")
    priorities = cursor.fetchall()
    cursor.execute("SELECT name FROM issue_user ORDER BY name")
    users = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

def makePriorityPicklist(priority):
    picklist = "<SELECT NAME='priority'>"
    for p in priorities:
        picklist += "<OPTION%s>%s</OPTION>" % (
                priority == p[0] and " SELECTED" or "", p[0])
    return picklist + "</SELECT>"

def makeUserPicklist(user, fieldName):
    picklist = "<SELECT NAME='%s'><OPTION>[Nobody]</OPTION>" % fieldName
    for u in users:
        picklist += "<OPTION%s>%s</OPTION>" % (
                user == u[0] and " SELECTED" or "", u[0])
    return picklist + "</SELECT>"

#----------------------------------------------------------------------
# Display the information in a form.
#----------------------------------------------------------------------
form = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>CDR Development</TITLE>
 </HEAD>
 <BASEFONT FACE='Arial, Helvetica, sans-serif'>
 <LINK REL='STYLESHEET' HREF='/stylesheets/dataform.css'>
 <BODY BGCOLOR='lightgrey'>
  <FORM ACTION='/cgi-bin/cdr/EditIssue.py' METHOD='POST'>
   <INPUT TYPE='hidden' NAME='id' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='assigned' VALUE='%s'>
   <INPUT TYPE='hidden' NAME='resolved' VALUE='%s'>
   <BR>
   <CENTER>
    <INPUT TYPE='submit' NAME='Request' VALUE='New'>&nbsp;&nbsp;&nbsp;
    <INPUT TYPE='submit' NAME='Request' VALUE='Save'
           onClick="if (this.value == 'Save') {\
               this.value = 'Please Wait...';\
               this.form.submit(); \
            } \
            else\
                this.value = 'Please Be Patient...';">
           <BR>
   </CENTER>
   <BR>
   <TABLE WIDTH='100%%' CELLSPACING='1' CELLPADDING='1' BORDER='0'>
    <TR>
     <TD ALIGN='right'><B>Issue #:&nbsp;</B></TD>
     <TD><B>%s</B></TD>
     <TD ALIGN='right'><B>Logged:&nbsp;</B></TD>
     <TD><B>%s</B></TD>
     <TD ALIGN='right'><B>Assigned:&nbsp;</B></TD>
     <TD><B>%s</B></TD>
     <TD ALIGN='right'><B>Resolved:&nbsp;</B></TD>
     <TD><B>%s</B></TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>Priority:&nbsp;</B></TD>
     <TD>%s</TD>
     <TD ALIGN='right'><B>By:&nbsp;</B></TD>
     <TD>%s</TD>
     <TD ALIGN='right'><B>To:&nbsp;</B></TD>
     <TD>%s</TD>
     <TD ALIGN='right'><B>By:&nbsp;</B></TD>
     <TD>%s</TD>
    </TR>
    <TR>
     <TD VALIGN='top' ALIGN='right'><B>Description:&nbsp;</B></TD>
     <TD COLSPAN='7'>
      <TEXTAREA COLS='80' ROWS='4' NAME='description'>%s</TEXTAREA>
     </TD>
    </TR>
    <TR>
     <TD VALIGN='top' ALIGN='right'><B>Notes:&nbsp;</B></TD>
     <TD COLSPAN='7'>
      <TEXTAREA COLS='80' ROWS='4' NAME='notes'>%s</TEXTAREA>
     </TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (rec[0] and `rec[0]` or '',
       rec[4] and rec[4] or '',
       rec[6] and rec[6] or '',
       rec[0] and `rec[0]` or '[New]',
       rec[2] and rec[2][:16] or "[Not Yet]",
       rec[4] and rec[4][:16] or "[Not Yet]",
       rec[6] and rec[6][:16] or "[Not Yet]",
       makePriorityPicklist(rec[1]),
       makeUserPicklist(rec[3], 'logged_by'),
       makeUserPicklist(rec[5] and rec[5] or "", 'assigned_to'),
       makeUserPicklist(rec[7] and rec[7] or "", 'resolved_by'),
       rec[8] and cgi.escape(rec[8]).replace('\r', '') or "",
       rec[9] and cgi.escape(rec[9]).replace('\r', '') or "")
cdrcgi.sendPage(form)
