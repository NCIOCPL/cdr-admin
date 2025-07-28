#!/usr/bin/env python

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

from datetime import datetime
from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller, BasicWebPage
from cdrcgi import FormFieldFactory as Factory
from nci_thesaurus import EVS, Normalizer, Term


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "Match Drug Terms By Name"
    LOGNAME = "updates-from-evs"
    CSS = "../../stylesheets/RefreshDrugTermsFromEVS.css"
    LOAD_FORM = "Load Form"
    CSS = (
        "table { width: 100%; margin-top: 2rem; }",
        "caption { margin-bottom: 1rem; font-size: 1.2em; }",
        "thead th { font-size: 1.1em; }",
        ".cb-row th, caption { text-align: left; }",
        ".cb-row th { border-left: none; border-right: none; }",
        ".cb-row th { padding: 2rem 0 1rem; }",
        ".footnote { font-size: .9em; font-style: italic; color: green; }",
        ".usa-button { margin-top: 2rem; }",
    )

    def populate_form(self, page):
        """Show terms differing from the EVS.

        If any refresh requests were specified, perform them and show the
        results above the form.

        Pass:
            page - HTMLPage object where we communicate with the user
        """

        # Perform and report any requested updates from the EVS.
        start = datetime.now()
        page = BasicWebPage()
        url = "/uswds/css/uswds.min.css"
        page.head.append(page.B.LINK(href=url, rel="stylesheet"))
        page.head.append(page.B.STYLE("\n".join(self.CSS)))
        page.wrapper.append(page.B.H1(self.SUBTITLE))
        refreshes = self.fields.getlist("refreshes")
        creates = self.fields.getlist("creates")
        if refreshes or creates:
            EVS.show_updates(self, page, refreshes, creates)

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
            if len(doc_ids) > 1:
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

        # Start building the form.
        form = page.B.FORM(method="POST", action=self.script)
        page.wrapper.append(form)
        form.append(Factory.hidden_field(self.SESSION, self.session))
        form.append(Factory.hidden_field("concepts", self.concepts_path))
        form.append(Factory.button(self.SUBMIT))

        # Create a table showing matches we have found.
        tbody = page.B.TBODY()
        for code, doc_id in matched:
            ok_docs.add(doc_id)
            concept = self.concepts[code]
            doc = self.docs[doc_id]
            name = concept.name
            label = f"Match and refresh CDR{doc.cdr_id} from {code} ({name})"
            value = f"{code}-{doc_id}"
            opts = dict(value=value, label=label)
            checkbox = Factory.checkbox("refreshes", **opts)
            tbody.append(
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
            tbody.append(row)
            c_names = set(concept.normalized_other_names)
            d_names = set(doc.normalized_other_names)
            concept_list = page.B.UL()
            for other_name in sorted(concept.other_names):
                if Normalizer.normalize(other_name.name) not in d_names:
                    name = page.B.B(other_name.name)
                else:
                    name = other_name.name
                concept_list.append(page.B.LI(name))
            doc_list = page.B.UL()
            for other_name in sorted(doc.other_names):
                if Normalizer.normalize(other_name.name) not in c_names:
                    doc_list.append(page.B.LI(page.B.B(other_name.name)))
                else:
                    doc_list.append(page.B.LI(other_name.name))
            row = page.B.TR(
                page.B.TH("Other Name(s)"),
                page.B.TD(doc_list),
                page.B.TD(concept_list),
            )
            tbody.append(row)
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
                new_def = self.evs.show_changes(page.B, old_def, new_def)
            row = page.B.TR(
                page.B.TH("Definition"),
                page.B.TD(old_def),
                page.B.TD(new_def),
            )
            tbody.append(row)

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
            tbody
        )
        form.append(table)

        # Create another table for concepts which have no CDR matches.
        tbody = page.B.TBODY()
        concepts = []
        for code in unmatched:
            concepts.append(self.concepts[code])
        for concept in sorted(concepts):
            label = f"Import concept {concept.code} ({concept.name})"
            opts = dict(value=concept.code, label=label)
            checkbox = Factory.checkbox("creates", **opts)
            form.append(checkbox)
            tbody.append(
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
            tbody.append(row)
            for definition in concept.definitions:
                row = page.B.TR(
                    page.B.TH("Definition"),
                    page.B.TD(definition),
                )
                tbody.append(row)
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
            tbody
        )
        form.append(table)

        # Show the concepts with problems.
        count = len(problems)
        h2 = page.B.H2(f"Concepts Unable To Be Matched Or Imported ({count})")
        page.wrapper.append(h2)
        problem_list = page.B.UL()
        for problem in problems:
            problem_list.append(page.B.LI(problem))
        page.wrapper.append(problem_list)

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
        page.wrapper.append(h2)
        page.wrapper.append(page.B.UL(*problems))
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
        elapsed = datetime.now() - start
        message = f"{tasks} in {elapsed}."
        page.wrapper.append(page.B.P(message, page.B.CLASS("footnote")))
        page.send()

    def show_report(self):
        """Everything is shown on the form page."""
        self.show_form()

    @cached_property
    def buttons(self):
        """Customized button handling."""
        return []

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
        path = self.fields.getvalue("concepts")
        if path:
            return self.evs.load_from_cache(path, self.logger)

        # Otherwise, fetch the concepts from the EVS and cache them.
        return self.evs.load_drug_concepts(self.concepts_path, self.logger)

    @cached_property
    def concepts_path(self):
        """Location of cached concepts."""

        concepts_path = self.fields.getvalue("concepts")
        if not concepts_path:
            return self.evs.cache_path
        return concepts_path

    @cached_property
    def doc_ids(self):
        """Index of codes by CDR document IDs."""

        doc_ids = {}
        for code, ids in self.codes.items():
            for doc_id in ids:
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
        for doc_id in self.evs.drug_doc_ids:
            try:
                doc = Doc(self.session, id=doc_id)
                docs[doc_id] = Term(doc.id, doc.root)
            except Exception:
                self.logger.exception("parsing CDR%s", doc_id)
        args = len(docs), datetime.now() - start
        self.logger.info("fetched %d drug documents in %s", *args)
        return docs

    @cached_property
    def evs(self):
        """Access to common EVS utilities."""
        return EVS()

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
                name = doc.normalized_other_names[key].name
                problem = f"({name}) also appears in {ids}"
                return f"{prefix} {problem}"
            codes = self.evs_names.get(key, [])
            if code in codes:
                codes.remove(code)
            if codes:
                codes = ", ".join(codes)
                name = doc.normalized_other_names[key].name
                problem = f"({name}) also appears in {codes}"
                return f"{prefix} {problem}"
        return None


if __name__ == "__main__":
    Control().run()
