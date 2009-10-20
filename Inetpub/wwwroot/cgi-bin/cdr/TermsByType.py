#----------------------------------------------------------------------
#
# $Id$
#
# Task 176: For a user-specified type or types, a report that displays all
# terms with the type(s) must be generated.  The report must display all terms
# within the "type" classification in a hierarchical structure.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb, string

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = 'TermsByType.py'
#SCRIPT  = 'DumpParams.py'
FILTER  = '/cgi-bin/cdr/Filter.py'

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
names     = fields and fields.getvalue("TypeName")        or None
request   = cdrcgi.getRequest(fields)
buttons   = ["Submit"]
title     = "CDR Terminology Report by Type"
banner    = "CDR Terminology"

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
if not names:
    title   = "CDR Terminology"
    instr   = "Term by Type Report"
    buttons = ("Submit Request",)
    header  = cdrcgi.header(title, title, instr, SCRIPT, buttons)
    form    = """\
    <TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>
    <TR>
      <TD ALIGN='right'><B>Type Name:&nbsp;</B></TD>
      <TD><INPUT NAME='TypeName'></TD>
    </TR>
    <TR>
      <TD ALIGN='right'><B>Type Name:&nbsp;</B></TD>
      <TD><INPUT NAME='TypeName'></TD>
    </TR>
    <TR>
      <TD ALIGN='right'><B>Type Name:&nbsp;</B></TD>
      <TD><INPUT NAME='TypeName'></TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Display a single term.
#----------------------------------------------------------------------
def showTerm(term, offset, primaryTerm = 0):
    global html
    idInt = string.atoi(term.id)
    idStr = "CDR%010d" % idInt
    coloredId = "<FONT COLOR='%s'>%s</FONT>" % (
                    primaryTerm and 'red' or 'blue', idStr)
    termName = "<A HREF='%s?DocId=%d&Filter=CDR266307'><FONT COLOR='%s'>"\
               "%s</FONT></A>" % (
                FILTER, idInt, primaryTerm and 'red' or 'blue', term.name)
    if primaryTerm:
        html = html + "%s<B>%s (%s)</B>\n" % (
                offset and (' ' * (offset - 1) * 2 + '+-') or '',
                termName,
                coloredId)
    else:
        html = html + "%s%s (<A href='%s?DocId=%d'>%s</A>)\n" % (
                offset and (' ' * (offset - 1) * 2 + '+-') or '',
                termName,
                SCRIPT, 
                idInt, 
                coloredId)

#----------------------------------------------------------------------
# Recursively show nodes in a Terminology hierarchical (sub)tree.
#----------------------------------------------------------------------
def showTree(node, level = 0):
    global html, docId
    if not level:
        html += "<H3>Hierarchy from %s</H3><PRE>\n" % node.name
    showTerm(node, level, node.id == `docId`)
    if node.children:
        for child in node.children:
            showTree(child, level + 1)
    if not level: html += "</PRE>\n"

#----------------------------------------------------------------------
# Create the top of the page.
#----------------------------------------------------------------------
header = cdrcgi.header(title, banner, "Terms by Type", SCRIPT, ())

#----------------------------------------------------------------------
# Normalize the set of type names.
#----------------------------------------------------------------------
if type(names) != type([]):
    names = [names]

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Queries to find the term names and relationships.
#----------------------------------------------------------------------
query1 = """\
SELECT DISTINCT k.child,
                k.parent
           INTO #term_kids
           FROM term_kids k
           JOIN query_term q
             ON q.doc_id = k.child
          WHERE q.path = '/Term/TermType/TermTypeName'
            AND q.value = ?
"""
"""SELECT DISTINCT d.title,
                d.id
                k.parent
           FROM term_kids k
           JOIN document d
             ON d.id = k.child
           JOIN query_term q
             ON q.doc_id = d.id
          WHERE q.path = '/Term/TermType/TermTypeName'
            AND q.value = ?
"""

#----------------------------------------------------------------------
# Display the hierarchy for each term type specified.
#----------------------------------------------------------------------
for name in names:
    cursor.execute(query, (name,))
    rows = cursor.fetchall()
    terms = buildTree(name, rows)
    showTree(terms)

#----------------------------------------------------------------------
# If we have a term, show its hierarchy.
#----------------------------------------------------------------------
else:
    if docId[:3] == "CDR": docId = docId[3:]
    docId = string.atoi(docId)
    termSet = cdr.getTree('guest', "CDR%010d" % docId)
    if termSet.error: cdrcgi.bail(tree.error)
    roots = []
    terms = termSet.terms
    html  = "<H2>%s</H2>\n" % terms[`docId`].name
    html += "<FONT COLOR='black'>"
    html += "<I>Click term to view formatted term document.<BR>\n"
    html += "Click document ID to navigate tree.</I></FONT><BR>\n"
    for term in terms.values():
        if not term.parents: roots.append(term.id)
    for root in roots: showTree(terms[root])

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + html + "</FORM></BODY></HTML>")
