#!/usr/bin/env python

"""Check server health on a CDR Tier.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi import db
# pylint: disable-next=no-name-in-module
from socket import gethostbyname, create_connection


class Control(Controller):
    """Report builder"""

    SUBTITLE = "CDR Server Health Check"
    LOGNAME = "HealthCheck"

    def show_form(self):
        """Bypass form, which is not needed for this report."""
        self.show_report()

    def build_tables(self):
        """Create tables for the web server and the database server."""
        return self.app_server.table, self.db_server.table

    @property
    def app_server(self):
        """The CDR Windows server machine."""
        return self.AppServer(self)

    @property
    def db_server(self):
        """SQL Server with which the CDR communicates for data persistence."""
        return self.DatabaseServer(self)

    @property
    def ok_image(self):
        """Image with an "OK" green check mark."""

        opts = dict(src="/images/checkmark.gif", alt="check mark")
        cell = self.HTMLPage.B.IMG(**opts)
        return cell

    class AppServer:
        """The CDR Windows server."""

        ROLES = dict(
            APPC=443,
            DBWIN=None,
            SFTP=22,
            CG=443,
            DRUPAL=443,
        )

        def __init__(self, control):
            """Save a reference to the control object.

            Pass:
                control - access to table building tools and tier information
            """

            self.__control = control

        @property
        def control(self):
            """Access to the tools we need."""
            return self.__control

        @property
        def columns(self):
            """Column headers for the report table."""

            return (
                self.__control.Reporter.Column("Role", width="125px"),
                self.__control.Reporter.Column("Name", width="300px"),
                self.__control.Reporter.Column("IP Address"),
                self.__control.Reporter.Column("Status"),
            )

        @property
        def rows(self):
            """Values for the report table."""

            return [self.Role(self, name).row for name in sorted(self.ROLES)]

        @property
        def table(self):
            """Assemble the report table."""

            opts = dict(columns=self.columns, caption="Host Name Mappings")
            return self.__control.Reporter.Table(self.rows, **opts)

        class Role:
            """TCP/IP settings for a specific role on the server."""

            def __init__(self, server, name):
                """Capture the caller's values.

                Pass:
                    server - the app server machine on which the role lives
                    name - key into the tier's dictionary of role invofmation
                """

                self.__server = server
                self.__name = name

            @property
            def control(self):
                """Access to report building facilities."""
                return self.server.control

            @property
            def dns(self):
                """The fully qualified domain name used by this role."""
                return self.server.control.session.tier.hosts.get(self.__name)

            @property
            def error(self):
                """String describing a problem or None if OK."""

                if self.ok:
                    return None
                elif not self.dns:
                    return "MISSING"
                elif not self.ip:
                    return "NOT FOUND"
                else:
                    return "CONNECTION REFUSED"

            @property
            def error_cell(self):
                """Description of error encountered for this role."""

                span = self.control.HTMLPage.B.SPAN(self.error)
                span.set("class", "error")
                return self.control.Reporter.Cell(span)

            @property
            def name(self):
                """Key into the tier's dictionary of role information."""
                return self.__name

            @property
            def ip(self):
                """IP address used by this role."""

                if not hasattr(self, "_id"):
                    self._id = None
                    if self.dns:
                        try:
                            self._id = gethostbyname(self.dns)
                        except Exception:
                            self.logger.exception("%s not found", self.dns)
                return self._id

            @cached_property
            def logger(self):
                """Record what we do."""
                return self.control.logger

            @property
            def ok(self):
                """Can we connect?"""

                if not self.port or not self.dns:
                    return False
                try:
                    key = self.dns, self.port
                    conn = create_connection(key)
                    conn.close()
                    return True
                except Exception:
                    self.control.logger.exception("failure connecting")
                    return False

            @property
            def ok_cell(self):
                """Wrap the image in a `Cell` object."""

                cell = self.control.ok_image
                return self.control.Reporter.Cell(cell, center=True)

            @property
            def port(self):
                """TCP/IP port for SQL Server used by this role."""

                if not hasattr(self, "_port"):
                    if self.__name == "DBWIN":
                        self._port = self.sql_server_port
                    else:
                        self._port = self.server.ROLES.get(self.__name)
                return self._port

            @property
            def row(self):
                """Values for the database report table."""

                if not hasattr(self, "_row"):
                    self._row = (
                        self.name,
                        self.dns,
                        self.ip,
                        self.error_cell if self.error else self.ok_cell,
                    )
                return self._row

            @property
            def server(self):
                """The CDR Windows server."""
                return self.__server

            @property
            def sql_server_port(self):
                """Port on which SQL Server listens for this tier."""
                return self.control.session.tier.port("cdr")

    class DatabaseServer:
        """SQL Server with which the CDR communicates for data persistence."""

        DATABASES = dict(cdr=("cdrsqlaccount", "CdrPublishing", "CdrGuest"))

        def __init__(self, control):
            """Save the caller object.

            Pass:
                control - access to tier settings and report creation tools
            """

            self.__control = control

        @property
        def columns(self):
            """Column headers for the report table."""

            return (
                self.__control.Reporter.Column("Database", width="125px"),
                self.__control.Reporter.Column("Account", width="200px"),
                self.__control.Reporter.Column("Status")
            )

        @property
        def rows(self):
            """Values for the report table."""
            rows = []
            for database in sorted(self.DATABASES):
                for account in self.DATABASES[database]:
                    try:
                        db.connect(user=account, database=database)
                        status = self.__control.ok_image
                    except Exception:
                        status = self.__control.HTMLPage.B.SPAN("LOGIN FAILED")
                        status.set("class", "error")
                    status = self.__control.Reporter.Cell(status, center=True)
                    rows.append([database, account, status])
            return rows

        @property
        def table(self):
            """Assemble the report table."""

            opts = dict(columns=self.columns, caption="Database Credentials")
            return self.__control.Reporter.Table(self.rows, **opts)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
