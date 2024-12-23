#!/usr/bin/env python

"""Collect settings from this tier as JSON (OCECDR-4101).
"""

from functools import cached_property
from hashlib import md5
from importlib.metadata import packages_distributions, version
from json import dumps
from os import environ, walk
from pathlib import Path
from sys import getwindowsversion, version as sys_version
from lxml import etree
from cdr import run_command
from cdrcgi import Controller


class Control(Controller):
    """Web page creator."""

    TITLE = SUBTITLE = "Tier Settings"
    LOGNAME = "tier-settings"

    def populate_form(self, page):
        """Explain the report.

        Required positional argument:
          page - instance of the cdrcgi.HTMLPage class
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(
            "Click Submit to generate a JSON representation of the "
            f"settings for this tier ({self.session.tier}). "
            "This information includes:"
        ))
        fieldset.append(
            page.B.UL(
                page.B.LI("Operating system version identification"),
                page.B.LI("Environment variable values"),
                page.B.LI("Executable search path locations"),
                page.B.LI("Database settings"),
                page.B.LI("Python interpreter and module versions"),
                page.B.LI("Web server configuration settings"),
                page.B.LI("Checksums for relevant file system content"),
                page.B.LI("CDR document types and valid value enumerations")
            )
        )
        page.form.append(fieldset)

    def run(self):
        """Customized routing."""

        if not self.session.can_do("GET SYS CONFIG"):
            message = "User not authorized for viewing system settings."
            print(f"Status: 403\n\n{message}")
        elif self.fields.getvalue("prompt"):
            self.show_form()
        else:
            settings = Settings(self)
            self.send_page(settings.json, mime_type="application/json")


class Settings:
    """Collection of CDR server environment settings."""

    WEBCONFIG_ROOT = "Inetpub/wwwroot/web.config"
    WEBCONFIG_SECURE = "Inetpub/wwwroot/cgi-bin/secure/web.config"
    WEBCONFIG_API = "cdr/api/web.config"
    WEBCONFIG = dict(
        root=WEBCONFIG_ROOT,
        secure=WEBCONFIG_SECURE,
        api=WEBCONFIG_API,
    )
    DIRECTORIES = (
        "cdr/lib",
        "cdr/Bin",
        "cdr/Build",
        "cdr/ClientFiles",
        "cdr/Glossifier",
        "cdr/Licensee",
        "cdr/Mailers",
        "cdr/Publishing",
        "cdr/Licensee",
        "Inetpub/wwwroot",
    )

    def __init__(self, control):
        """Remember the caller's control object.

        Required positional argument:
          session - access to the database and the environment
        """

        self.control = control

    @cached_property
    def basedir(self):
        """Top-level directory for CDR files."""
        return Path(self.tier.basedir)

    @cached_property
    def cursor(self):
        """Access to the database."""
        return self.control.cursor

    @cached_property
    def doctypes(self):
        """Information about CDR document types."""

        doctypes = {}
        path = self.basedir / "ClientFiles" / "CdrDocTypes.xml"
        root = etree.parse(str(path)).getroot()
        for node in root.findall("CdrGetDocTypeResp"):
            key = node.get("Type")
            doctypes[key] = {}
            for child in node:
                if child.tag == "EnumSet":
                    values = [vv.text for vv in child.findall("ValidValue")]
                    doctypes[key][child.get("Node")] = sorted(values)
                elif child.tag == "LinkingElements":
                    elems = [e.text for e in child.findall("LinkingElements")]
                    doctypes[key]["linking-elements"] = sorted(elems)
        return doctypes

    @cached_property
    def files(self):
        """Information about the CDR files."""

        files = {}
        for location in self.DIRECTORIES:
            top = f"{self.tier.drive}:/{location}"
            for dirpath, _, filenames in walk(top):
                if "__pycache__" not in dirpath:
                    directory = Path(dirpath)
                    node = files
                    for name in directory.parts[1:]:
                        if name not in node:
                            node[name] = {}
                        node = node[name]
                    for name in filenames:
                        path = directory / name
                        try:
                            filehash = md5(path.read_bytes())
                            node[name] = filehash.hexdigest().lower()
                        except Exception:
                            self.control.logger.exception(path)
                            node[name] = "unreadable"
        return files

    @cached_property
    def iis_settings(self):
        """Web server settings."""

        class Config:
            """Extract web server values to a dictionary."""

            def __init__(self, path):
                """Remember the location of the configuration file.

                Required positional argument:
                  path - instance of the pathlib.Path class
                """
                self.path = path

            @cached_property
            def values(self):
                """Parse the configuration document."""
                root = etree.parse(str(self.path)).getroot()
                return {root.tag: self.parse(root)}

            def parse(self, node):
                """Recursively walk the nodes of the document.

                Required positional argument:
                  node - DOM node of the XML configuration document
                """
                children = {}
                for key in node.keys():
                    children[key] = [node.get(key)]
                for child in node:
                    if not isinstance(child.tag, str):
                        continue
                    if child.tag not in children:
                        children[child.tag] = []
                    children[child.tag].append(self.parse(child))
                for name in children:
                    if len(children[name]) == 1:
                        children[name] = children[name][0]
                return children

        web_config = {}
        for name in self.WEBCONFIG:
            path = Path(f"{self.tier.drive}:/{self.WEBCONFIG[name]}")
            web_config[name] = Config(path).values
        return {
            "account": run_command("whoami").stdout.strip(),
            "version": environ.get("SERVER_SOFTWARE"),
            "web.config": web_config,
        }

    @cached_property
    def json(self):
        """Serialize the collected settings."""

        opts = dict(indent=2, default=str)
        return dumps(dict(windows=self.windows_settings), **opts)

    @cached_property
    def mssql_settings(self):
        """Information about the SQL Server database."""

        self.cursor.execute("EXEC sp_server_info")
        settings = {}
        for _, attr_name, attr_value in self.cursor.fetchall():
            settings[attr_name] = attr_value
        return settings

    @cached_property
    def org(self):
        """CBIIT or (obsolete) OCE."""

        path = Path(self.tier.etc) / "cdrenv.rc"
        try:
            return path.read_text(encoding="ascii").strip()
        except Exception:
            self.logger.exception("Failure loading organization")
            return "CBIIT"

    @cached_property
    def python_settings(self):
        """Information about the server's Python environment."""

        distributions = packages_distributions()
        settings = dict(python=sys_version)
        for name in distributions:
            for package in distributions[name]:
                settings[package] = version(package)
        return settings

    @cached_property
    def session(self):
        """Provides access to the environment."""
        return self.control.session

    @cached_property
    def tier(self):
        """Information about the tier on which we're running."""
        return self.session.tier

    @cached_property
    def windows_settings(self):
        """Our only environment, for now."""

        # pylint: disable-next=no-member
        winver = getwindowsversion()
        settings = dict(version={})
        for name in ("major", "minor", "build", "platform", "service_pack"):
            settings["version"][name] = getattr(winver, name, "")
        settings["environ"] = dict(environ)
        path = [p for p in environ.get("PATH").split(";") if p]
        settings["search_path"] = path
        settings["mssql"] = self.mssql_settings
        settings["python"] = self.python_settings
        settings["iis"] = self.iis_settings
        settings["files"] = self.files
        settings["doctypes"] = self.doctypes
        return settings


if __name__ == "__main__":
    Control().run()
