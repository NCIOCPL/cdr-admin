#----------------------------------------------------------------------
# Hierarchical report (in thesaurus-like format) of terminology
# under Disease/Diagnosis.
#
# BZIssue::4762 (change 'cancer' to 'Malignant Neoplasm' [per WO])
#----------------------------------------------------------------------

from operator import attrgetter
from cdrapi import db
import cdrcgi, cgi
from html import escape as html_escape

class Term:
    def __init__(self, name):
        self.name = name
        self.aliases = []
        self.children = []
        self.parents = []
        self.uname = name.upper()

patriarch = None
conn = db.connect(user='CdrGuest')
cursor = conn.cursor()
fields = cgi.FieldStorage()
flavor = fields and fields.getvalue("flavor") or None
try:
    cursor.execute("CREATE TABLE #terms(id INTEGER, parent INTEGER)")
    conn.commit()
    cursor.execute("""\
        INSERT INTO #terms
             SELECT doc_id, NULL
               FROM query_term
              WHERE path = '/Term/PreferredName'
                AND value = 'Malignant Neoplasm'""")
    conn.commit()
    done = 0
    while not done:
        cursor.execute("""\
            INSERT INTO #terms
                 SELECT p.doc_id, p.int_val
                   FROM query_term p
                   JOIN #terms t
                     ON t.id = p.int_val
                  WHERE p.path = '/Term/TermRelationship/ParentTerm'
                               + '/TermId/@cdr:ref'
                    AND NOT EXISTS (SELECT *
                                      FROM #terms
                                     WHERE id = p.doc_id
                                       AND parent = p.int_val)
                    AND p.doc_id NOT IN (SELECT doc_id
                                           FROM query_term
                                          WHERE path = '/Term/TermType'
                                                     + '/TermTypeName'
                                            AND value = 'Obsolete term')""")
        if not cursor.rowcount:
            done = 1
        conn.commit()
    cursor.execute("""\
        SELECT d.id, n.value, d.parent
          FROM #terms d
          JOIN query_term n
            ON n.doc_id = d.id
         WHERE n.path = '/Term/PreferredName'""")
    terms = {}
    for id, name, parent in cursor.fetchall():
        if terms.has_key(id):
            term = terms[id]
        else:
            term = terms[id] = Term(name)
        if not parent:
            patriarch = id
        elif parent not in term.parents:
            term.parents.append(parent)
    if flavor != 'short':
        cursor.execute("""\
            SELECT DISTINCT q.doc_id, q.value
                       FROM query_term q
                       JOIN #terms t
                         ON t.id = q.doc_id
                      WHERE q.path = '/Term/OtherName/OtherTermName'""")
        for id, name in cursor.fetchall():
            if name not in terms[id].aliases:
                terms[id].aliases.append(name)
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

def addTerm(t):
    if not t.parents or patriarch in t.parents:
        cls = 'st'
    else:
        cls = 't'
    html = [f'<li class="{cls}">{html_escape(t.name)}</li>']
    if t.aliases or t.children:
        html.append("<ul>")
        t.aliases.sort()
        for alias in t.aliases:
            html.append(f'<li class="a">x {html_escape(alias)}</li>\n')
        for child in sorted(t.children, key=attrgetter("name")):
            html.append(addTerm(child))
        html.append("</ul>")
    return "\n".join(html)

html = f"""\
<html>
 <head>
  <title>CDR Cancer Diagnosis Hierarchy Report</title>
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
  <h1>CDR Cancer Diagnosis Hierarchy Report</h1>
  <ul>
{addTerm(terms[patriarch])}
  </ul>
 </body>
</html>"""
cdrcgi.sendPage(html)
