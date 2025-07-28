#!/usr/bin/env python

"""Interface for editing a CDR group.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doctype


class Control(Controller):
    """Top-level logic for editing interface."""

    EDIT_GROUPS = "EditGroups.py"
    GROUP_MENU = "Group Menu"
    SAVE_CHANGES = "Save Changes"
    SAVE_NEW = "Save New Group"
    DELETE = "Delete Group"

    def delete(self):
        """Delete the current group and return to the Groups menu."""
        self.group.delete(self.session)
        self.return_to_groups_menu(self.group.name)

    def populate_form(self, page):
        """Add the field sets and custom style rules to the page.

        Pass:
            page - HTMLPage object to be filled out
        """

        page.form.append(page.hidden_field("grp", self.group.name or ""))
        fieldset = page.fieldset("Group Identification")
        fieldset.append(page.text_field("name", value=self.group.name))
        opts = dict(value=self.group.comment, rows=5)
        fieldset.append(page.textarea("description", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Group Members")
        fieldset.set("id", "users-fieldset")
        fieldset.set("class", "usa-fieldset checkboxes")
        ul = page.B.UL()
        fieldset.append(ul)
        for name in sorted(self.users, key=str.lower):
            user = self.users[name]
            opts = dict(value=user.name, label=user.name)
            if user.fullname:
                opts["tooltip"] = user.fullname
            if self.group.users and name in self.group.users:
                opts["checked"] = True
            ul.append(page.B.LI(page.checkbox("user", **opts)))
        page.form.append(fieldset)
        fieldset = page.fieldset("Actions Independent Of Document Types")
        fieldset.set("class", "checkboxes usa-fieldset")
        fieldset.set("id", "independent-actions")
        ul = page.B.UL()
        fieldset.append(ul)
        for action in self.actions:
            if action.doctype_specific == "N":
                opts = dict(value=action.name, label=action.name)
                if self.group.actions and action.name in self.group.actions:
                    opts["checked"] = True
                ul.append(page.B.LI(page.checkbox("action", **opts)))
        page.form.append(fieldset)
        for action in self.actions:
            if action.doctype_specific == "Y":
                group = self.action_group_name(action)
                fieldset = page.fieldset(action.name)
                fieldset.set("class", "checkboxes usa-fieldset")
                ul = page.B.UL()
                fieldset.append(ul)
                if self.group.actions:
                    doctypes = self.group.actions.get(action.name) or []
                else:
                    doctypes = []
                for doctype in self.doctypes:
                    opts = dict(value=doctype, label=doctype)
                    if doctype in doctypes:
                        opts["checked"] = True
                    ul.append(page.B.LI(page.checkbox(group, **opts)))
                page.form.append(fieldset)

        # Don't know why the first column in the list is positioned lower than
        # the subsequent columns. Doesn't work that way for other links in
        # columns. May have something to do with the tricky positioning of
        # checkboxes used by USWDS. Solution is to raise the DIV for the first
        # checkbox by .75rem.
        page.add_css("""\
.checkboxes ul { column-width: 13rem; list-style-type: none; }
.checkboxes ul li:first-child div { margin-top: -.75rem; }
#independent-actions ul { column-width: 15rem; }
""")

    def return_to_groups_menu(self, deleted=None):
        """Go back to the menu listing all the CDR groups."""

        opts = dict(deleted=deleted) if deleted else dict(returned="true")
        self.navigate_to(self.EDIT_GROUPS, self.session.name, **opts)

    def run(self):
        """Override base class so we can handle the extra buttons."""

        try:
            if self.request == self.DELETE:
                return self.delete()
            elif self.request in (self.SAVE_CHANGES, self.SAVE_NEW):
                return self.save()
            elif self.request == self.GROUP_MENU:
                return self.return_to_groups_menu()
        except Exception as e:
            self.bail(f"Failure: {e}")
        Controller.run(self)

    def save(self):
        """Save the new or modified group object."""

        opts = dict(
            id=self.group.id,
            name=self.name,
            comment=self.comment,
            users=self.members,
            actions=self.allowed_actions,
        )
        self.group = self.session.Group(**opts)
        if self.group.id:
            self.group.modify(self.session)
            alert = f"Group {self.name!r} successfully updated."
        else:
            self.group.add(self.session)
            alert = f"Group {self.name!r} successfully added."
        self.alerts.append(dict(message=alert, type="success"))
        self.show_form()

    @cached_property
    def actions(self):
        """Sequence of `Action` objects for all the actions in the system."""
        return self.session.list_actions()

    @cached_property
    def allowed_actions(self):
        """Checkboxes checked for the "action" groups."""

        actions = {}
        independent_actions = self.fields.getlist("action")
        for action in self.actions:
            if action.doctype_specific == "N":
                if action.name in independent_actions:
                    actions[action.name] = [""]
            else:
                action_group_name = self.action_group_name(action)
                doctypes = self.fields.getlist(action_group_name)
                if doctypes:
                    actions[action.name] = doctypes
        return actions

    @cached_property
    def buttons(self):
        """Add our custom navigation buttons."""

        if self.group.id:
            return self.SAVE_CHANGES, self.DELETE, self.GROUP_MENU
        return self.SAVE_NEW, self.GROUP_MENU

    @cached_property
    def comment(self):
        """Current value of the form's description field."""
        return self.fields.getvalue("description")

    @cached_property
    def doctypes(self):
        """Sorted names of all the active document types."""
        return Doctype.list_doc_types(self.session)

    @cached_property
    def group(self):
        """Object for the CDR group being edited/created."""

        name = self.fields.getvalue("grp")
        if name:
            return self.session.get_group(name)
        opts = dict(
            name=self.name,
            comment=self.comment,
            session=self.session
        )
        return self.session.Group(**opts)

    @cached_property
    def members(self):
        """Checkboxes checked from the "user" group."""
        return self.fields.getlist("user")

    @cached_property
    def name(self):
        """Current value of the form's name field."""
        return self.fields.getvalue("name")

    @cached_property
    def same_window(self):
        """Don't open any new browser tabs."""
        return self.buttons

    @cached_property
    def subtitle(self):
        """Dynamic string for display under the main banner."""
        return self.group.name or "Add New Group"

    @cached_property
    def users(self):
        """Active users for whom we generate checkboxes."""

        users = {}
        for name in self.session.list_users():
            users[name] = self.session.User(self.session, name=name)
        return users

    @staticmethod
    def action_group_name(action):
        """Name the doctype buttons for a specific action.

        Pass:
            action - `Action` object
        """

        return action.name.lower().replace(" ", "_") + "-doctype"


Control().run()
