#!/usr/bin/env python

"""Manage the CDR control values.
"""

from functools import cached_property
from json import dumps
from cdrcgi import Controller
from cdrapi.db import Query


class Control(Controller):
    """Logic for managing the system control values."""

    SAVE = "Save"
    DELETE = "Delete"
    JSON = "JSON"
    SHOW = "Show All Values"
    SUBTITLE = "Manage Control Values"
    LOGNAME = "EditControlValues"
    INSTRUCTIONS = (
        "Enter a group or value name (or both) in the New Value block to "
        "override where the value (and its comment) will be stored when "
        "the Save button is clicked."
    )
    URL = "CdrQueries.py?query=Active Control Values&Request=Run"

    def inactivate(self):
        """Suppress a value which is no longer needed."""

        group = self.fields.getvalue("group")
        name = self.fields.getvalue("name")
        if not (group and name):
            message = "Nothing to inactivate."
            return self.alerts.append(dict(message=message, type="warning"))
        args = self.session, group, name
        try:
            self.session.tier.inactivate_control_value(*args)
        except Exception as e:
            self.logger.exception("Control deletion failure")
            return self.alerts.append(dict(message=str(e), type="error"))
        self.groups = Groups()
        for name in "_group", "_name", "_value", "_comment":
            if hasattr(self, name):
                delattr(self, name)
        message = "Value successfully dropped."
        self.alerts.append(dict(message=message, type="success"))
        self.show_form()

    def json(self):
        """Send the serialized active values to the client."""
        self.send_page(self.groups.json, "json")

    def populate_form(self, page):
        """Add the field groups to the tool's form.

        Pass:
            page - HTMLPage object to which we attach fields
        """

        # Show the user the instructions for creating new control values.
        fieldset = page.fieldset("Instructions")
        fieldset.set("id", "instruction-block")
        classes = "info center"
        fieldset.append(page.B.P(self.INSTRUCTIONS, page.B.CLASS(classes)))
        page.form.append(fieldset)

        # Add the fields for creating a new value.
        fieldset = page.fieldset("New Value")
        tip = "Group will be created if necessary"
        fieldset.append(page.text_field("new_group", label="Group", title=tip))
        tip = "Group/Name combination must not already exist"
        fieldset.append(page.text_field("new_name", label="Name", title=tip))
        page.form.append(fieldset)

        # Add the fields for editing the existing control values.
        fieldset = page.fieldset("Control Value")
        opts = dict(options=self.groups.options, onchange="check_group()")
        if self.group:
            opts["default"] = self.group.key
        fieldset.append(page.select("group", **opts))
        options = self.group.options if self.group else []
        opts = dict(
            options=options,
            default=self.name,
            onchange="check_name()"
        )
        fieldset.append(page.select("name", **opts))
        fieldset.append(page.textarea("value", value=self.value, rows=5))
        fieldset.append(page.textarea("comment", value=self.comment, rows=5))
        page.form.append(fieldset)

        # Add some fancy client-side scripting.
        page.add_script(f"const groups = {self.groups.json};")
        page.head.append(page.B.SCRIPT(src="/js/EditControlValues.js"))

        # Customize the fonts.
        page.add_css("#value { font-family: Courier; }")

    def run(self):
        """Override so we can handle some custom commands."""

        if not self.session.can_do("SET_SYS_VALUE"):
            self.bail("Not authorized to manage control values")
        try:
            if self.request == self.SHOW:
                params = dict(query="Active Control Values", Request="Run")
                self.redirect("CdrQueries.py", **params)
            if self.request == self.SAVE:
                return self.save()
            elif self.request == self.DELETE:
                return self.inactivate()
            elif self.request == self.JSON:
                return self.json()
        except Exception as e:
            self.logger.exception("Control value editing failure")
            self.bail(e)
        Controller.run(self)

    def save(self):
        """Save a new or updated control value."""

        group = self.new_group
        if not group and self.group:
            group = self.group.name
        name = self.new_name
        if not name and self.group:
            name = self.group[self.name].name
        if not (group and name):
            message = "Can't save without both a group and a name."
            return self.alerts.append(dict(message=message, type="warning"))
        args = self.session, group, name, self.value
        opts = dict(comment=self.comment)
        try:
            self.session.tier.set_control_value(*args, **opts)
        except Exception as e:
            self.logger.exception("Control save failure")
            return self.alerts.append(dict(message=str(e), type="error"))
        self.groups = Groups()
        self._group = self.groups[group.lower()]
        self._name = name.lower()
        message = "Value successfully saved."
        self.alerts.append(dict(message=message, type="success"))
        self.show_form()

    @cached_property
    def buttons(self):
        """Supply a customized set of action buttons."""
        return self.SAVE, self.DELETE, self.JSON, self.SHOW

    @property
    def comment(self):
        """The string value for the current comment.

        The manual caching is deliberate. Don't use @cached_property.
        """

        if not hasattr(self, "_comment"):
            if self.request == self.DELETE:
                self._comment = None
            else:
                self._comment = self.fields.getvalue("comment", "").strip()
            if self.request == self.SAVE:
                return self._comment
            if not self._comment and self.group and self.name:
                self._comment = self.group.values[self.name].comment
        return self._comment

    @property
    def group(self):
        """Tuple of group name and value dictionaries.

        The manual caching is deliberate. Don't use @cached_property.
        """

        if not hasattr(self, "_group"):
            self._group = group_name = None
            if self.request != self.DELETE:
                group_name = self.fields.getvalue("group")
            if group_name:
                key = group_name.lower()
                self._group = self.groups[key]
            if not self._group and self.groups:
                self._group = self.groups.default
        return self._group

    @cached_property
    def groups(self):
        """Dictionary of all active control values."""
        return Groups()

    @property
    def name(self):
        """Name of the current value.

        The manual caching is deliberate. Don't use @cached_property.
        """

        if not hasattr(self, "_name"):
            if self.request == self.DELETE:
                self._name = None
            else:
                self._name = self.fields.getvalue("name")
            if not self._name and self.group and self.group.keys:
                self._name = self.group.keys[0]
        return self._name

    @cached_property
    def new_group(self):
        """Group for which to store a new row in the ctl table."""
        return self.fields.getvalue("new_group", "").strip()

    @cached_property
    def new_name(self):
        """Name for which to store a new row in the ctl table."""
        return self.fields.getvalue("new_name", "").strip()

    @cached_property
    def same_window(self):
        """Avoid opening a new tab for these commands."""
        return "Save", "Delete"

    @property
    def value(self):
        """Current value string.

        The manual caching is deliberate. Don't use @cached_property.
        """

        if not hasattr(self, "_value"):
            if self.request == self.DELETE:
                self._value = None
            else:
                self._value = self.fields.getvalue("value")
            if self._value is None and self.group and self.name:
                self._value = self.group.values[self.name].value
        return self._value


