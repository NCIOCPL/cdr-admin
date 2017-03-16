#----------------------------------------------------------------------
# Hierarchical report (in thesaurus-like format) of index terms
# whose semantic types are some form of Intervention/procedure.
# BZIssue::3693 - user-requested modifications
#----------------------------------------------------------------------
import cdrcgi, cdrdb, cgi

fields = cgi.FieldStorage()
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
IncludeAlternateNames = fields and fields.getvalue("IncludeAlternateNames") or "True"

#debug code
#IncludeAlternateNames = "False"

class Term:
    def __init__(self, name, id, top):
        self.name = name
        self.parents = {}
        self.children = {}
        self.uname = name.upper()
        self.aliases = {}
        self.id = id
        self.top = top

patriarch = None
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
try:
    # get the root element
    cursor.execute("""\
        SELECT DISTINCT doc_id, 0 parent_id
                   INTO #intervention_semantic_types
                   FROM query_term
                  WHERE path = '/Term/PreferredName'
                    AND value IN ('Intervention/procedure',
                                  'Intervention or procedure')""")
    conn.commit()
    done = 0
    while not done:
        #get the top level items off the root (The green items)
        cursor.execute("""\
            INSERT INTO #intervention_semantic_types(doc_id, parent_id)
                 SELECT q.doc_id, q.int_val
                   FROM query_term q
                   JOIN #intervention_semantic_types ist
                     ON ist.doc_id = q.int_val
                   JOIN document d
                     ON d.id = q.doc_id
                  WHERE q.doc_id NOT IN (SELECT doc_id
                                           FROM #intervention_semantic_types)
                    AND d.active_status = 'A'
                    AND q.path = '/Term/TermRelationship/ParentTerm'
                               + '/TermId/@cdr:ref'""")
        if not cursor.rowcount:
            done = 1
        conn.commit()
    # get the preferred names for the root node and all top level nodes off the root
    cursor.execute("""\
        SELECT ist.doc_id, ist.parent_id, pname.value
          FROM #intervention_semantic_types ist
          JOIN query_term pname
            ON pname.doc_id = ist.doc_id
         WHERE pname.path = '/Term/PreferredName'
      ORDER BY ist.parent_id asc""")
    #semanticTypes = {}
    terms = {}
    for row in cursor.fetchall():
        id, parent, name = row
        top = 0
        if not parent:
            patriarch = id
        elif parent == patriarch:
            top = 1
        terms[id] = Term(name,id,top)
        if parent:
            terms[id].parents[parent] = 1
    for key in terms.keys():
        term = terms[key]
        if term.parents:
            for parentKey in term.parents.keys():
                terms[parentKey].children[key] = 1

    # Get all the terms including the top level terms off the root.
    # Not including the roo term
    cursor.execute("""\
        SELECT ist.doc_id SemanticTypeId, 
               it.doc_id IndexTermId, 
               pname.value IndexTermName
          INTO #index_terms
          FROM #intervention_semantic_types ist
          JOIN query_term it
            ON it.int_val = ist.doc_id
          JOIN query_term pname
            ON pname.doc_id = it.doc_id
          JOIN document d
            ON d.id = it.doc_id
         WHERE it.path = '/Term/SemanticType/@cdr:ref'
           AND d.active_status = 'A'
           AND pname.path = '/Term/PreferredName'""")
    conn.commit()

    cursor.execute("""SELECT * FROM #index_terms""")
    #indexTerms = {}
    for row in cursor.fetchall():
        typeId, termId, name = row
        if not terms.has_key(termId):
            terms[termId] = Term(name,termId, 0)

    # Get all the parent/child relationships
    cursor.execute("""\
        SELECT DISTINCT it.IndexTermId,
                        pid.int_val
                   FROM #index_terms it
                   JOIN query_term pid
                     ON pid.doc_id = it.IndexTermId
                   JOIN document d
                     ON d.id = pid.int_val
                  WHERE pid.path = '/Term/TermRelationship/ParentTerm'
                                 + '/TermId/@cdr:ref'
                    AND d.active_status = 'A'""")
    for row in cursor.fetchall():
        termId, parentId = row
        if terms.has_key(parentId):
            terms[parentId].children[termId] = 1
            terms[termId].parents[parentId] = 1
 
    #get the other term names
    cursor.execute("""\
        SELECT qt.doc_id, qt.value
          FROM query_term qt
          JOIN #index_terms it
            ON it.IndexTermId = qt.doc_id
         WHERE qt.path = '/Term/OtherName/OtherTermName'""")
    for row in cursor.fetchall():
        id, name = row
        terms[id].aliases[name] = 1
        
except:
    raise
    cdrcgi.bail("Database failure reading terminology information")

def sorter(a, b):
    return cmp(terms[a].uname, terms[b].uname)

def addTerm(t):
    classname = 't'
    if t.top:
        classname = 'st'
    html = """\
    <li class = '%s'>%s</li>
""" % (classname, cgi.escape(t.name))

    if t.children or (t.aliases and IncludeAlternateNames == "True"):
        html += "<ul>\n"
        if t.aliases and IncludeAlternateNames == "True":
            keys = t.aliases.keys()
            keys.sort()
            for key in keys:
                html += "<li class = 'a'>x %s</li>\n" % cgi.escape(key)
        if t.children:
            keys = t.children.keys()
            keys.sort(sorter)
            for key in keys:
                html += addTerm(terms[key])
        html += "</ul>\n"

    return html

altTitleExtension = ""
if IncludeAlternateNames == "False":
    altNameDisplay = "none"
    altTitleExtension = "(without Alternate Names)"
    
html = """\
<html>
 <head>
  <title>CDR Intervention and Procedure Index Terms</title>
  <style type = 'text/css'>
   h1 { color: navy; font-size: 14: font-weight: bold; 
        font-family: Arial, Helvetica, sans-serif; }
   li.st { color: green; font-size: 14; font-weight: bold; list-style: none;
          font-family: serif; font-variant: small-caps; }
   li.t { color: blue; font-size: 14; list-style: none; font-weight: normal;
          font-family: Arial, Helvetica, sans-serif; font-variant: normal }
   li.a { color: #FF2222; font-size: 12;  list-style: none;
          font-weight: normal; font-variant: normal;
          font-family: Arial, Helvetica, sans-serif; font-style: italic}
  </style>
 </head>
 <body>
  <h1>CDR Intervention or Procedure Index Terms %s</h1>
  <ul>
""" % altTitleExtension + addTerm(terms[patriarch]) + """\
  </ul>
 </body>
</html>"""
cdrcgi.sendPage(html)
