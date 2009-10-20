#----------------------------------------------------------------------
#
# $Id$
#
# Second prototype for CDR Terminology tree viewer.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = '/cgi-bin/cdr/TermTree.py'
FILTER  = '/cgi-bin/cdr/Filter.py'
PLUS    = '/images/tree-plus.gif'
MINUS   = '/images/tree-minus.gif'
BLANK   = '/images/tree-blank.gif'

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
path    = fields and fields.getvalue("path") or ""
ids     = path.split("/")

#----------------------------------------------------------------------
# Emit the top of the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>Major Term Hierarchies</TITLE>
 </HEAD>
 <BODY>
  <HR>
  <CENTER>
   <H2>
    <FONT COLOR='teal'>Major Term Hierarchies</FONT>
   </H2>
  </CENTER>
  <HR>
"""

topNodes = (cdr.QueryResult('CDR0000183045', 'Term', 'antineoplatic'),
            cdr.QueryResult('CDR0000182216', 'Term', 'cancer'),
            cdr.QueryResult('CDR0000187268', 'Term', 'gene'),
            cdr.QueryResult('CDR0000187897', 'Term', 'genetic condition'),
            cdr.QueryResult('CDR0000184264', 'Term', 'supportive care/therapy'))

def showNodes(nodes, level, parentPath):
    global html
    pathSep = parentPath and "/" or ""
    prevNode = ""
    for node in nodes:
        # XXX Take care of bogus dups until we track down the cause.
        if prevNode == node.docTitle: continue
        else: prevNode = node.docTitle
        if level < len(ids) and ids[level] == node.docId:
            image = MINUS
            path  = parentPath
        else:
            image = PLUS
            path  = parentPath + pathSep + node.docId
        html += "\240" * (1 + 4 * level)
        html += "<A HREF='%s?path=%s'><IMG SRC='%s' BORDER='0'></A>" % (SCRIPT,
                                                                        path,
                                                                        image)
        html += "\n<A HREF='%s?DocId=%s&Filter=CDR210817' TARGET='rec'>" % (
                FILTER, node.docId)
        html += "\n<FONT COLOR='blue'>%s</FONT></A><BR>\n" % node.docTitle
        if image == MINUS:
            children = cdr.search('guest', 
                    'CdrAttr/Term/TermParent/@cdr:ref="%s"' % node.docId)
            if type(children) == type(""): cdrcgi.bail(children)
            showNodes(children, level + 1, 
                    parentPath + pathSep + node.docId)

showNodes(topNodes, 0, "")

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + " </BODY>\n</HTML>\n")
