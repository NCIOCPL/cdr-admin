# see 3316 for details.
import cdrcgi, cdrdb, cgi

fields = cgi.FieldStorage()
SemanticTerms = fields and fields.getvalue("SemanticTerms") or "True"

class Term:
    def __init__(self, name, id, isSemantic):
        self.name = name
        self.id = id
        self.isSemantic = isSemantic
        #self.aliases = []
        self.children = []
        self.parents = []
        self.uname = name.upper()

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
try:
    # create a temporary table to store info
    cursor.execute("CREATE TABLE #terms(id INTEGER, parent INTEGER, boolSemanticType INTEGER)")
    conn.commit()

    # populate with all the semantic terms
    cursor.execute("""\
        INSERT INTO #terms
             SELECT doc_id, NULL, 1
               FROM query_term
              WHERE path = '/Term/TermType/TermTypeName'
                AND value = 'Semantic type'""")
    conn.commit()

    # populate with all the non-semantic terms
    cursor.execute("""\
        INSERT INTO #terms
             SELECT doc_id, NULL, 0
               FROM query_term
              WHERE path = '/Term/TermType/TermTypeName'
                AND value <> 'Semantic type'
                AND value <> 'Obsolete term'""")
    conn.commit()    
    
    done = 0
    while not done:
        # add the semantic types
        cursor.execute("""\
            INSERT INTO #terms
                 SELECT p.doc_id, p.int_val, 1
                   FROM query_term p
                   JOIN #terms t
                     ON t.id = p.int_val
                  WHERE p.path = '/Term/TermRelationship/ParentTerm'
                               + '/TermId/@cdr:ref'
                    AND NOT EXISTS (SELECT *
                                      FROM #terms
                                     WHERE id = p.doc_id
                                       AND parent = p.int_val)
                    AND p.doc_id IN (SELECT doc_id
                                           FROM query_term
                                          WHERE path = '/Term/TermType'
                                                     + '/TermTypeName'
                                            AND value = 'Semantic type')
                    AND p.int_val IN (SELECT doc_id
                                           FROM query_term
                                          WHERE path = '/Term/TermType'
                                                     + '/TermTypeName'
                                            AND value = 'Semantic type')
                                            """)
        
        if not cursor.rowcount:
            done = 1
        conn.commit()

        # add the non semantic types who don't have Semantic type documents as parents
        cursor.execute("""\
            INSERT INTO #terms
                 SELECT p.doc_id, p.int_val, 0
                   FROM query_term p
                   JOIN #terms t
                     ON t.id = p.int_val
                  WHERE p.path = '/Term/SemanticType/@cdr:ref'
                    AND NOT EXISTS (SELECT *
                                      FROM #terms
                                     WHERE id = p.doc_id
                                       AND parent = p.int_val)
                    AND p.doc_id IN (SELECT doc_id
                                           FROM query_term
                                          WHERE path = '/Term/TermType'
                                                     + '/TermTypeName'
                                            AND value <> 'Semantic type'
                                            AND value <> 'Obsolete term')
                    AND p.int_val IN (SELECT doc_id
                                           FROM query_term
                                          WHERE path = '/Term/TermType'
                                                     + '/TermTypeName'
                                            AND value <> 'Obsolete term')
                                            """)

        if not cursor.rowcount:
            done = 1
        conn.commit()        

        # add the non semantic types who don't have Semantic type documents as parents
        cursor.execute("""\
            INSERT INTO #terms
                 SELECT p.doc_id, p.int_val, 0
                   FROM query_term p
                   JOIN #terms t
                     ON t.id = p.int_val
                  WHERE p.path = '/Term/TermRelationship/ParentTerm'
                               + '/TermId/@cdr:ref'
                    AND NOT EXISTS (SELECT *
                                      FROM #terms
                                     WHERE id = p.doc_id
                                       AND parent = p.int_val)
                    AND p.doc_id IN (SELECT doc_id
                                           FROM query_term
                                          WHERE path = '/Term/TermType'
                                                     + '/TermTypeName'
                                            AND value <> 'Semantic type'
                                            AND value <> 'Obsolete term')
                    AND p.int_val IN (SELECT doc_id
                                           FROM query_term
                                          WHERE path = '/Term/TermType'
                                                     + '/TermTypeName'
                                            AND value <> 'Obsolete term')
                                            """)

        if not cursor.rowcount:
            done = 1
        conn.commit()

        
    cursor.execute("""\
        SELECT d.id, n.value, d.parent, d.boolSemanticType
          FROM #terms d
          JOIN query_term n
            ON n.doc_id = d.id
         WHERE n.path = '/Term/PreferredName'
      ORDER BY d.parent desc""")
    terms = {}
    for id, name, parent, isSemantic in cursor.fetchall():
        if terms.has_key(id):
            term = terms[id]
        else:
            term = terms[id] = Term(name.rstrip(),id,isSemantic)
        if parent and parent not in term.parents:
            term.parents.append(parent)
            
    #if flavor != 'short':
    #    cursor.execute("""\
    #        SELECT DISTINCT q.doc_id, q.value
    #                   FROM query_term q
    #                   JOIN #terms t
    #                     ON t.id = q.doc_id
    #                  WHERE q.path = '/Term/OtherName/OtherTermName'""")
    #    for id, name in cursor.fetchall():
    #        if name not in terms[id].aliases:
    #            terms[id].aliases.append(name)
