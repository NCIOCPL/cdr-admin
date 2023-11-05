#!/usr/bin/env python

"""Ad-hoc SQL query tool for CDR database.
"""

from datetime import datetime
from json import dumps
import sys
from lxml.html import tostring
import lxml.html.builder as B
from cdrcgi import Controller, Reporter, bail, REQUEST
from cdrapi import db


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
            position = self.query_names.index(self.query)
            delete = "DELETE FROM query WHERE name = ?"
            self.cursor.execute(delete, self.query)
            self.conn.commit()
            del self._queries
            position = min(position, len(self.queries)-1)
            self._query = self.query_names[position]
        self.show_form()

    def populate_form(self, page):
        """Put the fields on the form.

        Add client-side scripting so the user doesn't have to talk to
        the server to switch from one stored query's SQL to another's.

        Customize our HTML formatting, lightening the background to
        make the form more closely, since this tool shows the form and
        the report on the same page, unlike most of our reports, and
        widening the field sets so large SQL queries are easier to
        work with.

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
        page.add_script(f"""\
var queries = {dumps(self.queries, indent=4)};
function show_query() {{
    let name = jQuery("#query").children("option:selected").val();
    jQuery("#sql").val(queries[name]);
    adjust_height();
}}
function adjust_height() {{
    console.log("adjusting height");
    let box = jQuery("#sql");
    let sql = box.val() + "x";
    let rows = sql.split(/\\r\\n|\\r|\\n/).length;
    let old_rows = box.attr("rows");
    console.log("rows=" + rows + " old rows=" + old_rows);
    if (box.attr("rows") != rows)
        box.attr("rows", rows);
}}
jQuery(function() {{
    jQuery("#query").focus();
    jQuery("#sql").on("input", adjust_height);
}});""")

    def run(self):
        """Override the top-level entry point."""

        if self.request in self.buttons:
            self.buttons[self.request]()
        Controller.run(self)

    def run_query(self):
        """Execute the current SQL query and show an HTML table for it."""

        self.logger.debug("run_query(): self.sql=%s", self.sql)
        if self.sql:
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
            self._query = self.name
            #self.subtitle = "New query successfully stored"
        elif self.query:
            update = "UPDATE query SET value = ? WHERE name = ?"
            self.cursor.execute(update, (self.sql, self.query))
            self.conn.commit()
            #self.subtitle = "Query successfully deleted"
        self.show_form()

    @property
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

    def send_json(self):
        """Return JSON-encoded results from the current query to the user."""

        if self.sql:
            rows = self.rows
            if not self.cursor.description:
                bail("No query results")
            payload = dict(columns=self.cursor.description, rows=rows)
            print("Content-type: application/json\n")
            print(dumps(payload, default=str, indent=2))
            sys.exit(0)
        else:
            self.show_form()

    def show_form(self):
        """Populate an HTML page with a form and fields and send it."""

        self.populate_form(self.form_page)
        B = self.form_page.B
        button_classes = B.CLASS("button usa-button")
        delete_classes = B.CLASS("button usa-button usa-button--secondary")
        opts = dict(type="submit", name=REQUEST)
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

    @property
    def same_window(self):
        """Don't open a new tab for these commands."""
        return "Excel", "Save", "Delete"

    @property
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

    @property
    def cols(self):
        """Table column names (made up if necessary)."""

        if not hasattr(self, "_cols"):
            if self.rows is None:
                return None
            self._cols = []
            for i, desc in enumerate(self.cursor.description):
                if desc[0]:
                    col = desc[0].replace("_", " ").title()
                else:
                    col = f"Column {i+1}"
                self._cols.append(col)
        return self._cols

    @property
    def conn(self):
        """Database connection which can only write to the query table."""

        if not hasattr(self, "_safe_conn"):
            self._safe_conn = db.connect(user="CdrGuest", timeout=600)
        return self._safe_conn

    @property
    def cursor(self):
        """Cursor for our restricted connection to the database."""

        if not hasattr(self, "_safe_cursor"):
            self._safe_cursor = self.conn.cursor()
        return self._safe_cursor

    @property
    def excel_cols(self):
        """Column names wrapped in `Reporter.Cell` objects.

        This lets us have some control over wrapping and column width.
        """

        if not hasattr(self, "_excel_cols"):
            self._excel_cols = []
            for col in self.cols:
                self._excel_cols.append(Reporter.Column(col, width="250px"))
        return self._excel_cols

    @property
    def name(self):
        """Value from the field for creating/cloning a new query."""
        return self.fields.getvalue("name")

    @property
    def queries(self):
        """Dictionary of the stored SQL queries, indexed by unique name."""

        if not hasattr(self, "_queries"):
            query = db.Query("query", "name", "value")
            rows = query.execute(self.cursor).fetchall()
            self._queries = dict(tuple(row) for row in rows)
        return self._queries

    @property
    def query(self):
        """String for the currently selected stored query's name."""
        if not hasattr(self, "_query"):
            self._query = self.fields.getvalue("query")
        return self._query

    @property
    def query_names(self):
        """Sorted sequence of the names of the stored queries."""
        return sorted(self.queries, key=str.lower)

    @property
    def rows(self):
        """Data rows for the current query SQL."""

        if not hasattr(self, "_rows"):
            self._rows = [list(row) for row in self.cursor.execute(self.sql)]
        return self._rows

    @property
    def subtitle(self):
        """String to be displayed under the main banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Allow the secondary banner to be set dynamically."""
        self._subtitle = value

    @property
    def sql(self):
        """String ontents of the textarea field for the active SQL query."""
        if not hasattr(self, "_sql"):
            self._sql = self.fields.getvalue("sql")
            if not self._sql and self.query:
                self._sql = self.queries[self.query]
        return self._sql

    @property
    def table(self):
        """Object used to generate Excel or HTML output for the query."""

        if not hasattr(self, "_table"):
            cols = self.excel_cols if self.request == "Excel" else self.cols
            opts = dict(columns=cols, sheet_name="Ad-hoc Query")
            self._table = Reporter.Table(self.rows, **opts)
        return self._table


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    try:
        Control().run()
    except Exception as e:
        bail(f"Failure: {e}")
