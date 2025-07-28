#!/usr/bin/env python

"""Show the XML for CDR documents.
"""

from functools import cached_property
from collections import OrderedDict
from cdrcgi import Controller
from cdrapi.docs import Doc, Doctype


class Control(Controller):
    """Access to the database and to report-creation tools."""

    SUBTITLE = "CDR Document Viewer"
    LOGNAME = "cdr-document-viewer"
    BY_ID = "id"
    BY_TITLE = "title"
    SELECTION_METHODS = (
        (BY_ID, "By document ID"),
        (BY_TITLE, "By document title"),
    )
    VHELP = (
        "Integer (negative for recent versions: -1 is last version saved; "
        "-2 is next-to-last version, etc.)"
    )
    VERSION_TYPES = OrderedDict([
        ("cwd", "Current working document"),
        ("latest", "Most recently created version"),
        ("lastpub", "Most recently created publishable version"),
        ("exported", "Filtered XML most recently sent to cancer.gov"),
        ("num", "Version by number"),
    ])
    TITLE_HELP = (
        "Use SQL wildcards (e.g., liver cancer%) unless you only want "
        "documents whose document title is an exact match (ignoring case) "
        "with the Title field. "
        "You can also optionally select one or more document "
        "types to narrow the selection."
    )
    CSS = "../../stylesheets/ShowCdrDocument.css"
    SCRIPT = "../../js/ShowCdrDocument.js"

    def populate_form(self, page):
        """Let the user pick a document by ID or by title."""

        if self.xml:
            self.show_report()
        elif self.titles:
            self.logger.info("showing %d titles", len(self.titles))
            page.form.append(page.hidden_field("selection_method", self.BY_ID))
            fieldset = page.fieldset("Choose Document")
            for title in self.titles:
                opts = dict(value=title.value, label=title.label)
                if title.tooltip:
                    opts["tooltip"] = title.tooltip
                fieldset.append(page.radio_button("doc-id", **opts))
            page.form.append(fieldset)
            page.add_css("fieldset { width: 1024px; }")
        else:
            fieldset = page.fieldset("Selection Method")
            for value, label in self.SELECTION_METHODS:
                checked = value == self.selection_method
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Document ID", id="by-id-block")
            opts = dict(label="CDR ID", value=self.id)
            fieldset.append(page.text_field("doc-id", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Title Or Title Pattern")
            fieldset.set("id", "by-title-block")
            fieldset.append(page.B.P(self.TITLE_HELP))
            fieldset.append(page.text_field("title", value=self.fragment))
            opts = dict(label="Doc Type", options=self.doctypes, multiple=True)
            fieldset.append(page.select("doctype", **opts))
            page.form.append(fieldset)
        fieldset = page.fieldset("Document Version")
        for value, label in self.VERSION_TYPES.items():
            checked = value == self.version_type
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("vtype", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Version Number")
        fieldset.set("id", "version-number-block")
        opts = dict(tooltip=self.VHELP, value=self.version)
        fieldset.append(page.text_field("version", **opts))
        page.form.append(fieldset)
        page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def show_report(self):
        """Display the version of the CDR document requested by the user."""

        if not self.xml:
            self.show_form()
        else:
            self.send_page(self.xml, text_type="xml")

    @cached_property
    def doctype(self):
        """Document type string(s) selected by the user to narrow search."""

        doctype = self.fields.getlist("doctype")
        if set(doctype) - set(self.doctypes):
            self.bail()
        return doctype

    @cached_property
    def doctypes(self):
        """Valid value strings for available CDR document types."""
        return Doctype.list_doc_types(self.session)

    @cached_property
    def fragment(self):
        """String for matching CDR document by title substring."""

        if self.selection_method != self.BY_TITLE:
            return ""
        fragment = self.fields.getvalue("title", "").strip()
        if self.request and not fragment:
            message = "Required title fragment not provided."
            self.alerts.append(dict(message=message, type="error"))
        return fragment

    @cached_property
    def id(self):
        """Integer for the document to be displayed."""

        if self.selection_method != self.BY_ID:
            if len(self.titles) == 1:
                return self.titles[0].value
            return None
        id = self.fields.getvalue("doc-id", "").strip()
        if not id:
            if self.request:
                message = "Required ID not provided."
                self.alerts.append(dict(message=message, type="error"))
            return None
        try:
            return Doc.extract_id(id)
        except Exception:
            message = "Invalid document ID format."
            self.alerts.append(dict(message=message, type="error"))
            return None

    @cached_property
    def same_window(self):
        """Should we avoid opening a new browser tab?"""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def selection_method(self):
        """How the user wants to select the document to show."""

        method = self.fields.getvalue("selection_method", self.BY_ID)
        if method not in {values[0] for values in self.SELECTION_METHODS}:
            self.bail()
        return method

    @cached_property
    def suppress_sidenav(self):
        """Once we've moved from the original form, use more space."""
        return True if self.request else False

    @cached_property
    def titles(self):
        """Find documents matching the specified title fragment."""

        titles = []
        if self.fragment and self.selection_method == self.BY_TITLE:
            fragment = self.fragment
            query = self.Query("document d", "d.id", "d.title", "t.name")
            query.join("doc_type t", "t.id = d.doc_type")
            query.where(query.Condition("d.title", fragment, "LIKE"))
            if self.doctype:
                query.where(query.Condition("t.name", self.doctype, "IN"))
                types = ", ".join(sorted(self.doctype))
                self.logger.info("matching %r in %s", fragment, types)
            else:
                self.logger.info("matching title fragment %r", fragment)
            rows = query.order("d.id").execute(self.cursor).fetchall()

            class Doc:
                def __init__(self, row):
                    self.value = row.id
                    self.tooltip = None
                    self.label = f"CDR{row.id:d} [{row.name}] {row.title}"
                    if len(self.label) > 125:
                        self.tooltip = self.label
                        self.label = self.label[:125] + "..."
            for row in rows:
                titles.append(Doc(row))
            if not titles:
                message = "No matching titles found."
                self.alerts.append(dict(message=message, type="warning"))
        return titles

    @cached_property
    def version(self):
        """Integer version number for the user's request.

        Most often the user will request a version generically
        (latest version created, latest publishable version, etc.)
        but it is possible to enter a specific version number
        directly when picking a document by ID (doesn't work as
        well when entering a title fragment to be matched, because
        if the user doesn't already know the document ID, she's
        unlikely to know the numbers of the versions).
        """

        if not self.id:
            return None
        if self.version_type == "cwd":
            return 0
        doc = Doc(self.session, id=self.id)
        if self.version_type == "latest":
            last_version = doc.last_version
            if not last_version:
                self.alerts.append(dict(
                    message=f"CDR{self.id} has no versions.",
                    type="warning",
                ))
            return last_version
        if self.version_type == "lastpub":
            last_publishable_version = doc.last_publishable_version
            if not last_publishable_version:
                self.alerts.append(dict(
                    message=f"CDR{self.id} has no publishable versions.",
                    type="warning",
                ))
            return last_publishable_version
        elif self.version_type == "num":
            version = self.fields.getvalue("version", "").strip()
            try:
                version = int(version)
            except Exception:
                self.alerts.append(dict(
                    message="Version must be a (possibly positive) integer.",
                    type="error",
                ))
                return None
            versions = [values[0] for values in doc.list_versions()]
            versions = list(reversed(versions))
            count = len(versions)
            if version < 0:
                if abs(version) > count:
                    self.alerts.append(dict(
                        message=f"CDR{self.id} has only {count} versions.",
                        type="warning",
                    ))
                    return None
                return versions[version]
            if version not in versions:
                self.alerts.append(dict(
                    message=f"CDR{self.id} has only {count} versions.",
                    type="warning",
                ))
                return None
            return version
        return None

    @cached_property
    def version_type(self):
        """How the user wants to identify the selected version."""

        type = self.fields.getvalue("vtype", "cwd")
        return type if type in self.VERSION_TYPES else self.bail()

    @cached_property
    def xml(self):
        """What we came to display."""

        if not self.id:
            return None
        what = None
        if self.version_type == "exported":
            query = self.Query("pub_proc_cg", "xml")
            query.where(query.Condition("id", self.id))
            row = query.execute(self.cursor).fetchone()
            if row:
                self.logger.info("showing exported XML for CDR%d", self.id)
                return row.xml
            self.alerts.append(dict(
                message=f"CDR{self.id} is not published.",
                type="warning",
            ))
            return None
        if self.version is None:
            return None
        doc = Doc(self.session, id=self.id, version=self.version)
        try:
            if doc.version:
                what = f"version {doc.version:d}"
            else:
                what = "current working document"
            self.logger.info("showing %s for CDR%d", what, self.id)
            return doc.xml
        except Exception as e:
            id_version = f"CDR{self.id}V{self.version}"
            message = f"Failure fetching XML for {id_version}: {e}"
            self.alerts.append(dict(message=message, type="error"))
            self.logger.exception(message)
            return None


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
