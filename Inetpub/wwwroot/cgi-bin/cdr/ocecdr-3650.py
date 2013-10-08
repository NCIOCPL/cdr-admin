#----------------------------------------------------------------------
#
# $Id$
#
# Reports on internal links within a summary to support keeping standard
# treatment options in sync during the HP reformat process.  Implemented
# in a more general way in order to support other uses.
#
# JIRA::OCECDR-3650
#
#----------------------------------------------------------------------
import cgi, cdrcgi, cdrdb, lxml.etree as etree, re, sys, xlwt, msvcrt, os, time

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
font = xlwt.Font()
font.colour_index = 4
font.bold = True
alignment = xlwt.Alignment()
alignment.horz = xlwt.Alignment.HORZ_CENTER
style = xlwt.XFStyle()
style.font = font
style.alignment = alignment
book = xlwt.Workbook(encoding="UTF-8")
sheet = book.add_sheet("Links")
sheet.write_merge(0, 0, 0, 5, "Links for CDR%s (%s)" % (docId, title), style)
sheet.write(1, 0, "FragID", style)
sheet.write(1, 1, "Source Section/Subsection", style)
sheet.write(1, 2, "Section/Subsection Containing Fragment", style)
sheet.write(1, 3, "Text in Fragment", style)
sheet.write(1, 4, "In Table?", style)
sheet.write(1, 5, "In List?", style)
sheet.col(0).width = 4000
sheet.col(1).width = 15000
sheet.col(2).width = 15000
sheet.col(3).width = 15000
#sheet.col(4).width = 100
#sheet.col(5).width = 100
alignment = xlwt.Alignment()
alignment.vert = xlwt.Alignment.VERT_CENTER
alignment.horz = xlwt.Alignment.HORZ_RIGHT
style1 = xlwt.XFStyle()
style1.alignment = alignment
alignment = xlwt.Alignment()
alignment.vert = xlwt.Alignment.VERT_CENTER
alignment.horz = xlwt.Alignment.HORZ_LEFT
style2 = xlwt.XFStyle()
style2.alignment = alignment
alignment = xlwt.Alignment()
alignment.vert = xlwt.Alignment.VERT_TOP
alignment.horz = xlwt.Alignment.HORZ_LEFT
style3 = xlwt.XFStyle()
style3.alignment = alignment
alignment = xlwt.Alignment()
alignment.vert = xlwt.Alignment.VERT_TOP
alignment.horz = xlwt.Alignment.HORZ_CENTER
style4 = xlwt.XFStyle()
style4.alignment = alignment
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
    sheet.write_merge(first, last, 0, 0, target.fragId, style1)
    sheet.write_merge(first, last, 1, 1, targetSectionTitle, style2)
    for link in target.links:
        sourceSectionTitle = link.section and link.section.title or "None"
        sheet.write(row, 2, sourceSectionTitle, style3)
        sheet.write(row, 3, unicode(link.text), style3)
        if "/Table/" in link.path:
            sheet.write(row, 4, "X", style4)
        if "/ListItem/" in link.path:
            sheet.write(row, 5, "X", style4)
        row += 1
stamp = time.strftime("%Y%m%d%H%M%S")
name = "SummaryInternalLinks-CDR%s-%s.xls" % (docId, stamp)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
book.save(sys.stdout)
