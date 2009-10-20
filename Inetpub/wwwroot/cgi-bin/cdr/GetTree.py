#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for CDR Terminology tree viewer.
#
# $Log: not supported by cvs2svn $
# Revision 1.6  2002/01/02 20:45:01  bkline
# Fixed typo in error handling; replaced hard-coded filter ID.
#
# Revision 1.5  2001/07/13 17:00:28  bkline
# Added links to the formatted Term documents.
#
# Revision 1.4  2001/04/09 17:50:02  bkline
# Fixed bug in call to cdr.normalize().
#
# Revision 1.3  2001/04/09 15:45:11  bkline
# Added call to normlize document ID.
#
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
FILTER  = '/cgi-bin/cdr/Filter.py'

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
docId   = fields and cdr.normalize(fields.getvalue("id")) or None
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
    coloredId = "<FONT COLOR='%s'>%s</FONT>" % (
                    primaryTerm and 'red' or 'blue', termId)
    termName = "<A HREF='%s?DocId=%s&Filter=name:Terminology QC Report'><FONT COLOR='%s'>"\
               "%s</FONT></A>" % (
                    FILTER, termId, primaryTerm and 'red' or 'blue', term.name)
    if primaryTerm:
        html = html + "%s<B>%s (%s)</B>\n" % (
                offset and (' ' * (offset - 1) * 2 + '+-') or '',
                termName,
                coloredId)
    else:
        html = html + "%s%s (<A href='%s?id=%s'>%s</A>)\n" % (
                offset and (' ' * (offset - 1) * 2 + '+-') or '',
                termName,
                SCRIPT, 
                termId,
                coloredId)

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
    termSet = cdr.getTree('guest', docId)
    if termSet.error: cdrcgi.bail(termSet.error)
    roots = []
    terms = termSet.terms
    docId = `string.atoi(docId[3:])`
    html += "<H2>%s</H2>\n" % terms[docId].name
    html += "<I>Click term to view formatted term document.<BR>\n"
    html += "Click document ID to navigate tree.</I><BR>\n"
    for term in terms.values():
        if not term.parents: roots.append(term.id)
    for root in roots: showTree(terms[root])

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + " </BODY>\n</HTML>\n")
