#----------------------------------------------------------------------
#
# $Id: InterventionAndProcedureTerms.py,v 1.1 2002-12-11 13:02:25 bkline Exp $
#
# Hierarchical report (in thesaurus-like format) of index terms
# whose semantic types are some form of Intervention/procedure.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrcgi, cdrdb, cgi

class SemanticType:
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.children = {}
        self.terms = {}
        self.uname = name.upper()

class IndexTerm:
    def __init__(self, name):
        self.name = name
        self.aliases = {}
        self.children = {}
        self.parents = {}
        self.uname = name.upper()

patriarch = None
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
try:
    cursor.execute("""\
        SELECT DISTINCT doc_id, 0 parent_id
                   INTO #intervention_semantic_types
                   FROM query_term
                  WHERE path = '/Term/PreferredName'
                    AND value = 'Intervention/procedure'""")
    conn.commit()
    done = 0
    while not done:
        cursor.execute("""\
            INSERT INTO #intervention_semantic_types(doc_id, parent_id)
                 SELECT q.doc_id, q.int_val
                   FROM query_term q
                   JOIN #intervention_semantic_types ist
                     ON ist.doc_id = q.int_val
                  WHERE q.doc_id NOT IN (SELECT doc_id
                                           FROM #intervention_semantic_types)
                    AND q.path = '/Term/TermRelationship/ParentTerm'
                               + '/TermId/@cdr:ref'""")
        if not cursor.rowcount:
            done = 1
        conn.commit()
    cursor.execute("""\
        SELECT ist.doc_id, ist.parent_id, pname.value
          FROM #intervention_semantic_types ist
          JOIN query_term pname
            ON pname.doc_id = ist.doc_id
         WHERE pname.path = '/Term/PreferredName'""")
    semanticTypes = {}
    for row in cursor.fetchall():
        id, parent, name = row
        semanticTypes[id] = SemanticType(name, parent)
        if not parent:
            patriarch = id
    for key in semanticTypes.keys():
        semanticType = semanticTypes[key]
        if semanticType.parent:
            semanticTypes[semanticType.parent].children[key] = 1

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
         WHERE it.path = '/Term/SemanticType/@cdr:ref'
           AND pname.path = '/Term/PreferredName'""")
    conn.commit()

    cursor.execute("""SELECT * FROM #index_terms""")
    indexTerms = {}
    for row in cursor.fetchall():
        typeId, termId, name = row
        if not indexTerms.has_key(termId):
            indexTerms[termId] = IndexTerm(name)
        semanticTypes[typeId].terms[termId] = 1

    cursor.execute("""\
        SELECT DISTINCT it.IndexTermId,
                        pid.int_val
                   FROM #index_terms it
                   JOIN query_term pid
                     ON pid.doc_id = it.IndexTermId
                  WHERE pid.path = '/Term/TermRelationship/ParentTerm'
                                 + '/TermId/@cdr:ref'""")
    for row in cursor.fetchall():
        termId, parentId = row
        if indexTerms.has_key(parentId):
            indexTerms[parentId].children[termId] = 1
            indexTerms[termId].parents[parentId] = 1

    cursor.execute("""\
        SELECT qt.doc_id, qt.value
          FROM query_term qt
          JOIN #index_terms it
            ON it.IndexTermId = qt.doc_id
         WHERE qt.path = '/Term/OtherName/OtherTermName'""")
    for row in cursor.fetchall():
        id, name = row
        indexTerms[id].aliases[name] = 1
except:
    raise
    cdrcgi.bail("Database failure reading terminology information")

def semanticTypeSorter(a, b):
    return cmp(semanticTypes[a].uname, semanticTypes[b].uname)

def termSorter(a, b):
    return cmp(indexTerms[a].uname, indexTerms[b].uname)

def addSemanticType(st):
    html = """\
    <li class = 'st'>%s</li>
""" % cgi.escape(st.name)
    if st.children or st.terms:
        html += "<ul>\n"
        keys = st.children.keys()
        keys.sort(semanticTypeSorter)
        for key in keys:
            html += addSemanticType(semanticTypes[key])
        keys = st.terms.keys()
        keys.sort(termSorter)
        for key in keys:
            t = indexTerms[key]
            topLevel = 1
            for pKey in t.parents.keys():
                if st.terms.has_key(pKey):
                    topLevel = 0
                    break
            if topLevel:
                html += addTerm(indexTerms[key], st)
        html += "</ul>\n"
    return html

def addTerm(t, st):
    html = """\
    <li class = 't'>%s</li>
""" % cgi.escape(t.name)
    if t.aliases or t.children:
        html += "<ul>\n"
        keys = t.aliases.keys()
        keys.sort()
        for key in keys:
            html += "<li class = 'a'>x %s</li>\n" % cgi.escape(key)
        keys = t.children.keys()
        keys.sort(termSorter)
        for key in keys:
            if st.terms.has_key(key):
                html += addTerm(indexTerms[key], st)
        html += "</ul>\n"
    return html

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
          font-variant: normal;
          font-family: Arial, Helvetica, sans-serif; font-style: italic }
  </style>
 </head>
 <body>
  <h1>CDR Intervention/Procedure Index Terms</h1>
  <ul>
""" + addSemanticType(semanticTypes[patriarch]) + """\
  </ul>
 </body>
</html>"""
cdrcgi.sendPage(html)
