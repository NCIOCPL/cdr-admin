#!/usr/bin/env python

"""Menu for editing CDR actions.
"""

from functools import cached_property
from cdrcgi import Controller, FormFieldFactory


class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    SUBTITLE = "Manage Actions"
    LOGNAME = "ManageActions"
    ADD_NEW_ACTION = "Add New Action"
    EDIT_ACTION = "EditAction.py"
    WARNING = (
        "Do ",
        FormFieldFactory.B.STRONG("NOT"),
        " click the link for the existing ",
        FormFieldFactory.B.BR(),
        FormFieldFactory.B.CODE(FormFieldFactory.B.STRONG("ADD ACTION")),
        FormFieldFactory.B.BR(),
        " action below to add a new action!",
        FormFieldFactory.B.BR(),
        "Use the ",
        FormFieldFactory.B.STRONG("Add New Action"),
        " button below instead!!!",
    )

    def run(self):
        """Override base class to add action for new button."""
        if self.request == self.ADD_NEW_ACTION:
            self.navigate_to(self.EDIT_ACTION, self.session.name)
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Add action editing links and some custom style rules to the page."""

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Actions (click to edit)")
        fieldset.set("id", "action-list")
        warning = page.B.P(*self.WARNING, page.B.CLASS("text-red text-center"))
        page.form.append(warning)
        script = self.EDIT_ACTION
        ul = page.B.UL()
        for action in self.session.list_actions():
            link = page.menu_link(script, action.name, action=action.name)
            if not self.deleted and not self.returned:
                link.set("target", "_blank")
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css("""
#action-list ul { list-style-type: none; column-width: 15rem; }
#action-list a { text-decoration: none; }
#action-list a:visited { color: """ + page.LINK_COLOR + """; }
p.text-red { border: red solid 2px; padding: 1rem; margin: 2rem 0; }
p.text-red code strong { color: blue; }
""")

    @cached_property
    def alerts(self):
        """Let the user know if we successfully deleted an action."""

        if self.deleted:
            message = f"Successfully deleted action {self.deleted!r}."
            return [dict(message=message, type="success")]
        return []

    @property
    def buttons(self):
        """Override to specify custom button for this page."""
        return [self.ADD_NEW_ACTION]

    @cached_property
    def deleted(self):
        """Name of action which was just deleted, if appropriate."""
        return self.fields.getvalue("deleted")

    @cached_property
    def returned(self):
        """True if user clicked the Action Menu button on the editing form."""
        return True if self.fields.getvalue("returned") else False

    @cached_property
    def same_window(self):
        """Don't multiply browser tabs recursively."""
        return self.buttons if self.deleted or self.returned else []


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
