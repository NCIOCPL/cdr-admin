import cgi, cdrdb, lxml.etree as etree, sys, re

fields   = cgi.FieldStorage()
docId    = fields.getvalue('id')
docType  = fields.getvalue('dt')
docTitle = fields.getvalue('ti')
cursor   = cdrdb.connect('CdrGuest').cursor()
titles   = ""

def bail(message):
    print("""\
Content-type: text/html

<p style='font-weight: bold; font-size: 12pt; color: red'>%s</p>
""" % repr(message))
    sys.exit(0)

def makeDoctypeList():
    # takes too long to run the query to find doc types sent to CG
    return '''\
<select name="dt">
 <option value="">Optionally select one</option>
 <option value="34">CTGovProtocol</option>
 <option value="38">DrugInformationSummary</option>
 <option value="44">GlossaryTermName</option>
 <option value="18">InScopeProtocol</option>
 <option value="36">Media</option>
 <option value="22">Organization</option>
 <option value="2">Person</option>
 <option value="31">PoliticalSubUnit</option>
 <option value="19">Summary</option>
 <option value="11">Term</option>
</select>'''

    cursor.execute("""\
SELECT DISTINCT t.id, t.name
           FROM doc_type t
           JOIN document d
             ON d.doc_type = t.id
           JOIN pub_proc_cg c
             ON c.id = d.id
       ORDER BY t.name""")
    html = ['<select name="dt">']
    html.append('<option value="">Optionally select one</option>')
    for row in cursor.fetchall():
        value = row[0]
        name = cgi.escape(row[1])
        html.append('<option value="%d">%s</option>' % (value, name))
    html.append('</select>')
    return "".join(html)

if docTitle and not docId:
    extra = docType and (" AND doc_type = %s" % docType) or ""
    cursor.execute("""\
  SELECT id, title
    FROM document
   WHERE title LIKE ?
    %s
ORDER BY title""" % extra, docTitle)
    rows = cursor.fetchall()
    if len(rows) == 1:
        docId = rows[0][0]
    elif rows:
        html = [u"<ul>"]
        for row in rows:
            url = "show-cg-doc.py?id=%d" % row[0]
            title = cgi.escape(row[1])
            html.append('<li><a href="%s">%s</a></li>' % (url, title))
        html.append(u"</ul>")
        titles = u"\n".join(html).encode("utf-8")
    elif docTitle:
        cursor.execute("SELECT name FROM doc_type WHERE id = ?", docType)
        typeName = cursor.fetchall()[0][0]
        titles = (u'<p style="color: red">No %s documents match %s</p>' %
                  (typeName, cgi.escape(docTitle))).encode("utf-8")
    else:
        titles = (u'<p style="color: red">No documents match %s</p>' %
                  cgi.escape(docTitle)).encode("utf-8")
        
if not docId:
    print("""\
Content-type: text/html

<html>
 <head>
  <title>CDR Document Display</title>
  <script type="text/javascript">
   function setfocus() {
       document.getElementById("docid").focus();
   }
  </script>
 </head>
 <body style='font-family: Arial, sans-serif' onload="javascript:setfocus()">
  <h1 style='color: maroon'>CDR Document Display</h1>
  %s
  <form method="GET" action="show-cg-doc.py">
   <table>
    <tr>
     <th align="right">Document ID</th>
     <td><input name="id" id="docid" /></td>
    </tr>
    <tr>
     <th align="right">Document Title</th>
     <td><input name="ti" /></td>
    </tr>
    <tr>
     <th align="right">Document Type</th>
     <td>%s</td>
    </tr>
   </table>
   <br />
   <input type="submit">
  </form>
  <p style='border: 1px green solid; width: 80%%; padding: 5px; color: green'>
   You may specify a document ID directly (as an integer) or a document
   title pattern (using %% as a wildcard for unknown portions of the title).
   If you specify a title you may also optionally select a docuemnt type.
  </p>
 </body>
</html>""" % (titles, makeDoctypeList()))
    sys.exit(0)
cursor.execute("SELECT xml FROM pub_proc_cg WHERE id = ?", docId)
rows = cursor.fetchall()
if not rows:
    bail("CDR%d not found" % docId)

def markupTag(match):
    s = match.group(1)
    if s.startswith('/'):
        return "</@@TAG-START@@%s@@END-SPAN@@>" % s[1:]
    trailingSlash = ''
    if s.endswith('/'):
        s = s[:-1]
        trailingSlash = '/'
    pieces = re.split("\\s", s, 1)
    if len(pieces) == 1:
        return "<@@TAG-START@@%s@@END-SPAN@@%s>" % (s, trailingSlash)
    tag, attrs = pieces
    pieces = ["<@@TAG-START@@%s@@END-SPAN@@" % tag]
    for attr, delim in re.findall("(\\S+=(['\"]).*?\\2)", attrs):
        name, value = attr.split('=', 1)
        pieces.append(" @@NAME-START@@%s=@@END-SPAN@@"
                      "@@VALUE-START@@%s@@END-SPAN@@" % (name, value))
    pieces.append(trailingSlash)
    pieces.append('>')
    return "".join(pieces)

def markup(doc):
    doc = re.sub("<([^>]+)>", markupTag, doc)
    doc = cgi.escape(doc)
    doc = doc.replace('@@TAG-START@@', '<span class="tag">')
    doc = doc.replace('@@NAME-START@@', '<span class="name">')
    doc = doc.replace('@@VALUE-START@@', '<span class="value">')
    doc = doc.replace('@@END-SPAN@@', '</span>')
    return doc

docXml = rows[0][0]
try:
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.fromstring(docXml.encode('utf-8'), parser)
    doc = markup(etree.tostring(tree, pretty_print=True))
    #title = "CDR%010d" % int(docId)
    title = "CDR Vendor Document %s" % docId
    print("""\
Content-type: text/html;charset=utf-8

<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
.tag { color: blue; font-weight: bold }
.name { color: brown }
.value { color: red }
h1 { color: maroon; font-size: 14pt; font-family: Verdana, Arial, sans-serif; }
  </style>
 </head>
 <body>
  <h1>%s</h1>
  <pre>%s</pre>
 </body>
</html>""" % (title, title, doc))
except Exception as e:
    bail(e)
