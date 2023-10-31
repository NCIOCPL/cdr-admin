#!/usr/bin/env python

"""Report on demographic information in media documents for images.

This is essentially two reports, one of which selects media image documents,
and the other of which selects summary documents.

The report started out as a request for a "Media Demographic Information"
report. After an inordinate amount of confusion about the requirements,
which didn't seem to match that scope, the truth came out that what was
REALLY wanted was restricted to images.

See https://tracker.nci.nih.gov/browse/OCECDR-5095.
"""

from functools import cached_property
from cdrcgi import Controller, HTMLPage, bail
from cdrapi import db
from cdrapi.docs import Doc, Link
from cdr import Board, getDoctype


class Control(Controller):
    """Top-level logic for the report.
    """

    SUBTITLE = "Image Demographic Information"
    LOGNAME = "image-demographic-information"
    REPORT_TYPES = (("images", "Images"), ("summaries", "Summaries"))
    DEFAULT_REPORT_TYPE = "images"
    SUMMARY_METHODS = (
        ("title", "By Summary Title"),
        ("id", "By CDR ID"),
        ("board", "By PDQ Board"),
        ("type", "By Summary Type"),
    )
    IMAGE_METHODS = (
        ("title", "By Image Title"),
        ("id", "By CDR ID"),
        ("category", "By Image Category"),
    )
    AUDIENCES = dict(
        any="Any",
        hp="Health Professional",
        patient="Patient",
    )
    LANGUAGES = "any", "english", "spanish"
    DEFAULT_LEVEL = 3
    DEMOGRAPHIC_FIELDS = "Age", "Sex", "Race", "Skin Tone", "Ethnicity"

    @cached_property
    def age(self):
        return self.fields.getvalue("age")

    @cached_property
    def audience(self):
        """Health Professional, Patient, or Any."""
        return self.fields.getvalue("audience")

    @cached_property
    def board(self):
        """Which board(s) the user selected for picking summaries."""
        return self.fields.getlist("board")

    @cached_property
    def caption(self):
        """Lines showing report options."""

        caption = [f"Report Type: {self.report_type.capitalize()}"]
        match self.report_type:
            case "images":
                match self.selection_method:
                    case "title":
                        caption.append(f"Image Title: {self.image_title}")
                    case "id":
                        caption.append(f"Image CDR ID: {self.image_id}")
                    case "category":
                        categories = "; ".join(self.image_category)
                        caption.append(f"Image Categories: {categories}")
            case "summaries":
                match self.selection_method:
                    case "title":
                        caption.append(f"Summary Title: {self.summary_title}")
                    case "id":
                        caption.append(f"Summary CDR ID: {self.summary_id}")
                    case "board":
                        if "all" in self.board:
                            caption.append("Boards: All")
                        else:
                            boards = Board.get_boards(cursor=self.cursor)
                            names = [str(boards[int(id)]) for id in self.board]
                            names = "; ".join(names)
                            caption.append(f"Boards: {names}")
                    case "type":
                        types = "; ".join(self.summary_type)
                        caption.append(f"Summary Types: {types}")
                if self.include_summary_modules:
                    caption.append("Summary Options: include summary modules")
                else:
                    caption.append("Summary Options: exclude summary modules")
        if self.audience != "any":
            caption.append(f"Audience: {self.AUDIENCES[self.audience]}")
        if self.language != "any":
            caption.append(f"Language: {self.language.capitalize()}")
        if self.diagnosis != "all":
            diagnoses = dict(self.diagnoses)
            caption.append(f"Image Diagnosis: {diagnoses[int(self.diagnosis)]}")
        for name in self.DEMOGRAPHIC_FIELDS:
            value = self.fields.getvalue(name, "all")
            if value != "all":
                caption.append(f"{name}: {value}")
        if self.start:
            if self.end:
                caption.append(f"{self.start} to {self.end}")
            else:
                caption.append(f"from {self.start}")
        elif self.end:
            caption.append(f"through {self.end}")
        if self.report_type == "images":
            caption.append(f"Number of rows: {len(self.rows)}")
        return caption

    @cached_property
    def columns(self):
        columns = []
        if self.report_type == "summaries":
            if self.language != "spanish":
                columns.append("English Summary ID")
            if self.language != "english":
                columns.append("Spanish Summary ID")
            if self.language != "spanish":
                columns.append("English Summary Title")
            if self.language != "english":
                columns.append("Spanish Summary Title")
        if self.language != "spanish":
            columns.append("English Image ID")
        if self.language != "english":
            columns.append("Spanish Image ID")
        if self.report_type == "images":
            if self.language != "spanish":
                columns.append("English Image Title")
            if self.language != "english":
                columns.append("Spanish Image Title")
        for name in self.DEMOGRAPHIC_FIELDS:
            if self.language != "spanish":
                columns.append(f"{name} (en)")
            if self.language != "english":
                columns.append(f"{name} (es)")
        if self.language != "spanish":
            columns.append(f"Image Link (en)")
        if self.language != "english":
            columns.append(f"Image Link (es)")
        return columns

    @cached_property
    def diagnoses(self):
        """Picklist values for the image diagnoses."""

        diagnosis_path = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
        name_path = "/Term/PreferredName"
        query = self.Query("query_term d", "n.doc_id", "n.value")
        query.join("query_term n", "n.doc_id = d.int_val")
        query.where(f"d.path = '{diagnosis_path}'")
        query.where(f"n.path = '{name_path}'")
        query.unique().order("value")
        rows = query.execute(self.cursor).fetchall()
        return [(row.doc_id, row.value) for row in rows]

    @cached_property
    def diagnosis(self):
        """Diagnosis chosen for filtering the report."""
        return self.fields.getvalue("diagnosis")

    @cached_property
    def end(self):
        """Optional end of date range."""

        try:
            return self.parse_date(self.fields.getvalue("end"))
        except Exception:
            self.bail("invalid date")

    @cached_property
    def ethnicity(self):
        return self.fields.getvalue("ethnicity")

    @cached_property
    def image_categories(self):
        """Picklist values for image categories."""

        query = self.Query("query_term", "value").order("value").unique()
        query.where("path = '/Media/MediaContent/Categories/Category'")
        query.where("value NOT IN ('meeting recording', 'pronunciation')")
        rows = query.execute(self.cursor).fetchall()
        return [row.value for row in rows if row.value]

    @cached_property
    def image_category(self):
        """Which image category (categories) the user chose for selection."""
        return self.fields.getlist("image-category")

    @cached_property
    def image_id(self):
        """Value selected by the user for the CDR image document ID."""

        return self.fields.getvalue("image-id", "").strip()

    @cached_property
    def image_title(self):
        """Value selected by the user for the CDR image document title."""
        return self.fields.getvalue("image-title", "").strip()

    @cached_property
    def images(self):
        """Image documents selected for the report.

        Each Image object represents up to two image documents, one for
        English, and the other for Spanish, depending on which language(s)
        the user selected.
        """

        # Get the query started using the chosen selection method.
        query = self.Query("query_term_pub i", "i.doc_id").unique()
        query.where("i.path = '/Media/PhysicalMedia/ImageData/ImageType'")
        query.join("active_doc a", "a.id = i.doc_id")
        match self.selection_method:
            case "id":
                if not self.image_id:
                    self.bail("No image ID specified.")
                query.where(query.Condition("i.doc_id", self.image_id))
            case "title":
                if not self.image_title:
                    self.bail("No image title specified.")
                title = self.image_title
                query.join("query_term_pub t", "t.doc_id = i.doc_id")
                query.where ("t.path = '/Media/MediaTitle'")
                query.where(query.Condition("t.value", title, "LIKE"))
            case "category":
                path = '/Media/MediaContent/Categories/Category'
                if not self.image_category:
                    self.bail("No image categories selected.")
                categories = self.image_category
                query.join("query_term_pub c", "c.doc_id = i.doc_id")
                query.where(f"c.path = '{path}'")
                query.where(query.Condition("c.value", categories, "IN"))
            case _:
                self.bail("No valid selection method specified.")

        # Refine by language if appropriate.
        if self.language == "english":
            join_conditions = (
                "translation_of.doc_id = i.doc_id",
                "translation_of.path = '/Media/TranslationOf/@cdr:ref'"
            )
            query.outer("query_term_pub translation_of", *join_conditions)
            query.where("translation_of.int_val IS NULL")
        elif self.language == "spanish":
            join_condition = "translation_of.doc_id = i.doc_id"
            query.join("query_term_pub translation_of", join_condition)
            query.where("translation_of.path = '/Media/TranslationOf/@cdr:ref'")

        # Filter on audience as requested.
        audiences = dict(hp="Health_professionals", patient="Patients")
        audience = audiences.get(self.audience)
        if audience:
            query.join("query_term_pub audience", "audience.doc_id = i.doc_id")
            query.where("audience.path LIKE '/Media%/@audience'")
            query.where(query.Condition("audience.value", audience))

        # Add more refinement to the query as appropriate.
        self.__apply_common_filtering(query)

        # Collect the Media documents.
        ids = [row.doc_id for row in query.execute(self.cursor).fetchall()]
        docs = {}
        for id in ids:
            docs[id] = self.MediaDoc(self, id)

        # Now assemble the documents into a sequence of images, pairing
        # English and Spanish versions of the same image if appropriate.
        assembled = set()
        images = []
        for id in ids:
            if id in assembled:
                continue
            assembled.add(id)
            doc = docs[id]
            image = self.Image(doc)
            if self.language == "any":
                if doc.language == "English":
                    spanish_id = doc.spanish_translation_id
                    if spanish_id:
                        assembled.add(spanish_id)
                        if spanish_id not in docs:
                            docs[spanish_id] = self.MediaDoc(self, spanish_id)
                        image.spanish = docs[spanish_id]
                else:
                    english_id = doc.english_original_id
                    assembled.add(english_id)
                    if english_id not in docs:
                        docs[english_id] = self.MediaDoc(self, english_id)
                    image.english = docs[english_id]
            images.append(image)
        return images

    @cached_property
    def include_summary_modules(self):
        """Whether summary modules should be included or excluded."""
        return "modules" in self.fields.getlist("summary-options")

    @cached_property
    def language(self):
        """One of english, spanish, or any."""
        return self.fields.getvalue("language")

    @cached_property
    def race(self):
        return self.fields.getvalue("race")

    @cached_property
    def report_type(self):
        """Is this a report by images or a report by summaries?"""
        return self.fields.getvalue("type")

    @cached_property
    def rows(self):
        """Assemble the rows for the report."""

        rows = []
        docs = self.images if self.report_type == "images" else self.summaries
        for doc in docs:
            rows += doc.rows
        return rows

    @cached_property
    def selection_method(self):
        """How the user wants us to select CDR documents."""

        key = "image" if self.report_type == "images" else "summary"
        return self.fields.getvalue(f"{key}_method")

    @cached_property
    def sex(self):
        return self.fields.getvalue("sex")

    @cached_property
    def skin_tone(self):
        return self.fields.getvalue("skin_tone")

    @cached_property
    def start(self):
        """Optional start of date range."""

        try:
            return self.parse_date(self.fields.getvalue("start"))
        except Exception:
            self.bail("invalid date")

    @cached_property
    def summaries(self):
        """Summary documents selected for the report."""

        # Get the query started using the chosen selection method.
        Condition = self.Query.Condition
        fields = "s.doc_id AS summary_id", "i.doc_id as image_id"
        query = self.Query("query_term s", *fields).unique()
        query.where("s.path LIKE '/Summary/%MediaID/@cdr:ref'")
        query.join("query_term_pub i", "i.doc_id = s.int_val")
        query.where("i.path = '/Media/PhysicalMedia/ImageData/ImageType'")
        query.join("active_doc", "active_doc.id = i.doc_id")
        match self.selection_method:
            case "id":
                if not self.summary_id:
                    self.bail("No summary ID specified.")
                query.where(Condition("s.doc_id", int(self.summary_id)))
            case "title":
                if not self.summary_title:
                    self.bail("No summary title specified.")
                title = self.summary_title
                query.join("query_term t", "t.doc_id = s.doc_id")
                query.where("t.path = '/Summary/SummaryTitle'")
                query.where(Condition("t.value", title, "LIKE"))
            case "board":
                if "all" not in self.board:
                    b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
                    t_path = "/Summary/TranslationOf/@cdr:ref"
                    if self.language == "english":
                        query.join("query_term b", "b.doc_id = s.doc_id")
                        query.where(f"b.path = '{b_path}'")
                        query.where(Condition("b.int_val", self.board, "IN"))
                    elif self.language == "spanish":
                        query.join("query_term t", "t.doc_id = s.doc_id")
                        query.join("query_term b", "b.doc_id = t.int_val")
                        query.where(f"t.path = '{t_path}'")
                        query.where(f"b.path = '{b_path}'")
                        query.where(Condition("b.int_val", self.board, "IN"))
                    else:
                        boards = ",".join([str(int(id)) for id in self.board])
                        s_query = db.Query("query_term t", "t.doc_id").unique()
                        s_query.join("query_term b", "b.doc_id = t.int_val")
                        s_query.where(f"t.path = '{t_path}'")
                        s_query.where(f"b.path = '{b_path}'")
                        s_query.where(f"b.int_val IN ({boards})")
                        b_query = db.Query("query_term", "doc_id").unique()
                        b_query.where(f"path = '{b_path}'")
                        b_query.where(f"int_val IN ({boards})")
                        b_query.union(s_query)
                        query.where(Condition("s.doc_id", b_query, "IN"))
            case "type":
                if not self.summary_type:
                    self.bail("No summary types selected.")
                query.join("query_term t", "t.doc_id = s.doc_id")
                query.where("t.path = '/Summary/SummaryMetaData/SummaryType'")
                query.where(Condition("t.value", self.summary_type, "IN"))

        # Refine by language if appropriate.
        if self.language != "any":
            query.join("query_term l", "l.doc_id = s.doc_id")
            query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
            query.where(Condition("l.value", self.language.capitalize()))

        # Narrow by audience is so requested.
        audiences = dict(hp="Health professionals", patient="Patients")
        audience = audiences.get(self.audience)
        if audience:
            query.join("query_term a", "a.doc_id = s.doc_id")
            query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
            query.where(query.Condition("a.value", audience))

        # Exclude summaries only usable as modules if appropriate.
        if not self.include_summary_modules:
            args = "m.doc_id = s.doc_id", "m.path = '/Summary/@ModuleOnly'"
            query.outer("query_term m", *args)
            query.where("m.value IS NULL")

        # Apply the common filters and fetch the docs.
        self.__apply_common_filtering(query)
        rows = query.execute(self.cursor).fetchall()
        self.logger.info("query found %d rows", len(rows))
        summary_docs = {}
        image_docs = {}
        for row in rows:
            summary_doc = summary_docs.get(row.summary_id)
            if not summary_doc:
                summary_doc = self.SummaryDoc(self, row.summary_id)
                summary_docs[row.summary_id] = summary_doc
            image_doc = image_docs.get(row.image_id)
            if not image_doc:
                image_doc = self.MediaDoc(self, row.image_id)
                image_docs[row.image_id] = image_doc
            summary_doc.image_docs[row.image_id] = image_doc
        self.logger.info("created %d SummaryDoc objects", len(summary_docs))

        # Assemble the summary documents into pairs of English and Spanish
        # pairs if appropriate.
        summaries = []
        assembled = set()
        for summary_id in sorted(summary_docs):
            if summary_id in assembled:
                continue
            assembled.add(summary_id)
            summary_doc = summary_docs[summary_id]
            summary = self.Summary(summary_doc)
            if self.language == "any":
                if summary_doc.language == "English":
                    spanish_id = summary_doc.spanish_translation_id
                    if spanish_id:
                        assembled.add(spanish_id)
                        if spanish_id in summary_docs:
                            summary.spanish = summary_docs[spanish_id]
                else:
                    english_id = summary_doc.english_original_id
                    if english_id:
                        assembled.add(english_id)
                        if english_id in summary_docs:
                            summary.english = summary_docs[english_id]
            summaries.append(summary)

        self.logger.info("found %d summaries", len(summaries))
        return summaries

    @cached_property
    def summary_id(self):
        """Value selected by the user for the CDR Summary document ID."""
        return self.fields.getvalue("summary-id")

    @cached_property
    def summary_title(self):
        """Value selected by the user for the CDR Summary document title."""
        return self.fields.getvalue("summary-title")

    @cached_property
    def summary_type(self):
        """Which type(s) the user chose for selecting summaries."""
        return self.fields.getlist("summary-type")

    @cached_property
    def summary_types(self):
        """Picklist values for summary types."""

        query = self.Query("query_term", "value").order("value").unique()
        query.where("path = '/Summary/SummaryMetaData/SummaryType'")
        rows = query.execute(self.cursor).fetchall()
        return [row.value for row in rows if row.value]

    @cached_property
    def valid_values(self):
        """Dictionary of Media valid-values lists."""
        return dict(getDoctype("guest", "Media").vvLists)

    def build_tables(self):
        """Show the report if we have all the information we need."""

        opts = dict(columns=self.columns, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Assemble the main form for this report.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Report Type")
        checked = True
        for value, label in self.REPORT_TYPES:
            opts = dict(value=value, label=label, checked=checked)
            checked = False
            fieldset.append(page.radio_button("type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Image Selection Method")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "image-method-fieldset")
        checked = True
        for value, label in self.IMAGE_METHODS:
            opts = dict(value=value, label=label, checked=checked)
            checked = False
            fieldset.append(page.radio_button("image_method", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Summary Selection Method")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "summary-method-fieldset")
        checked = True
        for value, label in self.SUMMARY_METHODS:
            opts = dict(value=value, label=label, checked=checked)
            checked = False
            fieldset.append(page.radio_button("summary_method", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Image Title")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "image-title-fieldset")
        fieldset.append(page.text_field("image-title", label="Title"))
        page.form.append(fieldset)
        fieldset = page.fieldset("CDR Image ID")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "image-id-fieldset")
        fieldset.append(page.text_field("image-id", label="CDR ID"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Image Category")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "image-category-fieldset")
        for category in self.image_categories:
            opts = dict(value=category, label=category)
            fieldset.append(page.checkbox("image-category", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Summary Title")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "summary-title-fieldset")
        fieldset.append(page.text_field("summary-title", label="Title"))
        page.form.append(fieldset)
        fieldset = page.fieldset("CDR Summary ID")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "summary-id-fieldset")
        fieldset.append(page.text_field("summary-id", label="CDR ID"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Summary Boards")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "summary-board-fieldset")
        opts = dict(value="all", label="All Boards", checked=True)
        fieldset.append(page.checkbox("board", **opts))
        boards = Board.get_boards(cursor=self.cursor)
        for board in sorted(boards.values()):
            opts = dict(value=board.id, label=str(board))
            fieldset.append(page.checkbox("board", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Summary Types")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "summary-type-fieldset")
        for summary_type in self.summary_types:
            opts = dict(value=summary_type, label=summary_type)
            fieldset.append(page.checkbox("summary-type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Summary Options")
        fieldset.set("class", "default-hidden")
        fieldset.set("id", "summary-options-fieldset")
        opts = dict(value="modules", label="Include summary modules")
        fieldset.append(page.checkbox("summary-options", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Audience")
        checked = True
        for value, display in self.AUDIENCES.items():
            opts = dict(value=value, label=display, checked=checked)
            fieldset.append(page.radio_button("audience", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Language")
        checked = True
        for value in self.LANGUAGES:
            opts = dict(value=value, checked=checked)
            fieldset.append(page.radio_button("language", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Image Diagnosis")
        options = [["all", "All"]] + self.diagnoses
        opts = dict(options=options, default="all")
        fieldset.append(page.select("diagnosis", **opts))
        page.form.append(fieldset)
        wrapper = page.fieldset("Image Demographic Information")
        for name in self.DEMOGRAPHIC_FIELDS:
            fieldset = page.fieldset(name)
            values = self.valid_values[name.replace(" ", "")]
            name = name.lower().replace(" ", "_")
            opts = dict(value="all", checked=True)
            fieldset.append(page.radio_button(name, **opts))
            for value in values:
                opts = dict(value=value, label=value)
                fieldset.append(page.radio_button(name, **opts))
            wrapper.append(fieldset)
        page.form.append(wrapper)
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start"))
        fieldset.append(page.date_field("end"))
        page.form.append(fieldset)
        page.add_script("""\
function check_type(value) {
    if (value == "images") {
        var method = jQuery("input[name='image_method']:checked").val();
        check_image_method(method);
    }
    else {
        var method = jQuery("input[name='summary_method']:checked").val();
        check_summary_method(method);
    }
}
function check_image_method(value) {
    jQuery("fieldset.default-hidden").hide();
    jQuery("fieldset#image-method-fieldset").show();
    if (value == "id") {
        jQuery("fieldset#image-id-fieldset").show();
    }
    else if (value == "title") {
        jQuery("fieldset#image-title-fieldset").show();
    }
    else {
        jQuery("fieldset#image-category-fieldset").show();
    }
}
function check_summary_method(value) {
    jQuery("fieldset.default-hidden").hide();
    jQuery("fieldset#summary-method-fieldset").show();
    jQuery("fieldset#summary-options-fieldset").show();
    if (value == "id") {
        jQuery("fieldset#summary-id-fieldset").show();
    }
    else if (value == "title") {
        jQuery("fieldset#summary-title-fieldset").show();
    }
    else if (value == "board") {
        jQuery("fieldset#summary-board-fieldset").show();
    }
    else {
        jQuery("fieldset#summary-type-fieldset").show();
    }
}
function check_board(val) {
    if (val == "all") {
        jQuery("input[name='board']").prop("checked", false);
        jQuery("#board-all").prop("checked", true);
    }
    else if (jQuery("input[name='board']:checked").length > 0)
        jQuery("#board-all").prop("checked", false);
    else
        jQuery("#board-all").prop("checked", true);
}
jQuery(function() {
    var value = jQuery("input[name='type']:checked").val();
    console.log("value is " + value);
    check_type(value);
});""")

    def __apply_common_filtering(self, query):
        """Narrow the report further, if requested.

        Required positional argument:
            query - the Query object to be altered, as appropriate
        """

        # Ditto for diagnosis.
        if self.diagnosis != "all":
            path = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
            query.join("query_term diagnosis", "diagnosis.doc_id = i.doc_id")
            query.where(f"diagnosis.path = '{path}'")
            query.where(query.Condition("diagnosis.int_val", self.diagnosis))

        # Narrow by demographic information.
        counter = 1
        for label in self.DEMOGRAPHIC_FIELDS:
            name = label.lower().replace(" ", "_")
            value = getattr(self, name)
            if value and value != "all":
                tag = label.replace(" ", "")
                path = f"/Media/DemographicInformation/{tag}"
                alias = f"demographic_field_{counter}"
                counter += 1
                query.join(f"query_term {alias}", f"{alias}.doc_id = i.doc_id")
                query.where(f"{alias}.path = '{path}'")
                query.where(query.Condition(f"{alias}.value", value))

        # Filter by first publication date.
        if self.start or self.end:
            query.join("document", "document.id = i.doc_id")
            if self.start:
                start = str(self.start)
                query.where(query.Condition("document.first_pub", start, ">="))
            if self.end:
                end = f"{self.end} 23:59:59"
                query.where(query.Condition("document.first_pub", end, "<="))

        # Log tbe assembled query.
        query.log(label="Image Demographic Report Query")


    class Image:
        NAMES = "id", "title", "age", "sex", "race", "skin_tone", "ethnicity"
        SINGLE = "id", "title"
        def __init__(self, doc):
            self.control = doc.control
            self.english = self.spanish = None
            if doc.language == "English":
                self.english = doc
            else:
                self.spanish = doc
        @cached_property
        def rows(self):
            Cell = self.control.Reporter.Cell
            row = []
            english = self.control.language != "spanish"
            spanish = self.control.language != "english"
            for name in self.NAMES:
                if english:
                    value = getattr(self.english, name) if self.english else ""
                    if name not in self.SINGLE:
                        value = "\n".join(value) if value else ""
                    row.append(value)
                if spanish:
                    value = getattr(self.spanish, name) if self.spanish else ""
                    if name not in self.SINGLE:
                        value = "\n".join(value) if value else ""
                    elif self.spanish and isinstance(self.spanish.id, str):
                        if name == "id":
                            value = ""
                        elif name == "title":
                            value = Cell(self.spanish.id, classes="error")
                    row.append(value)
            if english:
                cell = ""
                if self.english:
                    opts = dict(href=self.english.url, target="_blank")
                    cell = Cell("QC Report", **opts)
                row.append(cell)
            if spanish:
                cell = ""
                if self.spanish and self.spanish.url:
                    opts = dict(href=self.spanish.url, target="_blank")
                    cell = Cell("QC Report", **opts)
                row.append(cell)
            return [row]


    class MediaDoc:
        def __init__(self, control, id):
            self.control = control
            self.id = id

        @cached_property
        def age(self):
            age = []
            if self.root is not None:
                for node in self.root.findall("DemographicInformation/Age"):
                    value = Doc.get_text(node)
                    if value:
                        age.append(value)
            return age

        @cached_property
        def categories(self):
            """Category strings assigned to this media document."""

            categories = []
            if self.root is not None:
                path = "MediaContent/Categories/Category"
                for node in self.root.findall(path):
                    category = Doc.get_text(node, "").strip()
                    if category:
                        categories.append(category)
            return categories

        @cached_property
        def doc(self):
            if isinstance(self.id, str):
                return None
            return Doc(self.control.session, id=self.id)

        @cached_property
        def english_original_id(self):
            if self.root is not None:
                for node in self.root.findall("TranslationOf"):
                    value = node.get(Link.CDR_REF)
                    if value:
                        try:
                            return Doc.extract_id(value)
                        except:
                            self.control.logger.exception(value)
            return None

        @cached_property
        def ethnicity(self):
            ethnicity = []
            if self.root is None:
                return ethnicity
            for node in self.root.findall("DemographicInformation/Ethnicity"):
                value = Doc.get_text(node)
                if value:
                    ethnicity.append(value)
            return ethnicity

        @cached_property
        def language(self):
            return "Spanish" if self.english_original_id else "English"

        @cached_property
        def race(self):
            race = []
            if self.root is not None:
                for node in self.root.findall("DemographicInformation/Race"):
                    value = Doc.get_text(node)
                    if value:
                        race.append(value)
            return race

        @cached_property
        def root(self):
            return self.doc.root if self.doc else None

        @cached_property
        def sex(self):
            sex = []
            if self.root is not None:
                for node in self.root.findall("DemographicInformation/Sex"):
                    value = Doc.get_text(node)
                    if value:
                        sex.append(value)
            return sex

        @cached_property
        def skin_tone(self):
            skin_tone = []
            if self.root is None:
                return skin_tone
            for node in self.root.findall("DemographicInformation/SkinTone"):
                value = Doc.get_text(node)
                if value:
                    skin_tone.append(value)
            return skin_tone

        @cached_property
        def spanish_translation_id(self):
            query = self.control.Query("query_term", "doc_id")
            query.where("path = '/Media/TranslationOf/@cdr:ref'")
            query.where(query.Condition("int_val", self.id))
            query.log(label="Spanish Translation ID query")
            rows = query.execute(self.control.cursor).fetchall()
            if not rows:
                return None
            if len(rows) == 1:
                return rows[0].doc_id
            id = f"CDR{self.id}"
            return f"Too many documents claim to be translations of {id}"

        @cached_property
        def title(self):
            if self.root is not None:
                return Doc.get_text(self.root.find("MediaTitle"))
            return None

        @cached_property
        def url(self):
            if isinstance(self.id, str):
                return ""
            return f"QcReport.py?DocId=CDR{self.id}"

    class Summary:
        def __init__(self, doc):
            self.control = doc.control
            self.english = self.spanish = None
            if doc.language == "English":
                self.english = doc
            else:
                self.spanish = doc

        @cached_property
        def rows(self):
            Cell = self.control.Reporter.Cell
            rows = []
            english = self.control.language != "spanish"
            spanish = self.control.language != "english"
            english_done = set()
            images = []
            if self.spanish:
                for sid in sorted(self.spanish.image_docs):
                    s = self.spanish.image_docs[sid]
                    e = None
                    if self.english:
                        eid = s.english_original_id
                        if eid in self.english.image_docs:
                            e = self.english.image_docs[eid]
                            english_done.add(eid)
                    images.append([e, s])
            if self.english:
                for eid in sorted(self.english.image_docs):
                    if eid not in english_done:
                        images.append([self.english.image_docs[eid], None])
            for e, s in images:
                row = []
                for name in ("id", "title"):
                    if english:
                        if self.english:
                            row.append(getattr(self.english, name))
                        else:
                            row.append("")
                    if spanish:
                        if self.spanish:
                            row.append(getattr(self.spanish, name))
                        else:
                            row.append("")
                for name in Control.Image.NAMES:
                    if name == "title":
                        continue
                    if english:
                        value = getattr(e, name) if e else ""
                        if value and name not in Control.Image.SINGLE:
                            value = "\n".join(value)
                        row.append(value)
                    if spanish:
                        value = getattr(s, name) if s else ""
                        if value and name not in Control.Image.SINGLE:
                            value = "\n".join(value)
                        row.append(value)

                if english:
                    cell = ""
                    if e:
                        opts = dict(href=e.url, target="_blank")
                        cell = Cell("QC Report", **opts)
                    row.append(cell)
                if spanish:
                    cell = ""
                    if s and s.url:
                        opts = dict(href=s.url, target="_blank")
                        cell = Cell("QC Report", **opts)
                    row.append(cell)
                rows.append(row)
            self.control.logger.debug("returning %d summary rows", len(rows))
            return rows


    class SummaryDoc:
        """Summary and the images to which it links."""

        def __init__(self, control, id):
            self.control = control
            self.id = id
            self.image_docs = {}

        @cached_property
        def doc(self):
            if not isinstance(self.id, int):
                return None
            return Doc(self.control.session, id=self.id)

        @cached_property
        def english_original_id(self):
            if self.root is not None:
                for node in self.root.findall("TranslationOf"):
                    value = node.get(Link.CDR_REF)
                    if value:
                        try:
                            return Doc.extract_id(value)
                        except:
                            self.control.logger.exception(value)
            return None

        @cached_property
        def language(self):
            node = self.root.find("SummaryMetaData/SummaryLanguage")
            return Doc.get_text(node)

        @cached_property
        def module(self):
            """True IFF this summary can only be used as a module."""
            return self.root.get("ModuleOnly") == "Y"

        @cached_property
        def root(self):
            return self.doc.root if self.doc else None

        @cached_property
        def spanish_translation_id(self):
            query = self.control.Query("query_term", "doc_id")
            query.where("path = '//Summary/TranslationOf/@cdr:ref'")
            query.where(query.Condition("int_val", self.id))
            query.log(label="Spanish Summary Translation ID query")
            rows = query.execute(self.control.cursor).fetchall()
            if not rows:
                return None
            if len(rows) == 1:
                return rows[0].doc_id
            id = f"CDR{self.id}"
            return f"Too many documents claim to be translations of {id}"

        @cached_property
        def title(self):
            suffix = " [Module Only]" if self.module else ""
            return Doc.get_text(self.root.find("SummaryTitle")) + suffix


if __name__ == "__main__":
    """Don't execute the script when loaded as a module."""
    Control().run()
