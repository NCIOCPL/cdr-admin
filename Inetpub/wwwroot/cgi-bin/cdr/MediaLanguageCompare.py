#!/usr/bin/env python

"""
    Report comparing media docs of a certain type with its Spanish translation

    (adapted from MediaInSummary.py)
"""

import datetime
from datetime import date
from cdrapi.docs import Doc
from cdrcgi import Controller
from cdr import URDATE, getSchemaEnumVals
from lxml import html, etree
from lxml.html import builder
from cdr import exNormalize
import sys



class Control(Controller):
    """
    Logic manager for report.
    """

    SUBTITLE = "Media Images Report"
    LOGNAME = "MediaLanguageCompare"
    CSS = "../../stylesheets/MediaLanguageCompare.css"
    DIAGNOSIS_PATH = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
    CATEGORY_PATH = "/Media/MediaContent/Categories/Category"
    MEDIA_SELECTION_METHODS = "id", "title", "search"


    def show_report(self):
        """Send the report back to the browser."""

        report = self.report
        opts = dict(
            pretty_print=True,
            doctype="<!DOCTYPE html>",
            encoding="utf-8",
        )
        sys.stdout.buffer.write(b"Content-type: text/html;charset=utf-8\n\n")
        sys.stdout.buffer.write(html.tostring(report, **opts))
        sys.exit(0)


    def get_int_cdr_id(self, value):
        """
        Convert CDR ID to integer. Exit with an error message on failure.
        """
        if value:
            try:
                return exNormalize(value)[1]
            except:
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
            args = self.SUBTITLE, B.BR(), "Language Comparison", B.BR(), time

            cdrId = self.get_int_cdr_id(self.fields.getvalue("cdr-id"))

            # Display search parameters as part of the report
            # -----------------------------------------------
            search_c = search_d = search_dr = ""
            search = True if self.category or self.diagnosis or self.start\
                          else False
            if search:
                search_hdr = B.P("Search Criteria", id="media-id")
                if self.category:
                    category = ",".join(x for x in self.category)
                    search_c = B.P(B.B("Category: "), f"{category}",
                                                 id="category-id")
                if self.diagnosis:
                    search_d = B.P(B.B("Diagnosis: "),
                                                 f"{self.diagnosis_names}",
                                                 id="diagnosis-id")
                if self.start and self.start is not None:
                    search_dr = B.P(B.B("Date Range: "),
                                                 f"{self.start} - {self.end}",
                                                 id="date-range-id")
                wrapper = body = B.BODY(B.E("header", B.H1(*args)),
                                                 search_hdr,
                                                 search_d, search_c, search_dr)
            else:
                orig_id = B.P(f"Media selected: CDR{cdrId}", id="media-id")
                wrapper = body = B.BODY(B.E("header", B.H1(*args)), orig_id)

            self._report = B.HTML(head, body)

            # Users want to be able to only display the content for a single
            # language.  For that case we created the media_docs pairs with
            # one of the CDR-IDs equal 0 (zero).
            # --------------------------------------------------------------
            media_docs = self.media_docs

            # Sorting documents by CDR-ID of English doc, then the Spanish
            media_docs.sort(key=lambda x: (x[0].id, x[1].id))

            # Creating one column per language
            # --------------------------------
            for media_pair in media_docs:
                # We need to indroduce a wrapper for the language pair
                # to ensure pairs are displayed side-by-side.  Otherwise a
                # floated DIV for English can show up in the Spanish column
                # The parent wrapper allows us to use flexbox.
                # ---------------------------------------------------------
                wrapper_pair = B.DIV(B.CLASS("pair-wrapper"))
                body.append(wrapper_pair)
                for media_doc in media_pair:
                    # Do nothing for the language with CDR-ID=0
                    if media_doc.id == 0:
                        continue

                    path = ".//TranslationOf"
                    lang = Doc.get_text(media_doc.doc.root.find(path))
                    lang = 'Spanish' if lang else 'English'

                    wrapper = B.DIV(B.CLASS("lang-wrapper"))
                    body.append(wrapper)

                    # Display the language and CDR-ID of the document
                    media_lang = B.P(f"{lang}", id=f"media-{lang.lower()}")
                    wrapper.append(media_lang)

                    # Display the media title
                    media_title = media_doc.title
                    media_info = B.P(f"CDR{media_doc.id} - {media_title}",
                                                    B.CLASS("media-title"))
                    wrapper.append(media_info)

                    image = ("/cgi-bin/cdr/GetCdrImage.py?"
                             f"id=CDR{media_doc.id}-400.jpg")
                    full_image = image.replace('-400', '')
                    wrapper.append(B.A(B.IMG(src=image), href=full_image))

                    # Displaying the media caption if required
                    # ----------------------------------------
                    attributes = {}
                    if self.show_caption:
                        path = ".//MediaCaption"
                        captions = media_doc.doc.root.findall(path)
                        for caption in captions:
                            attributes = caption.attrib
                            aud = 'Patient' if attributes.get('audience') \
                                                    == 'Patients' else 'HP'
                            if attributes.get('audience') in self.audiences:
                                wrapper.append(B.P(
                                    B.B(f"Caption - {aud}:")))
                                wrapper.append(B.P(
                                    Doc.get_text(caption, "None")))

                    # Displaying the media description if required
                    # --------------------------------------------
                    attributes = {}
                    if self.show_description:
                        path = ".//ContentDescription"
                        descriptions = media_doc.doc.root.findall(path)
                        for description in descriptions:
                            attributes = description.attrib
                            aud = 'Patient' if attributes.get('audience') \
                                                    == 'Patients' else 'HP'
                            if attributes.get('audience') in self.audiences:
                                wrapper.append(B.P(
                                    B.B(f"Description - {aud}:")))
                                wrapper.append(B.P(
                                    Doc.get_text(description, "None")))

                    if self.show_label:
                        labels = media_doc.doc.root.findall(".//LabelName")
                        wrapper.append(B.P(B.B("Labels:")))
                        for label in labels:
                            wrapper.append(B.SPAN(f"{Doc.get_text(label)}",
                                           B.BR()))

                    wrapper_pair.append(wrapper)
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
        opts = { "titles": titles, "id-label": "CDR ID" }
        opts["id-tip"] = "enter CDR ID"
        self.add_doc_selection_fields(page, **opts)

        # Add Report Filtering options
        # ----------------------------
        fieldset = page.fieldset("Report Filtering")
        fieldset.set("class", "by-search-block")
        opts = dict(options=["all"]+self.diagnoses, multiple=True)
        fieldset.append(page.select("diagnosis", **opts))
        opts["options"] = ["all"] + self.categories
        fieldset.append(page.select("category", **opts))
        page.form.append(fieldset)

        # Fieldset for date range
        # -----------------------
        fieldset = page.fieldset("Date Range")
        fieldset.set("class", "by-search-block")
        fieldset.append(page.date_field("start_date", value=self.start))
        fieldset.append(page.date_field("end_date", value=self.end))
        page.form.append(fieldset)


        # Fieldset for language selection
        # -------------------------------
        LANGUAGE = (
            ("en", "Display English only"),
            ("es", "Display Spanish only"),
            ("all", "Display English and Spanish"),
        )
        fieldset = page.fieldset("Language")
        fieldset.set("class", "by-search-block")
        for value, label in LANGUAGE:
            opts = dict(value=value, label=label, onclick=None)
            opts["checked"] = value == self.languages
            fieldset.append(page.radio_button("language", **opts))
        page.form.append(fieldset)

        # Fieldset for display options
        # ----------------------------
        DISPLAY = (
            ("caption", "Image Caption"),
            ("description", "Content Description"),
            ("labels", "Image Labels"),
        )
        fieldset = page.fieldset("Display Options")
        for value, label in DISPLAY:
            opts = dict(value=value, label=label, onclick=None)
            opts["checked"] = value in self.display_options
            fieldset.append(page.checkbox("show", **opts))
        page.form.append(fieldset)

        # Fieldset for audience options
        # -----------------------------
        AUDIENCE = (
            ("all", "Display Patient and HP"),
            ("Health_professionals", "Display HP only"),
            ("Patients", "Display Patient only"),
        )
        current = self.audiences[0] if len(self.audiences) == 1 else "all"
        fieldset = page.fieldset("Audience Display")
        for value, label in AUDIENCE:
            opts = dict(value=value, label=label, onclick=None)
            opts["checked"] = value == current
            fieldset.append(page.radio_button("audience", **opts))
        page.form.append(fieldset)


    def add_doc_selection_fields(self, page, **kwopts):
        """
        Display the fields used to specify which document should be
        selected for a report, using one of several methods:

            * by search parameters
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

        #--------------------------------------------------------------
        # Show the second stage in a cascading sequence of the form if we
        # have invoked this method directly from build_tables(). Widen
        # the form to accomodate the length of the title substrings
        # we're showing.
        #--------------------------------------------------------------
        titles = kwopts.get("titles")
        if titles:
            page.form.append(page.hidden_field("selection_method", "id"))
            fieldset = page.fieldset("Choose Media Doc")
            page.add_css("fieldset { width: 600px; }")
            for t in titles:
                opts = dict(label=t.display, value=t.id, tooltip=t.tooltip,
                            onclick=None)
                fieldset.append(page.radio_button("cdr-id", **opts))
            page.form.append(fieldset)
            page.add_script(self.media_selection_js)
            self.new_tab_on_submit(page)

        else:
            # Fields for the original form.
            fieldset = page.fieldset("Selection Method")
            methods = "Search", "CDR ID", "Media Title"
            checked = False
            for method in methods:
                value = method.split()[-1].lower()
                opts = dict(label=f"By {method}", value=value, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
                checked = True
            page.form.append(fieldset)

            fieldset = page.fieldset("Media ID")
            fieldset.set("class", "by-id-block")
            label = kwopts.get("id-label", "CDR ID")
            opts = dict(label=label, tooltip=kwopts.get("id-tip"))
            fieldset.append(page.text_field("cdr-id", **opts))
            page.form.append(fieldset)

            fieldset = page.fieldset("Media Title")
            fieldset.set("class", "by-title-block")
            tooltip = "Use wildcard (%) as appropriate."
            fieldset.append(page.text_field("title", tooltip=tooltip))
            page.form.append(fieldset)
            page.add_script(self.media_selection_js)


    @property
    def cdr_id(self):
        """Get the entered/selected CDR ID as an integer"""

        if not hasattr(self, "_cdr_id"):
            doc_id = self.fields.getvalue("cdr-id", "").strip()
            try:
                self._cdr_id = Doc.extract_id(doc_id)
            except:
                self.bail("Unable to extract CDR ID")
        return self._cdr_id


    @property
    def display_options(self):
        """Display options selected by the user (or defaulted)."""

        if not hasattr(self, "_display_options"):
            if self.request and self.request == self.SUBMIT:
                self._display_options = self.fields.getlist("show")
            else:
                self._display_options = ["caption", "description"]
        return self._display_options


    @property
    def media_selection_js(self):
        "Local JavaScript to manage sections of the form dynamically."

        return """\
