#!/usr/bin/env python

"""Show drug terms which have been removed from the refresh interface.
"""

from collections import defaultdict
from functools import cached_property
from cdrcgi import Controller, SESSION
from nci_thesaurus import EVS


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "Suppressed Drug Terms"
    LOGNAME = "suppressed-drug-terms"
    SUPPRESSED = "unrefreshable_drug_term"
    DELETE = f"DELETE FROM {SUPPRESSED} WHERE id = ?"
    SUBMENU = SUBMIT = None

    def populate_form(self, page):
        """Show terms suppressed from the refresh interface.

        Pass:
            page - HTMLPage object where we communicate with the user
        """

        # Remove a term from the list of suppressed terms.
        if self.id:
            self.cursor.execute(self.DELETE, (self.id,))
            self.conn.commit()

        # Show the suppressed terms.
        fieldset = page.fieldset("Click term to unsuppress")
        page.form.append(fieldset)
        if not self.suppressed:
            fieldset.append(page.B.P("No terms have been suppressed."))
        else:
            fieldset.append(page.B.UL(*self.suppressed))
        page.add_css("fieldset { width: 80%; }")

    @cached_property
    def id(self):
        """ID of term to be removed from the "suppressed" list."""
        return self.fields.getvalue("id")

    @cached_property
    def subtitle(self):
        """What to display under the main banner."""

        if self.id:
            return f"Removed CDR{self.id} from the set of suppressed terms"
        return "Suppressed Drug Terms"

    @cached_property
    def suppressed(self):
        """Sequence of list items containing links."""

        fields = "n.doc_id", "n.value AS name", "c.value AS code"
        query = self.Query("query_term n", *fields)
        query.join(f"{self.SUPPRESSED} s", "s.id = n.doc_id")
        query.join("query_term c", "c.doc_id = n.doc_id")
        query.order("n.value")
        query.where("n.path = '/Term/PreferredName'")
        query.where("c.path = '/Term/NCIThesaurusConcept'")
        terms = []
        B = self.HTMLPage.B
        script = self.script
        rows = []
        codes = []
        for row in query.execute(self.cursor).fetchall():
            rows.append(row)
            codes.append(row.code.strip())
        evs = EVS()
        concepts = evs.fetchmany(codes, include="minimal")
        for row in rows:
            code = row.code.strip()
            if code in concepts:
                name = concepts[code].name or "** unknown **"
            else:
                name = "** concept missing **"
            url = f"{self.script}?{SESSION}={self.session}&id={row.doc_id}"
            display = f"CDR{row.doc_id}: {row.name} (EVS name: {name})"
            terms.append(B.LI(B.A(display, href=url)))
        return terms


if __name__ == "__main__":
    Control().run()
