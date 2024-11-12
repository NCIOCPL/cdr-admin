#!/usr/bin/env python

"""Show drug terms which have been removed from the refresh interface.
"""

from functools import cached_property
from cdrcgi import Controller
from nci_thesaurus import EVS


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "Suppressed Drug Terms"
    LOGNAME = "suppressed-drug-terms"
    SUPPRESSED = "unrefreshable_drug_term"
    DELETE = f"DELETE FROM {SUPPRESSED} WHERE id = ?"
    SUBMIT = None

    def populate_form(self, page):
        """Show terms suppressed from the refresh interface.

        Pass:
            page - HTMLPage object where we communicate with the user
        """

        # Remove a term from the list of suppressed terms.
        if self.id:
            try:
                self.cursor.execute(self.DELETE, (self.id,))
                self.conn.commit()
                message = (
                    f"Removed CDR{self.id} from the set of suppressed "
                    "terms."
                )
                self.alerts.append(dict(message=message, type="success"))
            except Exception as e:
                self.logger.exception("removing %s", self.id)
                message = f"Failure unsuppressing CDR{self.id}: {e}"
                self.alerts.append(dict(message=message, type="error"))

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
            session = f"{self.SESSION}={self.session}"
            url = f"{self.script}?{session}&id={row.doc_id}"
            display = f"CDR{row.doc_id}: {row.name} (EVS name: {name})"
            terms.append(B.LI(B.A(display, href=url)))
        return terms


if __name__ == "__main__":
    Control().run()