class Groups:
    """All the control values in the system."""

    def __init__(self):
        """Assemble the dictionary of all control value groups."""

        groups = {}
        query = Query("ctl", "grp", "name", "val", "comment")
        query.where("inactivated IS NULL")
        for row in query.execute().fetchall():
            key = row.grp.lower()
            group = groups.get(key)
            if group is None:
                group = groups[key] = self.Group(row.grp, key)
            value = self.Value(row.name, row.val, row.comment)
            group.values[value.key] = value
        self.groups = groups

    @cached_property
    def options(self):
        """Tuples of value/label suitable for a picklist."""

        options = []
        for group in self.groups.values():
            options.append((group.key, group.name))
        return sorted(options)

    @cached_property
    def default(self):
        """Group with the first key."""
        return self.groups[self.keys[0]] if self.groups else None

    @cached_property
    def json(self):
        """Convert the object to a format usable by client-side scripting."""

        groups = {}
        for group in self.groups.values():
            values = {}
            for v in group.values.values():
                values[v.key] = dict(value=v.value, comment=v.comment)
            options = [dict(key=opt[0], name=opt[1]) for opt in group.options]
            groups[group.key] = dict(options=options, values=values)
        return dumps(groups, indent=2)

    @cached_property
    def keys(self):
        """Machine names for the groups."""
        return sorted(self.groups)

    def __len__(self):
        """Support boolean testing."""
        return len(self.groups)

    def __getitem__(self, key):
        """Make finding a group easier."""
        return self.groups.get(key)

    class Group:
        def __init__(self, name, key):
            """Capture the caller's values."""

            self.name = name
            self.key = key
            self.values = {}

        @cached_property
        def options(self):
            """Tuples of value/label suitable for a picklist."""

            options = []
            for value in self.values.values():
                options.append((value.key, value.name))
            return sorted(options)

        @cached_property
        def keys(self):
            """Canonical names for the values."""
            return sorted(self.values)

        def __getitem__(self, name):
            """Make the object more dictionary-like."""
            return self.values.get(name)

    class Value:
        """Named value in a group."""

        def __init__(self, name, value, comment):
            """Capture the caller's values."""

            self.name = name
            self.value = value
            self.comment = comment

        @cached_property
        def key(self):
            """Lowercase version of value name."""
            return self.name.lower()


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
