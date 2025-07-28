#!/usr/bin/env python

"""Show all references cited in a selected cancer information summary.
"""

from functools import cached_property
from locale import LC_COLLATE, setlocale, strcoll
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "Summary Citations Report"
    INCLUDE_MODULES = "Include citations in linked modules"
    EXCLUDE_MODULES = "Exclude citations in linked modules"

    def populate_form(self, page):
        """Show one of the cascading forms.

        Pass:
            page - HTMLPage object where the form is drawn
        """

        if self.summary:
            self.show_report()
        elif self.id:
            modules = "Y" if self.modules else "N"
            page.form.append(page.hidden_field("modules", modules))
            page.form.append(page.hidden_field("DocId", self.id))
            fieldset = page.fieldset(f"Select version for CDR{self.id:d}")
            opts = dict(label="Version", options=self.versions, default=0)
            fieldset.append(page.select("DocVersion", **opts))
            page.form.append(fieldset)
        elif self.titles:
            modules = "Y" if self.modules else "N"
            page.form.append(page.hidden_field("modules", modules))
            fieldset = page.fieldset("Select Summary")
            for title in self.titles:
                opts = dict(value=title.id, label=title.label)
                fieldset.append(page.radio_button("DocId", **opts))
            page.form.append(fieldset)
        else:
            fieldset = page.fieldset("Select a Document")
            fieldset.append(page.text_field("DocTitle", label="Title"))
            fieldset.append(page.text_field("DocId", label="CDR ID"))
            page.form.append(fieldset)
            fieldset = page.fieldset("Linked Summary Modules")
            opts = dict(label=self.INCLUDE_MODULES, value="Y", checked=True)
            fieldset.append(page.radio_button("modules", **opts))
            opts = dict(label=self.EXCLUDE_MODULES, value="N")
            fieldset.append(page.radio_button("modules", **opts))
            page.form.append(fieldset)

    def show_report(self):
        """Override base class method to show non-tabular report."""

        if not self.summary:
            return self.show_form()
        setlocale(LC_COLLATE, "")
        page = self.report.page
        page.form.append(page.B.H1(self.summary.title))
        page.form.append(page.B.H2("References"))
        if self.summary.citations:
            ordered_list = page.B.OL()
            for citation in sorted(self.summary.citations.values()):
                ordered_list.append(citation.list_item)
            page.form.append(ordered_list)
        else:
            page.form.append(page.B.P("No references found"))
        self.report.send()

    @cached_property
    def id(self):
        """Integer for the selected summary's CDR ID."""

        id = self.fields.getvalue("DocId")
        if id:
            return Doc.extract_id(id)
        elif len(self.titles) == 1:
            return self.titles[0].id
        return None

    @cached_property
    def modules(self):
        """True if references from linked modules should be included."""
        return self.fields.getvalue("modules") == "Y"

    @cached_property
    def no_results(self):
        """Suppress message about lack of tables."""
        return None

    @cached_property
    def parsed(self):
        """Remember summaries we've already parsed."""
        return set()

    @cached_property
    def same_window(self):
        """Go easy on the new browser tab creation."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def summary(self):
        """PDQ summary selected for the report."""

        if self.id:
            doc = Doc(self.session, id=self.id)
            try:
                if doc.doctype.name != "Summary":
                    message = f"CDR{doc.id} is a {doc.doctype} document."
                    self.logger.warning(message)
                    self.alerts.append(dict(message=message, type="warning"))
                    self.id = None
                    return None
            except Exception:
                self.logger.exception("checking doctype")
                message = f"Document {self.id} was not found."
                self.alerts.append(dict(message=message, type="warning"))
                self.id = None
                return None
            if self.version is not None:
                version = self.version if self.version > 0 else None
                return Summary(self, self.id, version)
            return None
        if self.request:
            if not self.title_fragment:
                message = "You must enter an ID or a title fragment."
                self.alerts.append(dict(message=message, type="error"))
            elif not self.titles:
                message = f"No summaries match {self.title_fragment!r}."
                self.alerts.append(dict(message=message, type="warning"))
            else:
                message = f"Multiple summaries match {self.title_fragment!r}."
                self.alerts.append(dict(message=message, type="info"))
        return None

    @cached_property
    def title_fragment(self):
        """String for selecting summary by title fragment."""
        return self.fields.getvalue("DocTitle", "").strip()

    @cached_property
    def titles(self):
        """Find the summaries matching the user's title fragment."""

        if not self.title_fragment:
            return []
        fragment = f"{self.title_fragment}%"
        query = self.Query("document d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Summary'")
        query.where(query.Condition("d.title", fragment, "LIKE"))
        rows = query.order("d.id").execute(self.cursor).fetchall()

        class Doc:
            def __init__(self, row):
                self.id = row.id
                self.label = f"[CDR{row.id:010d}] {row.title}"
        return [Doc(row) for row in rows]

    @cached_property
    def version(self):
        """Summary document's version selected for the report.

        The value 0 (zero) indicates that the current working
        (unnumbered) version of the document is to be parsed.
        Do not confuse this value with None, which indicates that
        a version is still to be selected.
        """

        if len(self.versions) == 1:
            return 0
        version = self.fields.getvalue("DocVersion")
        if not version:
            return None
        try:
            return int(version)
        except Exception:
            self.bail()

    @cached_property
    def versions(self):
        """Sequence of versions available for the selected summary."""

        query = self.Query("doc_version", "num", "dt", "comment")
        query.where(query.Condition("id", self.id))
        query.order("num DESC")
        rows = query.execute(self.cursor).fetchall()
        versions = [(0, "Current Working Version")]
        for row in rows:
            comment = row.comment or "[No comment]"
            date = str(row.dt)[:10]
            label = f"[V{row.num:d} {date}] {comment}"
            versions.append((row.num, label))
        return versions


