#!/usr/bin/env python

"""Pull audio files from the SFTP server to the CDR server.
"""

from glob import glob
import os
import re
import paramiko
from cdrcgi import Controller
from cdrapi.settings import Tier
from cdr import run_command
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
from openpyxl import load_workbook

class Control(Controller):
    """Processing logic."""

    TIER = Tier()
    SUBTITLE = "Retrieve Audio Files From CIPSFTP Server"
    LOGNAME = "FtpAudio"
    USER = "cdroperator"
    WEEK = r"^Week_\d{4}_\d\d(_Rev\d)?"
    FILE = r"\d+_e[ns]\d*"
    SSH_KEY = r"\etc\cdroperator_rsa"
    CDRSTAGING = "/sftp/sftphome/cdrstaging"
    AUDIO_DIR = f"{CDRSTAGING}/ciat/{TIER.name.lower()}/Audio"
    SOURCE_DIR = f"{AUDIO_DIR}/Term_Audio"
    TARGET_DIR = f"{TIER.basedir}/Audio_from_CIPSFTP"
    TRANSFERRED_DIR = f"{AUDIO_DIR}/Audio_Transferred"
    INSTRUCTIONS = (
        "Files which match the pattern Week_YYYY_WW.zip (or, for correction "
        "batches, Week_YYYY_WW_RevN.zip) will be retrieved from the source "
        "directory on the NCI SFTP server and placed in the target "
        "directory on the Windows CDR server. Then they will be moved "
        "on the SFTP server to the a separate directory for zip files "
        "which have already been transferred to the CDR server (referred "
        "to below as the Transferred directory). By default, retrieval "
        "of a zip file will be skipped if the file already exists on "
        "the Windows CDR server (though this can be overridden). "
        "In test mode, the retrievals will be reported as having been "
        "performed, even though that step will not actually take place, "
        "and the zip file will be copied to a unique (time-stamped) name "
        "(instead of moved) to the Transferred directory."
    )
    BUFSIZE = 2**15

    def populate_form(self, page):
        """Add fields to the form.

        Pass:
            page - HTMLPage object to be populated
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Directories")
        fieldset.set("id", "paths")
        fieldset.append(page.text_field("source", value=self.SOURCE_DIR))
        fieldset.append(page.text_field("destination", value=self.TARGET_DIR))
        opts = dict(value=self.TRANSFERRED_DIR)
        fieldset.append(page.text_field("transferred", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        label = "Don't move source documents to 'Transferred' directory"
        opts = dict(value="keep", label=label)
        fieldset.append(page.checkbox("options", **opts))
        opts = dict(value="test", label="Run in test mode")
        fieldset.append(page.checkbox("options", **opts))
        label = "Overwrite files in target directory if they already exist"
        opts = dict(value="overwrite", label=label)
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)
        page.add_css("fieldset {width:600px} #paths input {width:400px}")

    def build_tables(self):
        """Perform the retrievals and report the processing outcome."""

        if not self.session.can_do("AUDIO DOWNLOAD"):
            self.bail("Not authorized")
        self.logger.info("Running in %s mode", self.mode)
        lines = [
            f"Processing mode: {self.mode}",
            f"Source directory: {self.source_dir}",
            f"Destination directory: {self.destination_dir}",
            f"Transferred directory: {self.transferred_dir}",
        ]
        if not self.zipfiles:
            lines.append("No zip files found to be transferred")
        else:
            errors = []
            for name in self.zipfiles:
                errors += self.check_mp3_paths(name)
            if errors:
                lines += errors
                lines.append("Retrieval aborted by failed MP3 path checks")
            else:
                for name in self.zipfiles:
                    lines += self.retrieve(name)
        for name in self.rejected:
            lines.append(f"Skipped {name}")
        rows = [[line] for line in lines]
        caption = "Processing Results"
        return self.Reporter.Table(rows, caption=caption)

    def retrieve(self, name):
        """Transfer zipfile if appropriate and possible.

        Pass:
            name - string for the name of the zipfile to transfer

        Return:
           array of strings for the processing results table
        """

        source = f"{self.source_dir}/{name}"
        target = f"{self.destination_dir}/{name}"
        retrieve = not self.test
        if name.lower() in self.already_transferred:
            if self.overwrite:
                line = f"Retrieved {name}, overwriting existing file"
            else:
                line = f"Skipping {name}, which already exists"
                retrieve = False
        else:
            line = f"Retrieved {name}"
        failed = False

        if retrieve:
            try:
                with self.connection.open_sftp() as sftp:
                    sftp.get(source, target)
            except Exception as e:
                self.logger.exception("Retrieving %s", source)
                line = f"Failed retrieval of {name}: {e}"
                failed = True

            process = run_command(f"fix-permissions {target}")
            if process.stderr:
                self.bail(f"Unable to fix permissions for {target}",
                          extra=[process.stderr])

        lines = [line]
        if not failed and not self.keep:
            target = f"{self.transferred_dir}/{name}"
            program = "cp" if self.test else "mv"
            if self.test:
                target += f"-{self.stamp}"
            cmd = f"{program} {source} {target}"
            stdin, stdout, stderr = self.connection.exec_command(cmd)
            errors = stderr.readlines()
            if errors:
                if self.test:
                    lines.append(f"Errors copying {name} to {target}")
                else:
                    lines.append(f"Errors moving {name} to {target}")
                lines += errors
            elif self.test:
                lines.append(f"Copied {name} to {target}")
            else:
                lines.append(f"Moved {name} to {target}")
        return lines

    def check_mp3_paths(self, filename):
        """Make sure the spreadsheet and zip file MP3 paths match.

        Also ensures that the paths follow the pattern convention
        established for the audio files.

        Pass:
           filename - string for the name of the zipfile to inspect

        Return:
           Possibly empty sequence of error strings
        """

        with self.connection.open_sftp() as sftp:
            zip_path = f"{self.source_dir}/{filename}"
            with sftp.open(zip_path, bufsize=self.BUFSIZE) as fp:
                zipfile = ZipFile(BytesIO(fp.read()))
        self.logger.info("Verifying MP3 paths in %s", zip_path)
        mp3_paths = set()
        col_paths = set()
        errors = []
        for name in zipfile.namelist():
            normalized = name.lower()
            if "macosx" not in normalized:
                if normalized.endswith(".mp3"):
                    mp3_paths.add(name)
                elif normalized.endswith(".xlsx"):
                    opts = dict(read_only=True, data_only=True)
                    book = load_workbook(BytesIO(zipfile.read(name)), **opts)
                    sheet = book.active
                    headers = True
                    for row in sheet:
                        if headers:
                            headers = False
                        else:
                            try:
                                value = row[4].value
                                if not isinstance(value, str):
                                    errors.append("Missing MP3 path")
                                else:
                                    col_paths.add(value)
                            except:
                                errors.append("Missing MP3 path")
        all_paths = mp3_paths | col_paths
        for path in all_paths:
            if not self.member_pattern.match(path):
                errors.append(f"{filename} has invalid MP3 path format {path}")
        missing = col_paths - mp3_paths
        for path in missing:
            errors.append(f"{filename} does not contain {path}")
        unused = mp3_paths - col_paths
        for path in unused:
            errors.append(f"{filename} has unused MP3 file {path}")
        return errors

    @property
    def connection(self):
        """Connection to the SFTP server."""

        if not hasattr(self, "_connection"):
            self._connection = paramiko.SSHClient()
            policy = paramiko.AutoAddPolicy()
            self._connection.set_missing_host_key_policy(policy)
            pkey = paramiko.RSAKey.from_private_key_file(self.SSH_KEY)
            opts = dict(hostname=self.server, username=self.USER, pkey=pkey)
            self.logger.info("Connecting to %s ...", self.server)
            self._connection.connect(**opts)
            self.logger.info("Connected")
        return self._connection

    @property
    def destination_dir(self):
        """Directory to which we copy the audio zip archives."""

        if not hasattr(self, "_destination_dir"):
            directory = self.fields.getvalue("destination")
            if not os.path.exists(directory):
                try:
                    os.mkdir(directory)
                except Exception as e:
                    self.logger.exception("Creating %s", directory)
                    self.bail(e)
            self.logger.info("Destination directory: %s", directory)
            self._destination_dir = directory
        return self._destination_dir

    @property
    def keep(self):
        """If True, don't move files to transferred directory."""
        return "keep" in self.options

    @property
    def mode(self):
        """One of 'test' or 'live' values."""
        return "test" if self.test else "live"

    @property
    def names(self):
        """All the file names found in the source directory."""

        if not hasattr(self, "_names"):
            command = f"ls {self.SOURCE_DIR}/*"
            self.logger.info("Running %s", command)
            stdin, stdout, stderr = self.connection.exec_command(command)
            self._names = []
            for name in stdout.readlines():
                self._names.append(name.split("/")[-1].strip())
        return self._names

    @property
    def already_transferred(self):
        """Zipfiles which already existing in the destination directory."""

        if not hasattr(self, "_already_transferred"):
            os.chdir(self.destination_dir)
            names = glob("*.zip")
            self.logger.info("Target dir has %s", names)
            self._already_transferred = set([name.lower() for name in names])
        return self._already_transferred

    @property
    def options(self):
        """Overrides of runtime defaults."""
        if not hasattr(self, "_options"):
            self._options = self.fields.getlist("options")
        return self._options

    @property
    def overwrite(self):
        """Boolean indicating whether it is OK to overwrite target files."""
        return "overwrite" in self.options

    @property
    def pattern(self):
        """Files we want will match this regular expression."""

        if not hasattr(self, "_pattern"):
            self._pattern = re.compile(f"^{self.WEEK}.zip$")
        return self._pattern

    @property
    def member_pattern(self):
        """Members of zip files must match this regular expression."""

        if not hasattr(self, "_member_pattern"):
            self._member_pattern = re.compile(f"^{self.WEEK}/{self.FILE}.mp3$")
        return self._member_pattern

    @property
    def rejected(self):
        """File names which don't match our naming convention.

        We don't have to do anything but reference the `zipfiles`
        property, which takes care of populating both its own
        property and this one.
        """

        if self.zipfiles and not hasattr(self, "_rejected"):
            self.bail("Internal error")
        return self._rejected

    @property
    def server(self):
        """Local name of the SFTP server."""

        if not hasattr(self, "_server"):
            self._server = self.session.tier.hosts["SFTP"].split(".")[0]
        return self._server

    @property
    def source_dir(self):
        """Directory from which we copy the audio zip archives."""

        if not hasattr(self, "_source_dir"):
            self._source_dir = self.fields.getvalue("source")
            self.logger.info("Source directory: %s", self._source_dir)
        return self._source_dir

    @property
    def stamp(self):
        """String used to name files moved in test mode."""

        if not hasattr(self, "_stamp"):
            self._stamp = self.started.strftime("%Y%m%d%H%M%S")
        return self._stamp

    @property
    def test(self):
        """Are we testing the waters instead of running in live mode?"""
        return "test" in self.options

    @property
    def transferred_dir(self):
        """Directory where source files are moved after being transferred."""

        if not hasattr(self, "_transferred_dir"):
            directory = self.fields.getvalue("transferred")
            self.logger.info("Transferred directory: %s", directory)
            self._transferred_dir = directory
        return self._transferred_dir

    @property
    def zipfiles(self):
        """Names of files to be transferred."""

        if not hasattr(self, "_zipfiles"):
            zipfiles = []
            rejected = []
            for name in self.names:
                if self.pattern.match(name):
                    zipfiles.append(name)
                else:
                    rejected.append(name)
            self._zipfiles = zipfiles
            if not hasattr(self, "_rejected"):
                self._rejected = rejected
            if not zipfiles:
                self.logger.warning("No audio archive files found")
            else:
                self.logger.info("%d audio archive files found", len(zipfiles))
            for name in zipfiles:
                self.logger.info(name)
            if rejected:
                self.logger.warning("Ignored files: %r", rejected)
        return self._zipfiles


if __name__ == "__main__":
    """Don't run script if loaded as a module."""
    Control().run()
