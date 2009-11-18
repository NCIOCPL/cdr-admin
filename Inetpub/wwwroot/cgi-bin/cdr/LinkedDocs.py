#----------------------------------------------------------------------
#
# $Id$
#
# Reports on documents which link to a specified document.
#
# BZIssue::4672
# 
# $Log: LinkedDocs.py,v $
# Revision 1.6  2007/11/03 14:15:07  bkline
# Unicode encoding cleanup (issue #3716).
#
# Revision 1.5  2005/02/17 22:48:45  venglisc
# Added CDR-ID to header of report and changed display of header from
# using H4 tags to using table and CSS format (Bug 1532).
#
# Revision 1.4  2002/06/24 17:15:45  bkline
# Fixed encoding problems.
#
# Revision 1.3  2002/04/24 20:36:03  bkline
# Changed "Title" label to "DocTitle" as requested by Eileen (issue #161).
#
# Revision 1.2  2002/02/21 15:22:03  bkline
# Added navigation buttons.
#
# Revision 1.1  2002/01/22 21:36:08  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
docId    = fields.getvalue("DocId")          or None
fragId   = fields.getvalue("FragId")         or ""
docTitle = fields.getvalue("DocTitle")       or None
docType  = fields.getvalue("DocType")        or None
ldt      = fields.getvalue("LinkingDocType") or None
language = fields.getvalue("Language")       or "EN"
idBlkd   = fields.getvalue("WithBlocked1")   or "Y"
listBlkd = fields.getvalue("WithBlocked2")   or "Y"
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
title    = "Linked Documents Report"
instr    = "Report on documents which link to a specified document"
script   = "LinkedDocs.py"
SUBMENU  = 'Report Menu'
buttons  = (SUBMENU, cdrcgi.MAINMENU)

styleOutput = """\
   <STYLE type="text/css">
    H3            { font-weight: bold;
                    font-family: Arial;
                    font-size: 16pt;
                    margin: 8pt; }
    *.doctype     { font-size: 14pt;
                    font-weight: bold; }
    TABLE.output  { width: 90%; }
    th.col1       { font-size: 12pt; 
                    font-weight: bold;
                    width: 10%; }
    th.col2       { font-size: 12pt; 
                    font-weight: bold;
                    width: 65%; }
    th.col3       { font-size: 12pt; 
                    font-weight: bold;
                    width: 15%; }
    th.col4       { font-size: 12pt; 
                    font-weight: bold;
                    width: 10%; }
    h            { font-weight: bold; }
    TD.header     { font-weight: bold;
                    text-align: center; }
    TR.odd        { background-color: #E7E7E7; }
    TR.even       { background-color: #FFFFFF; }
    TR.head       { background-color: #D2D2D2; }
    .link         { color: blue;
                    text-decoration: underline; }
    tr.select:hover, tr.outrow:hover
                  { background: #FFFFCC; }
   </STYLE>
"""

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Extract integer for document ID.
#----------------------------------------------------------------------
def extractDocId(id):
    if id is None: return None
    if type(id) == type(9): return id
    digits = re.sub('[^\d]', '', id)
    return string.atoi(digits)

#----------------------------------------------------------------------
# Create string representing the current date.
#----------------------------------------------------------------------
def makeDate():
    now = time.time()
    return time.strftime("%B %d, %Y", time.localtime(now))

#----------------------------------------------------------------------
# Retrieve the list of document type names.
#----------------------------------------------------------------------
def getDocTypes():
    try:
        cursor.execute("""\
SELECT DISTINCT name 
           FROM doc_type 
          WHERE name IS NOT NULL and name <> '' AND active = 'Y'
       ORDER BY name
""")
        return cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Create a picklist for document types.
#----------------------------------------------------------------------
def makeList(fieldName, docTypes):
    picklist = u"<SELECT NAME='%s'><OPTION SELECTED>Any Type</OPTION>" \
        % fieldName
    for docType in docTypes:
        picklist += u"<OPTION>%s</OPTION>" % docType[0]
    return picklist + u"</SELECT>"

