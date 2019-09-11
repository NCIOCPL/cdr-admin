#----------------------------------------------------------------------
# Collect settings from this tier as JSON.
# OCECDR-4101
#----------------------------------------------------------------------
import cgi
import hashlib
import json
import os
import sys
import pkg_resources
import lxml.etree as etree
import requests
import cdr
import cdrdb
import cdrcgi
import cdrutil
from cdrapi.settings import Tier

class Settings:
    HOSTNAMES = Tier().hosts
    LOGFILE = f"{cdr.DEFAULT_LOGDIR}/fetch-tier-settings.log"
    WD = cdr.WORK_DRIVE
    WEBCONFIG_ROOT = "%s:/Inetpub/wwwroot/web.config" % WD
    WEBCONFIG_SECURE = "%s:/Inetpub/wwwroot/cgi-bin/secure/web.config" % WD
    def __init__(self, session):
        self.session = session
        self.org = cdrutil.getEnvironment()
        self.tier = cdrutil.getTier()
        self.glossifier = self.get_linux_settings("GLOSSIFIERC")
        self.emailers = self.get_linux_settings("EMAILERSC")
        self.windows = self.get_windows_settings()
    def get_linux_settings(self, key):
        args = self.HOSTNAMES[key], self.session
        url = "http://%s/cgi-bin/fetch-tier-settings.py?Session=%s" % args
        try:
            return json.loads(requests.get(url).text)
        except Exception as e:
            print(url, e)
            cdr.logwrite("%s: %s" % (url, e), self.LOGFILE)
            return {}
    def get_iis_settings(self):
        return {
            "account": cdr.runCommand("whoami").output.strip(),
            "version": os.environ.get("SERVER_SOFTWARE"),
            "web.config": {
                "root": self.xmltojson(self.WEBCONFIG_ROOT),
                "secure": self.xmltojson(self.WEBCONFIG_SECURE)
            }
        }
    def xmltojson(self, path):
        root = etree.parse(path).getroot()
        return { root.tag: self.extract_node(root) }
    def extract_node(self, node):
        children = {}
        for key in node.keys():
            children[key] = [node.get(key)]
        for child in node:
            if child.tag not in children:
                children[child.tag] = []
            children[child.tag].append(self.extract_node(child))
        for name in children:
            if len(children[name]) == 1:
                children[name] = children[name][0]
        return children
    def get_windows_settings(self):
        winver = sys.getwindowsversion()
        settings = { "version": {} }
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
        root = etree.parse("d:/cdr/ClientFiles/CdrDocTypes.xml").getroot()
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
        self.walk(files, "d:/cdr/lib")
        self.walk(files, "d:/cdr/Bin")
        self.walk(files, "d:/cdr/Build")
        self.walk(files, "d:/cdr/ClientFiles")
        self.walk(files, "d:/cdr/Licensee")
        self.walk(files, "d:/cdr/Mailers")
        self.walk(files, "d:/cdr/Publishing")
        self.walk(files, "d:/cdr/Licensee")
        self.walk(files, "d:/cdr/Licensee")
        self.walk(files, "d:/Inetpub/wwwroot")
        self.walk(files, "d:/usr/expat/Bin")
        self.walk(files, "d:/usr/Sablot/bin")
        self.walk(files, "d:/usr/xerces/bin")
        return files
    def walk(self, files, path):
        for path, dirs, filenames in os.walk(path):
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
        except Exception as e:
            md5 = "unreadable"
        files[name] = md5

    def get_python_settings(self):
        env = pkg_resources.Environment()
        settings = { "python": sys.version }
        for name in env:
            for package in env[name]:
                settings[package.project_name] = package.version
        return settings
    def get_mssql_settings(self):
        cursor = cdrdb.connect().cursor()
        cursor.execute("EXEC sp_server_info")
        settings = {}
        for attr_id, attr_name, attr_value in cursor.fetchall():
            settings[attr_name] = attr_value
        return settings
    def serialize(self):
        return json.dumps({
            "windows": self.windows,
            "glossifier": self.glossifier,
            "emailers": self.emailers
        }, indent=2)
    def run(self):
        print("Content-type: application/json\n\n%s" % self.serialize())
if __name__ == "__main__":
    fields = cgi.FieldStorage()
    session = cdrcgi.getSession(fields)
    if not session or not cdr.canDo(session, "GET SYS CONFIG"):
        print("Status: 403\n\nUser not authorized for viewing system settings")
        sys.exit(0)
    Settings(session).run()
