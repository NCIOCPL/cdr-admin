#!/usr/bin/env python

"""Add and link to glossary pronunciation Media documents.

Invoked from the CDR Admin web menu.

If for any reason this script will not process the correct set of
zip files (for example, because a file name did not match the
agreed pattern of "Week_YYYY_WW[_RevN].zip" or the file names for
a batch do not sort in the order the files should be processed),
then it will be necessary to have a developer load the batch from
the bastion host using DevTools/Utilities/Request4926.py.

JIRA::OCECDR-3373
"""

from glob import glob
from io import BytesIO
from re import search, IGNORECASE
from zipfile import ZipFile
from lxml import etree
from mutagen.mp3 import MP3
from openpyxl import load_workbook
from cdrapi.docs import Doc
from cdrcgi import Controller
from ModifyDocs import Job


class Control(Controller):
    """Top-level logic for the import job and its report."""

    SUBTITLE = "Load Glossary Audio Files"
    LOGNAME = "LoadGlossaryAudioFiles"
    AUDIO = "Audio_from_CIPSFTP"
    WEEK = r"Week_\d{4}_\d\d"
    INSTRUCTIONS = (
        "Press the Submit button to create Media documents for the MP3 files "
        "contained in the archive files listed below, and have those "
        "documents linked from the corresponding GlossaryTermName documents. "
        "Archives will be processed in the order in which they appear in this "
        "list, with MP3 clips found in later archives overriding those found "
        "in earlier archives. If this set is not the correct set of archives "
        "to be processed, please contact a CDR developer to have the audio "
        "files imported manually."
    )
    PERMISSIONS = (
        ("ADD DOCUMENT", "Media"),
        ("MODIFY DOCUMENT", "Media"),
        ("MODIFY DOCUMENT", "GlossaryTermName"),
        ("AUDIO IMPORT", None),
    )

    def build_tables(self):
        """Assemble the table reporting the documents we created/updated."""

        Linker(self).run()
        return self.Reporter.Table(self.rows, columns=self.columns)

    def populate_form(self, page):
        """Show the user the proposed list of zipfiles to be processed.

        Pass:
            page - object on which we draw the information
        """

        fieldset = page.fieldset()
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Compressed Archives containing Audio files")
        ordered_list = page.B.OL()
        for zipfile in self.zipfiles:
            ordered_list.append(page.B.LI(zipfile))
        fieldset.append(ordered_list)
        page.form.append(fieldset)

    @property
    def columns(self):
        """Column headers for the report."""

        if not hasattr(self, "_columns"):
            self._columns = (
                self.Reporter.Column("CDR ID"),
                self.Reporter.Column("Processing"),
            )
        return self._columns

    @property
    def directory(self):
        """Where the ZIP files live."""
        return f"{self.session.tier.basedir}/{self.AUDIO}"

    @property
    def rows(self):
        """Table rows reporting what we did for each document."""

        if not hasattr(self, "_rows"):
            self._rows = []
        return self._rows

    @property
    def term_docs(self):
        """Dictionary of term name docs for which we have new MP3 files."""

        # Do all this work only once, caching the resulting dictionary.
        if not hasattr(self, "_term_docs"):
            self._term_docs = {}

            # Don't log skipping the same term name document multiple times.
            skipped = set()

            for path in self.zipfiles:
                zipfile = ZipFile(f"{self.directory}/{path}")

                # Use these for logging multiple occurrences of values.
                filenames = set()
                termnames = set()

                # Find the Excel workbook in the zipfile.
                bookpath = None
                for name in zipfile.namelist():
                    if "MACOSX" not in name and name.endswith(".xlsx"):
                        bookpath = name
                if bookpath is None:
                    self.bail(f"no workbook in {path}")
                opts = dict(read_only=True, data_only=True)
                book = load_workbook(BytesIO(zipfile.read(bookpath)), **opts)
                sheet = book.active
                for row in sheet:

                    # Skip over the column header row.
                    if isinstance(self.get_cell_value(row, 0), (int, float)):
                        mp3 = AudioFile(self, path, zipfile, row)

                        # Check for unexpected multiple occurrences.
                        key = mp3.filename.lower()
                        if key in filenames:
                            logger.warning("multiple %r in %s", key, path)
                        filenames.add(key)
                        key = (mp3.term_id, mp3.name, mp3.language)
                        if key in termnames:
                            logger.warning("multiple %r in %s", key, path)
                        termnames.add(key)

                        # Add the MP3 file to the term document object.
                        doc = self._term_docs.get(mp3.term_id)
                        if doc is None:
                            doc = self._term_docs[mp3.term_id] = TermDoc()
                        doc.add(mp3)

            # Save the new or updated Media documents.
            self.logger.info("term ids: %s", sorted(self._term_docs))
            for id in self._term_docs:
                for mp3 in self._term_docs[id].mp3s:
                    mp3.save()

        return self._term_docs

    @property
    def zipfiles(self):
        """Most recent set of audio archive files.

        Collect the list of zip files representing the most recent batch
        of audio files to be loaded into the CDR. The behavior of the
        software relies on some assumptions.

          1. The zip file names all start with a "Week_YYYY_WW" prefix.
          2. All files in a single batch have the same prefix.
          3. The names, when sorted (without regard to case) are in
             order, corresponding to when the zip file was given to NCI.
          4. The users will pay attention to the list displayed, and
             either confirm if the list represents the correct set of
             files to be processed (in the correct order), or submit
             a request for a developer to import the files manually.

        Constructs a possibly empty sequence of filenames, sorted without
        regard to case differences.
        """

        # Don't waste the user's time unnecessarily.
        for action, doctype in self.PERMISSIONS:
            if not self.session.can_do(action, doctype):
                self.bail("Unauthorized")

        # Collect files for each week
        if not hasattr(self, "_zipfiles"):
            weeks = {}
            for path in glob(f"{self.directory}/Week_*.zip"):
                match = search(f"(({self.WEEK}).*.zip)", path, IGNORECASE)
                if match:
                    name = match.group(1)
                    week = match.group(2).upper()
                    if week not in weeks:
                        weeks[week] = []
                    weeks[week].append(name)
                else:
                    self.logger.warning("skipping %r", path)
            if not weeks:
                self.bail("Nothing to be loaded")
            week = sorted(weeks)[-1]
            self._zipfiles = sorted(weeks[week], key=str.upper)
            self.logger.info("zipfiles: %s", self._zipfiles)
        return self._zipfiles

    @staticmethod
    def get_cell_value(row, col):
        """Extract value from a cell in an Excel spreadsheet.

        Pass:
            row - indexable object for a row of cells in the worksheet
            col - integer offset of the column's position in the row

        Return:
            value of the cell if it exists or None
        """

        try:
            return row[col].value
        except:
            return None


