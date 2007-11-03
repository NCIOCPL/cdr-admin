#----------------------------------------------------------------------
#
# $Id: TermTreeB.py,v 1.2 2007-11-03 14:15:07 bkline Exp $
#
# Second prototype for CDR Terminology tree viewer.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, win32com.client

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = '/cgi-bin/cdr/TermTreeB.py'
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
html = u"""\
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
	<a href="/cgi-bin/cdr/TermTreeB.py">Top Hierarchies - </a><a href="javascript:openWindow('http://mmdb2.nci.nih.gov/cgi-bin/cdr/TermSrch.py')">Search</a>
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
        conn = win32com.client.Dispatch("ADODB.Connection")
        try:
            conn.Open("driver={SQL Server};"\
                      "server=mmdb2;"\
                      "uid=CdrGuest;"\
                      "pwd=***REDACTED***;"\
                      "database=cdr")
        except:
            conn = None
            cdrcgi.bail('Unable to connect to CDR server.')
    rs = win32com.client.Dispatch("ADODB.Recordset")
    query = """\
SELECT DISTINCT child, num_grandchildren, title
           FROM term_children
          WHERE parent = %s
       ORDER BY title
""" % parent
    rs.Open(query, conn)
    children = []
    rs.MoveFirst()
    while not rs.EOF:
        cols = rs.Fields
        children.append((`cols[0].value`, cols[1].value,
                          cols[2].value))
        rs.MoveNext()
    rs.Close()
    rs = None
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
        html += u"\240" * (1 + 4 * level)
        if image == BLANK:
            html += u"<IMG SRC='%s' BORDER='0'>" % image
        else:
         	html += (u"<A HREF='%s?path=%s&subtree=%s' >"
                     u"<IMG SRC='%s' BORDER='0'></A>" %
                     (SCRIPT, path,subtree, image))

        html += (u"\n<A HREF='#' onclick=\"changeFrames(\'%s?"
                 u"Filter=CDR210817&DocId=%s\','%s?docID=%s')\" >" %
                 (FILTER, node[0], SCRIPTL, node[0]))

        html += u"\n<FONT COLOR='blue'>%s</FONT></A><BR>\n" % node[2]
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
cdrcgi.sendPage(html + u" </BODY>\n</HTML>\n")





