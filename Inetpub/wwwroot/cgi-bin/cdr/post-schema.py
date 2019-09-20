#----------------------------------------------------------------------
# Post a new or modified CDR summary document.
# OCECDR-4239
#----------------------------------------------------------------------
import os
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    SUBMENU = None
    REASON = "Adding new CDR schema from post-schema.py"
    LOGNAME = "post-schema"
    def __init__(self):
        cdrcgi.Control.__init__(self, "Post CDR Schema")
        if not self.session:
            cdrcgi.bail("Invalid or missing session.")
        if not cdr.canDo(self.session, "MODIFY DOCUMENT", "schema"):
            cdrcgi.bail("Account not authorized for posting schemas.")
        self.comment = self.fields.getvalue("comment") or self.REASON
        self.action = self.fields.getvalue("action")
    def set_form_options(self, opts):
        opts["enctype"] = "multipart/form-data"
        return opts
    def populate_form(self, form):
        self.B = form.B
        message = self.post_schema()
        form.add("<fieldset>")
        form.add(self.B.LEGEND("Schema"))
        form.add_text_field("file", "Schema File", upload=True)
        form.add_text_field("comment", "Comment")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(self.B.LEGEND("Action"))
        form.add_radio("action", "Add New Schema", "add")
        form.add_radio("action", "Replace Existing Schema", "replace",
                       checked=True)
        form.add("</fieldset>")
        if message is not None:
            form.add(message)
    def show_report(self):
        self.show_form()
    def post_schema(self):
        try:
            schema = self.read_file("file")
            if schema is None:
                return None
            self.logger.info("Schema length: %d", len(schema))
            if not self.doc:
                messages = [self.add_doc(schema) + "\n"]
            else:
                messages = [self.rep_doc(schema) + "\n"]
            messages.append(self.check_dtds())
            messages.append(self.refresh_manifest())
            messages.append("Schema posted successfully.")
            return self.message("\n".join(messages), "green")
        except Exception as e:
            self.logger.exception("Failure")
            return self.message(e, "red")
    def check_dtds(self):
        cmd = r"python d:\cdr\build\CheckDtds.py"
        result = cdr.runCommand(cmd)
        if result.code:
            raise Exception("DTD check failure: %s" % result.output)
        self.logger.info("DTDs updated")
        return "Running CheckDtds.py ...\n" + str(result.output, "utf-8")
    def refresh_manifest(self):
        cmd = r"python d:\cdr\build\RefreshManifest.py"
        result = cdr.runCommand(cmd)
        if result.code:
            output = str(result.output, "utf-8")
            raise Exception(f"Manifest refresh failure: {output}")
        self.logger.info("Manifest updated")
        return "Running RefreshManifest.py ...\n" + str(result.output, "utf-8")
    def add_doc(self, schema):
        ctrl = dict(DocTitle=self.filename)
        doc = cdr.Doc(schema, doctype="schema", ctrl=ctrl)
        opts = dict(
            doc=str(doc),
            ver="Y",
            comment=self.comment,
            reason=self.comment,
            show_warnings=True
        )
        doc_id, warnings = cdr.addDoc(self.session, **opts)
        if doc_id:
            cdr.unlock(self.session, doc_id)
            message = "Created schema %s (%r)." % (doc_id, self.filename)
            self.logger.info(message)
            return message
        raise Exception(cdr.checkErr(warnings) or "Unexpected error")
    def rep_doc(self, schema):
        self.doc.xml = schema
        doc = str(self.doc)
        doc_id = cdr.repDoc(self.session, doc=doc, checkIn="Y", ver="Y")
        self.logger.info("Replaced %r", doc_id)
        return "Updated schema %s (%r)." % (doc_id, self.filename)
    def read_file(self, name):
        if name not in self.fields.keys():
            return None
        f = self.fields[name]
        self.filename = os.path.basename(f.filename)
        self.logger.info("filename is %r", self.filename)
        self.doc = self.find_schema(self.filename)
        if f.file:
            chars = []
            while True:
                more_chars = f.file.read()
                if not more_chars:
                    break
                chars.append(more_chars)
        else:
            chars = [f.value]
        return b"".join(chars)
    def find_schema(self, title):
        query = "CdrCtl/Title = {}".format(title)
        results = cdr.search(self.session, query, doctypes=["schema"])
        if isinstance(results, (str, bytes)):
            raise Exception(results)
        if len(results) < 1:
            self.logger.info("Search found no documents for %r", title)
            if self.action != "add":
                raise Exception("Schema document %r not found" % title)
            return None
        if len(results) > 1:
            raise Exception("Multiple documents match %r" % title)
        if self.action != "replace":
            raise Exception("Schema document %r already exists" % title)
        self.logger.info("Found schema document %s", results[0].docId)
        doc = cdr.getDoc(self.session, results[0].docId, "Y", getObject=True)
        if isinstance(doc, (str, bytes)):
            raise Exception("Failure fetching schema document: %r" % doc)
        return doc
    def message(self, what, color):
        style = "padding: 10px; border: solid 1px %s; width: 600px;" % color
        style += " color: %s; margin: 15px auto;" % color
        if color == "red":
            style += " text-align: center; font-weight: bold;"
            return self.B.P(str(what), style=style)
        else:
            what = str(what.replace("\n", cdrcgi.NEWLINE).replace("\r", ""))
            return self.B.PRE(what, style=style)
Control().run()
