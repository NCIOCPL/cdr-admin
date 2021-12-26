#!/usr/bin/env python3

"""Show drug terms which differ from their EVS counterparts.

Provides a form with checkboxes to select drug terms to be refreshed from
the EVS.
"""

from cdrapi.docs import Doc
from cdrcgi import Controller
from datetime import date, datetime
from difflib import SequenceMatcher
from functools import cached_property
from json import load, dump
from lxml import etree
from ModifyDocs import Job
from nci_thesaurus import Concept
from re import compile, escape, sub, UNICODE
from requests import get
from string import punctuation
from time import sleep
from uuid import uuid1


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "Drug Term Refresh"
    LOGNAME = "drug-term-refresh"
    EVS_API = "https://api-evsrest.nci.nih.gov/api/v1/concept/ncit"
    SEARCH_API = f"{EVS_API}/search"
    FETCH_API = f"{EVS_API}?include=full&list="
    BATCH_SIZE = 100
    CTRP_AGENT_TERMINOLOGY = "C116978"
    NCI_DRUG_DICTIONARY_TERMINOLOGY = "C176424"
    SUBSET_PARENTS = CTRP_AGENT_TERMINOLOGY, NCI_DRUG_DICTIONARY_TERMINOLOGY
    EVS_MAX_REQUESTS_ALLOWED_PER_SECOND = 3
    EVS_SLEEP = 1 / EVS_MAX_REQUESTS_ALLOWED_PER_SECOND
    CSS = "../../stylesheets/RefreshDrugTermsFromEVS.css"

    def populate_form(self, page):
        """Show terms differing from the EVS.

        If any refresh requests were specified, perform them and show the
        results above the form.

        Pass:
            page - HTMLPage object where we communicate with the user
        """

        # Perform and report any requested updates from the EVS.
        actions = self.fields.getlist("actions")
        if actions:
            self.__show_updates(page, actions)

        # Remember where we cached the concepts retrieved from the EVS.
        page.form.append(page.hidden_field("concepts", self.concepts_path))

        # Start building the form.
        start = datetime.now()
        page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))
        body = page.B.TBODY()

        # Check each of the EVS concepts for deltas with the CDR documents.
        terms = 0
        for concept in self.concepts:
            doc = self.__doc_for_code(concept.code)
            if not doc:
                continue
            if not concept.differs_from(doc):
                continue
            terms += 1
            code = concept.code
            name = concept.name
            label = f"Refresh CDR{doc.cdr_id} from {code} ({name})"
            value = f"{code}-{doc.cdr_id}"
            opts = dict(value=value, label=label)
            checkbox = page.checkbox("actions", **opts)
            body.append(
                page.B.TR(
                    page.B.TH(checkbox, colspan="3"),
                    page.B.CLASS("cb-row")
                )
            )
            if concept.normalized_name != doc.normalized_name:
                row = page.B.TR(
                    page.B.TH("Name"),
                    page.B.TD(doc.name),
                    page.B.TD(concept.name),
                )
                body.append(row)
            n = set([concept.normalized_name])
            c = set(concept.normalized_other_names) - n
            d = set(doc.normalized_other_names)
            if c != d:
                concept_list = page.B.UL()
                for other_name in sorted(concept.other_names):
                    if Normalizer.normalize(other_name.name) not in d:
                        name = page.B.B(other_name.name)
                    else:
                        name = other_name.name
                    concept_list.append(page.B.LI(name))
                doc_list = page.B.UL()
                for name in sorted(doc.other_names):
                    if Normalizer.normalize(name) not in c:
                        doc_list.append(page.B.LI(page.B.B(name)))
                    else:
                        doc_list.append(page.B.LI(name))
                row = page.B.TR(
                    page.B.TH("Other Name(s)"),
                    page.B.TD(doc_list),
                    page.B.TD(concept_list),
                )
                body.append(row)
            if concept.normalized_definitions != doc.normalized_definitions:
                if len(doc.definitions) == 1:
                    old_def = doc.definitions[0]
                else:
                    old_def = page.B.UL()
                    for definition in sorted(doc.definitions):
                        old_def.append(page.B.LI(definition))
                if len(concept.definitions) == 1:
                    new_def = concept.definitions[0]
                else:
                    new_def = page.B.UL()
                    for definition in sorted(concept.definitions):
                        new_def.append(page.B.LI(definition))
                if isinstance(old_def, str) and isinstance(new_def, str):
                    new_def = self.__show_changes(page.B, old_def, new_def)
                row = page.B.TR(
                    page.B.TH("Definition"),
                    page.B.TD(old_def),
                    page.B.TD(new_def),
                )
                body.append(row)

        # Assemble the table and connect it to the page.
        caption = f"Drug Terms Which Can Be Refreshed From the EVS ({terms})"
        table = page.B.TABLE(
            page.B.CAPTION(caption),
            page.B.THEAD(
                page.B.TR(
                    page.B.TH("Element", page.B.CLASS("sticky")),
                    page.B.TH("CDR", page.B.CLASS("sticky")),
                    page.B.TH("EVS", page.B.CLASS("sticky")),
                )
            ),
            body
        )
        elapsed = datetime.now() - start
        msg = f"Checked {len(self.concepts)} EVS concepts in {elapsed}."
        row = page.B.TR(page.B.TD(msg, page.B.CLASS("footnote"), colspan="3"))
        body.append(row)
        page.form.append(table)

    def show_report(self):
        """Everything is shown on the form page."""
        self.show_form()

    @cached_property
    def blocked(self):
        """CDR IDs of blocked Term documents."""

        query = self.Query("document d", "d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Term'")
        query.where("d.active_status <> 'A'")
        return {row.id for row in query.execute(self.cursor).fetchall()}

    @cached_property
    def codes(self):
        """Map of EVS concept codes to CDR IDs."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Term/NCIThesaurusConcept'")
        rows = query.execute(self.cursor).fetchall()
        docs_for_codes = {}
        for doc_id, code in rows:
            if doc_id not in self.blocked and doc_id in self.index_terms:
                code = code.strip().upper()
                if code not in docs_for_codes:
                    docs_for_codes[code] = []
                docs_for_codes[code].append(doc_id)
        codes = {}
        for code in docs_for_codes:
            if len(docs_for_codes[code]) == 1:
                codes[code] = docs_for_codes[code][0]
        return codes

    @cached_property
    def concepts(self):
        """Dictionary of EVS concepts, indexed by concept code."""

        # Load concept values from JSON cache, if available.
        if self.fields.getvalue("concepts"):
            path = self.fields.getvalue("concepts")
            with open(path) as fp:
                concepts = load(fp)
            self.logger.info("loaded concepts from %s", path)

        # Otherwise, fetch the concepts from the EVS and cache them.
        else:
            start = datetime.now()
            parms = dict(
                fromRecord=0,
                include="full",
                pageSize=self.BATCH_SIZE,
                subset=",".join(self.SUBSET_PARENTS),
            )
            done = False
            concepts = []
            while not done:

                # Don't give up right away when an error is encountered.
                tries = 5
                while tries > 0:
                    try:
                        response = get(self.SEARCH_API, params=parms)
                        if not response.ok:
                            raise Exception(response.reason)
                        values = response.json()
                        if not values.get("total"):
                            done = True
                            break
                        concepts += values.get("concepts")
                        parms["fromRecord"] += self.BATCH_SIZE
                        sleep(self.EVS_SLEEP)
                        break
                    except Exception:
                        tries -= 1
                        if tries < 1:
                            self.bail("EVS not available")
                        self.logger.exception("failure fetching concepts")
                        sleep(self.EVS_SLEEP)
            args = len(concepts), datetime.now() - start
            self.logger.info("fetched %d concepts in %s", *args)
            with open(self.concepts_path, "w") as fp:
                dump(concepts, fp, indent=2)

        # Parse and save the concepts.
        concept_map = []
        for values in concepts:
            concept = EVSConcept(values)
            concept_map.append(concept)
        concept_map = sorted(concept_map)
        return concept_map

    @cached_property
    def concepts_path(self):
        """Location of cached concepts."""

        concepts_path = self.fields.getvalue("concepts")
        if not concepts_path:
            concepts_path = f"d:/tmp/{uuid1()}.json"
        return concepts_path

    @cached_property
    def index_terms(self):
        """CDR IDs of Term documents with a term type of 'Index term'."""

        query = self.Query("query_term", "doc_id").unique()
        query.where("path = '/Term/TermType/TermTypeName'")
        query.where("value = 'Index term'")
        return {row.doc_id for row in query.execute(self.cursor).fetchall()}

    def __doc_for_code(self, code):
        """Fetch the CDR document matching the caller's EVS concept code.

        Pass:
            code - string for the EVS concept code

        Return:
            `CDRTerm` object if found, else `None`
        """

        if code in self.codes:
            doc_id = self.codes[code]
            try:
                query = self.Query("document", "xml")
                query.where(query.Condition("id", doc_id))
                row = query.execute(self.cursor).fetchone()
                root = etree.fromstring(row.xml.encode("utf-8"))
                return CDRTerm(doc_id, root)
            except Exception:
                self.logger.exception("fetching CDR%s for %s", doc_id, code)
        return None

    @staticmethod
    def __show_changes(B, old, new):
        """Highlight deltas in the EVS definition versus the CDR definition.

        If there are any insertions or replacements, we show those in red.
        Otherwise, we just show the deletions with strikethrough.

        Pass:
            B - HTML builder from the lxml package
            old - definition currently in the CDR document
            new - definition found in the EVS concept record

        Return:
            HTML div object
        """

        sm = SequenceMatcher(None, old, new)
        pieces = []
        new_segments_shown = False
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("replace", "insert"):
                segment = new[j1:j2]
                pieces.append(B.SPAN(segment, B.CLASS("insertion")))
                new_segments_shown = True
            elif tag == "equal":
                segment = new[j1:j2]
                pieces.append(B.SPAN(segment))
        if not new_segments_shown:
            sm = SequenceMatcher(None, old, new)
            pieces = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag in ("replace", "delete"):
                    segment = old[i1:i2]
                    pieces.append(B.SPAN(segment, B.CLASS("deletion")))
                elif tag == "equal":
                    segment = new[j1:j2]
                    pieces.append(B.SPAN(segment))
        return B.DIV(*pieces)

    def __show_updates(self, page, actions):
        """Perform and show requested drug term refresh actions.

        Pass:
            page - object on which results are displayed
            actions - list of values in the form code-cdrid
        """

        # Fetch the concepts we've been asked to use.
        rows = [value.split("-") for value in actions]
        codes = [row[0] for row in rows]
        offset = 0
        concepts = {}
        while offset < len(codes):
            subset = codes[offset:offset+self.BATCH_SIZE]
            offset += self.BATCH_SIZE
            api = self.FETCH_API + ",".join(subset)
            response = get(api)
            if offset < len(codes):
                sleep(self.EVS_SLEEP)
            for values in response.json():
                concept = EVSConcept(values=values)
                concepts[concept.code] = concept

        # Start the table for displaying the actions performed.
        body = page.B.TBODY()
        table = page.B.TABLE(
            page.B.CAPTION("Actions"),
            page.B.THEAD(
                page.B.TH("CDR ID"),
                page.B.TH("Code"),
                page.B.TH("Name"),
                page.B.TH("Notes"),
            ),
            body
        )

        # Make sure we will be able to check out the CDR documents.
        docs = {}
        for code, doc_id in rows:
            doc_id = int(doc_id)
            if code not in concepts:
                docs[doc_id] = None
            else:
                docs[doc_id] = concepts[code]
                try:
                    doc = Doc(self.session, id=doc_id)
                    doc.check_out()
                except Exception:
                    concepts[code].unavailable = True

        # Invoke the global change harness to perform the updates.
        self.successes = set()
        self.failures = {}
        Updater(self, docs).run()

        # Populate the table reporting the results.
        for doc_id in sorted(docs):
            concept = docs[doc_id]
            if concept is None:
                # This would be a very rare and odd edge case, in which the
                # concept was removed from the EVS between the time the form
                # was displayed and the time the refresh request was submitted.
                values = doc_id, "", "", "Concept not found"
            else:
                if doc_id in self.failures:
                    note = self.failures[doc_id]
                elif concept.unavailable:
                    note = "Term document checked out to another user."
                elif doc_id not in self.successes:
                    note = "CDR document unavailable for update"
                else:
                    note = "Refreshed"
                values = doc_id, concept.code, concept.name, note
            row = page.B.TR()
            for value in values:
                row.append(page.B.TD(str(value)))
            body.append(row)
        page.form.append(table)


class Normalizer:
    """Base class for `EVSConcept` and `CDRTerm` classes."""

    PUNCTUATION = compile(f"[{escape(punctuation)}]")
    SUFFIX = compile(r"\s*\(NCI\d\d\)$")
    NON_BREAKING_SPACE = chr(160)
    THIN_SPACE = chr(8201)
    ZERO_WIDTH_SPACE = chr(8203)
    FUNKY_WHITESPACE = NON_BREAKING_SPACE, THIN_SPACE, ZERO_WIDTH_SPACE

    @classmethod
    def normalize(cls, text, **opts):
        """
        Prepare a string value for comparison.

        TODO: discuss options with the users.

        The users have decided to eliminate duplicates of OtherName blocks
        for which the term name value differs only in spacing or case. They
        subsequently decided to apply the same approach to definitions.
        See https://tracker.nci.nih.gov/browse/OCECDR-4153.

        Pass:
            text - original value
            strip_punctuation - if True also remove punctuation
            strip_suffix - if True strip " (NCI04)" and similar suffixes

        Return:
            lowercase version of string with spacing normalized
        """

        return text.lower()
        #for c in self.FUNKY_WHITESPACE:
        #    text = text.replace(c, " ")
        #return sub(r"\s+", " ", text).strip().lower()
        #return sub(r"\s+", " ", sub(r"\W", " ", text)).lower().strip()
        """
        step1 = sub(r"\s+", " ", text.strip(), UNICODE)
        if opts.get("strip_suffix"):
            step2 = cls.SUFFIX.sub("", step1, UNICODE)
        else:
            step2 = step1
        step3 = step2.lower()
        step4 = sub(r"[^\w ]", "", step3, UNICODE)
        if opts.get("strip_punctuation", True):
            step5 = cls.PUNCTUATION.sub("", step4, UNICODE)
        else:
            step5 = step4
        return step5
        """

    def normalize_space(self, text):
        """Fold Unicode space characters into ASCII space.

        Pass:
            text - original string

        Return:
            original string with whitespace normalized
        """

        for c in self.FUNKY_WHITESPACE:
            text = text.replace(c, " ")
        return sub(r"\s+", " ", text).strip()

    @cached_property
    def normalized_name(self):
        """Normalized version of the preferred name."""
        return self.normalize(self.name)

    @cached_property
    def normalized_other_names(self):
        """Dictionary of other names indexed by normalized key."""

        normalized_other_names = {}
        for other_name in self.other_names:
            if isinstance(other_name, str):
                key = self.normalize(other_name)
            else:
                key = self.normalize(other_name.name)
            if key != self.normalized_name:
                if key not in normalized_other_names:
                    normalized_other_names[key] = other_name
        return normalized_other_names

    @cached_property
    def normalized_definitions(self):
        """Sequence of normalized definition strings."""

        opts = dict(strip_suffix=True)
        return {self.normalize(d, **opts) for d in self.definitions}


class EVSConcept(Normalizer):
    """Parsed concept record from the EVS."""

    NAME_PROPS = "CAS_Registry", "NSC_CODE", "IND_Code"
    DEFINITION_TYPES = "DEFINITION", "ALT_DEFINITION"

    def __init__(self, values):
        """Remember the caller's values.

        We also initialize a flag indicating whether the matching CDR document
        is checked out to another user.

        Pass:
            values - nested values extracted from the serialized JSON string
        """

        self.__values = values
        self.unavailable = False

    def __lt__(self, other):
        """Support sorting by the normalized name of the concept.

        Pass:
            other - concept being compared with this one

        Return:
            `True` if this concept should be sorted before the other one
        """

        return self.key < other.key

    def differs_from(self, doc):
        """Compare this concept with the corresponding CDR document.

        Pass:
            doc - reference to the matching `CDRTerm` object

        Return:
            `True` if any names or definitions differ
        """

        if self.normalized_name != doc.normalized_name:
            return True
        if set(self.normalized_other_names) != set(doc.normalized_other_names):
            return True
        if self.normalized_definitions != doc.normalized_definitions:
            return True
        return False

    @cached_property
    def code(self):
        """Concept code for this EVS record."""
        return self.__values.get("code", "").strip().upper()

    @cached_property
    def definitions(self):
        """Primary or alternate definitions for the concept."""

        definitions = []
        for values in self.__values.get("definitions", []):
            if values.get("type") in self.DEFINITION_TYPES:
                if values.get("source") == "NCI":
                    definition = values.get("definition", "").strip()
                    if definition:
                        definition = self.SUFFIX.sub("", definition)
                        definition = definition.removeprefix("NCI|")
                        definition = self.normalize_space(definition)
                        definitions.append(definition)
        return definitions

    @cached_property
    def key(self):
        """Tuple of the concept's normalized name string and code."""
        return self.normalized_name, self.code

    @cached_property
    def name(self):
        """Preferred name string for the concept."""
        return self.normalize_space(self.__values.get("name", ""))

    @cached_property
    def other_names(self):
        """Sequence of `OtherName` objects."""

        other_names = []
        for synonym in self.__values.get("synonyms", []):
            if synonym.get("type") == "FULL_SYN":
                name = synonym.get("name", "").strip()
                if name:
                    source = synonym.get("source", "").strip()
                    if source == "NCI":
                        name = self.normalize_space(name)
                        if self.normalize(name) != self.normalized_name:
                            group = synonym.get("termGroup", "").strip()
                            other_name = OtherName(name, group, "NCI")
                            other_names.append(other_name)
        for prop_name in self.NAME_PROPS:
            for code in self.properties.get(prop_name, []):
                code = self.normalize_space(code.strip())
                if code and self.normalize(code) != self.normalized_name:
                    other_names.append(OtherName(code, prop_name))
        return other_names

    @cached_property
    def properties(self):
        """Dictionary of named properties."""

        properties = {}
        for property in self.__values.get("properties", []):
            name = property.get("type")
            if name:
                value = property.get("value", "").strip()
                if value:
                    if name not in properties:
                        properties[name] = []
                    properties[name].append(value)
        return properties


