#!/usr/bin/env python

"""Create a spreadsheet of glossary term names without pronunciations.

See the notes in GlossaryTermAudioReview.py for an overview of the
process for which the Excel workbook created by this script is used.
"""

from cdrcgi import Controller, Excel
from cdrapi.docs import Doc
from cdr import run_command


class Control(Controller):
    """Script logic encapsulated here."""

    SUBTITLE = "Audio Spreadsheet Creation"
    SUBMIT = None
    COLUMNS = (
        ("CDR ID", 10),
        ("Term Name", 30),
        ("Language", 10),
        ("Pronunciation", 30),
        ("Filename", 30),
        ("Notes (Vanessa)", 20),
        ("Notes (NCI)", 30),
        ("Reuse Media ID", 15),
    )
    NAME_PATH = "/GlossaryTermName/T%Name/TermNameString"
    MEDIA_PATH = "/GlossaryTermName/%/MediaLink/MediaID/@cdr:ref"
    REDO_PATH = "/GlossaryTermName/%/MediaLink/@NeedsReplacementMedia"

    def populate_form(self, page):
        """Generate the workbook and provide the link to it.

        Pass:
            page - HTMLPage object where we communicate with the user.
        """

        fieldset = page.fieldset("Glossary Term Names Without Pronunciation")
        if self.url:
            para = page.B.P(
                f"Pronunciation files are needed for {self.count} "
                "glossary term names. ",
                page.B.A("Download the workbook", href=self.url),
                " to track the creation and review of those pronunciation "
                "files."
            )
        else:
            para = page.B.P("No glossary term names need pronunciations.")
        fieldset.append(para)
        page.form.append(fieldset)

    @property
    def book(self):
        """Excel workbook contining the names without pronunciations."""

        if not hasattr(self, "_book"):
            self._book = book = Excel(f"Week_{self.week}")
            book.add_sheet("Term Names")
            styles = dict(alignment=book.center, font=book.bold)
            col = 1
            for name, width in self.COLUMNS:
                book.set_width(col, width)
                book.write(1, col, name, styles)
                col += 1
            row = 2
            counts = {}
            for doc in self.docs:
                for name in doc.names:
                    lang = "en" if name.language == "English" else "es"
                    filename = f"{doc.id}_{lang}"
                    if filename not in counts:
                        counts[filename] = 1
                    else:
                        counts[filename] += 1
                        n = counts[filename]
                        filename = f"{filename}{n}"
                    book.write(row, 1, doc.id)
                    book.write(row, 2, name.string)
                    book.write(row, 3, name.language)
                    book.write(row, 4, name.pronunciation)
                    book.write(row, 5, f"Week_{self.week}/{filename}.mp3")
                    if name.media_id:
                        book.write(row, 8, name.media_id)
                    row += 1
        return self._book

    @property
    def count(self):
        """Number of term names needing pronunciations."""

        if not hasattr(self, "_count"):
            self._count = sum([len(doc.names) for doc in self.docs])
        return self._count

    @property
    def docs(self):
        """Name documents with at least one name needing an MP3."""

        if not hasattr(self, "_docs"):
            query = self.Query("query_term n", "n.doc_id").order("n.doc_id")
            query.join("pub_proc_cg c", "c.id = n.doc_id")
            query.outer("query_term m", "m.doc_id = n.doc_id",
                        f"m.path LIKE '{self.MEDIA_PATH}'",
                        "LEFT(m.node_loc, 4) = LEFT(n.node_loc, 4)")
            query.outer("query_term r", "r.doc_id = n.doc_id",
                        f"r.path LIKE '{self.REDO_PATH}'", "r.value = 'Yes'")
            query.where(f"n.path LIKE '{self.NAME_PATH}'")
            query.where("m.doc_id IS NULL OR r.doc_id IS NOT NULL")
            rows = query.unique().execute(self.cursor).fetchall()
            self._docs = [TermNameDoc(self, row.doc_id) for row in rows]
        return self._docs

    @property
    def url(self):
        """Address of the new Excel workbook, if any."""

        if not hasattr(self, "_url"):
            self._url = None
            if self.book:
                directory = f"{self.session.tier.basedir}/reports"
                self.book.save(directory)
                path = f"{directory}/{self.book.filename}"
                path = path.replace("/", "\\")
                process = run_command(f"fix-permissions.cmd {path}")
                if process.stderr:
                    self.bail(f"Failure settings permissions for {path}",
                              extra=[process.stderr])
                self._url = f"/cdrReports/{self.book.filename}"
        return self._url

    @property
    def week(self):
        """String for the current week using ISO numbering."""

        if not hasattr(self, "_week"):
            year, week, day = self.started.isocalendar()
            self._week = f"{year}_{week:02d}"
        return self._week


