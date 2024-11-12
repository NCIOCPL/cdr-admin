#!/usr/bin/env python

"""
    Report listing all media docs within a summary and its Spanish translation

    (adapted from DISTypeChangeReport.py)
"""

from datetime import date
from functools import cached_property
from cdrapi.docs import Doc, Link
from cdrcgi import Controller


class Control(Controller):
    """Logic manager for report."""

    SUBTITLE = "Media in Summary Report"
    LOGNAME = "MediaInSummary"
    METHODS = "CDR ID", "Summary Title"
    CSS = """\
body { font-family: "Source Sans Pro Web", Arial, sans-serif; }
h1 { text-align: center; font-size: 1.3em; }
.pair-wrapper { display: flex; }
.lang-wrapper { float: left; width: 48%; margin: 0 .5rem; }
.single .lang-wrapper { width: 98%; }
"""

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page - `cdrcgi.HTMLPage` object
        """

        # If we found more than one candidate summary, let the user pick one.
        if self.summaries:
            page.form.append(page.hidden_field("selection_method", "id"))
            fieldset = page.fieldset("Choose Summary")
            for summary in self.summaries:
                opts = dict(
                    label=summary.display,
                    value=summary.id,
                    tooltip=summary.tooltip,
                    onclick=None
                )
                fieldset.append(page.radio_button("cdr-id", **opts))
            page.form.append(fieldset)

        # Otherwise, show the fields for the selection methods.
        else:
            fieldset = page.fieldset("Selection Method")
            checked = False
            for method in self.METHODS:
                value = method.split()[-1].lower()
                opts = dict(label=f"By {method}", value=value, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
                checked = True
            page.form.append(fieldset)

            fieldset = page.fieldset("Summary ID")
            fieldset.set("class", "by-id-block usa-fieldset")
            opts = dict(label="CDR ID", tooltip="enter CDR ID")
            fieldset.append(page.text_field("cdr-id", **opts))
            page.form.append(fieldset)

            fieldset = page.fieldset("Summary Title")
            fieldset.set("class", "by-title-block usa-fieldset")
            tooltip = "Use wildcard (%) as appropriate."
            fieldset.append(page.text_field("title", tooltip=tooltip))
            page.form.append(fieldset)
            page.add_script(self.summary_selection_js)

        # The rest of the form is common to both conditions.
        fieldset = page.fieldset("Language")
        label = "Display English and Spanish Document"
        checked = self.show_both_languages
        opts = dict(value="all", label=label, checked=True, onclick=None)
        fieldset.append(page.checkbox("language", **opts))
        page.form.append(fieldset)

        fieldset = page.fieldset("Display Options")
        display_options = (
                ("caption", "Image Caption"),
                ("description", "Content Description"),
                ("labels", "Image Labels"),
        )
        for value, label in display_options:
            checked = not self.request or value in self.display
            opts = dict(value=value, label=label, checked=checked, onclick="")
            fieldset.append(page.checkbox("show", **opts))
        page.form.append(page.hidden_field("debug", self.debug or ""))
        page.form.append(fieldset)

    def show_report(self):
        """Send the report back to the browser if it's ready."""

        if self.cdr_id:
            self.send_page(self.report)
        message = None
        if self.selection_method == "id":
            message = "No CDR ID provided."
        elif not self.fragment:
            message = "No title fragment specified."
        elif not self.summaries:
            message = f"No matching summaries found for {self.fragment!r}."
        if message:
            self.alerts.append(dict(message=message, type="warning"))
        self.show_form()

    @cached_property
    def cdr_id(self):
        """Get the entered/selected CDR ID as an integer"""

        if self.selection_method == "id":
            doc_id = self.fields.getvalue("cdr-id", "").strip()
            if not doc_id:
                return None
            try:
                return Doc.extract_id(doc_id)
            except Exception:
                self.bail("Invalid format for CDR ID")
        if len(self.summaries) == 1:
            return self.summaries[0].id
        return None

    @cached_property
    def debug(self):
        """True if we're running with increased logging."""
        return True if self.fields.getvalue("debug") else False

    @cached_property
    def display(self):
        """Used by several other properties."""
        return self.fields.getlist("show")

    @cached_property
    def fragment(self):
        """Title fragment for selecting a DIS by title."""
        return self.fields.getvalue("title", "").strip()

    @cached_property
    def loglevel(self):
        """Override to support debug logging."""
        return "DEBUG" if self.debug else self.LOGLEVEL

    @cached_property
    def pair(self):
        """Tuple of English and Spanish CDR Summary document IDs."""

        # CDR ID for English summary entered.
        query = self.Query("query_term", "int_val", "doc_id")
        query.where("path = '/Summary/TranslationOf/@cdr:ref'")
        query.where(query.Condition("int_val", self.cdr_id))
        row = query.execute(self.cursor).fetchone()

        # CDR ID for Spanish summary entered
        if not row:
            query = self.Query("query_term", "int_val", "doc_id")
            query.where("path = '/Summary/TranslationOf/@cdr:ref'")
            query.where(query.Condition("doc_id", self.cdr_id))
            row = query.execute(self.cursor).fetchone()

        return tuple(row) if row else None

    @cached_property
    def report(self):
        """`HTMLPage` object for the report."""

        # Make sure a document has been selected.
        if not self.cdr_id:
            return None

        # Determine whether we're showing both languages or just one.
        warning = None
        if self.show_both_languages:
            if self.pair:
                summaries = [Summary(self, id) for id in self.pair]
            else:
                summaries = [Summary(self, self.cdr_id)]
                warning = "This summary only exists in one language."
        else:
            summaries = [Summary(self, self.cdr_id)]

        # Initialize the DOM object for the report page.
        B = self.HTMLPage.B
        head = B.HEAD(
            B.META(charset="utf-8"),
            B.TITLE(self.TITLE),
            B.LINK(href="/favicon.ico", rel="icon"),
            B.STYLE(self.CSS)
        )
        h1 = B.H1(B.DIV(self.SUBTITLE))
        if len(summaries) > 1:
            h1.append(B.DIV("Side-by-Side"))
        h1.append(B.DIV(str(date.today())))
        header = B.E("header", h1)
        if warning:
            header.append(B.P(warning, B.CLASS("warning")))
        if len(summaries) > 1:
            selected = f"Summary selected: CDR{self.cdr_id}"
            header.append(B.P(selected, id="summary-id"))
        body_class = "single" if len(summaries) == 1 else "double"
        body = B.BODY(header, B.CLASS(body_class))
        report = B.HTML(head, body)

        # Add a block for each language.
        script = "/cgi-bin/cdr/GetCdrImage.py"
        for summary in summaries:
            root = summary.doc.root
            language = Doc.get_text(root.find(".//SummaryLanguage"))
            audience = Doc.get_text(root.find(".//SummaryAudience"))
            audience = audience.replace(" ", "_")
            wrapper = B.DIV(B.CLASS("lang-wrapper"))
            body.append(wrapper)

            # Display the language, CDR ID, and title of the summary.
            opts = dict(id=f"summary-{language.lower()}")
            wrapper.append(B.P(f"{language} - CDR{summary.id}", **opts))
            wrapper.append(B.P(summary.title, B.CLASS("summary-title")))

            # Add each image linked from the summary.
            width = 800 / len(summaries)
            for media in summary.media_docs:

                # Display the image title and CDR-ID, followed by the image.
                span = B.SPAN(f"{media.title} (CDR{media.id})")
                wrapper.append(B.P(B.B("Image: "), span))
                src = f"{script}?id=CDR{media.id}-{width}.jpg"
                href = src.replace(f"-{width}", "")
                wrapper.append(B.A(B.IMG(src=src), href=href))

                # Show the caption(s) if requested.
                if "caption" in self.display:
                    for node in media.doc.root.findall(".//MediaCaption"):
                        if node.get("audience") == audience:
                            wrapper.append(B.H3("Caption"))
                            wrapper.append(B.P(Doc.get_text(node)))

                # Show the description(s) if requested.
                if "description" in self.display:
                    path = ".//ContentDescription"
                    for node in media.doc.root.findall(path):
                        if node.get("audience") == audience:
                            wrapper.append(B.H3("Description"))
                            wrapper.append(B.P(Doc.get_text(node)))

                # Show the labels if requested.
                if "labels" in self.display:
                    wrapper.append(B.H3("Labels"))
                    labels = B.UL(B.CLASS("labels"))
                    for node in media.doc.root.findall(".//LabelName"):
                        labels.append(B.LI(Doc.get_text(node)))
                    wrapper.append(labels)

        # Ready for display.
        return report

    @cached_property
    def same_window(self):
        """Don't open more than one new browser tab."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def show_both_languages(self):
        """Check if display of caption has been selected"""
        return not self.request or self.fields.getvalue("language") == "all"

    @cached_property
    def summaries(self):
        """Find the Summary documents that match the user's title fragment."""

        if self.selection_method != "title" or not self.fragment:
            return []

        class SummaryTitle:
            def __init__(self, doc_id, display, tooltip=None):
                self.id = doc_id
                self.display = display
                self.tooltip = tooltip
        fragment = f"{self.fragment}%"
        query = self.Query("active_doc d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Summary'")
        query.where(query.Condition("d.title", fragment, "LIKE"))
        query.order("d.title")
        choices = []
        for doc_id, title in query.execute(self.cursor).fetchall():
            if len(title) > 80:
                short_title = title[:77] + "..."
                choices.append(SummaryTitle(doc_id, short_title, title))
            else:
                choices.append(SummaryTitle(doc_id, title))
        return choices