function check_set(name, val) {
    var all_selector = "#" + name + "-all";
    var ind_selector = "#" + name + "-set .ind";
    if (val == "all") {
        if (jQuery(all_selector).prop("checked"))
            jQuery(ind_selector).prop("checked", false);
        else
            jQuery(all_selector).prop("checked", true);
    }
    else if (jQuery(ind_selector + ":checked").length > 0)
        jQuery(all_selector).prop("checked", false);
    else
        jQuery(all_selector).prop("checked", true);
}
/* function check_board(board) { check_set("board", board); } */
function check_selection_method(method) {
    switch (method) {
        case 'id':
            jQuery('.by-search-block').hide();
            jQuery('.by-id-block').show();
            jQuery('.by-title-block').hide();
            break;
        case 'search':
            jQuery('.by-search-block').show();
            jQuery('.by-id-block').hide();
            jQuery('.by-title-block').hide();
            break;
        case 'title':
            jQuery('.by-search-block').hide();
            jQuery('.by-id-block').hide();
            jQuery('.by-title-block').show();
            break;
    }
}
jQuery(function() {
    var method = jQuery("input[name='selection_method']:checked").val();
    // check_selection_method(method);
    check_selection_method('title');
}); """


    def get_media_pair(self, doc_id):
        """Get the corresponding media id for a single document
           EN --> ES or ES --> EN
           If the report is run for a single language only, set
           the doc_id = 0 for the other language """

        isSpanish = False
        isEnglish = False
        # CDR ID for English summary entered
        query = self.Query("query_term", "doc_id", "int_val")
        query.where("path = '/Media/TranslationOf/@cdr:ref'")
        query.where(f"int_val = {doc_id}")
        row = query.execute(self.cursor).fetchone()
        if row: isEnglish = True

        # CDR ID for Spanish summary entered
        if not row:
            query = self.Query("query_term", "doc_id", "int_val")
            query.where("path = '/Media/TranslationOf/@cdr:ref'")
            query.where(f"doc_id = {doc_id}")
            row = query.execute(self.cursor).fetchone()
            if row: isSpanish = True
        if not isSpanish: isEnglish = True

        if self.languages == 'en' and isEnglish:
            _media_pair = (doc_id, 0)
        elif self.languages == 'es' and isSpanish:
            _media_pair = (0, doc_id)
        else:
            try:
                _media_pair = (row[1], row[0])
            except:
                _media_pair = None
                self.logger.info(f"No Spanish translation exists for CDR{id}"
                                 " - excluded")
        return _media_pair


    @property
    def cdr_pair(self):
        """Get the corresponding summary id
           EN --> ES or ES --> EN"""

        if not hasattr(self, "_cdr_pair"):
            # CDR ID for English summary entered
            query = self.Query("query_term", "doc_id", "int_val")
            query.where("path = '/Media/TranslationOf/@cdr:ref'")
            query.where(f"int_val = {self.cdr_id}")
            row = query.execute(self.cursor).fetchone()

            # CDR ID for Spanish summary entered
            if not row:
                query = self.Query("query_term", "doc_id", "int_val")
                query.where("path = '/Media/TranslationOf/@cdr:ref'")
                query.where(f"doc_id = {self.cdr_id}")
                row = query.execute(self.cursor).fetchone()

            try:
                self._cdr_pair = (row[1], row[0]) or None
            except:
                self.bail(f"Error: CDR{self.cdr_id} is not a Media document"
                           " or a Spanish translation does not exist")
        return self._cdr_pair


    @property
    def categories(self):
        """ID/name tuples of the category terms for the form picklist."""

        query = self.Query("query_term", "value").order("value").unique()
        query.where("path = '/Media/MediaContent/Categories/Category'")
        query.where("value <> ''")
        return [row.value for row in query.execute(self.cursor).fetchall()]

    @property
    def category(self):
        """Categories selected by the user for filtering the report."""

        if not hasattr(self, "_category"):
            self._category = self.fields.getlist("category")
            if "all" in self._category:
                self._category = []
            self.logger.info("categories selected: %s", self._category)
        return self._category

    @property
    def category_names(self):
        """Display the category filtering selected for the report."""

        if not self.category:
            return "All Categories"
        return ", ".join(sorted(self.category))


    @property
    def diagnoses(self):
        """ID/name tuples of the diagnosis terms for the form picklist."""

        query = self.Query("query_term t", "t.doc_id", "t.value").unique()
        query.order("t.value")
        query.join("query_term m", "m.int_val = t.doc_id")
        query.where("t.path = '/Term/PreferredName'")
        query.where(query.Condition("m.path", self.DIAGNOSIS_PATH))
        return [tuple(row) for row in query.execute(self.cursor).fetchall()]

    @property
    def diagnosis(self):
        """Diagnoses selected by the user for filtering the report."""

        if not hasattr(self, "_diagnosis"):
            self._diagnosis = []
            diagnoses = self.fields.getlist("diagnosis")
            if "all" not in diagnoses:
                try:
                    for diagnosis in diagnoses:
                        self._diagnosis.append(int(diagnosis))
                except:
                    self.bail()
            self.logger.info("diagnoses selected: %s", self._diagnosis)
        return self._diagnosis

    @property
    def diagnosis_names(self):
        """Display the diagnosis filtering selected for the report."""

        if not self.diagnosis:
            return "All Diagnoses"
        names = []
        diagnoses = dict(self.diagnoses)
        try:
            for id in self.diagnosis:
                names.append(diagnoses[id])
        except:
            self.bail()
        return ", ".join(sorted(names))

    @property
    def start(self):
        """Beginning of the date range for the report - default: 1 week."""
        if not hasattr(self, "_start"):
            days_delta = datetime.timedelta(weeks=1)
            start = self.started - days_delta
            start_date = start.strftime("%Y-%m-%d")
            self._start = self.fields.getvalue("start_date") or start_date
        else:
            self._start = self.fields.getvalue("start_date")
        self.logger.info(f"start date selected: {self._start}")
        return self._start


    @property
    def end(self):
        """End of the date range for the report."""
        if not hasattr(self, "_end"):
            default = self.started.strftime("%Y-%m-%d")
            self._end = self.fields.getvalue("end_date") or default
        else:
            self._end = self.fields.getvalue("end_date")
        self.logger.info(f"end date selected: {self._end}")
        return self._end


    @property
    def languages(self):
        """Check which languages to display """
        if not hasattr(self, "_languages"):
            self._languages = self.fields.getvalue("language", "all")
        return self._languages


    @property
    def audiences(self):
        """Check which audience to display """

        if not hasattr(self, "_audiences"):
            all = ["Patients", "Health_professionals"]
            audiences = self.fields.getvalue("audience") or all[0]
            if audiences in all:
                self._audiences = [audiences]
            else:
                self._audiences = all
        return self._audiences


    @property
    def show_caption(self):
        """Check if display of caption has been selected"""

        if not hasattr(self, "_show_caption"):
            self._show_caption = "caption" in self.display_options
        return self._show_caption


    @property
    def show_description(self):
        """Check if display of description has been selected"""

        if not hasattr(self, "_show_description"):
            self._show_description = "description" in self.display_options
        return self._show_description


    @property
    def show_label(self):
        """Check if display of labels has been selected"""

        if not hasattr(self, "_show_label"):
            self._show_label = "labels" in self.display_options
        return self._show_label


    @property
    def debug(self):
        """True if we're running with increased logging."""

        if not hasattr(self, "_debug"):
            self._debug = True if self.fields.getvalue("debug") else False
        return self._debug

    @property
    def fragment(self):
        """Title fragment for selecting a Media by title."""

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
    def media_docs(self):
        """Media documents selected for the report.

        If the user chooses the "by media title" method for
        selecting which document to use for the report, and the
        fragment supplied matches more than one document, display the
        form a second time so the user can pick the correct document.

        The user selects a single document and we're selecting the
        English or Spanish translation depending on the document ID
        entered/selected.

        Since the search options return a list of media pairs we are
        inserting the single-pair media docs for the "title" and "id"
        methods inside another list.
        """

        if not hasattr(self, "_media_docs"):
            if self.selection_method == "title" and self.fragment:
                titles = self.choice_of_media_titles

                if not titles:
                    self.bail("No media matches that title fragment")
                if len(titles) == 1:
                    cdr_ids = self.cdr_pair

                    self._media_docs = [[Media(self, id) for id in cdr_ids]]
                else:
                    self.populate_form(self.form_page, titles)
                    self.form_page.send()
            elif self.selection_method == "id":
                if not self.cdr_id:
                    self.bail("A valid CDR ID is required.")

                cdr_ids = self.cdr_pair
                self._media_docs = [[Media(self, id) for id in cdr_ids]]
            else:

                c_path = '/Media/MediaContent/Categories/Category'
                d_path = '/Media/MediaContent/Diagnoses/Diagnosis'
                i_path = '/Media/PhysicalMedia/ImageData/ImageEncoding'
                s_path = '/Media/ProcessingStatuses/ProcessingStatus'
                sd_path = f'{s_path}/ProcessingStatusDate'
                query = self.Query("query_term q", "q.doc_id")
                query.where(f"q.path = '{i_path}'")
                if self.category:
                    c_val = [x for x in self.category]
                    query.join("query_term c", "c.doc_id = q.doc_id")
                    query.where(query.Condition("c.path", c_path))
                    query.where(query.Condition("c.value", c_val, "IN"))
                if self.diagnosis:
                    d_val = [x for x in self.diagnosis_names.split(',')]
                    query.join("query_term d", "d.doc_id = q.doc_id")
                    query.where(query.Condition("d.path", d_path))
                    query.where(query.Condition("d.value", d_val, "IN"))
                if self.start:
                    query.join("query_term sd", "sd.doc_id = q.doc_id")
                    query.where(query.Condition("sd.path", sd_path))
                    query.where(query.Condition("sd.node_loc", "%000001",
                                                "LIKE"))
                    query.where(query.Condition("sd.value", self.start, ">="))
                #if control.end:
                    query.where(query.Condition("sd.value", self.end, "<="))

                rows = query.execute(self.cursor).fetchall()
                if not rows:
                    self.bail(f"No documents exist for the given search "
                               "parameters and selected range of "
                               "{self.start} and {self.end}")

                # For the version of the report displaying both languages,
                # we skip documents without Spanish translation and we only
                # include unique pairs, i.e. if the query selected both, the
                # English and the Spanish ids separately, only one pair gets
                # created for these two entries.
                all_media_pairs = []
                self._media_docs = []

                for row, *_ in rows:
                    media_pair = self.get_media_pair(row)
                    if media_pair and media_pair not in all_media_pairs:
                        all_media_pairs.append(media_pair)
                        self._media_docs.append([Media(self, id)
                                                    for id in media_pair])

                # We created a list of media object pairs, one pair for
                # each document returned in the SQL query.  Depending on the
                # type of report (en, es, or all) we exclude the documents
                # without Spanish translation when running the report for
                # both languages and we're setting the CDR-ID=0 for one of
                # the languages when running for en or es only. However, the
                # pairs not to be included are still part of this list.
                # Here, we're stripping out those extra pairs (pairs for
                # which one of the CDR-ID is not 0.
                # We then sort the remaining list by CDR-ID.
                if self.languages == 'en':
                    english_docs = [x for x in self._media_docs if x[1].id==0]
                    self._media_docs = english_docs
                elif self.languages == 'es':
                    spanish_docs = [x for x in self._media_docs if x[0].id==0]
                    self._media_docs = spanish_docs

        return self._media_docs


    @property
    def selection_method(self):
        """How does the user want to select media for the report?"""

        if not hasattr(self, "_selection_method"):
            name = "selection_method"
            self._selection_method = self.fields.getvalue(name, "title")
            if self._selection_method not in self.MEDIA_SELECTION_METHODS:
                self.bail()
        return self._selection_method


    @property
    def choice_of_media_titles(self):
        """Find the Media documents that match the user's title fragment.

        Note that the user is responsible for adding any non-trailing
        SQL wildcards to the fragment string. If the title is longer
        than 80 characters, truncate with an ellipsis, but add a
        tooltip showing the whole title. We create a local class for
        the resulting list.

        ONLY WORKS IF YOU IMPLEMENT THE `self.fragment` PROPERTY!!!
        """

        if not hasattr(self, "_choice_of_media_titles"):
            self._choice_of_media_titles = None
            if hasattr(self, "fragment") and self.fragment:
                class MediaTitle:
                    def __init__(self, doc_id, display, tooltip=None):
                        self.id = doc_id
                        self.display = display
                        self.tooltip = tooltip
                fragment = f"{self.fragment}%"
                q_path = "/Media/PhysicalMedia/ImageData/ImageEncoding"
                query = self.Query("active_doc d", "d.id", "d.title")
                query.join("doc_type t", "t.id = d.doc_type")
                query.join("query_term q", "d.id = q.doc_id")
                query.where(query.Condition("q.path", q_path))
                query.where("t.name = 'Media'")
                query.where(query.Condition("d.title", fragment, "LIKE"))
                query.order("d.title")
                rows = query.execute(self.cursor).fetchall()
                self._choice_of_media_titles = []

                for doc_id, title in rows:
                    if len(title) > 80:
                        short_title = title[:77] + "..."
                        docs = MediaTitle(doc_id, short_title, title)
                    else:
                        docs = MediaTitle(doc_id, title)
                    self._choice_of_media_titles.append(docs)
        return self._choice_of_media_titles


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


