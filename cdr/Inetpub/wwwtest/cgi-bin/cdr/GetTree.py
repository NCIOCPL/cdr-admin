#----------------------------------------------------------------------
#
# $Id: GetTree.py,v 1.1 2001-04-08 17:21:28 bkline Exp $
#
# Prototype for CDR Terminology tree viewer.
#
# $Log: not supported by cvs2svn $
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
docId   = fields and fields.getvalue("id") or None #'CDR0000182201'
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
    if primaryTerm:
        html = html + "%s<FONT COLOR='red'><B>%s (%s)</B></FONT>\n" % (
                #ffset and ('+' + '-' * offset) or '',
                offset and (' ' * (offset - 1) * 2 + '+-') or '',
                term.name, 
                term.id)
    else:
        html = html + "%s<FONT COLOR='blue'>%s</FONT> "\
                      "(<A href='%s?id=%s'>%s</A>)\n" % (
                #ffset and ('+' + '-' * offset) or '',
                offset and (' ' * (offset - 1) * 2 + '+-') or '',
                term.name, 
                SCRIPT, 
                term.id,
                term.id)

def showTermAndChildren(node, offset, primaryTerm = 0):
    global html
    if not offset:
        html += "<H2>Hierarchy from %s</H2><PRE>\n" % node.name
    showTerm(node, offset, primaryTerm)
    if node.children:
        for child in node.children:
            showTermAndChildren(child, offset + 1)
    if not offset:
        html += "</PRE>\n"

def showTree(tree, parentList):
    global html
    topParent = parentList[-1]
    if topParent.parents:
        for parent in topParent.parents:
            showTree(tree, parentList + [parent])
    else:
        offset = 0
        html = html + "<H2 COLOR='blue'>Hierarchy from %s</H2><PRE>\n" % topParent.name
        parentList.reverse()
        for parent in parentList:
            showTerm(parent, offset)
            offset = offset + 1
        showTermAndChildren(tree, offset, 1)
        html = html + "</PRE>\n"

#----------------------------------------------------------------------
# If we have a request, do it.
#----------------------------------------------------------------------
if docId:
    tree = cdr.getTree(('rmk', '***REDACTED***'), docId)
    if tree.error: cdrcgi.bail(tree.error)
    if tree.parents:
        for parent in tree.parents:
            showTree(tree, [parent])
    else: showTermAndChildren(tree, 0, 1)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + " </BODY>\n</HTML>\n")
