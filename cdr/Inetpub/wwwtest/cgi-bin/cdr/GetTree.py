#----------------------------------------------------------------------
#
# $Id: GetTree.py,v 1.3 2001-04-09 15:45:11 bkline Exp $
#
# Prototype for CDR Terminology tree viewer.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2001/04/08 22:56:59  bkline
# New version to handle optimized processing using stored procedure.
#
# Revision 1.1  2001/04/08 17:21:28  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = '/cgi-bin/cdr/GetTree.py'

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
docId   = fields and normalize(fields.getvalue("id")) or None #'CDR0000182201'
submit  = fields and fields.getvalue("submit") or None

#----------------------------------------------------------------------
# Emit the top of the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>CDR Terminology Tree</TITLE>
 </HEAD>
 <BODY>
  <H1>CDR Terminology Tree Viewer</H1>
  <FORM ACTION='%s' METHOD='post'>
   Tree Node Document Id: &nbsp;
   <INPUT NAME='id' VALUE='%s'>&nbsp;&nbsp;
   <INPUT TYPE='submit' NAME='submit' VALUE='Submit Request'><br><br>
  </FORM>
""" % (SCRIPT, docId or '')

def showTerm(term, offset, primaryTerm = 0):
    global html
    termId = "CDR%010d" % string.atoi(term.id)
    if primaryTerm:
        html = html + "%s<FONT COLOR='red'><B>%s (%s)</B></FONT>\n" % (
                offset and (' ' * (offset - 1) * 2 + '+-') or '',
                term.name, 
                termId)
    else:
        html = html + "%s<FONT COLOR='blue'>%s</FONT> "\
                      "(<A href='%s?id=%s'>%s</A>)\n" % (
                offset and (' ' * (offset - 1) * 2 + '+-') or '',
                term.name, 
                SCRIPT, 
                termId,
                termId)

def showTree(node, level = 0):
    global html, docId
    if not level:
        html += "<H3>Hierarchy from %s</H3><PRE>\n" % node.name
    showTerm(node, level, node.id == docId)
    if node.children:
        for child in node.children:
            showTree(child, level + 1)
    if not level: html += "</PRE>\n"

#----------------------------------------------------------------------
# If we have a request, do it.
#----------------------------------------------------------------------
if docId:
    termSet = cdr.getTree(('rmk', '***REDACTED***'), docId)
    if termSet.error: cdrcgi.bail(tree.error)
    roots = []
    terms = termSet.terms
    docId = `string.atoi(docId[3:])`
    html += "<H2>%s</H2>\n" % terms[docId].name
    for term in terms.values():
        if not term.parents: roots.append(term.id)
    for root in roots: showTree(terms[root])

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + " </BODY>\n</HTML>\n")