# class Summary:
#     """
#     Represents one CDR Summary document.
#
#     Attributes:
#         id       -  CDR ID of summary document
#         title    -  title of summary (from title column of all_docs table)
#         control  -  object holding request parameters for report
#         media    -  list of MediaLink IDs for the summary
#     """
#
#     def __init__(self, control, doc_id):
#         """Remember the caller's values.
#
#         Pass:
#             control - access to the database and the report options
#             doc_id - integer for the PDQ summary's unique CDR document ID
#         """
#
#         self.__control = control
#         self.__doc_id = doc_id
#
#     @property
#     def control(self):
#         """Access to the database and the report options."""
#         return self.__control
#
#     @property
#     def doc(self):
#         """`Doc` object for the summary's CDR document."""
#
#         if not hasattr(self, "_doc"):
#             self._doc = Doc(self.control.session, id=self.id)
#         return self._doc
#
#     @property
#     def display_title(self):
#         return f"{self.title}"
#
#     @property
#     def id(self):
#         """Integer for the PDQ summary's unique CDR document ID."""
#         return self.__doc_id
#
#     @property
#     def title(self):
#         """Official title of the PDQ summary."""
#
#         if not hasattr(self, "_title"):
#             self._title = Doc.get_text(self.doc.root.find("Title"))
#             if not self._title:
#                 self._title = self.doc.title.split(";")[0]
#         return self._title
#
#     @property
#     def media_link_ids(self):
#         """MediaLink IDs for the images of a summary.
#
#            Extracting the MediaID (ref) attribute and converting the ID to an integer
#         """
#
#         if not hasattr(self, "_media_link_ids"):
#             self._media_link_ids = Doc.get_text(self.doc.root.find("MediaID"))
#             media_doc_ids = self.doc.root.findall(".//MediaLink/MediaID")
#             self._media_link_ids = []
#             for media_doc in media_doc_ids:
#                 self._media_link_ids.append(Doc.extract_id(media_doc.values()[0]))
#
#         return self._media_link_ids
#
#
#     @property
#     def media_docs(self):
#         """Media documents selected for the report.
#
#         """
#
#         if not hasattr(self, "_media_docs"):
#             if not self.media_link_ids:
#                 message = "Summary selected does not contain images"
#                 self.control.bail(f"ERROR: {message}")
#             self._media_docs = [Media(self, id) for id in self.media_link_ids]
#         return self._media_docs
#

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
            self._doc = Doc(self.__control.session, id=self.id)
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
