#!/usr/bin/env python
"""JSON API for fetching information from glossary term documents.
"""

from collections import defaultdict
from functools import cached_property
from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-glossary-terms API service"
    LOGNAME = "testing"

    def run(self):
        """Overridden because this is not a standard report."""

        self.logger.info("loaded %d terms", len(self.terms))
        terms = dumps(self.terms, indent=2)
        self.send_page(terms, mime_type="application/json")

    @cached_property
    def terms(self):
        """Sequence of value dictionaries for glossary terms."""

        # Get the most frequently linked terms first.
        terms = []
        done = set()
        for id in self.terms_sorted_by_link_frequency:
            term = dict(
                id=id,
                english_name=self.english_names.get(id),
                spanish_names=self.spanish_names.get(id),
                concept_id=self.concept_ids.get(id),
            )
            terms.append(term)
            done.add(id)
            if self.limit and len(terms) >= self.limit:
                return terms

        # If we still need more, fill in with the rest in ID order.
        query = self.Query("document d", "d.id")
        query.join("pub_proc_cg c", "c.id = d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'GlossaryTermName'")
        query.order(1).unique()
        for row in query.execute(self.cursor).fetchall():
            id = row.id
            if id in done:
                continue
            term = dict(
                id=id,
                english_name=self.english_names.get(id),
                spanish_names=self.spanish_names.get(id),
                concept_id=self.concept_ids.get(id),
            )
            terms.append(term)
            if self.limit and len(terms) >= self.limit:
                return terms
        return terms

    @cached_property
    def concept_ids(self):
        """Map of GTC IDs indexed by GTN IDs."""

        query = self.Query("query_term", "doc_id", "int_val")
        query.where("path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'")
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def english_names(self):
        """Map of GTN IDs to English name strings."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/GlossaryTermName/TermName/TermNameString'")
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def limit(self):
        """Optional throttle on the number of drugs to return."""
        return int(self.fields.getvalue("limit", "0"))

    @cached_property
    def terms_sorted_by_link_frequency(self):
        """Sequence of GTN IDs, most frequently linked first."""

        subquery = self.Query("document d", "d.id")
        subquery.join("doc_type t", "t.id = d.doc_type")
        subquery.join("pub_proc_cg c", "c.id = d.id")
        subquery.where("t.name = 'GlossaryTermName'")
        query = self.Query("query_term", "int_val", "COUNT(*)")
        query.where(query.Condition("int_val", subquery, "IN"))
        query.where("path LIKE '%/@cdr:%ref'")
        query.group("int_val")
        query.order("2 DESC")
        query.log()
        return [row.int_val for row in query.execute(self.cursor).fetchall()]

    @cached_property
    def spanish_names(self):
        """Map of GTN IDs to lists of Spanish name strings."""

        fields = "n.doc_id", "n.value", "a.value"
        tn_path = "/GlossaryTermName/TranslatedName"
        query = self.Query("query_term n", *fields)
        query.where(f"n.path = '{tn_path}/TermNameString'")
        query.join("query_term s", "s.doc_id = n.doc_id")
        query.where(f"s.path = '{tn_path}/TranslatedNameStatus'")
        query.where("s.value = 'Approved'")
        query.where("LEFT(s.node_loc, 4) = LEFT(n.node_loc, 4)")
        outer_join_conditions = (
            "a.doc_id = n.doc_id",
            "LEFT(a.node_loc, 4) = LEFT(n.node_loc, 4)",
            f"a.path = '{tn_path}/@NameType'",
        )
        query.outer("query_term a", *outer_join_conditions)
        query.log()
        names = defaultdict(list)
        for id, name, type in query.execute(self.cursor).fetchall():
            alternate = True if type == "alternate" else False
            values = dict(
                name=name,
                alternate=alternate
            )
            names[id].append(values)
        return names


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        message = "failure getting glossary terms"
        control.logger.exception(message)
        control.send_page(f"{message}: {e}", text_type="plain")