class TermNameDoc:
    """Information for a CDR GlossaryTermName document."""

    NAME_ELEMENTS = "TermName", "TranslatedName"

    def __init__(self, control, id):
        """Capture the caller's information.

        Pass:
            control - access to the current session
            id - CDR ID for the GlossaryTermName document
        """

        self.__control = control
        self.__id = id

    @property
    def id(self):
        """CDR ID for the GlossaryTermName document."""
        return self.__id

    @property
    def session(self):
        """Needed for creating the `Doc` object."""
        return self.__control.session

    @property
    def doc(self):
        """Object with the parsed XML for the term name document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.session, id=self.id)
        return self._doc

    @property
    def names(self):
        """The term names and translated names for the glossary term."""

        if not hasattr(self, "_names"):
            self._names = []
            for tag in self.NAME_ELEMENTS:
                for node in self.doc.root.findall(tag):
                    name = self.Name(node)
                    if not name.exclude:
                        self._names.append(name)
        return self._names

    class Name:
        """One of the English or Spanish names in a glossary term name doc."""

        def __init__(self, node):
            """Capture the caller's information.

            Pass:
                node - parsed XML for the name
            """

            self.__node = node

        @property
        def node(self):
            """Parsed XML node for the name."""
            return self.__node

        @property
        def exclude(self):
            """Boolean; True if no audio recording is needed for this name."""

            if not hasattr(self, "_exclude"):
                self._exclude = self.node.get("AudioRecording") == "No"
                if not self._exclude:
                    if self.media_id and not self.needs_replacement:
                        self._exclude = True
            return self._exclude

        @property
        def language(self):
            """English or Spanish."""
            return "English" if self.node.tag == "TermName" else "Spanish"

        @property
        def media_id(self):
            """Media ID if we already have audio for this name."""

            if not hasattr(self, "_media_id"):
                self._media_id = None
                node = self.node.find("MediaLink/MediaID")
                if node is not None:
                    value = node.get(f"{{{Doc.NS}}}ref")
                    try:
                        self._media_id = Doc.extract_id(value)
                    except Exception:
                        pass
            return self._media_id

        @property
        def needs_replacement(self):
            """True if the existing media needs to be replaced."""

            if not hasattr(self, "_needs_replacement"):
                self._needs_replacement = None
                node = self.node.find("MediaLink")
                if node is not None:
                    self._needs_replacement = False
                    if node.get("NeedsReplacementMedia") == "Yes":
                        self._needs_replacement = True
            return self._needs_replacement

        @property
        def string(self):
            """The value of the name."""

            if not hasattr(self, "_string"):
                self._string = Doc.get_text(self.node.find("TermNameString"))
            return self._string

        @property
        def pronunciation(self):
            """Optional pronuciation string for the name."""

            if not hasattr(self, "_pronunciation"):
                self._pronunciation = None
                if self.language == "English":
                    node = self.node.find("TermPronunciation")
                    self._pronunciation = Doc.get_text(node)
            return self._pronunciation


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
