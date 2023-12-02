#!/usr/bin/env python

"""Form for editing named CDR filter sets.
"""

from functools import cached_property
from json import loads
from cdrcgi import Controller
from cdrapi.docs import FilterSet


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
            self.bail("You are not authorized to use this page")
        try:
            request = self.request or self.fields.getvalue("action")
            if request == self.SAVE:
                return self.save()
            elif self.request == self.DELETE:
                return self.delete()
            elif self.request == self.SETS:
                self.navigate_to(self.EDIT_SETS, self.session.name)
        except Exception as e:
            self.logger.exception("Failure")
            self.bail(str(e))
        Controller.run(self)

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object to be modified
        """

        # Capture information in fields behind the scenes.
        page.form.append(page.hidden_field("members", ""))
        page.form.append(page.hidden_field("action", ""))
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
            message = "Saved set {} ({}) with {} members".format(*args)
            if self.set.id and self.set.name != filter_set.name:
                message += f" (name changed from {self.set.name})"
            self.alerts.append(dict(message=message, type="success"))
        except Exception as e:
            self.logger.exception("failure saving %s", self.name)
            self.bail(str(e))
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
            self.bail(str(e))
        self.navigate_to(self.EDIT_SETS, self.session.name, deleted=name)

    @cached_property
    def buttons(self):
        """Create custom action list (this isn't a report)."""

        if self.set.id:
            return [self.SAVE, self.DELETE, self.SETS]
        return [self.SAVE, self.SETS]

    @cached_property
    def description(self):
        """Short description string (from the editing form)."""
        return self.fields.getvalue("description")

    @cached_property
    def filter_list(self):
        """HTML ul object for the filter docs which can be made members."""

        items = []
        for doc in sorted(self.filters.values()):
            items.append(self.B.LI(doc.title, self.B.CLASS("filter")))
        return self.B.UL(*items, id="filters")

    @cached_property
    def filters(self):
        """Dictionary of `Doc` objects, indexed by normalized titles."""

        filters = {}
        for doc in FilterSet.get_filters(self.session):
            key = doc.title.lower().strip()
            filters[key] = doc
        return filters

    @cached_property
    def member_list(self):
        """HTML ul element for the filter set's members."""

        items = []
        for member in self.set.members:
            if isinstance(member, FilterSet):
                member_class = "set"
                label = member.name
            else:
                member_class = "filter"
                label = member.title
            items.append(self.B.LI(label, self.B.CLASS(member_class)))
        return self.B.UL(*items, id="members")

    @cached_property
    def members(self):
        """Ordered sequence of selected FilterSet and/or Doc objects."""

        members = []
        json = self.fields.getvalue("members")
        self.logger.info("member json is %s", json)
        for member in loads(json):
            types = member["type"].split()
            name = member["name"]
            key = name.lower().strip()
            if "filter" in types:
                members.append(self.filters[key])
            elif "set" in types:
                members.append(self.sets[key])
            else:
                message = "unrecognized type for member: %s"
                self.logger.warning(message, member)
        return members

    @cached_property
    def notes(self):
        """Extended information about the set (from the form)."""
        return self.fields.getvalue("notes") or None

    @cached_property
    def name(self):
        """Editable set name value from the form."""
        return self.fields.getvalue("name")

    @property
    def same_window(self):
        """Don't create new browser tabs."""
        return self.buttons

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

    @cached_property
    def set_list(self):
        """HTML ul object for the filter sets which can be made members."""

        items = []
        for filter_set in sorted(self.sets.values()):
            items.append(self.B.LI(filter_set.name, self.B.CLASS("set")))
        return self.B.UL(*items, id="sets")

    @cached_property
    def sets(self):
        """Dictionary of `FilterSet` objects, indexed by normalized names."""

        sets = {}
        for id, name in FilterSet.get_filter_sets(self.session):
            key = name.lower().strip()
            sets[key] = FilterSet(self.session, id=id, name=name)
        return sets


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
