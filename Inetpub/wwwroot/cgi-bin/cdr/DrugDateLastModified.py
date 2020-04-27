#!/usr/bin/env python

"""
Report on the last modifications to Drug Information Summary documents

JIRA::OCECDR-4506
"""

import datetime
import cdrcgi
from cdr import lastVersions
from cdrapi.db import connect, Query

class Control(cdrcgi.Control):
    """
    Custom behavior for the report
    """

    SUBTITLE = "Drug Information Summary Date Last Modified"
    REPORT_TYPES = "user", "system"
    COLUMN = cdrcgi.Report.Column

    def __init__(self):
        """
        Invoke base class constructor and add a database cursor
        """

        cdrcgi.Control.__init__(self, self.SUBTITLE)
        self.cursor = connect(user="CdrGuest").cursor()

    def build_tables(self):
        """
        Assemble the table for the report
        """

        self.PAGE_TITLE = "Drug Date Last Modified"
        cols = (
            self.COLUMN("DocId", width="100px"),
            self.COLUMN("Summary Title", width="350px"),
            self.COLUMN("Date Last Modified", width="130px"),
            self.COLUMN("Last Modify Action Date (System)", width="130px"),
            self.COLUMN("LastV Publishable?", width="100px"),
            self.COLUMN("User", width="150px"),
        )
        rows = []
        drugs = self.drugs
        rows = [drug.values for drug in self.drugs]
        pattern = "Drug Information Summary Date Last Modified ({}) Report"
        title = pattern.format(self.report_type.capitalize())
        subtitle = "{} \u2014 {}".format(self.start, self.end)
        report_date = "Report Date: {}".format(datetime.date.today())
        top_lines = title, subtitle
        tab = "DLM Report"
        opts = dict(caption=top_lines, sheet_name=tab, show_report_date=True)
        return [cdrcgi.Report.Table(cols, rows, **opts)]

    def populate_form(self, form):
        """
        Let the user select the report type, format, and date range
        """

        form.add("<fieldset>")
        form.add(form.B.LEGEND("Report Type"))
        for report_type in self.REPORT_TYPES:
            checked = report_type == self.report_type
            label = report_type.capitalize()
            form.add_radio("report-type", label, report_type, checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Date Range"))
        form.add_date_field("start", "Start", value=self.start)
        form.add_date_field("end", "End", value=self.end)
        form.add("</fieldset>")
        form.add_output_options(default="html")

    @property
    def drugs(self):
        """
        Collect the documents which match the report's date range
        """

        if not hasattr(self, "_drugs"):
            cols = "t.doc_id", "t.value", "m.value", "s.last_save_date"
            query = Query("query_term t", *cols).unique().order("t.value")
            query.where("t.path = '/DrugInformationSummary/Title'")
            query.join("doc_last_save s", "s.doc_id = t.doc_id")
            start = str(self.start)
            end = "{} 23:59:59".format(self.end)
            mpath = "m.path = '/DrugInformationSummary/DateLastModified'"
            mjoin = ["m.doc_id = t.doc_id", mpath]
            if self.report_type == "user":
                query.where("m.value IS NOT NULL")
                mjoin.append(query.Condition("m.value", start, ">="))
                mjoin.append(query.Condition("m.value", end, "<="))
            else:
                query.where(query.Condition("s.last_save_date", start, ">="))
                query.where(query.Condition("s.last_save_date", end, "<="))
            query.outer("query_term m", *mjoin)
            rows = query.execute(self.cursor).fetchall()
            query.log(label="Drug DLM")
            self._drugs = [Drug(self.cursor, row) for row in rows]
        return self._drugs

    @property
    def report_type(self):
        """
        Ensure that the report type parameter hasn't been tampered with
        """

        if not hasattr(self, "_report_type"):
            self._report_type = self.fields.getvalue("report-type", "user")
            if self._report_type not in self.REPORT_TYPES:
                cdrcgi.bail()
        return self._report_type

    @property
    def start(self):
        """
        Get the `datetime.date` object for the start of the range

        Ensure that the range is valid.
        """

        if not hasattr(self, "_start"):
            start = self.fields.getvalue("start")
            if start:
                self._start = self._parse_date(start)
                if self._start > self.end:
                    cdrcgi.bail("Invalid date range")
            else:
                self._start = self.end - datetime.timedelta(6)
        return self._start

    @property
    def end(self):
        """
        Get the `datetime.date` object for the end of the range
        """

        if not hasattr(self, "_end"):
            end = self.fields.getvalue("end")
            if end:
                self._end = self._parse_date(end)
            else:
                self._end = datetime.date.today()
        return self._end

    @staticmethod
    def _parse_date(string):
        """
        Extract a `datetime.date` object from an ISO date string
        """

        try:
            return datetime.datetime.strptime(string, "%Y-%m-%d").date()
        except:
            cdrcgi.bail("Invalid date string")


class Drug:
    """
    Drug Information Summary information needed for the report
    """

    CELL = cdrcgi.Report.Cell
    BASE = "https://{}{}".format(cdrcgi.WEBSERVER, cdrcgi.BASE)
    URL = BASE + "/DocVersionHistory.py?Session=guest&DocId={}"
    LINK_EASYXF = "font: colour blue, underline on;align: vert top"
    LINK_STYLE = cdrcgi.Report.xf(horiz="center", easyxf=LINK_EASYXF)

    def __init__(self, cursor, row):
        """
        Capture the arguments passed to the constructor

        Pass:
          cursor - needed for finding the user who last saved the document
          row - database result with doc ID, title, and dates last modified
                and saved
        """

        self.__cursor = cursor
        self.__row = row

    @property
    def doc_id(self):
        """
        Pull the DIS document ID from the database result set row
        """

        return self.__row[0]

    @property
    def title(self):
        """
        Pull the CDR document title from the database result set row
        """

        return self.__row[1]

    @property
    def modified(self):
        """
        Get the date portion of the "date last modified" value

        Return an empty string if the value is not present (only possible
        when the "system" report has been requested).
        """

        if not self.__row[2]:
            return ""
        return str(self.__row[2])[:10]

    @property
    def saved(self):
        """
        Drop the time from the DATETIME when the document was last saved
        """

        return str(self.__row[3])[:10]

    @property
    def user(self):
        """
        Return the full name of the user who last saved the document
        """

        if not hasattr(self, "_user"):
            query = Query("usr u", "u.fullname")
            query.join("doc_save_action a", "a.save_user = u.id")
            query.join("doc_last_save s", "s.last_save_date = a.save_date")
            query.where(query.Condition("s.doc_id", self.doc_id))
            row = query.execute(self.__cursor).fetchone()
            self._user = row.fullname if row else ""
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
                versions = lastVersions("guest", self.doc_id)
                last_any, last_pub, changed = versions
                if last_any < 1:
                    self._publishable = "N/A"
                elif last_any == last_pub:
                    self._publishable = "Y"
                else:
                    self._publishable = "N"
            except Exception as e:
                self._publishable = str(e)
        return self._publishable

    @property
    def values(self):
        """
        Assemble the table row for this drug information summary
        """

        url = self.URL.format(self.doc_id)
        opts = dict(href=url, sheet_style=self.LINK_STYLE)
        link = self.CELL("CDR{:d}".format(self.doc_id), **opts)
        modified = self.CELL(self.modified, center=True)
        saved = self.CELL(self.saved, center=True)
        publishable = self.CELL(self.publishable, center=True)
        user = self.CELL(self.user, center=True)
        return link, self.title, modified, saved, publishable, user


Control().run()