class OtherName:
    """Synonyms and codes found in an EVS concept record."""

    SKIP = {"PreferredName", "ReviewStatus"}
    TERM_TYPE_MAP = {
        "PT"               : "Synonym", # "Preferred term",
        "AB"               : "Abbreviation",
        "AQ"               : "Obsolete name",
        "BR"               : "US brand name",
        "CN"               : "Code name",
        "FB"               : "Foreign brand name",
        "SN"               : "Chemical structure name",
        "SY"               : "Synonym",
        "INDCode"          : "IND code",
        "NscCode"          : "NSC code",
        "CAS_Registry_Name": "CAS Registry name",
        "IND_Code"         : "IND code",
        "NSC_Code"         : "NSC code",
        "CAS_Registry"     : "CAS Registry name"
    }

    def __init__(self, name, group, source=None):
        """
        Extract the values we'll need for generating an OtherName block.

        Pass:
            name - string for the other name
            group - string for the type of name
            source - string for the name source
        """

        self.name = name
        self.group = group
        self.source = source
        self.include = source == "NCI" if source else True

    def __lt__(self, other):
        """Support sorting the concept's names.

        Pass:
            other - reference to other name being compared with this one

        Return:
            `True` if this name should sort before the other one
        """

        return self.name < other.name

    def convert(self, concept_code, status="Reviewed"):
        """
        Create an OtherName block for the CDR Term document.

        Pass:
            concept_code - added as the source ID for a primary term
            status - whether CIAT needs to review the name

        Return:
            reference to lxml `_Element` object
        """

        term_type = self.TERM_TYPE_MAP.get(self.group, "????" + self.group)
        node = etree.Element("OtherName")
        etree.SubElement(node, "OtherTermName").text = self.name
        etree.SubElement(node, "OtherNameType").text = term_type
        info = etree.SubElement(node, "SourceInformation")
        source = etree.SubElement(info, "VocabularySource")
        etree.SubElement(source, "SourceCode").text = "NCI Thesaurus"
        etree.SubElement(source, "SourceTermType").text = self.group
        if self.group == "PT" and concept_code:
            child = etree.SubElement(source, "SourceTermId")
            child.text = concept_code
        etree.SubElement(node, "ReviewStatus").text = status
        return node


