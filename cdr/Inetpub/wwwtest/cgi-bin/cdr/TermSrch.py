
import cgi, cdr, cdrcgi, re, string, cdrdb


#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
searchTerm   = fields and fields.getvalue("searchTerm") or ""




conn = None

def doTermSearch(searchTerm):
    terms = []
    if searchTerm == "":
        return terms
    global conn
    if not conn:
        try:
            conn = cdrdb.connect('CdrGuest')
        except cdrdb.Error, info:
            cdrcgi.bail('Database failure: %s' % info[1][0])
    cursor = conn.cursor()

    query = """

SELECT DISTINCT    document.id, document.title,  query_term.[value],query_term.path
FROM       document INNER JOIN
               query_term ON document.id = query_term.doc_id
WHERE     ((query_term.path LIKE '/Term/TermName' OR
                      query_term.path LIKE '/Term/TermSynonym')) AND 
                      ((document.title LIKE '"""+searchTerm+"""') OR (query_term.value LIKE '"""+searchTerm+"""'))
ORDER BY document.title , query_term.value



"""

    cursor.execute(query)
    for rec in cursor.fetchall():
        terms.append((`rec[0]`,rec[1],rec[2],rec[3]))
    cursor = None
    return terms



def showTerms(terms):
    #----------------------------------------------------------------------
    # Emit the top of the page.
    #----------------------------------------------------------------------
    html = """\
    <!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
    <HTML>
     <HEAD>
     </HEAD>
     <BODY>
     <TABLE><TR><TD valign='top'>
 
      <FORM METHOD="POST" NAME="search" ACTION="TermSrch.py"> 

     Search: 
     <INPUT TYPE="text" NAME="searchTerm" SIZE="20" >
     <INPUT TYPE="submit" NAME="submit" VALUE="Search Now" >
     </td><td>
    """
    if len(terms) > 0:
        html += "<Table>\n"
        for term in terms:
            if term[3] == '/Term/TermSynonym':
                qual = "(Synonym: " + term[2] + ")"            
            else:
                qual = ""
            treeLink = "/cgi-bin/cdr/TermTreeS.py?path=%s&subtree=%s" % (term[0],term[1])
            html += "\n<tr><td><font size = '-2'><a href = '%s' target='tree'>subtree</a><br><a href='Filter.py?Filter=CDR210817&DocId=%s\' target='rec'>full term</a></font></td><td  valign='top'><font color='teal'>%s %s [%s]</font> </td><td> </td></tr>\n" % (treeLink,term[0],term[1],qual,term[0])
        html += "</table>"
    else:
        html += " <CENTER><H4><FONT COLOR='teal'>No terms now selected.</FONT></H4></CENTER>"

    html += "</td></tr></table>"
    #----------------------------------------------------------------------
    # Send the page back to the browser.
    #----------------------------------------------------------------------
    cdrcgi.sendPage(html + " </BODY>\n</HTML>\n")
#    html += " </BODY>\n</HTML>\n"
#    print html

showTerms(doTermSearch(searchTerm))

