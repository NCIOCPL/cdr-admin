"""
   Report to display all summaries including a list of special elements.
   The elements currently included are:
     - Table
     - SummaryModuleLink
     - MediaLink
     - EmbeddedVideo
   This report can help answering questions like: Give me a summary
   including a video? or "I need a summary with multiple tables"
"""
import cdr, cdrdb, sys, xml.dom.minidom, cdrcgi
import lxml.etree as etree


# --------------------------------------------------------------------
# Create HTML list item by summary to be included in report
# --------------------------------------------------------------------
def addRow(summary):
    #print summary.id
    #print summary.modules
    #print summary.miscdocs
    html = """\
   <li class='summary'>%s (%s)
    <ul>
""" % (summary.title, summary.id)
    for element in summary.elements.keys():
        if element == 'SummaryModuleLink' and len(summary.elements[element]) > 0:
            for module in summary.elements[element]:
                html += """\
     <li class='%s'>%s (%s)</li>
""" % (element.lower(), module, element)
        else:
            if len(summary.elements[element]) > 0:
                html += """\
     <li class='%s'>%s %s(s)</li>
""" % (element.lower(), len(summary.elements[element]), element)

    html += """\
    </ul>
   </li>
"""
    return html


sumIncludes = {}
filtersByName = {}
errors = []
class SummaryInclude:
    def __init__(self, id, title, docXml):
        self.id = id
        self.title = title
        self.elements = {}
        self.error = None
        elements = ['Table', 
                    'SummaryModuleLink',
                    'MiscellaneousDocLink',
                    'MediaLink',
                    'EmbeddedVideo']

        # Create empty list for each element
        for i in elements:
            self.elements[i] = []

        try:
            dom = etree.fromstring(docXml.encode('utf-8'))
            for element in elements:
                # Creates a list of element objects
                nodes = dom.findall('.//%s' % element)

                # Inspect the list elements/objects
                for child in nodes:
                    if element in ('SummaryModuleLink', 'MiscellaneousDocLink'):
                        ref = child.attrib['{cips.nci.nih.gov/cdr}ref']
                        self.elements[element].append(ref)
                    else:
                        id = child.attrib['{cips.nci.nih.gov/cdr}id']
                        self.elements[element].append(id)

        except Exception, e:
            print '*** Error ***'
            self.error = "Failure parsing filter: %s" % str(e)

# -------------------------------------------------------------------
# Select the summaries to be included in the report (exlude blocked
# documents)
# -------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""
    SELECT d.id, d.title, d.xml
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'summary'
       AND d.title not like '%BLOCKED%'
  ORDER BY d.title""")
row = cursor.fetchone()
sumIncludes = []
while row:
    #print "%s (%d)" % (row[1], row[0])
    #sys.stderr.write("%s (%d)\n" % (row[1], row[0]))
    nameKey = row[1].upper().strip()
    sumInclude = SummaryInclude(row[0], row[1], row[2])

    sumIncludes.append(sumInclude)
    row = cursor.fetchone()


# Creating the HTML output page
# -----------------------------
report = u"""\
<html>
 <head>
  <title>Summaries including Modules, MiscDocs</title>
  <style type='text/css'>
   body       { font-family: Arial; }
   .summary        { color: blue; }
   .module-link    { color: red; }
   .misc-doc-link  { color: brown; }
   .media-link     { color: green; }
   .table          { color: purple; }
   .embedded-video { color: deeppink; }
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
  <h1>Elements Included in PDQ Summaries</h1>
  <p>Elements included: 
     <span class="embedded-video">EmbeddedVideo</span>, 
     <span class="media-link">MediaLink</span>, 
     <span class="misc-doc-link">MiscellaneousDocLink</span>,
     <span class="module-link">SummaryModuleLink</span>, 
     <span class="table">Table</span></p>
  <ul>
"""

# Concatenating each list item/summary output
# ------------------------------------------------
for summary in sumIncludes:
    report += addRow(summary)

# Adding the HTML footer to the output
# ------------------------------------
report += u"""\
  </ul>
 </body>
</html>"""

cdrcgi.sendPage(report)
