#----------------------------------------------------------------------
#
# Add and link to glossary pronunciation Media documents.
#
# Invoked from the CDR Admin web menu.
#
# If for any reason this script will not process the correct set of
# zip files (for example, because a file name did not match the
# agreed pattern of "Week_NNN*.zip" or the file names for a batch
# do not sort in the order the files should be processed), then it
# will be necessary to have a developer load the batch from the
# bastion host using DevTools/Utilities/Request4926.py.
#
# JIRA::OCECDR-3373
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi
import glob
import re
import xlrd
import ModifyDocs
import lxml.etree as etree
import mutagen
import zipfile
import cStringIO
from cdrapi import db

CDRNS = "cips.nci.nih.gov/cdr"
NSMAP = { "cdr" : CDRNS }
AUDIO = cdr.BASEDIR + "/Audio_from_CIPSFTP"
BANNER = "CDR Administration"
SUBTITLE = "Load Glossary Audio Files"
logger = cdr.Logging.get_logger("audio-import")

def get_latest_batch():
    """
    Collect the list of zip files representing the most recent batch
    of audio files to be loaded into the CDR. For some reason the users
    assign names starting with "Week_..." for the zip files, even
    though there appears to be no correspondence between week numbers
    embedded in the file and directory names and week numbers in the
    calendar. A better naming convention might have used "Batch..."
    or something along those lines, but we're working with what we're
    given. The behavior of the software relies on some assumptions.

      1. The zip file names have a 3-digit number following "Week_"
      2. All files in a single batch have this "Week_NNN" prefix
      3. The names, when sorted (without regard to case) are in
         order, representing when the zip file was given to NCI
      4. The users will pay attention to the list displayed, and
         either confirm if the list represents the correct set of
         files to be processed (in the correct order), or submit
         a request for a developer to import the files manually.

    Returns a sorted list of tuples, each of which contains the
    uppercase version of the zip file's name (to make sorting work
    properly) and the original name (with possibly mixed case).
    """
    sets = {}
    for path in glob.glob("%s/Week_*.zip" % AUDIO):
        match = re.search(r"((Week_\d+).*.zip)", path, re.I)
        if match:
            name = match.group(1)
            week = match.group(2).upper()
            if len(week) != 8:
                continue
            if week not in sets:
                sets[week] = []
            sets[week].append((name.upper(), name))
    if not sets:
        return None
    keys = sorted(sets.keys())
    return sorted(sets[keys[-1]])

def show_form():
    """
    Show the user the proposed list of zip files to be processed.
    """
    global buttons

    files = get_latest_batch()
    if not files:
        cdrcgi.bail("no archives found")
    form = cdrcgi.Page(BANNER, subtitle=SUBTITLE, session=session,
                       buttons=buttons, action="ocecdr-3373.py")
    ol = form.B.OL()
    for name_upper, name in files:
        value = "%s|%s" % (name_upper, name)
        form.add(form.B.INPUT(name="zipfiles", value=value, type="hidden"))
        ol.append(form.B.LI(name))
    form.add("<fieldset>")
    instructions = ("Press the Submit button to create Media documents "
                    "for the MP3 files contained in the archive files "
                    "listed below, and have those documents linked from "
                    "the corresponding GlossaryTermName documents. "
                    "Archives will be processed in the order "
                    "in which they appear in this list, with MP3 clips "
                    "found in later archives overriding those found in "
                    "earlier archives. If this set is not the correct "
                    "set of archives to be processed, please contact "
                    "a CDR developer to have the audio files imported "
                    "manually.")
    form.add(form.B.P(instructions))
    form.add("</fieldset>")
    form.add("<fieldset>")
    form.add(form.B.LEGEND("Compressed Archives containing Audio files"))
    form.add(ol)
    form.add("</fieldset>")
    form.send()

def getCreationDate(path, zipFile):
    """
    Find out when the audio file was created.
    """
    info = zipFile.getinfo(path)
    return "%04d-%02d-%02d" % info.date_time[:3]

def getRuntime(bytes):
    """
    Determine the duration of an audio clip.
    """
    fp = cStringIO.StringIO(bytes)
    mp3 = mutagen.File(fp)
    logger.info("runtime is %s", mp3.info.length)
    return int(round(mp3.info.length))

