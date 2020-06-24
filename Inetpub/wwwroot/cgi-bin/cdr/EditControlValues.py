#!/usr/bin/env python

"""Manage the CDR control values.
"""

from json import dumps
import cdr
from cdrcgi import Controller, bail
from cdrapi.db import Query

class Control(Controller):
    """Logic for managing the system control values."""

    SAVE = "Save"
    DELETE = "Delete"
    SHOW = "Show All Values"
    SUBTITLE = "Manage Control Values"
    LOGNAME = "EditControlValues"
    INSTRUCTIONS = (
        "Enter a group or value name (or both) in the New Value block to "
        "override where the value (and its comment) will be stored when "
        "the Save button is clicked."
    )
    URL = "CdrQueries.py?query=Active Control Values&Request=Run"

    def run(self):
        """Override so we can handle some custom commands."""

        if not self.session.can_do("SET_SYS_VALUE"):
            bail("Not authorized to manage control values")
        if self.request == self.SAVE:
            self.save()
        elif self.request == self.DELETE:
            self.inactivate()
        else:
            Controller.run(self)

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
        page.add_script(f"""\
var groups = {self.groups.json};
function check_group() {{
    let group = jQuery("#group option:checked").val();
    console.log("new group is " + group);
    //let name = groups[group]["default"];
    let dropdown = jQuery("#name");
    dropdown.empty();
    let checked = true;
    let options = groups[group].options;
    for (let o in options) {{
        let val = options[o].key;
        let name = options[o].name;
        console.log(name);
        let elem = jQuery("<option></option>").attr("value", val).text(name);
        if (checked) {{
            elem.attr("checked", true);
            dropdown.prop("selectedIndex", 0);
        }}
        checked = false;
        dropdown.append(elem);
    }}
    check_name();
}}
function check_name() {{
    let group = jQuery("#group option:checked").val();
    console.log("check_name(): group="+group);
    let name = jQuery("#name option:checked").val();
    console.log("check_name(): name="+name);
    let values = groups[group].values[name]
    jQuery("#value").val(values.value);
    jQuery("#comment").val(values.comment);
    let lines = (values.value.match(/\\n/g) || "").length + 2;
    if (lines > 50)
        lines = 50;
    jQuery("#value").attr("rows", lines);
}}
jQuery(function() {{
    jQuery("input[value='{self.SHOW}']").click(function() {{
        window.open("{self.URL}", "ControlValues");
    }});
}});""")

        # Customize the display widths, fonts.
        page.add_css("""\
fieldset { width: 800px; }
.labeled-field input,
.labeled-field textarea,
.labeled-field select { width: 650px; }
#value { font-family: Courier; }""")

    def save(self):
        """Save a new or updated control value."""

        group = self.new_group
        if not group and self.group:
            group = self.group.name
        name = self.new_name
        if not name and self.group:
            name = self.group[self.name].name
        if not (group and name):
            bail("Can't save without both a group and a name.")
        args = self.session, group, name, self.value
        opts = dict(comment=self.comment)
        try:
            self.session.tier.set_control_value(*args, **opts)
        except Exception as e:
            bail(str(e))
        if self.new_group or self.new_name:
            self._groups = Groups()
            self._group = self.groups[group.lower()]
            self._name = name.lower()
        self.subtitle = "Value successfully saved"
        self.show_form()

    def inactivate(self):
        """Suppress a value which is no longer needed."""

        group = self.fields.getvalue("group")
        name = self.fields.getvalue("name")
        if not (group and name):
            bail("Nothing to inactivate")
        args = self.session, group, name
        try:
            self.session.tier.inactivate_control_value(*args)
        except Exception as e:
            bail(str(e))
        names = "_group", "_name", "_value", "_comment"
        self._groups = Groups()
        for name in names:
            if hasattr(self, name):
                delattr(self, name)
        self.subtitle = "Value successfully deleted"
        self.show_form()

    @property
    def buttons(self):
        """Supply a customized set of action buttons."""

        return (
            self.SAVE,
            self.DELETE,
            self.SHOW,
            self.DEVMENU,
            self.ADMINMENU,
            self.LOG_OUT,
        )

    @property
    def comment(self):
        """The string value for the current comment."""

        if not hasattr(self, "_comment"):
            if self.request == self.DELETE:
                self._comment = None
            else:
                self._comment = self.fields.getvalue("comment")
            if not self._comment and self.group and self.name:
                self._comment = self.group.values[self.name].comment
        return self._comment

    @property
    def group(self):
        """Tuple of group name and value dictionaries."""

        if not hasattr(self, "_group"):
            self._group = group_name = None
            if self.request != self.DELETE:
                group_name = self.fields.getvalue("group")
            if group_name:
                gkey = group_name.lower()
                self._group = self.groups[gkey]
            if not self._group and self.groups:
                self._group = self.groups.default
        return self._group

    @property
    def groups(self):
        """Dictionary of all active control values."""

        if not hasattr(self, "_groups"):
            self._groups = Groups()
        return self._groups

    @property
    def name(self):
        """Name of the current value."""

        if not hasattr(self, "_name"):
            if self.request == self.DELETE:
                self._name = None
            else:
                self._name = self.fields.getvalue("name")
            if not self._name and self.group and self.group.keys:
                self._name = self.group.keys[0]
        return self._name

    @property
    def new_group(self):
        """Group for which to store a new row in the ctl table."""
        return self.fields.getvalue("new_group", "").strip()

    @property
    def new_name(self):
        """Name for which to store a new row in the ctl table."""
        return self.fields.getvalue("new_name", "").strip()

    @property
    def subtitle(self):
        """String to be displayed under the primary banner."""

        if not hasattr(self, "_subtitle"):
            self.subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Allow the subtitle to be updated dynamically."""
        self._subtitle = value

    @property
    def value(self):
        """Current value string."""

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

    @property
    def options(self):
        """Tuples of value/label suitable for a picklist."""

        if not hasattr(self, "_options"):
            options = []
            for group in self.groups.values():
                options.append((group.key, group.name))
            self._options = sorted(options)
        return self._options

    @property
    def default(self):
        """Group with the first key."""

        if not self.groups:
            return None
        return self.groups[self.keys[0]]

    @property
    def keys(self):
        """Machine names for the groups."""
        return sorted(self.groups)

    @property
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

        @property
        def options(self):
            """Tuples of value/label suitable for a picklist."""

            if not hasattr(self, "_options"):
                options = []
                for value in self.values.values():
                    options.append((value.key, value.name))
                self._options = sorted(options)
            return self._options

        @property
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

        @property
        def key(self):
            """Lowercase version of value name."""

            if not hasattr(self, "_key"):
                self._key = self.name.lower()
            return self._key


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
