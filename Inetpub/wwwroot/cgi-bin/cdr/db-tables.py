#!/usr/bin/env python

"""List the CDR tables/views and their structures.
"""

from cdrcgi import Controller


class Control(Controller):
    """Script logic."""

    SUBMIT = None
    SUBTITLE = "Database Tables and Views"
    DATABASES = "master..sysdatabases"

    def populate_form(self, page):
        """Go straight to the report (no form needed)."""

        for database in self.databases:
            try:
                if not database.tables and not database.view:
                    continue
                wrapper = page.B.DIV(page.B.CLASS("database"))
                wrapper = page.fieldset(f"{database.name.upper()}")
                for table_type in "table", "view":
                    tables = getattr(database, f"{table_type}s")
                    if tables:
                        wrapper.append(page.B.H3(f"{table_type.upper()}S"))
                        dl = page.B.DL()
                        for table in tables:
                            dl.append(page.B.DT(table.name))
                            for column in table.columns:
                                dl.append(column.dd)
                        wrapper.append(dl)
            except Exception as e:
                self.logger.warning("database %s: %s", database.name, e)
                continue
            page.form.append(wrapper)
        page.body.set("class", "report")
        page.add_css("""\
fieldset * { font-family: monospace; }
fieldset legend { font-size: 16pt; }
fieldset h2 { color: green; font-size: 16pt; }
fieldset h3 { font-size: 14pt; color: #00DD00; }
fieldset dt { color: navy; font-size: 12pt; font-weight: bold; }
fieldset dd.pk { color: red; font-size: 10pt; font-style: normal; }
fieldset dd.col { color: blue; font-size: 10pt; font-style: normal; }""")

    @property
    def databases(self):
        """Ordered list of all of the databases on the server."""

        if not hasattr(self, "_databases"):
            query = self.Query(self.DATABASES, "name").order("name")
            if not self.fields.getvalue("all"):
                query.where("name LIKE 'cdr%'")
            rows = query.execute(self.cursor).fetchall()
            self._databases = [Database(self, row.name) for row in rows]
        return self._databases

    @property
    def buttons(self):
        """Override the default set of buttons to add the dev menu."""

        return (
            self.REPORTS_MENU,
            self.DEVMENU,
            self.ADMINMENU,
            self.LOG_OUT,
        )


class Database:
    """Database to be cataloged."""

    def __init__(self, control, name):
        """Remember the caller's information.

        Let properties do the heavy lifting.

        Pass:
            control - access to the database
            name - string for the name of the database
        """

        self.__control = control
        self.__name = name

    @property
    def name(self):
        """String for the name of the database."""
        return self.__name

    @property
    def control(self):
        """Access to the database cursor."""
        return self.__control

    @property
    def cursor(self):
        """Access to the database."""
        return self.control.cursor

    @property
    def schema(self):
        """String for the name of the schema table for this database."""

        if not hasattr(self, "_schema"):
            self._schema = f"{self.name}.INFORMATION_SCHEMA"
        return self._schema

    @property
    def tables(self):
        """List of tables in the database, ordered by name."""

        if not hasattr(self, "_tables"):
            table = f"{self.schema}.TABLES"
            query = self.control.Query(table, "TABLE_NAME AS name").order(1)
            query.where("TABLE_TYPE = 'BASE TABLE'")
            rows = query.execute(self.cursor).fetchall()
            self._tables = [self.Table(self, row.name) for row in rows]
        return self._tables

    @property
    def views(self):
        """Ordered list of views contained in the database."""

        if not hasattr(self, "_views"):
            table = f"{self.schema}.TABLES"
            query = self.control.Query(table, "TABLE_NAME AS name").order(1)
            query.where("TABLE_TYPE = 'VIEW'")
            rows = query.execute(self.cursor).fetchall()
            self._views = [self.Table(self, row.name) for row in rows]
        return self._views

    class Table:
        """Table or view information."""

        def __init__(self, database, name):
            """Capture the caller's information.

            Properties will do the real work.

            Pass:
                database - `Database` object for this table/view's database
                name - string for the name of this table (or view)
            """

            self.__database = database
            self.__name = name

        @property
        def columns(self):
            """Ordered list of `Column` object for this table/view."""

            if not hasattr(self, "_columns"):
                fields = (
                    "COLUMN_NAME AS name",
                    "IS_NULLABLE AS nullable",
                    "DATA_TYPE AS type",
                )
                query = self.control.Query(f"{self.schema}.COLUMNS", *fields)
                query.where(query.Condition("TABLE_NAME", self.name))
                query.order("ORDINAL_POSITION")
                rows = query.execute(self.cursor).fetchall()
                self._columns = [self.Column(self, row) for row in rows]
            return self._columns

        @property
        def control(self):
            """Access to the database cursor."""
            return self.database.control

        @property
        def cursor(self):
            """Access to the database."""
            return self.control.cursor

        @property
        def database(self):
            """Database in which this table/view is contained."""
            return self.__database

        @property
        def name(self):
            """String for the name of this table or view."""
            return self.__name

        @property
        def primary_key_columns(self):
            """Columns which participate in the primary key for the table."""

            if not hasattr(self, "_primary_key_columns"):
                query = self.control.Query(f"{self.schema}.KEY_COLUMN_USAGE U",
                                           "U.COLUMN_NAME AS name")
                query.join(f"{self.schema}.TABLE_CONSTRAINTS C",
                           "C.CONSTRAINT_NAME = U.CONSTRAINT_NAME",
                           "C.TABLE_NAME = U.TABLE_NAME")
                query.where(query.Condition("U.TABLE_NAME", self.name))
                query.where("C.CONSTRAINT_TYPE = 'PRIMARY KEY'")
                rows = query.execute(self.cursor).fetchall()
                self._primary_key_columns = set([row.name for row in rows])
            return self._primary_key_columns

        @property
        def schema(self):
            """String for the name of the schema table for this database."""
            return self.database.schema

        class Column:
            """Column in a database table."""

            def __init__(self, table, row):
                """Capture the caller's information.

                Pass:
                    table - `Table` object in which this column belongs
                    row - carries the definition information for this column
                """

                self.__table = table
                self.__row = row

            @property
            def control(self):
                """Access to HTML builder class."""
                return self.table.control

            @property
            def dd(self):
                """Definition of the column wrapped in an HTML dd element."""

                if not hasattr(self, "_dd"):
                    self._dd = self.control.HTMLPage.B.DD(str(self))
                    if self.name in self.table.primary_key_columns:
                        self._dd.set("class", "pk")
                    else:
                        self._dd.set("class", "col")
                return self._dd

            @property
            def name(self):
                """String for the name of the database table/view column."""
                return self.__row.name

            @property
            def nullable(self):
                """Boolean indicating whether this column can have NULL."""

                if not hasattr(self, "_nullable"):
                    self._nullable = self.__row.nullable.lower() == "yes"
                return self._nullable

            @property
            def table(self):
                """Enclosing table (or view) for this column."""
                return self.__table

            @property
            def type(self):
                """Type of the values which can be stored in the column."""

                if not hasattr(self, "_type"):
                    self._type = self.__row.type.upper()
                return self._type

            def __str__(self):
                """String for the column's definition."""

                nullable = "NULL" if self.nullable else "NOT NULL"
                return f"{self.name} {self.type} {nullable}"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
