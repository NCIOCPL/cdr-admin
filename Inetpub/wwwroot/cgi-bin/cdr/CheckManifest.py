#----------------------------------------------------------------------
# Preliminary test program for experimenting with methods of verifying
# that the files in the manifest can be read by the web server.
#----------------------------------------------------------------------
import lxml.etree as etree
import hashlib
import os
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    def __init__(self):
        cdrcgi.Control.__init__(self, "Client Manifest Check")
    def run(self):
        try:
            self.show_report()
        except Exception, e:
            cdrcgi.bail(str(e))
    def build_tables(self):
        manifest_files = self.parse_manifest()
        client_files = self.gather_files()
        cols = [cdrcgi.Report.Column(name) for name in ("Path", "Manifest",
                                                        "File", "Status")]
        rows = sorted(self.find_errors(manifest_files, client_files))
        self.subtitle = "%d error(s) found" % len(rows)
        return [cdrcgi.Report.Table(cols, rows)]
    def find_errors(self, manifest, client):
        errors = []
        MANIFEST_NAME = cdr.MANIFEST_NAME.upper()
        for key in manifest:
            if MANIFEST_NAME in key:
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
        tree = etree.parse(cdr.MANIFEST_PATH)
        files = {}
        for node in tree.getroot().findall("FileList/File"):
            f = File(node)
            files[f.path.upper()] = f
        return files
    def gather_files(self):
        os.chdir(cdr.CLIENT_FILES_DIR)
        files = {}
        for f in self.recurse("."):
            files[f.path.upper()] = f
        return files
    def recurse(self, dir_path):
        files = []
        for name in os.listdir(dir_path):
            this_path = os.path.join(dir_path, name)
            if os.path.isdir(this_path):
                files += self.recurse(this_path)
            else:
                files.append(File(path=this_path))
        return files
class File:
    def __init__(self, node=None, path=None):
        self.path = path
        self.checksum = self.error = None
        if node is not None:
            for child in node:
                if child.tag == "Name":
                    self.path = child.text
                elif child.tag == "Checksum":
                    self.checksum = child.text
        else:
            try:
                fp = open(path, "rb")
                bytes = fp.read()
                fp.close()
                m = hashlib.md5()
                m.update(bytes)
                self.checksum = m.hexdigest().lower()
            except Exception, e:
                self.error = str(e)
Control().run()
