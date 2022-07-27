#!/usr/bin/env python

"""
    Report listing all media docs within a summary and its Spanish translation

    (adapted from DISTypeChangeReport.py)
"""

from datetime import date
from cdrapi.docs import Doc
from cdrcgi import Controller
from lxml import html
from lxml.html import builder
import sys


class Control(Controller):
    """
    Logic manager for report.
    """

    SUBTITLE = "Media in Summary Report"
    LOGNAME = "MediaInSummary"
    CURRENT = "Current (most recent changes for each category of change)"
    CSS = "../../stylesheets/MediaInSummary.css"

    def show_report(self):
        """Send the report back to the browser."""

        opts = dict(
            pretty_print=True,
            doctype="<!DOCTYPE html>",
            encoding="utf-8",
        )
        sys.stdout.buffer.write(b"Content-type: text/html;charset=utf-8\n\n")
        sys.stdout.buffer.write(html.tostring(self.report, **opts))
        sys.exit(0)

    def get_int_cdr_id(self, value):
        """
        Convert CDR ID to integer. Exit with an error message on failure.
        """
        if value:
            try:
                return Doc.extract_id(value)
            except Exception:
                self.bail("Invalid format for CDR ID")
        return None

    @property
    def report(self):
        """`HTMLPage` object for the report."""

        if not hasattr(self, "_report"):
            B = builder
            meta = B.META(charset="utf-8")
            link = B.LINK(href=self.CSS, rel="stylesheet")
            icon = B.LINK(href="/favicon.ico", rel="icon")
            head = B.HEAD(meta, B.TITLE(self.TITLE), icon, link)
            time = B.SPAN(self.today.strftime("%Y-%m-%d"))
            args = self.SUBTITLE, B.BR(), "Side-by-Side", B.BR(), time
            cdrId = self.get_int_cdr_id(self.fields.getvalue("cdr-id"))
            orig_id = B.P(f"Summary selected: CDR{cdrId}", id="summary-id")
            wrapper = body = B.BODY(B.E("header", B.H1(*args)), orig_id)
            self._report = B.HTML(head, body)

            # Users want to be able to only display the content for a single
            # language.  In that case we're creating a single element list
            # to iterate over
            # --------------------------------------------------------------
            if not self.show_both_languages:
                if int(cdrId) == self.summary_docs[0].id:
                    summary_docs = self.summary_docs[:1]
                else:
                    summary_docs = self.summary_docs[1:]
            else:
                summary_docs = self.summary_docs

            # Creating one column per language
            # --------------------------------
            for summary_doc in summary_docs:
                root = summary_doc.doc.root
                lang = Doc.get_text(root.find(".//SummaryLanguage"))
                audience = Doc.get_text(root.find(".//SummaryAudience"))
                wrapper = B.DIV(B.CLASS("lang-wrapper"))
                body.append(wrapper)

                # Display the language and CDR-ID of the summary
                summary_lang = B.P(f"{lang} - CDR{summary_doc.id}",
                                   id=f"summary-{lang.lower()}")
                wrapper.append(summary_lang)

                # Display the summary title
                summary_title = summary_doc.title
                summary_info = B.P(summary_title, B.CLASS("summary-title"))
                wrapper.append(summary_info)

                for media_doc in summary_doc.media_docs:
                    # Display the image title and CDR-ID, followed by the image
                    span = B.SPAN(f"{media_doc.title} (CDR{media_doc.id})")
                    wrapper.append(B.P(B.B("Image: "), span))
                    image = ("/cgi-bin/cdr/GetCdrImage.py?"
                             f"id=CDR{media_doc.id}-400.jpg")
                    full_image = image.replace('-400', '')
                    wrapper.append(B.A(B.IMG(src=image), href=full_image))

                    attributes = {}
                    if self.show_caption:
                        path = ".//MediaCaption"
                        for caption in media_doc.doc.root.findall(path):
                            attributes = caption.attrib
                            if attributes.get('audience') == audience:
                                # XXX Do we really want to nest p elements?
                                paragraph = B.P(
                                    B.B("Caption:"),
                                    B.BR(),
                                    B.P(Doc.get_text(caption))
                                )
                                wrapper.append(paragraph)

                    attributes = {}
                    if self.show_description:
                        path = ".//ContentDescription"
                        for node in media_doc.doc.root.findall(path):
                            attributes = node.attrib
                            if attributes.get('audience') == audience:
                                paragraph = B.P(
                                    B.B("Description:"),
                                    B.BR(),
                                    B.P(Doc.get_text(node))
                                )
                                wrapper.append(paragraph)

                    if self.show_label:
                        labels = media_doc.doc.root.findall(".//LabelName")
                        wrapper.append(B.P(B.B("Labels:")))
                        for label in labels:
                            wrapper.append(B.SPAN(f"{Doc.get_text(label)}",
                                           B.BR()))

        return self._report

    def populate_form(self, page, titles=None):
        """Put the fields on the form.

        Pass:
            page - `cdrcgi.HTMLPage` object
            titles - if not None, show the followup page for selecting
                     from multiple matches with the user's title fragment;
                     otherwise, show the report's main request form
        """

        page.form.append(page.hidden_field("debug", self.debug or ""))
        opts = {"titles": titles, "id-label": "CDR ID"}
        opts["id-tip"] = "enter CDR ID"
        self.add_doc_selection_fields(page, **opts)

        LANGUAGE = (
                ("all", "Display English and Spanish Document"),
        )
        fieldset = page.fieldset("Language")
        for value, label in LANGUAGE:
            opts = dict(value=value, label=label, checked=True, onclick=None)
            fieldset.append(page.checkbox("language", **opts))
        page.form.append(fieldset)

        DISPLAY = (
                ("caption", "Image Caption"),
                ("description", "Content Description"),
                ("labels", "Image Labels"),
        )
        fieldset = page.fieldset("Display Options")
        for value, label in DISPLAY:
            opts = dict(value=value, label=label, checked=True, onclick=None)
            fieldset.append(page.checkbox("show", **opts))
        page.form.append(fieldset)

    def add_doc_selection_fields(self, page, **kwopts):
        """
        Display the fields used to specify which document should be
        selected for a report, using one of several methods:

            * by document ID
            * by document title

        There are two branches taken by this method. If the user has
        elected to select a document by title, and the document
        title fragment matches more than one document, then a follow-up
        page is presented on which the user selects one of the documents
        and re-submits the report request. Otherwise, the user is shown
        options for choosing a selection method, which in turn displays
        the fields appropriate to that method dynamically. We also add
        JavaScript functions to handle the dynamic control of field display.

        Pass:
            page     - Page object on which to show the fields
            titles   - an optional array of document Title objects
            id-label - optional string for the CDR ID field (defaults
                       to "CDR ID" but can be overridden, for example,
                       to say "CDR ID(s)" if multiple IDs are accepted)
            id-tip   - optional string for the CDR ID field for popup
                       help (e.g., "separate multiple IDs by spaces")

        Return:
            nothing (the form object is populated as a side effect)
        """

        # --------------------------------------------------------------
        # Show the second stage in a cascading sequence of the form if we
        # have invoked this method directly from build_tables(). Widen
        # the form to accomodate the length of the title substrings
        # we're showing.
        # --------------------------------------------------------------
        titles = kwopts.get("titles")
        if titles:
            page.form.append(page.hidden_field("selection_method", "id"))
            # page.form.append(page.hidden_field("format", self.format))
            fieldset = page.fieldset("Choose Summary")
            page.add_css("fieldset { width: 600px; }")
            for t in titles:
                opts = dict(label=t.display, value=t.id, tooltip=t.tooltip,
                            onclick=None)
                fieldset.append(page.radio_button("cdr-id", **opts))
            page.form.append(fieldset)
            self.new_tab_on_submit(page)

        else:
            # Fields for the original form.
            fieldset = page.fieldset("Selection Method")
            methods = "CDR ID", "Summary Title"
            checked = False
            for method in methods:
                value = method.split()[-1].lower()
                opts = dict(label=f"By {method}", value=value, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
                checked = True
            page.form.append(fieldset)

            fieldset = page.fieldset("Summary ID")
            fieldset.set("class", "by-id-block")
            label = kwopts.get("id-label", "CDR ID")
            opts = dict(label=label, tooltip=kwopts.get("id-tip"))
            fieldset.append(page.text_field("cdr-id", **opts))
            page.form.append(fieldset)

            fieldset = page.fieldset("Summary Title")
            fieldset.set("class", "by-title-block")
            tooltip = "Use wildcard (%) as appropriate."
            fieldset.append(page.text_field("title", tooltip=tooltip))
            page.form.append(fieldset)
            page.add_script(self.summary_selection_js)

    @property
    def cdr_id(self):
        """Get the entered/selected CDR ID as an integer"""

        if not hasattr(self, "_cdr_id"):
            doc_id = self.fields.getvalue("cdr-id", "").strip()
            try:
                self._cdr_id = Doc.extract_id(doc_id)
            except Exception:
                self.bail("Invalid format for CDR ID")
        return self._cdr_id

    @property
    def show_both_languages(self):
        """Check if display of caption has been selected"""

        if not hasattr(self, "_show_both_languages"):
            self._show_both_languages = True
            show_languages = self.fields.getvalue("language", "")

            if not show_languages == 'all':
                self._show_both_languages = False
        return self._show_both_languages

    @property
    def show_caption(self):
        """Check if display of caption has been selected"""

        if not hasattr(self, "_show_caption"):
            show_caption = self.fields.getvalue("show", "")

            if isinstance(show_caption, list) and 'caption' in show_caption:
                self._show_caption = True
            elif isinstance(show_caption, str) and 'caption' == show_caption:
                self._show_caption = True
            else:
                self._show_caption = False
        return self._show_caption

    @property
    def show_description(self):
        """Check if display of description has been selected"""

        if not hasattr(self, "_show_description"):
            show = self.fields.getvalue("show", "")
            if isinstance(show, list) and 'description' in show:
                self._show_description = True
            elif isinstance(show, str) and 'description' == show:
                self._show_description = True
            else:
                self._show_description = False
        return self._show_description

    @property
    def show_label(self):
        """Check if display of labels has been selected"""

        if not hasattr(self, "_show_label"):
            show_label = self.fields.getvalue("show", "")

            if isinstance(show_label, list) and 'labels' in show_label:
                self._show_label = True
            elif isinstance(show_label, str) and 'labels' == show_label:
                self._show_label = True
            else:
                self._show_label = False
        return self._show_label

    @property
    def cdr_pair(self):
        """Get the corresponding summary id
           EN --> ES or ES --> EN"""

        if not hasattr(self, "_cdr_pair"):
            # CDR ID for English summary entered
            query = self.Query("query_term", "doc_id", "int_val")
            query.where("path = '/Summary/TranslationOf/@cdr:ref'")
            query.where(f"int_val = {self.cdr_id}")
            row = query.execute(self.cursor).fetchone()

            # CDR ID for Spanish summary entered
            if not row:
                query = self.Query("query_term", "doc_id", "int_val")
                query.where("path = '/Summary/TranslationOf/@cdr:ref'")
                query.where(f"doc_id = {self.cdr_id}")
                row = query.execute(self.cursor).fetchone()

            self._cdr_pair = (row[1], row[0]) or None
        return self._cdr_pair

    @property
    def debug(self):
        """True if we're running with increased logging."""

        if not hasattr(self, "_debug"):
            self._debug = True if self.fields.getvalue("debug") else False
        return self._debug

    @property
    def fragment(self):
        """Title fragment for selecting a DIS by title."""

        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("title")
        return self._fragment

    @property
    def loglevel(self):
        """Override to support debug logging."""
        return "DEBUG" if self.debug else self.LOGLEVEL

    @property
    def subtitle(self):
        """What we display under the main banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Allow the report page to override the subtitle."""
        self._subtitle = value

    @property
    def summary_docs(self):
        """Summary documents selected for the report.

        If the user chooses the "by summary title" method for
        selecting which document to use for the report, and the
        fragment supplied matches more than one document, display the
        form a second time so the user can pick the correct document.

        The user selects a single document and we're selecting the
        English or Spanish translation depending on the document ID
        entered/selected.
        """

        if not hasattr(self, "_summary_docs"):
            if self.selection_method == "title":
                if not self.fragment:
                    self.bail("Title fragment is required.")
                titles = self.choice_of_summary_titles
                if not titles:
                    self.bail("No summary matches that title fragment")
                if len(titles) == 1:
                    cdr_ids = self.cdr_pair
                    self._summary_docs = [Summary(self, id) for id in cdr_ids]
                else:
                    self.populate_form(self.form_page, titles)
                    self.form_page.send()
            elif self.selection_method == "id":
                if not self.cdr_id:
                    self.bail("A valid CDR ID is required.")
                cdr_ids = self.cdr_pair
                self._summary_docs = [Summary(self, id) for id in cdr_ids]
            else:
                self.bail("Invalid selection_method")
        return self._summary_docs

    @property
    def choice_of_summary_titles(self):
        """Find the Summary that matches the user's title fragment.

        Note that the user is responsible for adding any non-trailing
        SQL wildcards to the fragment string. If the title is longer
        than 80 characters, truncate with an ellipsis, but add a
        tooltip showing the whole title. We create a local class for
        the resulting list.

        ONLY WORKS IF YOU IMPLEMENT THE `self.fragment` PROPERTY!!!
        """

        if not hasattr(self, "_choice_of_summary_titles"):
            self._choice_of_summary_titles = None
            if hasattr(self, "fragment") and self.fragment:
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
                rows = query.execute(self.cursor).fetchall()
                self._choice_of_summary_titles = []
                for doc_id, title in rows:
                    if len(title) > 80:
                        short_title = title[:77] + "..."
                        docs = SummaryTitle(doc_id, short_title, title)
                    else:
                        docs = SummaryTitle(doc_id, title)
                    self._choice_of_summary_titles.append(docs)
        return self._choice_of_summary_titles

    @property
    def today(self):
        """Today's date object, used in several places."""

        if not hasattr(self, "_today"):
            self._today = date.today()
        return self._today

    @staticmethod
    def table_spacer(table, page):
        """
        Put some space before the table.
        """

        page.add_css("table { margin-top: 25px; }")


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

    @property
    def control(self):
        """Access to the database and the report options."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the summary's CDR document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id)
        return self._doc

    @property
    def display_title(self):
        return f"{self.title}"

    @property
    def id(self):
        """Integer for the PDQ summary's unique CDR document ID."""
        return self.__doc_id

    @property
    def title(self):
        """Official title of the PDQ summary."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("Title"))
            if not self._title:
                self._title = self.doc.title.split(";")[0]
        return self._title

    @property
    def media_link_ids(self):
        """MediaLink IDs for the images of a summary.

           Extracting the MediaID (ref) attribute and converting the
           ID to an integer
        """

        if not hasattr(self, "_media_link_ids"):
            self._media_link_ids = Doc.get_text(self.doc.root.find("MediaID"))
            media_doc_ids = self.doc.root.findall(".//MediaLink/MediaID")
            self._media_link_ids = []
            for media_doc in media_doc_ids:
                doc_id = Doc.extract_id(media_doc.values()[0])
                self._media_link_ids.append(doc_id)

        return self._media_link_ids

    @property
    def media_docs(self):
        """Media documents selected for the report.

        """

        if not hasattr(self, "_media_docs"):
            if not self.media_link_ids:
                message = "Summary selected does not contain images"
                self.control.bail(f"ERROR: {message}")
            self._media_docs = [Media(self, id) for id in self.media_link_ids]
        return self._media_docs


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

        self.__control = control
        self.__doc_id = doc_id

    @property
    def control(self):
        """Access to the database and the report options."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the media's CDR document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.control.session, id=self.id)
        return self._doc

    @property
    def display_title(self):
        return f"{self.title}"

    @property
    def cdr_id_link(self):
        return f"{self.id:d}"

    @property
    def id(self):
        """Integer for the PDQ summary's unique CDR document ID."""
        return self.__doc_id

    @property
    def title(self):
        """Official title of the media document"""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("Title"))
            if not self._title:
                self._title = self.doc.title.split(";")[0]
        return self._title


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
