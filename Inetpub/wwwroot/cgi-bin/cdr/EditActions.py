#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for editing CDR groups.
#
# OCECDR-4087
#
#----------------------------------------------------------------------

import urllib
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    ADD_NEW_ACTION = "Add New Action"
    EDIT_ACTION = "EditAction.py"
    B = cdrcgi.Page.B
    NCOLS = 4
    def __init__(self):
        cdrcgi.Control.__init__(self, "Manage Actions")
        if not self.authorized():
            cdrcgi.bail("Account not authorized for this page.")
        self.buttons = (self.ADD_NEW_ACTION, self.ADMINMENU, self.LOG_OUT)
        self.parms = { cdrcgi.SESSION: self.session }
    def populate_form(self, form):
        warning = (
            "<p class='warning'>DO NOT CLICK THE LINK FOR THE EXISTING "
            "'ADD ACTION' LINK BELOW IF YOU WANT TO ADD A NEW ACTION!<br>"
            "USE THE Add New Action BUTTON ABOVE INSTEAD!!!</p>"
        )
        form.add("<fieldset>")
        form.add(self.B.LEGEND("Existing Actions (click to edit)"))
        form.add(warning)
        form.add(self.make_table())
        form.add("</fieldset>")
        form.add_css("""\
fieldset { width: 1000px; }
table { background: transparent; }
th, td { background: transparent; padding: 3px; border: none; width: 25%; }
a { text-decoration: none; color: #00E; }
a:hover { text-decoration: underline; }
.warning { font-weight: bold; text-align: center; }""")
    def run(self):
        if self.request == self.ADD_NEW_ACTION:
            cdrcgi.navigateTo(self.EDIT_ACTION, self.session)
        else:
            cdrcgi.Control.run(self)
    def authorized(self):
        if not self.session:
            return False
        for action in ("ADD ACTION", "MODIFY ACTION", "DELETE ACTION"):
            if cdr.canDo(self.session, action):
                return True
        return False
    def make_table(self):
        actions = self.get_actions()
        nrows = len(actions) // self.NCOLS
        if len(actions) % self.NCOLS:
            nrows += 1
        rows = []
        while len(rows) < nrows:
            rows.append(self.make_row(actions, nrows, len(rows)))
        return self.B.TABLE(*rows)
    def make_row(self, actions, nrows, row_number):
        cells = []
        for col in range(self.NCOLS):
            index = nrows * col + row_number
            if index < len(actions):
                cells.append(self.make_cell(actions[index]))
        return self.B.TR(*cells)
    def make_cell(self, action):
        self.parms["action"] = action
        url = "%s?%s" % (self.EDIT_ACTION, urllib.urlencode(self.parms))
        return self.B.TD(self.B.A(action, href=url))
    def get_actions(self):
        actions = cdr.getActions(self.session)
        if isinstance(actions, basestring):
            cdrcgi.bail(actions)
        return sorted(actions)

Control().run()
