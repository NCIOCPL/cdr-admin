#!/usr/bin/env python

"""Report on the history of mailers for a particular document.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Report logic."""

    SUBTITLE = "Mailer History"
    FIELDS = (
        "t.value AS type",
        "s.value AS sent",
        "r.value AS received",
        "c.value AS change",
        "d.doc_id AS mailer_id"
    )

    def populate_form(self, page):
        """Add a field for the document ID.

        Pass:
            page - HTMLPage object on which to place the field
        """

        fieldset = page.fieldset("Select CDR Document for Report")
        fieldset.append(page.text_field("id", label="Document ID"))
        page.form.append(fieldset)

    def build_tables(self):
        """Show the mailer history for the selected document."""
        if not self.id:
            self.show_form()
        query = self.Query("query_term d", *self.FIELDS).order("s.value")
        query.where("d.path = '/Mailer/Document/@cdr:ref'")
        query.where(query.Condition("d.int_val", self.doc.id))
        query.join("query_term t", "t.doc_id = d.doc_id")
        query.where("t.path = '/Mailer/Type'")
        query.join("query_term s", "s.doc_id = d.doc_id")
        query.where("s.path = '/Mailer/Sent'")
        query.outer("query_term r", "r.doc_id = d.doc_id",
                    "r.path = '/Mailer/Response/Received'")
        query.outer("query_term c", "c.doc_id = r.doc_id",
                    "c.path = '/Mailer/Response/ChangesCategory'",
                    "LEFT(c.node_loc, 4) = LEFT(r.node_loc, 4)")
        rows = []
        for row in query.execute(self.cursor).fetchall():
            rows.append([
                self.Reporter.Cell(f"CDR{row.mailer_id:010d}", center=True),
                row.type,
                self.Reporter.Cell(row.sent.split("T")[0], center=True),
                self.Reporter.Cell(row.received, center=True),
                row.change,
            ])
        if not rows:
            return []
        cols = (
            self.Reporter.Column("Mailer ID", width="125px"),
            self.Reporter.Column("Mailer Type", width="300px"),
            self.Reporter.Column("Sent", width="85px"),
            self.Reporter.Column("Checked In", width="75px"),
            self.Reporter.Column("Change Category", width="200px"),
        )
        try:
            caption = self.doc.title
        except:
            self.bail("Invalid document ID {self.id!r}")
        return self.Reporter.Table(rows, cols=cols, caption=caption)

    @property
    def id(self):
        """Document ID pulled from the form field."""
        return self.fields.getvalue("id")

    @property
    def doc(self):
        """Document on which to report."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.session, id=self.id)
        return self._doc

    @property
    def subtitle(self):
        """Customize the string displayed under the main banner."""

        if self.request == "Submit":
            return f"Mailer History for {self.doc.cdr_id}"
        return self.SUBTITLE


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
