#!/usr/bin/env python

"""
    Report comparing media docs of a certain type with its Spanish translation

    (adapted from MediaInSummary.py)
"""

from datetime import date, timedelta
from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller


class Control(Controller):
    """Logic manager for report."""

    SUBTITLE = "Media Images Report"
    LOGNAME = "MediaLanguageCompare"
    DIAGNOSIS_PATH = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
    CATEGORY_PATH = "/Media/MediaContent/Categories/Category"
    METHODS = "Search", "CDR ID", "Media Title"
    METHOD_VALUES = {method.split()[-1].lower() for method in METHODS}
    AUDIENCES = dict(Patients="Patient", Health_professionals="HP")
    LANGUAGE = (
        ("en", "Display English only"),
        ("es", "Display Spanish only"),
        ("all", "Display English and Spanish"),
    )
    LANGUAGE_CODES = dict(en="English", es="Spanish")
    DISPLAY_OPTIONS = (
        ("caption", "Image Caption"),
        ("description", "Content Description"),
        ("labels", "Image Labels"),
    )
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

        # Add followup title-selection block if invoked recursively.
        if self.titles:
            page.form.append(page.hidden_field("selection_method", "id"))
            fieldset = page.fieldset("Choose Media Doc")
            for title in self.titles:
                opts = dict(
                    label=title.display,
                    value=title.id,
                    tooltip=title.tooltip,
                )
                fieldset.append(page.radio_button("cdr-id", **opts))
            page.form.append(fieldset)

        # Otherwise, this is a fresh form.
        else:

            # Have the user pick the Media document selection method.
            fieldset = page.fieldset("Selection Method")
            for method in self.METHODS:
                value = method.split()[-1].lower()
                checked = value == self.selection_method
                opts = dict(label=f"By {method}", value=value, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
            page.form.append(fieldset)

            # Add the field for choosing a single document by ID.
            fieldset = page.fieldset("Media ID")
            fieldset.set("class", "by-id-block usa-fieldset")
            opts = dict(
                label="CDR ID",
                tooltip="Enter CDR ID",
                value=self.cdr_id
            )
            fieldset.append(page.text_field("cdr-id", **opts))
            page.form.append(fieldset)

            # Add the field for a document title fragment.
            fieldset = page.fieldset("Media Title")
            fieldset.set("class", "by-title-block usa-fieldset")
            tooltip = "Use wildcard (%) as appropriate."
            opts = dict(tooltip=tooltip, value=self.fragment)
            fieldset.append(page.text_field("title", **opts))
            page.form.append(fieldset)

        # Add options for filtering by diagnoses and/or categories.
        fieldset = page.fieldset("Report Filtering")
        fieldset.set("class", "by-search-block usa-fieldset")
        opts = dict(
            options=["all"]+self.diagnoses,
            multiple=True,
            default=self.diagnosis,
        )
        fieldset.append(page.select("diagnosis", **opts))
        opts = dict(
            options=["all"]+self.categories,
            multiple=True,
            default=self.category,
        )
        opts["options"] = ["all"] + self.categories
        fieldset.append(page.select("category", **opts))
        page.form.append(fieldset)

        # Fields for filtering by processing status dates.
        fieldset = page.fieldset("Processing Status Date Range")
        fieldset.set("class", "by-search-block usa-fieldset")
        fieldset.append(page.date_field("start_date", value=self.start))
        fieldset.append(page.date_field("end_date", value=self.end))
        page.form.append(fieldset)

        # Fieldset for language selection.
        fieldset = page.fieldset("Language")
        fieldset.set("class", "by-search-block usa-fieldset")
        for value, label in self.LANGUAGE:
            opts = dict(value=value, label=label)
            opts["checked"] = value == self.languages
            fieldset.append(page.radio_button("language", **opts))
        page.form.append(fieldset)

        # Fieldset for display options.
        fieldset = page.fieldset("Display Options")
        for value, label in self.DISPLAY_OPTIONS:
            opts = dict(value=value, label=label)
            opts["checked"] = value in self.display
            fieldset.append(page.checkbox("show", **opts))
        page.form.append(fieldset)

        # Fieldset for audience options.
        values = (
            ("all", "Display Patient and HP"),
            ("Health_professionals", "Display HP only"),
            ("Patients", "Display Patient only"),
        )
        current = self.audiences[0] if len(self.audiences) == 1 else "all"
        fieldset = page.fieldset("Audience Display")
        for value, label in values:
            opts = dict(value=value, label=label)
            opts["checked"] = value == current
            fieldset.append(page.radio_button("audience", **opts))
        page.form.append(fieldset)

        # Add client-side scripting and a hidden debug field.
        page.form.append(page.hidden_field("debug", self.debug or ""))
        page.head.append(page.B.SCRIPT(src="/js/MediaLanguageCompare.js"))

    def show_report(self):
        """Send the report back to the browser."""

        if self.pairs:
            self.send_page(self.report)
        message = None
        if self.selection_method == "id":
            message = "No CDR ID provided."
        elif self.selection_method == "title":
            if not self.fragment:
                message = "No title fragment specified."
            elif not self.titles:
                message = f"No matching documents found for {self.fragment!r}."
        else:
            message = "No documents match the search criteria."
        if message:
            self.alerts.append(dict(message=message, type="warning"))
        self.show_form()

    @cached_property
    def audiences(self):
        """Check which audience(s) to display """

        audiences = self.fields.getvalue("audience") or "Patients"
        if audiences in self.AUDIENCES:
            return [audiences]
        return list(self.AUDIENCES)

    @cached_property
    def categories(self):
        """ID/name tuples of the category terms for the form picklist."""

        query = self.Query("query_term", "value").order("value").unique()
        query.where("path = '/Media/MediaContent/Categories/Category'")
        query.where("value <> ''")
        return [row.value for row in query.execute(self.cursor).fetchall()]

    @cached_property
    def category(self):
        """Categories selected by the user for filtering the report."""

        categories = self.fields.getlist("category")
        if "all" in categories:
            categories = []
        self.logger.info("categories selected: %s", categories)
        return categories

    @cached_property
    def category_names(self):
        """Display the category filtering selected for the report."""

        if not self.category:
            return "All Categories"
        return ", ".join(sorted(self.category))

    @cached_property
    def cdr_id(self):
        """Get the entered/selected CDR ID as an integer"""

        doc_id = self.fields.getvalue("cdr-id", "").strip()
        if not doc_id:
            return None
        try:
            return Doc.extract_id(doc_id)
        except Exception:
            self.bail("Unable to extract CDR ID")

    @cached_property
    def debug(self):
        """True if we're running with increased logging."""
        return True if self.fields.getvalue("debug") else False

    @cached_property
    def diagnoses(self):
        """ID/name tuples of the diagnosis terms for the form picklist."""

        query = self.Query("query_term t", "t.doc_id", "t.value").unique()
        query.order("t.value")
        query.join("query_term m", "m.int_val = t.doc_id")
        query.where("t.path = '/Term/PreferredName'")
        query.where(query.Condition("m.path", self.DIAGNOSIS_PATH))
        return [tuple(row) for row in query.execute(self.cursor).fetchall()]

    @cached_property
    def diagnosis(self):
        """Diagnoses selected by the user for filtering the report."""

        diagnoses = []
        values = self.fields.getlist("diagnosis")
        if "all" not in values:
            try:
                for value in values:
                    diagnoses.append(int(value))
            except Exception:
                self.bail()
        self.logger.info("diagnoses selected: %s", diagnoses)
        return diagnoses

    @cached_property
    def diagnosis_names(self):
        """Display the diagnosis filtering selected for the report."""

        if not self.diagnosis:
            return "All Diagnoses"
        names = []
        diagnoses = dict(self.diagnoses)
        try:
            for id in self.diagnosis:
                names.append(diagnoses[id])
        except Exception:
            self.bail()
        return ", ".join(sorted(names))

    @cached_property
    def display(self):
        """Display options selected by the user (or defaulted)."""

        if self.request == self.SUBMIT:
            return self.fields.getlist("show")
        else:
            return "caption", "description"

    @cached_property
    def end(self):
        """End of the date range for the report."""

        value = self.parse_date(self.fields.getvalue("end_date"))
        if not value:
            value = date.today()
        self.logger.info("end date selected: %s", value)
        return value

    @cached_property
    def fragment(self):
        """Title fragment for selecting a Media by title."""
        return self.fields.getvalue("title", "").strip()

    @cached_property
    def languages(self):
        """Check which languages to display """
        return self.fields.getvalue("language", "all")

    @cached_property
    def loglevel(self):
        """Override to support debug logging."""
        return "DEBUG" if self.debug else self.LOGLEVEL

    @cached_property
    def pairs(self):
        """Pairs of CDR IDs for matching English and Spanish documents.

        In the degenerate case, in which the user has elected to display
        only Media documents for a single language, the "pairs" will
        each contain only a single CDR ID.

        TODO: We're ignoring selected documents which have more than
        one matching Media documents in the other language. Fix?

        We do detect the condition in which the user has selected a
        specific English Media document for which there is no Spanish
        equivalent, but did not specify the English-only version of
        the report. In that case we abort with an error message.
        """

        pairs = set()
        for id in self.selected:
            query = self.Query("query_term", "int_val")
            query.where("path = '/Media/TranslationOf/@cdr:ref'")
            query.where(f"doc_id = {id}")
            rows = query.execute(self.cursor).fetchall()
            if rows:
                if self.languages == "all":
                    pairs.add((rows[0].int_val, id))
                elif self.languages == "es":
                    pairs.add((id,))
                else:
                    pairs.add((rows[0].int_val))
            elif self.languages == "en":
                pairs.add((id))
            else:
                query = self.Query("query_term", "doc_id")
                query.where("path = '/Media/TranslationOf/@cdr:ref'")
                query.where(f"int_val = {id}")
                rows = query.execute(self.cursor).fetchall()
                if rows:
                    if self.languages == "all":
                        pairs.add((id, rows[0].doc_id))
                    else:
                        pairs.add((rows[0].doc_id,))
                elif self.selection_method == "id":
                    self.bail(f"CDR{id} has no Spanish translation")
        return sorted(pairs)

    @cached_property
    def report(self):
        """DOM object for the report."""

        # Initialize the DOM object for the report page.
        B = self.HTMLPage.B
        head = B.HEAD(
            B.META(charset="utf-8"),
            B.TITLE(self.TITLE),
            B.LINK(href="/favicon.ico", rel="icon"),
            B.STYLE(self.CSS)
        )
        h1 = B.H1(B.DIV(self.SUBTITLE))
        if self.languages == "all":
            h1.append(B.DIV("Language Comparison"))
            classes = "double"
        else:
            language = self.LANGUAGE_CODES[self.languages]
            h1.append(B.DIV(f"Showing Only {language} Media"))
            classes = "single"
        h1.append(B.DIV(str(date.today())))
        header = B.E("header", h1)
        body = B.BODY(header, B.CLASS(classes))
        report = B.HTML(head, body)

        # Show how the Media document(s) were selected.
        show_search_criteria = self.selection_method == "search"
        if self.selection_method == "title" and not self.fragment:
            show_search_criteria = True
        if show_search_criteria:
            header.append(B.H3("Search Criteria"))
            if self.category:
                header.append(B.P(B.B("Category: "), self.category_names))
            if self.diagnosis:
                header.append(B.P(B.B("Diagnosis: "), self.diagnosis_names))
            if self.start:
                range = f"{self.start} - {self.end}"
                header.append(B.P(B.B("Date Range: ", range)))
        else:
            header.append(B.P(B.B(f"Media selected: CDR{self.cdr_id}")))

        # Walk through the pairs of Media document IDs.
        script = "/cgi-bin/cdr/GetCdrImage.py"
        width = 400 if self.languages == "all" else 800
        for pair in self.pairs:

            # Create a wrapper to keep the pairs aligned.
            pair_wrapper = B.DIV(B.CLASS("pair-wrapper"))
            body.append(pair_wrapper)

            # Loop through the IDs for the two languages.
            for id in pair:

                # Load the object for the Media document.
                media = Media(self, id)

                # Create a wrapper for this document's information.
                wrapper = B.DIV(B.CLASS("lang-wrapper"))
                pair_wrapper.append(wrapper)

                # Identify the document.
                wrapper.append(B.H3(media.language))
                wrapper.append(B.H3(f"CDR{media.id} - {media.title}"))

                # Show the image.
                src = f"{script}?id=CDR{media.id}-{width}.jpg"
                href = src.replace(f"-{width}", "")
                wrapper.append(B.A(B.IMG(src=src), href=href))

                # Show the caption(s) if requested.
                if "caption" in self.display:
                    for node in media.doc.root.findall(".//MediaCaption"):
                        audience = node.get("audience")
                        if audience in self.audiences:
                            audience = self.AUDIENCES[audience]
                            wrapper.append(B.H3(f"Caption ({audience})"))
                            wrapper.append(B.P(Doc.get_text(node) or "None"))

                # Show the description(s) if requested.
                if "description" in self.display:
                    path = ".//ContentDescription"
                    for node in media.doc.root.findall(path):
                        audience = node.get("audience")
                        if audience in self.audiences:
                            audience = self.AUDIENCES[audience]
                            wrapper.append(B.H3(f"Description ({audience})"))
                            wrapper.append(B.P(Doc.get_text(node) or "None"))

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
        """Tamp down on the number of new browser tabs opened."""
        return [self.SUBMIT] if self.request and not self.titles else []

    @cached_property
    def selected(self):
        """CDR document IDs identified by the user's selection method."""

        # If the user identified a specific document by ID, this is easy.
        if self.selection_method == "id":
            return [self.cdr_id] if self.cdr_id else []

        # If the user's title fragment matched a single document, use it.
        if self.selection_method == "title":
            return [self.titles[0].id] if len(self.titles) == 1 else []

        # Build a query using the user's filtering criteria.
        c_path = '/Media/MediaContent/Categories/Category'
        d_path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'
        i_path = '/Media/PhysicalMedia/ImageData/ImageEncoding'
        s_path = '/Media/ProcessingStatuses/ProcessingStatus'
        sd_path = f'{s_path}/ProcessingStatusDate'
        query = self.Query("query_term i", "i.doc_id").unique()
        query.where(f"i.path = '{i_path}'")
        if self.category:
            query.join("query_term c", "c.doc_id = i.doc_id")
            query.where(query.Condition("c.path", c_path))
            query.where(query.Condition("c.value", self.category, "IN"))
        if self.diagnosis:
            query.join("query_term d", "d.doc_id = i.doc_id")
            query.where(query.Condition("d.path", d_path))
            query.where(query.Condition("d.int_val", self.diagnosis, "IN"))
        if self.start or self.end:
            query.join("query_term sd", "sd.doc_id = i.doc_id")
            query.where(query.Condition("sd.path", sd_path))
            query.where(query.Condition("sd.node_loc", "%000001", "LIKE"))
            if self.start:
                query.where(query.Condition("sd.value", self.start, ">="))
                if self.end:
                    end = f"{self.end} 23:59:59"
                    query.where(query.Condition("sd.value", end, "<="))

        # Run the query and return the results.
        return [row.doc_id for row in query.execute(self.cursor).fetchall()]

    @cached_property
    def selection_method(self):
        """How does the user want to select media for the report?"""

        method = self.fields.getvalue("selection_method", "title")
        if method not in self.METHOD_VALUES:
            self.bail()
        return method

    @cached_property
    def start(self):
        """Beginning of the date range for the report - default: 1 week."""

        value = self.parse_date(self.fields.getvalue("start_date"))
        if not value:
            value = date.today() - timedelta(weeks=1)
        self.logger.info("start date selected: %s", value)
        return value

    @cached_property
    def titles(self):
        """Find the Media documents that match the user's title fragment."""

        if self.selection_method != "title" or not self.fragment:
            return []

        class MediaTitle:
            def __init__(self, doc_id, display, tooltip=None):
                self.id = doc_id
                self.display = display
                self.tooltip = tooltip
        fragment = f"{self.fragment}%"
        path = "/Media/PhysicalMedia/ImageData/ImageEncoding"
        query = self.Query("active_doc d", "d.id", "d.title")
        query.join("query_term q", "d.id = q.doc_id")
        query.where(query.Condition("q.path", path))
        query.where(query.Condition("d.title", fragment, "LIKE"))
        query.order("d.title")
        choices = []
        for doc_id, title in query.execute(self.cursor).fetchall():
            if len(title) > 80:
                short_title = title[:77] + "..."
                choices.append(MediaTitle(doc_id, short_title, title))
            else:
                choices.append(MediaTitle(doc_id, title))
        return choices


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
    def language(self):
        """English or Spanish."""

        node = self.doc.root.find(".//TranslationOf")
        return "English" if node is None else "Spanish"

    @cached_property
    def title(self):
        """Official title of the media document"""

        title = Doc.get_text(self.doc.root.find("Title"), "").strip()
        return title or self.doc.title.split(";")[0]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
