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

from datetime import date
from functools import cached_property
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
    TODAY = date.today().strftime("%Y-%m-%d")
    AUDIO = "Audio_from_CIPSFTP"
    WEEK = r"Week_\d{4}_\d\d"
    CREATOR = "Vanessa Richardson, VR Voice"
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
    NONE = "All available audio files sets have been loaded."

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
        if not self.zipfiles:
            fieldset.append(page.B.P(self.NONE))
        page.form.append(fieldset)

    @cached_property
    def columns(self):
        """Column headers for the report."""

        return (
            self.Reporter.Column("CDR ID"),
            self.Reporter.Column("Processing"),
        )

    @cached_property
    def creator(self):
        """String for the Creator element in the Media document."""

        query = self.Query("ctl", "val")
        query.where("grp = 'media'")
        query.where("name = 'audio-pronunciation-creator'")
        query.where("inactivated IS NULL")
        rows = query.execute(self.cursor).fetchall()
        if rows:
            return rows[0].val
        else:
            return self.CREATOR

    @cached_property
    def directory(self):
        """Where the ZIP files live."""
        return f"{self.session.tier.basedir}/{self.AUDIO}"

    @cached_property
    def rows(self):
        """Table rows reporting what we did for each document."""
        return []

    @cached_property
    def term_docs(self):
        """Dictionary of term name docs for which we have new MP3 files."""

        # Handle the case in which nothing is ready to be loaded.
        if not self.zipfiles:
            return {}

        # Process each zip archive.
        for path in self.zipfiles:
            zipfile = ZipFile(f"{self.directory}/{path}")

            # Use these for logging multiple occurrences of values.
            filenames = set()
            termnames = set()

            # Find the Excel workbook in the zipfile.
            term_docs = {}
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
                        self.logger.warning("multiple %r in %s", key, path)
                    filenames.add(key)
                    key = (mp3.term_id, mp3.name, mp3.language)
                    if key in termnames:
                        self.logger.warning("multiple %r in %s", key, path)
                    termnames.add(key)

                    # Add the MP3 file to the term document object.
                    doc = term_docs.get(mp3.term_id)
                    if doc is None:
                        doc = term_docs[mp3.term_id] = TermDoc()
                    doc.add(mp3)

        # Save the new or updated Media documents.
        self.logger.info("term ids: %s", sorted(term_docs))
        old = {}
        for term_doc in term_docs.values():
            for mp3 in term_doc.mp3s:
                if mp3.media_id:
                    old[mp3.media_id] = mp3
                mp3.save()
        if old:
            Updater(self, old).run()

        return term_docs

    @cached_property
    def user(self):
        """User login name for this run."""
        return self.session.User(self.session, id=self.session.user_id).name

    @cached_property
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
            return []
        week = sorted(weeks)[-1]
        zipfiles = sorted(weeks[week], key=str.upper)
        self.logger.info("zipfiles: %s", zipfiles)
        return zipfiles

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
        except Exception:
            return None


