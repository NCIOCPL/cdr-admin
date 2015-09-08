#----------------------------------------------------------------------
# $Id$
#
# Prototype for editing CDR document types.
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Import required modules.
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi

#----------------------------------------------------------------------
# Load the fields from the form.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = fields and cdrcgi.getSession(fields) or None
doctype    = fields and fields.getvalue("doctype") or None
format     = fields and fields.getvalue("format") or None
versioning = fields and fields.getvalue("versioning") or None
created    = fields and fields.getvalue("created") or None
schema_mod = fields and fields.getvalue("schema_mod") or None
dtd        = fields and fields.getvalue("dtd") or None
schema     = fields and fields.getvalue("schema") or None
comment    = fields and fields.getvalue("comment") or None
request    = fields and fields.getvalue("request") or None
_created   = fields and fields.getvalue("_created") or None
dtinfo     = None
enumSets   = None
changed    = 0
SUBMENU    = "DocType Menu"

#----------------------------------------------------------------------
# Validate parameters
#----------------------------------------------------------------------
# Server demands upper case, forcing case here can save user some aggravation
if versioning: versioning = versioning.upper()

# ISO date time format with optional milliseconds for time.strptime()
ISO_DATE_TIME = '%Y-%m-%d %H:%M:%S.%f'

# Toggle this on for testing or debugging, off for giving min info to hacker
# cdrcgi.REVEAL_DEFAULT = True

# Validation
if doctype:
    cdrcgi.valParmVal(doctype, valList=cdr.getDoctypes(session))
if format:
    cdrcgi.valParmVal(format, valList=cdr.getDocFormats())
if schema:
    cdrcgi.valParmVal(schema, valList=cdr.getSchemaDocs(session))
if versioning:
    cdrcgi.valParmVal(versioning, valList=('Y', 'N'))
if created:
    cdrcgi.valParmDate(created, ISO_DATE_TIME)
if _created:
    cdrcgi.valParmDate(_created, ISO_DATE_TIME)
if schema_mod:
    cdrcgi.valParmDate(schema_mod, ISO_DATE_TIME)
if request:
    cdrcgi.valParmVal(request, valList=('Fetch', 'Retrieve', 'Store', SUBMENU,
                                        cdrcgi.MAINMENU))

# Comment can't be validated but can at least be sanitized
if comment:
    comment = cgi.escape(comment)

# DEBUG Don't know if this is used or not
if dtd:
    cdr.logwrite("EditDocType.py: dtd\n%s" % dtd)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("EditDocTypes.py", session)

#----------------------------------------------------------------------
# Get or store the document type information if requested.
#----------------------------------------------------------------------
if session and doctype and request:
    if request == 'Store':
        if format and versioning and schema:
            changed = 1
            cmd = _created and cdr.modDoctype or cdr.addDoctype
            dtinfo = cmd(session, cdr.dtinfo(type       = doctype,
                                             format     = format,
                                             versioning = versioning,
                                             schema     = schema,
                                             comment    = comment))
        else: cdrcgi.bail('Format, Versioning, and Schema data required')
    elif request == 'Fetch' or request == 'Retrieve':
        dtinfo = cdr.getDoctype(session, doctype)
    if dtinfo:
        if dtinfo.error: cdrcgi.bail(dtinfo.error)
        doctype    = dtinfo.type
        format     = dtinfo.format
        versioning = dtinfo.versioning
        created    = dtinfo.created
        schema_mod = dtinfo.schema_mod
        dtd        = dtinfo.dtd
        schema     = dtinfo.schema
        comment    = dtinfo.comment
        enumSets   = dtinfo.vvLists
        _created   = created

#----------------------------------------------------------------------
# Retrieve the list of schema documents which can be used for the type.
#----------------------------------------------------------------------
if session:
    schemaDocs = cdr.getSchemaDocs(session)
    if not schemaDocs:
        cdrcgi.bail("Failure loading list of Schema documents")
    if type(schemaDocs) == type(""):
        cdrcgi.bail(schemaDocs)
    schemaDocs.sort(lambda a,b: cmp(a.lower(), b.lower()))

#----------------------------------------------------------------------
# Display the CDR document form.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>CDR Document Types</TITLE>
  <META http-equiv='Content-Type' content='text/html;charset=utf-8'>
 </HEAD>
 <BASEFONT FACE="Arial, Helvetica, sans-serif">
 <LINK REL=STYLESHEET HREF=/stylesheets/dataform2.css>
 <BODY BGCOLOR=#EFEFEF>
  <H1>CDR Document Type Editor</H1>
  %s
  <FORM ACTION='/cgi-bin/cdr/EditDocType.py' METHOD='POST'>
   <INPUT TYPE='hidden' name='_created' VALUE='%s'>
   <TABLE>
