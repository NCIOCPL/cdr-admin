#!/usr/bin/env python

"""Report on the last modifications to Drug Information Summary documents.
"""

from datetime import date, timedelta
from cdrapi.docs import Doc
from cdrcgi import Controller, WEBSERVER, BASE


class Control(Controller):
    """Access to report-building tools."""

    SUBTITLE = "Drug Information Summary Date Last Modified"
    REPORT_TYPES = "user", "system"

    def build_tables(self):
        """Assemble the table for the report."""

        opts = dict(
            caption=self.caption,
            sheet_name="DLM Report",
            columns=self.columns,
            show_report_date=True,
        )
        return [self.Reporter.Table(self.rows, **opts)]

    def populate_form(self, page):
        """Let the user select the report type, format, and date range.

        Pass:
            page - HTMLPage on which we draw the fields
        """

        fieldset = page.fieldset("Report Type")
        for report_type in self.REPORT_TYPES:
            checked = report_type == self.report_type
            opts = dict(value=report_type, checked=checked)
            fieldset.append(page.radio_button("report-type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start", value=self.start))
        fieldset.append(page.date_field("end", value=self.end))
        page.form.append(fieldset)
        page.add_output_options(default="html")

    @property
    def caption(self):
        """Rows to be displayed at the top of the report's table."""

        pattern = "Drug Information Summary Date Last Modified ({}) Report"
        return (
            pattern.format(self.report_type.capitalize()),
            f"{self.start} \u2014 {self.end}",
        )

    @property
    def columns(self):
        """Headers for the top of each report table column."""

        if not hasattr(self, "_columns"):
            Column = self.Reporter.Column
            self._columns = (
                Column("DocId", width="100px"),
                Column("Summary Title", width="350px"),
                Column("Date Last Modified", width="130px"),
                Column("Last Modify Action Date (System)", width="130px"),
                Column("LastV Publishable?", width="100px"),
                Column("User", width="150px"),
            )
        return self._columns

    @property
    def drugs(self):
        """Collect the documents which match the report's date range."""

        if not hasattr(self, "_drugs"):
            cols = (
                "t.doc_id",
                "t.value AS title",
                "m.value AS modified",
                "s.last_save_date",
            )
            query = self.Query("query_term t", *cols).unique().order("t.value")
            query.where("t.path = '/DrugInformationSummary/Title'")
            query.join("doc_last_save s", "s.doc_id = t.doc_id")
            start = str(self.start)
            end = f"{self.end} 23:59:59"
            m_path = "m.path = '/DrugInformationSummary/DateLastModified'"
            m_join = ["m.doc_id = t.doc_id", m_path]
            if self.report_type == "user":
                query.where("m.value IS NOT NULL")
                m_join.append(query.Condition("m.value", start, ">="))
                m_join.append(query.Condition("m.value", end, "<="))
            else:
                query.where(query.Condition("s.last_save_date", start, ">="))
                query.where(query.Condition("s.last_save_date", end, "<="))
            query.outer("query_term m", *m_join)
            rows = query.execute(self.cursor).fetchall()
            query.log(label="Drug DLM")
            self._drugs = [Drug(self, row) for row in rows]
        return self._drugs

    @property
    def end(self):
        """Get the `datetime.date` object for the end of the range."""

        if not hasattr(self, "_end"):
            end = self.fields.getvalue("end")
            if end:
                try:
                    self._end = self.parse_date(end)
                except Exception:
                    self.bail("Invalid end date")
            else:
                self._end = date.today()
        return self._end

    @property
    def report_type(self):
        """Ensure that the report type parameter hasn't been tampered with."""

        if not hasattr(self, "_report_type"):
            self._report_type = self.fields.getvalue("report-type", "user")
            if self._report_type not in self.REPORT_TYPES:
                self.bail()
        return self._report_type

    @property
    def rows(self):
        """Table rows for the report."""
        return [drug.values for drug in self.drugs]

    @property
    def start(self):
        """Get the `datetime.date` object for the start of the range."""

        if not hasattr(self, "_start"):
            start = self.fields.getvalue("start")
            if start:
                try:
                    self._start = self.parse_date(start)
                    if self._start > self.end:
                        self.bail("Invalid date range")
                except Exception:
                    self.bail("Invalid start date")
            else:
                self._start = self.end - timedelta(6)
        return self._start


class Drug:
    """Drug Information Summary information needed for the report."""

    BASE = f"https://{WEBSERVER}{BASE}"
    URL = BASE + "/DocVersionHistory.py?Session=guest&DocId={:d}"

    def __init__(self, control, row):
        """Capture the arguments passed to the constructor

        Pass:
          control - access to the session and to report-building tools
          row - database result with doc ID, title, and dates last modified
                and saved
        """

        self.__control = control
        self.__row = row

    @property
    def doc(self):
        """`Doc` object for the CDR DrugInformationSummary document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.__row.doc_id)
        return self._doc

    @property
    def title(self):
        """Pull the CDR document title from the database result set row."""
        return self.__row.title

    @property
    def modified(self):
        """Get the date portion of the "date last modified" value.

        Return an empty string if the value is not present (only possible
        when the "system" report has been requested).
        """

        if not self.__row.modified:
            return ""
        return str(self.__row.modified)[:10]

    @property
    def saved(self):
        """Drop the time from the DATETIME when the doc was last saved."""
        return str(self.__row.last_save_date)[:10]

    @property
    def user(self):
        """Return the name of the user who last saved the document."""

        if not hasattr(self, "_user"):
            if self.doc.modification is not None:
                user = self.doc.modification.user
            else:
                user = self.doc.creation.user
            self._user = user.fullname or user.name or "[unknown]"
        return self._user

    @property
    def publishable(self):
        """
        String for column indicating whether last version can be published

        Return:
          "Y" if it can be
          "N" if it cannot be
          "N/A" if the document has no versions
          Exception string if an exception is thrown
        """

        if not hasattr(self, "_publishable"):
            try:
                last_version = self.doc.last_version
                if last_version is None:
                    self._publishable = "N/A"
                elif last_version == self.doc.last_publishable_version:
                    self._publishable = "Y"
                else:
                    self._publishable = "N"
            except Exception as e:
                self._publishable = str(e)
        return self._publishable

    @property
    def url(self):
        """Link to the Document Version History report for this document."""
        return self.URL.format(self.doc.id)

    @property
    def values(self):
        """Assemble the table row for this drug information summary."""

        Cell = self.__control.Reporter.Cell
        return (
            Cell(f"CDR{self.doc.id:d}", href=self.url, center=True),
            Cell(self.title),
            Cell(self.modified, center=True),
            Cell(self.saved, center=True),
            Cell(self.publishable, center=True),
            Cell(self.user, center=True),
        )


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
