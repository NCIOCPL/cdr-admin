
import cgi, cdr, cdrcgi, re, string, cdrdb


#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
#path    = fields and fields.getvalue("path") or ""
#ids     = path.split("/")
docID   = fields and fields.getvalue("docID") or ""
docIDs  = docID.split("/")
myDoc   = docIDs[len(docIDs)-1]



conn     = None

def getLinksTo(docID):
    global conn
    if not conn:
        try:
            conn = cdrdb.connect('CdrGuest')
        except cdrdb.Error, info:
            cdrcgi.bail('Database failure: %s' % info[1][0])
    cursor = conn.cursor()


    query = """
SELECT DISTINCT document.id, document.title, doc_type.name, doc_type.id
FROM  document,query_term,doc_type
  WHERE document.id = query_term.doc_id AND
    doc_type.id = document.doc_type AND NOT query_term.path LIKE '/Term%' AND
    (query_term.[value] LIKE '%"""+docID+"""') 
    ORDER BY document.title
"""

    cursor.execute(query)
    links = []
    for rec in cursor.fetchall():
        links.append((`rec[0]`,rec[1],rec[2]))
    
    cursor = None
    return links



def showLinks(links):
    #----------------------------------------------------------------------
    # Emit the top of the page.
    #----------------------------------------------------------------------
    html = """\
    <!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
    <HTML>
     <HEAD>
     </HEAD>
     <BODY>
    """

    if len(links) > 0:
#        html += " <CENTER><H4><FONT COLOR='teal'>Links to this term:</FONT></H4></CENTER>"
        html += "<Table>"
#        html += "<row><th>ID</th><th>Doc Title</th></row>"
        for link in links:
            html += "<tr><td  valign='top'><font color='teal'><b> %s (%s)</b></font> </td><td> %s </td>" % (link[2],link[0],link[1])
        html += "</row></table>"
    else:
        html += " <CENTER><H4><FONT COLOR='teal'>No links to this Term</FONT></H4></CENTER>"
    #----------------------------------------------------------------------
    # Send the page back to the browser.
    #----------------------------------------------------------------------
    cdrcgi.sendPage(html + " </BODY>\n</HTML>\n")

showLinks(getLinksTo(myDoc))
