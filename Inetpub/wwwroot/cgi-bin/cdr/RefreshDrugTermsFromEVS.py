#!/usr/bin/env python

"""Show drug terms which differ from their EVS counterparts.

Provides a form with checkboxes to select drug terms to be refreshed from
the EVS.
"""

from collections import defaultdict
from datetime import datetime
from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller
from nci_thesaurus import EVS, Normalizer, Term


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "Drug Term Refresh"
    LOGNAME = "updates-from-evs"
    CSS = "../../stylesheets/RefreshDrugTermsFromEVS.css"
    SORT_BY_NAME = "Sort By Name"
    SORT_BY_ID = "Sort By CDR ID"
    SUPPRESSED = "unrefreshable_drug_term"
    SUPPRESS = f"INSERT INTO {SUPPRESSED} (id) VALUES (?)"

    def populate_form(self, page):
        """Show terms differing from the EVS.

        If any refresh requests were specified, perform them and show the
        results above the form.

        Pass:
            page - HTMLPage object where we communicate with the user
        """

        # Suppress any drug terms we've been asked to remove from the page.
        suppress = self.fields.getlist("suppress")
        if suppress:
            for doc_id in suppress:
                self.logger.info("%s: %r", self.SUPPRESS, doc_id)
                try:
                    self.cursor.execute(self.SUPPRESS, (doc_id,))
                except Exception:
                    self.logger.exception("suppressing CDR%d", doc_id)
            self.logger.info("committing suppressions")
            self.conn.commit()
            self.logger.info("committed suppressions")

        # Perform and report any requested updates from the EVS.
        actions = self.fields.getlist("actions")
        if actions:
            self.logger.info("actions: %r", actions)
            EVS.show_updates(self, page, actions)
            self.logger.info("actions applied")

        # Remember settings which should be carried forward.
        page.form.append(page.hidden_field("concepts", self.concepts_path))
        page.form.append(page.hidden_field("sort", self.sort))

        # Start building the form.
        start = datetime.now()
        page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))
        body = page.B.TBODY()

        # Check each of the EVS concepts for deltas with the CDR documents.
        terms = 0
        if self.sort == "name":
            concepts = sorted(self.concepts.values())
        else:
            doc_ids = defaultdict(list)
            for concept in self.concepts.values():
                doc_id = self.codes.get(concept.code)
                if doc_id:
                    doc_ids[doc_id].append(concept)
            concepts = []
            for doc_id in sorted(doc_ids):
                if len(doc_ids[doc_id]) == 1:
                    concepts.append(doc_ids[doc_id][0])
        for concept in concepts:
            doc = self.__doc_for_code(concept.code)
            if not doc or doc.cdr_id in self.suppressed:
                continue
            if not concept.differs_from(doc):
                continue
            terms += 1
            code = concept.code
            name = concept.name
            label = f"Refresh CDR{doc.cdr_id} from {code} ({name})"
            value = f"{code}-{doc.cdr_id}"
            opts = dict(value=value, label=label)
            refresh = page.checkbox("actions", **opts)
            opts = dict(value=doc.cdr_id, label=f"Suppress CDR{doc.cdr_id}")
            suppress = page.checkbox("suppress", **opts)
            body.append(
                page.B.TR(
                    page.B.TH(suppress, refresh, colspan="3"),
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
            if concept.other_names_differ(doc):
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
                    new_def = self.evs.show_changes(page.B, old_def, new_def)
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

    def run(self):
        """Allow the user to change the sort order."""
        if self.request == self.SORT_BY_ID:
            self.redirect(self.script, sort="id", concepts=self.concepts_path)
        elif self.request == self.SORT_BY_NAME:
            self.redirect(self.script, sort="name", concepts=self.concepts_path)
        else:
            Controller.run(self)

    def show_report(self):
        """Everything is shown on the form page."""
        self.show_form()

    @cached_property
    def buttons(self):
        """Custom list of action buttons."""

        standard = [self.SUBMIT, self.SUBMENU, self.ADMINMENU, self.LOG_OUT]
        if self.sort == "id":
            buttons = [self.SORT_BY_NAME]
        else:
            buttons = [self.SORT_BY_ID]
        return buttons + standard

    @cached_property
    def codes(self):
        """Map of EVS concept codes to CDR IDs."""

        codes = {}
        for code, ids in self.evs.linked_concepts.items():
            if len(ids) == 1:
                codes[code] = ids[0]
        return codes

    @cached_property
    def concepts(self):
        """Dictionary of EVS concepts, indexed by concept code."""

        # Load concept values from JSON cache, if available.
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
    def evs(self):
        """Access to common EVS utilities."""
        return EVS()

    @cached_property
    def sort(self):
        """How will the terms be sorted?"""
        return "id" if self.fields.getvalue("sort") == "id" else "name"

    @cached_property
    def suppressed(self):
        """Drug terms which the users don't want to see.

        Handle the case in which the table hasn't been created yet.
        """

        query = self.Query(self.SUPPRESSED, "id")
        try:
            return {row.id for row in query.execute(self.cursor).fetchall()}
        except Exception:
            self.cursor.execute(f"CREATE TABLE {self.SUPPRESSED} "
                                "(id INTEGER PRIMARY KEY)")
            self.cursor.execute(f"ALTER TABLE {self.SUPPRESSED} "
                                "ADD FOREIGN KEY(id) REFERENCES all_docs")
            self.cursor.execute(f"GRANT SELECT ON {self.SUPPRESSED} "
                                "TO CdrGuest")
            self.conn.commit()
            return set()

    def __doc_for_code(self, code):
        """Fetch the CDR document matching the caller's EVS concept code.

        Pass:
            code - string for the EVS concept code

        Return:
            `nci_thesaurus.Term` object if found, else `None`
        """

        if code in self.codes:
            doc_id = self.codes[code]
            try:
                doc = Doc(self.session, id=doc_id)
                return Term(doc.id, doc.root)
            except Exception:
                self.logger.exception("fetching CDR%s for %s", doc_id, code)
        return None


if __name__ == "__main__":
    Control().run()
