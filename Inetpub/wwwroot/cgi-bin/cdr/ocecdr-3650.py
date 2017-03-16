#----------------------------------------------------------------------
# Reports on internal links within a summary to support keeping standard
# treatment options in sync during the HP reformat process.  Implemented
# in a more general way in order to support other uses.
#
# JIRA::OCECDR-3650
#----------------------------------------------------------------------
import cgi
import datetime
import os
import re
import sys
import lxml.etree as etree
import msvcrt
import cdrcgi
import cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
docId     = fields.getvalue(cdrcgi.DOCID)
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "Internal Summary Links"
instr     = "Report on Links From One Section of a Summary to Another Section"
script    = "ocecdr-3650.py"
SUBMENU   = "Report Menu"
buttons   = (SUBMENU, cdrcgi.MAINMENU)
linkPattern = re.compile("CDR(\\d+)(?:#(.+))?")
fragNumPattern = re.compile("_(\\d+)")

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Put up the form if we don't have a document ID.
#----------------------------------------------------------------------
if not docId:
    header = cdrcgi.header(title, title, instr, script,
                           ("Submit", SUBMENU, cdrcgi.MAINMENU))
    form = u"""\
   <style>* { font-family: Arial; }</style>
   <input type='hidden' name='%s' value='%s'>
   <fieldset>
    <legend>&nbsp;Pick A Document&nbsp;</legend>
    <b>CDR Doc ID:&nbsp;</b>
    <input name="%s">
   </fieldset>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, cdrcgi.DOCID)
    cdrcgi.sendPage(header + form)

class Link:
    def __init__(self, node, elements):
        self.text = self.path = self.element = self.docId = self.fragId = None
        self.fragNum = self.section = None
        self.href = node.get("{cips.nci.nih.gov/cdr}href")
        if self.href:
            match = linkPattern.match(self.href.strip())
            if match:
                self.docId = int(match.group(1))
                self.fragId = match.group(2)
                self.element = elements[-1]
                self.path = "/" + "/".join(elements)
                self.text = node.text
                if self.fragId:
                    match = fragNumPattern.match(self.fragId)
                    if match:
                        self.fragNum = int(match.group(1))
                p = node.getparent()
                while p is not None:
                    if p.tag == "SummarySection":
                        self.section = SummarySection(p)
                        break
                    p = p.getparent()
    def __cmp__(self, other):
        if self.fragNum is not None:
            if other.fragNum is not None:
                return cmp(self.fragNum, other.fragNum)
            return -1
        return cmp(self.fragId, other.fragId)

class SummarySection:
    def __init__(self, node):
        self.title = self.parent = None
        for child in node:
            if child.tag == "Title":
                self.title = u"".join([t for t in child.itertext()])
                break
        return
        parent = node.getparent()
        while parent is not None:
            if parent.tag == "SummarySection":
                self.parent = SummarySection(parent)
                break
            parent = parent.getparent()

class Target:
    def __init__(self, top, fragId, fragNum):
        self.fragId = fragId
        self.fragNum = fragNum
        self.links = []
        self.elem = top.xpath("//*[@cdr:id='%s']" % fragId,
                              namespaces={"cdr": "cips.nci.nih.gov/cdr"})[0]
        self.section = None
        #self.text = u"".join([t for t in self.elem.itertext()])[:200]
        e = self.elem
        while e is not None:
            if e.tag == "SummarySection":
                self.section = SummarySection(e)
                break
            e = e.getparent()
    def __cmp__(self, other):
        if self.fragNum is not None:
            if other.fragNum is not None:
                return cmp(self.fragNum, other.fragNum)
            return -1
        return cmp(self.fragId, other.fragId)

def findLinks(docId, node, links, elements):
    elements.append(node.tag)
    link = Link(node, elements)
    if link.docId == docId:
        links.append(link)
    for child in node:
        findLinks(docId, child, links, list(elements))

cursor.execute("SELECT title, xml FROM document WHERE id = ?", docId)
rows = cursor.fetchall()
if not rows:
    cdrcgi.bail("can't find document %s" % docId)
tree = etree.XML(rows[0][1].encode("utf-8"))
title = rows[0][0]
links = []
elements = []
findLinks(int(docId), tree, links, elements)
msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
styles = cdrcgi.ExcelStyles()
styles.set_color(styles.header, "blue")
styles.frag = styles.style("align: horz right, vert center, wrap true")
styles.source = styles.style("align: horz left, vert center, wrap true")
sheet = styles.add_sheet("Links")
banner = "Links for CDR%s (%s)" % (docId, title)
sheet.write_merge(0, 0, 0, 5, banner, styles.header)
labels = ("FragID", "Source Section/Subsection",
          "Section/Subsection Containing Fragment Ref",
          "Text in Fragment Ref", "In Table?", "In List?")
widths = (10, 60, 60, 60, 10, 10)
assert(len(labels) == len(widths))
for i, chars in enumerate(widths):
    sheet.col(i).width = styles.chars_to_width(chars)
for i, label in enumerate(labels):
    sheet.write(1, i, label, styles.header)
targets = {}
for link in links:
    target = targets.get(link.fragId)
    if not target:
        targets[link.fragId] = target = Target(tree, link.fragId, link.fragNum)
    target.links.append(link)
row = 2
for target in sorted(targets.values()):
    targetSectionTitle = target.section and target.section.title or "None"
    first = row
    last = row + len(target.links) - 1
    sheet.write_merge(first, last, 0, 0, target.fragId, styles.frag)
    sheet.write_merge(first, last, 1, 1, targetSectionTitle, styles.source)
    for link in target.links:
        sourceSectionTitle = link.section and link.section.title or "None"
        sheet.write(row, 2, sourceSectionTitle, styles.left)
        sheet.write(row, 3, unicode(link.text), styles.left)
        if "/Table/" in link.path:
            sheet.write(row, 4, "X", styles.center)
        if "/ListItem/" in link.path:
            sheet.write(row, 5, "X", styles.center)
        row += 1
stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
name = "SummaryInternalLinks-CDR%s-%s.xls" % (docId, stamp)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
styles.book.save(sys.stdout)
