#!/usr/bin/env python

"""Interface for editing a CDR group.
"""

from cdrcgi import Controller, navigateTo, bail
from cdrapi.docs import Doctype


class Control(Controller):
    """Top-level logic for editing interface."""

    EDIT_GROUPS = "EditGroups.py"
    SUBMENU = "Group Menu"
    SAVE = "Save Changes"
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
        fieldset.set("class", "checkboxes")
        for name in sorted(self.users, key=str.lower):
            user = self.users[name]
            opts = dict(value=user.name, label=user.name)
            if user.fullname:
                opts["tooltip"] = user.fullname
            if self.group.users and name in self.group.users:
                opts["checked"] = True
            fieldset.append(page.checkbox("user", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Actions Independent Of Document Types")
        fieldset.set("class", "checkboxes")
        fieldset.set("id", "independent-actions")
        for action in self.actions:
            if action.doctype_specific == "N":
                opts = dict(value=action.name, label=action.name)
                if self.group.actions and action.name in self.group.actions:
                    opts["checked"] = True
                fieldset.append(page.checkbox("action", **opts))
        page.form.append(fieldset)
        for action in self.actions:
            if action.doctype_specific == "Y":
                group = self.action_group_name(action)
                fieldset = page.fieldset(action.name)
                fieldset.set("class", "checkboxes")
                if self.group.actions:
                    doctypes = self.group.actions.get(action.name) or []
                else:
                    doctypes = []
                for doctype in self.doctypes:
                    opts = dict(value=doctype, label=doctype)
                    if doctype in doctypes:
                        opts["checked"] = True
                    fieldset.append(page.checkbox(group, **opts))
                page.form.append(fieldset)
        page.add_css("""\
fieldset {width: 1200px; }
fieldset.checkboxes div { float: left; width: 240px; }
fieldset#users-fieldset div { width: 200px;}
fieldset#independent-actions div { width: 300px; }
.labeled-field textarea, .labeled-field #name { width: 1050px; }
""")

    def return_to_groups_menu(self, deleted=None):
        """Go back to the menu listing all the CDR groups."""

        opts = dict(deleted=deleted) if deleted else {}
        navigateTo(self.EDIT_GROUPS, self.session.name, **opts)

    def run(self):
        """Override base class so we can handle the extra buttons."""

        try:
            if self.request == self.DELETE:
                return self.delete()
            elif self.request == self.SAVE:
                return self.save()
            elif self.request == self.SUBMENU:
                return self.return_to_groups_menu()
        except Exception as e:
            bail(f"Failure: {e}")
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
            self.subtitle = f"Group {self.name!r} successfully updated"
        else:
            self.group.add(self.session)
            self.subtitle = f"Group {self.name!r} successfully added"
        self.show_form()

    @property
    def actions(self):
        """Sequence of `Action` objects for all the actions in the system."""

        if not hasattr(self, "_actions"):
            self._actions = self.session.list_actions()
        return self._actions

    @property
    def allowed_actions(self):
        """Checkboxes checked for the "action" groups."""

        if not hasattr(self, "_allowed_actions"):
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
            self._allowed_actions = actions
        return self._allowed_actions

    @property
    def buttons(self):
        """Add our custom navigation buttons."""

        if not hasattr(self, "_buttons"):
            buttons = [self.SAVE, self.SUBMENU, self.ADMINMENU, self.LOG_OUT]
            if self.group.id:
                buttons.insert(1, self.DELETE)
            self._buttons = buttons
        return self._buttons

    @property
    def comment(self):
        """Current value of the form's description field."""
        return self.fields.getvalue("description")

    @property
    def doctypes(self):
        """Sorted names of all the active document types."""

        if not hasattr(self, "_doctypes"):
            self._doctypes = Doctype.list_doc_types(self.session)
        return self._doctypes

    @property
    def group(self):
        """Object for the CDR group being edited/created."""

        if not hasattr(self, "_group"):
            name = self.fields.getvalue("grp")
            if name:
                self._group = self.session.get_group(name)
            else:
                opts = dict(
                    name=self.name,
                    comment=self.comment,
                    session=self.session
                )
                self._group = self.session.Group(**opts)
        return self._group

    @group.setter
    def group(self, value):
        """Allow replacement after a save."""
        self._group = value

    @property
    def members(self):
        """Checkboxes checked from the "user" group."""

        if not hasattr(self, "_members"):
            self._members = self.fields.getlist("user")
        return self._members

    @property
    def name(self):
        """Current value of the form's name field."""
        return self.fields.getvalue("name")

    @property
    def subtitle(self):
        """Dynamic string for display under the main banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.group.name or "Add New Group"
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Provide status information after a save."""
        self._subtitle = value

    @property
    def users(self):
        if not hasattr(self, "_users"):
            self._users = {}
            for name in self.session.list_users():
                self._users[name] = self.session.User(self.session, name=name)
        return self._users

    @staticmethod
    def action_group_name(action):
        """Name the doctype buttons for a specific action.

        Pass:
            action - `Action` object
        """

        return action.name.lower().replace(" ", "_") + "-doctype"


Control().run()
