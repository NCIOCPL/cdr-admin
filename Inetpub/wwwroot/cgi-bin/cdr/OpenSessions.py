#!/usr/bin/env python

"""Display of threads which are still running in the CDR Server.

Mostly used as a debugging tool.
"""

from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Open CDR Sessions"
    SUBMIT = None
    FIELDS = (
        "s.id",
        "s.initiated",
        "s.last_act",
        "u.name",
        "u.fullname",
        "u.email",
        "u.phone",
    )
    COLUMNS = (
        "ID",
        "Started",
        "Last Activity",
        "User ID",
        "User Name",
        "User Email",
        "User Phone",
    )

    def run(self):
        """Override to bypass form."""

        if not self.request:
            self.show_report()
            try:
                self.show_report()
            except Exception as e:
                self.logger.exception("Report failed")
                self.bail(e)
        else:
            Controller.run(self)

    def build_tables(self):
        """Return the only table we need for this report."""
        return self.table

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            opts = dict(classes="nowrap")
            for session in self.sessions:
                self._rows.append([
                    self.Reporter.Cell(session.id, right=True),
                    self.Reporter.Cell(session.initiated, **opts),
                    self.Reporter.Cell(session.last_act, **opts),
                    self.Reporter.Cell(session.name, **opts),
                    self.Reporter.Cell(session.fullname, **opts),
                    self.Reporter.Cell(session.email, **opts),
                    self.Reporter.Cell(session.phone, **opts),
                ])
        return self._rows

    @property
    def sessions(self):
        """The sessions to display."""

        if not hasattr(self, "_sessions"):
            query = self.Query("session s", *self.FIELDS).order("s.initiated")
            query.join("usr u", "u.id = s.usr")
            query.where("s.ended IS NULL")
            self._sessions = query.execute(self.cursor).fetchall()
        return self._sessions

    @property
    def table(self):
        """Create the single table for this report."""
        return self.Reporter.Table(self.rows, columns=self.COLUMNS)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
