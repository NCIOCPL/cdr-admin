#!/usr/bin/env python

"""Menu for the tools used to use EVS concepts for CDR drug Term documents.

This separate intermediate page serves two purposes.

   1. It explains what the tools do, and their relationship to each other.
   2. It warns the user that it takes a while to load each of the forms.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "EVS Concept Tools"
    INSTRUCTIONS = (
        "There are several tools available for managing the CDR Term "
        "documents for drugs using concepts from the NCI Thesaurus, now "
        "generally referred to as the Enterprise Vocabulary System (EVS).",
        "The first of these utilities finds CDR Term documents for drugs "
        "which are linked unambiguously to a single EVS concept, and which "
        "differ in the names and/or the definitions used by the "
        "two systems. For each such term the differences are displayed "
        "side-by-side with highlighting. Each term has a checkbox which can "
        "be used to mark the CDR Term document to be refreshed from the "
        "values in the EVS. A second checkbox is available for each term "
        "to suppress its appearance on this report. When you have finished "
        "queueing up the actions which should be performed you can click "
        "the Submit button to apply those queued actions. The form is long "
        "so you can use the Home key to return to the top of the page after "
        "queuing the desired actions. You can also submit the queued actions "
        "by pressing the Return (or Enter) key, as long as one of the radio "
        "button fields has the focus (which will be true immediately after "
        "you have clicked on any of the radio buttons). After the actions "
        "have been processed, the form will be re-drawn, with a report at "
        "the top of the page showing the details of what was done.",
        "It takes a while (typically over a minute) when the form is first "
        "loaded. When the form is redrawn after processing the requested "
        "actions, a cache of the EVS concepts which were loaded with the "
        "initial display of the form is used, and the delay before the form "
        "is refreshed will be significantly shorter.",
        "The second tool is used for drug term concepts in the EVS which are "
        "not linked by CDR Term documents. Two tables appear for this form, "
        "with the first showing EVS drug concepts each of which matches "
        "exactly one CDR Term document by name, but that CDR document does "
        "not yet have any link to an EVS concept. Each such concept has "
        "a checkbox for queuing the generation of such a link, combined "
        "with a refresh of the values in the CDR document using the values "
        "found in the matching EVS concept. A second table appears on this "
        "form identifying EVS drug concepts for which no matching CDR Term "
        "document was found. Each of those concepts has a checkbox to "
        "queue the concept to be imported as a new CDR Term document. "
        "Below these two tables, all of the problems found during the "
        "analysis of the EVS drug concepts and the CDR drug Term documents "
        "are displayed, "
        "with sufficient details about each problem to enable a user to "
        "decide how the problem should be resolved. Submitting the queued "
        "requests works the same way as for the first utility, and you "
        "can also expect to have to wait a bit for the initial drawing of "
        "the form, which involves analysis of thousands of EVS concepts and "
        "CDR Term documents. As with the first tool, subsequent redrawing "
        "of the form is sped up by using the cache of EVS concepts created "
        "when the form was first drawn.",
        "The third tool is a report of EVS concepts which were found to be "
        "linked by two or more CDR Term documents. Use this report to examine "
        "the CDR documents and determine how to resolve the ambiguities, so "
        "that the first tool can be used for refreshing those documents."
    )
    UTILITIES = (
        (
            "Refresh CDR Drug Term Documents With EVS Concepts",
            "RefreshDrugTermsFromEVS.py",
        ),
        (
            "Match CDR Terms to EVS Concepts By Name",
            "MatchDrugTermsByName.py",
        ),
        (
            "EVS concepts used by more than one CDR Drug Term",
            "AmbiguousEVSDrugConcepts.py",
        ),
    )

    def populate_form(self, page):
        """Explain how the tools work.

        Required positional argument:
          page - instance of the cdrcgi.HTMLPage class
        """

        accordion = page.accordion("instructions")
        for paragraph in self.INSTRUCTIONS:
            accordion.payload.append(page.B.P(paragraph))
        page.form.append(accordion.wrapper)
        fieldset = page.fieldset("Choose EVS Utility")
        utilities = page.B.UL(id="utilities")
        for label, script in self.UTILITIES:
            link = page.menu_link(script, label)
            link.set("target", "_blank")
            utilities.append(page.B.LI(link))
        fieldset.append(utilities)
        page.form.append(fieldset)
        color = f"color: {page.LINK_COLOR};"
        page.add_css(
            "#utilities { list-style: none; }\n"
            ".usa-form #utilities a { text-decoration: none; }\n"
            f".usa-form #utilities a:visited {{ {color} }}\n"
            ".usa-form #utilities li { margin-bottom: .5rem; }\n"
            ".usa-accordion { margin-bottom: 2rem; }\n"
        )

    @cached_property
    def buttons(self):
        """No buttons needed on this form."""
        return []


if __name__ == "__main__":
    Control().run()