def getDocTitle(docId):
    """
    Fetch the document title from a CDR document, identified by its CDR ID.
    """
    cursor.execute("SELECT title FROM document WHERE id = ?", docId)
    return cursor.fetchall()[0][0]

def getCellValue(sheet, row, col):
    """
    Extract and return the value from a cell in a spreadsheet, or
    None if the cell does not exist, or has no value.
    """
    try:
        cell = sheet.cell(row, col)
        return cell and cell.value or None
    except:
        return None

#----------------------------------------------------------------------
# Object representing a single pronunciation audio file.
#----------------------------------------------------------------------
class AudioFile:

    def __init__(self, zipName, zipFile, sheet, row):
        """
        Extract the information for the audio file from the spreadsheet
        representing the contents of the zip file, and from the audio
        file itself.
        """
        try:
            self.zipName = zipName
            self.nameId = int(getCellValue(sheet, row, 0))
        except Exception as e:
            logger.exception("%s row %s", zipName, row)
            raise
        try:
            self.nameTitle = getDocTitle(self.nameId)
        except Exception:
            logger.error("CDR document %d not found", self.nameId)
            raise
        try:
            self.name = getCellValue(sheet, row, 1)
        except Exception:
            logger.exception("CDR%d row %s in %s", self.nameId, row, zipName)
            raise
        try:
            self.language = getCellValue(sheet, row, 2)
            self.filename = getCellValue(sheet, row, 4)
            self.creator = getCellValue(sheet, row, 5)
            self.notes = getCellValue(sheet, row, 6)
            self.bytes = zipFile.read(self.filename)
            self.duration = getRuntime(self.bytes)
            self.created = getCreationDate(self.filename, zipFile)
            self.title = self.nameTitle.split(';')[0]
            if self.language == 'Spanish':
                self.title += u"-Spanish"
            if self.language not in ('English', 'Spanish'):
                raise Exception("unexpected language value '%s'" %
                                self.language)
        except Exception as e:
            logger.exception("CDR%d %r (%s) row %s in %s", self.nameId,
                             self.name, self.language, row, zipName)
            raise

    def makeElement(self):
        """
        Create an element representing a link to this audio file's Media
        document, for insertion into the XML document for the linking
        GlossaryTermName document.
        """
        element = etree.Element('MediaLink')
        child = etree.Element('MediaID')
        child.text = u"%s; pronunciation; mp3" % self.title
        child.set("{cips.nci.nih.gov/cdr}ref", "CDR%010d" % self.mediaId)
        element.append(child)
        return element

    def findNameNode(self, tree):
        """
        Find the node in a GlossaryTermName document where we will insert
        the element linking to the new Media document.
        """
        targetNode = None
        tag = self.language == 'English' and 'TermName' or 'TranslatedName'
        for node in tree.findall(tag):
            nameNode = NameNode(node)
            if nameNode.name == self.name:
                return nameNode
        raise Exception("unable to find name node for %s in CDR%s" %
                        (repr(self.name), self.nameId))

    def toXml(self):
        """
        Create the serialized XML for a new CDR Media document
        representing this audio file.
        """
        language = self.language == 'Spanish' and 'es' or 'en'
        creator = self.creator or u'Vanessa Richardson, VR Voice'
        root = etree.Element("Media", nsmap=NSMAP)
        root.set("Usage", "External")
        etree.SubElement(root, "MediaTitle").text = self.title
        physicalMedia = etree.SubElement(root, "PhysicalMedia")
        soundData = etree.SubElement(physicalMedia, "SoundData")
        etree.SubElement(soundData, "SoundType").text = "Speech"
        etree.SubElement(soundData, "SoundEncoding").text = "MP3"
        etree.SubElement(soundData, "RunSeconds").text = str(self.duration)
        mediaSource = etree.SubElement(root, "MediaSource")
        originalSource = etree.SubElement(mediaSource, "OriginalSource")
        etree.SubElement(originalSource, "Creator").text = creator
        etree.SubElement(originalSource, "DateCreated").text = self.created
        etree.SubElement(originalSource, "SourceFilename").text = self.filename
        mediaContent = etree.SubElement(root, "MediaContent")
        categories = etree.SubElement(mediaContent, "Categories")
        etree.SubElement(categories, "Category").text = "pronunciation"
        descs = etree.SubElement(mediaContent, "ContentDescriptions")
        desc = etree.SubElement(descs, "ContentDescription")
        desc.text = 'Pronunciation of dictionary term "%s"' % self.name
        desc.set("audience", "Patients")
        desc.set("language", language)
        proposedUse = etree.SubElement(root, "ProposedUse")
        glossary = etree.SubElement(proposedUse, "Glossary")
        glossary.set("{%s}ref" % CDRNS, "CDR%010d" % self.nameId)
        glossary.text = self.nameTitle
        return etree.tostring(root, pretty_print=True)

    def save(self, session):
        """
        Create the new Media document in the CDR for this audio file.
        """
        comment = "document created for CDR request OCECDR=3373"
        docTitle = u"%s; pronunciation; mp3" % self.title
        ctrl = dict(DocType="Media", DocTitle=docTitle.encode("utf-8"))
        doc = cdr.Doc(self.toXml(), doctype="Media", ctrl=ctrl)
        opts = dict(
            doc=str(doc),
            comment=comment,
            reason=comment,
            val="Y",
            ver="Y",
            publishable="Y",
            blob=self.bytes
        )
        result = cdr.addDoc(session, **opts)
        self.mediaId = cdr.exNormalize(result)[1]
        cdr.unlock(session, self.mediaId)
        return self.mediaId

