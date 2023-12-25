#!/usr/bin/env python

"""Replace one CDR document with the content of another one.

Replace an existing version of a document with a completely new
document that was separately created and edited under its own
CDR document ID.

This is primarily intended for use when a new Summary document has
been independently developed over a long period of time to replace
an existing Summary.

Requirements and design are described in Bugzilla issue #3561.
"""

from functools import cached_property
from lxml import etree
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the current CDR login session and form-building tools."""

    SUBTITLE = "Replace Old Document With New One"
    LOGNAME = "ReplaceDocWithNewDoc"
    SUPPORTED_DOCTYPES = {"Summary"}
    CONFIRM = "Confirm Replacement"
    CDR_REF = f"{{{Doc.NS}}}ref"
    PURPOSE = (
        "This program replaces the XML of a CDR document with the XML "
        "copied from another CDR document. This is typically done in "
        "the case of a summary which is undergoing significant "
        "modifications which requires work over a longer period of time. "
        "In order to be able to make minor corrections to the original "
        "documentation during this period, the new version of the "
        "summary is prepared as a separate, temporary document. "
        "When the work on the new version is complete and has been "
        "approved for replacement of the original summary, the XML "
        "from the new temporary document is copied as a new unpublishable "
        "version of the original summary, and the temporary document is "
        "marked as blocked to prevent it from being inadvertently "
        "published. In these instructions, the original document, whose "
        "contents will be updated, is referred to as the 'old' document, "
        "and the temporary document whose XML will be copied into the "
        "permanent ('old') summary, is referred to as the 'new' document.",
    )

    CONDITIONS = (
        "All of the following conditions must be met before replacment "
        "will proceed:",
        (
            "The user must be authorized to perform this operation.",
            "The old and new documents must both be Summaries.",
            "The new replacement document must have a WillReplace "
            "element with a cdr:ref attribute referencing the old document.",
            "After receiving feedback, the user must confirm that the "
            "replacement should proceed.",
        ),
    )

    OPERATION = (
        "A user first enters the CDR document ID for the old (replaced) "
        "and new (replacement) documents in the form below and clicks the "
        "Submit button. The program then checks to see if the first three "
        "conditions above are met. If they are, the program will report "
        "to the user:",
        (
            "The titles of the respective old and new documents.",
            "The validation status of the new document.",
            "A list of any documents that have links to specific "
            "fragments in the old document.",
        ),
        "Any such links will need to be resolved after the new document "
        "replaces the old.",
        "The user must then confirm that this replacement should proceed.",
        "If replacement is confirmed, the program will do the following:",
        (
            "Check out both documents.  If either document is locked by "
            "someone else, the program will stop.",
            "Version the current working document for the old document, "
            "if it is different from the last saved version.",
            "Remove the WillReplace element from the new document.",
            "Save the current working document for the new document as a "
            "non-publishable version under the old ID.",
            "Mark the now unused ID of the new document as blocked. That "
            "ID will no longer be used in the CDR.",
        )
    )
    INSTRUCTIONS = "Purpose", "Conditions", "Operation"
    NO_ERRORS = "There were no validation errors in the new document."
    ERRORS = "These errors occurred when validating the new document:"
    WARNING = (
        "Replacing an existing document with a new one that is invalid is "
        "allowed, but please consider whether you really want to do that. "
        "The new document will be saved as a non-publishable version."
    )
    EXTERNAL_LINKS_FOUND = (
        "There are links from other documents to specific fragments in the "
        "old document.  These are listed below.",
        "Fragment identifiers in the new replacement document are likely not "
        "the same as they are in the old document. Therefore, when a "
        "publishable version of the replaced document is created, a user "
        "must individually fix these links to refer to valid fragment IDs "
        "in the new replacement version, or the user must delete them. "
        "Otherwise misdirected or broken links are likely to occur in the "
        "published documents.",
        "The new document will be saved as a non-publishable version. "
        "Please coordinate the creation of a publishable version with "
        "fixups of fragment links to the document, so that both the new "
        "publishable version of this document and new publishable versions of "
        "any documents that link to it can all be published in the same "
        "publishing job.",
    )
    NO_EXTERNAL_LINKS_FOUND = (
        "There were no external documents with links to specific fragments "
        "that must be resolved. The new document can replace the old one "
        "without breaking any links.",
        "The new document will be saved as a non-publishable version.",
    )
    INTERNAL_LINKS_FOUND = (
        "The new document contains {:d} internal references (e.g., "
        'cdr:href="{}#_123") in which the new CDR ID will be replaced by the '
        "CDR ID of the old document (e.g., {}#_123)."
    )
    NO_INTERNAL_LINKS_FOUND = (
        'There were no internal references (e.g., cdr:href="{}#_123") '
        "in which the new CDR ID would need to be replaced by the old one."
    )

    def populate_form(self, page):
        """Ask the user to identify the two documents and explain what we do.

        Pass:
            page - HTMLPage object where the form is drawn
        """

        for name in self.INSTRUCTIONS:
            fieldset = page.fieldset(name)
            fieldset.set("class", "instructions usa-fieldset")
            for segment in getattr(self, name.upper()):
                if isinstance(segment, str):
                    fieldset.append(page.B.P(segment))
                else:
                    ul = page.B.UL()
                    for item in segment:
                        ul.append(page.B.LI(item))
                    fieldset.append(ul)
            page.form.append(fieldset)
        fieldset = page.fieldset("Enter IDs for Old and New Documents")
        opts = dict(label="Old Document ID")
        if self.old:
            opts["value"] = self.old.id
        fieldset.append(page.text_field("old", **opts))
        opts = dict(label="New Document ID")
        if self.new:
            opts["value"] = self.new.id
        fieldset.append(page.text_field("new", **opts))
        page.form.append(fieldset)

    def clear_locks(self):
        """Make sure we clean up after ourselves."""

        for which_doc in ("old", "new"):
            try:
                doc = getattr(self, which_doc)
                if doc and doc.lock:
                    doc.check_in()
            except Exception as e:
                self.logger.exception(f"Failure unlocking {which_doc} doc")
                self.alerts.append(dict(
                    message=f"Failure unlocking {which_doc} doc: {e}",
                    type="error",
                ))

    def confirm(self):
        """Show the user what will happen and request confirmation."""

        # Create a custom page.
        opts = dict(
            session=self.session,
            action=self.script,
            subtitle="Replacement Confirmation Required"
        )
        page = self.HTMLPage(self.TITLE, **opts)
        page.form.append(page.hidden_field("old", self.old.id))
        page.form.append(page.hidden_field("new", self.new.id))

        # Explain what's about to happen (if the user approves).
        old = f"{self.old.cdr_id} ({self.old.title})"
        new = f"{self.new.cdr_id} ({self.new.title})"
        fieldset = page.fieldset("Proposed Action")
        fieldset.append(page.B.P(f"{old} will be replaced by {new}."))
        page.form.append(fieldset)

        # Show any validation errors found in the replacement document, if any.
        fieldset = page.fieldset("Validation Report")
        if self.validation_errors:
            fieldset.append(page.B.P(self.ERRORS, page.B.CLASS("error")))
            ul = page.B.UL(page.B.CLASS("error"))
            for error in self.validation_errors:
                ul.append(page.B.LI(error))
            fieldset.append(ul)
            fieldset.append(page.B.P(self.WARNING, page.B.CLASS("error")))
        else:
            fieldset.append(page.B.P(self.NO_ERRORS, page.B.CLASS("info")))
        page.form.append(fieldset)

        # Show any fragment links which might need to be taken care of.
        fieldset = page.fieldset("Linked Fragment Report")
        if self.external_links:
            for paragraph in self.EXTERNAL_LINKS_FOUND:
                fieldset.append(page.B.P(paragraph))
            headers = page.B.TR()
            for header in ("Type", "ID", "Title", "Element", "Fragment"):
                headers.append(page.B.TH(header))
            fieldset.append(page.B.TABLE(headers, *self.external_links))
        else:
            for paragraph in self.NO_EXTERNAL_LINKS_FOUND:
                fieldset.append(page.B.P(paragraph))
        if self.internal_links:
            args = len(self.internal_links), self.new.cdr_id, self.old.cdr_id
            fieldset.append(page.B.P(self.INTERNAL_LINKS_FOUND.format(*args)))
        else:
            paragraph = self.NO_INTERNAL_LINKS_FOUND.format(self.new.cdr_id)
            fieldset.append(page.B.P(paragraph))
        page.form.append(fieldset)
        page.form.append(page.button(self.CONFIRM))
        page.form.set("target", "_self")
        page.send()

    def replace(self):
        """Save the old document with the new document's XML."""

        # Check out both documents.
        self.old.check_out()
        self.new.check_out()

        # Version the old document if there are unversioned changes.
        if self.old.has_unversioned_changes:
            comment = "Versioning last CWD of replaced document"
            self.old.save(version=True, comment=comment)

        # Add/adjust DateLastModified and drop WillReplace.
        will_replace = self.new.root.find("WillReplace")
        date_last_modified = self.new.root.find("DateLastModified")
        if date_last_modified is None:
            date_last_modified = etree.Element("DateLastModified")
            will_replace.addnext(date_last_modified)
        date_last_modified.text = self.started.strftime("%Y-%m-%d")
        self.new.root.remove(will_replace)

        # Adjust the internal links to point to the old document.
        target = f"{self.new.cdr_id}#"
        replacement = f"{self.old.cdr_id}#"
        for node, name in self.internal_links:
            value = node.get(name).replace(target, replacement)
            node.set(name, value)

        # Save the old document with XML from the replacement document.
        self.old.xml = etree.tostring(self.new.root, encoding="unicode")
        comment = "Replacing old version with content of replacement doc {}"
        opts = dict(
            version=True,
            val_types=("schema", "links"),
            comment=comment.format(self.new.cdr_id),
            unlock=True
        )
        self.old.save(**opts)
        args = self.old.cdr_id, self.new.cdr_id
        self.logger.info("Saved %s with XML from %s", *args)

        # Block the replacement document.
        comment = "This document's data is now in {}. Use that one, not this."
        comment = comment.format(self.old.cdr_id)
        self.new.set_status(Doc.INACTIVE, comment=comment)
        self.new.check_in(abandon=True)
        self.logger.info("Blocked %s", self.new.cdr_id)

        # Show the outcome.
        opts = dict(
            session=self.session,
            action=self.script,
            subtitle="Replacement Successful"
        )
        page = self.HTMLPage(self.TITLE, **opts)
        fieldset = page.fieldset("Result")
        message = "XML from {} successfully saved as a new version of {}."
        args = self.new.cdr_id, self.old.cdr_id
        fieldset.append(page.B.P(message.format(*args)))
        page.form.append(fieldset)
        if self.old.errors:
            fieldset = page.fieldset("Warnings")
            ul = page.B.UL()
            for error in self.old.errors:
                ul.append(page.B.LI(str(error), page.B.CLASS("error")))
            fieldset.append(ul)
            page.form.append(fieldset)
        page.send()

    def run(self):
        """Override base class version as this is not a standard report."""

        try:
            if not self.ready:
                self.show_form()
            elif self.request == self.SUBMIT:
                self.confirm()
            elif self.request == self.CONFIRM:
                self.replace()
            else:
                Controller.run(self)
        except Exception as e:
            self.logger.exception("failure")
            self.alerts.append(dict(message=f"Failure: {e}", type="error"))
            self.show_form()

    @cached_property
    def external_links(self):
        """Other documents linking to a portion of the old document."""

        fields = (
            "t.name AS doctype",
            "d.id",
            "d.title",
            "n.source_elem",
            "n.target_frag",
        )
        query = self.Query("document d", *fields).unique()
        query.join("doc_type t", "t.id = d.doc_type")
        query.join("link_net n", "n.source_doc = d.id")
        query.where("n.target_frag IS NOT NULL")
        query.where(query.Condition("n.target_doc", self.old.id))
        query.where("n.target_doc <> d.id")
        query.order("t.name", "d.id", "n.source_elem", "n.target_frag")
        links = []
        B = self.HTMLPage.B
        for row in query.execute(self.cursor).fetchall():
            links.append(
                B.TR(
                    B.TD(row.doctype),
                    B.TD(str(row.id), B.CLASS("center")),
                    B.TD(row.title),
                    B.TD(row.source_elem),
                    B.TD(row.target_frag, B.CLASS("center"))
                )
            )
        return links

    @cached_property
    def internal_links(self):
        """Internal links in the replacement document."""

        links = []
        target = f"{self.new.cdr_id}#"
        for local_name in ("ref", "href"):
            name = f"{{{Doc.NS}}}{local_name}"
            xpath = f"//*[starts-with(@cdr:{local_name}, '{target}')]"
            for node in self.new.root.xpath(xpath, namespaces=Doc.NSMAP):
                links.append((node, name))
        for name in ("ReferencedTableNumber", "ReferencedFigureNumber"):
            xpath = f"//{name}[starts-with(@Target, '{target}')]"
            for node in self.new.root.xpath(xpath):
                links.append((node, "Target"))
        return links

    @cached_property
    def new(self):
        """Document whose content will be used to update the old document."""

        id = self.fields.getvalue("new", "").strip()
        return Doc(self.session, id=id) if id else None

    @cached_property
    def old(self):
        """Existing document whose contents will be replaced."""

        id = self.fields.getvalue("old", "").strip()
        return Doc(self.session, id=id) if id else None

    @cached_property
    def ready(self):
        """True if the required information has been provided and is valid."""

        # If we're just starting out, the user won't have provided anything.
        if not self.request:
            return False

        # Make sure we have both documents, of the same supported doctype.
        if not self.old:
            self.alerts.append(dict(
                message="The Old Document ID field is required.",
                type="error",
            ))
        elif self.old.doctype.name not in self.SUPPORTED_DOCTYPES:
            message = (
                f"The old document is a {self.old.doctype} document, "
                "which is not supported."
            )
            self.alerts.append(dict(message=message, type="error"))
        if not self.new:
            self.alerts.append(dict(
                message="The New Document ID field is required.",
                type="error",
            ))
        elif self.new.doctype.name not in self.SUPPORTED_DOCTYPES:
            message = (
                f"The new document is a {self.new.doctype} document, "
                "which is not supported."
            )
            self.alerts.append(dict(message=message, type="error"))
        elif self.old and self.old.doctype.name != self.new.doctype.name:
            if self.old.doctype.name in self.SUPPORTED_DOCTYPES:
                message = (
                    f"The new document is a {self.new.doctype} document, "
                    f"which does not match the old {self.old.doctype} "
                    "document."
                )
                self.alerts.append(dict(message=message, type="error"))

        # Make sure the new document is marked as replacement for the old.
        if self.new:
            node = self.new.root.find("WillReplace")
            if node is None:
                self.alerts.append(dict(
                    message=f"CDR{self.new.id} has no WillReplace element.",
                    type="error",
                ))
            elif self.old:
                cdr_id = node.get(self.CDR_REF)
                if not cdr_id:
                    message = f"WillReplace for CDR{self.new.id} has no ID."
                    self.alerts.append(dict(message=message, type="error"))
                elif cdr_id != self.old.cdr_id:
                    message = f"WillReplace points to {cdr_id}."
                    self.alerts.append(dict(message=message, type="error"))

        # We only proceed if no problems were detected.
        return not self.alerts

    @cached_property
    def same_window(self):
        """Don't open multiple new browser tabs."""
        return [self.SUBMIT, self.CONFIRM] if self.request else []

    @cached_property
    def validation_errors(self):
        """Problems found in the replacement document."""

        self.new.validate(types=("schema", "links"))
        return [str(error) for error in self.new.errors]


if __name__ == "__main__":
    """Don't execute if loaded as a module."""

    Control().run()
