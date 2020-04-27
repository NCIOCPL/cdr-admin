#!/usr/bin/env python

"""Smoke test following an upgrade of Python on a CDR Windows server.

Shows versions of everything.
"""

from importlib import import_module
from pkg_resources import Environment
from os import devnull
import sys
from cdrcgi import Controller, Reporter

class Control(Controller):
    SUBTITLE = "Python Upgrade Information"
    SUBMIT = None
    MODULES = (
        ("apscheduler", "Required by ndscheduler"),
        ("cdr", "Legacy wrapper for the CDR client/server API"),
        ("cdrcgi", "Scaffolding for CDR web pages"),
        ("cdrapi.db", "CDR database API"),
        ("cdrapi.docs", "CDR document management API"),
        ("cdrapi.publishing", "CDR publishing API"),
        ("cdrapi.reports", "CDR reporting API"),
        ("cdrapi.searches", "CDR search module API"),
        ("cdrapi.settings", "CDR tier configuration API"),
        ("cdrapi.users", "CDR login session API"),
        ("dateutil", "Required by ndscheduler"),
        ("dateutil.parser", "Required by ndscheduler"),
        ("dateutil.tz", "Required by ndscheduler"),
        ("dateutil.relativedelta", "Required by ndscheduler"),
        ("lxml.etree", "Used by the CDR to manage XML documents"),
        ("lxml.html", "Used by the CDR to manage HTML pages"),
        ("mutagen", "Uused by the CDR to analyze MP3 files"),
        ("ndscheduler", "Required by the CDR Scheduler"),
        ("openpyxl", "Preferred package for reading/writing Excel workbooks"),
        ("paramiko", "Used by the CDR for SFTP connections"),
        ("PIL.Image", "Used by the CDR to manage images"),
        ("PIL.ImageEnhance", "Used by the CDR to scale/enhance images"),
        ("PIL.ImageFont", "Used for calculating font sizes"),
        ("pip", "Used for managing Python packages"),
        ("pkg_resources", "Used for cataloging installed Python modules"),
        ("psutil", "Used by the CDR scheduler software"),
        ("pyodbc", "Used the the CDR and ndscheduler for DB communication"),
        ("pytz", "Required by ndscheduler"),
        ("requests", "Preferred package for HTTP/HTTPS requests"),
        ("setuptools", "Required by ndscheduler"),
        ("tornado", "Required by apsscheduler package"),
        ("xlrd", "Legacy package for reading Excel workbooks (retire?)"),
        ("xlwt", "Legacy package for writing Excel workbooks (retire?)"),
        ("xlsxwriter",
         "Alternate package for creating workbooks with background images"),
        ("zeep", "Used for testing the CDR glossifier SOAP service"),
    )
    def show_form(self):
        """Go directly to the report."""
        self.show_report()
    def build_tables(self):
        """Test essential imports and show versions."""
        caption = "Module Import Status"
        cols = "Module", "Description", "Status"
        rows = []

        # This strange bit is needed because the ndscheduler package
        # is poorly implemented, and writes to stdout when it is loaded.
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
        cols = "Module", "Version"
        rows = [("Python", str(sys.version))]
        env = Environment()
        for key in sorted(env, key=str.lower):
            for package in env[key]:
                rows.append(str(package).split())
        tables.append(Reporter.Table(rows, columns=cols, caption=caption))
        return tables

Control().run()
