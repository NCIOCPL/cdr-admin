#!/usr/bin/env python

"""Show changes made by a global change test run.
"""

from collections import defaultdict
from glob import glob
from os import listdir, path, stat
from re import sub
from lxml import etree, html
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Global Change Test Results"
    CSS = "fieldset { width: 225px; }"
    TESTS = "Test Runs"
    BY_ID = "ID Sort"
    BY_DOCSIZE = "Doc Size Sort"
    BY_DIFFSIZE = "Diff Size Sort"
    SORTS = BY_ID, BY_DOCSIZE, BY_DIFFSIZE

    def build_tables(self):
        """Show the documents processed by the test global change job run."""

        opts = dict(columns=self.columns, caption=self.caption, id="docs")
        return self.Reporter.Table(self.docs.rows, **opts)

    def populate_form(self, page):
        """Add links to test results.

        Pass:
            page - HTMLPage object on which the links are placed
        """

        fieldset = page.fieldset("Choose Test Run Job")
        link_list = page.B.UL(page.B.CLASS("links"))
        for link in self.links:
            link_list.append(page.B.LI(link))
        fieldset.append(link_list)
        page.form.append(fieldset)
        page.add_css(self.CSS)

    def run(self):
        """Override base class logic for some custom routing."""

        if self.request == self.TESTS:
            self.show_form()
        elif self.text:
            self.show_file()
        elif self.docs:
            self.show_report()
        else:
            Controller.run(self)

    def show_file(self):
        """Display an XML or diff file."""

        body = self.HTMLPage.B.BODY(self.HTMLPage.B.PRE(self.text))
        page = self.HTMLPage.B.HTML(body)
        self.send_page(html.tostring(page, encoding="unicode"))

    def show_report(self):
        """Override the base class version so we can add extra buttons."""

        page = self.report.page
        page.add_css("#docs a { margin: auto 5px; }")
        page.form.append(page.hidden_field("dir", self.directory))
        buttons = page.body.find("form/header/h1/span")
        for sort in reversed(self.SORTS):
            if sort != self.sort:
                buttons.insert(0, page.button(sort))
        buttons.insert(0, page.button(self.TESTS))
        self.report.send()

    @property
    def base(self):
        """Top-level directory for the global change test output."""

        if not hasattr(self, "_base"):
            self._base = f"{self.session.tier.basedir}/GlobalChange"
        return self._base

    @property
    def caption(self):
        """What we display at the top of the report table."""

        return (
            f"Test job run at {self.runtime}",
            f"Total number of documents = {self.docs.count}",
            f"Total number of versions = {len(self.docs.rows)}",
        )

    @property
    def columns(self):
        """Headers for the report table's columns."""

        return "CDR ID", "Ver.", "Files", "New Size", "Diff Size"
        return (
            self.Reporter.Column("CDR ID"),
            self.Reporter.Column("Ver."),
            self.Reporter.Column("Files", colspan=4),
            self.Reporter.Column("New Size"),
            self.Reporter.Column("Diff Size"),
        )

    @property
    def directory(self):
        """Name of the directory for the selected job."""
        return self.fields.getvalue("dir")

    @property
    def docs(self):
        """`DocSet` object, containing all of the documents in the test run."""

        if not hasattr(self, "_docs"):
            self._docs = None
            if self.directory:
                self._docs = DocSet(self)
        return self._docs

    @property
    def filename(self):
        """Name of the file selected for display (if any)."""
        return self.fields.getvalue("file")

    @property
    def links(self):
        """Links for choosing a test run."""

        if not hasattr(self, "_links"):
            self._links = []
            for directory in sorted(glob(f"{self.base}/20*_*"), reverse=True):
                name = path.basename(directory)
                date_time = name.split("_")
                time_string = date_time[1].replace("-", ":")
                label = f"{date_time[0]} {time_string}"
                url = self.make_url(self.script, dir=name)
                self._links.append(self.HTMLPage.B.A(label, href=url))
        return self._links

    @property
    def runtime(self):
        "String for the date/time when the test global change job was run."""

        if not hasattr(self, "_runtime"):
            date_string, time_string = self.directory.split("_")
            time_string = time_string.replace("-", ":")
            self._runtime = f"{date_string} {time_string}"
        return self._runtime

    @property
    def sort(self):
        """How should the documents be ordered?"""

        if not hasattr(self, "_sort"):
            self._sort = self.fields.getvalue("sortBy")
            if not self._sort:
                if self.request in self.SORTS:
                    self._sort = self.request
            if self._sort not in self.SORTS:
                self._sort = self.BY_DIFFSIZE
        return self._sort

    @property
    def text(self):
        """Unicode string for the currently selected file."""

        if not (self.directory and self.filename):
            return None
        if not hasattr(self, "_text"):
            path = f"{self.base}/{self.directory}/{self.filename}"
            with open(path, encoding="utf-8") as fp:
                self._text = fp.read()
            if self.filename.lower().endswith(".xml"):
                xml = sub(r"<\?xml[^?]*\?>\s*", "", self._text)
                doc = Doc(self.session, xml=xml)
                doc.doctype = doc.root.tag
                doc.normalize()
                opts = dict(pretty_print=True, encoding="unicode")
                xml = etree.tostring(doc.root, **opts).replace("\r", "")
                lines = [line for line in xml.split("\n") if line.strip()]
                self._text = "\n".join(lines)
        return self._text


