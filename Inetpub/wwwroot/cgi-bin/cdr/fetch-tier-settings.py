#!/usr/bin/env python

# ----------------------------------------------------------------------
# Collect settings from this tier as JSON.
# OCECDR-4101
# ----------------------------------------------------------------------
import hashlib
import json
import os
import sys
import lxml.etree as etree
import cdr
import cdrcgi
from cdrapi import db
from cdrapi.settings import Tier
from importlib.metadata import packages_distributions, version


class Settings:
    TIER = Tier()
    HOSTNAMES = TIER.hosts
    LOGFILE = f"{cdr.DEFAULT_LOGDIR}/fetch-tier-settings.log"
    WD = cdr.WORK_DRIVE
    WEBCONFIG_ROOT = f"{WD}:/Inetpub/wwwroot/web.config"
    WEBCONFIG_SECURE = f"{WD}:/Inetpub/wwwroot/cgi-bin/secure/web.config"
    WEBCONFIG_API = f"{WD}:/cdr/api/web.config"

    def __init__(self, session):
        self.session = session
        try:
            with open(f"{self.TIER.etc}/cdrenv.rc") as fp:
                self.org = fp.read().strip()
        except Exception:
            self.org = "CBIIT"
        self.tier = self.TIER.name
        self.windows = self.get_windows_settings()

    def get_iis_settings(self):
        return {
            "account": cdr.run_command("whoami").stdout.strip(),
            "version": os.environ.get("SERVER_SOFTWARE"),
            "web.config": {
                "root": self.xmltojson(self.WEBCONFIG_ROOT),
                "secure": self.xmltojson(self.WEBCONFIG_SECURE),
                "api": self.xmltojson(self.WEBCONFIG_API),
            }
        }

    def xmltojson(self, path):
        root = etree.parse(path).getroot()
        return {root.tag: self.extract_node(root)}

    def extract_node(self, node):
        children = {}
        for key in node.keys():
            children[key] = [node.get(key)]
        for child in node:
            if not isinstance(child.tag, str):
                continue
            if child.tag not in children:
                children[child.tag] = []
            children[child.tag].append(self.extract_node(child))
        for name in children:
            if len(children[name]) == 1:
                children[name] = children[name][0]
        return children

    def get_windows_settings(self):
        # pylint: disable-next=no-member
        winver = sys.getwindowsversion()
        settings = dict(version={})
        for name in ("major", "minor", "build", "platform", "service_pack"):
            settings["version"][name] = getattr(winver, name, "")
        settings["environ"] = dict(os.environ)
        path = [p for p in os.environ.get("PATH").split(";") if p]
        settings["search_path"] = path
        settings["mssql"] = self.get_mssql_settings()
        settings["python"] = self.get_python_settings()
        settings["iis"] = self.get_iis_settings()
        settings["files"] = self.get_files()
        settings["doctypes"] = self.get_doctypes()
        return settings

    def get_doctypes(self):
        doctypes = {}
        path = f"{self.WD}:/cdr/ClientFiles/CdrDocTypes.xml"
        root = etree.parse(path).getroot()
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

    def get_files(self):
        files = {}
        self.walk(files, f"{self.WD}:/cdr/lib")
        self.walk(files, f"{self.WD}:/cdr/Bin")
        self.walk(files, f"{self.WD}:/cdr/Build")
        self.walk(files, f"{self.WD}:/cdr/ClientFiles")
        self.walk(files, f"{self.WD}:/cdr/Glossifier")
        self.walk(files, f"{self.WD}:/cdr/Licensee")
        self.walk(files, f"{self.WD}:/cdr/Mailers")
        self.walk(files, f"{self.WD}:/cdr/Publishing")
        self.walk(files, f"{self.WD}:/cdr/Licensee")
        self.walk(files, f"{self.WD}:/Inetpub/wwwroot")
        return files

    def walk(self, files, path):
        for path, dirs, filenames in os.walk(path):
            if "__pycache__" in path:
                continue
            path = path.replace("\\", "/")
            directory = files
            for name in path.split("/")[1:]:
                if name not in directory:
                    directory[name] = {}
                directory = directory[name]
            for name in filenames:
                self.add_file(path, name, directory)

    def add_file(self, path, name, files):
        try:
            path = "%s/%s" % (path, name)
            fp = open(path, "rb")
            bytes = fp.read()
            fp.close()
            md5 = hashlib.md5()
            md5.update(bytes)
            md5 = md5.hexdigest().lower()
        except Exception:
            md5 = "unreadable"
        files[name] = md5

    def get_python_settings(self):
        distributions = packages_distributions()
        settings = dict(python=sys.version)
        for name in distributions:
            for package in distributions[name]:
                settings[package] = version(package)
        return settings

    def get_mssql_settings(self):
        cursor = db.connect().cursor()
        cursor.execute("EXEC sp_server_info")
        settings = {}
        for attr_id, attr_name, attr_value in cursor.fetchall():
            settings[attr_name] = attr_value
        return settings

    def serialize(self):
        def dump(me):
            if isinstance(me, dict):
                print(f"dict keys: {me.keys()}")
                for value in me.values():
                    dump(value)
            elif isinstance(me, (list, tuple)):
                for item in me:
                    dump(item)
        # dump(self.windows)
        return json.dumps(dict(windows=self.windows), indent=2, default=str)

    def run(self):
        print(f"Content-type: application/json\n\n{self.serialize()}")


if __name__ == "__main__":
    fields = cdrcgi.FieldStorage()
    session = cdrcgi.getSession(fields)
    if not session or not cdr.canDo(session, "GET SYS CONFIG"):
        print("Status: 403\n\nUser not authorized for viewing system settings")
        sys.exit(0)
    if not fields.getvalue("prompt"):
        Settings(session).run()
        sys.exit(0)
    class Control(cdrcgi.Controller):
        TITLE = SUBTITLE = "Tier Settings"
        def populate_form(self, page):
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
    Control().run()
