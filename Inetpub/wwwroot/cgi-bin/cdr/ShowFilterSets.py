#----------------------------------------------------------------------
# Interface for viewing CDR filter sets.
#----------------------------------------------------------------------
import cdr, sys, xml.dom.minidom, cdrcgi
from lxml import etree
from cdrapi import db
from cdrapi.docs import Filter as APIFilter

XSL_INCLUDE = f"{{{APIFilter.NS}}}include"
XSL_IMPORT = f"{{{APIFilter.NS}}}import"

def showFilterSet(filterSet, setName):
    #sys.stderr.write("showFilterSet(%s)\n" % setName)
    html = """\
   <li class='set'>%s
    <ul>
""" % setName
    if filterSet:
        for member in filterSet.members:
            if type(member.id) == type(9):
                #sys.stderr.write("Found nested set %s\n" % member.name)
                html += showFilterSet(setDict.get(member.name), member.name)
            else:
                id = cdr.exNormalize(member.id)
                filter = filters.get(id[1])
                error = ''
                if filter and filter.error:
                    error = "<span class='error'>%s</span>" % filter.error
                html += """\
     <li class='filter'>%s (<a href='javascript:show(%d)'>%d</a>) %s
""" % (member.name, id[1], id[1], error)
                if filter:
                    html += showIncludedFilters(filter.includes)
                html += """\
     </li>
"""
    else:
        html += """\
     <li class='error'>*** CAN'T FIND FILTER SET DEFINITION ***</li>
"""
    html += """\
    </ul>
   </li>
"""
    return html

def showIncludedFilters(includedFilters):
    html = ""
    if includedFilters:
        html += """\
      <ul>
"""
        for includedFilter in includedFilters:
            filter = filtersByName.get(includedFilter.name[5:].upper().strip())
            if filter:
                html += """\
       <li class='include'>%s %s (<a href='javascript:show(%d)'>%d</a>)
""" % (includedFilter.elem, includedFilter.name, filter.id, filter.id)
                html += showIncludedFilters(filter.includes)
                html += """\
       </li>
"""
            else:
                html += """\
       <li class='error'>%s %s *** NO SUCH FILTER ***</li>
""" % (includedFilter.elem, includedFilter.name)
        html += """\
      </ul>
"""
    return html

filters = {}
filtersByName = {}
errors = []
class Filter:
    class Include:
        def __init__(self, elem, href):
            self.elem = elem
            self.href = href
            self.name = href
            if href.startswith('cdr:'):
                self.name = href[4:]
    def __init__(self, id, title, docXml):
        self.id = id
        self.title = title
        self.includes = []
        self.error = None
        try:
            for child in etree.fromstring(docXml.encode("utf-8")):
                if child.tag in (XSL_INCLUDE, XSL_IMPORT):
                    tag = child.tag.replace(f"{{{APIFilter.NS}}}", "xsl:")
                    href = child.get("href")
                    self.includes.append(self.Include(tag, href))
            '''
            dom = xml.dom.minidom.parseString(docXml)
            for child in dom.documentElement.childNodes:
                if child.nodeName in ('xsl:include', 'xsl:import'):
                    href = child.getAttribute('href')
                    self.includes.append(self.Include(child.nodeName, href))
            '''
        except Exception as e:
            self.error = "Failure parsing filter: %s" % str(e)
conn = db.connect(user='CdrGuest')
cursor = conn.cursor()
cursor.execute("""
    SELECT d.id, d.title, d.xml
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'filter'
  ORDER BY d.title""")
row = cursor.fetchone()
while row:
    #print "%s (%d)" % (row[1], row[0])
    #sys.stderr.write("%s (%d)\n" % (row[1], row[0]))
    nameKey = row[1].upper().strip()
    filter = Filter(row[0], row[1], row[2])
    filters[row[0]] = filtersByName[nameKey] = filter
    row = cursor.fetchone()
sets = cdr.getFilterSets('guest')
setDict = {}
for set in sets:
    filterSet = cdr.getFilterSet('guest', set.name)
    setDict[set.name] = filterSet
keys = sorted(setDict)

# Creating the HTML output page
# -----------------------------
report = u"""\
<html>
 <head>
  <title>CDR Filter Sets</title>
  <style type='text/css'>
   body       { font-family: Arial; }
   li.set     { color: purple; }
   li.filter  { color: blue; }
   li.include { color: green; }
   li.error   { color: red; }
   span.error { color: red; }
  </style>
  <script language='JavaScript'>
   //<![CDATA[
    function show(id) {
        var url  = "/cgi-bin/cdr/ShowRawXml.py?id=" + id;
        var name = "raw" + id
        var wind = window.open(url, name);
    }
   //]]>
  </script>
 </head>
 <body>
  <h1>CDR Filter Sets</h1>
  <ul>
"""

# Adding the individual filters with their members
# ------------------------------------------------
for key in keys:
    report += showFilterSet(setDict[key], key)

# Adding the HTML footer to the output
# ------------------------------------
report += u"""\
  </ul>
 </body>
</html>"""
#print """\
#Content-type: text/html
#
#""" + report
cdrcgi.sendPage(report)
