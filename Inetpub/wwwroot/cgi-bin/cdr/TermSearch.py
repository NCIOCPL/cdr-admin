#!/usr/bin/env python

"""Search for CDR Term documents.
"""

from cdr import unlock
from cdrcgi import AdvancedSearch, bail
from cdrapi.docs import Doc
from nci_thesaurus import Concept

class TermSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Term"
    SUBTITLE = DOCTYPE
    FILTER = "set:QC Term Set"
    NCIT = "https://nciterms.nci.nih.gov"
    PATHS = dict(
        name="/Term/PreferredName",
        other_name="/Term/OtherName/OtherTermName",
        term_type="/Term/TermType/TermTypeName",
        sem_type="/Term/SemanticType/@cdr:ref",
    )

    # Add some javascript to monitor the import/update fields.
    IMP_BTN = "term-import-button"
    JS = """\
function chk_cdrid() {
    if (jQuery("#cdrid").val().replace(/\D/g, "").length === 0)
        jQuery("#term-import-button input").val("Import");
    else
        jQuery("#term-import-button input").val("Update");
}
function chk_code() {
    if (jQuery("#code").val().trim().length === 0)
        jQuery("#term-import-button input").prop("disabled", true);
    else
        jQuery("#term-import-button input").prop("disabled", false);
}
$(function() { chk_cdrid(); chk_code(); });
"""

    def __init__(self):
        """Set the stage for showing the search form or the search results."""

        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        self.changes = None
        if self.term_type and self.term_type not in self.term_types:
            raise Exception("Tampering with form values")
        if self.sem_type:
            if self.sem_type not in [st[0] for st in self.semantic_types]:
                raise Exception("Tampering with form values")
        self.search_fields = (
            self.text_field("name"),
            self.text_field("other_name"),
            self.select("term_type", options=[""]+self.term_types),
            self.select("sem_type", options=[""]+self.semantic_types),
        )
        self.query_fields = []
        for name, path in self.PATHS.items():
            field = self.QueryField(getattr(self, name), [path])
            self.query_fields.append(field)

    def run(self):
        """Override the run() method of the base class.

        We need to handle requests to import or update PubMed
        articles from NLM.
        """

        if self.request in ("Import", "Update"):
            try:
                term = Term(self)
                term.save()
                self.changes = term.changes
                self.show_form(term.message)
            except Exception as e:
                self.session.logger.exception("%s from NCIT", self.request)
                error = f"Unable to import {self.code!r} from NCIT: {e}"
                bail(error)
        else:
            AdvancedSearch.run(self)

    def customize_form(self, page):
        """Add a button for browsing the NCI Thesaurus.

        If the user has sufficient permissions, also add fields for
        importing a new thesaurus concept or updating one we have imported
        in the past.
        """

        ncit = f"window.open('{self.NCIT}', 'ncit');"
        buttons = page.body.xpath("//*[@id='header-buttons']")
        buttons[0].append(self.button("Search NCI Thesaurus", onclick=ncit))
        if self.session.can_do("ADD DOCUMENT", "Term"):
            self.add_import_form(page)
        if self.changes:
            self.show_changes(page)

    def show_changes(self, page):
        """Add another box listing the changes made when we updated.

        Show name changes first, then definition changes.
        """

        ul = self.B.UL(id="ncit-changes")
        for change in self.changes:
            if "definition" not in change.lower():
                ul.append(self.B.LI(change))
        for change in self.changes:
            if "definition" in change.lower():
                ul.append(self.B.LI(change))
        box = self.fieldset("Changes")
        box.append(ul)
        page.form.append(box)

    def add_import_form(self, page):
        """Add another fieldset with fields for importing an NCIT concept."""

        # Create the fields and the button.
        help = "Optionally enter the CDR ID of a document to be updated."
        cdrid_field = self.text_field("cdrid", label="CDR ID", tooltip=help)
        cdrid_field.set("oninput", "chk_cdrid()")
        code_field = self.text_field("code")
        code_field.set("oninput", "chk_code()")
        button = self.button("Import")
        button.set("disabled")

        # Wrap them in a fieldset and plug in script for updating the button.
        fieldset = self.fieldset("Import or Update a Concept From NCIT")
        fieldset.append(code_field)
        fieldset.append(cdrid_field)
        fieldset.append(self.B.DIV(button, id=self.IMP_BTN))
        page.form.append(fieldset)
        page.head.append(self.B.SCRIPT(self.JS))

    @property
    def cdrid(self):
        """ID of an existing Term document to be updated."""
        cdrid = self.fields.getvalue("cdrid")
        return Doc.extract_id(cdrid) if cdrid else None

    @property
    def code(self):
        """Unique code of an NCI Thesaurus concept to be imported."""
        return self.fields.getvalue("code", "").strip()

    @property
    def semantic_types(self):
        """Valid values for the semantic types piclist."""

        fields = "d.id", "d.title"
        query = self.DBQuery("document d", *fields).unique().order("d.title")
        query.join("query_term t", "t.int_val = d.id")
        query.where(query.Condition("t.path", self.PATHS["sem_type"]))
        rows = query.execute(self.session.cursor).fetchall()
        return [(f"CDR{row.id:010d}", row.title) for row in rows]

    @property
    def term_types(self):
        """Valid values for the term types picklist."""
        return self.values_for_paths([self.PATHS["term_type"]])


class Term:
    """Logic for assembling and saving a new or updated Term document."""

    UPDATE_OPTS = dict(skip_other_name=False, skip_definitions=False)

    def __init__(self, control):
        """Save the caller's object referencd.

        Most of the work is done while assembling this object's properties.
        """

        self.__control = control
        self.changes = self.message = None

    def save(self):
        """Save the new or updated Term document.

        The `Concept` object takes care of making sure the document
        gets unlocked if exceptions are raised.

        We save the message string to be displayed in the sub-banner
        to let the user know the outcome of the request. We also
        capture the list of changes made to the concept for an update
        of an existing Term doc.
        """

        # Update the document if we have already imported the concept.
        if self.cdrid:
            opts = self.UPDATE_OPTS
            args = self.session, self.cdrid
            self.changes = self.concept.update(*args, **opts)
            if self.changes:
                self.message = "New version created"
            else:
                self.message = "No changes found to save"

        # Otherwise, create a new Term document.
        else:
            self.message = self.concept.add(self.session)

    @property
    def concept(self):
        """Load the concept document from NCI Thesaurus service."""

        if not hasattr(self, "_concept"):
            try:
                self._concept = Concept(code=self.code)
            except Exception as e:
                self.logger.exception("unable to load %r", self.code)
                bail(f"Failure importing concept from NCI Thesaurus: {e}")
        return self._concept

    @property
    def session(self):
        """CDR login session object"""
        return self.__control.session

    @property
    def cdrid(self):
        """ID of an existing Term document to be updated."""
        return self.__control.cdrid

    @property
    def code(self):
        """Unique code of an NCI Thesaurus concept to be imported."""
        return self.__control.code

    @property
    def logger(self):
        """Access to session logging."""
        return self.__control.session.logger


if __name__ == "__main__":
    TermSearch().run()
