#!/usr/bin/env python

"""Remove sample data used by the automated tests of the audio scripts.
"""

from functools import cached_property
from pathlib import Path
from paramiko import AutoAddPolicy, RSAKey, SSHClient
from cdrapi.docs import Doc
from cdrapi.settings import Tier
from cdrcgi import Controller, HTMLPage


class Control(Controller):
    """Processing logic."""

    SUBTITLE = "Remove Audio Pronunciation Test Data"
    CREATE_SCRIPT = "make-audio-test-data.py"
    DOCTYPE = "GlossaryTermName"
    ENGLISH_NAME = "sample term for unit tests"
    SPANISH_NAME = "término de prueba de muestra"
    WEEK = "Week_2099_01"
    TIER = Tier()
    LOGNAME = "testing"
    USER = "cdroperator"
    SSH_KEY = r"\etc\cdroperator_rsa"
    CDRSTAGING = "/sftp/sftphome/cdrstaging"
    SFTP_DIR = f"{CDRSTAGING}/ciat/{TIER.name.lower()}/Audio"
    CDR_DIR = f"{TIER.basedir}/Audio_from_CIPSFTP"
    INSTRUCTIONS = (
        "This script cleans up any test data left by the audio testing "
        "scripts. If custom locations were used for a test, adjust the "
        "locations below as appropriate. Note that the remote directory "
        "is one level higher than the target directory for the ",
        HTMLPage.B.A("script used for generating the test data"),
        ", because this cleanup script also needs to take care of any "
        "archives moved to the sibling Audio_Transferred directory."
    )

    def populate_form(self, page):
        """Add fields to the form.

        Pass:
            page - HTMLPage object to be populated
        """

        fieldset = page.fieldset("Instructions")
        args = []
        for arg in self.INSTRUCTIONS:
            if not isinstance(arg, str):
                arg.set("href", self.make_url(self.CREATE_SCRIPT))
            args.append(arg)
        fieldset.append(page.B.P(*args))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optionally override the file locations")
        opts = dict(value=self.sftp_dir, label="Remote Audio Directory")
        fieldset.append(page.text_field("sftp-dir", **opts))
        opts = dict(value=self.cdr_dir, label="CDR Audio Directory")
        fieldset.append(page.text_field("cdr-dir", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Create and store the test data and re-draw the form."""

        if self.session.tier.name == "PROD":
            message = "This script cannot be used on the production server."
            self.alerts.append(dict(message=message, type="error"))
            return self.show_form()
        if not self.session.can_do("DELETE DOCUMENT", self.DOCTYPE):
            message = "This account is not permitted to delete term documents."
            self.alerts.append(dict(message=message, type="error"))
            return self.show_form()
        try:
            for doc in self.docs:
                doc.delete()
                message = f"Deleted {doc.doctype} document {doc.cdr_id}."
                self.logger.info(message)
                self.alerts.append(dict(message=message, type="success"))
            for archive in self.remote_archives:
                self.connection.exec_command(f"rm {archive}")
                message = f"Removed remote {archive}."
                self.logger.info(message)
                self.alerts.append(dict(message=message, type="success"))
            for archive in self.local_archives:
                archive.unlink()
                message = f"Removed local {archive}."
                self.logger.info(message)
                self.alerts.append(dict(message=message, type="success"))
            self.cursor.execute(
                "DELETE FROM term_audio_mp3"
                " WHERE mp3_name LIKE 'Week_2099%'"
            )
            if self.cursor.rowcount > 0:
                s = "s" if self.cursor.rowcount > 1 else ""
                message = (
                    f"Removed {self.cursor.rowcount} row{s} "
                    "from the term_audio_mp3 table."
                )
                self.alerts.append(dict(message=message, type="success"))
                self.conn.commit()
            self.cursor.execute(
                "DELETE FROM term_audio_zipfile"
                " WHERE filename LIKE 'Week_2099%'"
            )
            if self.cursor.rowcount > 0:
                s = "s" if self.cursor.rowcount > 1 else ""
                message = (
                    f"Removed {self.cursor.rowcount} row{s} "
                    "from the term_audio_zipfile table."
                )
                self.alerts.append(dict(message=message, type="success"))
                self.conn.commit()
        except Exception as e:
            message = f"Cleanup failure"
            self.logger.exception(message)
            self.alerts.append(dict(message=f"{message}: {e}", type="error"))
        if self.nothing_to_do:
            message = "Nothing found to remove."
            self.logger.info(message)
            self.alerts.append(dict(message=message, type="info"))
        self.show_form()

    @cached_property
    def cdr_dir(self):
        """Local directory where the audio pronunciation sets are stored."""
        return Path(self.fields.getvalue("cdr-dir") or self.CDR_DIR)

    @cached_property
    def connection(self) -> SSHClient:
        """Connection to the SFTP server."""

        connection = SSHClient()
        policy = AutoAddPolicy()
        connection.set_missing_host_key_policy(policy)
        pkey = RSAKey.from_private_key_file(self.SSH_KEY)
        opts = dict(hostname=self.server, username=self.USER, pkey=pkey)
        self.logger.info("Connecting to %s ...", self.server)
        connection.connect(**opts)
        self.logger.info("Connected")
        return connection

    @cached_property
    def docs(self):
        """Sample test glossary term documents to be removed."""

        query = self.Query("document", "id").order("id")
        query.where(f"title LIKE '{self.ENGLISH_NAME}%'") # OR title LIKE 'test sample term%'")
        rows = query.execute(self.cursor).fetchall()
        return [Doc(self.session, id=row.id) for row in rows]

    @cached_property
    def local_archives(self):
        """The test audio sets found on the local CDR server."""
        return [a for a in self.cdr_dir.glob(f"{self.WEEK}*.zip")]

    @cached_property
    def nothing_to_do(self):
        """If there's nothing to remove, we'll tell the user that."""

        if self.docs or self.local_archives or self.remote_archives:
            return False
        query = self.Query("term_audio_zipfile", "COUNT(*) AS n")
        query.where("filename LIKE 'Week_2099%'")
        if query.execute(self.cursor).fetchone().n > 0:
            return False
        query = self.Query("term_audio_mp3", "COUNT(*) AS n")
        query.where("mp3_name LIKE 'Week_2099%'")
        if query.execute(self.cursor).fetchone().n > 0:
            return False

        return True

    @cached_property
    def remote_archives(self):
        """All the test audio sets found on the s/FTP server."""

        command = f"ls {self.sftp_dir}/*/{self.WEEK}*"
        _, stdout, _ = self.connection.exec_command(command)
        return [archive.strip() for archive in stdout]

    @cached_property
    def same_window(self):
        """Don't create any new browser tabs."""
        return [self.SUBMIT]

    @cached_property
    def server(self):
        """Local name of the SFTP server."""
        return self.session.tier.hosts["SFTP"].split(".")[0]

    @cached_property
    def sftp_dir(self):
        """Directory on the s/FTP server where audio sets are put."""
        return self.fields.getvalue("sftp-dir") or self.SFTP_DIR


# Don't run script if loaded as a module.
if __name__ == "__main__":
    Control().run()
