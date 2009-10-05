#----------------------------------------------------------------------
#
# $Id: TermTreeS.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Second prototype for CDR Terminology tree viewer.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, odbc

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = '/cgi-bin/cdr/TermTreeS.py'
SCRIPTL = '/cgi-bin/cdr/TermLinks.py'
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
subtree = fields and fields.getvalue("subtree") or ""
#termText= fields and fields.getvalue("termText") or ""

#----------------------------------------------------------------------
# Emit the top of the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<HTML>
 <HEAD>
  <TITLE>Major Term Hierarchies</TITLE>
	<script>
		function changeFrames(newRec,newLinks) {
   			parent.rec.location.href=newRec; 
   			parent.links.location.href=newLinks;
		} 
	function openWindow(pageURL) {
   		winStats='width=275,height=125'
   		if (navigator.appName.indexOf('Microsoft')>=0) {
      		winStats+=',left=10,top=25'
    	}else{
      		winStats+=',screenX=10,screenY=25'
    	}
		windowName=window.open(pageURL,'mywindow')
	}

	</script>
 </HEAD>
 <BODY>
  <HR>
  <CENTER>
   <H2>
    <FONT COLOR='teal'>Term Hierarchies</FONT>
   </H2>
	<a href="/cgi-bin/cdr/TermTreeS.py">Top Hierarchies - </a><a href="javascript:openWindow('http://mmdb2.nci.nih.gov/cgi-bin/cdr/TermSrch.py')">Search</a>
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
        conn = odbc.odbc('cdr/CdrGuest/readonly')
        if not conn: cdrcgi.bail('Unable to connect to CDR server.')
    cursor = conn.cursor()
    query = """\
SELECT DISTINCT child, num_grandchildren, title
           FROM term_children
          WHERE parent = %s
       ORDER BY title
""" % parent
    cursor.execute(query)
    children = []
    for rec in cursor.fetchall():
        children.append((`rec[0]`, rec[1], rec[2]))
    cursor = None
    return children

def showNodes(nodes, level, parentPath):
    global html
    pathSep = parentPath and "/" or ""
    for node in nodes:
        if not node[1]:
            image = BLANK
            path = None
        elif level < len(ids) and ids[level] == node[0]:
            image = MINUS
            path  = parentPath
        else:
            image = PLUS
            path  = parentPath + pathSep + node[0]
        html += "\240" * (1 + 4 * level)
        if image == BLANK:
            html += "<IMG SRC='%s' BORDER='0'>" % image
        else:
         	html += "<A HREF='%s?path=%s&subtree=%s' ><IMG SRC='%s' BORDER='0'></A>" % (SCRIPT, path,subtree, image)
 
        html += "\n<A HREF='#' onclick=\"changeFrames(\'%s?Filter=CDR210817&DocId=%s\','%s?docID=%s')\" >" % (FILTER,node[0],SCRIPTL,node[0])

        html += "\n<FONT COLOR='blue'>%s</FONT></A><BR>\n" % node[2]
        if image == MINUS:
            showNodes(getChildren(node[0]), level + 1, 
                    parentPath + pathSep + node[0])

if subtree:
#	topNodes = ((ids[len(ids)-1], 1, subtree),)        
	topNodes = ((ids[0], 1, subtree),)        


showNodes(topNodes, 0, "")

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + " </BODY>\n</HTML>\n")