class Summary:
    """
    Represents one CDR Summary document.

    Attributes:
        id       -  CDR ID of summary document
        title    -  title of summary (from title column of all_docs table)
        control  -  object holding request parameters for report
        media    -  list of MediaLink IDs for the summary
    """

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report options
            doc_id - integer for the PDQ summary's unique CDR document ID
        """

        self.__control = control
        self.__doc_id = doc_id

    @cached_property
    def control(self):
        """Access to the database and the report options."""
        return self.__control

    @cached_property
    def doc(self):
        """`Doc` object for the summary's CDR document."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def id(self):
        """Integer for the PDQ summary's unique CDR document ID."""
        return self.__doc_id

    @cached_property
    def title(self):
        """Official title of the PDQ summary."""

        title = Doc.get_text(self.doc.root.find("Title"))
        return title or self.doc.title.split(";")[0]

    @cached_property
    def media_link_ids(self):
        """Sequence of CDR IDs for Media documents linked from the summary."""

        ids = []
        for node in self.doc.root.findall(".//MediaLink/MediaID"):
            value = node.get(Link.CDR_REF)
            if value:
                try:
                    ids.append(Doc.extract_id(value))
                except Exception:
                    self.control.logger.exception("Invalid ID %s", value)
                    message = f"Invalid media link {value!r} found."
                    alert = dict(message=message, type="warning")
                    self.control.alerts.append(alert)
        if not ids:
            message = f"No valid media links found in CDR{self.id}."
            self.control.alerts.append(dict(message=message, type="warning"))
            self.control.show_form()
        return ids

    @cached_property
    def media_docs(self):
        """Media documents selected for the report."""

        if not self.media_link_ids:
            message = "Summary selected does not contain images."
            self.control.bail(f"ERROR: {message}")
        return [Media(self.control, id) for id in self.media_link_ids]


class Media:
    """
    Represents one CDR Media document.

    Attributes:
        id       -  CDR ID of media document
        title    -  title of media (from title column of all_docs table)
        control  -  object holding request parameters for report
        label
        description
        caption
    """

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report options
            doc_id - integer for the PDQ summary's unique CDR document ID
        """

        self.control = control
        self.id = doc_id

    @cached_property
    def doc(self):
        """`Doc` object for the media's CDR document."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def title(self):
        """Official title of the media document"""

        title = Doc.get_text(self.doc.root.find("Title"), "").strip()
        return title or self.doc.title.split(";")[0]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
