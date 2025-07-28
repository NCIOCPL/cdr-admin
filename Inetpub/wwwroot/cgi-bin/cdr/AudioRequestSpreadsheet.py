#!/usr/bin/env python

"""Create a spreadsheet of glossary term names without pronunciations.

See the notes in GlossaryTermAudioReview.py for an overview of the
process for which the Excel workbook created by this script is used.
"""

from functools import cached_property
from sys import platform
from cdrcgi import Controller, Excel
from cdrapi.docs import Doc
from cdr import run_command


class Control(Controller):
    """Script logic encapsulated here."""

    SUBTITLE = "Audio Spreadsheet Creation"
    COLUMNS = (
        ("CDR ID", 10, "unique ID for the GlossaryTermName document"),
        ("Term Name", 30, "string for the name needing pronunciation"),
        ("Language", 10, "English or Spanish"),
        ("Pronunciation", 30, "representation of the name's pronunciation"),
        ("Filename", 30, "relative path where the audio file will be stored"),
        ("Notes (Vanessa)", 20, "column where contractor can enter notes"),
        ("Notes (NCI)", 30, "for instructions provided to the contractor"),
        ("Reuse Media ID", 15, "optional ID of Media document to be reused"),
    )
    NAME_PATH = "/GlossaryTermName/T%Name/TermNameString"
    MEDIA_PATH = "/GlossaryTermName/%/MediaLink/MediaID/@cdr:ref"
    REDO_PATH = "/GlossaryTermName/%/MediaLink/@NeedsReplacementMedia"
    INSTRUCTIONS = (
        "Click Submit to request an Excel workbook in which are recorded "
        "GlossaryTermName documents with names which need to have audio "
        "pronunciation files created. This workbook can be edited, as "
        "appropriate, to reduce the amount of work requested, or to add "
        "instructions for the contractor who created the pronunciation "
        "files. The generation of the workbook may take up to a minute or "
        "two. The Term Names sheet (the only sheet in the workbook) contains "
        "the following columns:"
    )
    MORE_INSTRUCTIONS = (
        "The workbook will be posted by the contractor to the NCI sFTP server "
        "as part of a zipfile, which will also contain the individual MP3 "
        "audio pronunciation files, each located in the relative path shown "
        "in the Filename column of the workbook."
    )

    def populate_form(self, page):
        """Generate the workbook and provide the link to it.

        Pass:
            page - HTMLPage object where we communicate with the user.
        """

        if self.request != self.SUBMIT:
            fieldset = page.fieldset("Instructions")
            fieldset.append(page.B.P(self.INSTRUCTIONS))
            columns = page.B.UL(page.B.CLASS("usa-list"))
            for label, _, description in self.COLUMNS:
                extra = f" ({description})"
                columns.append(page.B.LI(page.B.STRONG(label), extra))
            fieldset.append(columns)
            fieldset.append(page.B.P(self.MORE_INSTRUCTIONS))
        else:
            legend = "Glossary Term Names Without Pronunciation"
            fieldset = page.fieldset(legend)
            if self.count:
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

    def show_report(self):
        """Redirect back to form."""
        self.show_form()

    @cached_property
    def book(self):
        """Excel workbook contining the names without pronunciations."""

        book = Excel(f"Week_{self.week}")
        book.add_sheet("Term Names")
        styles = dict(alignment=book.center, font=book.bold)
        col = 1
        for name, width, _ in self.COLUMNS:
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
        return book

    @cached_property
    def buttons(self):
        """Hide the Submit button on the second page."""
        return [] if self.request == self.SUBMIT else [self.SUBMIT]

    @cached_property
    def count(self):
        """Number of term names needing pronunciations."""
        return sum([len(doc.names) for doc in self.docs])

    @cached_property
    def docs(self):
        """Name documents with at least one name needing an MP3."""

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
        return [TermNameDoc(self, row.doc_id) for row in rows]

    @property
    def same_window(self):
        """Don't open new browser tabs."""
        return [self.SUBMIT]

    @cached_property
    def url(self):
        """Address of the new Excel workbook, if any."""

        if self.book:
            directory = f"{self.session.tier.basedir}/reports"
            self.book.save(directory)
            path = f"{directory}/{self.book.filename}"
            if platform == "win32":
                path = path.replace("/", "\\")
                process = run_command(f"fix-permissions.cmd {path}")
                if process.stderr:
                    message = f"Failure settings permissions for {path}"
                    self.bail(message, extra=[process.stderr])
            return f"/cdrReports/{self.book.filename}"
        return None

    @cached_property
    def week(self):
        """String for the current week using ISO numbering."""

        year, week, day = self.started.isocalendar()
        return f"{year}_{week:02d}"


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

    @cached_property
    def doc(self):
        """Object with the parsed XML for the term name document."""
        return Doc(self.session, id=self.id)

    @cached_property
    def names(self):
        """The term names and translated names for the glossary term."""

        names = []
        for tag in self.NAME_ELEMENTS:
            for node in self.doc.root.findall(tag):
                name = self.Name(node)
                if not name.exclude:
                    names.append(name)
        return names

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

        @cached_property
        def exclude(self):
            """Boolean; True if no audio recording is needed for this name."""

            exclude = self.node.get("AudioRecording") == "No"
            if not exclude:
                if self.media_id and not self.needs_replacement:
                    exclude = True
            return exclude

        @cached_property
        def language(self):
            """English or Spanish."""
            return "English" if self.node.tag == "TermName" else "Spanish"

        @cached_property
        def media_id(self):
            """Media ID if we already have audio for this name."""

            node = self.node.find("MediaLink/MediaID")
            if node is not None:
                value = node.get(f"{{{Doc.NS}}}ref")
                try:
                    return Doc.extract_id(value)
                except Exception:
                    pass
            return None

        @cached_property
        def needs_replacement(self):
            """True if the existing media needs to be replaced."""

            needs_replacement = None
            node = self.node.find("MediaLink")
            if node is not None:
                needs_replacement = False
                if node.get("NeedsReplacementMedia") == "Yes":
                    needs_replacement = True
            return needs_replacement

        @cached_property
        def string(self):
            """The value of the name."""
            return Doc.get_text(self.node.find("TermNameString"))

        @cached_property
        def pronunciation(self):
            """Optional pronuciation string for the name."""

            if self.language == "English":
                node = self.node.find("TermPronunciation")
                return Doc.get_text(node)
            return None


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
