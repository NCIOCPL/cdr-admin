#!/usr/bin/env python3

"""Show EVS concepts linked by more than one active CDR drug index term.
"""

from datetime import datetime
from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller, HTMLPage
from nci_thesaurus import EVS


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "EVS Drug Concepts Used By More Than One CDR Drug Term"
    LOGNAME = "ambiguous-evs-drug-concepts"

    def show_form(self):
        """Skip the form."""
        self.show_report()

    def show_report(self):
        opts = dict(
            banner=self.title,
            subtitle=self.subtitle,
            body_classes="report",
            buttons=[],
            session=self.session,
            action=self.script,
            control=self,
        )
        page = HTMLPage(self.title, **opts)
        opts = dict(Filter="set:QC Term Set")
        for concept in sorted(self.concepts.values()):
            page.form.append(page.B.H3(f"{concept.name} ({concept.code})"))
            if concept.definitions:
                page.form.append(page.B.P(concept.definitions[0]))
                ul = page.B.UL()
                ids = self.evs.linked_concepts[concept.code]
                docs = [Doc(self.session, id=id) for id in ids]
                for doc in sorted(docs):
                    opts["DocId"] = doc.id
                    url = self.make_url("Filter.py", **opts)
                    link = page.B.A(doc.cdr_id, href=url, target="_blank")
                    ul.append(page.B.LI(f"{doc.title} (", link, ")"))
                page.form.append(ul)
        elapsed = datetime.now() - self.started
        count = len(self.concepts)
        footnote = page.B.P(f"{count} concepts; elapsed: {elapsed}")
        footnote.set("class", "report-footer text-green")
        page.form.append(footnote)
        page.send()

    @cached_property
    def concepts(self):
        """Concepts associated with more than one CDR document."""

        codes = []
        for code, ids in self.evs.linked_concepts.items():
            if len(ids) > 1:
                codes.append(code)
        return self.evs.fetchmany(codes)

    @cached_property
    def evs(self):
        """Access to common EVS utilities."""
        return EVS()


if __name__ == "__main__":
    Control().run()
