#!/usr/bin/env python

"""Show which CDR accounts belong to which groups.

Not in the CDR Admin menus. Generated as an HTML report unless the
format parameter is passed with the value 'excel'.
"""

from cdrcgi import Controller


class Control(Controller):
    """Facilities for report building and database access."""

    SUBTITLE = "CDR Group Membership"

    def show_form(self):
        """Bypass the form, which is not needed for this report."""
        self.show_report()

    def build_tables(self):
        """Provide the single table for this report."""
        return self.table

    @property
    def caption(self):
        """Caption for the report table."""
        return f"CDR {self.session.tier} Groups as of {self.started}"

    @property
    def columns(self):
        """Column headers for the report table."""
        return [""] + [user.name for user in self.users]

    @property
    def groups(self):
        """CDR groups."""

        if not hasattr(self, "_groups"):
            query = self.Query("grp", "id", "name").order("name")
            rows = query.execute(self.cursor).fetchall()
            self._groups = [self.Group(self, row) for row in rows]
        return self._groups

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = [group.row for group in self.groups]
        return self._rows

    @property
    def table(self):
        """Create the single table used for this report."""

        if not hasattr(self, "_table"):
            opts = dict(columns=self.columns, caption=self.caption)
            self._table = self.Reporter.Table(self.rows, **opts)
        return self._table

    @property
    def users(self):
        """Active CDR accounts which are not machine local accounts."""

        if not hasattr(self, "_users"):
            query = self.Query("usr", "id", "name", "fullname")
            query.where("expired IS NULL")
            query.where("(password IS NULL OR password = '')")
            rows = query.execute(self.cursor).fetchall()
            self._users = sorted([self.User(row) for row in rows])
        return self._users


    class Group:
        """Group of CDR user accounts with specific permissions."""

        def __init__(self, control, row):
            """Capture the caller's values.

            Pass:
                control - access to the database and HTML page building
                row - row from the group query's result set
            """

            self.__control = control
            self.__row = row

        @property
        def id(self):
            """Integer for the group's unique identifier."""
            return self.__row.id

        @property
        def members(self):
            """IDs for the members of this group."""

            if not hasattr(self, "_members"):
                query = self.__control.Query("grp_usr", "usr")
                query.where(query.Condition("grp", self.id))
                rows = query.execute(self.__control.cursor).fetchall()
                self._members = set([row.usr for row in rows])
            return self._members

        @property
        def name(self):
            """String for the display name of the group."""
            return self.__row.name

        @property
        def row(self):
            """Sequence of values for the report's table."""

            if not hasattr(self, "_row"):
                Cell = self.__control.Reporter.Cell
                self._row = [Cell(self.name, bold=True)]
                for user in self.__control.users:
                    if user.id in self.members:
                        self._row.append(Cell("X", center=True))
                    else:
                        self._row.append("")
            return self._row


    class User:
        """Active non-machine CDR account."""

        def __init__(self, row):
            """Save the caller's values.

            Pass:
                row - row from the users query result set
            """

            self.__row = row

        @property
        def name(self):
            """Full name if we have one, else account name."""

            if not hasattr(self, "_name"):
                self._name = self.__row.name
                if self.__row.fullname:
                    self._name = f"{self._name} ({self.__row.fullname})"
            return self._name

        @property
        def id(self):
            """Primary key into the table of CDR users."""
            return self.__row.id

        def __lt__(self, other):
            """Support sorting by display name, case insensitive."""
            return self.name.lower() < other.name.lower()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
