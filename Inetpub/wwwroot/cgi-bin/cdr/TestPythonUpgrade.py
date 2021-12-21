#!/usr/bin/env python

"""Smoke test following an upgrade of Python on a CDR Windows server.

Shows versions of everything.
"""

from importlib import import_module
from importlib.metadata import packages_distributions, version
from os import devnull
import sys
from cdrcgi import Controller, Reporter

class Control(Controller):
    SUBTITLE = "Python Upgrade Information"
    SUBMIT = None
    MODULES = (
        ("apscheduler", "Required by cdr_scheduler"),
        ("cdr", "Legacy wrapper for the CDR client/server API"),
        ("cdrcgi", "Scaffolding for CDR web pages"),
        ("cdrapi.db", "CDR database API"),
        ("cdrapi.docs", "CDR document management API"),
        ("cdrapi.publishing", "CDR publishing API"),
        ("cdrapi.reports", "CDR reporting API"),
        ("cdrapi.searches", "CDR search module API"),
        ("cdrapi.settings", "CDR tier configuration API"),
        ("cdrapi.users", "CDR login session API"),
        ("dateutil.parser", "Used by the CDR for parsing dates"),
        ("lxml.etree", "Used by the CDR to manage XML documents"),
        ("lxml.html", "Used by the CDR to manage HTML pages"),
        ("mutagen", "Uused by the CDR to analyze MP3 files"),
        ("openpyxl", "Preferred package for reading/writing Excel workbooks"),
        ("paramiko", "Used by the CDR for SFTP connections"),
        ("PIL.Image", "Used by the CDR to manage images"),
        ("PIL.ImageEnhance", "Used by the CDR to scale/enhance images"),
        ("PIL.ImageFont", "Used for calculating font sizes"),
        ("pip", "Used for managing Python packages"),
        ("pyodbc", "Used the the CDR for database communication"),
        ("pytz", "Required by apscheduler"),
        ("requests", "Preferred package for HTTP/HTTPS requests"),
        ("xlrd", "Legacy package for reading Excel workbooks (retire?)"),
        ("xlwt", "Legacy package for writing Excel workbooks (retire?)"),
        ("xlsxwriter",
         "Alternate package for creating workbooks with background images"),
    )
    def show_form(self):
        """Go directly to the report."""
        self.show_report()
    def build_tables(self):
        """Test essential imports and show versions."""
        caption = "Module Import Status"
        cols = "Module", "Description", "Status"
        rows = []

        # This strange bit was needed because the ndscheduler package
        # is poorly implemented, and writes to stdout when it is loaded.
        # We have abandoned that package, but left this in as harmless.
        stdout = sys.stdout
        sys.stdout = open(devnull, "w")
        for name, description in self.MODULES:
            try:
                import_module(name)
                status = Reporter.Cell("OK", classes="success center")
            except Exception as e:
                status = Reporter.Cell(str(e), classes="failure center")
            rows.append((name, description, status))

        # Restore sanity to the world.
        sys.stdout = stdout
        tables = [Reporter.Table(rows, columns=cols, caption=caption)]
        caption = "Module Versions"
        cols = "Distribution", "Module", "Version"
        rows = [("python.org", "Python", str(sys.version))]
        distributions = packages_distributions()
        for name in distributions:
            for package in distributions[name]:
                rows.append((name, package, version(package)))
        tables.append(Reporter.Table(rows, columns=cols, caption=caption))
        return tables

Control().run()
