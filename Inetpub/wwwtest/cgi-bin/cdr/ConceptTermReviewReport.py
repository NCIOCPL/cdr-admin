#----------------------------------------------------------------------
#
# $Id: ConceptTermReviewReport.py,v 1.2 2002-02-21 22:34:00 bkline Exp $
#
# Report for task 174.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/01/22 21:36:45  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
docId    = fields and fields.getvalue("DocId")    or None
termName = fields and fields.getvalue("DocTitle") or None
depth    = fields and fields.getvalue("Depth")    or "1"
request  = cdrcgi.getRequest(fields)
session  = cdrcgi.getSession(fields)
depth    = string.atoi(depth)
SUBMENU  = 'Report Menu'
if not session: cdrcgi.bail("User not logged in.")

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
if not docId and not termName:
    title   = "Terminology"
    instr   = "Concept/Term Review Report"
    script  = "ConceptTermReviewReport.py"
    buttons = ("Submit Request", SUBMENU, cdrcgi.MAINMENU)
    header  = cdrcgi.header(title, title, instr, script, buttons)
    form    = """\
    <TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>
    <TR>
      <TD ALIGN='right'><B>Term ID:&nbsp;</B></TD>
      <TD><INPUT NAME='DocId'></TD>
    </TR>
    <TR>
      <TD ALIGN='right'><B>Preferred Name:&nbsp;</B></TD>
      <TD><INPUT NAME='DocTitle'></TD>
    </TR>
    <TR>
      <TD ALIGN='right'><B>Child Depth:&nbsp;</B></TD>
      <TD><INPUT NAME='Depth' VALUE='1'></TD>
    </TR>
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Find the document ID.
#----------------------------------------------------------------------
elif docId:
    pattern = re.compile("(\d+)")
    match = pattern.search(docId)
    if not match:
        cdrcgi.bail("Invalid document ID: %s" % docId)
    intVal = string.atoi(match.group(1))
    if not intVal:
        cdrcgi.bail("Invalid document ID: %s" % docId)
    docId = intVal
else:
    try:
        conn = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute(u"""\
SELECT doc_id
  FROM query_term
 WHERE path = '/Term/PreferredName'
   AND value = ?""", termName)
        row = cursor.fetchone()
        if not row: cdrcgi.bail("Term '%s' not found." % termName)
        docId = row[0]
    except cdrdb.Error, info:
        cdrcgi.bail('Database connection failure: %s' % info[1][0])
    
#----------------------------------------------------------------------
# Display one term in the hierarchy.
#----------------------------------------------------------------------
def showTerm(term, offset, primaryTerm = 0):
    global tree
    termId = "CDR%010d" % string.atoi(term.id)
    coloredId = "<FONT COLOR='%s'>%s</FONT>" % (
                    primaryTerm and 'red' or 'blue', termId)
    termName = "<FONT COLOR='%s'>%s</FONT>" % (
                    primaryTerm and 'red' or 'blue', term.name)
    tree = tree + "%s<B>%s (%s)</B>\n" % (
            offset and (' ' * (offset - 1) * 2 + '+-') or '',
            termName,
            coloredId)

#----------------------------------------------------------------------
# Show the term in hierarchical context.
#----------------------------------------------------------------------
def showTree(node, level = 0):
    global tree, docId
    if not level:
        tree += "<H3>Hierarchy from %s</H3><PRE>\n" % node.name
    showTerm(node, level, node.id == docId)
    if node.children:
        for child in node.children:
            showTree(child, level + 1)
    if not level: tree += "</PRE>\n"

#----------------------------------------------------------------------
# Get the context from the server and build a hierachical display.
#----------------------------------------------------------------------
termSet = cdr.getTree(session, docId, depth)
if termSet.error: cdrcgi.bail(termSet.error)
roots = []
terms = termSet.terms
intId = docId
docId = `docId`
tree  = "<H2>Term Hierarchies for '%s'</H2>\n" % terms[docId].name
for term in terms.values():
    if not term.parents: roots.append(term.id)
for root in roots: showTree(terms[root])

#----------------------------------------------------------------------
# Filter the term and plug in the hierarchical tree display.
#----------------------------------------------------------------------
resp = cdr.filterDoc(session, ['name:Terminology QC Report Filter'], docId)
if type(resp) != type(()) and type(resp) != type([]):
    cdrcgi.bail(resp)
html = resp[0].replace('@@TERMTREE@@', ' --> %s <!-- ' % tree)

cdrcgi.sendPage(html)
