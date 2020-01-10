#!/usr/bin/env python

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and HTML page creation."""

    FILTER = "name:Help Table of Contents"
    HELP = "CDR Help"

    def show_form(self):
        """Bypass the form."""
        self.show_report()

    def show_report(self):
        """Override to bypass the form/table module."""

        buttons = (
            self.HTMLPage.button(self.SUBMENU),
            self.HTMLPage.button(self.ADMINMENU),
            self.HTMLPage.button(self.LOG_OUT),
        )
        opts = dict(
            buttons=buttons,
            session=self.session,
            action=self.script,
            banner=self.title,
            footer=None,
            subtitle=self.doc.title.split(";")[0],
        )
        page = self.HTMLPage(self.title, **opts)
        for menu_list in self.lists:
            page.body.append(menu_list)
        page.body.set("class", "admin-menu")
        page.send()

    @property
    def lists(self):
        """Nested lists of menu links."""

        if not hasattr(self, "_lists"):
            root = self.doc.filter(self.FILTER).result_tree.getroot()
            self._lists = root.findall("body/ul")
        return self._lists

    @property
    def doc(self):
        """The documentation table of contents document to display."""
        return Doc(self.session, id=self.id)

    @property
    def id(self):
        """ID of the table of contents document to render."""
        return self.fields.getvalue("id", self.default)

    @property
    def default(self):
        """Fallback if an "id" paramater is not present."""

        query = self.Query("query_term", "doc_id")
        query.where("path = '/DocumentationToC/ToCTitle'")
        query.where(f"path = '{self.HELP}'")
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            query = self.Query("query_term", "MIN(doc_id) AS doc_id")
            query.where("path = '/DocumentationToC/ToCTitle'")
            rows = query.execute(self.cursor).fetchall()
            if not rows:
                self.bail("Help system missing")
        return rows[0].doc_id


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
