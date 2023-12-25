#!/usr/bin/env python

"""Edit CDR query term definitions.
"""

from functools import cached_property
from lxml import html
from requests import get
from cdrcgi import Controller
from cdrapi.searches import QueryTermDef
from cdrapi.settings import Tier


class Control(Controller):

    SUBTITLE = "Manage Query Term Definitions"
    TIERS = "PROD", "STAGE", "QA", "DEV"
    COMPARE = "Compare"
    ADD = "Add"
    REMOVE = "Remove"
    LOGNAME = "EditQueryTermDefs"
    MANAGE = "Return To Form"

    def run(self):
        """Add some extra routing."""

        try:
            if self.request == self.COMPARE:
                return self.compare()
            elif self.request == self.ADD:
                return self.add()
            elif self.request == self.REMOVE:
                return self.remove()
            elif self.request == self.MANAGE:
                return self.show_form()
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
            opts["default"] = "DEV"
        fieldset.append(page.select("lower", **opts))
        opts["default"] = "PROD"
        fieldset.append(page.select("upper", **opts))
        page.form.append(fieldset)
        button = page.button(self.COMPARE, onclick=self.SAME_WINDOW)
        page.form.append(button)
        fieldset = page.fieldset("Enter a New Path and Click 'Add'")
        fieldset.set("id", "new-dev")
        fieldset.append(page.text_field("new_path"))
        page.form.append(fieldset)
        button = page.button(self.ADD, onclick=self.SAME_WINDOW)
        page.form.append(button)
        legend = "Select Definitions to Delete and Click 'Remove'"
        fieldset = page.fieldset(legend)
        for definition in self.definitions:
            path = definition.path
            id = path.lower().replace("/", "SLASH").replace("@", "AT")
            id = id.replace(":", "COLON")
            opts = dict(value=path, label=path, widget_id=f"path-{id}")
            fieldset.append(page.checkbox("path", **opts))
        page.form.append(fieldset)
        page.add_css(
            "#submit-button-compare, #submit-button-add {\n"
            "  margin: 1rem 0 3rem;\n"
            "}\n"
        )

    def add(self):
        """Add a new definition and re-display the form."""

        if not self.new_path:
            warning = "No path specified to be added."
            self.alerts.append(dict(message=warning, type="warning"))
        else:
            QueryTermDef(self.session, self.new_path).add()
            message = f"{self.new_path} successfully added."
            self.alerts.append(dict(message=message, type="success"))
        self.show_form()

    def compare(self):
        """Compare the definitions on two tiers."""

        opts = dict(
            action=self.script,
            buttons=[self.MANAGE],
            subtitle=self.subtitle,
            session=self.session,
            method=self.method,
            control=self,
        )
        page = self.HTMLPage(self.title, **opts)
        lower = self.fetch_definitions(self.lower)
        upper = self.fetch_definitions(self.upper)
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
            for path in sorted(only_upper, key=str.lower):
                ul.append(page.B.LI(path))
            fieldset.append(ul)
            page.form.append(fieldset)
        if not only_lower and not only_upper:
            p = page.B.P(f"{self.lower} and {self.upper} match.")
            p.set("class", "news info center")
            page.form.append(p)
        button = page.button(self.MANAGE, onclick=self.SAME_WINDOW)
        page.form.append(button)
        page.send()

    def fetch_definitions(self, tier):
        """Get a set of query term definition paths for a tier.

        Required positional argument:
          tier - string naming the source for the definitions

        Return:
          set of strings for the query term definitions for the tier
        """

        host = Tier(tier.upper()).hosts["APPC"]
        url = f"https://{host}/cgi-bin/cdr/EditQueryTermDefs.py"
        response = get(url, verify=False)
        if not response.ok:
            self.bail(f"Failure loading {tier} definitions: {response.reason}")
        definitions = []
        try:
            root = html.fromstring(response.content)
            labels = root.xpath("//fieldset/div/label")
            for label in labels:
                if label.get("for", "").startswith("path-"):
                    definition = label.text
                    if definition:
                        definitions.append(definition.strip())
        except Exception as e:
            self.logger.exception("failure parsing definitions")
            self.bail(f"Failure parsing definitions: {e}")
        return set(definitions)

    def remove(self):
        """Delete the checked paths and re-display the form."""

        if not self.deletions:
            warning = "No definitions marked for deletion."
            self.alerts.append(dict(message=warning, type="warning"))
        else:
            for path in self.deletions:
                QueryTermDef(self.session, path).delete()
                message = f"{path} successfully removed."
                self.alerts.append(dict(message=message, type="success"))
        self.show_form()

    @cached_property
    def buttons(self):
        """Customize form buttons."""
        return [self.REMOVE]

    @cached_property
    def definitions(self):
        """Sorted names of the existing query term definitions."""
        return QueryTermDef.get_definitions(self.session)

    @cached_property
    def deletions(self):
        """Paths marked for removal."""
        return self.fields.getlist("path")

    @cached_property
    def lower(self):
        """Lower tier name for comparing definitions."""
        return self.fields.getvalue("lower")

    @cached_property
    def new_path(self):
        """String for new query term definition to be added."""
        return (self.fields.getvalue("new_path") or "").strip()

    @cached_property
    def same_window(self):
        """Reduce the number of new browser tabs created."""
        return self.ADD, self.REMOVE, self.MANAGE, self.COMPARE

    @cached_property
    def upper(self):
        """Upper tier name for comparing definitions."""

        upper = self.fields.getvalue("upper")
        if upper == self.lower:
            self.bail(f"Attempt to compare {self.lower} to itself")
        return upper


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
