#!/usr/bin/env python

"""Report history of changes to a single summary.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
from datetime import date
import lxml.html


class Control(Controller):
    """Access to the database, logging, form building, etc."""

    SUBTITLE = "History of Changes to Summary"
    METHOD = "get"
    SCOPES = "all", "range"
    FILTER = "name:Summary Changes Report"
    CSS = (
        "#summary-title, #wrapper h2 { text-align: center; }",
        "#summary-title span { font-size: .85em; }",
        "#wrapper h2 { font-size: 14pt; }",
    )
    SCRIPT = (
        "function check_scope(scope) {",
        "  if (scope == 'all')",
        "    jQuery('#date-range').hide();",
        "  else",
        "    jQuery('#date-range').show();",
        "}",
    )

    def populate_form(self, page):
        """Ask for the information we need for the report.

        Pass:
            page - HTMLPage object
        """

        if self.summaries:
            page.form.append(page.hidden_field("start", self.start))
            page.form.append(page.hidden_field("end", self.end))
            page.form.append(page.hidden_field("scope", self.scope))
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
            fieldset = page.fieldset("Report Options")
            opts = dict(value="range", label="Date Range", checked=True)
            fieldset.append(page.radio_button("scope", **opts))
            opts = dict(value="all", label="Complete History")
            fieldset.append(page.radio_button("scope", **opts))
            page.form.append(fieldset)
            end = date.today()
            year = end.year - 2
            day = end.day
            if day == 29 and end.month == 2:
                day = 28
            start = date(year, end.month, day)
            fieldset = page.fieldset("Date Range Of Report")
            fieldset.set("id", "date-range")
            fieldset.append(page.date_field("start", value=start))
            fieldset.append(page.date_field("end", value=end))
            page.form.append(fieldset)
            page.add_script("\n".join(self.SCRIPT))
        page.form.append(fieldset)

    def show_report(self):
        """Override, because this is not a tabular report."""

        B = lxml.html.builder
        if not self.id:
            self.show_form()
        title = self.doc.title.split(";")[0]
        if self.all:
            description = "Complete history of changes in the CDR"
        elif self.start:
            if self.end:
                description = f"Changes made {self.start} through {self.end}"
            else:
                description = f"Changes made since {self.start}"
        elif self.end:
            description = f"Changes made through {self.end}"
        else:
            description = "Complete history of changes in the CDR"
        span = B.SPAN(description)
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
    def all(self):
        """True if we should report on all changes."""
        return self.scope == "all"

    @property
    def doc(self):
        """The summary document for the report."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.session, id=self.id)
        return self._doc

    @property
    def end(self):
        """End of date range for the report."""

        if not hasattr(self, "_end"):
            self._end = self.parse_date(self.fields.getvalue("end"))
        return self._end

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
                except Exception:
                    self.bail("Invalid ID")
            elif self.summaries and len(self.summaries) == 1:
                self._id = self.summaries[0][0]
        return self._id

    @property
    def no_results(self):
        """Suppress the message we'd get with no tables."""
        return None

    @property
    def scope(self):
        """How is the user deciding which versions to report on?"""

        if not hasattr(self, "_scope"):
            self._scope = self.fields.getvalue("scope")
            if self._scope not in self.SCOPES:
                self.bail()
        return self._scope

    @property
    def sections(self):
        """Sequence of sections of the report, one for each change."""

        if not hasattr(self, "_sections"):
            last_section = None
            sections = []
            for version, version_date in self.versions:
                display_date = version_date.strftime("%m/%d/%Y")
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
    def start(self):
        """Beginning of date range for the report."""

        if not hasattr(self, "_start"):
            self._start = self.parse_date(self.fields.getvalue("start"))
        return self._start

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
            query = self.Query("doc_version", "num", "dt").order("num")
            query.where(query.Condition("id", self.id))
            if not self.all:
                if self.start:
                    query.where(query.Condition("dt", self.start, ">="))
                if self.end:
                    end = f"{self.end} 23:59:59"
                    query.where(query.Condition("dt", end, "<="))
            query.where("publishable = 'Y'")
            rows = query.execute(self.cursor).fetchall()
            self._versions = [tuple(row) for row in rows]
        return self._versions


if __name__ == "__main__":
    "Let the script be loaded as a module."
    Control().run()