class AudioFile:
    """Object representing a single pronunciation audio file."""

    CREATOR = "Vanessa Richardson, VR Voice"
    COMMENT = f"Saved by {Control.SUBTITLE} script"
    TERM_ID = 0
    NAME = 1
    LANGUAGE = 2
    FILENAME = 4
    MEDIA_ID = 7
    CDR_REF = f"{{{Doc.NS}}}ref"
    GLOSSARY_TERM_NAME_TAGS = dict(en="TermName", es="TranslatedName")
    MESSAGE = "{} Media doc for CDR{:d} ({!r} [{}]) from {}"
    BEFORE_MEDIA_LINK = set(
        "TermNameString",
        "TermPronunciation",
        "PronunciationResource",
        "TranslationResource",
    )

    def __init__(self, control, path, zipfile, row):
        """Remember initial values from caller.

        Pass:
            control - access to logging and the database
            path - location of the zipfile
            zipfile - archive containing the audio files
            row - cell values from a spreadsheet row
        """

        self.__control = control
        self.__path = path
        self.__zipfile = zipfile
        self.__row = row

    def save(self):
        """Create or update the Media document for this audio file."""

        if self.media_id:
            doc = Doc(self.__control.session, id=self.media_id)
            if doc.doctype.name != "Media":
                raise Exception(f"CDR{self.media_id} is not a Media document")
            doc.check_out(comment="re-using media document")
            doc.blob = self.bytes
            action = "updated"
        else:
            opts = dict(xml=self.xml, blob=self.bytes, doctype="Media")
            doc = Doc(self.__control.session, **opts)
            action = "created"
        opts = dict(
            version=True,
            publishable=True,
            comment=self.COMMENT,
            reason=self.COMMENT,
            val_types=("schema", "links"),
            unlock=True,
        )
        doc.save(**opts)
        args = action, self.term_id, self.name, self.langcode, self.__path
        message = self.MESSAGE.format(*args)
        self.__control.rows.append((f"CDR{doc.id}", message))
        self.__control.logger.info("%s as CDR%d", message, doc.id)
        self.media_id = doc.id

    @property
    def bytes(self):
        """Binary content of the audio file."""

        if not hasattr(self, "_bytes"):
            self._bytes = self.__zipfile.read(self.filename)
        return self._bytes

    @property
    def created(self):
        """Date string for when the audio file was created."""

        if not hasattr(self, "_created"):
            info = self.__zipfile.getinfo(self.filename)
            self._created = "{:04d}-{:02d}-{:02d}".format(*info.date_time[:3])
        return self._created

    @property
    def creator(self):
        """String for the Creator element in the Media document."""

        if not hasattr(self, "_creator"):
            query = self.__control.Query("ctl", "val")
            query.where("grp = 'media'")
            query.where("name = 'audio-pronunciation-creator'")
            query.where("inactivated IS NULL")
            rows = query.execute(self.__control.cursor).fetchall()
            if rows:
                self._creator = rows[0].val
            else:
                self._creator = self.CREATOR
        return self._creator

    @property
    def duration(self):
        """Runtime length in seconds for the MP3 audio file."""

        if not hasattr(self, "_duration"):
            mp3 = MP3(BytesIO(self.bytes))
            self._duration = int(round(mp3.info.length))
            self.__control.logger.debug("runtime is %s", self._duration)
        return self._duration

    @property
    def filename(self):
        """Where to find the MP3 bytes in the zipfile."""

        if not hasattr(self, "_filename"):
            self._filename = self.__cell(self.FILENAME)
        return self._filename

    @property
    def language(self):
        """English or Spanish."""

        if not hasattr(self, "_language"):
            self._language = self.__cell(self.LANGUAGE)
            if self._language not in ("English", "Spanish"):
                raise Exception(f"Unexpected language {self._language!r}")
        return self._language

    @property
    def langcode(self):
        """ISO code for language (en or es)."""

        if not hasattr(self, "_langcode"):
            self._langcode = "en" if self.language == "English" else "es"
        return self._langcode

    @property
    def link_node(self):
        """MediaLink element linking to this audio file's CDR document.

        Create an element representing a link to this audio file's Media
        document, for insertion into the XML document for the linking
        GlossaryTermName document. Don't cache this, as we need a separate
        instance for each link.
        """

        element = etree.Element("MediaLink")
        child = etree.SubElement(element, "MediaID")
        child.text = f"{self.title}; pronunciation; mp3"
        child.set(self.CDR_REF, f"CDR{self.media_id:010d}")
        return element

    @property
    def media_id(self):
        """CDR document ID for this pronunciation file."""

        if not hasattr(self, "_media_id"):
            self._media_id = self.__cell(self.MEDIA_ID)
            if self._media_id:
                self._media_id = int(self._media_id)
        return self._media_id

    @media_id.setter
    def media_id(self, value):
        """Set this when the document is created.

        Pass:
            value - integer for the newly created Media document
        """

        self._media_id = value

    @property
    def name(self):
        """String for the glossary term name being pronounced."""

        if not hasattr(self, "_name"):
            self._name = self.__cell(self.NAME)
            if self._name:
                self._name = self._name.strip()
        return self._name

    @property
    def name_title(self):
        """Full CDR document title for the GlossaryTermName document."""

        if not hasattr(self, "_name_title"):
            query = self.__control.Query("document", "title")
            query.where(query.Condition("id", self.term_id))
            row = query.execute(self.__control.cursor).fetchone()
            if not row:
                raise Exception(f"Term name CDR{self.term_id} not found")
            self._name_title = row.title
        return self._name_title

    @property
    def term_id(self):
        """CDR ID for the pronunciation's GlossaryTermName document."""

        if not hasattr(self, "_term_id"):
            self._term_id = int(self.__cell(self.TERM_ID))
        return self._term_id

    @property
    def title(self):
        """String used for the MediaTitle and MediaLink elements."""

        if not hasattr(self, "_title"):
            self._title = self.name_title.split(";")[0]
            if self.language == "Spanish":
                self._title += "-Spanish"
        return self._title

    @property
    def today(self):
        """String for today's date in ISO format."""

        if not hasattr(self, "_today"):
            self._today = self.__control.started.strftime("%Y-%m-%d")
        return self._today

    @property
    def xml(self):
        """Serialized XML for a new CDR Media document for this audio file."""

        root = etree.Element("Media", nsmap=Doc.NSMAP)
        root.set("Usage", "External")
        etree.SubElement(root, "MediaTitle").text = self.title

        # Add the physical characteristics of the media file.
        physical_media = etree.SubElement(root, "PhysicalMedia")
        sound_data = etree.SubElement(physical_media, "SoundData")
        etree.SubElement(sound_data, "SoundType").text = "Speech"
        etree.SubElement(sound_data, "SoundEncoding").text = "MP3"
        etree.SubElement(sound_data, "RunSeconds").text = str(self.duration)

        # Add the source information.
        media_source = etree.SubElement(root, "MediaSource")
        original_source = etree.SubElement(media_source, "OriginalSource")
        etree.SubElement(original_source, "Creator").text = self.creator
        etree.SubElement(original_source, "DateCreated").text = self.created
        source_filename = etree.SubElement(original_source, "SourceFilename")
        source_filename.text = self.filename

        # Add the elements describing the media's content.
        media_content = etree.SubElement(root, "MediaContent")
        categories = etree.SubElement(media_content, "Categories")
        etree.SubElement(categories, "Category").text = "pronunciation"
        descs = etree.SubElement(media_content, "ContentDescriptions")
        desc = etree.SubElement(descs, "ContentDescription")
        desc.text = f'Pronunciation of dictionary term "{self.name}"'
        desc.set("audience", "Patients")
        desc.set("language", self.langcode)

        # Identify what the media file will be used for.
        proposed_use = etree.SubElement(root, "ProposedUse")
        glossary = etree.SubElement(proposed_use, "Glossary")
        glossary.set(self.CDR_REF, f"CDR{self.term_id:010d}")
        glossary.text = self.name_title
        return etree.tostring(root, pretty_print=True, encoding="unicode")

    def __cell(self, col):
        """Convenience method for fetching values from the spreadsheet row."""
        return Control.get_cell_value(self.__row, col)

    def update_name(self, root):
        """Make appropriate changes to GTN doc for one of its term names.

        Here are the child elements in the term name blocks.
            TermNameString [required]
            TermPronunciation [en, optional]
            PronunciationResource [en, optional, multiple allowed]
            TranslationResource [es, optional, multiple allowed]
            MediaLink [optional, but will be added here if missing]
            TermNameSource [en, optional]
            TranslatedNameStatus [es, required]
            TranslatedNameStatusDate [es, optional]
            TermNameVerificationResource [en, optional, multiple allowed]
            Comment [optional, multiple allowed]
            DateLastModified [optional, but will be added here if missing]
        Pass:
            root - top-level object for parsed GlossaryTermName document

        Return:
            string "Updating" or "Adding" as appropriate
        """

        node = None
        verb = "Updating"
        error = f"unable to find home for {self.name!r} in CDR{self.term_id}"
        path = f"{self.GLOSSARY_TERM_NAME_TAGS[self.langcode]}/TermNameString"
        for term_name_string in root.findall(path):
            if self.name == term_name_string.text:
                node = name.getparent()
                break
        if node is None:
            error = f"unable to find {self.name!r} in CDR{self.term_id}"
            raise Exception(error)
        date_last_modified = node.find("DateLastModified")
        if date_last_modified is None:
            date_last_modified = etree.SubElement(node, "DateLastModified")
        date_last_modified.text = self.today
        media_link = node.find("MediaLink")
        if media_link is None:
            verb = "Adding"
            sibling = current = term_name_string
            while current is not None:
                next = current.getnext()
                if next is not None:
                    if isinstance(next.tag, str):
                        if next.tag in self.BEFORE_MEDIA_LINK:
                            sibling = next
                        else:
                            break
                current = next
            sibling.addnext(self.link_node)
        else:
            node.replace(media_link, self.link_node)
            sibling = self.link_node
            while sibling.tag not in ("Comment", "DateLastModified"):
                sibling = sibling.getnext()
            comment = etree.Element("Comment")
            comment.text = "Approved audio re-recording linked"
            sibling.addprevious(comment)
        return verb


