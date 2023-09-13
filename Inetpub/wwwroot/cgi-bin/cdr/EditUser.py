#!/usr/bin/env python

"""Create a new CDR user account or modify an existing one.
"""

from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for editing interface."""

    EDIT_USERS = "EditUsers.py"
    SUBMENU = "User Menu"
    SAVE_CHANGES = "Save Changes"
    SAVE_NEW = "Save New User Account"
    INACTIVATE = "Inactivate Account"
    ELEMENT = "{http://www.w3.org/2001/XMLSchema}element"
    LOGNAME = "EditUser"

    def inactivate(self):
        """Retire the account and return to the parent menu."""
        self.user.delete()
        self.return_to_users_menu(self.user.name)

    def populate_form(self, page):
        """Add the field sets and custom style rules to the page.

        Pass:
            page - HTMLPage object to be filled out
        """

        # Add the account type buttons, driving the rest of the form.
        fieldset = page.fieldset("Account Type")
        opts = dict(value="network", label="Standard CDR Account")
        if self.user.authmode != "local":
            opts["checked"] = True
        opts["tooltip"] = "Uses NIH domain account credentials"
        fieldset.append(page.radio_button("authmode", **opts))
        opts = dict(value="local", label="Local System Account")
        if self.user.authmode == "local":
            opts["checked"] = True
        opts["tooltip"] = "Restricted to scheduled jobs on local CDR Server"
        fieldset.append(page.radio_button("authmode", **opts))
        page.form.append(fieldset)

        # Add the hideable fields for the account password.
        legend = "Password (leave fields blank to keep existing password)"
        if self.user.authmode == "local":
            legend = "Password (required for local accounts)"
        fieldset = page.fieldset(legend)
        fieldset.set("id", "password-fields")
        fieldset.set("class", "text-fields-box")
        fieldset.append(page.password_field("password"))
        fieldset.append(page.password_field("confirm"))
        page.form.append(fieldset)

        # Add the fields for the account's text values.
        page.form.append(page.hidden_field("usr", self.user.name))
        fieldset = page.fieldset("User Account Settings")
        fieldset.set("class", "text-fields-box")
        fieldset.append(page.text_field("name", value=self.user.name))
        fieldset.append(page.text_field("full_name", value=self.user.fullname))
        fieldset.append(page.text_field("office", value=self.user.office))
        fieldset.append(page.text_field("email", value=self.user.email))
        fieldset.append(page.text_field("phone", value=self.user.phone))
        wrapper = page.textarea("comment", value=self.user.comment)
        textarea = wrapper.find("textarea")
        textarea.set("maxlength", "255")
        textarea.set("title", "Maximum number of comment characters is 255.")
        fieldset.append(wrapper)
        page.form.append(fieldset)

        # Add the checkbox fields for the account's group memberships.
        self.logger.debug("groups is %s", self.user.groups)
        fieldset = page.fieldset("Group Membership")
        fieldset.set("id", "group-membership-fields")
        for group in self.groups:
            opts = dict(value=group)
            if self.user.groups and group in self.user.groups:
                opts["checked"] = True
            fieldset.append(page.checkbox("group", **opts))
        page.form.append(fieldset)

        # Add the client-side script to control the password block.
        page.add_script("""\
function check_authmode(mode) {
    switch (mode) {
        case 'local':
            jQuery('#password-fields').show();
            break;
        case 'network':
            jQuery('#password-fields').hide();
            break;
    }
}
jQuery(function() {
    var mode = jQuery("input[name='authmode']:checked").val();
    check_authmode(mode);
});""")

        # Make it easier to see all the groups.
        page.add_css("""\
