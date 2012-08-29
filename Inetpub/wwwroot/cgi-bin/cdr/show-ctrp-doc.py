#----------------------------------------------------------------------
#
# $Id$
#
# Display trials in the ctrp_import table.
#
# BZIssue::4942
#
#----------------------------------------------------------------------
import cgi, cdrdb, lxml.etree as etree, sys, re

fields  = cgi.FieldStorage()
docId   = fields.getvalue('id')
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
  <title>CTRP Documents</title>
 </head>
 <body style='font-family: Arial, sans-serif'>
  <h1 style='color: maroon'>CTRP Documents</h1>
  <table border="1" cellpadding="2" cellspacing="0">
   <tr>
    <th>CTRP ID</th>
    <th>Disposition</th>
    <th>CDR ID</th>
    <th>NCT ID</th>
   </tr>"""
    cursor.execute("""\
  SELECT i.ctrp_id, d.disp_name, i.cdr_id, i.nct_id
    FROM ctrp_import i
    JOIN ctrp_import_disposition d
      ON d.disp_id = i.disposition
ORDER BY i.ctrp_id""")
    for ctrpId, disp, cdrId, nctId in cursor.fetchall():
        print """\
   <tr>
    <td><a href="show-ctrp-doc.py?id=%s">%s</a></td>
    <td>%s</td>
    <td><a href="show-cdr-doc.py?id=%s">%s</a></td>
    <td><a href="http://clinicaltrials.gov/ct2/show/%s">%s</a></td>
   </tr>""" % (ctrpId, ctrpId, disp, cdrId, cdrId, nctId, nctId)
    print """\
  </table>
 </body>
</html>"""
    sys.exit(0)

cursor.execute("SELECT doc_xml FROM ctrp_import WHERE ctrp_id = ?", docId)
rows = cursor.fetchall()
if not rows:
    bail("%s not found" % docId)

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
    doc = markup(etree.tostring(tree, pretty_print=True, encoding='utf-8',
                                xml_declaration=True))
    title = "CTRP Document %s" % docId
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
</html>""" % (title, title, doc)
except Exception, e:
    bail(e)
