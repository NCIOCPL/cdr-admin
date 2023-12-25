#!/usr/bin/env python

"""Replace working version of a document with an earlier version.

Used when the most recent copy of a document has problems and
we wish to revert to an earlier version.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Top-level logic controller for the tool."""

    SUBTITLE = "Replace CWD With Older Version"
    LOGNAME = "ReplaceCWD"
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
        "caption {color: green; }",
    )

    def populate_form(self, page):
        """Ask the user for the required information.

        Pass:
            page - object on which we place the form fields
        """

        fieldset = page.fieldset("Instructions")
        for paragraph, strong in self.INSTRUCTIONS:
            p = page.B.P(paragraph)
            if strong:
                p.set("class", "text-secondary-vivid")
            fieldset.append(p)
        page.form.append(fieldset)
        fieldset = page.fieldset("Replacement Information")
        fieldset.append(page.text_field("id", label="Doc ID", value=self.id))
        opts = dict(value=self.version, tooltip=self.TOOLTIP)
        fieldset.append(page.text_field("version", **opts))
        opts = dict(value=self.comment, tooltip="Reason for change")
        fieldset.append(page.textarea("comment", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        for value, label in self.OPTIONS:
            opts = dict(value=value, label=label)
            if not self.request or getattr(self, value.replace("-", "_")):
                opts["checked"] = True
            fieldset.append(page.checkbox("opts", **opts))
        page.form.append(fieldset)

    def replace(self):
        """Promote the selected version, log the action, and show the form."""

        if not self.session.can_do("MODIFY DOCUMENT", self.doc.doctype.name):
            self.alerts.append(dict(
                message="Account not authorized to perform this operation.",
                type="error",
            ))
        elif self.ready:
            comment = f"Replacing CWD with version {self.version:d}"
            doc = Doc(self.session, id=self.doc.id, version=self.version)
            doc.check_out(comment=comment)
            if self.comment:
                comment = f"{comment}: {self.comment}"
            opts = dict(
                version=self.create_version,
                publishable=self.pub_version,
                val_types=("schema", "links") if self.pub_version else None,
                comment=comment,
                reason=comment,
                unlock=True,
            )
            doc.save(**opts)
            for error in doc.errors:
                level = error.level
                if level not in ("error", "warning"):
                    level = "error"
                self.alerts.append(dict(message=error.message, type=level))
            if not doc.errors:
                self.alerts.append(dict(
                    message=f"Successfully updated CDR{self.doc.id}.",
                    type="success",
                ))
            path = f"{self.session.tier.logdir}/CWDReplacements.log"
            try:
                with open(path, "a", encoding="utf-8") as fp:
                    fp.write(f"{self.message}\n")
            except IOError as e:
                self.alerts.append(dict(
                    message=f"Unable to record replacement in {path}: {e}",
                    type="warning",
                ))
        self.show_form()

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

    @cached_property
    def comment(self):
        """Explanation for replacement."""
        return self.fields.getvalue("comment")

    @cached_property
    def create_version(self):
        """True if we should create a new version."""
        return self.pub_version or "create-version" in self.opts

    @cached_property
    def doc(self):
        """Document object for CWD of selected CDR document."""
        return Doc(self.session, id=self.id) if self.id else None

    @cached_property
    def doctype(self):
        """The type of the CDR document."""

        try:
            return self.doc.doctype.name
        except Exception:
            self.logger.exception(f"Failure looking up doctype for {self.id}")
            return None

    @cached_property
    def id(self):
        """The CDR ID of the document to be modified."""
        return self.fields.getvalue("id")

    @cached_property
    def message(self):
        """Log entry to record what was done."""

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
            "Y" if self.pub_version else "N",
            self.comment or "",
        )
        return "\t".join([str(value) for value in values])

    @cached_property
    def opts(self):
        """Versioning options."""
        return self.fields.getlist("opts")

    @cached_property
    def pub_version(self):
        """True if we should make the new version publishable."""
        return "pub-version" in self.opts

    @cached_property
    def ready(self):
        """True if we have all the required field values and they are valid.

        As a side effect,
          * populates the self.alerts array
          * transforms self.version from string to mapped/validated integer
        """

        # Make sure we have a CDR document and a version number.
        if not self.id:
            self.alerts.append(dict(
                message="The Doc ID field is required.",
                type="error",
            ))
        elif not self.doctype:
            self.alerts.append(dict(
                message=f"CDR document {self.id} not found.",
                type="error",
            ))
        elif not self.versions:
            self.alerts.append(dict(
                message=f"CDR{self.doc.id} has no saved versions.",
                type="warning",
            ))
        if not self.version:
            self.alerts.append(dict(
                message="The version field is required.",
                type="error",
            ))
        else:
            try:
                self.version = int(self.version)
            except Exception:
                self.alerts.append(dict(
                    message="Version must be a positive or negative integer.",
                    type="error",
                ))

        # At this point, if there are problems, there's nothing more to check.
        if self.alerts:
            return False

        # Make sure the version exists.
        cdr_id = f"CDR{self.doc.id}"
        if self.version < 0:
            count = len(self.versions)
            if abs(self.version) > count:
                self.alerts.append(dict(
                    message=f"{cdr_id} has only {count} versions.",
                    type="warning",
                ))
            else:
                self.version = self.versions[self.version]
        elif self.version not in self.versions:
            message = f"{cdr_id} has only {len(self.versions)} versions."
            self.alerts.append(dict(message=message, type="warning"))
        return not self.alerts

    @cached_property
    def report(self):
        """Show the user what we're planning to do."""

        if not self.ready:
            self.show_form()
        values = (
            ("Replace CWD for", self.doc.cdr_id),
            ("Document type", self.doctype),
            ("Document title", self.doc.title),
            ("Current total versions", len(self.versions)),
            ("Make this version the CWD", self.version),
            ("Also create a new version", self.create_version),
            ("Make version publishable", self.pub_version),
            ("Reason to be logged", self.comment),
        )
        rows = []
        opts = dict(bold=True, right=True)
        for label, value in values:
            rows.append((self.Reporter.Cell(label, **opts), value))
        table = self.Reporter.Table(rows, caption=self.CAPTION)
        opts = dict(
            banner=self.title,
            subtitle=self.SUBTITLE,
            page_opts=dict(
                session=self.session,
                action=self.script,
            ),
        )
        report = self.Reporter(self.title, [table], **opts)
        page = report.page
        form = page.form
        form.append(page.hidden_field("id", self.doc.id))
        form.append(page.hidden_field("version", self.version))
        if self.create_version:
            form.append(page.hidden_field("opts", "create-version"))
        if self.pub_version:
            form.append(page.hidden_field("opts", "pub-version"))
        if self.comment:
            form.append(page.hidden_field("comment", self.comment))
        page.form.append(page.button(self.CONFIRM))
        page.form.append(page.button(self.CANCEL))
        page.add_css("\n".join(self.CSS))
        return report

    @cached_property
    def same_window(self):
        """Only create a new browser tab once."""

        if self.request:
            return self.SUBMIT, self.CANCEL, self.CONFIRM
        return []

    @cached_property
    def version(self):
        """Integer for the version to promote as the replacement.

        We start out capturing what the user entered. The `ready`
        property will take care of validating it and converting
        it into an integer.
        """

        return self.fields.getvalue("version", "").strip()

    @cached_property
    def versions(self):
        """Sequence of all version IDs for the selected document."""

        versions = [values[0] for values in self.doc.list_versions()]
        return list(reversed(versions))


if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
