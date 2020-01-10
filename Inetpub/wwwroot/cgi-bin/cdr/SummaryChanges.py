#!/usr/bin/env python

"""Report history of changes to a single summary.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
from datetime import timedelta
import lxml.html


class Control(Controller):
    """Access to the database, logging, form building, etc."""

    SUBTITLE = "History of Changes to Summary"
    METHOD = "get"
    FILTER = "name:Summary Changes Report"
    CSS = (
        "#summary-title, #wrapper h2 { text-align: center; }",
        "#summary-title span { font-size: .85em; }",
        "#wrapper h2 { font-size: 14pt; }",
    )

    def populate_form(self, page):
        """Ask for the information we need for the report.

        Pass:
            page - HTMLPage object
        """

        if self.summaries:
            page.form.append(page.hidden_field("years", self.years))
            fieldset = page.fieldset("Select Summary")
            checked = True
            for id, title in self.summaries:
                label = f"[CDR{id:010d}] {title}"
                opts = dict(label=label, value=id, checked=checked)
                fieldset.append(page.radio_button("DocId", **opts))
                checked = False
            page.add_css("fieldset { width: 1024px; }")
        else:
            if self.fragment:
                fieldset = page.fieldset("Error")
                message = page.B.P(f"No matches for {self.fragment!r}")
                message.set("class", "error")
                fieldset.append(message)
                page.form.append(fieldset)
            fieldset = page.fieldset("Term ID or Title for Summary")
            fieldset.append(page.text_field("DocId", label="CDR ID"))
            fieldset.append(page.text_field("title", label="Doc Title"))
            page.form.append(fieldset)
            fieldset = page.fieldset("Date Range of Report")
            fieldset.append(page.text_field("years", value=2))
        page.form.append(fieldset)

    def show_report(self):
        """Override, because this is not a tabular report."""

        B = lxml.html.builder
        if not self.id:
            self.show_form()
        title = self.doc.title.split(";")[0]
        span = B.SPAN(f"Changes made in the Last {self.years} Year(s)")
        title = B.H2(title, B.BR(), span, id="summary-title")
        self.report.page.form.append(title)
        wrapper = B.DIV(id="wrapper")
        for section in self.sections:
            wrapper.append(B.BR())
            for fragment in section:
                wrapper.append(fragment)
            wrapper.append(B.HR())
            wrapper.append(B.BR())
        self.report.page.form.append(wrapper)
        self.report.page.add_css("\n".join(self.CSS))
        self.report.send()

    @property
    def doc(self):
        """The summary document for the report."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.session, id=self.id)
        return self._doc

    @property
    def fragment(self):
        """Title fragment for the summary."""
        return self.fields.getvalue("title")

    @property
    def id(self):
        """Document ID for the report."""

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("DocId")
            if self._id:
                try:
                    self._id = Doc.extract_id(self._id)
                except:
                    self.bail("Invalid ID")
            elif self.summaries and len(self.summaries) == 1:
                self._id = self.summaries[0][0]
        return self._id

    @property
    def no_results(self):
        """Suppress the message we'd get with no tables."""
        return None

    @property
    def sections(self):
        """Sequence of sections of the report, one for each change."""

        if not hasattr(self, "_sections"):
            last_section = None
            sections = []
            for version, date in self.versions:
                display_date = date.strftime("%m/%d/%Y")
                doc = Doc(self.session, id=self.id, version=version)
                response = doc.filter(self.FILTER)
                html = str(response.result_tree).strip()
                if html != last_section:
                    last_section = html
                    html = html.replace("@@PubVerDate@@", display_date)
                    sections.append(lxml.html.fragments_fromstring(html))
            self._sections = reversed(sections)
        return self._sections

    @property
    def summaries(self):
        """Sequence of ID/title tuples for the summary picklist."""

        if not hasattr(self, "_summaries"):
            self._summaries = None
            if self.fragment:
                fragment = f"{self.fragment}%"
                query = self.Query("document d", "d.id", "d.title").order(2)
                query.join("doc_type t", "t.id = d.doc_type")
                query.where("t.name = 'Summary'")
                query.where(query.Condition("d.title", fragment, "LIKE"))
                rows = query.execute(self.cursor).fetchall()
                self._summaries = [tuple(row) for row in rows]
        return self._summaries

    @property
    def versions(self):
        """Sequence of num/date for versions to be included in the report."""

        if not hasattr(self, "_versions"):
            days = int(365.25 * self.years)
            start = self.started - timedelta(days)
            query = self.Query("doc_version", "num", "dt").order("num")
            query.where(query.Condition("id", self.id))
            query.where(query.Condition("dt", start, ">="))
            query.where("publishable = 'Y'")
            rows = query.execute(self.cursor).fetchall()
            self._versions = [tuple(row) for row in rows]
        return self._versions

    @property
    def years(self):
        """Date range for the report."""
        try:
            return int(self.fields.getvalue("years"))
        except:
            return 2


if __name__ == "__main__":
    "Let the script be loaded as a module."
    Control().run()
