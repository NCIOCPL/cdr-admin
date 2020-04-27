#!/usr/bin/env python

"""Show complete information about a glossary concept and its names.
"""

from copy import deepcopy
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

    def populate_form(self, page):
        """Ask for more information if we don't have everything we need."""

        if self.concept:
            self.show_report()
            sys.exit(0)
        if self.names:
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

    def show_report(self):
        """Provide custom routing for the multiple forms."""

        if not self.concept:
            self.show_form()
        else:
            self.concept.show_report()

    @property
    def concept(self):
        """Subject of the report."""

        if not hasattr(self, "_concept"):
            self._concept = Concept(self) if self.id else None
        return self._concept

    @property
    def id(self):
        """CDR GlossaryTermConcept document ID."""

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("id")
            if self._id is None:
                self._id = self.fields.getvalue("DocId")
            if self._id is None:
                if self.names and len(self.names) == 1:
                    self._id = self.names[0][0]
                elif self.name_id:
                    query = self.Query("query_term", "int_val")
                    query.where(query.Condition("path", self.CONCEPT_PATH))
                    query.where(query.Condition("doc_id", self.name_id))
                    rows = query.execute(self.cursor).fetchall()
                    if not rows:
                        self.bail("Not a GlossaryTermName document ID")
                    self._id = rows[0][0]
            else:
                self._id = Doc.extract_id(self._id)
        return self._id

    @property
    def name_id(self):
        """CDR ID for a GlossaryTermName document."""

        if not hasattr(self, "_name_id"):
            self._name_id = self.fields.getvalue("name_id")
            if self._name_id:
                self._name_id = Doc.extract_id(self._name_id)
        return self._name_id

    @property
    def names(self):
        """Concept-id/name-string tuples matching name fragment."""

        if not hasattr(self, "_names"):
            fragment = self.fields.getvalue("name")
            if fragment:
                fields = "c.int_val", "n.value"
                query = self.Query("query_term n", *fields).order("n.value")
                query.join("query_term c", "c.doc_id = n.doc_id")
                query.where(query.Condition("n.path", self.NAME_PATH))
                query.where(query.Condition("c.path", self.CONCEPT_PATH))
                query.where(query.Condition("n.value", fragment, "LIKE"))
                rows = query.execute(self.cursor).fetchall()
                self._names = [tuple(row) for row in rows]
            else:
                self._names = []
        return self._names


