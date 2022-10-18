#!/usr/bin/env python

"""Show a piece of a log file.
"""

import glob
import os
import sys
import time
import re
import cdr
from cdrcgi import Controller
from functools import cached_property

class Control(Controller):
    """Script master."""

    SUBTITLE = "Log Viewer"
    DEFAULT_PATH = f"{cdr.DEFAULT_LOGDIR}/cdrpub.log"
    HEADERS = "Content-type: text/plain; charset=utf-8\n\n".encode("utf-8")
    ENCODINGS = "utf-8", "latin-1"

    def run(self):
        """Customize the request routing."""

        self.authenticate()
        self.message = None
        self.encoding = self.fields.getvalue("encoding")
        if self.request == self.SUBMIT:
            if not self.path:
                self.show_form()
            if self.pattern:
                self.find()
            elif "*" in self.path or "?" in self.path:
                self.dir()
            elif self.raw:
                self.get_binary()
            else:
                self.show()
        else:
            Controller.run(self)

    def authenticate(self):
        """Ensure that only those authorized to do so can run this scropt."""
        if not self.session or not cdr.canDo(self.session, "VIEW LOGS"):
            self.bail("Account not authorized for this action")

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page
                An instance of the cdrcgi.HTMLPage class
        """
        page.form.set("method", "get")
        if self.message:
            message_class = page.B.CLASS("center error")
            page.form.append(page.B.P(self.message, message_class))
        path = self.path or self.DEFAULT_PATH
        upath = self.user_path
        fieldset = page.fieldset("Display Parameters")
        opts = dict(label="File Name", options=self.options, default=path)
        fieldset.append(page.select("p", **opts))
        fieldset.append(page.text_field("u", label="Custom Path", value=upath))
        fieldset.append(page.text_field("s", label="Start", value=self.start))
        fieldset.append(page.text_field("c", label="Count", value=self.count))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        label = "Retrieve raw log bytes"
        fieldset.append(page.checkbox("r", value="yes", label=label))
        page.form.append(fieldset)
        page.body.append(page.B.SCRIPT("jQuery('#p').focus();"))

    def find(self):
        """Use the Windows find command to search for a pattern in the file."""
        sys.stdout.buffer.write(self.HEADERS)
        try:
            cmd = f"find {self.pattern} {self.path}"
            process = cdr.run_command(cmd, merge_output=True, binary=True)
            sys.stdout.buffer.write(process.stdout)
        except Exception as e:
            sys.stdout.buffer.write(f"{cmd}\n{e}\n".encode("utf-8"))

    def dir(self):
        """Display the output of the Windows dir command."""
        sys.stdout.buffer.write(self.HEADERS)
        try:
            cmd = f"dir {self.path}"
            process = cdr.run_command(cmd, merge_output=True, binary=True)
            sys.stdout.buffer.write(process.stdout)
        except Exception as e:
            sys.stdout.buffer.write(str(e).encode("utf-8"))

    def get_binary(self):
        """Return the raw bytes for the file directly."""
        try:
            name = os.path.basename(self.path)
            with open(self.path, "rb") as fp:
                file_bytes = fp.read()
            sys.stdout.buffer.write(f"""\
Content-type: application/octet-stream
Content-disposition: attachment;filename={name}

""".encode("utf-8"))
            sys.stdout.buffer.write(file_bytes)
        except Exception as e:
            sys.stdout.buffer.write(self.HEADERS)
            sys.stdout.buffer.write(str(e).encode("utf-8"))

    def show(self):
        """Show a slice (usually the last lines) of the selected file."""
        if self.slice.count:
            first = self.slice.start + 1
            last = self.slice.start + self.slice.count
            description = f"{self.info} lines {first}-{last}"
            description += f" of {len(self.offsets)} lines"
            border = "-" * len(description)
            prologue = f"""\
Content-type: text/plain; charset=utf-8

{border}
{description}
{border}

