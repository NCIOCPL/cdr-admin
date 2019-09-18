"""
   Report to display all summaries including a list of special elements.
   The elements currently included are:
     - Comment
     - EmbeddedVideo
     - MediaLink
     - MiscellaneousDocLink
     - StandardWording
     - SummaryModuleLink
     - Table
   This report can help answering questions like: Give me a summary
   including a video? or "I need a summary with multiple tables"
"""
import cdrcgi
from lxml import etree
from cdrapi import db

# --------------------------------------------------------------------
# Create HTML list item by summary to be included in report
# --------------------------------------------------------------------
def addRow(summary):
    #print summary.elemInfo
    html = """\
   <li class='summary'>%s (%s)
    <ul>
""" % (summary.title, summary.id)
    for element in summary.elemInfo.keys():
        if (element == 'SummaryModuleLink' and
            len(summary.elements[element]) > 0):
            for module in summary.elements[element]:
                html += """\
     <li class='%s'>%s (%s)</li>
""" % (summary.elemInfo[element], module, element)
        else:
            if len(summary.elements[element]) > 0:
                html += """\
     <li class='%s'>%s %s(s)</li>
""" % (summary.elemInfo[element], len(summary.elements[element]), element)

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
        self.error = None
        self.elemInfo = {'Table':'table',
                         'SummaryModuleLink':'module-link',
                         'MiscellaneousDocLink':'misc-doc-link',
                         'MediaLink':'media-link',
                         'EmbeddedVideo':'embedded-video',
                         'StandardWording':'standard-wording',
                         'Comment':'comment'}
        self.elements = {}

        # Create empty list for each element
        elements = list(self.elemInfo.keys())
        for elem in elements:
            self.elements[elem] = []

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
                    elif element in ('StandardWording', 'Comment'):
                        self.elements[element].append(1)
                    else:
                        id = child.attrib['{cips.nci.nih.gov/cdr}id']
                        self.elements[element].append(id)

        except Exception as e:
            # print '*** Error ***'
            self.error = "Failure parsing filter: %s" % str(e)

# -------------------------------------------------------------------
# Select the summaries to be included in the report (exlude blocked
# documents)
# -------------------------------------------------------------------
conn = db.connect(user='CdrGuest')
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
   .standard-wording { color: lime; }
   .comment        { color: fuchsia; }
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
     <span class="comment">Comment</span>,
     <span class="embedded-video">EmbeddedVideo</span>,
     <span class="media-link">MediaLink</span>,
     <span class="misc-doc-link">MiscellaneousDocLink</span>,
     <span class="standard-wording">StandardWording</span>,
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
