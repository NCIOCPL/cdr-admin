#!/usr/bin/env python

"""Main menu for advanced search forms.
"""

from cdrapi import db
from cdrcgi import Controller


class Control(Controller):
    SUBTITLE = "CDR Documentation"
    SUBMIT = None

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("Documentation Categories"))
        ol = page.B.OL()
        page.form.append(ol)
        query = db.Query("query_term", "doc_id", "value").order("value")
        query.where("path = '/DocumentationToC/ToCTitle'")
        for row in query.execute(self.cursor).fetchall():
            link = page.menu_link("Help.py", row.value, id=row.doc_id)
            ol.append(page.B.LI(link))


Control().run()
