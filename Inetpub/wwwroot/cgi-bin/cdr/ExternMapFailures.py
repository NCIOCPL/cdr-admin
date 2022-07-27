#!/usr/bin/env python

"""Report on unmapped values in the external mapping table.
"""

from cdrcgi import Controller
import datetime


class Control(Controller):
    """Access to the database and report generation tools."""

    SUBTITLE = "External Map Failures Report"
    NON_MAPPABLE = "non-mappable"
    OPTION = NON_MAPPABLE, "Include non-mappable values"

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page - HTMLPage object on which to place the fields
        """

        fieldset = page.fieldset("Select at Least One Usage")
        for usage in self.usages:
            opts = dict(value=usage, label=usage)
            fieldset.append(page.checkbox("usage", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Age (in days)")
        fieldset.append(page.text_field("age", value=30))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        value, label = self.OPTION
        fieldset.append(page.checkbox("options", value=value, label=label))
        page.form.append(fieldset)

    def build_tables(self):
        """Assemble the report's tables."""

        if not self.usage:
            self.show_form()
        tables = []
        for name in self.usage:
            table = Usage(self, name).table
            if table is not None:
                tables.append(table)
        return tables

    @property
    def options(self):
        """Report options."""
        return self.fields.getlist("options")

    @property
    def start(self):
        """Start date for the report based on the age value from the form."""

        if not hasattr(self, "_start"):
            age = self.fields.getvalue("age")
            if not age:
                self._start = None
            else:
                try:
                    days = int(age)
                except Exception:
                    self.bail("Age must be an integer")
                today = datetime.date.today()
                self._start = today - datetime.timedelta(days)
        return self._start

    @property
    def usage(self):
        """Mapping type(s) selected by the user from the form."""
        return self.fields.getlist("usage")

    @property
    def usages(self):
        """Valid usage values for the form's picklist."""

        query = self.Query("external_map_usage", "name").order("name")
        return [row.name for row in query.execute(self.cursor).fetchall()]


class Usage:
    """Mappings for a specific mapping usage."""

    FIELDS = "m.value", "m.last_mod"

    def __init__(self, control, name):
        """Remember the caller's values.

        Pass:
            control - access to the database and report generation facilities
            name - string describing the mapping usage
        """

        self.__control = control
        self.__name = name

    @property
    def columns(self):
        """Column headers for the report table."""
        return (
            self.__control.Reporter.Column("Value", width="800px"),
            self.__control.Reporter.Column("Recorded", width="100px"),
        )

    @property
    def rows(self):
        """Values for the report table."""

        if not hasattr(self, "_rows"):
            query = self.__control.Query("external_map m", *self.FIELDS)
            query.order("m.last_mod DESC", "m.value")
            query.join("external_map_usage u", "u.id = m.usage")
            query.where("m.doc_id IS NULL")
            query.where(query.Condition("u.name", self.__name))
            if self.start:
                query.where(query.Condition("m.last_mod", self.start, ">="))
            if Control.NON_MAPPABLE not in self.__control.options:
                query.where("m.mappable <> 'N'")
            self._rows = query.execute(self.__control.cursor).fetchall()
        return self._rows

    @property
    def start(self):
        """Start date for the report based on the age value from the form."""
        return self.__control.start

    @property
    def table(self):
        """Report table for this mapping type."""

        if not self.rows:
            return None
        opts = dict(columns=self.columns, caption=self.__name)
        return self.__control.Reporter.Table(self.rows, **opts)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
