#!/usr/bin/env python

"""Show all references cited in a selected cancer information summary.
"""

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
            page.add_css("fieldset { width: 1000px; }")
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

    @property
    def id(self):
        """Integer for the selected summary's CDR ID."""

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("DocId")
            if self._id:
                self._id = Doc.extract_id(self._id)
            elif len(self.titles) == 1:
                self._id = self.titles[0].id
        return self._id

    @property
    def modules(self):
        """True if references from linked modules should be included."""
        return self.fields.getvalue("modules") == "Y"

    @property
    def no_results(self):
        """Suppress message about lack of tables."""
        return None

    @property
    def parsed(self):
        """Remember summaries we've already parsed."""

        if not hasattr(self, "_parsed"):
            self._parsed = set()
        return self._parsed

    @property
    def summary(self):
        """PDQ summary selected for the report."""

        if not hasattr(self, "_summary"):
            self._summary = None
            if self.id and self.version is not None:
                version = self.version if self.version > 0 else None
                self._summary = Summary(self, self.id, version)
        return self._summary

    @property
    def title_fragment(self):
        """String for selecting summary by title fragment."""

        if not hasattr(self, "_title_fragment"):
            self._title_fragment = self.fields.getvalue("DocTitle", "").strip()
        return self._title_fragment

    @property
    def titles(self):
        """Find the summaries matching the user's title fragment."""

        if not hasattr(self, "_titles"):
            self._titles = []
            if self.title_fragment:
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
                self._titles = [Doc(row) for row in rows]
        return self._titles

    @property
    def version(self):
        """Summary document's version selected for the report.

        The value 0 (zero) indicates that the current working
        (unnumbered) version of the document is to be parsed.
        Do not confuse this value with None, which indicates that
        a version is still to be selected.
        """

        if not hasattr(self, "_version"):
            if len(self.versions) == 1:
                self._version = 0
            else:
                self._version = self.fields.getvalue("DocVersion")
                if self._version:
                    try:
                        self._version = int(self._version)
                    except Exception:
                        self.bail()
        return self._version

    @property
    def versions(self):
        """Sequence of versions available for the selected summary."""

        if not hasattr(self, "_versions"):
            self._versions = []
            query = self.Query("doc_version", "num", "dt", "comment")
            query.where(query.Condition("id", self.id))
            query.order("num DESC")
            rows = query.execute(self.cursor).fetchall()
            if rows:
                self._versions = [(0, "Current Working Version")]
                for row in rows:
                    comment = row.comment or "[No comment]"
                    date = str(row.dt)[:10]
                    label = f"[V{row.num:d} {date}] {comment}"
                    self._versions.append((row.num, label))
        return self._versions


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

        self.__control = control
        self.__id = id
        self.__version = version

    @property
    def citations(self):
        """Dictionary of the citations used by the summary document.

        The key is the citation text combined with the Pubmed ID,
        so any variants in the citation text for the same article
        will be reflected in the report.
        """

        if not hasattr(self, "_citations"):
            self._citations = {}
            for node in self.root.iter("ReferenceList"):
                for child in node.findall("Citation"):
                    citation = Citation(self.control, child)
                    if citation.key and citation.key not in self._citations:
                        self._citations[citation.key] = citation

            # Recurse if appropriate, rolling citations from linked modules
            # into this dictionary.
            if self.control.modules:
                for node in self.root.iter("SummaryModuleLink"):
                    cdr_ref = node.get(f"{{{Doc.NS}}}ref")
                    if cdr_ref:
                        try:
                            id = Doc.extract_id(cdr_ref)
                        except Exception:
                            self.control.bail("bad module link %s", cdr_ref)
                        if id not in self.control.parsed:
                            summary = Summary(self.control, id)
                            for key in summary.citations:
                                if key not in self._citations:
                                    citation = summary.citations[key]
                                    self._citations[key] = citation
        return self._citations

    @property
    def control(self):
        """Access to the report's options and report-building tools."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the CDR summary document."""

        if not hasattr(self, "_doc"):
            opts = dict(id=self.__id, version=self.__version)
            self._doc = Doc(self.control.session, **opts)
            self.control.parsed.add(self.__id)
        return self._doc

    @property
    def root(self):
        """Denormalized summary document's DOM root."""

        if not hasattr(self, "_root"):
            self._root = self.doc.filter(*self.FILTERS).result_tree.getroot()
        return self._root

    @property
    def title(self):
        """String for the official title of the summary document."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.root.find("SummaryTitle"))
        return self._title


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

        self.__control = control
        self.__node = node

    def __lt__(self, other):
        """Fold characters with different diacritics together."""
        return strcoll(self.sort_key, other.sort_key) < 0

    @property
    def key(self):
        """Unique tuple distinguishing this reference."""

        if not hasattr(self, "_key"):
            self._key = (self.pmid, self.text) if self.text else None
        return self._key

    @property
    def list_item(self):
        """Return an HTML LI object for this citation.

        If the citation has a Pubmed ID, also include a link to the
        citation on the Pubmed web site.
        """

        B = self.__control.HTMLPage.B
        if self.pmid:
            a = B.A(self.pmid, href=f"{self.URL}/{self.pmid}", target="_blank")
            a.tail = "]"
            return B.LI(f"{self.text} [", a)
        else:
            return B.LI(self.text)

    @property
    def pmid(self):
        """String for NLM's Pubmed ID for this citation."""

        if not hasattr(self, "_pmid"):
            self._pmid = self.__node.get("PMID", "").strip()
        return self._pmid

    @property
    def sort_key(self):
        """Ignore case for sorting."""

        if not hasattr(self, "_sort_key"):
            self._sort_key = self.text.lower()
        return self._sort_key

    @property
    def text(self):
        """String for the citation's reference text."""

        if not hasattr(self, "_text"):
            self._text = Doc.get_text(self.__node, "").strip()
            if self._text and not self._text.endswith("."):
                self._text += "."
        return self._text


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