""" % (changed and "<H2>Changes stored successfully</H2>" or "",
       _created or "")

#----------------------------------------------------------------------
# If not logged in yet add fields for username and password.
#----------------------------------------------------------------------
if not session:
    if fields and fields.getvalue(cdrcgi.USERNAME):
        cdrcgi.bail("Login failure")
    html = html + """\
    <TR>
     <TH ALIGN='right'>User ID</TH>
     <TD><INPUT NAME='%s'></TD>
    </TR>
    <TR>
     <TH ALIGN='right'>Password</TH>
     <TD><INPUT TYPE='password' NAME='%s'></TD>
    </TR>
""" % (cdrcgi.USERNAME, cdrcgi.PASSWORD)

#----------------------------------------------------------------------
# Otherwise, remember our session ID for subsequent requests.
#----------------------------------------------------------------------
else:
    html = html + """\
    <INPUT TYPE='hidden' VALUE='%s' NAME='%s'>
""" % (session, cdrcgi.SESSION)

#----------------------------------------------------------------------
# Add field for document type name and request buttons.
#----------------------------------------------------------------------
html = html + """\
    <TR>
     <TH ALIGN='right'>Name</TH>
     <TD>
      <INPUT NAME='doctype' VALUE='%s'>&nbsp;&nbsp;&nbsp;
      <INPUT TYPE='submit' NAME='request' VALUE='Retrieve'>&nbsp;&nbsp;&nbsp;
      <INPUT TYPE='submit' NAME='request' VALUE='Store'>&nbsp;&nbsp;&nbsp;
      <INPUT TYPE='submit' NAME='request' VALUE='%s'>&nbsp;&nbsp;&nbsp;
      <INPUT TYPE='submit' NAME='request' VALUE='%s'>
     </TD>
    </TR>
""" % (doctype or '', SUBMENU, cdrcgi.MAINMENU)

#----------------------------------------------------------------------
# Put up the rest of the form if appropriate.
#----------------------------------------------------------------------
if session:
    html = html + """\
    <TR>
     <TH ALIGN='right'>Format</TH>
     <TD><INPUT NAME='format' VALUE='%s'></TD>
    </TR>
    <TR>
     <TH ALIGN='right'>Versioning</TH>
     <TD><INPUT NAME='versioning' VALUE='%s'></TD>
    </TR>
    <TR>
     <TH ALIGN='right'>Created</TH>
     <TD><INPUT NAME='read-only-created' VALUE='%s'>&nbsp;(System supplied)</TD>
    </TR>
    <TR>
     <TH ALIGN='right'>Modified</TH>
     <TD><INPUT NAME='read-only-schemamod' VALUE='%s'>&nbsp;(System supplied)</TD>
    </TR>
""" % (format or '', versioning or '',
       created and created[:19] or '',
       schema_mod and schema_mod[:19] or '')
    # Note on above: 'created' and 'schema_mod' are 19 character ISO dates
    #                like '2015-07-16 15:53:08' with optional milliseconds

    html += """\
    <TR>
     <TH ALIGN='right'>Schema</TH>
     <TD>
      <SELECT NAME='schema'>
"""
    for schemaDoc in schemaDocs:
        html += """\
       <OPTION%s>%s</OPTION>
""" % (schema == schemaDoc and " SELECTED" or "", schemaDoc)
    html = html + """\
      </SELECT>
     </TD>
    </TR>
"""
    if 0 and dtd: html = html + """\
    <TR>
     <TH ALIGN='right'>DTD</TH>
     <TD><PRE>%s</PRE></TD>
    </TR>
""" % dtd
    html = html + """\
    <TR>
     <TH ALIGN='right' VALIGN='top'>Comment</TH>
     <TD><TEXTAREA NAME='comment' ROWS='5' COLS='80'>%s</TEXTAREA></TD>
    </TR>
   </TABLE>
  </FORM>
""" % (comment or '')
    if enumSets:
        for enumSet in enumSets:
            html += "<H2>Valid values for %s</H2>\n<UL>" % enumSet[0]
            for vv in enumSet[1]:
                html += "<LI>%s</LI>\n" % vv
            html += "</UL>\n"
    html += """\
 </BODY>
</HTML>
"""

#----------------------------------------------------------------------
# All done.
#----------------------------------------------------------------------
cdrcgi.sendPage(unicode(html, 'utf-8'))
