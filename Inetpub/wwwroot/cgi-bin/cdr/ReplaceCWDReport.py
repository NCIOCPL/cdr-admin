#!/usr/bin/env python

"""Show documents for which the CWD was replaced by an earlier version.
"""

from functools import cached_property
from cdrcgi import Controller, BasicWebPage


class Control(Controller):
    """Access to the database and report generation tools."""

    SUBTITLE = "Report CWD Replacements"
    SOURCE = "CWDReplacements.log"
    COLUMNS = (
        ("Date/time", "When did the replacement occur?"),
        ("DocID", "CDR ID of the affected document"),
        ("Doc type", "Document type for the affected document"),
        ("User", "ID of the user promoting the version"),
        ("LV", "Version number of last version after promotion"),
        ("PV",
         "Version number of last publishable version at that time, -1 = None"),
        ("Chg", "'Y' = CWD was different from last version, else 'N'"),
        ("V#", "Version number promoted to become CWD"),
        ("V", "Was new CWD also versioned? (Y/N)"),
        ("P", "Was new CWD also versioned as publishable? (Y/N)"),
        ("Comment", "System-generated comment ':' user-entered comment"),
    )
    INSTRUCTIONS = (
        "Retrieve information on documents for which someone has replaced "
        "the current working document (CWD) with an older version. "
        "Fill in the form to select only those replacements meeting the "
        "criteria given in the parameter values.  All parameters are "
        "optional.  If all are blank, all replacements will be reported "
        "for which we have logged information."
    )

    def populate_form(self, page):
        """Ask the user for the report parameters.

        Pass:
            page - HTMLPage object where the fields go
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Parameters")
        fieldset.append(page.date_field("start", label="Earliest Date"))
        fieldset.append(page.text_field("user", label="User ID"))
        fieldset.append(page.text_field("doctype", label="Doc Type"))
        fieldset.append(page.text_field("id", label="CDR ID"))
        page.form.append(fieldset)

    def show_report(self):
        """Overridden because the table is too wide for the standard layout."""

        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.subtitle))
        report.wrapper.append(self.table.node)
        report.wrapper.append(self.footer)
        report.page.head.append(report.B.STYLE("table { width: 100%; }"))
        report.send()

    @cached_property
    def caption(self):
        """String to be display directly above the report table."""
        return f"Document Replacements ({len(self.rows)})"

    @cached_property
    def columns(self):
        """Column headers for the report."""

        columns = []
        for label, tooltip in self.COLUMNS:
            columns.append(self.Reporter.Column(label, tooltip=tooltip))
        return columns

    @cached_property
    def doctype(self):
        """Optional document type for filtering the report."""
        return self.fields.getvalue("doctype", "").lower()

    @cached_property
    def id(self):
        """Optional document ID for filtering the report."""
        return self.fields.getvalue("id", "").lower()

    @cached_property
    def rows(self):
        """Values for the report's table."""

        rows = []
        with open(f"{self.session.tier.basedir}/Log/{self.SOURCE}") as fp:
            for line in fp:
                record = Record(self, line)
                if record.in_scope:
                    rows.append(record.row)
        return rows

    @cached_property
    def start(self):
        """Optional cutoff for the earliest replacements to include."""
        return str(self.parse_date(self.fields.getvalue("start")) or "")

    @cached_property
    def table(self):
        """Assemble the table for the report."""

        opts = dict(columns=self.columns, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    @cached_property
    def user(self):
        """Optional user for filtering the report."""
        return self.fields.getvalue("user", "").lower()


class Record:
    """One row from the log file."""

    TIPS = [column[1] for column in Control.COLUMNS]

    def __init__(self, control, line):
        """Save the caller's values.

        Pass:
            control - access to the report parameters
            line - string for the line from the log file we're parsing
        """

        self.control = control
        self.fields = line.strip().split("\t")

    @cached_property
    def date(self):
        """When the replacement occurred."""
        return self.fields[0]

    @cached_property
    def id(self):
        """CDR ID for the document."""
        return self.fields[1]

    @cached_property
    def doctype(self):
        """Normalized string for the document's type."""
        return self.fields[2].lower()

    @cached_property
    def user(self):
        """Normalized account name for the user."""
        return self.fields[3].lower()

    @cached_property
    def in_scope(self):
        """Boolean: should this record be included in the report?"""

        if len(self.fields) != len(self.TIPS):
            return False
        if self.control.start and self.date < self.control.start:
            return False
        if self.control.id and self.control.id != self.id:
            return False
        if self.control.doctype and self.control.doctype != self.doctype:
            return False
        if self.control.user and self.control.user != self.user:
            return False
        return True

    @cached_property
    def row(self):
        """Values for the report table."""

        values = []
        for i, field in enumerate(self.fields):
            opts = dict(tooltip=self.TIPS[i])
            cell = self.control.Reporter.Cell(field.strip(), **opts)
            values.append(cell)
        return values


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
