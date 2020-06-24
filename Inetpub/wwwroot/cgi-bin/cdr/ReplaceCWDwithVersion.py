#!/usr/bin/env python

"""Replace working version of a document with an earlier version.

Used when the most recent copy of a document has problems and
we wish to revert to an earlier version.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Top-level logic controller for the tool."""

    SUBTITLE = "Replace CWD With Older Version"
    INSTRUCTIONS = (
        ("This program will replace the current working version of "
         "a document with the XML text of an earlier version. It "
         "can be used to restore the status of a document after it "
         "was damaged in some way. The Doc ID and Version fields "
         "are both required.", False),
        ("Warning!  Replacing the CWD with an older version will "
         "obscure and complicate the true version history and will "
         "override recent changes. Therefore this function should "
         "be used very sparingly, only when there is a serious "
         "problem with the CWD that cannot be recovered by a simple "
         "edit.", True),
    )
    TOOLTIP = (
        "Version to promote\n"
        "(use -1 for last version, -2 for next-to-last, etc.)"
    )
    OPTIONS = (
        ("create-version", "Also create new version"),
        ("pub-version", "Make new version publishable"),
    )
    ACTION = "REPLACE CWD WITH VERSION"
    CONFIRM = "Confirm"
    CANCEL = "Cancel"
    CAPTION = (
        "Click Confirm to perform action(s).",
        "Click Cancel to start over.",
    )
    CSS = (
        "body.report, th, td { background-color: #e8e8e8; }",
        "caption {color: green; }",
    )

    def run(self):
        """Override base version to support custom actions."""

        if not self.session.can_do(self.ACTION):
            self.bail("Unauthorized")
        try:
            if self.request == self.CONFIRM:
                return self.replace()
            elif self.request == self.CANCEL:
                return self.show_form()
        except Exception as e:
            self.logger.exception("replacement failure")
            self.bail(e)
        Controller.run(self)

    def populate_form(self, page):
        """As the user for the required information.

        Pass:
            page - object on which we place the form fields
        """

        fieldset = page.fieldset("Instructions")
        for paragraph, strong in self.INSTRUCTIONS:
            p = page.B.P(paragraph)
            if strong:
                p.set("class", "strong warning")
            fieldset.append(p)
        page.form.append(fieldset)
        fieldset = page.fieldset("Replacement Information")
        fieldset.append(page.text_field("id", label="Doc ID"))
        fieldset.append(page.text_field("version", tooltip=self.TOOLTIP))
        fieldset.append(page.textarea("comment", tooltip="Reason for change"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        for value, label in self.OPTIONS:
            opts = dict(value=value, label=label, checked=True)
            fieldset.append(page.checkbox("opts", **opts))
        page.form.append(fieldset)

    @property
    def report(self):
        """Show the user what we're planning to do."""

        if not self.session.can_do("MODIFY DOCUMENT", self.doc.doctype.name):
            self.bail("Not authorized")
        if not self.version:
            self.bail("No version specified")
        if not hasattr(self, "_report"):
            values = (
                ("Replace CWD for", self.doc.cdr_id),
                ("Document type", self.doc.doctype.name),
                ("Document title", self.doc.title),
                ("Current total versions", len(self.versions)),
                ("Make this version the CWD", self.version),
                ("Also create a new version", self.create_version),
                ("Make version publishable", self.make_version_publishable),
                ("Reason to be logged", self.comment),
            )
            rows = []
            opts = dict(bold=True, right=True)
            for label, value in values:
                rows.append((self.Reporter.Cell(label, **opts), value))
            table = self.Reporter.Table(rows, caption=self.CAPTION)
            buttons = (
                self.HTMLPage.button(self.CONFIRM),
                self.HTMLPage.button(self.CANCEL),
                self.HTMLPage.button(self.ADMINMENU),
                self.HTMLPage.button(self.LOG_OUT),
            )
            opts = dict(
                banner=self.title,
                subtitle=self.SUBTITLE,
                page_opts=dict(
                    buttons=buttons,
                    session=self.session,
                    action=self.script,
                ),
            )
            self._report = self.Reporter(self.title, [table], **opts)
            page = self._report.page
            form = page.form
            form.append(page.hidden_field("id", self.doc.id))
            form.append(page.hidden_field("version", self.version))
            if self.create_version:
                form.append(page.hidden_field("opts", "create-version"))
            if self.make_version_publishable:
                form.append(page.hidden_field("opts", "pub-version"))
            if self.comment:
                form.append(page.hidden_field("comment", self.comment))
            page.add_css("\n".join(self.CSS))
        return self._report

    def replace(self):
        """Promote the selected version, log the action, and show the form."""

        if not self.session.can_do("MODIFY DOCUMENT", self.doc.doctype.name):
            self.bail("Not authorized")
        if not self.version:
            self.bail("No version specified")
        comment = f"Replacing CWD with version {self.version:d}"
        doc = Doc(self.session, id=self.doc.id, version=self.version)
        doc.check_out(comment=comment)
        pub_ver = self.make_version_publishable
        if self.comment:
            comment = f"{comment}: {self.comment}"
        opts = dict(
            version=self.create_version,
            publishable=pub_ver,
            val_types=("schema", "links") if pub_ver else None,
            comment=comment,
            reason=comment,
            unlock=True,
        )
        doc.save(**opts)
        path = f"{self.session.tier.logdir}/CWDReplacements.log"
        try:
            with open(path, "a", encoding="utf-8") as fp:
                fp.write(f"{self.message}\n")
        except IOError as e:
            self.bail(f"Error writing to {path}: {e}")
        self.show_form()

    @property
    def comment(self):
        """Explanation for replacement."""
        return self.fields.getvalue("comment")

    @property
    def doc(self):
        """Document object for CWD of selected CDR document."""

        if not hasattr(self, "_doc"):
            self._doc = self.fields.getvalue("id")
            if self._doc:
                self._doc = Doc(self.session, id=self._doc)
        return self._doc

    @property
    def create_version(self):
        """True if we should create a new version."""
        return self.make_version_publishable or "create-version" in self.opts

    @property
    def make_version_publishable(self):
        """True if we should make the new version publishable."""
        return "pub-version" in self.opts

    @property
    def message(self):
        """Log entry to record what was done."""

        if not hasattr(self, "_message"):
            values = (
                self.started.strftime("%Y-%m-%d %H:%M:%S"),
                self.doc.id,
                self.doc.doctype,
                self.session.user_name,
                self.doc.last_version or -1,
                self.doc.last_publishable_version or -1,
                "Y" if self.doc.has_unversioned_changes else "N",
                self.version,
                "Y" if self.create_version else "N",
                "Y" if self.make_version_publishable else "N",
                self.comment or "",
            )
            self._message = "\t".join([str(value) for value in values])
        return self._message

    @property
    def opts(self):
        """Versioning options."""
        return self.fields.getlist("opts")

    @property
    def subtitle(self):
        """What to display below the main banner."""

        if self.request == self.CONFIRM:
            return "Replacement successful."
        else:
            return self.SUBTITLE

    @property
    def version(self):
        """Integer for the version to promote as the replacement."""

        if not hasattr(self, "_version"):
            self._version = self.fields.getvalue("version")
            if self._version:
                if not self.doc:
                    self.bail("Document ID is required")
                try:
                    self._version = int(self._version)
                except Exception:
                    self.bail("Version must be a positive or negative integer")
                if self._version < 0:
                    if abs(self._version) > len(self.versions):
                        self.bail(f"Only {len(self.versions)} versions found")
                    self._version = self.versions[self._version]
                elif self._version not in self.versions:
                    self.bail(f"Version {self._version} does not exist")
        return self._version

    @property
    def versions(self):
        """Sequence of all version IDs for the selected document."""

        if not hasattr(self, "_versions"):
            versions = [values[0] for values in self.doc.list_versions()]
            self._versions = list(reversed(versions))
        return self._versions


if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