#----------------------------------------------------------------------
# Object representing the element in a GlossaryTermName document to
# which a new child element will be inserted for the link to a new
# CDR Media document.
#----------------------------------------------------------------------
class NameNode:
    def __init__(self, node):
        self.node = node
        self.name = None
        self.insertPosition = 0
        for child in node:
            if child.tag == 'TermNameString':
                self.name = child.text
                self.insertPosition += 1
            elif child.tag in ('TranslationResource', 'MediaLink',
                               'TermPronunciation', 'PronunciationResource'):
                self.insertPosition += 1

#----------------------------------------------------------------------
# Job control object. Implements the interface used by the ModifyDocs
# module, returning the list of IDs for the documents to be modified,
# and performing the actual document modifications.
#----------------------------------------------------------------------
class Request4926(ModifyDocs.Job):

    LOGNAME = "ocecdr-3373"
    COMMENT = "OCECDR-3373"
    MESSAGE = "Added link from this document to Media document CDR{:d}"

    def __init__(self, mp3s, report_rows, **opts):
        ModifyDocs.Job.__init__(self, **opts)
        self.mp3s = mp3s
        self.report_rows = report_rows

    def select(self):
        return sorted(self.mp3s)

    def transform(self, doc):
        int_id = cdr.exNormalize(doc.id)[1]
        string_id = "CDR{:d}".format(int_id)
        try:
            root = etree.fromstring(doc.xml)
            mp3s = self.mp3s[int_id]
            report_rows = []
            for mp3 in mp3s:
                node = mp3.findNameNode(root)
                node.node.insert(node.insertPosition, mp3.makeElement())
                message = self.MESSAGE.format(mp3.mediaId)
                report_rows.append([string_id, message])
            return_value = etree.tostring(root)
            self.report_rows += report_rows
            return return_value
        except Exception as e:
            logger.exception(string_id)
            self.report_rows.append([string_id, str(e)])
            return doc.xml

