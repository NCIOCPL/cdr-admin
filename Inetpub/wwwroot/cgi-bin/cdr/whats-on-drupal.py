#!/usr/bin/env python

"""Show which Summaries (DIS & CIS) are on the Drupal CMS
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc
from cdrapi.publishing import DrupalClient


class Control(Controller):

    SUBTITLE = "PDQ Summaries on Drupal"
    COLUMNS = "CDR ID", "Title", "Type", "Language"

    def build_tables(self):
        """Populate a table with the CMS summaries the Drupal server has."""

        rows = [doc.row for doc in self.docs]
        return self.Reporter.Table(rows, columns=self.COLUMNS)

    def populate_form(self, page):
        """Let the user choose another Drupal server.

        Pass:
            page - HTMLPage object where the field goes.
        """

        fieldset = page.fieldset("Drupal Server")
        opts = dict(label="Server", value=self.host)
        fieldset.append(page.text_field("host", **opts))
        page.form.append(fieldset)
        page.add_output_options(default="html")

    @cached_property
    def docs(self):
        """PDQ Summary documents on the Drupal host."""

        client = DrupalClient(self.session, base=f"https://{self.host}")
        return [self.Summary(self, doc) for doc in client.list()]

    @cached_property
    def host(self):
        """Drupal host to query."""

        default = self.session.tier.hosts.get("DRUPAL")
        return self.fields.getvalue("host") or default

    class Summary:
        """PDQ summary document for the report."""

        def __init__(self, control, doc):
            """Remember the caller's values.

            Pass:
                control - access to the current session
                doc - item from the Drupal catalog
            """

            self.__control = control
            self.__doc = doc

        @cached_property
        def row(self):
            """Table row for the report."""
            return self.id, self.title, self.type, self.language

        @cached_property
        def id(self):
            """CDR document ID for the summary."""
            return f"CDR{self.__doc.cdr_id:d}"

        @cached_property
        def title(self):
            """Short title for the PDQ summary document."""

            doc = Doc(self.__control.session, id=self.__doc.cdr_id)
            if not doc.title:
                Cell = self.__control.Reporter.Cell
                title = "[NO TITLE FOUND -- POSSIBLY FROM ANOTHER TIER?]"
                return Cell(title, classes="error")
            return doc.title.split(";")[0].strip()

        @cached_property
        def type(self):
            """DIS or CIS (for Drug|Cancer Information Summary)."""
            return "DIS" if "drug" in self.__doc.type else "CIS"

        @cached_property
        def language(self):
            """English or Spanish."""
            return "English" if self.__doc.langcode == "en" else "Spanish"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