class AudioFile:
    """Object representing a single pronunciation audio file."""

    COMMENT = f"Saved by {Control.SUBTITLE} script"
    TERM_ID = 0
    NAME = 1
    LANGUAGE = 2
    FILENAME = 4
    MEDIA_ID = 7
    CDR_REF = f"{{{Doc.NS}}}ref"
    GLOSSARY_TERM_NAME_TAGS = dict(en="TermName", es="TranslatedName")
    MESSAGE = "{} Media doc for CDR{:d} ({!r} [{}]) from {}"
    BEFORE_MEDIA_LINK = {
        "TermNameString",
        "TermPronunciation",
        "PronunciationResource",
        "TranslationResource",
    }

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
        """Create the Media document for this audio file.

        With changes introduced by CDR Maxwell, we also update Media
        documents which are being recycled with a new audio pronunciation
        recording. For those we defer the updating of those documents
        to be done in a batch using the global change harness, and
        only log them here. See OCECDR-4890 and other Maxwell tickets.
        """

        if self.media_id:
            doc = Doc(self.__control.session, id=self.media_id)
            if doc.doctype.name != "Media":
                raise Exception(f"CDR{self.media_id} is not a Media document")
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
            self.media_id = doc.id
        args = action, self.term_id, self.name, self.langcode, self.__path
        message = self.MESSAGE.format(*args)
        self.__control.rows.append((f"CDR{doc.id}", message))
        self.__control.logger.info("%s as CDR%d", message, doc.id)

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
                node = term_name_string.getparent()
                break
        if node is None:
            error = f"unable to find {self.name!r} in CDR{self.term_id}"
            raise Exception(error)
        date_last_modified = node.find("DateLastModified")
        if date_last_modified is None:
            date_last_modified = etree.SubElement(node, "DateLastModified")
        date_last_modified.text = Control.TODAY
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
            link_node = self.link_node
            node.replace(media_link, link_node)
            sibling = link_node
            while sibling.tag not in ("Comment", "DateLastModified"):
                sibling = sibling.getnext()
            comment = etree.Element("Comment")
            comment.text = "Approved audio re-recording linked"
            sibling.addprevious(comment)
        return verb

    @cached_property
    def bytes(self):
        """Binary content of the audio file."""

        try:
            return self.__zipfile.read(self.filename)
        except Exception as e:
            self.__control.logger.exception("fetching mp3 bytes")
            self.__control.bail(e)

    @cached_property
    def created(self):
        """Date string for when the audio file was created."""

        info = self.__zipfile.getinfo(self.filename)
        return "{:04d}-{:02d}-{:02d}".format(*info.date_time[:3])

    @cached_property
    def duration(self):
        """Runtime length in seconds for the MP3 audio file."""

        mp3 = MP3(BytesIO(self.bytes))
        duration = int(round(mp3.info.length))
        self.__control.logger.debug("runtime is %s", duration)
        return duration

    @cached_property
    def filename(self):
        """Where to find the MP3 bytes in the zipfile."""
        return self.__cell(self.FILENAME)

    @cached_property
    def language(self):
        """English or Spanish."""

        language = self.__cell(self.LANGUAGE)
        if language not in ("English", "Spanish"):
            raise ValueError(f"Unexpected language {language!r}")
        return language

    @cached_property
    def langcode(self):
        """ISO code for language (en or es)."""
        return "en" if self.language == "English" else "es"

    @property
    def link_node(self):
        """MediaLink element linking to this audio file's CDR document.

        Create an element representing a link to this audio file's Media
        document, for insertion into the XML document for the linking
        GlossaryTermName document. Don't cache this, as we need a separate
        instance for each link. By the same token, don't reference this
        property twice if you don't want two separate nodes.
        """

        element = etree.Element("MediaLink")
        child = etree.SubElement(element, "MediaID")
        child.text = f"{self.title}; pronunciation; mp3"
        child.set(self.CDR_REF, f"CDR{self.media_id:010d}")
        return element

    @cached_property
    def media_id(self):
        """CDR document ID for this pronunciation file."""

        media_id = self.__cell(self.MEDIA_ID)
        return int(media_id) if media_id else media_id

    @cached_property
    def name(self):
        """String for the glossary term name being pronounced."""

        name = self.__cell(self.NAME)
        return name.strip() if name else name

    @cached_property
    def name_title(self):
        """Full CDR document title for the GlossaryTermName document."""

        query = self.__control.Query("document", "title")
        query.where(query.Condition("id", self.term_id))
        row = query.execute(self.__control.cursor).fetchone()
        if not row:
            raise Exception(f"Term name CDR{self.term_id} not found")
        return row.title

    @cached_property
    def path(self):
        """Name of the zipfile fromwhich we got this MP3."""
        return self.__path

    @cached_property
    def term_id(self):
        """CDR ID for the pronunciation's GlossaryTermName document."""
        return int(self.__cell(self.TERM_ID))

    @cached_property
    def title(self):
        """String used for the MediaTitle and MediaLink elements."""

        title = self.name_title.split(";")[0]
        if self.language == "Spanish":
            title += "-Spanish"
        return title

    @cached_property
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
        creator = self.__control.creator
        etree.SubElement(original_source, "Creator").text = creator
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

    @cached_property
    def mp3s(self):
        """Sequence of audio files to be saved and linked."""

        mp3s = []
        for name in self.names:
            for language in self.names[name]:
                if self.names[name][language]:
                    mp3s.append(self.names[name][language][-1])
        return mp3s

    @cached_property
    def names(self):
        """Nested dictionary of `AudioFile` objects.

        The top-level index is by name, under which are nested dictionaries
        indexed by language. Populated by calls to the `add()` method.
        """

        return {}


