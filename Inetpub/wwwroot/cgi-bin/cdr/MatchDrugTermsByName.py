#!/usr/bin/env python3

"""Look for matches by name between EVS concepts and CDR drug term documents.

Provides two forms. One is for CDR drug term documents which have no EVS
concept code but at least one of whose names uniquely matches one EVS concept
whose code is not found in any CDR drug term documents. This form has
checkboxes for selecting which of these pairs should have the CDR drug term
documents updated with the names, definitions, and concept codes of their
matching EVS concepts. The other for is for EVS concept records whose concept
codes are not found in any CDR documents, and none of whose names appear in
other concepts or in any of the CDR drug term documents. Checkboxes are
provided on this form selecting which concepts should be used to create new
CDR drug term documents.

The forms are followed by a list of concepts which cannot be matched or
imported, each with the explanation for the concept's problem preventing
that match or import. Finally a list of CDR drug term documents which are
not unambiguously matchable with any EVS concept, each with a description
of the document's anomaly.
"""

from cdrapi.docs import Doc
from cdrcgi import Controller
from datetime import date, datetime
from difflib import SequenceMatcher
from functools import cached_property
from json import load, dump
from lxml import etree
from ModifyDocs import Job
from re import compile, escape, sub
from requests import get
from string import punctuation
from time import sleep
from uuid import uuid1


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "Match Drug Terms By Name"
    LOGNAME = "drug-term-name-matches"
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
    CDR_ID = compile(r"(\d+)\.xml$")
    DRUG_AGENT = 256166
    DRUG_AGENT_CATEGORY = 256164
    DRUG_AGENT_COMBINATION = 256171
    SEMANTIC_TYPES = DRUG_AGENT, DRUG_AGENT_CATEGORY, DRUG_AGENT_COMBINATION

    def populate_form(self, page):
        """Show terms differing from the EVS.

        If any refresh requests were specified, perform them and show the
        results above the form.

        Pass:
            page - HTMLPage object where we communicate with the user
        """

        # Perform and report any requested updates from the EVS.
        start = datetime.now()
        refreshes = self.fields.getlist("refreshes")
        creates = self.fields.getlist("creates")
        if refreshes or creates:
            self.__show_updates(page, refreshes, creates)

        # Figure out the disposition for the concepts.
        problems = []
        matched = []
        unmatched = []
        ok_docs = set()
        for concept in sorted(self.concepts.values()):
            doc_ids = self.codes.get(concept.code, [])
            if len(doc_ids) == 1:
                ok_docs.add(doc_ids[0])
                continue
            elif len(doc_ids) > 1:
                docs = ", ".join([f"CDR{id}" for id in sorted(doc_ids)])
                problem = (f"Concept code {concept.code} ({concept.name}) "
                           f"found in {docs}")
                problems.append(problem)
                continue
            problem = None
            matches = set()
            names = [concept.normalized_name]
            names += list(concept.normalized_other_names)
            for name in names:
                codes = self.evs_names[name]
                if len(codes) != 1:
                    codes.remove(concept.code)
                    codes = ", ".join(codes)
                    problem = (f"Name {name!r} for concept "
                               f"{concept.code} also found in {codes}")
                    problems.append(problem)
                    break
                ids = self.cdr_names.get(name, [])
                if len(ids) == 1:
                    matches.add(ids[0])
                elif len(ids) > 1:
                    ids = ", ".join([f"CDR{id}" for id in ids])
                    problem = (f"Name {name!r} for concept {concept.code} "
                               f"found in {ids}")
                    problems.append(problem)
                    break
            if not problem:
                if len(matches) == 1:
                    doc_id = matches.pop()
                    problem = self.__check_match(doc_id, concept)
                    if problem:
                        problems.append(problem)
                    else:
                        matched.append((concept.code, doc_id))
                elif len(matches) == 0:
                    unmatched.append(concept.code)
                else:
                    ids = ", ".join([f"CDR{id}" for id in sorted(matches)])
                    problem = (f"Concept {concept.code} has name matches "
                               f"with {ids}")
                    problems.append(problem)

        # Remember where we cached the concepts retrieved from the EVS.
        page.form.append(page.hidden_field("concepts", self.concepts_path))

        # Start building the form.
        page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))

        # Create a table showing matches we have found.
        body = page.B.TBODY()
        for code, doc_id in matched:
            ok_docs.add(doc_id)
            concept = self.concepts[code]
            doc = self.docs[doc_id]
            name = concept.name
            label = f"Match and refresh CDR{doc.cdr_id} from {code} ({name})"
            value = f"{code}-{doc_id}"
            opts = dict(value=value, label=label)
            checkbox = page.checkbox("refreshes", **opts)
            body.append(
                page.B.TR(
                    page.B.TH(checkbox, colspan="3"),
                    page.B.CLASS("cb-row")
                )
            )
            row = page.B.TR(
                page.B.TH("Name"),
                page.B.TD(doc.name),
                page.B.TD(concept.name),
            )
            body.append(row)
            n = set([concept.normalized_name])
            c = set(concept.normalized_other_names) - n
            d = set(doc.normalized_other_names)
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
        count = len(matched)
        caption = f"Drug Terms Which Can Be Linked With EVS Concepts ({count})"
        table = page.B.TABLE(
            page.B.CAPTION(caption),
            page.B.THEAD(
                page.B.TR(
                    page.B.TH("Element"),
                    page.B.TH("CDR"),
                    page.B.TH("EVS"),
                )
            ),
            body
        )
        page.form.append(table)

        # Create another table for concepts which have no CDR matches.
        body = page.B.TBODY()
        concepts = []
        for code in unmatched:
            concepts.append(self.concepts[code])
        for concept in sorted(concepts):
            label = f"Import concept {concept.code} ({concept.name})"
            opts = dict(value=concept.code, label=label)
            checkbox = page.checkbox("creates", **opts)
            page.form.append(checkbox)
            body.append(
                page.B.TR(
                    page.B.TH(checkbox, colspan="2"),
                    page.B.CLASS("cb-row")
                )
            )
            names = page.B.UL()
            for other_name in sorted(concept.other_names):
                name = other_name.name
                names.append(page.B.LI(name))
            row = page.B.TR(
                page.B.TH("Other Names"),
                page.B.TD(names),
            )
            body.append(row)
            for definition in concept.definitions:
                row = page.B.TR(
                    page.B.TH("Definition"),
                    page.B.TD(definition),
                )
                body.append(row)
        count = len(unmatched)
        caption = f"Concepts Importable As New CDR Drug Terms ({count})"
        table = page.B.TABLE(
            page.B.CAPTION(caption),
            page.B.THEAD(
                page.B.TR(
                    page.B.TH("Element"),
                    page.B.TH("Values"),
                )
            ),
            body
        )
        page.form.append(table)

        # Show the concepts with problems.
        count = len(problems)
        h2 = page.B.H2(f"Concepts Unable To Be Matched Or Imported ({count})")
        page.form.append(h2)
        problem_list = page.B.UL()
        for problem in problems:
            problem_list.append(page.B.LI(problem))
        page.form.append(problem_list)

        # Finally, figure out which CDR drug term documents can't be matched.
        problems = []
        for doc_id in sorted(self.docs):
            if doc_id in ok_docs:
                continue
            codes = self.doc_ids.get(doc_id, [])
            if len(codes) == 1:
                continue
            doc = self.docs[doc_id]
            name = doc.name
            if len(codes) > 1:
                problem = page.B.LI(f"CDR{doc_id} ({name}) "
                                    f"linked with {codes}")
                problems.append(problem)
            if not codes:
                problem = page.B.LI(f"CDR{doc_id} ({name}) cannot be matched "
                                    "unambiguously with any EVS concept")
                problems.append(problem)
        count = len(problems)
        h2 = page.B.H2(f"CDR Drug Term Documents With Anomalies ({count})")
        page.form.append(h2)
        page.form.append(page.B.UL(*problems))
        elapsed = datetime.now() - start
        tasks = [
            f"Checked {len(self.concepts)} EVS concepts",
            f"checked {len(self.docs)} CDR drug term documents",
        ]
        if refreshes:
            count = len(refreshes)
            tasks.append(f"processed {count} update request(s)")
        if creates:
            count = len(creates)
            tasks.append(f"processed {count} document creation request(s)")
        if len(tasks) > 2:
            # Use the Oxford comma.
            tasks = [
                ", ".join(tasks[:-1]),
                tasks[-1],
            ]
            tasks = ", and ".join(tasks)
        else:
            tasks = " and ".join(tasks)
        message = f"{tasks} in {elapsed}."
        page.form.append(page.B.P(message, page.B.CLASS("footnote")))

    def show_report(self):
        """Everything is shown on the form page."""
        self.show_form()

    @cached_property
    def cdr_names(self):
        """Term names found in CDR drug term documents."""

        cdr_names = {}
        for doc_id in sorted(self.docs):
            doc = self.docs[doc_id]
            if doc.normalized_name not in cdr_names:
                cdr_names[doc.normalized_name] = [doc_id]
            else:
                cdr_names[doc.normalized_name].append(doc_id)
            for name in doc.normalized_other_names:
                if name != doc.normalized_name:
                    if name not in cdr_names:
                        cdr_names[name] = [doc_id]
                    else:
                        cdr_names[name].append(doc_id)
        return cdr_names

    @cached_property
    def codes(self):
        """Map of EVS concept codes to CDR IDs."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Term/NCIThesaurusConcept'")
        rows = query.execute(self.cursor).fetchall()
        codes = {}
        for cdr_id, code in rows:
            code = code.strip().upper()
            if code not in codes:
                codes[code] = []
            codes[code].append(cdr_id)
        return codes

    @cached_property
    def concepts(self):
        """Dictionary of EVS concepts, indexed by concept code."""

        # Load from cache, if available.
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

        # Parse and index the concepts.
        concept_map = {}
        for values in concepts:
            concept = EVSConcept(values)
            concept_map[concept.code] = concept
        return concept_map

    @cached_property
    def concepts_path(self):
        """Location of cached concepts."""

        concepts_path = self.fields.getvalue("concepts")
        if not concepts_path:
            concepts_path = f"d:/tmp/{uuid1()}.json"
        return concepts_path

    @cached_property
    def doc_ids(self):
        """Index of codes by CDR document IDs."""

        doc_ids = {}
        for code in self.codes:
            for doc_id in self.codes[code]:
                if doc_id not in doc_ids:
                    doc_ids[doc_id] = [code]
                else:
                    doc_ids[doc_id].append(code)
        return doc_ids

    @cached_property
    def docs(self):
        """CDR Drug documents, indexed by document ID."""

        start = datetime.now()
        docs = {}
        query = self.Query("query_term", "doc_id").unique()
        query.where("path = '/Term/SemanticType/@cdr:ref'")
        query.where(query.Condition("int_val", self.SEMANTIC_TYPES, "IN"))
        for row in query.execute(self.cursor).fetchall():
            try:
                doc = Doc(self.session, id=row.doc_id)
                docs[row.doc_id] = CDRTerm(doc.id, doc.root)
            except Exception:
                self.logger.exception("parsing CDR%s", row.doc_id)
        args = len(docs), datetime.now() - start
        self.logger.info("fetched %d drug documents in %s", *args)
        return docs

    @cached_property
    def evs_names(self):
        """Unique names from the EVS, mapped to each concept where found."""

        names = {}
        for code in sorted(self.concepts):
            concept = self.concepts[code]
            if concept.normalized_name not in names:
                names[concept.normalized_name] = [code]
            else:
                names[concept.normalized_name].append(code)
            for name in concept.normalized_other_names:
                if name != concept.normalized_name:
                    if name not in names:
                        names[name] = [code]
                    else:
                        names[name].append(code)
        return names

    def __check_match(self, doc_id, concept):
        """See if this pairing of CDR drug term and EVS concept has a problem.

        Pass:
            doc_id - integer for CDR drug term document's unique ID
            concept - object for the matching EVS concept candidate

        Return:
            string describing the problem, if any, else None
        """

        code, name = concept.code, concept.name
        prefix = f"Concept {code} ({name}) matched CDR{doc_id} by name(s), but"
        if doc_id in self.doc_ids:
            codes = ", ".join(self.doc_ids[doc_id])
            problem = f"that document is already associated with {codes}"
            return f"{prefix} {problem}"
        doc = self.docs[doc_id]
        ids = self.cdr_names[doc.normalized_name]
        prefix = f"{prefix} that document's name"
        if len(ids) > 1:
            ids.remove(doc_id)
            ids = ", ".join([f"CDR{id}" for id in ids])
            name = doc.name
            problem = f"({name}) also appears in {ids}"
            return f"{prefix} {problem}"
        codes = self.evs_names.get(doc.normalized_name, [])
        if code in codes:
            codes.remove(code)
        if codes:
            codes = ", ".join(codes)
            name = doc.name
            problem = f"({name}) also appears in {codes}"
            return f"{prefix} {problem}"
        for key in doc.normalized_other_names:
            ids = self.cdr_names[key]
            if len(ids) > 1:
                ids.remove(doc_id)
                ids = ", ".join([f"CDR{id}" for id in ids])
                name = doc.normalized_other_names[key]
                problem = f"({name}) also appears in {ids}"
                return f"{prefix} {problem}"
            codes = self.evs_names.get(key, [])
            if code in codes:
                codes.remove(code)
            if codes:
                codes = ", ".join(codes)
                name = doc.normalized_other_names[key]
                problem = f"({name}) also appears in {codes}"
                return f"{prefix} {problem}"
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

    def __show_updates(self, page, refreshes, creates):
        """Perform and show requested drug term refresh actions.

        Pass:
            page - object on which results are displayed
            refreshes - list of values in the form code-cdrid
            creates - list of concept codes for creating new Term docs
        """

        # Fetch the concepts we've been asked to use, to get fresh values.
        refresh_pairs = [value.split("-") for value in refreshes]
        codes = [row[0] for row in refresh_pairs] + creates
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

        # Start the table for displaying the refreshes performed.
        if refreshes:
            body = page.B.TBODY()
            table = page.B.TABLE(
                page.B.CAPTION("Updates"),
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
            for code, doc_id in refresh_pairs:
                doc_id = int(doc_id)
                if code not in concepts:
                    docs[doc_id] = code
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
                if isinstance(concept, str):
                    # This would be a very rare and odd edge case, in which
                    # the concept was removed from the EVS between the time
                    # the form was displayed and the time the refresh request
                    # was submitted.
                    values = doc_id, concept, "", "Concept not found"
                else:
                    if doc_id in self.failures:
                        note = self.failures[doc_id]
                    elif concept.unavailable:
                        note = "Term document checked out to another user."
                    elif doc_id not in self.successes:
                        note = "CDR document unavailable for update"
                    else:
                        note = "Refreshed from and associated with EVS concept"
                    values = doc_id, concept.code, concept.name, note
                row = page.B.TR()
                for value in values:
                    row.append(page.B.TD(str(value)))
                body.append(row)
            page.form.append(table)

        # Add any new CDR Term documents requested.
        if creates:
            body = page.B.TBODY()
            table = page.B.TABLE(
                page.B.CAPTION("New CDR Drug Term Documents"),
                page.B.THEAD(
                    page.B.TH("Code"),
                    page.B.TH("Name"),
                    page.B.TH("CDR ID"),
                    page.B.TH("Notes"),
                ),
                body
            )
            for code in creates:
                if code not in concepts:
                    # See note on comparable condition in the previous table.
                    values = code, "", "", "Concept not found"
                else:
                    try:
                        concept = concepts[code]
                        xml = concept.xml
                        doc = Doc(self.session, doctype="Term", xml=xml)
                        opts = dict(
                            version=True,
                            publishable=True,
                            val_types=("schema", "links"),
                            unlock=True,
                        )
                        doc.save(**opts)
                        values = code, concept.name, doc.cdr_id, "Created"
                    except Exception as e:
                        self.logger.exception(f"Saving doc for {code}")
                        values = code, concept.name, "", str(e)
                row = page.B.TR()
                for value in values:
                    row.append(page.B.TD(value))
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
    def normalize(cls, text):
        """Lowercase the caller's string value.

        In all cases whitespace has already been normalized.

        Pass:
            text - original value

        Return:
            lowercase version of string
        """

        return text.lower()

    def normalize_space(self, text):
        """Fold Unicode space characters into ASCII space.

        Strips leading and trailing whitespace and collapses sequences
        of contiguous spaces to a single space.

        Pass:
            text - original string

        Return:
            original string with whitespace normalized
        """

        for c in self.FUNKY_WHITESPACE:
            text = text.replace(c, " ")
        return sub(r"\s+", " ", text).strip()

    @cached_property
    def normalized_definitions(self):
        """Sequence of normalized definition strings."""
        return {self.normalize(d) for d in self.definitions}

    @cached_property
    def normalized_name(self):
        """Normalized version of the preferred name."""
        return self.normalize(self.name)

    @cached_property
    def normalized_other_names(self):
        """Dictionary of other names indexed by normalized key."""

        normalized_names = {}
        for other_name in self.other_names:
            if isinstance(other_name, str):
                key = self.normalize(other_name)
            else:
                key = self.normalize(other_name.name)
            if key != self.normalized_name:
                if key not in normalized_names:
                    normalized_names[key] = other_name
        return normalized_names


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
                        definition = sub(r"^NCI\|", "", definition)
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

    @cached_property
    def xml(self):
        """CDR document xml created using this EVS concept's values."""

        root = etree.Element("Term", nsmap=Doc.NSMAP)
        node = etree.SubElement(root, "PreferredName")
        node.text = self.name
        names = set([self.normalized_name])
        for key in sorted(self.normalized_other_names):
            if key not in names:
                names.add(key)
                other_name = self.normalized_other_names[key]
                root.append(other_name.convert(self.code))
        for definition in self.definitions:
            root.append(Updater.make_definition_node(definition))
        term_type = etree.SubElement(root, "TermType")
        etree.SubElement(term_type, "TermTypeName").text = "Index term"
        etree.SubElement(root, "TermStatus").text = "Reviewed-retain"
        code = etree.SubElement(root, "NCIThesaurusConcept", Public="Yes")
        code.text = self.code
        opts = dict(pretty_print=True, encoding="Unicode")
        return etree.tostring(root, **opts)


