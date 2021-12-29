#!/usr/bin/env python

"""Create a new CDR action or modify an existing one.
"""

from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for editing interface."""

    EDIT_ACTIONS = "EditActions.py"
    SUBMENU = "Action Menu"
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

        opts = dict(deleted=deleted) if deleted else {}
        self.navigate_to(self.EDIT_ACTIONS, self.session.name, **opts)

    def run(self):
        """Override base class so we can handle the extra buttons."""

        try:
            if self.request == self.DELETE:
                return self.delete()
            elif self.request in (self.SAVE_CHANGES, self.SAVE_NEW):
                return self.save()
            elif self.request == self.SUBMENU:
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
            self.action.modify(self.session)
            self.subtitle = f"Action {self.name!r} successfully updated"
        else:
            self.action.add(self.session)
            self.subtitle = f"Action {self.name!r} successfully added"
            self.action = self.session.get_action(self.name)
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

    @property
    def buttons(self):
        """Add our custom navigation buttons."""

        if not hasattr(self, "_buttons"):
            self._buttons = [self.SUBMENU, self.ADMINMENU, self.LOG_OUT]
            if self.action.id:
                self._buttons.insert(0, self.DELETE)
                self._buttons.insert(0, self.SAVE_CHANGES)
            else:
                self._buttons.insert(0, self.SAVE_NEW)
        return self._buttons

    @property
    def comment(self):
        """Get the comment value from the form field."""
        return self.fields.getvalue("comment")

    @property
    def doctype_specific(self):
        """True if permissions for this action are doctype-specific."""

        if not hasattr(self, "_doctype_specific"):
            if "doctype-specific" in self.fields.getlist("options"):
                self._doctype_specific = True
            else:
                self._doctype_specific = False
        return self._doctype_specific

    @property
    def name(self):
        """Current value of the form's name field."""
        return self.fields.getvalue("name")

    @property
    def subtitle(self):
        """Dynamic string for display under the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.name:
                self._subtitle = f"Editing {self.name!r} action"
            else:
                self._subtitle = "Adding New Action"
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Provide status information after a save."""
        self._subtitle = value


if __name__ == "__main__":
    """Don't execute the script if we've been loaded as a module."""
    Control().run()
