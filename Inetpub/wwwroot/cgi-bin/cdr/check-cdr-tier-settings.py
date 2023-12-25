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

    @cached_property
    def app_server(self):
        """The CDR Windows server machine."""
        return self.AppServer(self)

    @cached_property
    def db_server(self):
        """SQL Server with which the CDR communicates for data persistence."""
        return self.DatabaseServer(self)

    @property
    def ok_image(self):
        """Image with an "OK" green check mark (deliberately uncached)."""

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

        @cached_property
        def control(self):
            """Access to the tools we need."""
            return self.__control

        @cached_property
        def columns(self):
            """Column headers for the report table."""

            return (
                self.__control.Reporter.Column("Role", width="125px"),
                self.__control.Reporter.Column("Name", width="300px"),
                self.__control.Reporter.Column("IP Address"),
                self.__control.Reporter.Column("Status"),
            )

        @cached_property
        def rows(self):
            """Values for the report table."""

            return [self.Role(self, name).row for name in sorted(self.ROLES)]

        @cached_property
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

            @cached_property
            def control(self):
                """Access to report building facilities."""
                return self.server.control

            @cached_property
            def dns(self):
                """The fully qualified domain name used by this role."""
                return self.server.control.session.tier.hosts.get(self.__name)

            @cached_property
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

            @cached_property
            def error_cell(self):
                """Description of error encountered for this role."""

                span = self.control.HTMLPage.B.SPAN(self.error)
                span.set("class", "error text-red text-bold")
                return self.control.Reporter.Cell(span)

            @cached_property
            def name(self):
                """Key into the tier's dictionary of role information."""
                return self.__name

            @cached_property
            def ip(self):
                """IP address used by this role."""

                if self.dns:
                    try:
                        return gethostbyname(self.dns)
                    except Exception:
                        message = "%s not found"
                        self.control.logger.exception(message, self.dns)
                return None

            @cached_property
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
                """Wrap the image in a `Cell` object (uncached)."""

                cell = self.control.ok_image
                return self.control.Reporter.Cell(cell)

            @cached_property
            def port(self):
                """TCP/IP port for SQL Server used by this role."""

                if self.name == "DBWIN":
                    return self.sql_server_port
                return self.server.ROLES.get(self.__name)

            @cached_property
            def row(self):
                """Values for the database report table."""

                return (
                    self.name,
                    self.dns,
                    self.ip,
                    self.error_cell if self.error else self.ok_cell,
                )

            @cached_property
            def server(self):
                """The CDR Windows server."""
                return self.__server

            @cached_property
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

        @cached_property
        def columns(self):
            """Column headers for the report table."""

            return (
                self.__control.Reporter.Column("Database", width="125px"),
                self.__control.Reporter.Column("Account", width="200px"),
                self.__control.Reporter.Column("Status")
            )

        @cached_property
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
                        status.set("class", "error text-red test-bold")
                    status = self.__control.Reporter.Cell(status)
                    rows.append([database, account, status])
            return rows

        @cached_property
        def table(self):
            """Assemble the report table."""

            opts = dict(columns=self.columns, caption="Database Credentials")
            return self.__control.Reporter.Table(self.rows, **opts)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("Tier settings check failure")
        control.bail(e)