class OtherName:
    """Synonyms and codes found in an EVS concept record."""

    SKIP = {"PreferredName", "ReviewStatus"}
    TERM_TYPE_MAP = {
        "PT": "Synonym",
        "AB": "Abbreviation",
        "AQ": "Obsolete name",
        "BR": "US brand name",
        "CN": "Code name",
        "FB": "Foreign brand name",
        "SN": "Chemical structure name",
        "SY": "Synonym",
        "INDCode": "IND code",
        "NscCode": "NSC code",
        "CAS_Registry_Name": "CAS Registry name",
        "IND_Code": "IND code",
        "NSC_Code": "NSC code",
        "CAS_Registry": "CAS Registry name"
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

        self.cdr_id = cdr_id
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

        names = set()
        for node in self.root.findall("OtherName/OtherTermName"):
            name = Doc.get_text(node, "").strip()
            if name:
                names.add(self.normalize_space(name))
        return names


class Updater(Job):
    """Global change job used to update CDR term documents from the EVS."""

    LOGNAME = Control.LOGNAME
    COMMENT = f"Term document refreshed from EVS {date.today()}"
    NCIT = "NCI Thesaurus"
    TYPE = "Health professional"
    STRIP = "OtherName", "Definition", "NCIThesaurusConcept"

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
            etree.strip_elements(root, *self.STRIP)

            # Don't duplicate the preferred name in the OtherName blocks.
            names = set([concept.normalized_name])

            # Insert the nodes in reverse order.
            for definition in concept.definitions:
                root.insert(position, self.make_definition_node(definition))
            for key in reversed(sorted(concept.normalized_other_names)):
                if key not in names:
                    names.add(key)
                    other_name = concept.normalized_other_names[key]
                    root.insert(position, other_name.convert(concept.code))

            # Add the concept code.
            position = 0
            for node in root:
                if node.tag in ("Comment", "DateLastModified", "PdqKey"):
                    break
                position += 1
            code_node = etree.Element("NCIThesaurusConcept", Public="Yes")
            code_node.text = concept.code
            root.insert(position, code_node)

            # Record the transformation and return the results.
            self.__control.successes.add(int_id)
            return etree.tostring(root)

        except Exception as e:

            # Record the failure.
            self.logger.exception(f"CDR{int_id}")
            self.__control.failures[int_id] = str(e)

    @classmethod
    def make_definition_node(cls, text):
        """Create the block for the definition being added.

        Pass:
            text - the string for the definition

        Return:
            `_Element` created using the lxml package
        """

        node = etree.Element("Definition")
        etree.SubElement(node, "DefinitionText").text = text
        etree.SubElement(node, "DefinitionType").text = cls.TYPE
        source = etree.SubElement(node, "DefinitionSource")
        etree.SubElement(source, "DefinitionSourceName").text = cls.NCIT
        etree.SubElement(node, "ReviewStatus").text = "Reviewed"
        return node


if __name__ == "__main__":
    """Allow the script to be loaded as a module."""
    Control().run()