class DocSet:
    """Documents for the selected global change test run."""

    def __init__(self, control):
        """Remember the caller's value.

        Pass:
            control - access to the report settings
        """

        self.__control = control

    @property
    def control(self):
        """Access to the report options."""
        return self.__control

    @property
    def count(self):
        """How many documents in the test run?"""
        return len(self.docs)

    @property
    def directory(self):
        """Absolute path to the test job's files."""

        if not hasattr(self, "_directory"):
            self._directory = f"{self.control.base}/{self.control.directory}"
        return self._directory

    @property
    def docs(self):
        """`DocSet.Doc` objects for the CDR documents in the test run."""

        if not hasattr(self, "_docs"):
            self._docs = [self.Doc(self, cdr_id) for cdr_id in self.files]
        return self._docs

    @property
    def files(self):
        """All of the relevant files from the job, indexed by CDR ID."""

        if not hasattr(self, "_files"):
            self._files = defaultdict(list)
            for filename in listdir(self.directory):
                name = self.Name(filename)
                if name.in_scope:
                    self._files[name.cdr_id].append(filename)
        return self._files

    @property
    def rows(self):
        """All rows for the report table."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for doc in sorted(self.docs):
                self._rows += doc.rows
        return self._rows


    class Doc:
        """One of the CDR documents processed by the global change test run."""

        VERSIONS = "cwd", "lastv", "lastp"

        def __init__(self, docs, cdr_id):
            """Remember the caller's values.

            Pass:
                docs - access to report settings and the test run's files
                cdr_id - string ID for this CDR document
            """

            self.__docs = docs
            self.__cdr_id = cdr_id

        def __lt__(self, other):
            """Sort order is controlled by the `key` property."""
            return self.key < other.key

        @property
        def cdr_id(self):
            """String ID for this CDR document."""
            return self.__cdr_id

        @property
        def docs(self):
            """Access to the report's setetings and the test run's files."""
            return self.__docs

        @property
        def key(self):
            """Set the sort key based on the order requested by the user.

            Using negative numbers for the sizes to get bigger files
            up to the top.
            """

            if not hasattr(self, "_key"):
                if self.docs.control.sort == Control.BY_ID:
                    self._key = self.cdr_id
                elif self.docs.control.sort == Control.BY_DOCSIZE:
                    self._key = -self.versions[0].new.size
                else:
                    self._key = -self.versions[0].diff.size
            return self._key

        @property
        def rows(self):
            """One row for each of the document's versions in the job."""

            if not hasattr(self, "_rows"):
                self._rows = [version.row for version in self.versions]
            return self._rows

        @property
        def versions(self):
            """Versions of this document processed by this job."""

            if not hasattr(self, "_versions"):
                self._versions = []
                for name in self.VERSIONS:
                    version = self.Version(self, name)
                    try:
                        if version.old.size:
                            if version.new.size:
                                if version.diff.size:
                                    self._versions.append(version)
                    except Exception:
                        if name == self.VERSIONS[0]:
                            message = f"Can't read {self.cdr_id} files"
                            raise
                            self.docs.control.bail(message)
            return self._versions


        class Version:
            """One of the versions of a document processed by the job."""

            def __init__(self, doc, name):
                """Save the caller's values.

                Pass:
                    doc - access to the base information about the document
                    name - cwd, lastv, or lastp
                """

                self.__doc = doc
                self.__name = name

            @property
            def base(self):
                """Front part of the names of this version's files."""

                if not hasattr(self, "_base"):
                    if self.name == "lastp":
                        suffix = "pub"
                    else:
                        suffix = self.name
                    self._base = f"{self.doc.cdr_id}.{suffix}"
                return self._base

            @property
            def diff(self):
                """Output from comparing before and after for the version."""

                if not hasattr(self, "_diff"):
                    self._diff = self.File(self, "diff")
                return self._diff

            @property
            def doc(self):
                """Access to the big picture for the report."""
                return self.__doc

            @property
            def errors(self):
                """Error file for this version (usually not present)."""

                if not hasattr(self, "_errors"):
                    try:
                        errors = self.File(self, "errs")
                        if errors.size != None:
                            self._errors = errors
                    except Exception:
                        self._errors = None
                return self._errors

            @property
            def files(self):
                """Links to display of the version's files."""

                if not hasattr(self, "_files"):
                    links = [
                        self.old.link,
                        self.new.link,
                        self.diff.link,
                    ]
                    if self.errors:
                        links.append(self.errors.link)
                    self._files = self.doc.docs.control.HTMLPage.B.SPAN(*links)
                return self._files

            @property
            def name(self):
                """One of cwd, lastv, or lastp."""
                return self.__name

            @property
            def new(self):
                """Original XML for this version of the document."""

                if not hasattr(self, "_new"):
                    self._new = self.File(self, "new")
                return self._new

            @property
            def old(self):
                """Original XML for this version of the document."""

                if not hasattr(self, "_old"):
                    self._old = self.File(self, "old")
                return self._old

            @property
            def row(self):
                """Report row for this version of the document."""

                if not hasattr(self, "_row"):
                    Cell = self.doc.docs.control.Reporter.Cell
                    self._row = []
                    if self.name == self.doc.versions[0].name:
                        opts = dict(
                            rowspan=len(self.doc.versions),
                            middle=True,
                        )
                        self._row.append(Cell(self.doc.cdr_id, **opts))
                    self._row += [
                        self.name.upper(),
                        self.files,
                        Cell(self.new.size, right=True),
                        Cell(self.diff.size, right=True),
                    ]
                return self._row


            class File:
                """Stat info for one of the revision's files."""

                SUFFIXES = dict(
                    new="new.xml",
                    old="old.xml",
                    diff=".diff",
                    errs=".NEW_ERRORS.txt",
                )

                def __init__(self, version, label):
                    """Remember the caller's values.

                    Pass:
                        version - access to the front of the path
                        label - string distinguishing this file
                    """

                    self.__version = version
                    self.__label = label

                @property
                def docs(self):
                    """The set of documents included on the report."""
                    return self.__version.doc.docs

                @property
                def suffix(self):
                    """End of the file name."""
                    return self.SUFFIXES[self.__label]

                @property
                def label(self):
                    """Capitalized version of the label string."""
                    return self.__label.capitalize()

                @property
                def link(self):
                    """Hyperlink to show this file."""

                    if not hasattr(self, "_link"):
                        B = self.docs.control.HTMLPage.B
                        self._link = B.A(self.label, href=self.url)
                    return self._link

                @property
                def name(self):
                    """Base name for the file."""

                    if not hasattr(self, "_name"):
                        self._name = f"{self.__version.base}{self.suffix}"
                    return self._name

                @property
                def size(self):
                    """Number of bytes in the file.

                    Let exceptions bubble up.
                    """

                    if not hasattr(self, "_size"):
                        path = f"{self.docs.directory}/{self.name}"
                        self._size = stat(path).st_size
                    return self._size

                @property
                def url(self):
                    """Link to this file's display URL."""

                    if not hasattr(self, "_url"):
                        control = self.docs.control
                        params = dict(
                            dir=control.directory,
                            file=self.name,
                        )
                        self._url = control.make_url(control.script, **params)
                    return self._url


    class Name:
        """File name found in the job's directory."""

        SUFFIXES = "xml", "diff", "NEW_ERRORS.txt"
        ID_LEN = len("CDR0123456789")

        def __init__(self, name):
            """Remember the file's name."""
            self.name = name

        @property
        def in_scope(self):
            """Is this part of the job?"""

            if not self.name.startswith("CDR0"):
                return False
            for suffix in self.SUFFIXES:
                if self.name.endswith(suffix):
                    return True
            return False

        @property
        def cdr_id(self):
            """Extract the string for the CDR document ID."""

            if not hasattr(self, "_cdr_id"):
                self._cdr_id = self.name[:self.ID_LEN]
            return self._cdr_id


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
