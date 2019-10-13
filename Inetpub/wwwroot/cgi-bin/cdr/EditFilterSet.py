#!/usr/bin/env python

"""Form for editing named CDR filter sets.
"""

from json import loads
from cdrcgi import Controller, bail, navigateTo
from cdrapi.docs import Doc, FilterSet

class Control(Controller):
    """Processing control logic for managing filter sets."""

    SUBTITLE = "Edit Filter Set"
    LOGNAME = "EditFilterSet"
    SAVE = "Save Set"
    SETS = "Manage Filter Sets"
    EDIT_SETS = "EditFilterSets.py"
    DELETE = "Delete Set"
    JS = "/js/EditFilterSet.js"
    CSS = "/stylesheets/EditFilterSet.css"
    from lxml.html import builder as B
    INSTRUCTIONS = (
        "Drag filters or sets into the Members box to add them to the set.",
        "Drag members within the box to re-order them.",
        "Drag members out of the box to remove them from the set.",
        "Double-click filters or sets to append them to the set.",
        "Double-click members to remove them from the set.",
        "If you change the name, adjust the sets which include this one!",
    )

    def run(self):
        """Handle our custom actions."""

        if not self.session.can_do("MODIFY FILTER SET"):
            bail("You are not authorized to use this page")
        try:
            if self.request == self.SAVE:
                return self.save()
            elif self.request == self.DELETE:
                return self.delete()
            elif self.request == self.SETS:
                navigateTo(self.EDIT_SETS, self.session.name)
        except Exception as e:
            self.logger.exception("Failure")
            bail(str(e))
        Controller.run(self)

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object to be modified
        """

        # Capture information in fields behind the scenes.
        page.form.append(page.hidden_field("members", ""))
        page.form.append(page.hidden_field("id", self.set.id))

        # Explain how to use the tool.
        fieldset = page.fieldset("Instructions")
        br = None
        lines = []
        for line in self.INSTRUCTIONS:
            if br is not None:
                lines.append(br)
            br = page.B.BR()
            lines.append(f"\u261e {line}")
        fieldset.append(page.B.P(*lines, page.B.CLASS("info")))
        page.form.append(fieldset)

        # Add the regular text-based fields.
        fieldset = page.fieldset("Properties")
        fieldset.append(page.text_field("name", value=self.set.name))
        opts = dict(value=self.set.description)
        fieldset.append(page.text_field("description", **opts))
        fieldset.append(page.textarea("notes", value=self.set.notes))

        # Add the draggable widgets for set membership management.
        # These are not fields, but are tracked by client-side scripting
        # to populate the hidden 'members' field at save time.
        page.form.append(fieldset)
        fieldset = page.fieldset("Put Your Set Members Here")
        fieldset.append(self.member_list)
        page.form.append(fieldset)
        fieldset = page.fieldset("Filters You Can Drag To Your Filter Set")
        fieldset.append(self.filter_list)
        page.form.append(fieldset)
        fieldset = page.fieldset("Filter Sets You Can Drag To Your Set")
        fieldset.append(self.set_list)
        page.form.append(fieldset)

        # Add the magic.
        page.head.append(page.B.SCRIPT(src=self.JS))
        page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))

    def save(self):
        """Save the new or modified filter set."""

        original_name = self.set.name
        opts = dict(
            name=self.name,
            description=self.description,
            notes=self.notes,
            members=self.members,
        )
        if self.set.id:
            opts["id"] = self.set.id
        filter_set = FilterSet(self.session, **opts)
        try:
            filter_set.save()
            args = filter_set.id, filter_set.name, len(filter_set.members)
            self.subtitle = "Saved set {} ({}) with {} members".format(*args)
            if self.set.id and self.set.name != filter_set.name:
                self.subtitle += f" (name changed from {self.set.name})"
        except Exception as e:
            self.logger.exception("failure saving %s", self.name)
            bail(str(e))
        self._set = filter_set
        self.show_form()

    def delete(self):
        """Delete the current filter set and navigate back to the sets."""

        filter_set = FilterSet(self.session, id=self.set.id)
        name = filter_set.name
        try:
            filter_set.delete()
        except Exception as e:
            self.logger.exception("failure deleting %s", self.set.name)
            bail(str(e))
        navigateTo(self.EDIT_SETS, self.session.name, deleted=name)

    @property
    def buttons(self):
        """Create custom action list (this isn't a report)."""

        buttons = [
            self.SAVE,
            self.SETS,
            self.DEVMENU,
            self.ADMINMENU,
            self.LOG_OUT,
        ]
        if self.set.id:
            buttons.insert(1, self.DELETE)
        return buttons

    @property
    def description(self):
        """Short description string (from the editing form)."""

        if not hasattr(self, "_description"):
            self._description = self.fields.getvalue("description")
        return self._description

    @property
    def filter_list(self):
        """HTML ul object for the filter docs which can be made members."""

        if not hasattr(self, "_filter_list"):
            items = []
            for doc in sorted(self.filters.values()):
                items.append(self.B.LI(doc.title, self.B.CLASS("filter")))
            self._filter_list = self.B.UL(*items)
            self._filter_list.set("id", "filters")
        return self._filter_list

    @property
    def filters(self):
        """Dictionary of `Doc` objects, indexed by normalized titles."""

        if not hasattr(self, "_filters"):
            docs = FilterSet.get_filters(self.session)
            self._filters = {}
            for doc in docs:
                key = doc.title.lower().strip()
                self._filters[key] = doc
        return self._filters

    @property
    def member_list(self):
        """HTML ul element for the filter set's members."""

        if not hasattr(self, "_member_list"):
            items = []
            for member in self.set.members:
                if isinstance(member, FilterSet):
                    member_class = "set"
                    label = member.name
                else:
                    member_class = "filter"
                    label = member.title
                li = self.B.LI(label, self.B.CLASS(member_class))
                items.append(li)
            self._member_list = self.B.UL(*items)
            self._member_list.set("id", "members")
        return self._member_list

    @property
    def members(self):
        """Ordered sequence of selected FilterSet and/or Doc objects."""

        if not hasattr(self, "_members"):
            self._members = []
            members = self.fields.getvalue("members")
            self.logger.info("members are %s", members)
            for member in loads(members):
                types = member["type"].split()
                name = member["name"]
                key = name.lower().strip()
                if "filter" in types:
                    self._members.append(self.filters[key])
                elif "set" in types:
                    self._members.append(self.sets[key])
                else:
                    message = "unrecognized type for member: %s"
                    self.logger.warning(message, member)
        return self._members

    @property
    def notes(self):
        """Extended information about the set (from the form)."""
        return self.fields.getvalue("notes")

    @property
    def name(self):
        """Editable set name value from the form."""

        if not hasattr(self, "_name"):
            self._name = self.fields.getvalue("name")
        return self._name

    @property
    def set(self):
        """Instantiate an object for the set we are editing."""

        if not hasattr(self, "_set"):
            id = self.fields.getvalue("id")
            if id:
                self._set = FilterSet(self.session, id=id)
            else:
                self._set = FilterSet(self.session)
        return self._set

    @set.setter
    def set(self, value):
        """Allow save() to refresh the set object."""
        self._set = value

    @property
    def set_list(self):
        """HTML ul object for the filter sets which can be made members."""

        if not hasattr(self, "_set_list"):
            items = []
            for filter_set in sorted(self.sets.values()):
                items.append(self.B.LI(filter_set.name, self.B.CLASS("set")))
            self._set_list = self.B.UL(*items)
            self._set_list.set("id", "sets")
        return self._set_list

    @property
    def sets(self):
        """Dictionary of `FilterSet` objects, indexed by normalized names."""
        if not hasattr(self, "_sets"):
            self._sets = {}
            for id, name in FilterSet.get_filter_sets(self.session):
                key = name.lower().strip()
                self._sets[key] = FilterSet(self.session, id=id, name=name)
        return self._sets

    @property
    def subtitle(self):
        """String to be displayed under the main banner."""

        if hasattr(self, "_subtitle"):
            return self._subtitle
        return self.SUBTITLE

    @subtitle.setter
    def subtitle(self, value):
        """Make this value modifiable on the fly."""
        self._subtitle = value


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