fieldset { width: 1200px; }
fieldset.text-fields-box input,
fieldset.text-fields-box select,
fieldset.text-fields-box textarea {
    width: 1050px;
}
#group-membership-fields div { width: 300px; float: left; }""")

    def return_to_users_menu(self, deleted=None):
        """Go back to the menu listing all the CDR user accounts."""

        opts = dict(deleted=deleted) if deleted else {}
        self.navigate_to(self.EDIT_USERS, self.session.name, **opts)

    def run(self):
        """Override base class so we can handle the extra buttons."""

        try:
            if self.request == self.INACTIVATE:
                return self.inactivate()
            elif self.request in (self.SAVE_CHANGES, self.SAVE_NEW):
                return self.save()
            elif self.request == self.SUBMENU:
                return self.return_to_users_menu()
        except Exception as e:
            self.bail(f"Failure: {e}")
        Controller.run(self)

    def save(self):
        """Save the new or modified user account object."""

        if not self.name:
            self.bail("Required name is missing")
        if self.user.name:
            self.subtitle = f"Changes to {self.name} saved successfully"
        else:
            self.subtitle = f"New user {self.name} saved successfully"
        opts = dict(
            authmode=self.authmode,
            comment=self.comment,
            email=self.email,
            fullname=self.fullname,
            groups=self.group,
            name=self.name,
            office=self.office,
            phone=self.phone,
        )
        if self.user.id:
            opts["id"] = self.user.id
        if self.authmode == "local":
            if self.password != self.confirm:
                self.bail("Password confirmation mismatch")
            password = self.password or None
            if not self.user.name and not password:
                self.bail("Password required for local system accounts")
        else:
            password = None
        self.user = self.session.User(self.session, **opts)
        self.user.save(password)
        self.show_form()

    @property
    def authmode(self):
        """Get the authmode value from the form field."""
        return self.fields.getvalue("authmode")

    @property
    def buttons(self):
        """Add our custom navigation buttons."""

        if not hasattr(self, "_buttons"):
            self._buttons = [self.SUBMENU, self.ADMINMENU, self.LOG_OUT]
            if self.user.id:
                self._buttons.insert(0, self.INACTIVATE)
                self._buttons.insert(0, self.SAVE_CHANGES)
            else:
                self._buttons.insert(0, self.SAVE_NEW)
        return self._buttons

    @property
    def comment(self):
        """Get the comment value from the form field."""
        return self.fields.getvalue("comment")

    @property
    def confirm(self):
        """Get the confirm value from the form field."""
        return self.fields.getvalue("confirm")

    @property
    def email(self):
        """List of group checkboxes which have been checked."""
        return self.fields.getvalue("email")

    @property
    def fullname(self):
        """Value from the form's full_name field."""
        return self.fields.getvalue("full_name")

    @property
    def group(self):
        """List of group checkboxes which have been checked."""
        return self.fields.getlist("group")

    @property
    def groups(self):
        """Sorted names of all CDR groups."""

        if not hasattr(self, "_groups"):
            self._groups = self.session.list_groups()
        return self._groups

    @property
    def loglevel(self):
        if self.fields.getvalue("debug"):
            return "DEBUG"
        return self.LOGLEVEL

    @property
    def name(self):
        """Value from the form's name field."""
        return self.fields.getvalue("name")

    @property
    def office(self):
        """Value from the form's office field."""
        return self.fields.getvalue("office")

    @property
    def password(self):
        """Get the password value from the form field."""
        return self.fields.getvalue("password")

    @property
    def phone(self):
        """Value from the form's phone field."""
        return self.fields.getvalue("phone")

    @property
    def subtitle(self):
        """Dynamic string for display under the main banner."""

        if not hasattr(self, "_subtitle"):
            name = self.user.fullname or self.user.name
            if name:
                self._subtitle = f"Editing User Account {name}"
            else:
                self._subtitle = "Adding New User Account"
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Provide status information after a save."""
        self._subtitle = value

    @property
    def user(self):
        """Object for the CDR user account being edited/created."""

        if not hasattr(self, "_user"):
            name = self.fields.getvalue("usr")
            self._user = self.session.User(self.session, name=name)
        return self._user

    @user.setter
    def user(self, value):
        """Allow replacement after a save."""
        self._user = value


if __name__ == "__main__":
    """Don't execute the script if we've been loaded as a module."""
    Control().run()
