#!/usr/bin/env python

"""Audit Trail report requested by Lakshmi.
"""

from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Audit Trail"
    OPTIONS = (
        ("blocking", "Include blocking/unblocking actions"),
        ("comments", "Include comments"),
        ("order-ascending", "Show oldest actions first"),
    )

    def build_tables(self):
        """Callback invoked by show_report()."""
        return [self.table] if self.doc else self.show_form()

    def populate_form(self, page):
        """Ask for a document ID if we didn't get one already."""

        if self.doc:
            return self.show_report()
        fieldset = page.fieldset("Report Request")
        fieldset.append(page.text_field("id"))
        fieldset.append(page.text_field("rows", value=150))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optional Inclusions")
        for value, label in self.OPTIONS:
            fieldset.append(page.checkbox("opts", label=label, value=value))
        page.form.append(fieldset)

    @cached_property
    def doc(self):
        """The subject of the report."""

        doc_id = self.fields.getvalue("id", "").strip()
        if doc_id:
            doc = Doc(self.session, id=doc_id)
            if doc.title is None:
                message = f"Document {doc_id} was not found."
                self.alerts.append(dict(message=message, type="warning"))
                return None
            return doc
        if self.request:
            message = "Document ID is required."
            self.alerts.append(dict(message=message, type="error"))
        return None

    @cached_property
    def actions(self):
        """Information pulled from the audit trail."""

        fields = [
            't.dt AS "date"',
            'u.fullname AS "username"',
            'a.name AS "action"',
        ]
        if self.include_comments:
            fields.append("t.comment")
        query = self.Query("audit_trail t", *fields)
        query.join("usr u", "u.id = t.usr")
        query.join("action a", "a.id = t.action")
        query.where(query.Condition("t.document", self.doc.id))
        rows = query.execute(self.cursor).fetchall()
        return [self.Action(self, row) for row in rows]

    @cached_property
    def blocking_actions(self):
        """Blocking/unblocking actions for the report's document."""

        query = self.Query("audit_trail_added_action b", "b.dt", "a.name")
        query.join("action a", "a.id = b.action")
        query.where(query.Condition("b.document", self.doc.id))
        actions = {}
        for row in query.execute(self.cursor).fetchall():
            actions[str(row.dt)] = row.name
        return actions

    @cached_property
    def counts(self):
        """String showing how many actions were found, how many shown."""

        total = len(self.actions) + len(self.locks)
        shown = min(total, self.limit)
        return f"Showing {shown} of {total} actions"

    @cached_property
    def include_blocking_actions(self):
        """True if we should include blocking/unblocking actions."""

        return "blocking" in self.options

    @cached_property
    def include_comments(self):
        """True if we should include a column for comments."""
        return "comments" in self.options

    @cached_property
    def limit(self):
        """How many rows should be included in the report."""
        return int(self.fields.getvalue("rows", "150"))

    @cached_property
    def locks(self):
        """Locking actions for this document."""

        fields = [
            'c.dt_out AS "date"',
            'u.fullname AS "username"',
            '\'LOCK DOCUMENT\' AS "action"',
        ]
        if self.include_comments:
            fields.append("c.comment")
        query = self.Query("checkout c", *fields)
        query.join("usr u", "u.id = c.usr")
        query.where(query.Condition("c.id", self.doc.id))
        rows = query.execute(self.cursor).fetchall()
        return [self.Action(self, row) for row in rows]

    @property
    def options(self):
        return self.fields.getlist("opts")

    @cached_property
    def reverse(self):
        """True if the newer actions should be show first (the default)."""
        return "order-ascending" not in self.options

    @cached_property
    def rows(self):
        """Rows for the report's table."""

        actions = sorted(self.actions + self.locks)
        if self.reverse:
            actions = reversed(actions)
        return [a.row for a in list(actions)[:self.limit]]

    @cached_property
    def same_window(self):
        """Don't open more than one new browser tab."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def table(self):
        """Table assembled for the report."""

        caption = self.doc.cdr_id, self.doc.title, self.counts
        columns = ["Date/Time", "User Name", "Action"]
        if self.include_comments:
            columns.append("Comments")
        return self.Reporter.Table(self.rows, columns=columns, caption=caption)

    @cached_property
    def wide_css(self):
        """Use more space if showing comments."""
        return self.Reporter.Table.WIDE_CSS if self.include_comments else ""

    class Action:
        """Information for one row in the report."""

        def __init__(self, control, row):
            """Capture the caller's values.

            Required positional arguments:
              control - access to report options and blocking information
              row - information about the audit action
            """

            self.control = control
            self.dbrow = row

        def __lt__(self, other):
            """Sort the actions by date."""
            return self.dbrow.date < other.dbrow.date

        @cached_property
        def action(self):
            """What the user did with the document."""

            action = self.dbrow.action
            if not self.control.include_blocking_actions:
                return action
            verb = action.split()[0]
            if verb not in ("ADD", "MODIFY"):
                return action
            blocking_action = self.control.blocking_actions.get(self.date)
            if not blocking_action:
                return action
            blocking_verb = blocking_action.split()[0]
            return f"{verb} and {blocking_verb} DOCUMENT"

        @cached_property
        def date(self):
            """When the action took place."""
            return str(self.dbrow.date)

        @cached_property
        def row(self):
            """What goes in the report's table."""

            row = [
                self.control.Reporter.Cell(self.date[:19], classes="nowrap"),
                self.control.Reporter.Cell(self.username, classes="nowrap"),
                self.control.Reporter.Cell(self.action, classes="nowrap"),
            ]
            if self.control.include_comments:
                row.append(self.dbrow.comment)
            return row

        @cached_property
        def username(self):
            """Who performed the action."""
            return self.dbrow.username


if __name__ == "__main__":
    Control().run()
