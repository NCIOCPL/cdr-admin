#!/usr/bin/env python

"""Menu for editing CDR actions.
"""

from cdrcgi import Controller, navigateTo

class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    ADD_NEW_ACTION = "Add New Action"
    EDIT_ACTION = "EditAction.py"
    WARNING = (
        "DO NOT CLICK THE LINK FOR THE EXISTING 'ADD ACTION' LINK BELOW "
        "IF YOU WANT TO ADD A NEW ACTION!",
        "USE THE Add New Action BUTTON ABOVE INSTEAD!!!",
    )

    def run(self):
        """Override base class to add action for new button."""
        if self.request == self.ADD_NEW_ACTION:
            navigateTo(self.EDIT_ACTION, self.session.name)
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Add action editing links and some custom style rules to the page."""

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Actions (click to edit)")
        fieldset.set("class", "flexlinks")
        warning = page.B.P(page.B.CLASS("warning center strong"))
        br = None
        for line in self.WARNING:
            if br is not None:
                warning.append(br)
            br = page.B.BR()
            warning.append(page.B.SPAN(line))
        fieldset.append(warning)
        script = self.EDIT_ACTION
        ul = page.B.UL()
        for action in self.session.list_actions():
            link = page.menu_link(script, action.name, action=action.name)
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)

    @property
    def subtitle(self):
        """Dynamically determine what to display under the main banner."""

        if not hasattr(self, "_subtitle"):
            action = self.fields.getvalue("deleted")
            if action:
                self._subtitle = f"Successfully deleted action {action!r}"
            else:
                self._subtitle = "Manage Actions"
        return self._subtitle

    @property
    def buttons(self):
        """Override to specify custom buttons for this page."""
        return self.ADD_NEW_ACTION, self.DEVMENU, self.ADMINMENU, self.LOG_OUT


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
