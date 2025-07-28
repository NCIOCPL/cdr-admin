#!/usr/bin/env python

"""Create a new CDR action or modify an existing one.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for editing interface."""

    EDIT_ACTIONS = "EditActions.py"
    ACTION_MENU = "Action Menu"
    DELETE = "Delete Action"
    SAVE_CHANGES = "Save Changes"
    SAVE_NEW = "Save New Action"

    def delete(self):
        """Delete the current action and return to the parent menu."""
        self.action.delete(self.session)
        self.return_to_actions_menu(self.action.name)

    def populate_form(self, page):
        """Add the field sets and custom style rules to the page.

        Pass:
            page - HTMLPage object to be filled out
        """

        page.form.append(page.hidden_field("action", self.action.name or ""))
        fieldset = page.fieldset("Action Identification")
        fieldset.append(page.text_field("name", value=self.action.name))
        opts = dict(value=self.action.comment, rows=5)
        fieldset.append(page.textarea("comment", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        label = "Permissions set per doctype?"
        opts = dict(value="doctype-specific", label=label)
        if self.action.doctype_specific == "Y":
            opts["checked"] = True
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)

    def return_to_actions_menu(self, deleted=None):
        """Go back to the menu listing all the CDR actions."""

        opts = dict(deleted=deleted) if deleted else dict(returned="true")
        self.navigate_to(self.EDIT_ACTIONS, self.session.name, **opts)

    def run(self):
        """Override base class so we can handle the extra buttons."""

        try:
            if self.request == self.DELETE:
                return self.delete()
            elif self.request in (self.SAVE_CHANGES, self.SAVE_NEW):
                return self.save()
            elif self.request == self.ACTION_MENU:
                return self.return_to_actions_menu()
        except Exception as e:
            self.bail(f"Failure: {e}")
        Controller.run(self)

    def save(self):
        """Save the new or modified action object."""

        self.action.name = self.name
        self.action.comment = self.comment
        self.action.doctype_specific = "Y" if self.doctype_specific else "N"
        if self.action.id:
            alert = f"Action {self.name!r} successfully updated."
            self.action.modify(self.session)
        else:
            alert = f"Action {self.name!r} successfully added."
            self.action.add(self.session)
            self.action = self.session.get_action(self.name)
        self.alerts.append(dict(message=alert, type="success"))
        self.show_form()

    @property
    def action(self):
        """Object for the CDR action being edited/created."""

        if not hasattr(self, "_action"):
            name = self.fields.getvalue("action")
            if name:
                self._action = self.session.get_action(name)
            else:
                self._action = self.session.Action("", "N")
        return self._action

    @action.setter
    def action(self, value):
        """Allow replacement after a save."""
        self._action = value

    @cached_property
    def buttons(self):
        """Identify our custom navigation buttons."""

        if self.action.id:
            return [self.SAVE_CHANGES, self.DELETE, self.ACTION_MENU]
        return [self.SAVE_NEW, self.ACTION_MENU]

    @cached_property
    def comment(self):
        """Get the comment value from the form field."""
        return self.fields.getvalue("comment")

    @cached_property
    def doctype_specific(self):
        """True if permissions for this action are doctype-specific."""

        if "doctype-specific" in self.fields.getlist("options"):
            return True
        return False

    @cached_property
    def name(self):
        """Current value of the form's name field."""
        return self.fields.getvalue("name")

    @cached_property
    def same_window(self):
        """Don't open any new browser tabs."""
        return self.buttons

    @property
    def subtitle(self):
        """Dynamic string for display under the main banner."""

        if self.action.id:
            return f"Edit {self.action.name} Action"
        return "Add New Action"


if __name__ == "__main__":
    """Don't execute the script if we've been loaded as a module."""
    Control().run()