"""
            with open(self.path, encoding=self.encoding) as fp:
                sys.stdout.buffer.write(prologue.encode("utf-8"))
                fp.seek(self.offsets[self.slice.start])
                done = 0
                while done < self.slice.count:
                    line = fp.readline()
                    if not line:
                        break
                    sys.stdout.buffer.write(line.encode("utf-8"))
                    done += 1
        else:
            self.message = self.info
            self.show_form()

    @property
    def start(self):
        """Lines to skip past before we start displaying the log file."""
        if not hasattr(self, "_start"):
            self._start = self.fields.getvalue("s", "")
        return self._start

    @property
    def count(self):
        """Total number of lines to display."""
        if not hasattr(self, "_count"):
            self._count = self.fields.getvalue("c", "")
        return self._count

    @property
    def raw(self):
        """Whether to return the bytes for the log file directly."""
        if not hasattr(self, "_raw"):
            self._raw = True if self.fields.getvalue("r") else False
        return self._raw

    @property
    def pattern(self):
        """Pattern to feed to the Windows find command."""
        if not hasattr(self, "_pattern"):
            self._pattern = re.match('".+"', self.start) and self.start or None
        return self._pattern

    @property
    def path(self):
        """Location of the log file to be displayed."""
        if not hasattr(self, "_path"):
            self._path = self.user_path or self.fields.getvalue("p")
        return self._path

    @property
    def user_path(self):
        """Path for log file not on the picklist."""
        if not hasattr(self, "_user_path"):
            self._user_path = self.fields.getvalue("u")
        return self._user_path

    @cached_property
    def offsets(self):
        """Sequence of starting positions for each line in the file."""

        exceptions = []
        encodings = [self.encoding] if self.encoding else self.ENCODINGS
        for encoding in encodings:
            offset = 0
            try:
                with open(self.path, encoding=encoding) as fp:
                    while True:
                        try:
                            line = fp.readline()
                            self.encoding = encoding
                            break
                        except UnicodeDecodeError as e:
                            offset += 1
                            if offset > 3:
                                raise
                            fp.seek(offset)
                    offsets = []
                    while line:
                        offsets.append(offset)
                        offset = fp.tell()
                        line = fp.readline()
                    return offsets
            except Exception as e:
                exception = f"offset {offset}, encoding {encoding!r}: {e}"
                exceptions.append(exception)
        self.bail(f"{self.path}: {exceptions}")

    @property
    def stat(self):
        """File size, times, etc."""
        if not hasattr(self, "_stat"):
            self._stat = os.stat(self.path) if self.path else None
        return self._stat

    @property
    def slice(self):
        """Range of lines to be displayed from the log file."""
        if not hasattr(self, "_slice"):
            self._slice = self.Slice(self)
        return self._slice

    @property
    def info(self):
        """String describing the file."""
        if not self.stat:
            return ""
        stamp = time.gmtime(self.stat.st_mtime)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", stamp)
        return f"{self.path} {self.stat.st_size} bytes ({stamp} GMT)"

    @property
    def options(self):
        """Values for the path picklist."""
        if not hasattr(self, "_options"):
            options = [("", "")]
            for path in glob.glob(f"{cdr.DEFAULT_LOGDIR}/*.log"):
                path = path.replace("\\", "/")
                display = path.split("/")[-1]
                options.append((path, display))
            self._options = sorted(options, key=lambda o: o[1].lower())
        return self._options

    class Slice:
        """Range of lines to be displayed from the log file.
        """

        DEFAULT_COUNT = 1000

        def __init__(self, control):
            """Let the @properties do the heavy lifting."""
            self.__control = control

        @property
        def count(self):
            """How many lines to display."""
            if not hasattr(self, "_count"):
                # Make sure the count is not negative.
                self._count = int(self.__control.count or self.DEFAULT_COUNT)
                if self._count < 0:
                    self._count = 0
                # We have to force calculation of self.start to make any
                # adjustments to the count.
                assert(self.start is not None)
            return self._count

        @property
        def start(self):
            """How many lines to skip before we start displaying lines."""
            if not hasattr(self, "_start"):

                # How many lines total in the file?
                num_lines = len(self.__control.offsets)

                # Did the user specify a starting position?
                if self.__control.start:
                    self._start = int(self.__control.start)

                    # A negative starting number means count back from the end.
                    if self._start < 0:
                        if abs(self._start) > num_lines:
                            self._start = 0
                        else:
                            self._start = num_lines + self._start

                    # Make sure we don't start beyond the end of the file.
                    elif self._start >= num_lines:
                        self._start = num_lines

                    # Adjust the count if necessary.
                    available = num_lines - self._start
                    if self.count > available:
                        self._count = available

                # User didn't specify a starting position.
                else:

                    # Start `count` lines from the end if we have enough.
                    if self.count < num_lines:
                        self._start = num_lines - self.count

                    # Otherwise constrain the count to what's available.
                    else:
                        self._count = num_lines
                        self._start = 0
            return self._start


Control().run()
