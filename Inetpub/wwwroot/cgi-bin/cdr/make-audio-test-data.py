#!/usr/bin/env python

"""Create sample data for the automated tests of the audio scripts.
"""

from functools import cached_property
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from paramiko import AutoAddPolicy, RSAKey, SSHClient
from cdrapi.docs import Doc
from cdrapi.settings import Tier
from cdrcgi import Controller, Excel, HTMLPage


class Control(Controller):
    """Processing logic."""

    SUBTITLE = "Create Audio Pronunciation Test Data"
    DOCTYPE = "GlossaryTermName"
    CLEANUP_SCRIPT = "remove-audio-test-data.py"
    ENGLISH_NAME = "sample term for unit tests"
    SPANISH_NAME = "término de prueba de muestra"
    PRONUNCIATION = "test SAM-pul term"
    COLUMNS = (
        ("CDR ID", 10),
        ("Term Name", 30),
        ("Language", 10),
        ("Pronunciation", 30),
        ("Filename", 30),
        ("Notes (Vanessa)", 20),
        ("Notes (NCI)", 30),
        ("Reuse Media ID", 15),
    )
    WEEK = "Week_2099_01"
    TIER = Tier()
    LOGNAME = "testing"
    USER = "cdroperator"
    SSH_KEY = "/etc/cdroperator_rsa"
    CDRSTAGING = "/sftp/sftphome/cdrstaging"
    AUDIO_DIR = f"{CDRSTAGING}/ciat/{TIER.name.lower()}/Audio"
    TARGET_DIR = f"{AUDIO_DIR}/Term_Audio"
    INSTRUCTIONS = (
        "This script generates two zip-compressed archives containing Excel "
        "workbooks and sample MP3 files, and stores those archive in the "
        "directory specified below. If you invoke this script directly, "
        "you should be careful to run the ",
        HTMLPage.B.A("companion script for cleaning up the test data"),
        " when you have finished so that user testing is not disrupted. "
        "This script supports automated testing, and should not be run on "
        "the production server."
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
                arg.set("href", self.make_url(self.CLEANUP_SCRIPT))
            args.append(arg)
        fieldset.append(page.B.P(*args))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optionally override the target location")
        opts = dict(value=self.target, label="Target Directory")
        fieldset.append(page.text_field("target", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Create and store the test data and re-draw the form."""

        if self.session.tier.name == "PROD":
            message = "This script cannot be used on the production server."
            self.alerts.append(dict(message=message, type="error"))
            return self.show_form()
        if not self.session.can_do("ADD DOCUMENT", self.DOCTYPE):
            message = "This account is not permitted to create term documents."
            self.alerts.append(dict(message=message, type="error"))
            return self.show_form()
        try:
            targets = (
                f"{self.target}/{self.WEEK}.zip",
                f"{self.target}/{self.WEEK}_Rev1.zip",
            )
            sources = (
                BytesIO(self.base_zipfile),
                BytesIO(self.followup_zipfile),
            )
            with self.connection.open_sftp() as sftp:
                sftp.putfo(sources[0], targets[0])
                message = f"Successfully stored {targets[0]}."
                self.alerts.append(dict(message=message, type="success"))
                sftp.putfo(sources[1], targets[1])
                message = f"Successfully stored {targets[1]}."
                self.alerts.append(dict(message=message, type="success"))
        except Exception as e:
            message = f"Failed pushing {targets[0]} and {targets[1]}"
            self.logger.exception(message)
            self.alerts.append(dict(message=f"{message}: {e}", type="error"))
        self.show_form()

    @cached_property
    def connection(self):
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
    def doc(self):
        """Sample test glossary term document."""

        doc = Doc(self.session, doctype=self.DOCTYPE, xml=self.xml)
        doc.save()
        message = f"Created test GlossaryTermName document {doc.cdr_id}."
        self.alerts.append(dict(message=message, type="success"))
        return doc

    @cached_property
    def mp3(self):
        """Bytes for test MP3 file (contains two minutes of silence)."""

        path = Path(__file__).parent.parent.parent / "tests" / "test.mp3"
        return path.read_bytes()

    @cached_property
    def same_window(self):
        """Don't create any new browser tabs."""
        return [self.SUBMIT]

    @cached_property
    def server(self):
        """Local name of the SFTP server."""
        return self.session.tier.hosts["SFTP"].split(".")[0]

    @cached_property
    def target(self):
        """Directory in which we store the test archive."""

        target = self.fields.getvalue("target") or self.TARGET_DIR
        self.logger.info("Target directory: %s", target)
        return target

    @cached_property
    def xml(self):
        """Serialized XML for the sample glossary document."""

        root = etree.Element(self.DOCTYPE, nsmap=Doc.NSMAP)
        child = etree.SubElement(root, "TermName")
        etree.SubElement(child, "TermNameString").text = self.ENGLISH_NAME
        child = etree.SubElement(root, "TranslatedName")
        etree.SubElement(child, "TermNameString").text = self.SPANISH_NAME
        opts = dict(pretty_print=True, encoding="utf-8")
        return etree.tostring(root, **opts)

    @cached_property
    def base_workbook(self):
        """Bytes for first workbook of test audio pronunciations."""

        excel = Excel(self.WEEK)
        excel.add_sheet("Term Names")
        styles = dict(alignment=excel.center, font=excel.bold)
        col = 1
        for col, (name, width) in enumerate(self.COLUMNS, start=1):
            excel.set_width(col, width)
            excel.write(1, col, name, styles)
        excel.write(2, 1, self.doc.id)
        excel.write(2, 2, self.ENGLISH_NAME)
        excel.write(2, 3, "English")
        excel.write(2, 4, self.PRONUNCIATION)
        excel.write(2, 5, f"{self.WEEK}/{self.doc.id}_en.mp3")
        excel.write(3, 1, self.doc.id)
        excel.write(3, 2, self.SPANISH_NAME)
        excel.write(3, 3, "Spanish")
        excel.write(3, 5, f"{self.WEEK}/{self.doc.id}_es.mp3")
        excel.write(3, 6, "I think this is right")
        iobytes = BytesIO()
        excel.book.save(iobytes)
        return iobytes.getvalue()

    @cached_property
    def base_zipfile(self):
        """File to be dropped on the s/FTP server."""

        iobytes = BytesIO()
        zipfile = ZipFile(iobytes, "w")
        zipfile.writestr(f"{self.WEEK}/{self.WEEK}.xlsx", self.base_workbook)
        zipfile.writestr(f"{self.WEEK}/{self.doc.id}_en.mp3", self.mp3)
        zipfile.writestr(f"{self.WEEK}/{self.doc.id}_es.mp3", self.mp3)
        zipfile.close()
        return iobytes.getvalue()

    @cached_property
    def followup_workbook(self):
        """Bytes for a second workbook."""

        excel = Excel(f"{self.WEEK}_Rev1")
        excel.add_sheet("Term Names")
        styles = dict(alignment=excel.center, font=excel.bold)
        col = 1
        for col, (name, width) in enumerate(self.COLUMNS, start=1):
            excel.set_width(col, width)
            excel.write(1, col, name, styles)
        excel.write(2, 1, self.doc.id)
        excel.write(2, 2, self.SPANISH_NAME)
        excel.write(2, 3, "Spanish")
        excel.write(2, 5, f"{self.WEEK}_Rev1/{self.doc.id}_es.mp3")
        excel.write(2, 6, "Second time's the charm!")
        iobytes = BytesIO()
        excel.book.save(iobytes)
        return iobytes.getvalue()

    @cached_property
    def followup_zipfile(self):
        """Second file to be dropped on the s/FTP server."""

        iobytes = BytesIO()
        zipfile = ZipFile(iobytes, "w")
        workbook = self.followup_workbook
        zipfile.writestr(f"{self.WEEK}_Rev1/{self.WEEK}_Rev1.xlsx", workbook)
        zipfile.writestr(f"{self.WEEK}_Rev1/{self.doc.id}_es.mp3", self.mp3)
        zipfile.close()
        return iobytes.getvalue()


# Don't run script if loaded as a module.
if __name__ == "__main__":
    Control().run()
