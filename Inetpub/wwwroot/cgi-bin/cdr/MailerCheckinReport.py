#!/usr/bin/env python

"""Report mailers with responses recorded during a specified date range.
"""

import datetime
from cdrcgi import Controller, Reporter


class Control(Controller):
    """Report logic."""

    SUBTITLE = "Mailer Checkin"

    def build_tables(self):
        """Create one table for each mailer type selected."""
        return [mailer_type.table for mailer_type in self.types]

    def populate_form(self, page):
        """Let the user pick a mailer type and a date range.

        Pass:
            page - HTMLPage object on which the fields are installed
        """

        fieldset = page.fieldset("Select Mailer Type")
        fieldset.append(page.radio_button("type", value="any", checked=True))
        for name in self.type_names:
            fieldset.append(page.radio_button("type", value=name))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range")
        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)

    @property
    def end(self):
        """String for the end of the report's date range (optional)."""
        return self.fields.getvalue("end")

    @property
    def no_results(self):
        """String to display if no results are found."""
        return "No mailer responses found."

    @property
    def start(self):
        """String for the start of the report's date range (optional)."""
        return self.fields.getvalue("start")

    @property
    def subtitle(self):
        """Customize the string below the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.request == "Submit":
                self._subtitle = "Mailer Responses Checked In"
                start, end = self.start, self.end
                if start:
                    if end:
                        self._subtitle += f" Between {start} and {end}"
                    else:
                        self._subtitle += f" Since {start}"
                elif self.end:
                    self._subtitle += f" Through {end}"
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle

    @property
    def type_names(self):
        """Mailer type name strings for the form picklist."""
        if not hasattr(self, "_type_names"):
            query = self.Query("query_term", "value").unique().order("value")
            query.where("path = '/Mailer/Type'")
            rows = query.execute(self.cursor).fetchall()
            self._type_names = [row.value for row in rows]
        return self._type_names

    @property
    def types(self):
        """Sequence of `MailerType` object with report results."""

        if not hasattr(self, "_types"):
            name = self.fields.getvalue("type")
            names = self.type_names if name == "any" else [name]
            self._types = []
            for name in names:
                mailer_type = MailerType(self, name)
                if mailer_type.table:
                    self._types.append(mailer_type)
        return self._types


class MailerType:
    """Mailer type with responses."""

    COLUMNS = (
        Reporter.Column("Change Category", width="400px"),
        Reporter.Column("Count", width="100px"),
    )

    def __init__(self, control, name):
        """Capture the caller's information.

        Pass:
            control - access to the database and the report options
            name - string for the mailer type's name
        """

        self.__control = control
        self.__name = name

    @property
    def control(self):
        """Access to the database and the report options."""
        return self.__control

    @property
    def name(self):
        """String for the mailer type's name."""
        return self.__name

    @property
    def change_categories(self):
        """Ordered sequence of (category name, count) tuples."""

        if not hasattr(self, "_change_categories"):
            fields = "c.value", "COUNT(*) AS n"
            join = ["c.doc_id = t.doc_id"]
            if self.control.start or self.control.end:
                join.append("LEFT(c.node_loc, 4) = LEFT(r.node_loc, 4)")
            query = self.__make_query(fields)
            query.join("query_term c", *join)
            query.where("c.path = '/Mailer/Response/ChangesCategory'")
            query.group("c.value")
            query.order("c.value")
            rows = query.execute(self.control.cursor).fetchall()
            self._change_categories = [tuple(row) for row in rows]
        return self._change_categories

    @property
    def mailers(self):
        """Count of mailers with responses in the report's date range."""

        if not hasattr(self, "_mailers"):
            count = "COUNT(DISTINCT t.doc_id) AS n"
            query = self.__make_query([count])
            rows = query.execute(self.control.cursor).fetchall()
            self._mailers = rows[0].n
        return self._mailers

    @property
    def table(self):
        """Report table for this mailer type (or None if no responses)."""

        if not hasattr(self, "_table"):
            self._table = None
            if self.change_categories:
                caption = f"{self.name} ({self.mailers:d} Mailers Received)"
                rows = []
                for category, count in self.change_categories:
                    rows.append((category, Reporter.Cell(count, right=True)))
                opts = dict(caption=caption, columns=self.COLUMNS)
                self._table = Reporter.Table(rows, **opts)
        return self._table

    def __make_query(self, fields):
        """Create the base object for a database query.

        Pass:
            fields - sequence of query field strings
        """

        start, end = self.control.start, self.control.end
        query = self.control.Query("query_term t", *fields)
        query.where("t.path = '/Mailer/Type'")
        query.where(query.Condition("t.value", self.name))
        if start or end:
            query.join("query_term r", "r.doc_id = t.doc_id")
            query.where("r.path = '/Mailer/Response/Received'")
            if start:
                query.where(query.Condition("r.value", start, ">="))
            if end:
                end = f"{end} 23:59:59"
                query.where(query.Condition("r.value", end, "<="))
        return query


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
