#!/usr/bin/env python

"""Report on modified CDR documents.

"We need a simple 'Documents Modified' Report to be generated in an Excel
spreadsheet, which verifies what documents were changed within a given time
frame."
"""

from cdrcgi import Controller
import datetime

class Control(Controller):

    SUBTITLE = "Documents Modified Report"

    def build_tables(self):
        """Assemble and return the report table."""

        opts = dict(columns=self.columns, sheet_name="Modified Documents")
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Add a date range to the form.

        Pass:
            page - HTMLPage on which the fields are placed
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(6)
        fieldset = page.fieldset("Report Options")
        opts = dict(label="Doc Type", options=["all"]+self.doctypes)
        fieldset.append(page.select("doctype", **opts))
        opts = dict(label="Start Date", value=start)
        fieldset.append(page.date_field("start", **opts))
        opts = dict(label="End Date", value=end)
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)

    @property
    def format(self):
        """Override the default for the report so that it's a workbook."""
        return "excel"

    @property
    def columns(self):
        """Column headers for the report."""
        return (
            self.Reporter.Column("Doc ID", width="70px"),
            self.Reporter.Column("Doc Title", width="700px"),
            self.Reporter.Column("Last Version", width="100px"),
            self.Reporter.Column("Publishable", width="100px"),
        )

    @property
    def start(self):
        """Date range beginning selected on the form."""

        try:
            start = self.fields.getvalue("start")
            return self.parse_date(start)
        except:
            self.logger.exception("invalid start date")
            self.bail("Invalid starting date")

    @property
    def end(self):
        """Date range end selected on the form."""

        try:
            end = self.fields.getvalue("end")
            return self.parse_date(end)
        except:
            self.logger.exception("invalid end date")
            self.bail("Invalid ending date")

    @property
    def doctype(self):
        """CDR document type selected for the report."""

        if not hasattr(self, "_doctype"):
            self._doctype = self.fields.getvalue("doctype")
            if self._doctype == "all":
                self._doctype = None
            if self._doctype:
                try:
                    self._doctype = int(self._doctype)
                except:
                    self.bail()
                if self._doctype not in [pair[0] for pair in self.doctypes]:
                    self.bail()
        return self._doctype

    @property
    def doctypes(self):
        """Active document types for the form's picklist."""

        if not hasattr(self, "_doctypes"):
            query = self.Query("doc_type", "id", "name").order("name")
            query.where("active = 'Y'")
            query.where("xml_schema IS NOT NULL")
            query.where("name NOT IN ('Filter', 'xxtest', 'schema')")
            rows = query.execute(self.cursor).fetchall()
            self._doctypes = [list(row) for row in rows]
        return self._doctypes

    @property
    def rows(self):
        """Values for the report table.

        Values have been scrubbed, so interpolation within the SQL
        subquery is safe. SQL Server limitations prevent the use
        of placeholders in subqueries.
        """

        subquery = self.Query("doc_version", "id", "MAX(num) as num")
        if self.doctype:
            subquery.where(f"doc_type = {self.doctype:d}")
        subquery.group("id")
        if self.start:
            subquery.where(f"dt >= '{self.start}'")
        if self.end:
            subquery.where(f"dt <= '{self.end} 23:59:59'")
        subquery.alias("m")
        fields = "v.id", "v.title", "v.num", "v.publishable"
        query = self.Query("doc_version v", *fields).order("v.id")
        query.join(subquery, "m.id = v.id", "m.num = v.num")
        rows = []
        for row in query.execute(self.cursor).fetchall():
            rows.append([
                self.Reporter.Cell(row.id, center=True),
                self.Reporter.Cell(row.title),
                self.Reporter.Cell(row.num, center=True),
                self.Reporter.Cell(row.publishable, center=True),
            ])
        return rows


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