#----------------------------------------------------------------------
# Get the user name and format it for display at the bottom of the page.
#----------------------------------------------------------------------
def getUser():
    if not session: return u""
    try:
        cursor.execute("""
SELECT DISTINCT u.fullname
           FROM usr u
           JOIN session s
             ON s.usr = u.id
          WHERE s.name = ?""", session)
        uName = cursor.fetchone()[0]
        if not uName: return u""
        return u"<BR><I><FONT SIZE='-1'>%s</FONT></I><BR>" % uName
    except: return u""
#----------------------------------------------------------------------
# If we have a document ID, produce a report.
#----------------------------------------------------------------------
if docId:
    try:
        idPieces = cdr.exNormalize(docId)
    except Exception, e:
        cdrcgi.bail("%s" % e)
    docId = idPieces[1]
    fragId = fragId or idPieces[2]
    try:
        # Get the target doc info.
        cursor.execute("""\
SELECT d.title, t.name
  FROM document d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE d.id = ?""", docId)
        targetDocInfo = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])

    # Get the info for the linking docs.
    ldtConstraint = fragConstraint = blockConstraint = ""
    if ldt and ldt != 'Any Type':
        ldtConstraint = "AND t.name = '%s'" % ldt
    if fragId:
        fragConstraint = "AND n.target_frag = '%s'" % fragId.replace("'", "''")
    if idBlkd == 'N':
        blockConstraint = "AND d.active_status = 'A'"
    query = """\
SELECT DISTINCT d.id, d.title, t.name, n.source_elem, n.target_frag
           FROM document d
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN link_net n
             ON n.source_doc = d.id
          WHERE n.target_doc = ?
            %s
            %s
            %s
       ORDER BY t.name, d.title, n.source_elem, n.target_frag""" % (
                              ldtConstraint, fragConstraint, blockConstraint)
    try:
        cursor.execute(query, extractDocId(docId))
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])

    # Build the report and show it.
    title2 = u"%s for %s Document CDR%d %s" % (title, targetDocInfo[1], 
            docId, makeDate())
    html = cdrcgi.header(title2, title, instr, script, buttons, 
                         stylesheet = styleOutput)
    report = u"""\
    <table>
     <tr>
      <td class="docLabel" align="right">Document Type:</td>
      <td class="docValue">%s</td>
     </tr>
     <tr>
      <td class="docLabel" align="right">Document Title:</td>
      <td class="docValue">%s</td>
     </tr>
     <tr>
      <td class="docLabel" align="right">Document ID:</td>
      <td class="docValue">%s</td>
     </tr>
    </table>
<BR>

<B><I>Linked Documents</I></B>
<BR>&nbsp;<BR>
""" % (targetDocInfo[1], targetDocInfo[0], docId)

    prevDocType = ""
    row = cursor.fetchone()
    while row:
        linkingDocId       = row[0]
        linkingDocTitle    = row[1]
        linkingDocType     = row[2]
        linkingElementName = row[3]
        linkingFragId      = row[4]
        if linkingDocType != prevDocType:
            if prevDocType:
                report += u"""\
  </TABLE>"""
            prevDocType = linkingDocType
            report += u"""\
  <BR><span class="doctype">%s</span><BR><BR>
  <TABLE class="output" CELLSPACING='0' CELLPADDING='2' BORDER='1'>
   <TR>
    <TH class="col1">DocID</TD>
    <TH class="col2">DocTitle</TD>
    <TH class="col3">ElementName</TD>
    <TH class="col4">FragmentID</TD>
   </TR>""" % linkingDocType
        report += u"""\
   <TR class="outrow">
    <TD VALIGN='top'>CDR%d</TD>
    <TD VALIGN='top'>%s</TD>
    <TD VALIGN='top'>%s</TD>
    <TD VALIGN='top'>%s</TD>
   </TR>""" % (linkingDocId, linkingDocTitle, linkingElementName,
               linkingFragId or "&nbsp;")
        row = cursor.fetchone()
    if prevDocType:
        html += report + u"""\
  </TABLE>"""
    else:
        frag = (fragId and "#%s" % fragId) or ""
        html += u"""\
  <H3>No Documents Currently Link to CDR%d%s</H3>""" % (docId, frag)
    html += u"""\
  </FORM>
  %s
 </BODY>
</HTML>""" % getUser()
    cdrcgi.sendPage(html)

