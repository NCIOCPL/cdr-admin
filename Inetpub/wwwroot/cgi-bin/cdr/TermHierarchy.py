#----------------------------------------------------------------------
#
# $Id: TermHierarchy.py,v 1.5 2002-08-15 19:38:42 bkline Exp $
#
# Prototype for display of Term hierarchy (requirement 2.6 from 
# Terminology Processing Requirements).
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2002/08/12 20:59:58  bkline
# Added better error message for terms without hierarchy.
#
# Revision 1.3  2002/05/08 17:41:53  bkline
# Updated to reflect Volker's new filter names.
#
# Revision 1.2  2002/04/25 02:58:29  bkline
# Replaced hardwired filter ID with name.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, cdrdb, string

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = 'TermHierarchy.py'
#SCRIPT  = 'DumpParams.py'
FILTER  = '/cgi-bin/cdr/Filter.py'

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
name      = fields and fields.getvalue("TermName")        or None
docId     = fields and fields.getvalue("DocId")           or None
request   = cdrcgi.getRequest(fields)
buttons   = ["Submit"]
title     = "CDR Terminology Hierarchy Display"
banner    = "CDR Terminology"
message   = ""

#----------------------------------------------------------------------
# Display a single term.
#----------------------------------------------------------------------
def showTerm(term, offset, primaryTerm = 0):
    global html
    idInt = string.atoi(term.id)
    idStr = "CDR%010d" % idInt
    coloredId = "<FONT COLOR='%s'>%s</FONT>" % (
                    primaryTerm and 'red' or 'blue', idStr)
    termName = "<A HREF='%s?DocId=%d&Filter=name:Denormalization Filter "\
               "(1/1): Terminology&Filter1=name:Terminology QC Report Filter'>"\
               "<FONT COLOR='%s'>"\
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
# Menu listing matches for term name search.
#----------------------------------------------------------------------
def showTermList(rows):
    header = cdrcgi.header(title, banner, "Select Term", SCRIPT)
    menu = "<H2>Select focus term for hierarchical display</H2><OL>"
    for row in rows:
        menu += """\
<LI><A href='%s?DocId=%d&%s=%s'>%s</A></LI>
""" % (SCRIPT, row[0], cdrcgi.SESSION, session, row[1])
    cdrcgi.sendPage(header + menu + "</OL></FORM></BODY></HTML>")

#----------------------------------------------------------------------
# If we have a name search, find the matching terms.
#----------------------------------------------------------------------
if name:
    try:
        query = """\
SELECT DISTINCT d.id, d.title
           FROM document d
           JOIN query_term t
             ON t.doc_id = d.id
          WHERE t.path IN ('/Term/PreferredName', 
                           '/Term/OtherName/OtherTermName')
            AND t.value %s '%s'
""" % (cdrcgi.getQueryOp(name), cdrcgi.getQueryVal(name))
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        cursor = None
        if len(rows) == 0:
            docId = None
            message = "No Term documents match '%s'" % name
        elif len(rows) == 1:
            docId = str(rows[0][0])
        else:
            showTermList(rows)
    except cdrdb.Error, info:
        cdrcgi.bail('Failure connecting to CDR: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the top of the page.
#----------------------------------------------------------------------
header = cdrcgi.header(title, banner, "Hierarchical Display", SCRIPT, 
        buttons)
if message:
    header += "<H2>%s</H2>" % message

#----------------------------------------------------------------------
# Put up a search box if we don't already have a Term document.
#----------------------------------------------------------------------
if not docId:
    html = "<B>Term Name:&nbsp;</B><INPUT NAME='TermName'><BR><BR>"

#----------------------------------------------------------------------
# If we have a term, show its hierarchy.
#----------------------------------------------------------------------
else:
    if docId[:3] == "CDR": docId = docId[3:]
    docId = string.atoi(docId)
    termSet = cdr.getTree('guest', "CDR%010d" % docId)
    if termSet.error: cdrcgi.bail(tree.error)
    if not termSet.terms: cdrcgi.bail("Term document does not specify "
                                      "any relationships to any other "
                                      "documents.")
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
