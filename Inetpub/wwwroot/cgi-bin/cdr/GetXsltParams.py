#----------------------------------------------------------------------
# Show all of the top-level parameters used by CDR filters.  Useful
# for XSL/T script writers who want to avoid conflicting uses of the
# same parameter names across more than one script, which might be
# invoked as a set (the CdrFilter command expects all of the parameters
# supplied for the command to be applicable to all filters named by
# the command).
#----------------------------------------------------------------------
import cdrdb
import lxml.etree as etree
import lxml.html.builder as builder

TITLE = "Global Filter Parameters"

class Filter:
    def __init__(self, doc_id, doc_title, doc_xml):
        self.doc_id = doc_id
        self.doc_title = doc_title
        root = etree.XML(doc_xml.encode("utf-8"))
        path = "{http://www.w3.org/1999/XSL/Transform}param"
        names = set()
        for node in root.findall(path):
            name = node.get("name")
            if name not in names:
                names.add(name)
                parameter = Parameter.parameters.get(name)
                if not parameter:
                    parameter = Parameter(name)
                    Parameter.parameters[name] = parameter
                parameter.filters.append(self)
    def make_cells(self):
        return (
            builder.TD("CDR%010d" % self.doc_id),
            builder.TD(self.doc_title)
        )

class Parameter:
    parameters = {}
    def __init__(self, name):
        self.name = name
        self.filters = []
    def add_rows(self, tbody):
        name = builder.TH(self.name)
        if len(self.filters) > 1:
            name.set("rowspan", str(len(self.filters)))
        row = builder.TR(name, *self.filters[0].make_cells())
        tbody.append(row)
        for f in self.filters[1:]:
            tbody.append(builder.TR(*f.make_cells()))

def main():
    cursor = cdrdb.connect("CdrGuest").cursor()
    query = cdrdb.Query("document d", "d.id", "d.title", "d.xml").order(2)
    query.join("doc_type t", "t.id = d.doc_type")
    query.where("t.name = 'Filter'")
    filters = []
    for doc_id, doc_title, doc_xml in query.execute(cursor).fetchall():
        filters.append(Filter(doc_id, doc_title, doc_xml))
    tbody = builder.TBODY()
    caption = builder.CAPTION(TITLE)
    for parm in sorted(Parameter.parameters.values()):
        parm.add_rows(tbody)
    page = builder.HTML(
        builder.HEAD(
            builder.TITLE(TITLE),
            builder.LINK(rel="stylesheet", href="/stylesheets/cdr.css"),
            builder.STYLE("th { text-align: right; vertical-align: top; }")
        ),
        builder.BODY(builder.TABLE(caption, tbody), builder.CLASS("report"))
    )
    print "Content-type: text/html\n"
    print etree.tostring(page, pretty_print=True)

if __name__ == "__main__":
    main()
