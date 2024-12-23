#!/usr/bin/env python

"""Render a QC report using parameters stored in the database.

This gets around the length limitation on parameters in a GET URL.
"""

from functools import cached_property
from json import loads
from cdrcgi import Controller
from cdrapi.docs import Doc
from cdr import FILTERS


class Control(Controller):

    LOGNAME = "QCforWord"

    def run(self):
        """Short-circuit the normal form/report routing."""

        try:
            args = self.doc.cdr_id, self.filters, self.parms
            self.logger.info("%s filtered by %s with parms %s", *args)
            result = self.doc.filter(*self.filters, parms=self.parms)
            self.send_page(str(result.result_tree))
        except Exception as e:
            self.logger.exception("Report failure")
            self.bail(e)

    @cached_property
    def doc(self):
        """Document to be filtered and displayed."""

        id = self.fields.getvalue(self.DOCID)
        if not id:
            self.bail("Missing document ID")
        version = self.fields.getvalue("DocVersion")
        return Doc(self.session, id=id, version=version)

    @cached_property
    def filter_key(self):
        """String used to select filters for the report."""

        key = self.doc.doctype.name
        if not self.report_type:
            return key
        return f"{key}:{self.report_type}"

    @cached_property
    def filters(self):
        """XSL/T filters to be applied to the document."""

        filters = FILTERS.get(self.filter_key)
        if not filters:
            self.bail(f"Filter for {self.filter_key} not supported")
        return filters

    @cached_property
    def parms(self):
        """Filtering parameters."""

        id = self.fields.getvalue("parmid") or self.bail("Missing parameters")

        # Testing if 'parmid' includes a fragment ID
        if '#' in id:
            id = id.split('#')[0]

        query = self.Query("url_parm_set", "longURL")
        query.where(query.Condition("id", id))
        rows = query.execute(self.cursor).fetchall()
        return dict(loads(rows[0].longURL))

    @cached_property
    def report_type(self):
        """Flavor of the report (e.g., "rs" for redline/strikeout)."""
        return self.fields.getvalue("ReportType")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
