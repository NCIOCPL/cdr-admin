#!/usr/bin/env python

"""Report on abandoned documents.
"""

from cdrcgi import Controller
from cdrapi.reports import Report


class Control(Controller):

    SUBTITLE = "Checked Out Documents With No Activity"
    REPORT = "Inactive Checked Out Documents"
    COLUMNS = (
        "Document ID",
        "Type",
        "User",
        "Checked Out",
        "Last Action",
        "Action Date",
    )

    def populate_form(self, page):
        """Add the sole field to the form for the number of days."""

        fieldset = page.fieldset("Inactivity Threshold (up to 99 days)")
        fieldset.append(page.text_field("days", value=10))
        page.form.append(fieldset)

    def build_tables(self):
        """Return the single table for this report."""

        if not self.days:
            self.show_form()
        opts = dict(columns=self.COLUMNS, caption="Inactive Documents")
        return self.Reporter.Table(self.rows, **opts)

    def show_report(self):
        """Override to add a style rule."""

        self.report.page.add_css("table { width: 75%; }")
        self.report.send()

    @property
    def days(self):
        """Threshold in days for the inactivity report."""

        if not hasattr(self, "_days"):
            self._days = self.fields.getvalue("days")
            if self._days:
                try:
                    self._days = int(self._days)
                except:
                    self.bail("Days must be an integer")
                if not 0 < self._days < 100:
                    self.bail("Days must be between 1 and 99")
        return self._days

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            parms = dict(InactivityLength=f"0000-00-{self.days:02d}")
            root = Report(self.session, self.REPORT, **parms).run()
            for node in root.findall("ReportRow"):
                row = self.Row(node)
                self._rows.append([
                    self.Reporter.Cell(row.id, center=True),
                    row.type,
                    row.user,
                    self.Reporter.Cell(str(row.locked)[:19], center=True),
                    row.action,
                    self.Reporter.Cell(str(row.when)[:19], center=True),
                ])
        return self._rows

    @property
    def subtitle(self):
        """Customize the string under the banner for the report page."""

        subtitle = self.SUBTITLE
        if self.request == self.SUBMIT:
            subtitle += f" for Longer Than {self.days} Days"
        return subtitle

    class Row:
        """Information for one row in the report."""

        def __init__(self, node):
            """Save the node for unpacking.

            Pass:
                node - one ReportRow element from the report object
            """

            self.__node = node

        @property
        def id(self):
            """The CDR document ID."""
            return self.__node.find("DocId").text

        @property
        def type(self):
            """The type of the CDR document."""
            return self.__node.find("DocType").text

        @property
        def user(self):
            """The CDR user to whom the document is checked out."""
            return self.__node.find("CheckedOutTo").text

        @property
        def locked(self):
            """When The CDR document was checked out."""
            return self.__node.find("WhenCheckedOut").text

        @property
        def action(self):
            """The last action performed on the CDR document."""
            return self.__node.find("LastActivity/ActionType").text

        @property
        def when(self):
            """The when last action was performed on the CDR document."""
            return self.__node.find("LastActivity/ActionWhen").text


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