except:
    raise
    cdrcgi.bail("Database failure reading terminology information")

for id in terms:
    term = terms[id]
    for parent in term.parents:
        try:
            alreadyHaveIt = 0
            for child in terms[parent].children:
                if child.name == term.name:
                    alreadyHaveIt = 1
                    break
            if not alreadyHaveIt:
                terms[parent].children.append(term)
        except:
            cdrcgi.bail("No object for parent %s" % str(parent))

# add all terms that don't have parents
def addTerms(terms,SemanticTerms):
    html=""
    
    # create a dummy partent node so we can sort the top node
    parentTerm = terms[-1] = Term("",-1,0)

    for id in terms:
        if id > 0:
            term = terms[id]
            if SemanticTerms == 'True':
                if not term.parents and term.isSemantic:
                    parentTerm.children.append(term)
            else:
                if not term.parents and not term.isSemantic:
                    parentTerm.children.append(term)
                                
    parentTerm.children.sort(lambda a,b: cmp(a.uname, b.uname))
    
    for rootTerm in parentTerm.children:
        html += addTerm(rootTerm,rootTerm)
        
    return html

# add a term to the hierarchy list
def addTerm(t,parent):
    html=""

    if not t.parents:
        html += """        
var myobj%s = { label: "%s", id:"treeRoot%s" };
var tmpNode%s = new YAHOO.widget.TextNode(myobj%s, root, false);""" % (t.id,cgi.escape(cdrcgi.unicodeToLatin1(t.name)),
                                                                       t.id,t.id,t.id)
    else:
        html += """        
var myobj%s = { label: "%s", id:"treeNode%s" };
var tmpNode%s = new YAHOO.widget.TextNode(myobj%s, tmpNode%s, false);""" % (t.id,cgi.escape(cdrcgi.unicodeToLatin1(t.name)),
                                                                          t.id,t.id,t.id,parent.id)

    #if t.aliases or t.children:
    if t.children:
        t.children.sort(lambda a,b: cmp(a.uname, b.uname))
        for child in t.children:
            html += addTerm(child,t)
    return html

# generate HTML, uses a javascript tree control form yahoo.
html ="""\
<html>
 <head>
 <title>Term Hierarchy Tree</title>
 <!-- Required CSS --> 
  <link type="text/css" rel="stylesheet" href="http://yui.yahooapis.com/2.2.2/build/treeview/assets/tree.css"> 
 </head>
 <body>
 <!-- Dependency source files -->
  <script src = "http://yui.yahooapis.com/2.2.2/build/yahoo/yahoo-min.js" ></script>
  <script src = "http://yui.yahooapis.com/2.2.2/build/event/event-min.js" ></script>

  <!-- TreeView source file -->
  <script src = "http://yui.yahooapis.com/2.2.2/build/treeview/treeview-min.js" ></script>
  <table><tr><td width="60%">
  <h1>Term Hierarchy Tree</h1></td><td align="right">"""

if SemanticTerms == 'True':
    html += """<a href="TermHierarchyTree.py?SemanticTerms=False">Show the terms that don't have any semantic types.</a>"""
else:
    html += """<a href="TermHierarchyTree.py">Show the terms that have semantic types.</a>"""
    
html +="""</td></tr></table><div id="treeDiv"></div>
  <script type="text/javascript">

  var tree;
  function treeInit() {
   tree = new YAHOO.widget.TreeView("treeDiv");

   var root = tree.getRoot();  
""" + addTerms(terms,SemanticTerms) + """\

tree.draw();
}

YAHOO.util.Event.addListener(window, "load", treeInit);

 </script>
 </body>
</html>"""
cdrcgi.sendPage(html)

