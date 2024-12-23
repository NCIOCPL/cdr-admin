#!/usr/bin/env python

"""Report history of changes to a single summary.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
from datetime import date
from dateutil.relativedelta import relativedelta
from functools import cached_property
import lxml.html


class Control(Controller):
    """Access to the database, logging, form building, etc."""

    SUBTITLE = "History of Changes to Summary"
    METHOD = "get"
    SCOPES = dict(all="Complete History", range="Date Range")
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

        # Don't need a form if we already have a document.
        if self.doc:
            return self.show_report()

        # If we have more than one match for the title fragment, pick one.
        if self.summaries:
            fieldset = page.fieldset("Select Summary")
            checked = True
            for id, title in self.summaries:
                label = f"[CDR{id:010d}] {title}"
                opts = dict(label=label, value=id, checked=checked)
                fieldset.append(page.radio_button("DocId", **opts))
                checked = False
            page.form.append(fieldset)

        # Otherwise, show the title and ID fields.
        else:
            fieldset = page.fieldset("Term ID or Title for Summary")
            opts = dict(label="CDR ID", value=self.id)
            fieldset.append(page.text_field("DocId", **opts))
            opts = dict(label="Doc Title", value=self.fragment)
            fieldset.append(page.text_field("title", **opts))
            page.form.append(fieldset)

        # These fields are common to both forms.
        fieldset = page.fieldset("Report Options")
        default = self.scope or "range"
        for value in reversed(sorted(self.SCOPES)):
            checked = value == default
            opts = dict(
                value=value,
                label=self.SCOPES[value],
                checked=checked,
            )
            fieldset.append(page.radio_button("scope", **opts))
        page.form.append(fieldset)
        if self.request:
            start, end = self.start, self.end
        else:
            end = date.today()
            start = end - relativedelta(years=2)
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
        if not self.doc:
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

    @cached_property
    def all(self):
        """True if we should report on all changes."""
        return self.scope == "all"

    @cached_property
    def doc(self):
        """The summary document for the report.

        As a side effect, alerts are registered here to show the user
        useful information.
        """

        id = self.id
        if not id:
            if not self.fragment:
                if self.request:
                    message = "CDR ID or title is required."
                    self.alerts.append(dict(message=message, type="error"))
                return None
            elif not self.summaries:
                message = f"No summaries found for {self.fragment!r}."
                self.alerts.append(dict(message=message, type="warning"))
                return None
            elif len(self.summaries) > 1:
                message = f"Multiple matches found for {self.fragment!r}."
                self.alerts.append(dict(message=message, type="info"))
                return None
            self.logger.info("summmaries=%r", self.summaries)
            id = self.summaries[0][0]
        doc = Doc(self.session, id=id)
        try:
            doctype = doc.doctype.name
            if doctype != "Summary":
                message = f"CDR{doc.id} is a {doctype} document."
                self.alerts.append(dict(message=message, type="warning"))
                return None
            return doc
        except Exception:
            message = f"Document {id} not found."
            self.logger.exception(message)
            self.alerts.append(dict(message=message, type="error"))
            return None

    @cached_property
    def end(self):
        """End of date range for the report."""
        return self.parse_date(self.fields.getvalue("end"))

    @cached_property
    def fragment(self):
        """Title fragment for the summary."""
        return self.fields.getvalue("title")

    @cached_property
    def id(self):
        """Document ID for the report."""
        return self.fields.getvalue("DocId", "").strip()

    @cached_property
    def no_results(self):
        """Suppress the message we'd get with no tables."""
        return None

    @cached_property
    def scope(self):
        """How is the user deciding which versions to report on?"""

        scope = self.fields.getvalue("scope")
        if scope and scope not in self.SCOPES:
            self.bail()
        return scope

    @cached_property
    def sections(self):
        """Sequence of sections of the report, one for each change."""

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
        return reversed(sections)

    @cached_property
    def start(self):
        """Beginning of date range for the report."""
        return self.parse_date(self.fields.getvalue("start"))

    @cached_property
    def same_window(self):
        """Decide when to avoid opening a new browser tab."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def suppress_sidenav(self):
        """Don't show the left navigation column on followup pages."""
        return True if self.id or self.fragment else False

    @cached_property
    def summaries(self):
        """Sequence of ID/title tuples for the summary picklist."""

        if not self.fragment:
            return None
        query = self.Query("document d", "d.id", "d.title").order(2)
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Summary'")
        query.where(query.Condition("d.title", f"{self.fragment}%", "LIKE"))
        rows = query.execute(self.cursor).fetchall()
        return [tuple(row) for row in rows]

    @cached_property
    def versions(self):
        """Sequence of num/date for versions to be included in the report."""

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
        return [tuple(row) for row in rows]


if __name__ == "__main__":
    "Let the script be loaded as a module."
    Control().run()
