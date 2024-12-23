#!/usr/bin/env python

"""Show complete information about a glossary concept and its names.
"""

from copy import deepcopy
from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc
from cdrapi.users import Session
from lxml import html, etree
from lxml.html import builder
import sys


class Control(Controller):
    SUBTITLE = "Glossary QC Report - Full"
    CONCEPT_PATH = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
    NAME_PATH = "/GlossaryTermName/TermName/TermNameString"
    METHOD = "get"
    SIDE_BY_SIDE = "English and Spanish Side-By-Side"
    STACKED = "English and Spanish Stacked"
    LAYOUTS = SIDE_BY_SIDE, STACKED

    def populate_form(self, page):
        """Ask for more information if we don't have everything we need."""

        if self.concept:
            self.show_report()
            sys.exit(0)
        if self.names:
            page.form.append(page.hidden_field("layout", self.layout))
            fieldset = page.fieldset("Select Glossary Concept Document")
            for concept_id, name in self.names:
                opts = dict(label=name, value=concept_id)
                fieldset.append(page.radio_button("id", **opts))
        else:
            fieldset = page.fieldset("Enter Document ID or Term Name")
            opts = dict(
                tooltip="Use wildcards if appropriate",
                label="Term Name",
            )
            fieldset.append(page.text_field("id", label="Concept ID"))
            fieldset.append(page.text_field("name_id", label="Name ID"))
            fieldset.append(page.text_field("name", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Choose Layout")
            for layout in self.LAYOUTS:
                checked = layout == self.layout
                opts = dict(value=layout, label=layout, checked=checked)
                fieldset.append(page.radio_button("layout", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Provide custom routing for the multiple forms."""

        if not self.concept:
            if self.fragment and not self.names:
                warning = f"No documents found matching {self.fragment!r}."
                self.alerts.append(dict(message=warning, type="warning"))
            self.show_form()
        else:
            self.concept.show_report()

    @cached_property
    def concept(self):
        """Subject of the report."""
        return Concept(self) if self.id else None

    @cached_property
    def fragment(self):
        """Term name fragment, possibly with wildcards."""
        return self.fields.getvalue("name")

    @cached_property
    def id(self):
        """CDR GlossaryTermConcept document ID."""

        id = self.fields.getvalue("id")
        if not id:
            id = self.fields.getvalue("DocId")
        if id:
            return Doc.extract_id(id)
        if self.names and len(self.names) == 1:
            return self.names[0][0]
        if self.name_id:
            query = self.Query("query_term", "int_val")
            query.where(query.Condition("path", self.CONCEPT_PATH))
            query.where(query.Condition("doc_id", self.name_id))
            rows = query.execute(self.cursor).fetchall()
            if not rows:
                self.bail("Not a GlossaryTermName document ID")
            return rows[0][0]
        return None

    @cached_property
    def layout(self):
        """Should English and Spanish be stacked or side-by-side?"""

        layout = self.fields.getvalue("layout", self.LAYOUTS[0])
        if layout not in self.LAYOUTS:
            self.bail()
        return layout

    @cached_property
    def name_id(self):
        """CDR ID for a GlossaryTermName document."""

        name_id = self.fields.getvalue("name_id")
        try:
            return Doc.extract_id(name_id) if name_id else None
        except Exception:
            self.bail(f"Invalid Name ID {name_id!r}")

    @cached_property
    def names(self):
        """Concept-id/name-string tuples matching name fragment."""

        if not self.fragment:
            return []
        fields = "c.int_val", "n.value"
        query = self.Query("query_term n", *fields).order("n.value")
        query.join("query_term c", "c.doc_id = n.doc_id")
        query.where(query.Condition("n.path", self.NAME_PATH))
        query.where(query.Condition("c.path", self.CONCEPT_PATH))
        query.where(query.Condition("n.value", self.fragment, "LIKE"))
        rows = query.execute(self.cursor).fetchall()
        return [tuple(row) for row in rows]

    @cached_property
    def same_window(self):
        """Only open a new browser tab from the initial menu page."""

        initial_menu_page = self.fields.getvalue("initial-menu-page")
        return [] if initial_menu_page else [self.SUBMIT]


class Concept:
    """Subject of the report."""

    TITLE = "Glossary Term Concept"
    SUBTITLE = "Glossary Term Concept - Full"
    DEFINITION_ELEMENTS = "TermDefinition", "TranslatedTermDefinition"
    GUEST = Session("guest")
    LANGUAGES = dict(en="English", es="Spanish")
    AUDIENCES = "Patient", "Health professional"
    FILTER = "name:Glossary Term Definition Update"
    EN_INGLES = " (en ingl\xe9s)"
    CSS = "../../stylesheets/GlossaryConceptFull.css"

    def __init__(self, control):
        """Save the control object, which has everything we need.

        Pass:
            control - access to the database and the report parameters
        """

        self.__control = control

    def show_report(self):
        """Send the report back to the browser."""

        opts = dict(
            pretty_print=True,
            doctype="<!DOCTYPE html>",
            encoding="utf-8",
        )
        sys.stdout.buffer.write(b"Content-type: text/html;charset=utf-8\n\n")
        sys.stdout.buffer.write(html.tostring(self.report, **opts))
        sys.exit(0)

    @cached_property
    def control(self):
        """Access to all the information we need for the report."""
        return self.__control

    @cached_property
    def definitions(self):
        """`Definition` objects for the concept, indexed by langcode."""

        definitions = {}
        for langcode in self.LANGUAGES:
            definitions[langcode] = {}
        for name in self.DEFINITION_ELEMENTS:
            for node in self.doc.root.findall(name):
                definition = self.Definition(self, node)
                entry = {definition.audience: definition}
                definitions[definition.langcode].update(entry)
        return definitions

    @cached_property
    def doc(self):
        """CDR `Doc` object for the GlossaryTermConcept document."""

        doc = Doc(self.control.session, id=self.control.id)
        if doc.doctype.name != "GlossaryTermConcept":
            self.control.bail("Not a GlossaryTermConcept document")
        return doc

    @cached_property
    def drug_links(self):
        """Drug summary links for the concept."""
        return self.Link.get_links(self, "drug")

    @cached_property
    def external_refs(self):
        """Links from this concept to pages outside the CDR."""
        return self.Link.get_links(self, "xref")

    @cached_property
    def media_links(self):
        """Links to images not associated with a specific definition."""

        nodes = self.doc.root.findall("MediaLink")
        return [self.MediaLink(node) for node in nodes]

    @cached_property
    def media_table(self):
        """Table showing all the non-definition-specific images."""

        table = builder.TABLE()
        for link in self.media_links:
            table.append(link.row)
        return table

    @cached_property
    def name_links(self):
        """Links to other glossary term names."""
        return self.Link.get_links(self, "term")

    @cached_property
    def names(self):
        """Objects for the concept's GlossaryTermName documents."""

        query = self.control.Query("query_term", "doc_id")
        query.where(query.Condition("path", self.control.CONCEPT_PATH))
        query.where(query.Condition("int_val", self.doc.id))
        rows = query.execute(self.control.cursor).fetchall()
        return [self.Name(self, row.doc_id) for row in rows]

    @cached_property
    def pdq_terms(self):
        """Links to PDQ term documents."""
        return self.Link.get_links(self, "pdqt")

    @cached_property
    def related_info_table(self):
        """Table at the bottom of the report to links to other information."""

        rows = [drug_link.row for drug_link in self.drug_links]
        rows += [summary_ref.row for summary_ref in self.summary_refs]
        rows += [external_ref.row for external_ref in self.external_refs]
        rows += [name_link.row for name_link in self.name_links]
        rows += [pdq_term.row for pdq_term in self.pdq_terms]
        if self.thesaurus_ids:
            label = "NCI Thesaurus ID"
            args = [self.thesaurus_ids[0]]
            for id in self.thesaurus_ids[1:]:
                args += [builder.BR(), id]
            rows.append(builder.TR(builder.TD(label), builder.TD(*args)))
        if not rows:
            return None
        return builder.TABLE(*rows, builder.CLASS("related-info-table"))

    @cached_property
    def report(self):
        """`HTMLPage` object for the report."""

        B = builder
        meta = B.META(charset="utf-8")
        link = B.LINK(href=self.CSS, rel="stylesheet")
        icon = B.LINK(href="/favicon.ico", rel="icon")
        jqry = B.SCRIPT(src=self.control.HTMLPage.JQUERY)
        head = B.HEAD(meta, B.TITLE(self.TITLE), icon, link, jqry)
        time = B.SPAN(self.control.started.ctime())
        args = self.SUBTITLE, B.BR(), "QC Report", B.BR(), time
        concept_id = B.P(f"CDR{self.doc.id}", id="concept-id")
        wrapper = body = B.BODY(B.E("header", B.H1(*args)), concept_id)
        report = B.HTML(head, body)
        sortopts = dict(reverse=True)
        for langcode in sorted(self.definitions):
            language = self.LANGUAGES[langcode]
            if self.parallel:
                wrapper = B.DIV(B.CLASS("lang-wrapper"))
                body.append(wrapper)
            for audience in sorted(self.definitions[langcode], **sortopts):
                definition = self.definitions[langcode][audience]
                section = f"{language} - {definition.audience.title()}"
                wrapper.append(B.H2(section))
                wrapper.append(definition.term_table)
                wrapper.append(definition.info_table)
        if self.media_table is not None:
            body.append(self.media_table)
        body.append(self.term_type_table)
        if self.related_info_table is not None:
            body.append(B.H2("Related Information"))
            body.append(self.related_info_table)
        body.append(B.SCRIPT("""\
jQuery(function() {
    jQuery("a.sound").click(function() {
        var url = jQuery(this).attr("href");
        var audio = document.createElement("audio");
        audio.setAttribute("src", url);
        audio.load();
        audio.addEventListener("canplay", function() {
            audio.play();
        });
        return false;
    });
});"""))
        return report

    @cached_property
    def parallel(self):
        """True if the English and Spanish should be side-by-side."""
        return self.control.layout == Control.SIDE_BY_SIDE

    @cached_property
    def summary_refs(self):
        """Links to Cancer Information Summary documents."""
        return self.Link.get_links(self, "sref")

    @cached_property
    def term_type_table(self):
        """Table showing all of the term type string for the concept."""

        args = [self.term_types[0]]
        for term_type in self.term_types[1:]:
            args += [builder.BR(), term_type]
        term_types = builder.TD(*args)
        table = builder.TABLE(builder.TR(builder.TD("Term Type"), term_types))
        table.set("class", "term-type-table")
        return table

    @cached_property
    def term_types(self):
        """Sequence of term type strings for the concept, in document order."""

        term_types = []
        for node in self.doc.root.findall("TermType"):
            term_types.append(Doc.get_text(node, "").strip())
        return term_types

    @cached_property
    def thesaurus_ids(self):
        """Links to concepts in the NCI thesaurus."""

        thesaurus_ids = []
        for node in self.doc.root.findall("NCIThesaurusID"):
            thesaurus_ids.append(Doc.get_text(node, "").strip())
        return thesaurus_ids

    @cached_property
    def videos(self):
        """Embedded videos not associated with a specific definition.

        Note that we're collecting these, but never displaying them.
        That is surely a mistake.
        """

        nodes = self.doc.root.findall("EmbeddedVideo")
        return [Concept.Video(node) for node in nodes]

    class Definition:
        """One concept definition for a specifc language/audience combo."""

        ROWS = (
            ("definitions", "Definition Resource"),
            ("media_links", "Media Link"),
        )
        RESOURCES = dict(en="Definition Resource", es="Translation Resource")
        STATUSES = dict(en="Definition Status", es="Translation Status")

        def __init__(self, concept, node):
            """Capture the caller's information.

            Pass:
                concept - `Concept` to which this definition belongs
                node - wrapper element for this definition
            """

            self.__concept = concept
            self.__node = node

        @cached_property
        def audience(self):
            """Audience for this definition."""
            return Doc.get_text(self.node.find("Audience"))

        @cached_property
        def comments(self):
            """`Comment` objects belonging to the definition."""

            comments = []
            for node in self.node.findall("Comment"):
                comments.append(self.Comment(node))
            return comments

        @cached_property
        def concept(self):
            """Access to the terms connected with the concept."""
            return self.__concept

        @cached_property
        def dictionaries(self):
            """Dictionaries in which this definition should appear."""

            dictionaries = []
            for node in self.node.findall("Dictionary"):
                dictionaries.append(Doc.get_text(node, "").strip())
            return dictionaries

        @cached_property
        def info_table(self):
            """Table with meta information about this definition."""

            table = builder.TABLE(builder.CLASS("definition-info"))
            for row in self.rows:
                table.append(row)
            return table

        @cached_property
        def langcode(self):
            """Language code for this definition ("en" or "es")."""
            return "en" if self.node.tag == "TermDefinition" else "es"

        @cached_property
        def last_modified(self):
            """Date the definition was last modified."""

            child = self.node.find("DateLastModified")
            return Doc.get_text(child, "").strip() or None

        @cached_property
        def last_reviewed(self):
            """Date the definition was last reviewed."""

            child = self.node.find("DateLastReviewed")
            return Doc.get_text(child, "").strip() or None

        @cached_property
        def media_links(self):
            """Links to images for the definition."""

            children = self.node.findall("MediaLink")
            return [Concept.MediaLink(child) for child in children]

        @cached_property
        def node(self):
            """Parsed XML node for the definition."""
            return self.__node

        @cached_property
        def replacements(self):
            """Replacement strings not specific to any term name."""

            replacements = {}
            for node in self.node.findall("ReplacementText"):
                replacements[node.get("name")] = node
            return replacements

        @cached_property
        def resources(self):
            """Resources used for this definition."""

            resources = []
            for tag in ("DefinitionResource", "TranslationResource"):
                for node in self.node.findall(tag):
                    resources.append(Doc.get_text(node, "").strip())
            return resources

        @cached_property
        def rows(self):
            """Table rows for this definition's meta data."""

            rows = []
            resources = self.RESOURCES[self.langcode]
            self.__add_row(rows, "resources", resources)
            for media_link in self.media_links:
                rows.append(media_link.row)
            for video in self.videos:
                rows.append(video.row)
            self.__add_row(rows, "dictionaries", "Dictionary")
            self.__add_row(rows, "status", self.STATUSES[self.langcode])
            self.__add_row(rows, "status_date", "Status Date")
            # Only include the topmost comment
            for comment in self.comments[:1]:
                rows.append(comment.row)
            self.__add_row(rows, "last_modified", "Date Last Modified")
            self.__add_row(rows, "last_reviewed", "Date Last Reviewed")
            return rows

        @cached_property
        def status(self):
            """String for the definition's status."""

            for tag in ("DefinitionStatus", "TranslatedStatus"):
                status = self.node.find(tag)
                if status is not None:
                    return Doc.get_text(status, "").strip()
            return None

        @cached_property
        def status_date(self):
            """Date of the definition's current status."""

            for tag in ("StatusDate", "TranslatedStatusDate"):
                node = self.node.find(tag)
                if node is not None:
                    return Doc.get_text(node, "").strip()
            return None

        @cached_property
        def term_table(self):
            """Table showing term names and customized definitions.

               The definition is included via the resolve_placeholders() method
               and by transforming the text via a XSLT filter
            """

            B = builder
            table = B.TABLE(B.CLASS("name-and-def"))
            for name in self.concept.names:
                if self.langcode == "en":
                    langname = name.english_name
                elif name.spanish_name is not None:
                    langname = name.spanish_name
                else:
                    langname = name.english_name
                markup = name.markup_for_name(langname)
                if markup.tag == "p":
                    markup.tag = "span"
                args = [markup, f" (CDR{name.id})"]
                if self.langcode == "es":
                    if name.spanish_pronunciation is not None:
                        args.append(" ")
                        args.append(name.spanish_pronunciation)
                    if name.spanish_name is None:
                        markup = B.SPAN(" (en ingl\xe9s)", B.CLASS("special"))
                        args.append(markup)
                    elif name.alternate_spanish_names:
                        separator = None
                        args.append(" \xa0[alternate: ")
                        for alt_name in name.alternate_spanish_names:
                            if separator:
                                args.append(separator)
                            separator = ", "
                            markup = name.markup_for_name(alt_name)
                            if markup.tag == "p":
                                markup.tag = "span"
                            args.append(markup)
                        args.append("]")
                elif name.english_pronunciation is not None:
                    args.append(" ")
                    args.append(name.english_pronunciation)
                if name.blocked:
                    args = ["BLOCKED - "] + args + [B.CLASS("blocked")]
                table.append(B.TR(B.TD("Name"), B.TD(*args), B.CLASS("name")))
                if not name.blocked:
                    table.append(name.resolve_placeholders(self))
            return table

        @cached_property
        def text(self):
            """Definition text with placeholders to be resolved."""
            return self.node.find("DefinitionText")

        @cached_property
        def videos(self):
            """Sequence of embedded videos for this definition."""

            nodes = self.node.findall("EmbeddedVideo")
            return [Concept.Video(node) for node in nodes]

        def __add_row(self, rows, name, label):
            """Helper method to create a row for the definition meta table."""

            values = getattr(self, name)
            if values:
                label = builder.TD(label)
                if not isinstance(values, list):
                    values = [values]
                args = [values[0]]
                for value in values[1:]:
                    args.append(builder.BR())
                    args.append(value)
                values = builder.TD(*args)
                rows.append(builder.TR(label, values))

        class Comment:
            """Comment associated with the definition."""

            def __init__(self, node):
                """Remember the node for this comment.

                Pass:
                    node - parsed XML for the comment's element
                """

                self.__node = node

            @cached_property
            def row(self):
                """HTML markup for this comment."""

                wrapper = etree.Element("GlossaryTermDef")
                wrapper.append(self.__node)
                doc = Doc(Concept.GUEST, xml=etree.tostring(wrapper))
                result = doc.filter(Concept.FILTER)
                return html.fromstring(str(result.result_tree))

    class Link:
        """Link to be displayed in the concept's table for related info."""

        RELINFO = "RelatedInformation"
        DRUG_SUMMARY_LINK = "RelatedInformation/RelatedDrugSummaryLink"
        EXTERNAL_REF = "RelatedInformation/RelatedExternalRef"
        SUMMARY_REF = "RelatedInformation/RelatedSummaryRef"
        TERM_NAME_LINK = "RelatedInformation/RelatedGlossaryTermNameLink"
        PDQ_TERM = "PDQTerm"
        TYPES = dict(
            drug=(DRUG_SUMMARY_LINK, "Rel Drug Summary Link", "ref", True),
            xref=(EXTERNAL_REF, "Rel External Ref", "xref", True),
            sref=(SUMMARY_REF, "Rel Summary Ref", "ref", True),
            term=(TERM_NAME_LINK, "Rel Glossary Term", "ref", True),
            pdqt=(PDQ_TERM, "PDQ Term", "ref", False),
        )

        def __init__(self, label, value, text, external, indent):
            """Capture the caller's values.

            Pass:
                label - string for the left-side column
                value - string extracted from the linking attribute
                text - text displayed in the right-side column
                external - True if this is a link outside the CDR
                indent - whether the label should be offset from the left
            """

            self.__label = label
            self.__value = value
            self.__text = text
            self.__external = external
            self.__indent = indent

        @cached_property
        def row(self):
            """HTML markup for the link."""

            label = builder.TD(self.__label)
            if self.__indent:
                label.set("class", "indent")
            if self.__external:
                display = url = self.__value
            else:
                doc_id = Doc.extract_id(self.__value)
                display = f"CDR{doc_id:d}"
                url = f"QcReport.py?Session=guest&DocId={doc_id:d}"
            link = builder.A(display, href=url)
            args = f"{self.__text} (", link, ")"
            return builder.TR(label, builder.TD(*args))

        @classmethod
        def get_links(cls, concept, key):
            """Find all the links of a given type for the concept.

            Pass:
                concept - subject of the report
                key - index into the values for this type of link
            """

            path, label, name, indent = cls.TYPES[key]
            external = name == "xref"
            name = f"{{{Doc.NS}}}{name}"
            links = []
            for node in concept.doc.root.findall(path):
                text = Doc.get_text(node, "").strip()
                value = node.get(name)
                links.append(cls(label, value, text, external, indent))
                label = ""
            return links

    class MediaLink:
        """Link to an image used by the glossary term."""

        CDR_REF = f"{{{Doc.NS}}}ref"
        CGI = "https://cdr.cancer.gov/cgi-bin/cdr"
        URL = f"{CGI}/GetCdrImage.py?id={{}}-300.jpg"

        def __init__(self, node):
            """Remember the XML node for this link.

            Pass:
                node - wrapper element for the image information
            """

            self.__node = node

        @property
        def id(self):
            """CDR ID for the image document (cached by hand)."""

            if not hasattr(self, "_id"):
                node = self.node.find("MediaID")
                try:
                    self._id = Doc.extract_id(node.get(f"{{{Doc.NS}}}ref"))
                except Exception:
                    self._id = None
                if not hasattr(self, "_text"):
                    self._text = Doc.get_text(node, "").strip()
            return self._id

        @cached_property
        def node(self):
            """Wrapper node for the media link."""
            return self.__node

        @cached_property
        def row(self):
            """HTML markup for the the image's table row."""

            B = builder
            img = B.IMG(src=self.URL.format(self.id))
            args = f"{self.text} (CDR{self.id})", B.BR(), img
            return B.TR(B.TD("Media Link"), B.TD(*args))

        @property
        def text(self):
            """Text to be displayed above the image (manually cached)."""

            if not hasattr(self, "_text"):
                node = self.node.find("MediaID")
                self._text = Doc.get_text(node, "").strip()
                if not hasattr(self, "_id"):
                    try:
                        self._id = Doc.extract_id(node.get(self.CDR_REF))
                    except Exception:
                        self._id = None
            return self._text

    class Name:
        """Information needed from a GlossaryTermName document."""

        NAME_TAGS = "TermName", "TranslatedName"

        def __init__(self, concept, id):
            """Remember the caller's information.

            Pass:
                concept - `Concept` to which this name belongs
                id - CDR ID for the GlossaryTermName document
            """

            self.__concept = concept
            self.__id = id

        def resolve_placeholders(self, definition):
            """Assemble the definition using our name and replacements.

            Pass:
                definition - definition with placeholders to be resolved

            Return:
                marked-up definition row
            """

            if definition.langcode == "en":
                name = deepcopy(self.english_name)
            elif self.spanish_name is None:
                name = deepcopy(self.english_name)
                self.__append_en_ingles(name)
            else:
                name = deepcopy(self.spanish_name)
            root = etree.Element("GlossaryTermDef")
            root.append(name)
            root.append(self.__make_capped_name(name))
            root.append(deepcopy(definition.node.find("DefinitionText")))
            if self.replacements:
                node = etree.Element("GlossaryTermPlaceHolder")
                for replacement in self.replacements.values():
                    node.append(deepcopy(replacement))
                root.append(node)
            if definition.replacements:
                node = etree.Element("GlossaryConceptPlaceHolder")
                for replacement in definition.replacements.values():
                    node.append(deepcopy(replacement))
                root.append(node)
            doc = Doc(Concept.GUEST, xml=etree.tostring(root))
            result = doc.filter(Concept.FILTER)
            return html.fromstring(str(result.result_tree))

        @property
        def alternate_spanish_names(self):
            """Extra spanish names (manually cached)."""

            if not hasattr(self, "_alternate_spanish_names"):
                self._alternate_spanish_names = []
                path = "TranslatedName/TermNameString"
                for node in self.doc.root.findall(path):
                    if node.get("NameType") == "alternate":
                        self._alternate_spanish_names.append(node)
                    elif not hasattr(self, "_spanish_name"):
                        self._spanish_name = node
            return self._alternate_spanish_names

        @cached_property
        def blocked(self):
            """True if the name document can't be published."""
            return self.doc.active_status != Doc.ACTIVE

        @cached_property
        def doc(self):
            """CDR `Doc` object for the GlossaryTermName document."""
            return Doc(Concept.GUEST, id=self.id)

        @cached_property
        def id(self):
            """CDR ID for the GlossaryTermName document."""
            return self.__id

        @cached_property
        def english_name(self):
            """English name for the glossary term."""
            return self.doc.root.find("TermName/TermNameString")

        @cached_property
        def english_pronunciation(self):
            """Link to the audio file for pronunciation of the English name."""

            if not self.english_pronunciation_url:
                return None
            B = builder
            url = self.english_pronunciation_url
            img = B.IMG(B.CLASS("sound"), src="/images/audio.png")
            return B.A(img, B.CLASS("sound"), href=url)

        @cached_property
        def english_pronunciation_url(self):
            """URL for the audio file for pronunciation of the English name."""

            node = self.doc.root.find("TermName/MediaLink/MediaID")
            if node is not None:
                id = node.get(f"{{{Doc.NS}}}ref")
                if id:
                    return f"GetCdrBlob.py?disp=inline&id={id}"
            return None

        @cached_property
        def replacements(self):
            """The name's replacement strings for definition placeholders."""

            replacements = {}
            for node in self.doc.root.findall("ReplacementText"):
                replacements[node.get("name")] = node
            return replacements

        @property
        def spanish_name(self):
            """Primary (non-"alternate") Spanish name for the term.

            Manual caching is intentional.
            """

            if not hasattr(self, "_spanish_name"):
                self._spanish_name = None
                alternates = []
                for node in self.doc.root.findall("TranslatedName"):
                    child = node.find("TermNameString")
                    if child is not None:
                        if node.get("NameType") != "alternate":
                            self._spanish_name = child
                        else:
                            alternates.append(child)
                if not hasattr(self, "_alternate_spanish_names"):
                    self._alternate_spanish_names = alternates
            return self._spanish_name

        @cached_property
        def spanish_pronunciation(self):
            """Link to the audio file for pronunciation of the Spanish name."""

            if self.spanish_pronunciation_url:
                B = builder
                url = self.spanish_pronunciation_url
                img = B.IMG(B.CLASS("sound"), src="/images/audio.png")
                return B.A(img, B.CLASS("sound"), href=url)
            return None

        @cached_property
        def spanish_pronunciation_url(self):
            """URL for the audio file for pronunciation of the Spanish name."""

            node = self.doc.root.find("TranslatedName/MediaLink/MediaID")
            if node is not None:
                id = node.get(f"{{{Doc.NS}}}ref")
                if id:
                    return f"GetCdrBlob.py?disp=inline&id={id}"
            return None

        @staticmethod
        def markup_for_name(name):
            """Highlight insertion/deletion markup for the term name.

            Pass:
                name - parsed XML node for the term name string
            """

            doc = Doc(Concept.GUEST, xml=etree.tostring(name))
            result = doc.filter(Concept.FILTER)
            return html.fromstring(str(result.result_tree).strip())

        @staticmethod
        def __make_capped_name(node):
            """Helper method for uppercasing the first character of a name.

            Pass:
                node - parsed XML node containing the term name
            """

            node = deepcopy(node)
            node.tag = "CappedNameString"
            for n in node.iter("*"):
                if n.text is not None and n.text.strip():
                    n.text = n.text[0].upper() + n.text[1:]
                    break
                elif n is not node and n.tail is not None and n.tail.strip():
                    n.tail = n.tail[0].upper() + n.tail[1:]
                    break
            return node

        @staticmethod
        def __append_en_ingles(node):
            """Helper method for marking this name as an English substitute.

            Pass:
                node - XML node to which the suffix is added
            """

            last_child = None
            for child in node.findall("*"):
                last_child = child
            if last_child is not None:
                if last_child.tail is not None:
                    last_child.tail += Concept.EN_INGLES
                else:
                    last_child.tail = Concept.EN_INGLES
            else:
                node.text += Concept.EN_INGLES

    class Video:
        """Information about a YouTube video."""

        IMAGE_URL = "https://img.youtube.com/vi/{}/hqdefault.jpg"
        VIDEO_URL = "https://www.youtube.com/watch?v={}"
        SESSION = Session("guest")

        def __init__(self, node):
            """Capture the caller's information.

            Pass:
                node - wrapper node for the video information
            """

            self.__node = node

        @cached_property
        def id(self):
            """CDR ID for the video's Media document."""

            node = self.node.find("VideoID")
            if node is not None:
                try:
                    return Doc.extract_id(node.get(f"{{{Doc.NS}}}ref"))
                except Exception:
                    return None
            return None

        @cached_property
        def img(self):
            """Still image displayed for the video."""
            return builder.IMG(src=self.IMAGE_URL.format(self.youtube_id))

        @cached_property
        def link(self):
            """Link for playing the YouTube video."""

            url = self.VIDEO_URL.format(self.youtube_id)
            return builder.A("Watch video on YouTube", href=url)

        @cached_property
        def node(self):
            """Wrapper element for the video information."""
            return self.__node

        @cached_property
        def row(self):
            """HTML markup for displaying the video info and link."""

            B = builder
            args = self.text, B.BR(), self.img, B.BR(), self.link
            return B.TR(B.TD("Video Link"), B.TD(*args))

        @cached_property
        def text(self):
            """String describing the video, displayed at the top."""

            for name in ("SpecificMediaTitle", "VideoID"):
                text = Doc.get_text(self.node.find(name), "").strip()
                if text:
                    return text
            return ""

        @cached_property
        def youtube_id(self):
            """Token for the URL to play the video."""

            doc = Doc(self.SESSION, id=self.id)
            node = doc.root.find("PhysicalMedia/VideoData/HostingID")
            return Doc.get_text(node, "").strip() or None


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
