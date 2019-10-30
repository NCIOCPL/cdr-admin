#!/usr/bin/env python

"""Show documents for which the CWD was replaced by an earlier version.
"""

from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report generation tools."""

    SUBTITLE = "Report CWD Replacements"
    SOURCE = "CWDReplacements.log"
    COLUMNS = (
        ("Date/time", "When did the replacement occur?"),
        ("DocID", "CDR ID of the affected document"),
        ("Doc type", "Document type for the affected document"),
        ("User", "User ID of the user promoting the version"),
        ("LV", "Version number of last version at time of promotion"),
        ("PV",
         "Version number of last publishable version at that time, -1 = None"),
        ("Chg", "'Y' = CWD was different from last version, else 'N'"),
        ("V#", "Version number promoted to become CWD"),
        ("V", "Was new CWD also versioned? (Y/N)"),
        ("P", "Was new CWD also versioned as publishable? (Y/N)"),
        ("Comment", "System generated comment ':' user entered comment"),
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

    def build_tables(self):
        """Assemble the report table."""

        opts = dict(columns=self.columns, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    @property
    def caption(self):
        """String to be display directly above the report table."""
        return f"Replaced Documents ({len(self.rows)})"

    @property
    def columns(self):
        """Column headers for the report."""

        columns = []
        for label, tooltip in self.COLUMNS:
            columns.append(self.Reporter.Column(label, tooltip=tooltip))
        return columns

    @property
    def doctype(self):
        """Optional document type for filtering the report."""
        return self.fields.getvalue("doctype", "").lower()

    @property
    def id(self):
        """Optional document ID for filtering the report."""
        return self.fields.getvalue("id", "").lower()

    @property
    def rows(self):
        """Values for the report's table."""

        if not hasattr(self, "_rows"):
            self._rows = []
            with open(f"{self.session.tier.basedir}/Log/{self.SOURCE}") as fp:
                for line in fp:
                    record = Record(self, line)
                    if record.in_scope:
                        self._rows.append(record.row)
        return self._rows

    @property
    def start(self):
        """Optional cutoff for the earliest replacements to include."""
        return self.fields.getvalue("start")

    @property
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

        self.__control = control
        self.__fields = line.strip().split("\t")

    @property
    def control(self):
        """Access to the report settings."""
        return self.__control

    @property
    def date(self):
        """When the replacement occurred."""
        return self.__fields[0]

    @property
    def id(self):
        """CDR ID for the document."""
        return self.__fields[1]

    @property
    def doctype(self):
        """Normalized string for the document's type."""
        return self.__fields[2].lower()

    @property
    def user(self):
        """Normalized account name for the user."""
        return self.__fields[3].lower()

    @property
    def in_scope(self):
        """Boolean: should this record be included in the report?"""

        if len(self.__fields) != len(self.TIPS):
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

    @property
    def row(self):
        """Values for the report table."""

        values = []
        for i, field in enumerate(self.__fields):
            opts = dict(tooltip=self.TIPS[i])
            cell = self.__control.Reporter.Cell(field.strip(), **opts)
            values.append(cell)
        return values


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