def collectInfo(zipNames):
    """
    Create a nested dictionary for all of the sound files found in all
    of the zipfiles identified on the command line.  The top level of
    the dictionary is indexed by the CDR ID for the GlossaryTermName
    document with which the sound file belongs.  Within a given
    GlossaryTermName document is a nested dictionary indexed by the
    term name string.  Because Spanish and English often spell the
    term name the same way, each entry in this dictionary is in turn
    another dictionary indexed by the name of the language.  Each entry
    in these dictionaries at the lowest level is a sequence of MP3 objects.
    Since the zipfiles are named on the command line in ascending order
    of precedence, the last MP3 object in a given sequence supercedes
    the earlier objects in that sequence.
    """
    nameDocs = {}
    for zipName in zipNames:
        zipFile = zipfile.ZipFile(zipName)
        fileNames = set()
        termNames = set()
        for name in zipFile.namelist():
            if "MACOSX" not in name and name.endswith(".xls"):
                xlBytes = zipFile.read(name)
                book = xlrd.open_workbook(file_contents=xlBytes)
                sheet = book.sheet_by_index(0)
                for row in range(sheet.nrows):
                    try:
                        mp3 = AudioFile(zipName, zipFile, sheet, row)
                    except Exception as e:
                        continue
                    lowerName = mp3.filename.lower()
                    if lowerName in fileNames:
                        logger.error("multiple %r in %s", lowerName, zipName)
                    else:
                        fileNames.add(lowerName)
                    key = (mp3.nameId, mp3.name, mp3.language)
                    if key in termNames:
                        logger.error("multiple %r in %s", key, zipName)
                    else:
                        termNames.add(key)
                    nameDoc = nameDocs.get(mp3.nameId)
                    if nameDoc is None:
                        nameDoc = nameDocs[mp3.nameId] = {}
                    termName = nameDoc.get(mp3.name)
                    if termName is None:
                        termName = nameDoc[mp3.name] = {}
                    mp3sForThisLanguage = termName.get(mp3.language)
                    if mp3sForThisLanguage is None:
                        mp3sForThisLanguage = termName[mp3.language] = []
                    mp3sForThisLanguage.append(mp3)
                break
    return nameDocs

#----------------------------------------------------------------------
# Collect the request's parameters.
#----------------------------------------------------------------------
fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
files = fields.getlist("zipfiles")

# Validate them
buttons = ('Submit', cdrcgi.MAINMENU)
if request: cdrcgi.valParmVal(request, valList=buttons)
if files:   cdrcgi.valParmVal(files, regex='Week_\d{3}.*\.zip', icase=True)

#----------------------------------------------------------------------
# Make sure the user is authorized to run this script.
#----------------------------------------------------------------------
if not cdr.canDo(session, "ADD DOCUMENT", "Media"):
    cdrcgi.bail("Sorry, you aren't authorized to create new Media documents")
if not cdr.canDo(session, "MODIFY DOCUMENT", "GlossaryTermName"):
    cdrcgi.bail("Sorry, you aren't authorized to modify GlossaryTermName docs")

# Navigate away from script?
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# If we don't have a request yet, show the page asking for confirmation.
#----------------------------------------------------------------------
if request != "Submit" or not files:
    show_form()
cursor = db.connect(user='CdrGuest').cursor()
cursor.execute("""\
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path LIKE '/GlossaryTermName/%/MediaLink/MediaID/@cdr:ref'""")
alreadyDone = set([row[0] for row in cursor.fetchall()])
logger.info("%d documents already processed", len(alreadyDone))
files = ["%s/%s" % (AUDIO, f.split("|")[1]) for f in files]
info = collectInfo(files)
mediaDocs = {}
docs = {}
report_rows = []
for nameId in info:
    if nameId in alreadyDone:
        logger.info("skipping CDR%d: already done", nameId)
        report_rows.append(["CDR%d" % nameId, "Skipped (already processed)"])
        continue
    mp3sForNameDoc = []
    termNames = info[nameId]
    for termName in termNames:
        languages = termNames[termName]
        for language in languages:
            mp3s = languages[language]
            lang = language == 'Spanish' and 'es' or 'en'
            key = (nameId, termName, lang)
            mp3 = mp3s[-1]
            mp3sForNameDoc.append(mp3)
            mediaId = mediaDocs.get(key)
            if mediaId:
                message = "%s already saved as CDR%d" % (repr(key), mediaId)
                logger.info(message)
                report_rows.append(["", message])
                mp3.mediaId = mediaId
            else:
                mediaId = mp3.save(session)
                mediaDocs[key] = mediaId
                logger.info("saved %s from %s as CDR%d", key, mp3.zipName,
                            mediaId)
                message = "Media doc created for %s from %s" % (repr(key),
                                                                mp3.zipName)
                report_rows.append(["CDR%d" % mediaId, message])
    if mp3sForNameDoc:
        docs[nameId] = mp3sForNameDoc
opts = dict(session=session, mode="live", console=False)
job = Request4926(docs, report_rows, **opts)
job.run()
columns = (cdrcgi.Report.Column("CDR ID"), cdrcgi.Report.Column("Processing"))
table = cdrcgi.Report.Table(columns, job.report_rows)
opts = dict(banner=BANNER, subtitle=SUBTITLE)
report = cdrcgi.Report("Pronunciation Media Document Imports", [table], **opts)
report.send()
