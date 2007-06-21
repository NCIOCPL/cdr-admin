# see 3316 for details.
import cdrcgi, cdrdb, cgi

fields = cgi.FieldStorage()
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
SemanticTerms = fields and fields.getvalue("SemanticTerms") or "True"
cdrid = fields and fields.getvalue("CDRID") or None
title    = "CDR Administration"
section  = "Term Hierarchy Tree"
SUBMENU  = "Reports Menu"
buttons  = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, section,
                         "TermHierarchyTree.py", buttons, method = 'GET')
if cdrid:
    cdrid = int(cdrid)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

class CDRID:
    def __init__(self, id):
        self.id = id

class Term:
    def __init__(self, name, id, isSemantic):
        self.name = name
        self.id = id
        self.isSemantic = isSemantic
        #self.aliases = []
        self.children = []
        self.parents = []
        self.uname = name.upper()
        self.showMode = "hide"
        self.sign = "+"
        self.selectedTerm = "False"

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
        # add the semantic type parent rows
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

        #add the non-semantic type parent rows
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
                                            AND value <> 'Semantic type'
                                            AND value <> 'Obsolete term')
                                            """)
        
        if not cursor.rowcount:
            done = 1
        conn.commit()
        
        # all non-semantic rows that don't have parents will be assigned to a semantic term.
        cursor.execute("""\
            INSERT INTO #terms
                 SELECT p.doc_id, p.int_val, 0
                   FROM query_term p
                  WHERE NOT EXISTS (SELECT *
                                      FROM #terms
                                     WHERE id = p.doc_id
                                       AND parent = p.int_val)
                    AND p.doc_id IN (SELECT id from #terms
                                      WHERE parent is null and boolSemanticType = 0)
                    AND p.doc_id NOT IN (SELECT id from #terms
                                      WHERE parent is not null)
                    AND p.int_val IN (SELECT doc_id
                                           FROM query_term
                                          WHERE path = '/Term/TermType'
                                                     + '/TermTypeName'
                                            AND value = 'Semantic type')
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

def expandUp(t):
    for id in t.parents:
        term = terms[id]
        term.showMode = "show"
        term.sign = "-"
        if term.parents:
            expandUp(term)
    return

# add all terms that don't have parents
def addTerms(terms,SemanticTerms):
    html = [u""""""]
    
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
            if cdrid:
                if cdrid == id:
                    term.selectedTerm = "True"
                    # expand the tree upward
                    if term.parents:
                        expandUp(term)
                                
    parentTerm.children.sort(lambda a,b: cmp(a.uname, b.uname))
    
    for rootTerm in parentTerm.children:
        html.append(addTerm(rootTerm,rootTerm))

    html = u"".join(html)        
    return html

def addLeafIDsToList(t,cdrids):
    for child in t.children:
        if not child.children:
            if child.id not in cdrids:
                cdrids[child.id] = CDRID(child.id)
        else:
            addLeafIDsToList(child,cdrids)
    return

# add a term to the hierarchy list
def addTerm(t,parent):
    html = [u""""""]
    cbText=""

    if t.children:
        cdrids = {}
        addLeafIDsToList(t,cdrids)
        cbText = u" ".join([`id` for id in cdrids])
        #for id in cdrids:
        #    cbText += "%d " % id
        html.append(u""" <li class="parent %s" onclick="Toggle(event,this);"><span>%s</span>&nbsp;%s""" % (t.showMode,t.sign,cdrcgi.unicodeToLatin1(t.name)))
        if len(cbText) > 0:
            html.append(u"""<a STYLE="font-size: 8pt; color: rgb(200, 100, 100)" onclick="Send2Clipboard('%s');" href=#">&nbsp(copy)</a>""" % cbText)
        html.append(u"""<ul>""")
        
        t.children.sort(lambda a,b: cmp(a.uname, b.uname))
        for child in t.children:
            html.append(addTerm(child,t))
        html.append(u"""</ul></li>""")
    else:
        html.append(u""" <li class="leaf""")
        if t.selectedTerm == "True":
            html.append(u""" selected""")
        html.append(u"""">&nbsp;&nbsp;%s</li>""" % cdrcgi.unicodeToLatin1(t.name))

    html = u"".join(html)
    return html


