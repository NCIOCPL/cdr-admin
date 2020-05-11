#!/usr/bin/env python

"""Show the XML for CDR documents.
"""

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
        (BY_ID, "By document ID", True),
        (BY_TITLE, "By document title", False),
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
            version = self.fields.getvalue("version", "").strip()
            page.form.append(page.hidden_field("selection_method", self.BY_ID))
            page.form.append(page.hidden_field("version", version))
            page.form.append(page.hidden_field("vtype", self.version_type))
            fieldset = page.fieldset("Choose Document")
            for title in self.titles:
                opts = dict(value=title.value, label=title.label)
                if title.tooltip:
                    opts["tooltip"] = title.tooltip
                fieldset.append(page.radio_button("doc-id", **opts))
            page.form.append(fieldset)
            page.add_css("fieldset { width: 1024px; }")
            self.new_tab_on_submit(page)
        else:
            fieldset = page.fieldset("Selection Method")
            for value, label, checked in self.SELECTION_METHODS:
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Document ID", id="by-id-block")
            fieldset.append(page.text_field("doc-id", label="CDR ID"))
            page.form.append(fieldset)
            fieldset = page.fieldset("Title Or Title Pattern")
            fieldset.set("id", "by-title-block")
            fieldset.append(page.B.P(self.TITLE_HELP))
            fieldset.append(page.text_field("title"))
            opts = dict(label="Doc Type", options=self.doctypes, multiple=True)
            fieldset.append(page.select("doctype", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Document Version")
            checked = True
            for value, label in self.VERSION_TYPES.items():
                opts = dict(value=value, label=label, checked=checked)
                #if value == "num":
                #    opts["wrapper_id"] = "num-div"
                fieldset.append(page.radio_button("vtype", **opts))
                checked=False
            page.form.append(fieldset)
            fieldset = page.fieldset("Version Number")
            fieldset.set("id", "version-number-block")
            fieldset.append(page.text_field("version", tooltip=self.VHELP))
            page.form.append(fieldset)
            page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))
            page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def show_report(self):
        """Display the version of the CDR document requested by the user."""

        if not self.xml:
            if self.selection_method == self.BY_TITLE and self.fragment:
                if not self.titles:
                    self.bail("No matching documents found")
            elif self.id:
                if self.version_type == "exported":
                    self.bail(f"CDR{self.id} not published")
                elif self.version == 0:
                    self.bail(f"CDR{self.id} not found")
                elif self.version:
                    self.bail(f"CDR{self.id} version {self.version} not found")
            self.show_form()
        else:
            self.send_page(self.xml, text_type="xml")

    @property
    def doctype(self):
        """Document type string(s) selected by the user to narrow search."""

        if not hasattr(self, "_doctype"):
            self._doctype = self.fields.getlist("doctype")
            if set(self._doctype) - set(self.doctypes):
                self.bail()
        return self._doctype

    @property
    def doctypes(self):
        """Valid value strings for available CDR document types."""

        if not hasattr(self, "_doctypes"):
            self._doctypes = Doctype.list_doc_types(self.session)
        return self._doctypes

    @property
    def fragment(self):
        """String for matching CDR document by title substring."""

        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("title", "").strip()
        return self._fragment

    @property
    def id(self):
        """Integer for the document to be displayed."""

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("doc-id")
            if self._id:
                try:
                    self._id = Doc.extract_id(self._id)
                except Exception:
                    self.bail("invalid document ID format")
            elif len(self.titles) == 1:
                self._id = self.titles[0].value
        return self._id

    @property
    def method(self):
        """Carry the parameters in the URL."""
        return "GET"

    @property
    def selection_method(self):
        """How the user wants to select the document to show."""

        if not hasattr(self, "_selection_method"):
            methods = [method[0] for method in self.SELECTION_METHODS]
            method = self.fields.getvalue("selection_method", "id")
            if method not in methods:
                self.bail()
            else:
                self._selection_method = method
        return self._selection_method

    @property
    def titles(self):
        """Find documents matching the specified title fragment."""

        if not hasattr(self, "_titles"):
            self._titles = []
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
                    self._titles.append(Doc(row))
        return self._titles

    @property
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

        if not hasattr(self, "_version"):
            self._version = None
            if self.id:
                if self.version_type == "cwd":
                    self._version = 0
                else:
                    doc = Doc(self.session, id=self.id)
                if self.version_type == "latest":
                    self._version = doc.last_version
                elif self.version_type == "lastpub":
                    self._version = doc.last_publishable_version
                elif self.version_type == "num":
                    version = self.fields.getvalue("version", "").strip()
                    try:
                        self._version = int(version)
                    except Exception:
                        self.bail("invalid version")
                    if self._version < 0:
                        back = abs(self._version)
                        versions = doc.list_versions(limit=back)
                        if len(versions) == back:
                            self._version = versions[-1][0]
        return self._version

    @property
    def version_type(self):
        """How the user wants to identify the selected version."""

        if not hasattr(self, "_version_type"):
            self._version_type = self.fields.getvalue("vtype", "cwd")
            if self._version_type not in self.VERSION_TYPES:
                self.bail()
        return self._version_type

    @property
    def xml(self):
        """What we came to display."""

        if not hasattr(self, "_xml"):
            self._xml = what = None
            if self.id:
                if self.version_type == "exported":
                    query = self.Query("pub_proc_cg", "xml")
                    query.where(query.Condition("id", self.id))
                    row = query.execute(self.cursor).fetchone()
                    if row:
                        self._xml = row.xml
                        what = "exported XML"
                elif self.version is not None:
                    doc = Doc(self.session, id=self.id, version=self.version)
                    try:
                        self._xml = doc.xml
                        if doc.version:
                            what = f"version {doc.version:d}"
                        else:
                            what = "current working document"
                    except Exception:
                        message = "fetching XML for CDR%dV%d"
                        self.logger.exception(message, self.id, self.version)
                if what:
                    self.logger.info("showing %s for CDR%d", what, self.id)
        return self._xml


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
