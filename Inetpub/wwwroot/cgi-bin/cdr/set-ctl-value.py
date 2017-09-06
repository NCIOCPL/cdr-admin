"""
Add a row to the ctl table.
"""

import cdr
import cdrcgi
import cdrdb

class Control(cdrcgi.Control):
    def __init__(self):
        cdrcgi.Control.__init__(self, "CDR Control Values")
        self.name = self.fields.getvalue("name") or ""
        self.group = self.fields.getvalue("group") or ""
        self.value = self.fields.getvalue("value") or ""
        self.comment = self.fields.getvalue("comment") or ""
        if not self.session or not cdr.canDo(self.session, "SET_SYS_VALUE"):
            cdrcgi.bail("Not authorized to manage control values")
    def populate_form(self, form):
        tip = "Enter @@INACTIVATE@@ to inactivate the control value."
        form.add("<fieldset>")
        form.add(form.B.LEGEND("All fields required except Comment"))
        form.add_text_field("group", "Group", value=self.group)
        form.add_text_field("name", "Name", value=self.name)
        form.add_textarea_field("value", "Value", value=self.value, tooltip=tip)
        form.add_textarea_field("comment", "Comment", value=self.comment)
        form.add("</fieldset>")
        query = cdrdb.Query("ctl", "grp", "name", "val", "comment")
        query.where("inactivated IS NULL")
        query.order("grp", "name")
        rows = query.execute().fetchall()
        table = form.B.TABLE(
            form.B.TR(
                form.B.TH("Group"),
                form.B.TH("Name"),
                form.B.TH("Value"),
                form.B.TH("Comment")
            )
        )
        for grp, name, val, comment in rows:
            row = form.B.TR(
                form.B.TD(grp or ""),
                form.B.TD(name or ""),
                form.B.TD(val or ""),
                form.B.TD(comment or "")
            )
            table.append(row)
        form.add(table)
    def show_report(self):
        if not (self.group and self.name and self.value):
            cdrcgi.bail("group, name, and value are all required fields")
        try:
            if self.value == "@@INACTIVATE@@":
                cdr.updateCtl(self.session, "Inactivate", self.group,
                              self.name, comment=self.comment)
            else:
                cdr.updateCtl(self.session, "Create", self.group, self.name,
                              self.value, self.comment)
            self.show_form()
        except Exception as e:
            cdrcgi.bail(str(e))

if __name__ == "__main__":
    Control().run()
