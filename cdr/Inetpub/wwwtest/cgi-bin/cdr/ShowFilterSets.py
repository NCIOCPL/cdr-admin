#----------------------------------------------------------------------
#
# $Id: ShowFilterSets.py,v 1.1 2004-07-13 18:08:27 bkline Exp $
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, sys, xml.dom.minidom

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
                html += """\
     <li class='filter'>%s (<a href='javascript:show(%d)'>%d</a>)
""" % (member.name, id[1], id[1])
                filter = filters.get(id[1])
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
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
        for child in dom.documentElement.childNodes:
            if child.nodeName in ('xsl:include', 'xsl:import'):
                href = child.getAttribute('href')
                self.includes.append(self.Include(child.nodeName, href))
conn = cdrdb.connect('CdrGuest')
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
    filters[row[0]] = filtersByName[nameKey] = Filter(row[0], row[1], row[2])
    row = cursor.fetchone()
sets = cdr.getFilterSets('guest')
setDict = {}
for set in sets:
    filterSet = cdr.getFilterSet('guest', set.name)
    setDict[set.name] = filterSet
keys = setDict.keys()
keys.sort()
report = """\
<html>
 <head>
  <title>CDR Filter Sets</title>
  <style type='text/css'>
   body       { font-family: Arial; }
   li.set     { color: purple; }
   li.filter  { color: blue; }
   li.include { color: green; }
   li.error   { color: red; }
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
for key in keys:
    report += showFilterSet(setDict[key], key)
report += """\
  </ul>
 </body>
</html>"""
print """\
Content-type: text/html

""" + report
