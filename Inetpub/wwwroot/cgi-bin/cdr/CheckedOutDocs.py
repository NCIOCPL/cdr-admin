#!/usr/bin/env python

"""Report on documents checked out to a user.
"""

from cdrcgi import Controller, Reporter
from cdrapi.db import Query


class Control(Controller):

    SUBTITLE = "Checked Out Documents"
    COLUMNS = (
        Reporter.Column("Checked Out", width="140px"),
        Reporter.Column("Type", width="150px"),
        Reporter.Column("CDR ID", width="70px"),
        Reporter.Column("Document Title", width="700px"),
    )

    def populate_form(self, page):
        """Show the form fields iff there are any locked documents."""
        if self.lockers:
            fieldset = page.fieldset("Select User")
            page.form.append(fieldset)
            field = page.select("User", options=self.lockers)
            field.find("select").set("autofocus")
            fieldset.append(field)
            page.add_output_options("html")
        else:
            page.form.append(page.B.P("No CDR documents are locked."))
            submit = page.body.xpath("//input[@value='Submit']")
            submit.getparent().remove(submit)

    def run(self):
        """Bypass the Submit button if we already have a user."""
        if not self.request and self.user:
            self.show_report()
        else:
            Controller.run(self)

    @property
    def lockers(self):
        """Get sequence of id/name pairs for users with locked documents."""
        if not hasattr(self, "_lockers"):
            fields = "COUNT(*) AS n", "u.id", "u.name", "u.fullname"
            query = Query("usr u", *fields)
            query.join("checkout c", "c.usr = u.id")
            query.join("document d", "d.id = c.id")
            query.group(*fields[1:])
            query.where("c.dt_in IS NULL")
            users = []
            for row in query.execute(self.cursor):
                name = row.fullname or row.name
                display = f"{name} ({row.n} locks)"
                users.append((name.lower(), row.id, display))
            self._lockers = [(uid, label) for key, uid, label in sorted(users)]
        return self._lockers

    @property
    def user(self):
        """Get the subject of the report.

        This report can be invoked from the web admin menus, where the
        form has the user ID, and from XMetaL, which passes the user
        name instead. We have to be able to handle both.
        """

        if not hasattr(self, "_user"):
            self._user = None
            value = self.fields.getvalue("User")
            if value:
                if value.isdigit():
                    opts = dict(id=int(value))
                else:
                    opts = dict(name=value)
                self._user = self.session.User(self.session, **opts)
        return self._user

    def build_tables(self):
        """Show the documents the user has locked."""
        fields = "c.dt_out", "t.name", "d.id", "d.title"
        query = Query("usr u", *fields).order(*fields[:3])
        query.join("checkout c", "c.usr = u.id")
        query.join("document d", "d.id = c.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("c.dt_in IS NULL")
        query.where(query.Condition("u.id", self.user.id))
        rows = []
        for dt_out, doc_type, doc_id, title in query.execute(self.cursor):
            doc_id = Reporter.Cell(doc_id, center=True)
            rows.append([str(dt_out)[:19], doc_type, doc_id, title])
        caption = f"Checked out by {self.user.fullname or self.user.name}"
        return Reporter.Table(rows, caption=caption, columns=self.COLUMNS)


Control().run()