class Linker(Job):
    """Job for adding MediaLink elements to GlossaryTermName docs.

    Implements the interface used by the ModifyDocs module, returning
    the list of IDs for the documents to be modified, and performing
    the actual document modifications.
    """

    LOGNAME = Control.LOGNAME
    COMMENT = f"GTN Doc MediaLink updated {Control.TODAY}"
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


class Updater(Job):
    """Modify the reused Media documents.

    Implementing enhancement for OCECDR-4890:
      Update MediaTitle
        For English, use the TermNameString for the English TermName
        For Spanish, use the same (English) name with "-Spanish" appended
      Update MediaSource/OriginalSource elements
        Creator = "Vanessa RichardsonVanessa Richardson, VR Voice"
        DateCreated = today (YYYY-MM-DD string)
        SourceFilename = WEEK_DIRECTORY/GTN-CDR-INTEGER-ID_e[ns]_rr.mp3
      Update ContentDescription element:
        text = 'Pronunciation of dictionary term "{mp3.name}"'
      Add two new ProcessingStatus blocks
        for value in "Processing Complete", "Audio re-recording approved":
          ProcessingStatusValue = {value}
          ProcessingStatusDate = today (YYYY-MM-DD string)
          EnteredBy = self.__control.user

    Implements the interface used by the ModifyDocs module, returning
    the list of IDs for the documents to be modified, and performing
    the actual document modifications.

    Modification for OCECDR-4924: use the creation date for the MP3 file
    from the zip info instead of the current system date for the DateCreated
    element.
    """

    LOGNAME = Control.LOGNAME
    COMMENT = f"Media Doc updated with rerecorded audio file – {Control.TODAY}"
    WARNING = "Multiple ContentDescription elements"
    STATUSES = "Audio re-recording approved", "Processing Complete"
    DESC_PATH = "MediaContent/ContentDescriptions/ContentDescription"
    INSERT_BEFORE = {
        "DateLastModified",
        "RelatedDocuments",
        "TranslationOf",
        "Comment",
    }

    def __init__(self, control, docs):
        """Capture the caller's value and initialize the base class.

        Pass:
            control - access to the rows for the report (to which we
                      contribute), and the term names and their audio files
            docs - dictionary of recycled Media Doc object, indexed by CDR ID
        """

        self.__control = control
        self.__docs = docs
        opts = dict(session=control.session, mode="live", console=False)
        Job.__init__(self, **opts)

    def get_blob(self, doc_id):
        """Provide the MP3 bytes for a specific Media document.

        Pass:
            doc_id - integer for the CDR Media document ID

        Return:
            bytes for the MP3 audio file
        """

        return self.__docs[doc_id].bytes

    def select(self):
        """Provide the sorted Media document IDs."""
        return sorted(self.__docs)

    def transform(self, doc):
        """Apply changes requested by OCECDR-4890.

        Pass:
            doc - `cdr.Doc` object

        Return:
            Possibly transformed XML
        """

        int_id = Doc.extract_id(doc.id)
        cdr_id = f"CDR{int_id:d}"
        mp3 = self.__docs[int_id]
        try:
            root = etree.fromstring(doc.xml)
            self.__update_title(root, mp3)
            self.__update_source(root, mp3)
            self.__update_description(root, mp3)
            self.__update_status(root, mp3)
            return etree.tostring(root)
        except Exception as e:
            self.logger.exception(cdr_id)
            self.__control.rows.append([cdr_id, str(e)])
            return doc.xml

    def __update_description(self, root, mp3):
        """Set the ContentDescription element of the document.

        Pass:
            root - top-level element of the Media document
            mp3 - AudioFile object
        """

        descriptions = [node for node in root.findall(self.DESC_PATH)]
        if not descriptions:
            raise Exception("required ContentDescription missing")
        if len(descriptions) == 1:
            description = f'Pronunciation of dictionary term "{mp3.name}"'
            descriptions[0].text = description
        else:
            self.__control.rows.append((f"CDR{mp3.media_id:d}", self.WARNING))
            self.logger.warning("%s for CDR%d", self.WARNING, mp3.media_id)

    def __update_source(self, root, mp3):
        """Set the current values for the OriginalSource block.

        Pass:
            root - top-level element of the Media document
            mp3 - AudioFile object
        """

        parent = root.find("MediaSource/OriginalSource")
        if parent is None:
            grandparent = root.find("MediaSource")
            if grandparent is None:
                sibling = root.find("PhysicalMedia")
                if sibling is None:
                    sibling = root.find("MediaTitle")
                grandparent = etree.Element("MediaSource")
                sibling.addnext(grandparent)
            parent = etree.Element("OriginalSource")
            grandparent.insert(0, parent)
        creator_node = parent.find("Creator")
        if creator_node is None:
            creator_node = etree.Element("Creator")
            parent.insert(0, creator_node)
        creator_node.text = self.__control.creator
        created_node = parent.find("DateCreated")
        if created_node is None:
            created_node = etree.Element("DateCreated")
            sibling = parent.find("SourcePublication")
            if sibling is None:
                sibling = [parent.findall("Creator")][-1]
            sibling.addnext(created_node)
        created_node.text = mp3.created
        filename_node = parent.find("SourceFilename")
        if filename_node is None:
            filename_node = etree.Element("SourceFilename")
            comment_node = parent.find("Comment")
            if comment_node is None:
                parent.append(filename_node)
            else:
                comment_node.addprevious(filename_node)
        filename = f"{mp3.term_id}_{mp3.langcode}_rr.mp3"
        filename_node.text = f"{mp3.path[:-4]}/{filename}"

    def __update_title(self, root, mp3):
        """Set the new title of the document in case the name changed.

        Pass:
            root - top-level element of the Media document
            mp3 - AudioFile object
        """

        node = root.find("MediaTitle")
        if node is None:
            node = etree.Subtitle(root, "MediaTitle")
        node.text = mp3.title

    def __update_status(self, root, mp3):
        """Insert a couple of new ProcessingStatus elements.

        Pass:
            root - top-level element of the Media document
            mp3 - AudioFile object
        """

        statuses = root.find("ProcessingStatuses")
        if statuses is None:
            statuses = etree.Element("ProcessingStatuses")
            sibling = None
            for node in root.findall("*"):
                if node.tag in self.INSERT_BEFORE:
                    sibling = node
                    break
            if sibling is None:
                root.append(statuses)
            else:
                sibling.addprevious(statuses)
        for status in self.STATUSES:
            ps = etree.Element("ProcessingStatus")
            etree.SubElement(ps, "ProcessingStatusValue").text = status
            etree.SubElement(ps, "ProcessingStatusDate").text = Control.TODAY
            etree.SubElement(ps, "EnteredBy").text = self.__control.user
            statuses.insert(0, ps)


if __name__ == "__main__":
    """Only execute if loaded as a script."""
    Control().run()
