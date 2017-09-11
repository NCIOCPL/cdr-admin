#----------------------------------------------------------------------
# Fetch an English summary ready for translation
# BZIssue::4906
#----------------------------------------------------------------------
import cgi, cdrdb, lxml.etree as etree, sys, re

fields  = cgi.FieldStorage()
docId   = fields.getvalue('id')
version = fields.getvalue('ver')
fmt     = fields.getvalue('format')
cursor  = cdrdb.connect('CdrGuest').cursor()

def bail(message):
    print """\
Content-type: text/html

<p style='font-weight: bold; font-size: 12pt; color: red'>%s</p>
""" % repr(message)
    sys.exit(0)

if not docId:
    print """\
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
  <form method="POST" action="get-english-summary.py">
   <table>
    <tr>
     <th align="right">Document ID</th>
     <td><input name="id" id="docid" /></td>
    </tr>
    <tr>
     <th align="right">Version</th>
     <td><input name="ver" /></td>
    </tr>
    <tr>
     <th align="right">Output</th>
     <td><input name="format" type="radio" value="display" checked="checked" />
         Display
         <input name="format" type="radio" value="raw" /> Raw
         </td>
    </tr>
   </table>
   <br />
   <input type="submit">
  </form>
  <p style='border: 1px green solid; width: 80%; padding: 5px; color: green'>
     Document ID is required, and must be an integer.  Version is optional,
     and can be a positive or negative integer (negative number count back
     from the most recent version, so -1 means last version, -2 is the one
     before that, etc.).
     If the version is omitted, the current working copy of the document
     is retrieved.  You can also give <i>last</i> for the most recent
     version, or <i>pub</i> for the latest publishable version.  The
     default output is the display of the document in the browser;
     select the "raw" output option to get the XML document itself,
     which you can save to your local file system and pass on to
     Trados for translation.</p>
 </body>
</html>"""
    sys.exit(0)
if version:
    if version.lower() in ('last', 'cur', 'current'):
        cursor.execute("SELECT MAX(num) FROM doc_version WHERE id = ?", docId)
        rows = cursor.fetchall()
        if not rows:
            bail("No versions found for CDR%s" % docId)
        ver = rows[0][0]
    elif version.lower() in ('pub', 'lastpub'):
        cursor.execute("""\
SELECT MAX(num)
  FROM publishable_version
 WHERE id = ?""", docId)
        rows = cursor.fetchall()
        if not rows:
            bail("No publishable versions found for CDR%s" % docId)
        ver = rows[0][0]
    elif version.startswith("-"):
        try:
            n = int(version[1:])
        except:
            bail("Invalid version %s" % version)
        cursor.execute("""\
  SELECT TOP %d num
    FROM doc_version
   WHERE id = ?
ORDER BY num DESC""" % n, docId)
        rows = cursor.fetchall()
        if not rows:
            bail("No versions found for CDR%s" % docId)
        elif len(rows) < n:
            bail("Only %d versions found for CDR%s" % (len(rows), docId))
        ver = rows[-1][0]
    else:
        try:
            ver = int(version)
        except:
            bail("invalid version %s" % version)
    cursor.execute("""\
SELECT xml
  FROM doc_version
 WHERE id = ?
   AND num = ?""", (docId, ver))
    rows = cursor.fetchall()
    if not rows:
        bail("Version %d for CDR%s not found" % (ver, docId))
else:
    cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
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

def strip(xml):
    doomed = ('Comment', 'MediaLink', 'SectMetaData', 'ReplacementFor',
              'PdqKey', 'DateLastModified', 'ComprehensiveReviewDate',
              'BoardMember')
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml.encode('utf-8'), parser).getroottree()
        debug = []
        first = True
        for node in root.findall("SummaryMetaData/MainTopics"):
            if first:
                first = False
                debug.append("keeping first main topic")
            else:
                parent = node.getparent()
                parent.remove(node)
                debug.append("dropped subsequent main topics")
        for node in root.xpath("SummarySection["
                               "SectMetaData/SectionType="
                               "'Changes to summary']"):
            debug.append("removed summary section")
            parent = node.getparent()
            parent.remove(node)

        etree.strip_elements(root, with_tail=False, *doomed)
        etree.strip_attributes(root, 'PdqKey')
        return etree.tostring(root, pretty_print=True, encoding="utf-8",
                              xml_declaration=True)# + "<br />".join(debug)
    except Exception, e:
        bail("processing XML document: %s" % e)

docXml = strip(rows[0][0])
if fmt == "raw":
    name = "CDR%s" % docId
    if version:
        name += "V%d" % ver
    name += ".xml"
    print """\
ContentType: text/xml;charset=utf-8
Content-disposition: attachment; filename=%s

%s""" % (name, docXml)
    sys.exit(0)
try:
    title = "CDR Document %s" % docId
    if version:
        title += " (version %d)" % ver
    print """\
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
</html>""" % (title, title, markup(docXml))
except Exception, e:
    bail(e)
