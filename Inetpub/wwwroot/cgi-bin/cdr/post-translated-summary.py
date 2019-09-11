#----------------------------------------------------------------------
# Create new summary document for translated version (CGI interface).
# OCECDR-4004
#----------------------------------------------------------------------
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    SUBMENU = None
    def __init__(self):
        cdrcgi.Control.__init__(self, "Create World Server Translated Summary")
        if not self.session:
            cdrcgi.bail("Invalid or missing session.")
        if not cdr.canDo(self.session, "CREATE WS SUMMARIES"):
            cdrcgi.bail("Account not authorized for adding WS summaries.")
        self.set_binary_mode()
    def set_form_options(self, opts):
        opts["enctype"] = "multipart/form-data"
        return opts
    def populate_form(self, form):
        self.B = form.B
        message = self.load_file("file")
        if message is not None:
            form.add(message)
        form.add("<fieldset>")
        form.add(self.B.LEGEND("Translated Summary"))
        form.add_text_field("file", "Summary File", upload=True)
        form.add_text_field("comment", "Comment")
        form.add("</fieldset>")
    def show_report(self):
        self.show_form()
    def load_file(self, name):
        try:
            xml = self.read_file(name)
            if xml is None:
                return None
            doc_id = self.add_doc(xml)
            return self.message(doc_id, "green")
        except Exception as e:
            return self.message(e, "red")
    def add_doc(self, xml):
        doc = cdr.Doc(xml, doctype="Summary")
        reason = "Creating document translated in Trados"
        reason = self.fields.getvalue("comment", reason)
        opts = dict(
            doc=str(doc),
            ver="Y",
            comment=reason,
            reason=reason,
            check_in="Y",
            show_warnings=True
        )
        doc_id, warnings = cdr.addDoc(self.session, **opts)
        if doc_id:
            return "Created %s." % doc_id
        raise Exception(cdr.checkErr(warnings) or "Unexpected error")
    def read_file(self, name):
        if name not in self.fields.keys():
            return None
        f = self.fields[name]
        if f.file:
            bytes = []
            while True:
                more_bytes = f.file.read()
                if not more_bytes:
                    break
                bytes.append(more_bytes)
        else:
            bytes = [f.value]
        return "".join(bytes)
    def message(self, what, color):
        style = "text-align: center; font-weight: bold; color: %s;" % color
        return self.B.P(str(what), style=style)
    def set_binary_mode(self):
        try:
            import msvcrt
            import os
            msvcrt.setmode(0, os.O_BINARY) # stdin = 0
            msvcrt.setmode(1, os.O_BINARY) # stdout = 1
        except ImportError:
            pass
        except:
            cdrcgi.bail("Internal error")
Control().run()
