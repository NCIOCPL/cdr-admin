#!/usr/bin/env python

"""Render a QC report using parameters stored in the database.

This gets around the length limitation on parameters in a GET URL.
"""

from cdrcgi import Controller, sendPage, DOCID
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
            sendPage(str(result.result_tree))
        except Exception as e:
            self.logger.exception("Report failure")
            self.bail(e)

    @property
    def doc(self):
        """Document to be filtered and displayed."""

        if not hasattr(self, "_doc"):
            id = self.fields.getvalue(DOCID)
            if not id:
                self.bail("Missing document ID")
            version = self.fields.getvalue("DocVersion")
            self._doc = Doc(self.session, id=id, version=version)
        return self._doc

    @property
    def filter_key(self):
        """String used to select filters for the report.

        Note that the parameter used to convey this value has a
        completely misleading name.
        """

        if not hasattr(self, "_doctype"):
            self._doctype = self.fields.getvalue("DocType")
            if not self._doctype:
                self._doctype = self.doc.doctype.name
        return self._doctype

    @property
    def filters(self):
        """XSL/T filters to be applied to the document."""

        if not hasattr(self, "_filters"):
            self._filters = FILTERS.get(self.filter_key)
            if not self._filters:
                self.bail(f"Filter for {self.filter_key} not supported")
        return self._filters

    @property
    def parms(self):
        """Filtering parameters."""

        id = self.fields.getvalue("parmid") or self.bail("Missing parameters")

        # Testing if 'parmid' includes a fragment ID
        if '#' in id: id = id.split('#')[0]

        query = self.Query("url_parm_set", "longURL")
        query.where(query.Condition("id", id))
        rows = query.execute(self.cursor).fetchall()
        return dict(eval(rows[0].longURL))


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
