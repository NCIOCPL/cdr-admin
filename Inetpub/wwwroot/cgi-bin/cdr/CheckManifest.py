#!/usr/bin/env python

"""Determine whether the manifest for client files is up to date.
"""

import hashlib
import os
import cdr
from cdrcgi import Controller, Reporter
import lxml.etree as etree

class Control(Controller):

    SUBTITLE = "Client Manifest Check"
    COLNAMES = "Path", "Manifest", "File", "Status"
    MANIFEST_NAME = cdr.MANIFEST_NAME.upper()

    def populate_form(self, form):
        """Bypass the form, going straight to the report."""
        self.show_report()

    def build_tables(self):
        """Show the problems found in the manifest, if any."""
        manifest_files = self.parse_manifest()
        client_files = self.gather_files()
        rows = sorted(self.find_errors(manifest_files, client_files))
        caption = f"{len(rows):d} error(s) found"
        return Reporter.Table(rows, columns=self.COLNAMES, caption=caption)

    def find_errors(self, manifest, client):
        """Compare the manifest with the files looking for problems.

        Pass:
            manifest
                dictionary of `File` objects pulled from the manifest
            client
                dictionary of `File` objects representing the file system

        Return:
            sequence of tuples representing problems found
        """
        errors = []
        for key in manifest:
            if self.MANIFEST_NAME in key:
                continue
            f = manifest[key]
            if key not in client:
                errors.append((f.path, f.checksum, None, "File missing"))
            else:
                c = client[key]
                if c.error:
                    errors.append((f.path, f.checksum, None, c.error))
                elif f.checksum != c.checksum:
                    errors.append((f.path, f.checksum, c.checksum,
                                   "Checksums don't match"))
        for key in client:
            if key not in manifest:
                f = client[key]
                errors.append((f.path, None, f.checksum, "Not in manifest"))
        return errors

    def parse_manifest(self):
        """Create dictionary of `File` objects for nodes in the manifest."""
        tree = etree.parse(cdr.MANIFEST_PATH)
        files = {}
        for node in tree.getroot().findall("FileList/File"):
            f = File(node)
            files[f.path.upper()] = f
        return files

    def gather_files(self):
        """Create a dictionary of `File` objects for the client files."""
        os.chdir(cdr.CLIENT_FILES_DIR)
        files = {}
        for f in self.recurse("."):
            files[f.path.upper()] = f
        return files

    def recurse(self, dir_path):
        """Do the real work for the `gather_files()` method.

        Pass:
            dir_path
                string for the directory in which to look for files

        Return:
            sequence of `File` objects
        """
        files = []
        for name in os.listdir(dir_path):
            this_path = os.path.join(dir_path, name)
            if os.path.isdir(this_path):
                files += self.recurse(this_path)
            else:
                files.append(File(path=this_path))
        return files


class File:
    """Capture the checksum and file path for a CDR client file.

    Can represent information from a node in the manifest or
    information from a file on the disk.
    """

    def __init__(self, node=None, path=None):
        """Remember the path and get the file's checksum.

        Pass either a node object if parsing the manifest, or
        a path string if traversing the file system.
        """

        # Initialize the attributes.
        self.path = path
        self.checksum = self.error = None

        # Parse the node if this is from the manifest.
        if node is not None:
            for child in node:
                if child.tag == "Name":
                    self.path = child.text
                elif child.tag == "Checksum":
                    self.checksum = child.text

        # Otherwise, get the bytes from the file and calculate the checksum.
        else:
            try:
                with open(path, "rb") as fp:
                    file_bytes = fp.read()
                m = hashlib.md5()
                m.update(file_bytes)
                self.checksum = m.hexdigest().lower()
            except Exception as e:
                self.error = str(e)


Control().run()
