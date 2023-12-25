#!/usr/bin/env python

"""Report on invalid or blocked CDR documents.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Invalid Documents"

    def build_tables(self):
        """Assemble the two tables used for this report."""

        if not self.doctype:
            message = "No document type has been selected."
            self.alerts.append(dict(message=message, type="warning"))
            return self.show_form()
        subquery = self.Query("doc_version", "MAX(num)").where("id = v.id")
        fields = "v.id", "v.title", "d.active_status"
        query = self.Query("doc_version v", *fields).order("v.id")
        query.join("document d", "d.id = v.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.id", self.doctype))
        query.where(query.Condition("v.num", subquery))
        query.where("v.val_status = 'I'")
        invalid = []
        blocked = []
        for doc in query.execute(self.cursor).fetchall():
            row = (self.Reporter.Cell(doc.id, classes="right"), doc.title)
            if doc.active_status == "I":
                blocked.append(row)
            else:
                invalid.append(row)
        doctype = dict(self.doctypes)[int(self.doctype)]
        caption = f"Invalid {doctype} Documents"
        opts = dict(columns=self.columns, caption=caption)
        invalid = self.Reporter.Table(invalid, **opts)
        opts["caption"] = f"Blocked {doctype} Documents"
        blocked = self.Reporter.Table(blocked, **opts)
        return invalid, blocked

    def populate_form(self, page):
        """Let the user pick a document type.

        Pass:
            page - HTMLPage document on which to drop the fields
        """

        fieldset = page.fieldset("Select Document Type")
        for id, name in self.doctypes:
            opts = dict(value=id, label=name)
            fieldset.append(page.radio_button("doctype", **opts))
        page.form.append(fieldset)

    @cached_property
    def columns(self):
        """Column headers for the report."""

        return (
            self.Reporter.Column("ID", width="50px"),
            self.Reporter.Column("Title", width="950px"),
        )

    @cached_property
    def doctype(self):
        """CDR document type selected for the report."""
        return self.fields.getvalue("doctype")

    @cached_property
    def doctypes(self):
        """Active document types for the form's picklist."""

        query = self.Query("doc_type", "id", "name").order("name")
        query.where("active = 'Y'")
        query.where("xml_schema IS NOT NULL")
        query.where("name NOT IN ('Filter', 'xxtest', 'schema')")
        rows = query.execute(self.cursor).fetchall()
        return [tuple(row) for row in rows]

    @cached_property
    def same_window(self):
        """Don't open more than one new browser tab."""
        return [self.SUBMIT] if self.request else []


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