class Concept:
    """Subject of the report."""

    TITLE = "Glossary Term Concept"
    SUBTITLE  = "Glossary Term Concept - Full"
    DEFINITION_ELEMENTS = "TermDefinition", "TranslatedTermDefinition"
    GUEST = Session("guest")
    LANGUAGES = dict(en="English", es="Spanish")
    AUDIENCES = "Patient", "Health professional"
    FILTER = "name:Glossary Term Definition Update"
    EN_INGLES = " (en ingl\xe9s)"
    CSS = "/stylesheets/GlossaryConceptFull.css"

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

    @property
    def control(self):
        """Access to all the information we need for the report."""
        return self.__control

    @property
    def definitions(self):
        """`Definition` objects for the concept, indexed by langcode."""

        if not hasattr(self, "_definitions"):
            self._definitions = {}
            for langcode in self.LANGUAGES:
                self._definitions[langcode] = []
            for name in self.DEFINITION_ELEMENTS:
                for node in self.doc.root.findall(name):
                    definition = self.Definition(self, node)
                    self._definitions[definition.langcode].append(definition)
        return self._definitions

    @property
    def doc(self):
        """CDR `Doc` object for the GlossaryTermConcept document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.control.id)
            if self._doc.doctype.name != "GlossaryTermConcept":
                self.control.bail("Not a GlossaryTermConcept document")
        return self._doc

    @property
    def names(self):
        """Objects for the concept's GlossaryTermName documents."""

        if not hasattr(self, "_names"):
            query = self.control.Query("query_term", "doc_id")
            query.where(query.Condition("path", self.control.CONCEPT_PATH))
            query.where(query.Condition("int_val", self.doc.id))
            rows = query.execute(self.control.cursor).fetchall()
            self._names = [self.Name(self, row.doc_id) for row in rows]
        return self._names

    @property
    def report(self):
        """`HTMLPage` object for the report."""

        if not hasattr(self, "_report"):
            B = builder
            meta = B.META(charset="utf-8")
            link = B.LINK(href=self.CSS, rel="stylesheet")
            icon = B.LINK(href="/favicon.ico", rel="icon")
            head = B.HEAD(meta, B.TITLE(self.TITLE), icon, link)
            time = B.SPAN(self.control.started.ctime())
            args = self.SUBTITLE, B.BR(), "QC Report", B.BR(), time
            concept_id = B.P(f"CDR{self.doc.id}", id="concept-id")
            body = B.BODY(B.E("header", B.H1(*args)), concept_id)
            self._report = B.HTML(head, body)
            for langcode in sorted(self.definitions):
                language = self.LANGUAGES[langcode]
                for definition in self.definitions[langcode]:
                    section = f"{language} - {definition.audience}"
                    body.append(B.H2(section))
                    body.append(definition.term_table)
                    body.append(definition.info_table)
                if langcode == "en" and self.media_table is not None:
                    body.append(self.media_table)
            body.append(self.term_type_table)
            if self.related_info_table is not None:
                body.append(B.H2("Related Information"))
                body.append(self.related_info_table)
        return self._report

    @property
    def drug_links(self):
        """Drug summary links for the concept."""

        if not hasattr(self, "_drug_links"):
            self._drug_links = self.Link.get_links(self, "drug")
        return self._drug_links

    @property
    def external_refs(self):
        """Links from this concept to pages outside the CDR."""

        if not hasattr(self, "_external_refs"):
            self._external_refs = self.Link.get_links(self, "xref")
        return self._external_refs

    @property
    def summary_refs(self):
        """Links to Cancer Information Summary documents."""

        if not hasattr(self, "_summary_refs"):
            self._summary_refs = self.Link.get_links(self, "sref")
        return self._summary_refs

    @property
    def name_links(self):
        """Links to other glossary term names."""

        if not hasattr(self, "_name_links"):
            self._name_links = self.Link.get_links(self, "term")
        return self._name_links

    @property
    def pdq_terms(self):
        """Links to PDQ term documents."""

        if not hasattr(self, "_pdq_terms"):
            self._pdq_terms = self.Link.get_links(self, "pdqt")
        return self._pdq_terms

    @property
    def related_info_table(self):
        """Table at the bottom of the report to links to other information."""

        if not hasattr(self, "_related_info_table"):
            self._related_info_table = None
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
            if rows:
                self._related_info_table = builder.TABLE(*rows)
                self._related_info_table.set("class", "related-info-table")
        return self._related_info_table

    @property
    def thesaurus_ids(self):
        """Links to concepts in the NCI thesaurus."""

        if not hasattr(self, "_thesaurus_ids"):
            self._thesaurus_ids = []
            for node in self.doc.root.findall("NCIThesaurusID"):
                self._thesaurus_ids.append(Doc.get_text(node, "").strip())
        return self._thesaurus_ids

    @property
    def media_links(self):
        """Links to images not associated with a specific definition."""

        if not hasattr(self, "_media_links"):
            nodes = self.doc.root.findall("MediaLink")
            self._media_links = [self.MediaLink(node) for node in nodes]
        return self._media_links

    @property
    def media_table(self):
        """Table showing all the non-definition-specific images."""

        if not hasattr(self, "_media_table"):
            self._media_table = builder.TABLE()
            for link in self.media_links:
                self._media_table.append(link.row)
        return self._media_table

    @property
    def term_type_table(self):
        """Table showing all of the term type string for the concept."""

        args = [self.term_types[0]]
        for term_type in self.term_types[1:]:
            args += [builder.BR(), term_type]
        term_types = builder.TD(*args)
        table = builder.TABLE(builder.TR(builder.TD("Term Type"), term_types))
        table.set("class", "term-type-table")
        return table

    @property
    def term_types(self):
        """Sequence of term type strings for the concept, in document order."""

        if not hasattr(self, "_term_types"):
            self._term_types = []
            for node in self.doc.root.findall("TermType"):
                self._term_types.append(Doc.get_text(node, "").strip())
        return self._term_types

    @property
    def videos(self):
        """Embedded videos not associated with a specific definition.

        Note that we're collecting these, but never displaying them.
        That is surely a mistake.
        """

        if not hasattr(self, "_videos"):
            nodes = self.doc.root.findall("EmbeddedVideo")
            self._videos = [Concept.Video(node) for node in nodes]
        return self._videos


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

        @property
        def audience(self):
            """Audience for this definition."""

            if not hasattr(self, "_audience"):
                self._audience = Doc.get_text(self.node.find("Audience"))
            return self._audience

        @property
        def comments(self):
            """`Comment` objects belonging to the definition."""

            if not hasattr(self, "_comments"):
                self._comments = []
                for node in self.node.findall("Comment"):
                    self._comments.append(self.Comment(node))
            return self._comments

        @property
        def concept(self):
            """Access to the terms connected with the concept."""
            return self.__concept

        @property
        def dictionaries(self):
            """Dictionaries in which this definition should appear."""

            if not hasattr(self, "_dictionaries"):
                self._dictionaries = []
                for node in self.node.findall("Dictionary"):
                    self._dictionaries.append(Doc.get_text(node, "").strip())
            return self._dictionaries

        @property
        def info_table(self):
            """Table with meta information about this definition."""

            table = builder.TABLE(builder.CLASS("definition-info"))
            for row in self.rows:
                table.append(row)
            return table

        @property
        def langcode(self):
            """Language code for this definition ("en" or "es")."""
            return "en" if self.node.tag == "TermDefinition" else "es"

        @property
        def last_modified(self):
            """Date the definition was last modified."""

            if not hasattr(self, "_last_modified"):
                self._last_modified = None
                node = self.node.find("DateLastModified")
                if node is not None:
                    self._last_modified = Doc.get_text(node, "").strip()
            return self._last_modified

        @property
        def last_reviewed(self):
            """Date the definition was last reviewed."""

            if not hasattr(self, "_last_reviewed"):
                self._last_reviewed = None
                node = self.node.find("DateLastReviewed")
                if node is not None:
                    self._last_reviewed = Doc.get_text(node, "").strip()
            return self._last_reviewed

        @property
        def media_links(self):
            """Links to images for the definition."""

            if not hasattr(self, "_media_links"):
                nodes = self.node.findall("MediaLink")
                self._media_links = [Concept.MediaLink(node) for node in nodes]
            return self._media_links

        @property
        def node(self):
            """Parsed XML node for the definition."""
            return self.__node

        @property
        def replacements(self):
            """Replacement strings not specific to any term name."""

            if not hasattr(self, "_replacements"):
                self._replacements = {}
                for node in self.node.findall("ReplacementText"):
                    self._replacements[node.get("name")] = node
            return self._replacements

        @property
        def resources(self):
            """Resources used for this definition."""

            if not hasattr(self, "_resources"):
                self._resources = []
                for tag in ("DefinitionResource", "TranslationResource"):
                    for node in self.node.findall(tag):
                        self._resources.append(Doc.get_text(node, "").strip())
            return self._resources

        @property
        def rows(self):
            """Table rows for this definition's meta data."""

            if not hasattr(self, "_rows"):
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
                for comment in self.comments:
                    rows.append(comment.row)
                self.__add_row(rows, "last_modified", "Date Last Modified")
                self.__add_row(rows, "last_reviewed", "Date Last Reviewed")
                self._rows = rows
            return self._rows

        @property
        def status(self):
            """String for the definition's status."""

            if not hasattr(self, "_status"):
                self._status = None
                for tag in ("DefinitionStatus", "TranslatedStatus"):
                    self._status = self.node.find(tag)
                    if self._status is not None:
                        self._status = Doc.get_text(self._status, "").strip()
                        break
            return self._status

        @property
        def status_date(self):
            """Date of the definition's current status."""

            if not hasattr(self, "_status_date"):
                self._status_date = None
                for tag in ("StatusDate", "TranslatedStatusDate"):
                    node = self.node.find(tag)
                    if node is not None:
                        self._status_date = Doc.get_text(node, "").strip()
                        break
            return self._status_date

        @property
        def term_table(self):
            """Table showing term names and customized definitions."""

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
                alt_names = ""
                if self.langcode == "es":
                    if name.spanish_name is None:
                        args = markup, " (en ingl\xe9s)", B.CLASS("special")
                        markup = B.SPAN(*args)
                    elif name.alternate_spanish_names:
                        alt_names = name.alternate_spanish_names
                        alt_names = ", ".join(alt_names)
                        alt_names = f" \xa0[{alt_names}]"
                args = [markup, f" (CDR{name.id})", alt_names]
                if name.blocked:
                    args = ["BLOCKED - "] + args + [B.CLASS("blocked")]
                table.append(B.TR(B.TD("Name"), B.TD(*args), B.CLASS("name")))
                if not name.blocked:
                    table.append(name.resolve_placeholders(self))
            return table

        @property
        def text(self):
            """Definition text with placeholders to be resolved."""

            if not hasattr(self, "_text"):
                self._text = self.node.find("DefinitionText")
            return self._text

        @property
        def videos(self):
            """Sequence of embedded videos for this definition."""

            if not hasattr(self, "_videos"):
                nodes = self.node.findall("EmbeddedVideo")
                self._videos = [Concept.Video(node) for node in nodes]
            return self._videos

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

            @property
            def row(self):
                """HTML markup for this comment."""

                if not hasattr(self, "_row"):
                    wrapper = etree.Element("GlossaryTermDef")
                    wrapper.append(self.__node)
                    doc = Doc(Concept.GUEST, xml=etree.tostring(wrapper))
                    result = doc.filter(Concept.FILTER)
                    self._row = html.fromstring(str(result.result_tree))
                return self._row


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

        @property
        def row(self):
            """HTML markup for the link."""

            if not hasattr(self, "_row"):
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
                self._row = builder.TR(label, builder.TD(*args))
            return self._row

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
            """CDR ID for the image document."""

            if not hasattr(self, "_id"):
                node = self.node.find("MediaID")
                try:
                    self._id = Doc.extract_id(node.get(f"{{{Doc.NS}}}ref"))
                except:
                    self._id = None
                if not hasattr(self, "_text"):
                    self._text = Doc.get_text(node, "").strip()
            return self._id

        @property
        def node(self):
            """Wrapper node for the media link."""
            return self.__node

        @property
        def row(self):
            """HTML markup for the the image's table row."""

            if not hasattr(self, "_row"):
                B = builder
                img = B.IMG(src=self.URL.format(self.id))
                args = self.text, B.BR(), img
                self._row = B.TR(B.TD("Media Link"), B.TD(*args))
            return self._row

        @property
        def text(self):
            """Text to be displayed above the image."""

            if not hasattr(self, "_text"):
                node = self.node.find("MediaID")
                self._text = Doc.get_text(node, "").strip()
                if not hasattr(self, "_id"):
                    try:
                        self._id = Doc.extract_id(node.get(self.CDR_REF))
                    except:
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
            """Extra spanish names."""

            if not hasattr(self, "_alternate_spanish_names"):
                self._alternate_spanish_names = []
                path = "TranslatedName/TermNameString"
                for node in self.doc.root.findall(path):
                    if node.get("NameType") == "alternate":
                        self._alternate_spanish_names.append(node)
                    elif not hasattr(self, "_spanish_name"):
                        self._spanish_name = node
            return self._alternate_spanish_names

        @property
        def blocked(self):
            """True if the name document can't be published."""
            self.doc.active_status != Doc.ACTIVE

        @property
        def doc(self):
            """CDR `Doc` object for the GlossaryTermName document."""

            if not hasattr(self, "_doc"):
                self._doc = Doc(Concept.GUEST, id=self.id)
            return self._doc

        @property
        def id(self):
            """CDR ID for the GlossaryTermName document."""
            return self.__id

        @property
        def english_name(self):
            """English name for the glossary term."""

            if not hasattr(self, "_english_name"):
                node = self.doc.root.find("TermName/TermNameString")
                self._english_name = node
            return self._english_name

        @property
        def replacements(self):
            """The name's replacement strings for definition placeholders."""

            if not hasattr(self, "_replacements"):
                self._replacements = {}
                for node in self.doc.root.findall("ReplacementText"):
                    self._replacements[node.get("name")] = node
            return self._replacements

        @property
        def spanish_name(self):
            """Primary (non-"alternate") Spanish name for the term."""

            if not hasattr(self, "_spanish_name"):
                self._spanish_name = None
                alternates = []
                path = "TranslatedName/TermNameString"
                for node in self.doc.root.findall(path):
                    if node.get("NameType") != "alternate":
                        self._spanish_name = node
                    else:
                        alternates.append(node)
                if not hasattr(self, "_alternate_spanish_names"):
                    self._alternate_spanish_names = alternates
            return self._spanish_name

        @staticmethod
        def markup_for_name(name):
            """Highlight insertion/deletion markup for the term name.

            Pass:
                name - parsed XML node for the term name string
            """

            doc = Doc(Concept.GUEST, xml=etree.tostring(name))
            result = doc.filter(Concept.FILTER)
            return html.fromstring(str(result.result_tree))

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

        @property
        def id(self):
            """CDR ID for the video's Media document."""

            if not hasattr(self, "_id"):
                node = self.node.find("VideoID")
                self._id = None
                if node is not None:
                    try:
                        self._id = Doc.extract_id(node.get(f"{{{Doc.NS}}}ref"))
                    except:
                        pass
            return self._id

        @property
        def img(self):
            """Still image displayed for the video."""

            if not hasattr(self, "_img"):
                url = self.IMAGE_URL.format(self.youtube_id)
                self._img = builder.IMG(src=url)
            return self._img

        @property
        def link(self):
            """Link for playing the YouTube video."""

            if not hasattr(self, "_link"):
                url = self.VIDEO_URL.format(self.youtube_id)
                self._link = builder.A("Watch video on YouTube", href=url)
            return self._link

        @property
        def node(self):
            """Wrapper element for the video information."""
            return self.__node

        @property
        def row(self):
            """HTML markup for displaying the video info and link."""

            if not hasattr(self, "_row"):
                B = builder
                args = self.text, B.BR(), self.img, B.BR(), self.link
                self._row = B.TR(B.TD("Video Link"), B.TD(*args))
            return self._row

        @property
        def text(self):
            """String describing the video, displayed at the top."""

            if not hasattr(self, "_text"):
                self._text = None
                node = self.node.find("SpecificMediaTitle")
                if node is not None:
                    self._text = Doc.get_text(node, "").strip()
                if not self._text:
                    node = self.node.find("VideoID")
                    if node is not None:
                        self._text = Doc.get_text(node, "").strip()
            return self._text

        @property
        def youtube_id(self):
            """Token for the URL to play the video."""

            if not hasattr(self, "_youtube_id"):
                doc = Doc(self.SESSION, id=self.id)
                node = doc.root.find("PhysicalMedia/VideoData/HostingID")
                self._youtube_id = Doc.get_text(node, "").strip() or None
            return self._youtube_id


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