#----------------------------------------------------------------------
# Search for linked document by title, if so requested.
#----------------------------------------------------------------------
if docTitle:
    header   = cdrcgi.header(title, title, instr, script, 
                                    ("Submit", SUBMENU, cdrcgi.MAINMENU),
                                    stylesheet = styleOutput)
    docTypes = getDocTypes()
    dtConstraint = ""
    if docType and docType != 'Any Type':
        dtConstraint = "AND t.name = '%s'" % docType
    titleParam = docTitle
    if docTitle[-1] != '%':
        titleParam += '%'
    query = """\
SELECT d.id, d.title
  FROM document d
  JOIN doc_type t
    ON t.id = d.doc_type
 WHERE d.title LIKE ?
   %s""" % dtConstraint
    try:
        cursor.execute(query, titleParam)
        row = cursor.fetchone()

        # Check to make sure we got at least one row.
        if not row:
            cdrcgi.bail("No documents match '%s'" % docTitle)
        form     = u"""\
   <BR>
   <B>Linking Document Type:&nbsp;</B>
   %s
   <BR><BR>
   <TABLE>""" % makeList(
        "LinkingDocType", docTypes)
        while row:
            form += u"""
    <TR class="select">
     <TD>
      <INPUT TYPE='radio' NAME='DocId' VALUE='%d' id='%s'>
     </TD>
     <TD><label for='%s'>CDR%d</label></TD>
     <TD><label for='%s'>%s</label></TD>
    </TR>""" % (row[0], row[0], row[0], row[0], row[0], row[1])
            row = cursor.fetchone()
        form += u"""
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <INPUT TYPE='hidden' Name='WithBlocked1' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>""" % (cdrcgi.SESSION, session and session or '', listBlkd)
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Put up the main request form.
#----------------------------------------------------------------------
header   = cdrcgi.header(title, title, instr, script, ("Submit",
                                                       SUBMENU,
                                                       cdrcgi.MAINMENU))
docTypes = getDocTypes()
form     = u"""\
   <fieldset>
    <legend>&nbsp;Find Document by Document ID or ...&nbsp;</legend>
    <table>
     <tr>
      <td>
       <label class='ilabel' for='DocId'>Document ID</label>
      </td>
      <td>
       <input name='DocId'>
      </td>
     </tr>
     <tr>
      <td>
       <label class='ilabel' for='FragId'>Fragment ID</label>
      </td>
      <td>
       <input name='FragId'>
      </td>
     </tr>
     <tr>
      <td>
       <label class='ilabel' for='XXX'>Linking Document Type</label>
      </td>
      <td>
       %s
      </td>
     </tr>
     <tr>
      <td>Include Blocked?:&nbsp;</td>
      <td>
       <label for='Y1'>Yes</label>
          <input type='radio' name='WithBlocked1' value='Y' id='Y1'>
       &nbsp;&nbsp;&nbsp;
       <label for='N1'>No</label>
          <input type='radio' name='WithBlocked1' value='N' CHECKED id='N1'>
      </td>
     </tr>
    </table>
   </fieldset>
   <p/>
   <fieldset>
    <legend>&nbsp;... Find Document by Document Type and Title&nbsp;</legend>
    <table>
     <tr>
      <td>
       <label class='ilabel' for='DocTitle'>Document Title</label>
      </td>
      <td>
       <input name='DocTitle' size='40'>
      </td>
     </tr>
     <tr>
      <td>Document Type:&nbsp;</td>
      <td>%s</td>
     </tr>
     <!--tr>
      <td>Language:&nbsp;</td>
      <td>
       <select name='Language'>
        <option SELECTED>EN</option>
        <option>ES</option>
       </select>
      </td>
     </tr-->
     <tr>
      <td>Include Blocked?:&nbsp;</td>
      <td>
       <label for='Y2'>Yes</label>
          <input type='radio' name='WithBlocked2' value='Y' id='Y2'>
       &nbsp;&nbsp;&nbsp;
       <label for='N2'>No</label>
          <input type='radio' name='WithBlocked2' value='N' CHECKED id='N2'>
      </td>
     </tr>
    </table>
   </fieldset>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (makeList("LinkingDocType", docTypes), 
       makeList("DocType", docTypes),
       cdrcgi.SESSION, session and session or '')
cdrcgi.sendPage(header + form)