class Summary:
    """Summary and its citation references."""

    FILTERS = ("set:QC Insertion/Deletion Set",
               "set:Denormalization Summary Set")

    def __init__(self, control, id, version=None):
        """Remember the caller's values.

        Pass:
            control = access to the report's options and report-building tools
            id - integer for the summary's CDR document ID
            version - optional integer for the version of the summary to parse
        """

        self.control = control
        self.id = id
        self.version = version

    @cached_property
    def citations(self):
        """Dictionary of the citations used by the summary document.

        The key is the citation text combined with the Pubmed ID,
        so any variants in the citation text for the same article
        will be reflected in the report.
        """

        citations = {}
        for node in self.root.iter("ReferenceList"):
            for child in node.findall("Citation"):
                citation = Citation(self.control, child)
                if citation.key and citation.key not in citations:
                    citations[citation.key] = citation

        # Recurse if appropriate, rolling citations from linked modules
        # into this dictionary.
        if self.control.modules:
            for node in self.root.iter("SummaryModuleLink"):
                cdr_ref = node.get(f"{{{Doc.NS}}}ref")
                if cdr_ref:
                    try:
                        id = Doc.extract_id(cdr_ref)
                    except Exception:
                        self.control.bail(f"bad module link {cdr_ref}")
                    if id not in self.control.parsed:
                        summary = Summary(self.control, id)
                        for key in summary.citations:
                            if key not in citations:
                                citation = summary.citations[key]
                                citations[key] = citation
        return citations

    @cached_property
    def doc(self):
        """`Doc` object for the CDR summary document."""

        opts = dict(id=self.id, version=self.version)
        self.control.parsed.add(self.id)
        return Doc(self.control.session, **opts)

    @cached_property
    def root(self):
        """Denormalized summary document's DOM root."""
        return self.doc.filter(*self.FILTERS).result_tree.getroot()

    @cached_property
    def title(self):
        """String for the official title of the summary document."""
        return Doc.get_text(self.root.find("SummaryTitle"))


class Citation:
    """A citation reference found in a CDR PDQ summary document."""

    URL = "https://www.ncbi.nlm.nih.gov/pubmed"
    URL = "https://pubmed.ncbi.nlm.nih.gov"

    def __init__(self, control, node):
        """Remember the caller's values.

        Pass:
            control - access to report-building tools
            node - where the citation reference was found
        """

        self.control = control
        self.node = node

    def __lt__(self, other):
        """Fold characters with different diacritics together."""
        return strcoll(self.sort_key, other.sort_key) < 0

    @cached_property
    def key(self):
        """Unique tuple distinguishing this reference."""
        return (self.pmid, self.text) if self.text else None

    @cached_property
    def list_item(self):
        """Return an HTML LI object for this citation.

        If the citation has a Pubmed ID, also include a link to the
        citation on the Pubmed web site.
        """

        B = self.control.HTMLPage.B
        if self.pmid:
            a = B.A(self.pmid, href=f"{self.URL}/{self.pmid}", target="_blank")
            a.tail = "]"
            return B.LI(f"{self.text} [", a)
        else:
            return B.LI(self.text)

    @cached_property
    def pmid(self):
        """String for NLM's Pubmed ID for this citation."""
        return self.node.get("PMID", "").strip()

    @cached_property
    def sort_key(self):
        """Ignore case for sorting."""
        return self.text.lower()

    @cached_property
    def text(self):
        """String for the citation's reference text."""

        text = Doc.get_text(self.node, "").strip()
        if text and not text.endswith("."):
            text += "."
        return text


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
