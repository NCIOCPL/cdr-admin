#!/usr/bin/env python

"""Ad-hoc SQL query tool for CDR database.
"""

from datetime import datetime
from functools import cached_property
from json import dumps
from sys import exit as sys_exit
from lxml.html import tostring
from cdrapi import db
from cdrcgi import Controller, Reporter


class Control(Controller):
    """Top-level router for script logic.

    The overridden `run()` method is where everything starts.
    """

    LOGNAME = "CdrQueries"
    SUBTITLE = "CDR Stored Database Queries"
    TABLE_STYLE = (
        "tbody tr:nth-child(odd) { background-color: #eee; }",
        "p { font-style: italic; color: green; }",
    )

    def create_sheet(self):
        """Create and send an Excel report for the current SQL query."""

        if self.sql:
            title = self.query or "Ad-hoc Query"
            report = Reporter(title, self.table, wrap=False)
            report.send("excel")
        else:
            self.show_form()

    def delete_query(self):
        """Delete the currently selected query and re-draw the form."""

        if self.query:
            delete = "DELETE FROM query WHERE name = ?"
            self.cursor.execute(delete, self.query)
            self.conn.commit()
            self.logger.info("deleted query %r", self.query)
            self.query = self.name = self.sql = None
        self.show_form()

    def populate_form(self, page):
        """Put the fields on the form.

        Add client-side scripting so the user doesn't have to talk to
        the server to switch from one stored query's SQL to another's.

        Pass:
            page - HTMLPage object on which we place the fields
        """

        # Add the three field sets.
        fieldset = page.fieldset("New Saved Query")
        tip = "Used for storing the current SQL as a new saved query."
        fieldset.append(page.text_field("name", tooltip=tip))
        page.form.append(fieldset)
        fieldset = page.fieldset("Saved Queries")
        self.logger.info("populate_form(): self.query=%s", self.query)
        prompt = "-- Select a query or create a new one --"
        opts = dict(
            options=[("", prompt)] + self.query_names,
            onchange="show_query();",
            default=self.query,
        )
        queries = page.select("query", **opts)
        queries.set("size", "10")
        fieldset.append(queries)
        page.form.append(fieldset)
        fieldset = page.fieldset("Active Query")
        sql = self.sql
        if not sql and self.query:
            opts["default"] = self.query
            sql = self.queries.get(self.query, "")
        sql = (sql or "").strip()
        self.logger.debug("populate_form(): self.sql=%s", self.sql)
        rows = sql.count("\n") + 2
        textarea = page.textarea("sql", label="SQL", value=sql, rows=rows)
        textarea.set("spellcheck", "false")
        fieldset.append(textarea)
        page.form.append(fieldset)

        # Customize the appearance of this tool's web page.
        page.add_css("""\
.labeled-field textarea#sql {
    font-family: Courier;
    min-height: 2rem;
}
.usa-textarea { height: auto; }""")

        # Add some client-side scripting to support scrolling through
        # the stored queries.
        page.add_script(f"var queries = {dumps(self.queries, indent=2)};")
        page.head.append(page.B.SCRIPT(src="/js/CdrQueries.js"))

    def run(self):
        """Override the top-level entry point."""

        if not self.session.can_do("RUN SQL QUERIES"):
            self.bail("Not permitted")
        if self.request in self.buttons:
            self.buttons[self.request]()
        Controller.run(self)

    def run_query(self):
        """Execute the current SQL query and show an HTML table for it."""

        self.logger.debug("run_query(): self.sql=%s", self.sql)
        if self.sql:
            B = self.HTMLPage.B
            start = datetime.now()
            table = self.table.node
            if self.query:
                table.insert(0, B.CAPTION(self.query or "Ad-hoc query"))
            elapsed = datetime.now() - start
            elapsed = f"Retrieved {len(self.rows):d} rows in {elapsed}"
            style = "\n".join(self.TABLE_STYLE)
            page = B.HTML(
                B.HEAD(B.TITLE("Ad-hoc query results"), B.STYLE(style)),
                B.BODY(table, B.P(elapsed))
            )
            opts = dict(
                pretty_print=True,
                doctype="<!DOCTYPE html>",
                encoding="unicode",
            )
            self.send_page(tostring(page, **opts))
        self.form_page.send()

    def save_query(self):
        """Update the SQL string for the currently selected query."""

        if self.name:
            insert = "INSERT INTO query (name, value) VALUES(?, ?)"
            self.cursor.execute(insert, (self.name, self.sql or ""))
            self.conn.commit()
            self.query = self.name
        elif self.query:
            update = "UPDATE query SET value = ? WHERE name = ?"
            self.cursor.execute(update, (self.sql, self.query))
            self.conn.commit()
        if self.query:
            self.logger.info("saved query %r", self.query)
        self.show_form()

    def send_json(self):
        """Return JSON-encoded results from the current query to the user."""

        if self.sql:
            rows = self.rows
            if not self.cursor.description:
                self.bail("No query results")
            payload = dict(columns=self.cursor.description, rows=rows)
            print("Content-type: application/json")
            print("X-Content-Type-Options: nosniff\n")
            print(dumps(payload, default=str, indent=2))
            sys_exit(0)
        else:
            self.show_form()

    def show_form(self):
        """Populate an HTML page with a form and fields and send it."""

        self.populate_form(self.form_page)
        B = self.form_page.B
        button_classes = B.CLASS("button usa-button")
        delete_classes = B.CLASS("button usa-button usa-button--secondary")
        opts = dict(type="submit", name=self.REQUEST)
        for value in list(self.buttons):
            classes = delete_classes if value == "Delete" else button_classes
            button = B.INPUT(classes, value=value, **opts)
            if value in self.same_window:
                button.set("onclick", self.SAME_WINDOW)
            self.form_page.form.append(button)
        for alert in self.alerts:
            message = alert["message"]
            del alert["message"]
            self.form_page.add_alert(message, **alert)
        self.form_page.send()

    @cached_property
    def alerts(self):
        """Show any notifications which are appropriate."""
        if self.request == "Save" and (self.name or self.query):
            query = "New query" if self.name else "Query"
            alert = {"type": "success"}
            alert["message"] = f"{query} successfuly stored."
            return [alert]
        elif self.request == "Delete":
            message = "Query successfully deleted."
            return [dict(type="success", message=message)]
        return []

    @cached_property
    def buttons(self):
        """Actions which we support.

        Mapped to methods for handling each action.
        """

        return dict(
            Run=self.run_query,
            Excel=self.create_sheet,
            JSON=self.send_json,
            Save=self.save_query,
            Delete=self.delete_query,
        )

    @cached_property
    def cols(self):
        """Table column names (made up if necessary)."""

        if self.rows is None:
            return None
        cols = []
        for i, desc in enumerate(self.cursor.description):
            if desc[0]:
                col = desc[0].replace("_", " ").title()
            else:
                col = f"Column {i+1}"
            cols.append(col)
        return cols

    @cached_property
    def conn(self):
        """Database connection which can only write to the query table."""
        return db.connect(user="CdrGuest", timeout=600)

    @cached_property
    def cursor(self):
        """Cursor for our restricted connection to the database."""
        return self.conn.cursor()

    @cached_property
    def excel_cols(self):
        """Column names wrapped in `Reporter.Cell` objects.

        This lets us have some control over wrapping and column width.
        """

        cols = []
        for col in self.cols:
            cols.append(Reporter.Column(col, width="250px"))
        return cols

    @cached_property
    def name(self):
        """Value from the field for creating/cloning a new query."""
        return self.fields.getvalue("name")

    @cached_property
    def queries(self):
        """Dictionary of the stored SQL queries, indexed by unique name."""

        query = db.Query("query", "name", "value")
        rows = query.execute(self.cursor).fetchall()
        self.logger.info("loaded %d queries", len(rows))
        return dict(tuple(row) for row in rows)

    @cached_property
    def query(self):
        """String for the currently selected stored query's name."""
        return self.fields.getvalue("query")

    @cached_property
    def query_names(self):
        """Sorted sequence of the names of the stored queries."""
        return sorted(self.queries, key=str.lower)

    @cached_property
    def rows(self):
        """Data rows for the current query SQL."""
        return [list(row) for row in self.cursor.execute(self.sql)]

    @cached_property
    def same_window(self):
        """Don't open a new tab for these commands."""
        return "Excel", "Save", "Delete"

    @cached_property
    def sql(self):
        """String ontents of the textarea field for the active SQL query."""

        sql = self.fields.getvalue("sql")
        if not sql and self.query:
            sql = self.queries[self.query]
        return sql

    @cached_property
    def table(self):
        """Object used to generate Excel or HTML output for the query."""

        cols = self.excel_cols if self.request == "Excel" else self.cols
        opts = dict(columns=cols, sheet_name="Ad-hoc Query")
        return Reporter.Table(self.rows, **opts)


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    try:
        Control().run()
    except Exception as e:
        Controller.bail(f"Failure: {e}")
