#----------------------------------------------------------------------
# Interface for editing CDR document types.
# JIRA::OCECDR-4091
#----------------------------------------------------------------------
import urllib
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    ADD_NEW_DOCTYPE = "Add New Document Type"
    EDIT_DOCTYPE = "EditDoctype.py"
    B = cdrcgi.Page.B
    NCOLS = 4
    def __init__(self):
        cdrcgi.Control.__init__(self, "Manage Document Types")
        self.buttons = (self.ADD_NEW_DOCTYPE, self.ADMINMENU, self.LOG_OUT)
        self.parms = { cdrcgi.SESSION: self.session }
    def populate_form(self, form):
        form.add("<fieldset>")
        form.add(self.B.LEGEND("Existing Document Types (click to edit)"))
        form.add(self.make_table())
        form.add("</fieldset>")
        form.add_css("""\
fieldset { width: 750px; }
table { background: transparent; }
th, td { background: transparent; padding: 3px; border: none; width: 25%; }
a { text-decoration: none; color: #00E; }
a:hover { text-decoration: underline; }
.warning { font-weight: bold; text-align: center; }""")
    def run(self):
        if self.request == self.ADD_NEW_DOCTYPE:
            cdrcgi.navigateTo(self.EDIT_DOCTYPE, self.session)
        else:
            cdrcgi.Control.run(self)
    def make_table(self):
        doctypes = self.get_doctypes()
        nrows = len(doctypes) // self.NCOLS
        if len(doctypes) % self.NCOLS:
            nrows += 1
        rows = []
        while len(rows) < nrows:
            rows.append(self.make_row(doctypes, nrows, len(rows)))
        return self.B.TABLE(*rows)
    def make_row(self, doctypes, nrows, row_number):
        cells = []
        for col in range(self.NCOLS):
            index = nrows * col + row_number
            if index < len(doctypes):
                cells.append(self.make_cell(doctypes[index]))
        return self.B.TR(*cells)
    def make_cell(self, doctype):
        self.parms["doctype"] = doctype
        url = "%s?%s" % (self.EDIT_DOCTYPE, urllib.urlencode(self.parms))
        return self.B.TD(self.B.A(doctype, href=url))
    def get_doctypes(self):
        doctypes = cdr.getDoctypes(self.session)
        if isinstance(doctypes, basestring):
            cdrcgi.bail(doctypes)
        return sorted(doctypes)

Control().run()
