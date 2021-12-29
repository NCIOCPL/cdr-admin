#!/usr/bin/env python

"""Show highlights from user-selected Media documents.

Users enter date, diagnosis, category, and language selection criteria.
The program selects those documents and outputs the requested fields,
one document per row.

Report enhanced to include an additional, optional column with a
thumbnail image.
"""

from datetime import datetime, date, timedelta
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
        opts = dict(default="any", options=self.diagnoses, multiple=True)
        fieldset.append(page.select("diagnosis", **opts))
        opts = dict(default="any", options=self.categories, multiple=True)
        fieldset.append(page.select("category", **opts))
        opts = dict(default="all", options=self.languages)
        fieldset.append(page.select("language", **opts))
        opts = dict(default="all", options=self.audiences)
        fieldset.append(page.select("audience", **opts))
        opts = dict(default="N", options=self.YES_NO)
        fieldset.append(page.select("images", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Override so we can embed images in the report spreadsheet."""

        if not self.ids:
            message = "Your selection criteria did not retrieve any documents"
            extra = ["Please click the back button and try again."]
            self.bail(message, extra)
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

    @property
    def audience(self):
        """User's selection for which audiences are to be included."""

        if not hasattr(self, "_audience"):
            self._audience = self.fields.getvalue("audience") or "all"
            if self._audience not in {a[0] for a in self.audiences}:
                self.bail()
        return self._audience

    @property
    def audiences(self):
        """Options for the Audience form picklist."""

        return (
            ("all", "All Audiences"),
            ("Health_professionals", "HP"),
            ("Patients", "Patient"),
        )

    @property
    def book(self):
        """Excel workbook for the report."""

        if not hasattr(self, "_book"):
            opts = dict(in_memory=True)
            self._book = Workbook(self.output, opts)
        return self._book

    @property
    def categories(self):
        """Options for the Categories form picklist."""

        if not hasattr(self, "_categories"):
            query = self.Query("query_term c", "c.value", "c.value").unique()
            query.where(f"c.path = '{self.CATEGORY_PATH}'")
            query.where("c.value <> ''")
            query.outer("query_term s", "s.doc_id = c.doc_id",
                        f"s.path = '{self.SOUND_PATH}'")
            query.where("s.doc_id IS NULL")
            rows = query.order(1).execute()
            self._categories = [("any", "Any Category")]
            self._categories += [tuple(row) for row in rows]
        return self._categories

    @property
    def category(self):
        """User's selection(s) for which categories to include."""

        if not hasattr(self, "_category"):
            self._category = self.fields.getlist("category") or ["any"]
            if set(self._category) - {c[0] for c in self.categories}:
                self.bail()
        return self._category

    @property
    def cell_format(self):
        """Styling for data cells."""

        if not hasattr(self, "_cell_format"):
            opts = dict(align="left", valign="top", text_wrap=True)
            self._cell_format = self.book.add_format(opts)
        return self._cell_format

    @property
    def coverage(self):
        """String describing the date range for the report."""

        if not hasattr(self, "_coverage"):
            if self.start_date:
                if self.end_date:
                    self._coverage = f"{self.start_date} -- {self.end_date}"
                else:
                    self._coverage = f"Since {self.start_date}"
            elif self.end_date:
                self._coverage = f"Through {self.end_date}"
            else:
                self._coverage = "All dates"
        return self._coverage

    @property
    def diagnoses(self):
        """Options for the form's Diagnosis picklist."""

        if not hasattr(self, "_diagnoses"):
            query = self.Query("query_term t", "t.doc_id", "t.value")
            query.join("query_term d", "d.int_val = t.doc_id")
            query.where(f"t.path = '{self.TERM_PATH}'")
            query.where(f"d.path = '{self.DIAGNOSIS_PATH}'")
            query.outer("query_term s", "s.doc_id = d.doc_id",
                        f"s.path = '{self.SOUND_PATH}'")
            query.where("s.doc_id IS NULL")
            rows = query.unique().order(2).execute(self.cursor).fetchall()
            self._diagnoses = [("any", "Any Diagnosis")]
            self._diagnoses += [tuple(row) for row in rows]
        return self._diagnoses

    @property
    def diagnosis(self):
        """User's choice(s) for which diagnoses to include on the report."""

        if not hasattr(self, "_diagnosis"):
            self._diagnosis = self.fields.getlist("diagnosis") or ["any"]
            if set(self._diagnosis) - {str(c[0]) for c in self.diagnoses}:
                self.bail()
        return self._diagnosis

    @property
    def end_date(self):
        """User's selection for the end of the report's date range."""

        if not hasattr(self, "_end_date"):
            end_date = self.fields.getvalue("end_date")
            try:
                self._end_date = self.parse_date(end_date)
            except Exception:
                self.bail("Invalid date")
        return self._end_date

    @property
    def header_format(self):
        """Styling for the report header rows."""

        if not hasattr(self, "_header_format"):
            opts = dict(
                align="center",
                bold=True,
                fg_color="#0000FF",
                font_color="#FFFFFF",
            )
            self._header_format = self.book.add_format(opts)
        return self._header_format

    @property
    def ids(self):
        """CDR integer IDs for the selected Media documents."""

        if not hasattr(self, "_ids"):
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
                self._ids = [row.id for row in rows]
            except Exception as e:
                self.logger.exception("Report database query failure")
                msg = "Database error executing MediaCaptionContent.py query"
                extra = f"query = {query}", f"error = {e}"
                self.bail(msg, extra=extra)
        return self._ids

    @property
    def include_images(self):
        """True if we should include a column for the JPEG images."""

        if not hasattr(self, "_include_images"):
            self._include_images = self.fields.getvalue("images") == "Y"
        return self._include_images

    @property
    def labels(self):
        """Sequence of strings for the report's column headers."""

        if not hasattr(self, "_labels"):
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
            self._labels = tuple(labels)
        return self._labels

    @property
    def language(self):
        """User's selection for which language(s) should be included."""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language") or "all"
            if self._language not in {lang[0] for lang in self.languages}:
                self.bail()
        return self._language

    @property
    def languages(self):
        """Options for the form's language picklist."""

        return (
            ("all", "All Languages"),
            ("en", "English"),
            ("es", "Spanish"),
        )

    @property
    def merge_format(self):
        """Styling used to merge the header rows for the report."""

        if not hasattr(self, "_merge_format"):
            opts = dict(align="center", bold=True)
            self._merge_format = self.book.add_format(opts)
        return self._merge_format

    @property
    def output(self):
        """Memory stream to capture the Excel workbook's bytes."""

        if not hasattr(self, "_output"):
            self._output = BytesIO()
        return self._output

    @property
    def sheet(self):
        """Spreadsheet on which the report is build."""

        if not hasattr(self, "_sheet"):
            last_col = len(self.labels) - 1
            self._sheet = self.book.add_worksheet("Media Caption-Content")
            self._sheet.freeze_panes(3, 0)
            args = 0, 0, 0, last_col, self.sheet_title, self.merge_format
            self._sheet.merge_range(*args)
            args = 1, 0, 1, last_col, self.coverage, self.merge_format
            self._sheet.merge_range(*args)
            for i, width in enumerate(self.widths):
                self._sheet.set_column(i, i, width)
            for column, label in enumerate(self.labels):
                self._sheet.write(2, column, label, self.header_format)
        return self._sheet

    @property
    def sheet_title(self):
        """Title row's string describing the report."""

        if not hasattr(self, "_sheet_title"):
            self._sheet_title = "Media Caption and Content Report"
            if self.audience == "Health_professionals":
                self._sheet_title += " - HP"
            elif self.audience == "Patients":
                self._sheet_title += " - Patient"
        return self._sheet_title

    @property
    def start_date(self):
        """User's selection for the start of the report's date range."""

        if not hasattr(self, "_start_date"):
            start_date = self.fields.getvalue("start_date")
            try:
                self._start_date = self.parse_date(start_date)
            except Exception:
                self.bail("Invalid date")
        return self._start_date

    @property
    def widths(self):
        """Column widths for the report table."""

        if not hasattr(self, "_widths"):
            widths = [10, 25, 25, 25, 25, 25, 25, 25]
            if self.include_images:
                widths.append(30)
            self._widths = tuple(widths)
        return self._widths


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

    @property
    def audience(self):
        """Optional value to narrow the report to a single audience."""

        if not hasattr(self, "_audience"):
            self._audience = self.__control.audience
            if self._audience == "all":
                self._audience = None
        return self._audience

    @property
    def captions(self):
        """Sequence of strings for the Media document's captions."""

        if not hasattr(self, "_captions"):
            self._captions = []
            path = "MediaContent/Captions/MediaCaption"
            for node in self.root.findall(path):
                audience = node.get("audience")
                if not self.audience or audience == self.audience:
                    language = node.get("language")
                    if not self.language or language == self.language:
                        caption = Doc.get_text(node, "").strip()
                        if caption:
                            self._captions.append(caption)
        return self._captions

    @property
    def descriptions(self):
        """Sequence of strings for the document's content descriptions."""

        if not hasattr(self, "_descriptions"):
            self._descriptions = []
            path = "MediaContent/ContentDescriptions/ContentDescription"
            for node in self.root.findall(path):
                audience = node.get("audience")
                if not self.audience or audience == self.audience:
                    language = node.get("language")
                    if not self.language or language == self.language:
                        description = Doc.get_text(node, "").strip()
                        if description:
                            self._descriptions.append(description)
        return self._descriptions

    @property
    def diagnoses(self):
        """Sequence of strings for the Media document's diagnoses."""

        if not hasattr(self, "_diagnoses"):
            self._diagnoses = []
            for node in self.root.findall("MediaContent/Diagnoses/Diagnosis"):
                diagnosis = Doc.get_text(node, "").strip()
                if diagnosis:
                    self._diagnoses.append(diagnosis)
        return self._diagnoses

    @property
    def doc(self):
        """The CDR API object for this Media document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.__id)
        return self._doc

    @property
    def encoding(self):
        """String for the image encoding if this is an image document."""

        if not hasattr(self, "_encoding"):
            self._encoding = None
            node = self.root.find("PhysicalMedia/ImageData/ImageEncoding")
            if node is not None:
                self._encoding = Doc.get_text(node, "").strip()
        return self._encoding

    @property
    def labels(self):
        """Sequence of strings for the Media document's labels."""

        if not hasattr(self, "_labels"):
            self._labels = []
            for node in self.root.findall("PhysicalMedia/ImageData/LabelName"):
                language = node.get("language")
                if not self.language or language == self.language:
                    label = Doc.get_text(node, "").strip()
                    if label:
                        self._labels.append(label)
        return self._labels

    @property
    def language(self):
        """Optionally narrow the values to those for a single audience."""

        if not hasattr(self, "_language"):
            self._language = self.__control.language
            if self._language == "all":
                self._language = None
        return self._language

    @property
    def root(self):
        """Top-level DOM element for the Media document."""

        if not hasattr(self, "_root"):
            result = self.doc.filter(self.FILTER)
            self._root = result.result_tree.getroot()
        return self._root

    @property
    def summaries(self):
        """Sequence of titles of summaries for which the media will be used."""

        if not hasattr(self, "_summaries"):
            self._summaries = []
            for node in self.root.findall("ProposedUse/Summary"):
                summary = Doc.get_text(node, "").strip()
                if summary:
                    self._summaries.append(summary)
        return self._summaries

    @property
    def terms(self):
        """Sequence of glossary terms for which the media will be used."""

        if not hasattr(self, "_terms"):
            self._terms = []
            for node in self.root.findall("ProposedUse/Glossary"):
                term = Doc.get_text(node, "").strip()
                if term:
                    self._terms.append(term)
        return self._terms

    @property
    def title(self):
        """String for the title of this Media document."""

        if not hasattr(self, "_title"):
            title = Doc.get_text(self.root.find("MediaTitle"), "")
            self._title = title.strip()
        return self._title

    @property
    def url(self):
        """Address of the script to fetch the document's media blob."""

        if not hasattr(self, "_url"):
            host = self.__control.session.tier.hosts["APPC"]
            self._url = self.URL.format(host, self.doc.id)
        return self._url


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
