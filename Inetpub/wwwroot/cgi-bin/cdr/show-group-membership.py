#!/usr/bin/env python

"""Show which CDR accounts belong to which groups.

Not in the CDR Admin menus. Generated as an HTML report unless the
format parameter is passed with the value 'excel'.
"""

from functools import cached_property
from cdrcgi import Controller, BasicWebPage


class Control(Controller):
    """Facilities for report building and database access."""

    SUBTITLE = "CDR Group Membership"
    CSS = """\
table { width: 100%; }
.text-center { text-align: center; }
th { padding: .25rem; }
td { color: green; }
td, th { background: white; }
thead th { position: sticky; top: 0; z-index: 1; }
thead th:first-child { left: 0; z-index: 2; }
td:first-child { position: sticky; left: 0; z-index: 1; }
td:first-child { white-space: nowrap; color: black; }
th { white-space: nowrap; }
"""

    def show_form(self):
        """Bypass the form, which is not needed for this report."""
        self.show_report()

    def show_report(self):
        """Override to accommodate the report's wide table."""

        if self.format == "excel":
            report = self.Reporter(self.SUBTITLE, [self.table])
            report.send("excel")
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        report.wrapper.append(self.table.node)
        report.wrapper.append(self.footer)
        report.page.head.append(report.B.STYLE(self.CSS))
        report.send()

    @cached_property
    def caption(self):
        """Caption for the report table."""
        return f"CDR {self.session.tier} Groups as of {self.started}"

    @cached_property
    def columns(self):
        """Column headers for the report table."""

        opts = {} if self.format == "html" else dict(width="250px")
        columns = [self.Reporter.Column("", **opts)]
        for user in self.users:
            if self.format == "html":
                if user.fullname:
                    fullname = f"({user.fullname})"
                    span = self.HTMLPage.B.SPAN(
                        user.name,
                        self.HTMLPage.B.BR(),
                        fullname
                    )
                    columns.append(self.Reporter.Column(span))
                else:
                    columns.append(user.name)
            else:
                value = user.name
                if user.fullname:
                    value = f"{value}\n({user.fullname})"
                columns.append(self.Reporter.Column(value, width="125px"))
        return columns

    @cached_property
    def groups(self):
        """CDR groups."""

        query = self.Query("grp", "id", "name").order("name")
        rows = query.execute(self.cursor).fetchall()
        return [self.Group(self, row) for row in rows]

    @cached_property
    def rows(self):
        """Table rows for the report."""
        return [group.row for group in self.groups]

    @cached_property
    def table(self):
        """Create the single table used for this report."""

        opts = dict(columns=self.columns, caption=self.caption)
        opts["freeze_panes"] = "B4"
        return self.Reporter.Table(self.rows, **opts)

    @cached_property
    def users(self):
        """Active CDR accounts which are not machine local accounts."""

        query = self.Query("usr", "id", "name", "fullname")
        query.where("expired IS NULL")
        query.where("(password IS NULL OR password = '')")
        rows = query.execute(self.cursor).fetchall()
        return sorted([self.User(row) for row in rows])

    class Group:
        """Group of CDR user accounts with specific permissions."""

        def __init__(self, control, row):
            """Capture the caller's values.

            Pass:
                control - access to the database and HTML page building
                row - row from the group query's result set
            """

            self.control = control
            self.dbrow = row

        @cached_property
        def id(self):
            """Integer for the group's unique identifier."""
            return self.dbrow.id

        @cached_property
        def members(self):
            """IDs for the members of this group."""

            query = self.control.Query("grp_usr", "usr")
            query.where(query.Condition("grp", self.id))
            rows = query.execute(self.control.cursor).fetchall()
            return set([row.usr for row in rows])

        @cached_property
        def name(self):
            """String for the display name of the group."""
            return self.dbrow.name

        @cached_property
        def row(self):
            """Sequence of values for the report's table."""

            Cell = self.control.Reporter.Cell
            row = [Cell(self.name, bold=True)]
            for user in self.control.users:
                if user.id in self.members:
                    # Other possibilities: \u2705 or \u2611.
                    row.append(Cell("\u2713", center=True))
                else:
                    row.append("")
            return row

    class User:
        """Active non-machine CDR account."""

        def __init__(self, row):
            """Save the caller's values.

            Pass:
                row - row from the users query result set
            """

            self.row = row

        @cached_property
        def fullname(self):
            """Full name if we have one."""
            return self.row.fullname

        @cached_property
        def name(self):
            """Account name for the user."""
            return self.row.name

        @cached_property
        def id(self):
            """Primary key into the table of CDR users."""
            return self.row.id

        def __lt__(self, other):
            """Support sorting by display name, case insensitive."""
            return self.name.lower() < other.name.lower()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
