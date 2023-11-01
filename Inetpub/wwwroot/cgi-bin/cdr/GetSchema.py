#!/usr/bin/env python

"""Show the raw XML for a CDR schema document.
"""

import sys
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Script logic."""

    SUBMIT = None
    SUBTITLE = "Show Schema"

    def run(self):
        """Override router."""

        if self.id:
            sys.stdout.buffer.write(b"Content-type: text/plain;charset=utf-8")
            sys.stdout.buffer.write(b"\n\n")
            sys.stdout.buffer.write(self.doc.xml.encode("utf-8"))
            sys.exit(0)
        Controller.run(self)

    def populate_form(self, page):
        """If we don't have an ID, show the form as a menu.

        Pass:
            page - HTMLPage object to be populated
        """

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Schemas")
        fieldset.set("id", "schema-list")
        ul = page.B.UL()
        script = self.script
        for schema in self.schemas:
            link = page.menu_link(script, schema.name, id=schema.id)
            link.set("target", "_blank")
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css("""
#schema-list ul { list-style-type: none; column-width: 15rem; }
#schema-list a { text-decoration: none; }
""")
        # page.add_css(".flexlinks ul { height: 400px; }")

    @property
    def doc(self):
        """Document whose XML we will display."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.session, id=self.id)
        return self._doc

    @property
    def id(self):
        """ID of schema document to be displayed."""
        return self.fields.getvalue("id")

    @property
    def schemas(self):
        """Sorted sequence of `Schema` objects for the menu."""

        if not hasattr(self, "_schemas"):
            query = self.Query("document d", "d.id", "d.title").order(2)
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'Schema'")

            class Schema:
                def __init__(self, row):
                    self.id = row.id
                    self.name = row.title.replace(".xml", "")
            self._schemas = [Schema(row) for row in query.execute(self.cursor)]
        return self._schemas


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
