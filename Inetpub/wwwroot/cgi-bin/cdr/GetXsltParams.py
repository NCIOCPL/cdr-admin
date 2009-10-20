#----------------------------------------------------------------------
#
# $Id$
#
# Show all of the top-level parameters used by CDR filters.  Useful
# for XSL/T script writers who want to avoid conflicting uses of the
# same parameter names across more than one script, which might be 
# invoked as a set (the CdrFilter command expects all of the parameters
# supplied for the command to be applicable to all filters named by
# the command).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi, xml.sax

#----------------------------------------------------------------------
# Create a SAX content handler.
#----------------------------------------------------------------------
class FilterHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.level = 0
        self.params = {}
    def startElement(self, name, attributes):
        self.level += 1
        if name == "xsl:param" and self.level == 2:
            paramName = attributes.get("name")
            if not self.params.has_key(paramName):
                self.params[paramName] = []
            self.params[paramName].append((self.id, self.title))
    def endElement(self, name):
        self.level -= 1
handler = FilterHandler()

#----------------------------------------------------------------------
# Start the report HTML.
#----------------------------------------------------------------------
html = """\
<html>
 <head>
  <title>Global filter parameters</title>
 <head>
 <body>
  <h2>Global filter parameters</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
"""

#----------------------------------------------------------------------
# Find all of the filter documents.
#----------------------------------------------------------------------
conn = cdrdb.connect("CdrGuest")
cursor = conn.cursor()
cursor.execute("""\
    SELECT document.id, 
           document.title,
           document.xml
      FROM document
      JOIN doc_type
        ON doc_type.id = document.doc_type
     WHERE doc_type.name = 'Filter'
  ORDER BY document.title""")

#----------------------------------------------------------------------
# Parse the filters, looking for "top-level" param elements.
#----------------------------------------------------------------------
for row in cursor.fetchall():
    handler.id = row[0]
    handler.title = row[1]
    try:
        xml.sax.parseString(row[2].encode('utf-8'), handler)
    except:
        handler.level = 0

#----------------------------------------------------------------------
# Show the sorted parameters, each listing all filters using it.
#----------------------------------------------------------------------
keys = handler.params.keys()
keys.sort()
for key in keys:
    html += """\
   <tr>
    <th align='right'>%s</th>
    <td>CDR%010d</td>
    <td>%s</td>
   </tr>
""" % (key, handler.params[key][0][0], handler.params[key][0][1])
    for filter in handler.params[key][1:]:
        html += """\
   <tr>
    <td>&nbsp;</td>
    <td>CDR%010d</td>
    <td>%s</td>
""" % (filter[0], filter[1])

#----------------------------------------------------------------------
# Show the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
