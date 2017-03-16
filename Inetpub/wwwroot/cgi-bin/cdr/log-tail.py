#----------------------------------------------------------------------
# Show a piece of a log file.
#----------------------------------------------------------------------
import os
import sys
import time
import re
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    DEFAULT_COUNT = "2000000"
    DEFAULT_PATH = r"D:\cdr\Log\Jobmaster.log"
    def __init__(self):
        cdrcgi.Control.__init__(self, "Log Viewer")
        self.authenticate()
        self.set_binary()
        self.path = self.fields.getvalue("p", "")
        self.start = self.fields.getvalue("s", "")
        self.count = self.fields.getvalue("c", "")
        self.raw = self.fields.getvalue("r", None) # raw (binary)?
        self.pattern = re.match('".+"', self.start) and self.start or None
    def authenticate(self):
        if not self.session or not cdr.canDo(self.session, "VIEW LOGS"):
            cdrcgi.bail("Account not authorized for this action")
    def populate_form(self, form):
        path = self.path or self.DEFAULT_PATH
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Display Parameters"))
        form.add_text_field("p", "Path", value=path)
        form.add_text_field("s", "Start", value=self.start)
        form.add_text_field("c", "Count", value=self.count)
        form.add("</fieldset>")
        form.add_script("jQuery('#p').focus();")
    def find(self):
        try:
            cmd = "find %s %s" % (self.pattern, self.path)
            result = cdr.runCommand(cmd)
            print "Content-type: text/plain\n\n%s" % result.output
        except Exception, e:
            print "Content-type: text/plain\n\n%s\n%s" % (cmd, e)
    def dir(self):
        try:
            result = cdr.runCommand("dir %s" % self.path)
            print "Content-type: text/plain\n\n%s" % result.output
        except Exception, e:
            print "Content-type: text/plain\n\n%s" % e
    def get_binary(self):
        try:
            name = os.path.basename(self.path)
            fp = open(self.path, "rb")
            bytes = fp.read()
            fp.close()
            print "Content-type: application/octet-stream"
            print "Content-disposition: attachment;filename=%s" % name
            print ""
            sys.stdout.write(bytes)
        except Exception, e:
            print "Content-type: text/plain\n\n%s" % repr(e)
    def run(self):
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
            cdrcgi.Control.run(self)
    def show(self):
        try:
            stat = os.stat(self.path)
            info = self.get_info(self.path, stat)
            slice = self.Slice(self, stat.st_size)
            print "Content-type: text/plain\n"
            print "%s bytes %d-%d\n" % (info, slice.start + 1,
                                        slice.start + slice.count)
            if slice.count:
                fp = open(self.path, "rb")
                if slice.start:
                    fp.seek(slice.start)
                bytes = fp.read(slice.count)
                print self.make_ascii(bytes)
            else:
                showForm(info)
        except Exception, e:
            print "Content-type: text/plain\n\n%s" % e
    @staticmethod
    def get_info(path, stat):
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(stat.st_mtime))
        return "%s %s bytes (%s GMT)" % (path, stat.st_size, stamp)
    @staticmethod
    def set_binary():
        try: # Windows needs stdio set for binary mode.
            import msvcrt
            msvcrt.setmode (0, os.O_BINARY) # stdin  = 0
            msvcrt.setmode (1, os.O_BINARY) # stdout = 1
        except ImportError:
            pass
    @staticmethod
    def make_ascii(s):
        return re.sub(u"[\x80-\xff%]",
                      lambda m: "%%%02X" % ord(m.group(0)[0]), s)
    class Slice:
        def __init__(self, control, filesize):

            # Make sure the count is not negative.
            self.count = long(control.count or Control.DEFAULT_COUNT)
            if self.count < 0:
                self.count = 0

            # Handle the case where the user specified a starting position.
            if control.start:
                self.start = long(control.start)

                # A negative starting number means count from the end of
                # the file.
                if self.start < 0:
                    if abs(self.start) > filesize:
                        self.start = 0
                    else:
                        self.start = filesize + self.start

                # Make sure we don't start beyond the end of the file.
                elif self.start > filesize:
                    self.start = filesize

                # Make sure our count doesn't go beyond the end of the file.
                available = filesize - self.start
                if self.count > available:
                    self.count = available

            # User didn't specify a starting position.
            else:

                # Start count bytes from the end of the file if the file
                # can satisfy the count.
                if self.count <= filesize:
                    self.start = filesize - self.count

                # Otherwise constrain the count to what's available.
                else:
                    self.count = filesize
                    self.start = 0

Control().run()
