#!/usr/bin/env python

"""Show highlights from user-selected Media documents.

Users enter date, diagnosis, category, and language selection criteria.
The program selects those documents and outputs the requested fields,
one document per row.

Report enhanced to include an additional, optional column with a
thumbnail image.
"""

from datetime import datetime, date, timedelta
from functools import cached_property
from io import BytesIO
from sys import stdout
from xlsxwriter import Workbook
from cdr import get_image
from cdrapi.docs import Doc
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Media Caption and Content Report"
    LOGNAME = "MediaCaptionContent"
    CATEGORY_PATH = "/Media/MediaContent/Categories/Category"
    DIAGNOSIS_PATH = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
    CAPTION_PATH = "/Media/MediaContent/Captions/MediaCaption"
    LANGUAGE_PATH = "/Media/MediaContent/Captions/MediaCaption/@language"
    AUDIENCE_PATH = "/Media/MediaContent/Captions/MediaCaption/@audience"
    SOUND_PATH = "/Media/PhysicalMedia/SoundData/SoundEncoding"
    TERM_PATH = "/Term/PreferredName"
    YES_NO = (("Y", "Yes"), ("N", "No"))
    FILENAME = "media-{}.xlsx".format(datetime.now().strftime("%Y%m%d%H%M%S"))
    INSTRUCTIONS = (
        "To prepare an Excel format report of Media Caption and Content "
        "information, enter starting and ending dates (inclusive) for the "
        "last versions of the Media documents to be retrieved. You may also "
        "select documents with specific diagnoses, categories, language, or "
        "audience of the content description. Relevant fields from the Media "
        "documents that meet the selection criteria will be displayed in an "
        "Excel spreadsheet."
    )

    def populate_form(self, page):
        """Let the user decide which Media documents to include.

        Pass:
            page - HTMLPage object where the form's fields are displayed
        """

        diagnosis = category = ["any"]
        language = audience = ["all"]
        images = "N"
        if self.request:
            start = self.start_date
            end = self.end_date
            diagnosis = self.diagnosis
            category = self.category
            language = self.language
            audience = self.audience
            images = "Y" if self.include_images else "N"
        else:
            end = date.today()
            start = end - timedelta(30)
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Time Frame")
        fieldset.append(page.date_field("start_date", value=start))
        fieldset.append(page.date_field("end_date", value=end))
        page.form.append(fieldset)
        fieldset = page.fieldset("Include Specific Content")
        opts = dict(default=diagnosis, options=self.diagnoses, multiple=True)
        fieldset.append(page.select("diagnosis", **opts))
        opts = dict(default=category, options=self.categories, multiple=True)
        fieldset.append(page.select("category", **opts))
        opts = dict(default=language, options=self.languages)
        fieldset.append(page.select("language", **opts))
        opts = dict(default=audience, options=self.audiences)
        fieldset.append(page.select("audience", **opts))
        opts = dict(default=images, options=self.YES_NO)
        fieldset.append(page.select("images", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Override so we can embed images in the report spreadsheet."""

        if not self.ids:
            message = "Your selection criteria did not retrieve any documents"
            self.alerts.append(dict(message=message, type="warning"))
            return self.show_form()
        row = 3
        for id in self.ids:
            media = Media(self, id)
            row = media.report(row)
        self.logger.info("sending %s", self.FILENAME)
        self.book.close()
        self.output.seek(0)
        book_bytes = self.output.read()
        stdout.buffer.write(f"""\
Content-type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename={self.FILENAME}
Content-length: {len(book_bytes):d}

""".encode("utf-8"))
        stdout.buffer.write(book_bytes)

    @cached_property
    def audience(self):
        """User's selection for which audiences are to be included."""

        audience = self.fields.getvalue("audience") or "all"
        if audience not in {a[0] for a in self.audiences}:
            self.bail()
        return audience

    @cached_property
    def audiences(self):
        """Options for the Audience form picklist."""

        return (
            ("all", "All Audiences"),
            ("Health_professionals", "HP"),
            ("Patients", "Patient"),
        )

    @cached_property
    def book(self):
        """Excel workbook for the report."""
        return Workbook(self.output, dict(in_memory=True))

    @cached_property
    def categories(self):
        """Options for the Categories form picklist."""

        query = self.Query("query_term c", "c.value", "c.value").unique()
        query.where(f"c.path = '{self.CATEGORY_PATH}'")
        query.where("c.value <> ''")
        query.outer("query_term s", "s.doc_id = c.doc_id",
                    f"s.path = '{self.SOUND_PATH}'")
        query.where("s.doc_id IS NULL")
        rows = query.order(1).execute()
        categories = [("any", "Any Category")]
        categories += [tuple(row) for row in rows]
        return categories

    @cached_property
    def category(self):
        """User's selection(s) for which categories to include."""

        categories = self.fields.getlist("category") or ["any"]
        if set(categories) - {c[0] for c in self.categories}:
            self.bail()
        return categories

    @cached_property
    def cell_format(self):
        """Styling for data cells."""

        opts = dict(align="left", valign="top", text_wrap=True)
        return self.book.add_format(opts)

    @cached_property
    def coverage(self):
        """String describing the date range for the report."""

        if self.start_date:
            if self.end_date:
                return f"{self.start_date} -- {self.end_date}"
            return f"Since {self.start_date}"
        if self.end_date:
            return f"Through {self.end_date}"
        return "All dates"

    @cached_property
    def diagnoses(self):
        """Options for the form's Diagnosis picklist."""

        query = self.Query("query_term t", "t.doc_id", "t.value")
        query.join("query_term d", "d.int_val = t.doc_id")
        query.where(f"t.path = '{self.TERM_PATH}'")
        query.where(f"d.path = '{self.DIAGNOSIS_PATH}'")
        query.outer("query_term s", "s.doc_id = d.doc_id",
                    f"s.path = '{self.SOUND_PATH}'")
        query.where("s.doc_id IS NULL")
        rows = query.unique().order(2).execute(self.cursor).fetchall()
        diagnoses = [("any", "Any Diagnosis")]
        diagnoses += [tuple(row) for row in rows]
        return diagnoses

    @cached_property
    def diagnosis(self):
        """User's choice(s) for which diagnoses to include on the report."""

        diagnoses = self.fields.getlist("diagnosis") or ["any"]
        if set(diagnoses) - {str(c[0]) for c in self.diagnoses}:
            self.bail()
        return diagnoses

    @cached_property
    def end_date(self):
        """User's selection for the end of the report's date range."""

        end_date = self.fields.getvalue("end_date")
        try:
            return self.parse_date(end_date)
        except Exception:
            self.bail("Invalid date")

    @cached_property
    def header_format(self):
        """Styling for the report header rows."""

        opts = dict(
            align="center",
            bold=True,
            fg_color="#0000FF",
            font_color="#FFFFFF",
        )
        return self.book.add_format(opts)

    @cached_property
    def ids(self):
        """CDR integer IDs for the selected Media documents."""

        path_used = False
        query = self.Query("document d", "d.id", "d.title")
        query.join("doc_version v", "d.id = v.id")
        if self.start_date:
            query.where(query.Condition("v.dt", self.start_date, ">="))
        if self.end_date:
            end = f"{self.end_date} 23:59:59"
            query.where(query.Condition("v.dt", end, "<="))
        if self.diagnosis and "any" not in self.diagnosis:
            diagnosis = [int(diagnosis) for diagnosis in self.diagnosis]
            query.join("query_term q1", "q1.doc_id = d.id")
            query.where(query.Condition("q1.path", self.DIAGNOSIS_PATH))
            query.where(query.Condition("q1.int_val", diagnosis, "IN"))
            path_used = True
        if self.category and "any" not in self.category:
            query.join("query_term q2", "q2.doc_id = d.id")
            query.where(query.Condition("q2.path", self.CATEGORY_PATH))
            query.where(query.Condition("q2.value", self.category, "IN"))
            path_used = True
        if self.language and self.language != "all":
            query.join("query_term q3", "q3.doc_id = d.id")
            query.where(query.Condition("q3.path", self.LANGUAGE_PATH))
            query.where(query.Condition("q3.value", self.language))
            path_used = True
        if self.audience and self.audience != "all":
            query.join("query_term q4", "q4.doc_id = d.id")
            query.where(query.Condition("q4.path", self.AUDIENCE_PATH))
            query.where(query.Condition("q4.value", self.audience))
            path_used = True
        if not path_used:
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'Media'")
        query.outer("query_term s", "s.doc_id = d.id",
                    f"s.path = '{self.SOUND_PATH}'")
        query.where("s.doc_id IS NULL")
        query.unique()
        query.order("d.title")
        query.log(logfile=f"{self.session.tier.logdir}/media.log")
        try:
            rows = query.execute(self.cursor).fetchall()
            return [row.id for row in rows]
        except Exception as e:
            self.logger.exception("Report database query failure")
            msg = "Database error executing MediaCaptionContent.py query"
            extra = f"query = {query}", f"error = {e}"
            return self.bail(msg, extra=extra)

    @cached_property
    def include_images(self):
        """True if we should include a column for the JPEG images."""
        return self.fields.getvalue("images") == "Y"

    @cached_property
    def labels(self):
        """Sequence of strings for the report's column headers."""

        labels = [
            "CDR ID",
            "Title",
            "Diagnosis",
            "Proposed Summaries",
            "Proposed Glossary Terms",
            "Label Names",
            "Content Description",
            "Caption",
        ]
        if self.include_images:
            labels.append("Image")
        return tuple(labels)

    @cached_property
    def language(self):
        """User's selection for which language(s) should be included."""

        language = self.fields.getvalue("language") or "all"
        if language not in {lang[0] for lang in self.languages}:
            self.bail()
        return language

    @cached_property
    def languages(self):
        """Options for the form's language picklist."""

        return (
            ("all", "All Languages"),
            ("en", "English"),
            ("es", "Spanish"),
        )

    @cached_property
    def merge_format(self):
        """Styling used to merge the header rows for the report."""
        return self.book.add_format(dict(align="center", bold=True))

    @cached_property
    def output(self):
        """Memory stream to capture the Excel workbook's bytes."""
        return BytesIO()

    @cached_property
    def same_window(self):
        """Don't open more than one new browser tab."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def sheet(self):
        """Spreadsheet on which the report is built."""

        last_col = len(self.labels) - 1
        sheet = self.book.add_worksheet("Media Caption-Content")
        sheet.freeze_panes(3, 0)
        args = 0, 0, 0, last_col, self.sheet_title, self.merge_format
        sheet.merge_range(*args)
        args = 1, 0, 1, last_col, self.coverage, self.merge_format
        sheet.merge_range(*args)
        for i, width in enumerate(self.widths):
            sheet.set_column(i, i, width)
        for column, label in enumerate(self.labels):
            sheet.write(2, column, label, self.header_format)
        return sheet

    @cached_property
    def sheet_title(self):
        """Title row's string describing the report."""

        title = "Media Caption and Content Report"
        if self.audience == "Health_professionals":
            return f"{title} - HP"
        elif self.audience == "Patients":
            return f"{title} - Patient"
        return title

    @cached_property
    def start_date(self):
        """User's selection for the start of the report's date range."""

        start_date = self.fields.getvalue("start_date")
        try:
            return self.parse_date(start_date)
        except Exception:
            self.bail("Invalid date")

    @cached_property
    def widths(self):
        """Column widths for the report table."""

        widths = [10, 25, 25, 25, 25, 25, 25, 25]
        if self.include_images:
            widths.append(30)
        return tuple(widths)


class Media:
    """Capture report data from a CDR Media document."""

    FILTER = "name:Fast Denormalization Filter"
    MEDIA_OPTS = dict(x_offset=10, y_offset=10, x_scale=1.0, y_scale=1.0)
    IMAGE_OPTS = dict(height=200, width=200, return_stream=True)
    URL = "https://{}/cgi-bin/cdr/GetCdrImage.py?pp=N&id={}"

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the user's report selections
            id - CDR integer ID for the Media document
        """

        self.__control = control
        self.__id = id

    def report(self, row):
        """Add a row to the report's spreadsheet for this Media document.

        Pass:
            row - integer identifying the row we write to

        Return:
            Integer for the next Media document's row (skipping a blank row)
        """

        sheet = self.__control.sheet
        fmt = self.__control.cell_format
        sheet.write(row, 0, self.doc.id, fmt)
        sheet.write(row, 1, self.title, fmt)
        sheet.write(row, 2, "\n".join(self.diagnoses), fmt)
        sheet.write(row, 3, "\n".join(self.summaries), fmt)
        sheet.write(row, 4, "\n".join(self.terms), fmt)
        sheet.write(row, 5, "\n".join(self.labels), fmt)
        sheet.write(row, 6, "\n\n".join(self.descriptions), fmt)
        sheet.write(row, 7, "\n\n".join(self.captions), fmt)
        if self.__control.include_images and self.encoding == "JPEG":
            try:
                image = get_image(self.doc.id, **self.IMAGE_OPTS)
            except Exception:
                self.__control.logger.exception("Image for %s", self.doc.id)
            else:
                opts = dict(self.MEDIA_OPTS)
                opts["url"] = self.url
                opts["image_data"] = image
                sheet.insert_image(row, 8, "dummy", opts)
                sheet.set_row(row, 170)
        return row + 2

    @cached_property
    def audience(self):
        """Optional value to narrow the report to a single audience."""

        audience = self.__control.audience
        return None if audience == "all" else audience

    @cached_property
    def captions(self):
        """Sequence of strings for the Media document's captions."""

        captions = []
        for node in self.root.findall("MediaContent/Captions/MediaCaption"):
            audience = node.get("audience")
            if not self.audience or audience == self.audience:
                language = node.get("language")
                if not self.language or language == self.language:
                    caption = Doc.get_text(node, "").strip()
                    if caption:
                        captions.append(caption)
        return captions

    @cached_property
    def descriptions(self):
        """Sequence of strings for the document's content descriptions."""

        descriptions = []
        path = "MediaContent/ContentDescriptions/ContentDescription"
        for node in self.root.findall(path):
            audience = node.get("audience")
            if not self.audience or audience == self.audience:
                language = node.get("language")
                if not self.language or language == self.language:
                    description = Doc.get_text(node, "").strip()
                    if description:
                        descriptions.append(description)
        return descriptions

    @cached_property
    def diagnoses(self):
        """Sequence of strings for the Media document's diagnoses."""

        diagnoses = []
        for node in self.root.findall("MediaContent/Diagnoses/Diagnosis"):
            diagnosis = Doc.get_text(node, "").strip()
            if diagnosis:
                diagnoses.append(diagnosis)
        return diagnoses

    @cached_property
    def doc(self):
        """The CDR API object for this Media document."""
        return Doc(self.__control.session, id=self.__id)

    @cached_property
    def encoding(self):
        """String for the image encoding if this is an image document."""

        node = self.root.find("PhysicalMedia/ImageData/ImageEncoding")
        if node is not None:
            return Doc.get_text(node, "").strip()
        return None

    @cached_property
    def labels(self):
        """Sequence of strings for the Media document's labels."""

        labels = []
        for node in self.root.findall("PhysicalMedia/ImageData/LabelName"):
            language = node.get("language")
            if not self.language or language == self.language:
                label = Doc.get_text(node, "").strip()
                if label:
                    labels.append(label)
        return labels

    @cached_property
    def language(self):
        """Optionally narrow the values to those for a single audience."""

        language = self.__control.language
        return None if language == "all" else language

    @cached_property
    def root(self):
        """Top-level DOM element for the Media document."""
        return self.doc.filter(self.FILTER).result_tree.getroot()

    @cached_property
    def summaries(self):
        """Sequence of titles of summaries for which the media will be used."""

        summaries = []
        for node in self.root.findall("ProposedUse/Summary"):
            summary = Doc.get_text(node, "").strip()
            if summary:
                summaries.append(summary)
        return summaries

    @cached_property
    def terms(self):
        """Sequence of glossary terms for which the media will be used."""

        terms = []
        for node in self.root.findall("ProposedUse/Glossary"):
            term = Doc.get_text(node, "").strip()
            if term:
                terms.append(term)
        return terms

    @cached_property
    def title(self):
        """String for the title of this Media document."""
        return Doc.get_text(self.root.find("MediaTitle"), "").strip()

    @cached_property
    def url(self):
        """Address of the script to fetch the document's media blob."""

        host = self.__control.session.tier.hosts["APPC"]
        return self.URL.format(host, self.doc.id)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
