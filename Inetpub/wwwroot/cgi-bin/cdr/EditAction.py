#----------------------------------------------------------------------
# Create a new CDR action or modify an existing one.
# TODO: use real xml package instead of string manipulation in cdr
#       module functions instead of escaping the strings here.
#----------------------------------------------------------------------

import cdr
import cdrcgi
from html import escape as html_escape

class Control(cdrcgi.Control):
    EDIT_ACTIONS = "EditActions.py"
    CANCEL = "Actions Menu"
    DELETE = "Delete"
    SAVE_CHANGES = "Save Changes"
    SAVE_NEW = "Save New Action"
    def __init__(self):
        cdrcgi.Control.__init__(self, "Edit Action")
        self.actions = self.get_actions()
        self.action_name = self.fields.getvalue("action", "")
        if self.action_name:
            if self.action_name not in self.actions:
                cdrcgi.bail(cdrcgi.TAMPERING)
            self.buttons = [self.SAVE_CHANGES, self.DELETE]
        else:
            self.buttons = [self.SAVE_NEW]
        self.buttons += [self.CANCEL, self.ADMINMENU, self.LOG_OUT]
        self.buttons = self.get_buttons()
    def get_buttons(self):
        if self.action_name:
            buttons = [self.SAVE_CHANGES, self.DELETE]
        else:
            buttons = [self.SAVE_NEW]
        return buttons + [self.CANCEL, self.ADMINMENU, self.LOG_OUT]
    def populate_form(self, form):
        action = self.get_action()
        comment = action.comment or ""
        comment = comment.replace("\r", "").replace("\n", cdrcgi.NEWLINE)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Action"))
        form.add_hidden_field("action", action.name)
        form.add_text_field("name", "Name", value=action.name)
        form.add_textarea_field("comment", "Comment", value=comment)
        form.add("</fieldset>")
        form.add("<fieldset>")
        legend = "Action authorized for individual document types?"
        form.add(form.B.LEGEND(legend))
        for label in ("Yes", "No"):
            value = label[0]
            checked = action.doctype_specific == value
            form.add_radio("doctype-specific", label, value, checked=checked)
        form.add("</fieldset>")
    def run(self):
        if self.request == self.CANCEL:
            cdrcgi.navigateTo(self.EDIT_ACTIONS, self.session)
        if self.request == self.DELETE and self.action_name:
            self.delete_action()
        if self.request in (self.SAVE_CHANGES, self.SAVE_NEW):
            self.save_action()
        cdrcgi.Control.run(self)
    def delete_action(self):
        error = cdr.delAction(self.session, html_escape(self.action_name))
        if error:
            cdrcgi.bail(error)
        cdrcgi.navigateTo(self.EDIT_ACTIONS, self.session)
    def save_action(self):
        name = self.fields.getvalue("name")
        comment = self.fields.getvalue("comment") or None
        flag = self.fields.getvalue("doctype-specific") or "N"
        if not name:
            cdrcgi.bail("Name field is required.")
        if flag not in ("Y", "N"):
            cdrcgi.bail(cdrcgi.TAMPERING)
        if comment:
            comment = html_escape(comment)
        action = cdr.Action(html_escape(name), flag, comment)
        action_name = self.action_name and html_escape(self.action_name) or None
        error = cdr.putAction(self.session, action_name, action)
        if error:
            cdrcgi.bail(error)
        self.action_name = action.name
        self.buttons = self.get_buttons()
    def get_actions(self):
        actions = cdr.getActions(self.session)
        if isinstance(actions, (str, bytes)):
            cdrcgi.bail(actions)
        return sorted(actions)
    def get_action(self):
        if not self.action_name:
            return cdr.Action("", "N")
        action = cdr.getAction(self.session, self.action_name)
        if isinstance(action, (str, bytes)):
            cdrcgi.bail(action)
        return action
Control().run()
