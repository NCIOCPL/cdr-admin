#!/usr/bin/env python

"""Edit CDR query term definitions.
"""

from cdrcgi import Controller
from cdrapi.searches import QueryTermDef
from cdrapi.users import Session


class Control(Controller):

    SUBTITLE = "Manage Query Term Definitions"
    TIERS = "PROD", "STAGE", "QA", "DEV"
    COMPARE = "Compare"
    ADD = "Add"
    REMOVE = "Remove"
    LOGNAME = "EditQueryTermDefs"
    MANAGE = "Manage Definitions"

    def run(self):
        """Add some extra routing."""

        try:
            if self.request == self.COMPARE:
                return self.compare()
            elif self.request == self.ADD:
                return self.add()
            elif self.request == self.REMOVE:
                return self.remove()
        except Exception as e:
            self.logger.exception("Failure of %s command", self.request)
            self.bail(e)
        Controller.run(self)

    def populate_form(self, page):
        """Add the fields to the form page.

        Pass:
            page - HTMLPage object to which we add fields
        """

        fieldset = page.fieldset("Choose Tiers and Click the 'Compare' Button")
        opts = dict(options=self.TIERS, default=self.session.tier.name)
        if self.session.tier.name == "PROD":
            default = "DEV"
        fieldset.append(page.select("lower", **opts))
        opts["default"] = "PROD"
        fieldset.append(page.select("upper", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Enter a New Path and Click 'Add'")
        fieldset.set("id", "new-dev")
        fieldset.append(page.text_field("new_path"))
        page.form.append(fieldset)
        legend = "Select Definitions to Delete and Click 'Remove'"
        fieldset = page.fieldset(legend)
        for definition in self.definitions:
            opts = dict(value=definition.path, label=definition.path)
            fieldset.append(page.checkbox("path", **opts))
        page.form.append(fieldset)
        page.add_css("""\
fieldset { width: 1024px; }
.labeled-field select, #new-dev input { width: 874px; }""")

    def compare(self):
        """Compare the definitions on two tiers."""

        session = Session("guest", tier=self.lower)
        lower = set([d.path for d in QueryTermDef.get_definitions(session)])
        session = Session("guest", tier=self.upper)
        upper = set([d.path for d in QueryTermDef.get_definitions(session)])
        buttons = (
            self.HTMLPage.button(self.MANAGE),
            self.HTMLPage.button(self.DEVMENU),
            self.HTMLPage.button(self.ADMINMENU),
            self.HTMLPage.button(self.LOG_OUT),
        )
        opts = dict(
            action=self.script,
            buttons=buttons,
            subtitle=self.subtitle,
            session=self.session,
            method=self.method,
        )
        page = self.HTMLPage(self.title, **opts)
        diffs = False
        only_lower = lower - upper
        only_upper = upper - lower
        if only_lower:
            fieldset = page.fieldset(f"Only on {self.lower}")
            ul = page.B.UL()
            for path in sorted(only_lower, key=str.lower):
                ul.append(page.B.LI(path))
            fieldset.append(ul)
            page.form.append(fieldset)
        if only_upper:
            fieldset = page.fieldset(f"Only on {self.upper}")
            ul = page.B.UL()
            for path in sorted(only_upper, key=str.upper):
                ul.append(page.B.LI(path))
            fieldset.append(ul)
            page.form.append(fieldset)
        if not only_lower and not only_upper:
            p = page.B.P(f"{self.lower} and {self.upper} match.")
            p.set("class", "news info center")
            page.form.append(p)
        page.send()

    def add(self):
        """Add a new definition and re-display the form."""

        if not self.new_path:
            self.bail("No path specified to be added")
        QueryTermDef(self.session, self.new_path).add()
        self.subtitle = "New query term definition successfully added"
        self.show_form()

    def remove(self):
        """Delete the checked paths and re-display the form."""

        if not self.deletions:
            self.bail("No definitions marked for deletion")
        for path in self.deletions:
            QueryTermDef(self.session, path).delete()
        count = len(self.deletions)
        self.subtitle = f"Removed {count} definition(s) successfully"
        self.show_form()

    @property
    def buttons(self):
        """Customize form buttons."""

        return (
            self.COMPARE,
            self.ADD,
            self.REMOVE,
            self.DEVMENU,
            self.ADMINMENU,
            self.LOG_OUT,
        )

    @property
    def definitions(self):
        """Sorted names of the existing query term definitions."""

        if not hasattr(self, "_definitions"):
            self._definitions = QueryTermDef.get_definitions(self.session)
        return self._definitions

    @property
    def deletions(self):
        """Paths marked for removal."""
        return self.fields.getlist("path")

    @property
    def lower(self):
        """Lower tier name for comparing definitions."""
        return self.fields.getvalue("lower")

    @property
    def new_path(self):
        """String for new query term definition to be added."""
        return (self.fields.getvalue("new_path") or "").strip()

    @property
    def subtitle(self):
        """String to be displayed under banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Allow some actions to change this.

        Pass:
            value - replacement string for subtitle
        """

        self._subtitle = value

    @property
    def upper(self):
        """Upper tier name for comparing definitions."""
        if not hasattr(self, "_upper"):
            self._upper = self.fields.getvalue("upper")
            if self._upper == self.lower:
                self.bail(f"Attempt to compare {self.lower} to itself")
        return self._upper


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
