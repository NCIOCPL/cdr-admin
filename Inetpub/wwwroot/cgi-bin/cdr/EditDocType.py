#----------------------------------------------------------------------
# Interface for editing CDR document types.
# OCECDR-4091 - support for modifying active flag
#----------------------------------------------------------------------
import lxml.etree as etree
import cdr
import cdrcgi
from cdrapi import db

class Control(cdrcgi.Control):
    """
    Handles creating/editing CDR document types.
    """

    SUBMENU = "Document Type Menu"
    CANCEL = SUBMENU
    FLAGS = ("versioning", "active")

    def __init__(self):
        """
        Gather and validate the parameters for the request.
        """

        cdrcgi.Control.__init__(self, "CDR Document Type Editor")
        self.formats = self.load_formats()
        self.schemas = self.load_schemas()
        self.filters = self.load_filters()
        self.doctype = self.get_doctype()
        self.name = self.get_string("name", 32)
        self.comment = self.get_string("comment", 255) or ""
        self.format = self.get_int("format", self.formats.map)
        self.schema = self.get_int("schema", self.schemas.map)
        self.title_filter = self.get_int("filter", self.filters.map)
        self.flags = self.get_list("flags", self.FLAGS)
        self.message = None

    def run(self):
        """
        Override the base class method to support our extra button.
        """

        if self.request == self.CANCEL:
            cdrcgi.navigateTo("EditDocTypes.py", self.session)
        cdrcgi.Control.run(self)

    def show_report(self):
        """
        Override the base class method, because we're not really
        showing a report, we're processing a form which stores
        values in the database, and then re-displaying the form.
        """

        required = ["format"]
        if not self.doctype:
            required.append("name")
        for name in required:
            if not getattr(self, name):
                cdrcgi.bail("document type must have a %s" % name)
        doctype = self.doctype or cdr.dtinfo()
        if not self.doctype:
            doctype.type = self.name
        doctype.format = self.formats.map[self.format]
        doctype.schema = self.schemas.map.get(self.schema, "")
        doctype.title_filter = self.filters.map.get(self.title_filter, "")
        doctype.comment = self.comment
        doctype.versioning = ("versioning" in self.flags) and "Y" or "N"
        doctype.active = ("active" in self.flags) and "Y" or "N"
        command = self.doctype and cdr.modDoctype or cdr.addDoctype
        doctype = command(self.session, doctype)
        if doctype.error:
            errors = doctype.error
            if isinstance(errors, (str, bytes)):
                errors = [errors]
            cdrcgi.bail(errors[0], extra=errors[1:])
        self.doctype = self.get_doctype(doctype.type)
        self.message = "Document type %s saved" % doctype.type
        self.show_form()

    def populate_form(self, form):
        """
        Put up the editing form, followed by valid value lists for
        the document type if we're not creating a new document type.
        """

        flags = list(self.FLAGS)
        legend = "Create Document Type"
        fmt = self.formats.lookup("xml")
        schema = ""
        schemas = self.schemas.values
        comment = ""
        filters = self.filters.values
        title_filter = ""
        if self.doctype:
            legend = "Edit %s Document Type" % self.doctype.type
            created = str(self.doctype.created)[:10]
            modified = str(self.doctype.schema_mod)[:10]
            fmt = self.formats.lookup(self.doctype.format)
            if self.doctype.schema:
                schema = self.schemas.lookup(self.doctype.schema)
            if self.doctype.title_filter:
                title_filter = self.filters.lookup(self.doctype.title_filter)
            comment = self.doctype.comment
            for flag in self.FLAGS:
                if getattr(self.doctype, flag) != "Y":
                    flags.remove(flag)
        form.add("<fieldset>")
        form.add(form.B.LEGEND(legend))
        if self.doctype:
            form.add_text_field("created", "Created", value=created,
                                disabled=True)
            form.add_text_field("modified", "Modified", value=modified,
                                disabled=True)
            form.add_hidden_field("doctype", self.doctype.type)
        else:
            form.add_text_field("name", "Name")
        form.add_select("format", "Format", self.formats.values, fmt)
        form.add_select("schema", "Schema", schemas, schema)
        form.add_select("filter", "Title Filter", filters, title_filter)
        form.add_textarea_field("comment", "Comment", value=comment)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Document Type Flags"))
        for flag in self.FLAGS:
            label = flag.capitalize()
            checked = flag in flags
            form.add_checkbox("flags", label, flag, checked=checked)
        form.add("</fieldset>")
        if self.doctype and self.doctype.vvLists:
            form.add("<fieldset>")
            form.add(form.B.LEGEND("Valid Values"))
            for vv in self.doctype.vvLists:
                form.add("<dl>")
                form.add(form.B.DT(form.B.B(vv[0])))
                for value in vv[1]:
                    form.add(form.B.DD(value))
                form.add("</dl>")
            form.add("</fieldset>")

    def set_form_options(self, opts):
        """
        Override the base class method so we can set our own buttons.
        """

        buttons = (self.SUBMIT, self.CANCEL, self.ADMINMENU, self.LOG_OUT)
        opts["buttons"] = buttons
        if self.message:
            opts["subtitle"] = self.message
        return opts

    def get_list(self, name, values):
        """
        Fetch a list of values for a given parameter name. Validate the list.
        """

        field_values = self.fields.getlist(name)
        if set(field_values) - set(values):
            cdrcgi.bail()
        return field_values

    def get_doctype(self, name=None):
        """
        Load a cdr.dtinfo object if we have a document name.
        """

        name = name or self.fields.getvalue("doctype")
        if not name:
            return None
        doctype = cdr.getDoctype(self.session, name)
        if not doctype.type:
            cdrcgi.bail()
            cdrcgi.bail("failure loading %s" % repr(name))
            cdrcgi.bail(doctype.error[0], extra=doctype.error[1:])
        else:
            return doctype

    def load_formats(self):
        """
        Load the valid values for document type formats.

        Consider eliminating this field, as we no longer really support
        formats other than 'xml' in the CDR.
        """

        query = db.Query("format", "id", "name").order("name")
        return self.load_values(query.execute(self.cursor).fetchall(), "xml")

    def load_schemas(self):
        """
        Create a set of schema documents which can be used for controlling
        validation of documents of a given type.
        """

        query = db.Query("document d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'schema'")
        rows = query.order("d.title").execute(self.cursor).fetchall()
        rows = [(row[0], row[1]) for row in rows if self.top_schema(row[0])]
        return self.load_values(rows)

    def load_filters(self):
        """
        Create a set of filter documents which can be used for extracting
        the title of documents of a given type.
        """

        query = db.Query("document d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Filter'")
        rows = query.order("d.title").execute(self.cursor).fetchall()
        rows = [tuple(row) for row in rows if row[1].startswith("DocTitle ")]
        return self.load_values(rows)

    def top_schema(self, doc_id):
        """
        We need to weed out schema documents which do not have a top-level
        'element' element, as those are not appropriate for controlling
        validation for a document type (they are instead included in other
        schema documents which are appropriate).
        """

        query = db.Query("document", "xml")
        query.where(query.Condition("id", doc_id))
        row = query.execute(self.cursor).fetchone()
        if row and row[0]:
            try:
                root = etree.fromstring(row[0].encode("utf-8"))
                if root.findall("{http://www.w3.org/2001/XMLSchema}element"):
                    return True
            except:
                pass
        return False

    def load_values(self, values, default=None):
        """
        Load an object representing valid values.
        """

        class Values:
            """
            Set of valid values, each having a key and a display value

            Properties:

                map - dictionary mapping integer key to display string
                normalized - maps lowercase display string to integer key
                values - ordered sequence of key, display tuples
                default - optional key for default value
            """

            def __init__(self, values, default=None):
                """
                Create maps and ordered sequence of valid values.

                Pass:
                    values - sequence of ordered key, value tuples
                             from a database query
                    default - optional display string for the default value
                """

                self.map = {}
                self.normalized = {}
                self.values = []
                self.default = None
                for key, value in values:
                    normalized = value.strip().lower()
                    self.map[key] = value
                    self.normalized[normalized] = key
                    self.values.append((key, value))
                    if default and default == normalized:
                        self.default = key

            def lookup(self, value):
                """
                Find the key for the value's display string.
                It's a fatal error if the value is not found.
                """

                key = self.normalized.get(value.lower())
                if not key:
                    cdrcgi.bail()
                    cdrcgi.bail("%s not found; map=%s" % (value, self.map))
                return key

        return Values(values, default)

    def get_int(self, name, values):
        """
        Load and validate an integer (foreign key) parameter.
        """

        value = self.fields.getvalue(name)
        if value:
            try:
                value = int(value)
                if value not in values:
                    raise Exception()
            except:
                cdrcgi.bail(cdrcgi.TAMPERING)
        return value

    def get_string(self, name, max_len):
        """
        Load and validate a string parameter.
        """

        value = self.fields.getvalue(name)
        if value:
            try:
                value.encode("ascii")
            except:
                cdrcgi.bail("%s must contain only ASCII" % repr(name))
            if len(value) > max_len:
                cdrcgi.bail("%s has length limit of %d" % (repr(name), max_len))
            if name == "name":
                try:
                    etree.Element(name)
                except:
                    cdrcgi.bail("%s is an invalid Element name" % repr(name))
        return value
Control().run()