class CDRTerm(Normalizer):
    """Parsed CDR drug term document."""

    def __init__(self, cdr_id, root):
        """Remember the caller's values.

        Pass:
            cdr_id - unique ID integer for the CDR Term document
            root - top-level node of the parsed XML document
        """

        self.cdr_id = int(cdr_id)
        self.root = root

    @cached_property
    def definitions(self):
        """Sequence of definition strings found in the CDR document."""

        definitions = []
        for node in self.root.findall("Definition/DefinitionText"):
            definition = Doc.get_text(node, "").strip()
            if definition:
                definitions.append(self.normalize_space(definition))
        return definitions

    @cached_property
    def name(self):
        """Preferred name for the CDR drug term document."""

        name = Doc.get_text(self.root.find("PreferredName"))
        return self.normalize_space(name)

    @cached_property
    def other_names(self):
        """Synonyms for the drug term."""

        other_names = set()
        for node in self.root.findall("OtherName/OtherTermName"):
            name = Doc.get_text(node, "").strip()
            if name:
                other_names.add(self.normalize_space(name))
        return other_names


class Updater(Job):
    """Global change job used to update CDR term documents from the EVS."""

    LOGNAME = Control.LOGNAME
    COMMENT = f"Term document refreshed from EVS {date.today()}"
    NCIT = "NCI Thesaurus"
    TYPE = "Health professional"

    def __init__(self, control, docs):
        """Capture the caller's values.

        Pass:
            control - used to record successes and failures
            docs - dictionary of `EVSConcept` objects indexded by CDR ID
        """

        self.__control = control
        self.__docs = docs
        opts = dict(session=control.session, mode="live", console=False)
        Job.__init__(self, **opts)

    def select(self):
        """Return sequence of CDR ID integers for documents to transform."""
        return sorted([id for id in self.__docs if self.__docs[id]])

    def transform(self, doc):
        """Refresh the CDR document with values from the EVS concept.

        Pass:
            doc - reference to `cdr.Doc` object

        Return:
            serialized XML for the modified document
        """

        # Find the concept whose values we will apply to the CDR document.
        int_id = Doc.extract_id(doc.id)
        concept = self.__docs[int_id]

        # Catch any failures.
        try:

            # Find where our new elements will be inserted.
            root = etree.fromstring(doc.xml)
            position = 0
            for node in root:
                if node.tag in ("OtherName", "Definition"):
                    break
                position += 1

            # Make sure the document has the correct preferred name, statuses.
            root.find("PreferredName").text = concept.name
            for node in root.findall("TermStatus"):
                node.text = "Reviewed-retain"
            node = root.find("ReviewStatus")
            if node is not None:
                node.text = "Reviewed"

            # Start with a clean slate.
            etree.strip_elements(root, "OtherName", "Definition")

            # Don't duplicate the preferred name in the OtherName blocks.
            names = set([concept.normalized_name])

            # Insert the nodes in reverse order.
            for definition in concept.definitions:
                root.insert(position, self.__make_definition_node(definition))
            for key in reversed(sorted(concept.normalized_other_names)):
                if key not in names:
                    names.add(key)
                    other_name = concept.normalized_other_names[key]
                    root.insert(position, other_name.convert(concept.code))

            # Record the transformation and return the results.
            self.__control.successes.add(int_id)
            return etree.tostring(root)

        except Exception as e:

            # Record the failure.
            self.logger.exception(f"CDR{int_id}")
            self.__control.failures[int_id] = str(e)

    def __make_definition_node(self, text):
        """Create the block for the definition being added.

        Pass:
            text - the string for the definition

        Return:
            `_Element` created using the lxml package
        """

        node = etree.Element("Definition")
        etree.SubElement(node, "DefinitionText").text = text
        etree.SubElement(node, "DefinitionType").text = self.TYPE
        source = etree.SubElement(node, "DefinitionSource")
        etree.SubElement(source, "DefinitionSourceName").text = self.NCIT
        etree.SubElement(node, "ReviewStatus").text = "Reviewed"
        return node


if __name__ == "__main__":
    """Allow the script to be loaded as a module."""
    Control().run()
