#----------------------------------------------------------------------
#
# $Id: TermTree3.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Second prototype for CDR Terminology tree viewer.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = '/cgi-bin/cdr/TermTree2.py'
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

conn     = None
topNodes = (('183045', 1, 'antineoplatic'),
            ('182216', 1, 'cancer'),
            ('187268', 1, 'gene'),
            ('187897', 1, 'genetic condition'),
            ('184264', 1, 'supportive care/therapy'))

def getChildren(parent):
    global conn
    if not conn:
        try:
            conn = cdrdb.connect('CdrGuest')
        except cdrdb.Error, info:
            cdrcgi.bail('Database failure: %s' % info[1][0])
    cursor = conn.cursor()
    query = """\
SELECT DISTINCT child, title
           FROM term_kids
          WHERE parent = %s
       ORDER BY title
""" % parent
    cursor.execute(query)
    children = []
    for row in cursor.fetchall():
        children.append((`row[0]`, 1, row[1]))
    cursor = None
    return children

def showNodes(nodes, level, parentPath):
    global html
    pathSep = parentPath and "/" or ""
    for node in nodes:
        if level < len(ids) and ids[level] == node[0]:
            image = MINUS
            path  = parentPath
        else:
            image = PLUS
            path  = parentPath + pathSep + node[0]
        html += "\240" * (1 + 4 * level)
        html += "<A HREF='%s?path=%s'><IMG SRC='%s' BORDER='0'></A>" % (SCRIPT,
                                                                        path,
                                                                        image)
        html += "\n<A HREF='%s?DocId=%s&Filter=CDR210817' TARGET='rec'>" % (
                FILTER, node[0])
        html += "\n<FONT COLOR='blue'>%s</FONT></A><BR>\n" % node[2]
        if image == MINUS:
            showNodes(getChildren(node[0]), level + 1, 
                    parentPath + pathSep + node[0])

showNodes(topNodes, 0, "")

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + " </BODY>\n</HTML>\n")