# generate HTML
html =[u"""\
<html>
<input type='hidden' name='%s' value='%s'>""" % (cdrcgi.SESSION, session)]

html.append(u"""<head>
 <title>Term Hierarchy Tree</title>
 <style type="text/css">
     ul.treeview li {
        font-family: courier,serif;
        padding-left: 6px;
        list-style-type: none;
	}

	ul.treeview li.leaf {
		color: Teal;
		cursor: default;
		list-style-type: none;
	}

    ul.treeview li.leaf.selected {
		font-style: italic;
	}	

	ul.treeview li.parent{
		color: Navy;
		cursor: pointer;
	}
	ul.treeview li.show ul {
		display: block;
	}

	ul.treeview li.hide ul {
		display: none;
	}
  </style> 
  
  <script type="text/javascript">
    function onload()
    {
        // Don't show the clipboard edit box if using IE
        if( window.clipboardData )
        {
            var CDRIDTextField = document.getElementById("CopiedCDRIDs");
            CDRIDTextField.style.display="none";
        }
    }
  
    function Send2Clipboard(s) 
    {
        if( window.clipboardData ) 
        { 
            clipboardData.setData("text", s);
            alert("Data has been copied to the clipboard."); 
        }
        else
        {
            var myTextField = document.getElementById("CopiedCDRIDsEditBox");
            myTextField.value = s;
            myTextField.select();
            alert("CDRID's have been copied to the edit box at the bottom of this page. You can type Ctrl+C now to copy to the clipboard.");
        } 
    } 
    
    function Toggle(e, item)
    {
        e = (e) ? e : ((window.event) ? window.event : "")
        if (e) 
        {
            var tg = (window.event) ? e.srcElement : e.target;

            if (tg == item) 
            {
                if (item.className == "parent hide")
                {
                    item.className = "parent show";
                    // loop through and find first span tag
                    // instead of search and replace on innerHTML
                    // because it's much faster
                    for (i=0; i<item.childNodes.length; i++)
                    {
                        if (item.childNodes[i].tagName.toUpperCase() == "SPAN")
                        {
                            item.childNodes[i].innerHTML = "-";
                            break;
                        }        
                    }
                }
                else
                {
                    item.className = "parent hide";
                    for (i=0; i<item.childNodes.length; i++)
                    {
                        if (item.childNodes[i].tagName.toUpperCase() == "SPAN")
                        {
                            item.childNodes[i].innerHTML = "+";
                            break;
                        }        
                    }
                }
            }
            else
                return;               
        }                                                           
    }
	</script>
 </head>
 <body>
  <table><tr><td width="60%">
  <h1>Term Hierarchy Tree</h1></td><td align="right">""")

if SemanticTerms == 'True':
    html.append(u"""<a STYLE="font-size: 10pt; color: rgb(50, 100, 150)" href="TermHierarchyTree.py?%s=%s&SemanticTerms=False">Click Here to show the terms that don't have any semantic types.</a>""" % (cdrcgi.SESSION, session))
else:
    html.append(u"""<a STYLE="font-size: 10pt; color: rgb(50, 100, 150)" href="TermHierarchyTree.py?%s=%s">Click here to show the terms that have semantic types.</a>""" % (cdrcgi.SESSION, session))
    
html.append(u"""</td></tr></table>

  <ul class="treeview">

""")

html.append(addTerms(terms,SemanticTerms))

html.append(u"""\
</ul>
<p id ="CopiedCDRIDs" STYLE="font-size: 10pt; color: rgb(200, 100, 100)">Here are the copied CDRID's. Highlight the list and type Ctrl+C to copy to the clipboard:<br>
<input type="text" id = "CopiedCDRIDsEditBox" name="CopiedCDRIDsEditBox" value="" STYLE="width: 100%;"/>
</p>
 </body>
</html>""")
html = u"".join(html)
header = header.replace("<BODY","""<BODY onload="onload();" """)
cdrcgi.sendPage(header + html)

