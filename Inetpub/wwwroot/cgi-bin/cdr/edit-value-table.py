#!/usr/bin/env python

"""Manage control tables for valid values.

    Manages three separate form pages:
     1. form for selecting a table
     2. form for selecting a value
     3. form for adding/editing/dropping a value

    This class/script can be used to support any table of valid values
    comprised as having exactly these columns:
        value_id - primary key (integer) automatically generated by the DBMS
        value_name - required display name for the value (VARCHAR(128)
        value_pos - required unique integer controlling position of value
                    on pick lists

    To add support for such a table, all that is needed is to add the
    name of the table to the Control.TABLES tuple immediately below.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and form-building tools."""

    SUBTITLE = "Edit Value Tables"
    LOGNAME = "EditValueTables"
    TABLES = (
        "glossary_translation_state",
        "media_translation_state",
        "summary_translation_state",
        "summary_change_type"
    )
    FIELDS = "value_id", "value_name", "value_pos"
    ADD = "Add"
    DROP = "Drop"
    SAVE = "Save"
    CANCEL = "Cancel"
    MAX_VALUE_LEN = 128

    def run(self):
        """Override base class method because we have multiple forms."""

        if not self.session.can_do("MANAGE DB TABLES"):
            self.bail("not authorized")
        self.logger.info("request=%r", self.request)
        match self.request:
            case self.DROP:
                self.drop()
            case self.SAVE:
                self.save()
            case self.ADD | self.SUBMIT:
                self.show_form()
            case self.CANCEL:
                message = "Edit canceled."
                self.alerts.append(dict(message=message, type="info"))
                self.id = None
                self.show_form()
            case _:
                Controller.run(self)

    def populate_form(self, page):
        """If we need more information, ask for it.

        Pass:
            page - HTMLPage object on which we draw the form fields
        """

        self.logger.info("top of populate form")
        if not self.table:
            self.logger.info("no table")
            fieldset = page.fieldset("Select Table")
            for table in self.TABLES:
                opts = dict(value=table, label=table)
                fieldset.append(page.radio_button("table", **opts))
        elif self.editing:
            self.logger.info("drawing the editing form")
            page.form.append(page.hidden_field("table", self.table))
            page.form.append(page.hidden_field("id", self.id))
            self.logger.info("collecting the value and position")
            value = self.value
            self.logger.info("value=%r", value)
            position = self.position
            self.logger.info("value=%r position=%r", value, position)
            if self.id:
                value = self.map[self.id].name
                position = self.map[self.id].position
            fieldset = page.fieldset("Unique Value Name and Position")
            field = page.text_field("value", label="Value Name", value=value)
            field.set("maxlength", str(self.MAX_VALUE_LEN))
            fieldset.append(field)
            opts = dict(value=position)
            fieldset.append(page.text_field("position", **opts))
        else:
            self.logger.info("drawing the list of values")
            page.form.append(page.hidden_field("table", self.table))
            fieldset = page.fieldset("Values (click link to edit a value)")
            ul = page.B.UL()
            params = dict(table=self.table)
            for value in sorted(self.map.values()):
                display = f"{value.name} (position {value.position:d})"
                params["id"] = str(value.id)
                url = self.make_url(self.script, **params)
                ul.append(page.B.LI(page.B.A(display, href=url)))
            fieldset.append(ul)
        self.logger.info("form is ready; alerts=%s", self.alerts)
        page.form.append(fieldset)

    def save(self):
        """Save a new or modified row in the selected valid values table."""

        if self.value and self.position:
            if not self.id:
                cols = ", ".join(self.FIELDS[1:])
                args = self.value, self.position
                query = f"INSERT INTO {self.table} ({cols}) VALUES (?,?)"
            else:
                sets = ", ".join([f"{col} = ?" for col in self.FIELDS[1:]])
                args = self.value, self.position, self.id
                query = f"UPDATE {self.table} SET {sets} WHERE value_id = ?"
            try:
                self.cursor.execute(query, args)
                self.conn.commit()
                message = f"Value {self.value!r} saved."
                self.alerts.append(dict(message=message, type="success"))
                self.id = None
                del self.map
            except Exception as e:
                message = f"Failure saving value {self.value!r}: {e}"
                self.alerts.append(dict(message=message, type="error"))
        self.show_form()

    def drop(self):
        """Remove a value from the table.

        Will fail with an error message displayed if the value
        is still in use.
        """

        if not self.id:
            self.bail()
        value = self.map[self.id]
        query = f"DELETE FROM {self.table} WHERE value_id = ?"
        try:
            self.cursor.execute(query, self.id)
            self.conn.commit()
            message = f"Value {value.name!r} successfully dropped."
            self.alerts.append(dict(message=message, type="success"))
            self.id = None
            del self.map
        except Exception as e:
            args = self.id, self.table
            self.logger.exception("failure dropping row %s from %s", *args)
            message = f"Failure dropping value {value.name!r}: {e}"
            self.alerts.append(dict(message=message, type="error"))
        self.show_form()

    @cached_property
    def buttons(self):
        """Customize the button list, depending on what's going on."""

        if self.table:
            if self.editing:
                if self.id:
                    return [self.SAVE, self.CANCEL, self.DROP]
                return [self.SAVE, self.CANCEL]
            return [self.ADD]
        return [self.SUBMIT]

    @cached_property
    def editing(self):
        """If True, we need to render the form for editing."""

        if not self.table:
            return False
        if self.id:
            args = self.id, self.table
            self.logger.info("editing value %s for table %s", *args)
            return True
        match self.request:
            case self.CANCEL | self.SUBMIT:
                return False
            case self.ADD:
                return True
            case self.DROP | self.SAVE:
                for alert in self.alerts:
                    if alert.get("type") == "error":
                        return True
                return False
            case _:
                return False

    @cached_property
    def id(self):
        """Primary key for the current value."""

        value_id = self.fields.getvalue("id", "").strip()
        if value_id:
            try:
                value_id = int(value_id)
            except Exception:
                self.bail()
        if value_id and value_id not in self.map:
            self.bail()
        return value_id

    @cached_property
    def map(self):
        """Dictionary of `Value` objects, indexed by `value_id`."""

        value_map = {}
        if self.table:
            query = self.Query(self.table, *self.FIELDS)
            for row in query.execute(self.cursor).fetchall():
                value = self.Value(row)
                value_map[value.id] = value
        return value_map

    @cached_property
    def position(self):
        """Indication of where this value should be display in picklists."""

        position = self.fields.getvalue("position", "").strip()
        if position:
            try:
                position = int(position)
            except Exception:
                message = "Position must be an integer."
                self.alerts.append(dict(message=message, type="error"))
                return None
        if isinstance(position, int):
            for value in self.map.values():
                if position == value.position and self.id != value.id:
                    message = f"Position {position} is already in use."
                    self.alerts.append(dict(message=message, type="error"))
                    return None
        elif self.request == self.SAVE:
            message = "Position field is required."
            self.alerts.append(dict(message=message, type="error"))
            return None
        return position

    @cached_property
    def same_window(self):
        """Once we're on the second browser tab, don't open any more."""
        return self.SUBMIT, self.ADD, self.DROP, self.SAVE, self.CANCEL

    @cached_property
    def table(self):
        """Table selected by the user from the landing page form."""

        table = self.fields.getvalue("table")
        if table and table not in self.TABLES:
            self.bail()
        if not table and self.request == self.SUBMIT:
            message = "Please select a table to edit."
            self.alerts.append(dict(message=message, type="warning"))
        return table

    @cached_property
    def value(self):
        """String for the `value_name` column."""

        value_name = self.fields.getvalue("value", "").strip()
        if value_name:
            key = value_name.lower()
            for value in self.map.values():
                if key == value.name.lower() and self.id != value.id:
                    message = f"The name {value_name!r} is already in use."
                    self.alerts.append(dict(message=message, type="error"))
                    return None
        elif self.request == self.SAVE:
            message = "Value name is required."
            self.alerts.append(dict(message=message, type="error"))
            return None
        return value_name

    class Value:
        """Column values for a database table row."""

        def __init__(self, row):
            """Save the caller's value.

            Pass:
                row - record from the query's results
            """

            self.__row = row

        def __lt__(self, other):
            """Sort by position, not name."""
            return self.position < other.position

        @cached_property
        def id(self):
            """Primary key for the value."""
            return self.__row.value_id

        @cached_property
        def name(self):
            """String for this valid value's name."""
            return self.__row.value_name

        @cached_property
        def position(self):
            """Integer for where this value should appear in picklists."""
            return self.__row.value_pos


if __name__ == "__main__":
    "Let the script be loaded as a module."
    Control().run()
