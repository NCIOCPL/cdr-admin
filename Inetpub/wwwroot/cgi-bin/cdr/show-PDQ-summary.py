#!/usr/bin/env python

"""Demonstrate rendering of PDQ Summary documents.

Script to take our sample XML PDQ summary (PDQ-summary.xml) and apply
the sample XSLT stylesheet (PDQ-summary.xsl) to create a sample HTML
output file (PDQ-summary.html).  These files have been created in
response to PDQ partner requests wanting to see samples of our
transformation.

When this cgi is run it is expected that both files, the XML as well
as the XSL documents, are located within the cdr/pdqdocs directory.
The user can display the entire file or an individual section only:
 http://cdr-dev.cancer.gov/cgi-bin/cdr/show-PDQ-summary.py?section=*
or
 http://cdr-dev.cancer.gov/cgi-bin/cdr/show-PDQ-summary.py?section=2

This file has been originally created by Bob Kline.

Created:                              Volker Englisch - 2016-03-23

History:
--------
OCECDR-3856: Create Content Distribution Partner Headstart
"""

from lxml import etree, html
from cdrapi.docs import Doc
from cdrcgi import Controller, sendPage


class Control(Controller):
    """Access to the current CDR logon session."""

    XSL = "PDQ-summary.xsl"
    DOC = "PDQ-summary.xml"
    PDQDOCS = "pdqdocs"
    DOCTYPE = "<!DOCTYPE html>"
    OPTS = dict(pretty_print=True, encoding="unicode", doctype=DOCTYPE)

    def show_form(self):
        """Suppress the form handling, which this script doesn't use."""
        self.show_report()

    def show_report(self):
        """Override the base class version, as this isn't a tabular report."""

        page = self.transform(self.doc_root, section=self.section)
        sendPage(html.tostring(page, **self.OPTS))

    @property
    def doc_root(self):
        """Parsed summary document."""

        if self.doc_id:
            return Doc(self.session, id=self.doc_id).root
        return etree.parse(f"{self.pdqdocs}/{self.DOC}").getroot()

    @property
    def xsl_root(self):
        """Parsed filter document."""
        return etree.parse(f"{self.pdqdocs}/{self.XSL}").getroot()

    @property
    def pdqdocs(self):
        """Location of the filter and the default summary document on disk."""
        return f"{self.session.tier.basedir}/{self.PDQDOCS}"

    @property
    def section(self):
        """Which part of the summary document to include (default: all)."""
        return self.fields.getvalue("section") or "*"

    @property
    def doc_id(self):
        """Optional document from the repository (default: summary on disk)."""
        return self.fields.getvalue("doc-id")

    @property
    def transform(self):
        """Function which performs the XSL/T transformation of the summary."""
        return etree.XSLT(self.xsl_root)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