class TermDoc:
    """GlossaryTermName document and its `AudioFile` objects."""

    def add(self, mp3):
        """Insert the `AudioFile` object into our nested `names` dictionary.

        Pass:
            mp3 - `AudioFile` object created for this glossary term name
        """
        if mp3.name not in self.names:
            self.names[mp3.name] = dict(English=[], Spanish=[])
        self.names[mp3.name][mp3.language].append(mp3)

    @property
    def mp3s(self):
        """Sequence of audio files to be saved and linked."""

        if not hasattr(self, "_mp3s"):
            self._mp3s = []
            for name in self.names:
                for language in self.names[name]:
                    if self.names[name][language]:
                        self._mp3s.append(self.names[name][language][-1])
        return self._mp3s

    @property
    def names(self):
        """Nested dictionary of `AudioFile` objects.

        The top-level index is by name, under which are nested dictionaries
        indexed by language. Populated by calls to the `add()` method.
        """

        if not hasattr(self, "_names"):
            self._names = {}
        return self._names


class Linker(Job):
    """Job for adding MediaLink elements to GlossaryTermName docs.

    Implements the interface used by the ModifyDocs module, returning
    the list of IDs for the documents to be modified, and performing
    the actual document modifications.
    """

    LOGNAME = "LoadGlossaryAudioFiles"
    COMMENT = "Setting links from glossary term name docs to media docs"
    MESSAGE = "{} link from this document to Media document CDR{:d}"

    def __init__(self, control):
        """Capture the caller's value and initialize the base class.

        Pass:
            control - access to the rows for the report (to which we
                      contribute), and the term names and their audio files
        """

        self.__control = control
        opts = dict(session=control.session, mode="live", console=False)
        Job.__init__(self, **opts)

    def select(self):
        """Provide the sorted GlossaryTermName document IDs."""
        return sorted(self.__control.term_docs)

    def transform(self, doc):
        """Add `MediaLink` elements to the GlossaryTermName document.

        Pass:
            doc - `cdr.Doc` object

        Return:
            Possibly transformed XML
        """

        int_id = Doc.extract_id(doc.id)
        cdr_id = f"CDR{int_id:d}"
        try:
            root = etree.fromstring(doc.xml)
            for mp3 in self.__control.term_docs[int_id].mp3s:
                verb = mp3.update_name(root)
                message = self.MESSAGE.format(verb, mp3.media_id)
                self.__control.rows.append((cdr_id, message))
                self.logger.info(message.replace("this document", cdr_id))
            return etree.tostring(root)
        except Exception as e:
            self.logger.exception(cdr_id)
            self.__control.rows.append([cdr_id, str(e)])
            return doc.xml


if __name__ == "__main__":
    """Only execute if loaded as a script."""
    Control().run()
