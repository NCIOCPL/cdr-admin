#----------------------------------------------------------------------
# The Glossary Term Concept by Spanish Definition Status Report will serve
# as a QC report for Spanish and corresponding English Definitions by Status.
#
# BZIssue::4344
# Rewritten July 2015 to eliminate security vulnerabilities.
# JIRA::OCECDR-3954 - new column for Spanish version of the report
#----------------------------------------------------------------------
import cdrcgi
import cgi
import cdr
import cdrdb
import datetime
import lxml.etree as etree

class Control:
    """
    Top-level processing driver. Puts up the request form, collects
    the user's options, and displays the report.
    """

    AUDIENCES = ("Patient", "Health professional")
    SPANISH = "4344"
    ENGLISH = "4342"
    SUBMENU = "Report Menu"
    TITLE = "CDR Administration"
    STATUSES = ("Approved", "New pending", "Revision pending", "Rejected")
    BUTTONS = ("Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out")

    def __init__(self):
        "Collect the CGI parameters and scrub them"
        self.cursor = cdrdb.connect("CdrGuest").cursor()
        fields = cgi.FieldStorage()
        self.session = cdrcgi.getSession(fields)
        self.request = cdrcgi.getRequest(fields)
        self.start = fields.getvalue("start")
        self.end = fields.getvalue("end")
        self.status = fields.getvalue("status")
        self.language = fields.getvalue("language") or "all"
        self.audience = fields.getvalue("audience")
        self.show_resources = fields.getvalue("resources") and True or False
        self.notes = fields.getvalue("notes") and True or False
        self.blocked = fields.getvalue("blocked") and True or False
        self.report = fields.getvalue("report") or Control.SPANISH
        self.script = "Request4344.py"
        part = self.report == Control.SPANISH and "Spanish" or "English"
        self.section  = "Glossary Term Concept by %s Definition Status" % part
        self.sanitize()

    def run(self):
        """
        Figure out what the user asked us to do and do it.
        """
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", self.session)
        elif self.request == Control.SUBMENU:
            cdrcgi.navigateTo("Reports.py", self.session)
        if self.request == "Log Out":
            cdrcgi.logout(self.session)
        if self.request == "Submit Request":
            self.show_report()
        self.show_form()

    def show_report(self):
        "Display the requested report"
        columns = self.columns()
        subtitle = "%s to %s" % (self.start, self.end)
        caption = "%s Concepts With %s Status" % (self.audience, self.status)
        trans = (self.report == Control.SPANISH and "Translated" or "",) * 2
        path = "/GlossaryTermConcept/%sTermDefinition/%sStatusDate" % trans
        query = cdrdb.Query("query_term", "doc_id").unique()
        query.where(query.Condition("path", path))
        query.where(query.Condition("value", self.start, ">="))
        query.where(query.Condition("value", "%s 23:59:59" % self.end, "<="))
        query.order("doc_id")
        concepts = []
        for row in query.execute(self.cursor).fetchall():
            concept = Concept(self, row[0])
            if concept.in_scope():
                concepts.append(concept)
        rows = []
        for concept in concepts:
            rows += concept.rows()
        table = cdrcgi.Report.Table(columns, rows, caption=caption,
                                    html_callback_pre=Control.add_css)
        report = cdrcgi.Report(self.section, [table], subtitle=subtitle,
                               banner=self.section)
        report.send()

    @staticmethod
    def add_css(table, page):
        "Callback to add CSS to the report page"
        page.add_css(".blocked { color: red; font-weight: bold; }")

    def show_form(self):
        "Display the form for requesting the report"
        opts = {
            "subtitle": self.section,
            "session": self.session,
            "action": self.script,
            "buttons": self.BUTTONS
        }
        today = datetime.date.today()
        last_week = today - datetime.timedelta(7)
        page = cdrcgi.Page(Control.TITLE, **opts)
        page.add_hidden_field("report", self.report)
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Date Range"))
        page.add_date_field("start", "Start Date", value=last_week)
        page.add_date_field("end", "End Date", value=today)
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Definition Status"))
        checked = True
        for status in Control.STATUSES:
            page.add_radio("status", status, status, checked=checked)
            checked = False
        page.add("</fieldset>")
        if self.report == Control.SPANISH:
            page.add("<fieldset>")
            page.add(page.B.LEGEND("Language"))
            page.add_radio("language", "Spanish", "es", checked=True)
            page.add_radio("language", "All", "all")
            page.add("</fieldset>")
        page.add("<fieldset>")
        checked = True
        page.add(page.B.LEGEND("Audience"))
        for audience in Control.AUDIENCES:
            page.add_radio("audience", audience, audience, checked=checked)
            checked = False
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Other Report Options"))
        if self.report == Control.SPANISH:
            label = "Display Translation Resources"
        else:
            label = "Display Pronunciation Resources"
        page.add_checkbox("resources", label, "Y")
        page.add_checkbox("notes", "Display QC Notes Column", "Y")
        page.add_checkbox("blocked", "Include Blocked Term Name Documents", "Y")
        page.add("</fieldset>")
        page.send()
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Date Range"))
        page.add("</fieldset>")

    def sanitize(self):
        "Make sure the CGI parameters haven't been hacked"
        msg = "CGI parameter tampering detected"
        if not self.session: cdrcgi.bail("Unknown or expired CDR session.")
        cdrcgi.valParmVal(self.request, val_list=self.BUTTONS, emptyOK=True,
                          msg=msg)
        cdrcgi.valParmDate(self.start, emptyOK=True, msg=msg)
        cdrcgi.valParmDate(self.end, emptyOK=True, msg=msg)
        cdrcgi.valParmVal(self.status, val_list=Control.STATUSES, emptyOK=True,
                          msg=msg)
        cdrcgi.valParmVal(self.language, val_list=("all", "es"), msg=msg)
        cdrcgi.valParmVal(self.audience, val_list=Control.AUDIENCES,
                          emptyOK=True, msg=msg)
        if self.request == "Submit Request":
            if not (self.start and self.end and self.status and self.audience):
                cdrcgi.bail("Date range, status, and audience are "
                            "required fields")

    def columns(self):
        """
        Assemble the sequence of columns to be displayed, depending
        on which report was requested, with which options.
        """
        resource = { "class": "resource" }
        cols = [cdrcgi.Report.Column("CDR ID of GTC")]#, width="60px")]
        if self.report == Control.SPANISH:
            if self.language == "all":
                cols.append(cdrcgi.Report.Column("Term Name (EN)"))
            cols.append(cdrcgi.Report.Column("Term Name (ES)"))
            if self.language == "all":
                cols.append(cdrcgi.Report.Column("Definition (EN)"))
            cols.append(cdrcgi.Report.Column("Definition (ES)"))
            cols.append(cdrcgi.Report.Column("Comment"))
            if self.show_resources:
                cols.append(cdrcgi.Report.Column("Translation Resource",
                                                 **resource))
        else:
            cols.append(cdrcgi.Report.Column("Term Name (Pronunciation)"))
            if self.show_resources:
                cols.append(cdrcgi.Report.Column("Pronun. Resource",
                                                 **resource))
            cols.append(cdrcgi.Report.Column("Definition"))
            if self.status == "Revision pending":
                label = "Definition (Revision pending)"
                cols.append(cdrcgi.Report.Column(label))
            cols.append(cdrcgi.Report.Column("Definition Resource",
                                             **resource))
        if self.notes:
            padding = u"\xa0" * 10
            padding = ""
            heading = "QC %sNotes%s" % (padding, padding)
            cols.append(cdrcgi.Report.Column(heading, id="notes",
                                             width="200px"))
        return cols

class Cell(cdrcgi.Report.Cell):
    """
    Cell in the report's table, overriding the behavior of the
    default class in the cdrcgi module. Knows how to add HTML
    markup to the td element, representing the markup in the
    original CDR documents.
    """
    STYLES = {
        "Insertion": "color: red",
        "Deletion": "text-decoration: line-through",
        "Strong": "font-weight: bold",
        "Emphasis": "font-style: italic",
        "ScientificName": "font-style: italic"
    }
    B = cdrcgi.Page.B
    def __init__(self, value, **opts):
        cdrcgi.Report.Cell.__init__(self, value, **opts)
        self.extra = None
        self.concept = None
        self.suppress_deletion_markup = False
        self.comments = []

    def set_rowspan(self, rowspan):
        "Add a rowspan to the cell after the constructor has built the object"
        self._rowspan = rowspan

    def to_td(self):
        """
        Create a td element. If the source data is an element from
        a CDR document, using the markup in that element to create
        span child elements with appropriate styling. Otherwise
        just drop the string value in as the text content of the
        td element. Overrides Cell.to_td() from the cdrcgi module's
        version of this class.
        """
        if isinstance(self._value, etree._Element):
            td = self.populate(self.B.TD(), self._value)

            # 2015-12-09: Linda changed her mind - doesn't want this after all.
            # (see 2015-12-08 comment on
            #  https://tracker.nci.nih.gov/browse/OCECDR-3954)
            # for comment in self.comments:
            #     td.append(self.B.BR())
            #     td.append(self.B.SPAN(u"[COMMENT: %s]" % comment))
        else:
            td = self.B.TD(str(self._value))
        if self._rowspan:
            td.set("rowspan", str(self._rowspan))
        if self._classes:
            td.set("class", " ".join(self._classes))
        if self.extra is not None:
            td.append(self.extra)
        td.tail = None
        return td

    def populate(self, target, source, capitalize=False):
        """
        Recursively transfer text and markup from the source
        DOM subtree to the target element.
        """
        target.text = source.text
        if capitalize and target.text is not None and target.text:
            target.text = target.text.capitalize()
            capitalize = False
        for child in source:
            if child.tag == "Deletion" and self.suppress_deletion_markup:
                continue
            if child.tag == "PlaceHolder":
                name = child.get("name")
                if not name:
                    raise Exception(u"CDR%d: PlaceHolder without name" %
                                    self.concept.doc_id)
                if name in ("TERMNAME", "CAPPEDTERMNAME"):
                    replacement = None
                    if self.language == "en":
                        if self.concept.en_name:
                            replacement = self.concept.en_name._value
                    else:
                        if self.concept.es_name:
                            replacement = self.concept.es_name._value
                else:
                    replacement = self.concept.rep_nodes.get(name)
                if replacement is None:
                    span = self.B.SPAN("*** NO REPLACEMENT FOR %s ***" %
                                       repr(name))
                    span.set("style", "font-weight: bold; color: red")
                    span.tail = child.tail
                else:
                    span = self.B.SPAN(style="font-weight: bold")
                    if isinstance(replacement, basestring):
                        if name == "CAPPEDTERMNAME":
                            replacement = replacement.capitalize()
                        span.text = replacement
                        span.tail = child.tail
                    else:
                        capitalize = name == "CAPPEDTERMNAME"
                        replacement.tail = child.tail
                        self.populate(span, replacement, capitalize)
                target.append(span)
            else:
                span = self.B.SPAN()
                style = self.STYLES.get(child.tag)
                if style:
                    span.set("style", style)
                target.append(self.populate(span, child, capitalize))
        target.tail = source.tail
        return target

class Error(Cell):
    "Convenience subclass for a cell to be displayed in red"
    def __init__(self, message, rowspan=None):
        Cell.__init__(self, message, rowspan=rowspan, classes="error")

class Definition(Cell):
    """
    One of the definitions for a glossary concept. See base Cell class
    for more information about recursive mapping of the source information
    to a td element in the report page's table.
    """
    def __init__(self, concept, node):
        Cell.__init__(self, node.find("DefinitionText"))
        self.concept = concept
        self.language = node.tag == "TermDefinition" and "en" or "es"
        self.control = concept.control
        self.audience = node.find("Audience").text
        self.status = self.status_date = None
        self.resources = []
        for child in node:
            if child.tag in ("DefinitionResource",
                             "TranslationResource"):
                self.resources.append(child.text)
            elif child.tag in ("DefinitionStatus",
                               "TranslatedStatus"):
                self.status = child.text
            elif child.tag in ("StatusDate", "TranslatedStatusDate"):
                self.status_date = child.text
            elif child.tag == "Comment" and self.language == "es":
                self.comments.append(child.text)

    def in_scope(self):
        "Determine whether this definition matches the options for the report"
        if not self.status_date:
            return False
        if self.status_date < self.control.start:
            return False
        if self.status_date > self.control.end:
            return False
        if self.audience != self.control.audience:
            return False
        return self.status == self.control.status

class NameString(Cell):
    """
    The CDR glossary documents have an odd structure, in order to
    meet some fairly complicated requirements. Each glossary concept
    can have one or more GlossaryTermName documents and each valid
    GlossaryTermName document will have one English name string
    and zero or more Spanish name strings. Each of those name
    strings is represented by one of these objects. Derived from
    the Cell class to support rich text markup derivied from the
    markup in the original source elements in the CDR documents.
    """
    def __init__(self, name, node, english=False):
        Cell.__init__(self, node.find("TermNameString"),
                      classes=name.blocked and "blocked" or "")
        self.sort_key = u"".join(node.itertext()).lower()
        self.concept = name.concept
        if english and name.control.report == Control.ENGLISH:
            pron = node.find("TermPronunciation")
            if pron is not None and pron.text is not None:
                pron_text = pron.text.strip()
                if pron_text:
                    self.extra = self.B.SPAN(u" (%s)" % pron_text)
        tag = "PronunciationResource"
        self.resources = [child.text for child in node.findall(tag)]

    def __cmp__(self, other):
        """
        Name strings are sortable on the text content with markup
        stripped.
        """
        return cmp(self.sort_key, other.sort_key)

class Name:
    """
    One of the English names of a CDR glossary term concept, along
    with the Spanish names associated with that English name.
    See notes on the NameString class above.
    """
    def __init__(self, concept, doc_id):
        self.concept = concept
        self.control = concept.control
        self.doc_id = doc_id
        self.english = self.last_pub = self.pub_ver = self.blocked = None
        self.spanish  = []
        self.rep_nodes = {}
        query = cdrdb.Query("pub_proc_cg c", "d.doc_version", "p.completed")
        query.join("pub_proc_doc d", "d.doc_id = c.id")
        query.join("pub_proc p", "p.id = c.pub_proc")
        query.where(query.Condition("d.doc_id", doc_id))
        rows = query.execute(self.control.cursor, timeout=300).fetchall()
        if rows:
            self.pub_ver, self.last_pub = rows[0]
        query = cdrdb.Query("document", "xml", "active_status")
        query.where(query.Condition("id", doc_id))
        rows = query.execute(self.control.cursor).fetchall()
        if not rows:
            raise Exception("glossary concept name document CDR%s missing" %
                            doc_id)
        doc_xml, active_status = rows[0]
        self.blocked = active_status != "A"
        root = etree.XML(doc_xml.encode("utf-8"))
        for node in root.iter("ReplacementText"):
            self.rep_nodes[node.get("name")] = node
        for node in root:
            if node.tag == "TermName":
                self.english = NameString(self, node, True)
            elif node.tag == "TranslatedName":
                self.spanish.append(NameString(self, node))

    def get_published_definition(self):
        """
        Get the denormlized (that is, with placeholders replaced)
        definition from the version of the GlossaryTerm document
        we last exported to cancer.gov and our content distribution
        partners.
        """
        query = cdrdb.Query("pub_proc_cg", "xml")
        query.where(query.Condition("id", self.doc_id))
        rows = query.execute(self.control.cursor).fetchall()
        if not rows:
            return None
        if self.control.report == Control.ENGLISH:
            tag = "TermDefinition"
        else:
            tag = "SpanishTermDefinition"
        root = etree.XML(rows[0][0].encode("utf-8"))
        for node in root.iter(tag):
            definition = audience = None
            for child in node:
                if child.tag == "Audience":
                    audience = child.text
                elif child.tag == "DefinitionText":
                    definition = child
            if audience == self.control.audience:
                if definition is not None:
                    return Definition(self.concept, node)
        return None

    def __cmp__(self, other):
        """
        Support sorting of the names of a glossary concept,
        based on the English name string or the "first" Spanish
        name string, depending on which report we're creating.
        """
        if self.control.report == Control.ENGLISH:
            diff = cmp(self.english, other.english)
        else:
            if not self.spanish:
                if not other.spanish:
                    return cmp(self.docId, other.docId)
                return 1
            elif not other.spanish:
                return -1
            else:
                diff = cmp(self.spanish[0], other.spanish[0])
        if diff:
            return diff
        return cmp(self.docId, other.docId)

class Concept:
    """
    The top-level objects in the CDR glossary are concepts.
    Each concept has one or more definitions (for different
    languages and audiences) and possibly many names.
    """
    def __init__(self, control, doc_id):
        self.control = control
        self.doc_id = doc_id
        self.sp_def = self.en_def = self.en_name = self.es_name = None
        self.name = self.blocked = None
        self.names = []
        self.rep_nodes = {}
        query = cdrdb.Query("document", "xml", "active_status")
        query.where(query.Condition("id", doc_id))
        doc_xml, active_status = query.execute(control.cursor).fetchone()
        self.blocked = active_status != "A"
        root = etree.XML(doc_xml.encode("utf-8"))
        for node in root.iter("ReplacementText"):
            self.rep_nodes[node.get("name")] = node
        en_defs = [Definition(self, n)
                   for n in root.findall("TermDefinition")]
        sp_defs = [Definition(self, n)
                   for n in root.findall("TranslatedTermDefinition")]
        if control.report == Control.ENGLISH:
            for d in en_defs:
                if d.in_scope():
                    self.en_def = d
                    break
            if not self.en_def:
                return
        else:
            for d in sp_defs:
                if d.in_scope():
                    self.sp_def = d
                    break
            if not self.sp_def:
                return
            for d in en_defs:
                if d.audience == control.audience:
                    self.en_def = d
        path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
        query = cdrdb.Query("query_term", "doc_id").unique()
        query.where(query.Condition("path", path))
        query.where(query.Condition("int_val", doc_id))
        for row in query.execute(control.cursor).fetchall():
            n = Name(self, row[0])
            if control.blocked or not n.blocked:
                self.names.append(n)
        self.names.sort()
        for name in self.names:
            if name.last_pub:
                if not self.name or name.last_pub > self.name.last_pub:
                    self.name = name
        if not self.name:
            if self.names:
                self.name = self.names[0]
        if self.name:
            self.en_name = self.name.english
            for name in self.name.rep_nodes:
                self.rep_nodes[name] = self.name.rep_nodes[name]
        for name in self.names:
            if name.spanish:
                self.es_name = name.spanish[0]
                break

    def in_scope(self):
        "Should we include this glossary concept in the report?"
        if self.control.report == Control.SPANISH:
            if self.sp_def:
                return True
        else:
            return self.en_def and True or False

    def rows(self):
        "Requirements for the two reports differ enough to split out the logic"
        if self.control.report == Control.ENGLISH:
            return self.rows_en()
        return self.rows_es()

    def rows_en(self):
        """
        Assemble and return the rows for the report of glossary term
        concepts by English definition status.
        """
        rowspan = rev_def = None
        if len(self.names) > 1:
            rowspan = len(self.names)
        if self.names and self.names[0].english:
            name = self.names[0].english
            resource = self.names[0].english.resources
        else:
            name = Error("NO NAME FOUND")
            resource = ""
        definition = self.en_def
        definition.set_rowspan(rowspan)
        if self.control.status == "Revision pending":
            rev_def = definition
            rev_def.suppress_deletion_markup = True
            definition = None
            if self.name:
                definition = self.name.get_published_definition()
                if definition is not None:
                    definition.set_rowspan(rowspan)
            if definition is None:
                definition = Error("NO PUBLISHED DEFINITION FOUND", rowspan)
        row = [cdrcgi.Report.Cell(self.doc_id, rowspan=rowspan), name]
        if self.control.show_resources:
            row.append(resource)
        row.append(definition)
        if rev_def:
            row.append(rev_def)
        definition_resources = self.en_def.resources
        row.append(cdrcgi.Report.Cell(definition_resources, rowspan=rowspan))
        if self.control.notes:
            row.append(cdrcgi.Report.Cell("", rowspan=rowspan, width="100px"))
        rows = [row]
        for name in self.names[1:]:
            if name.english:
                row = [name.english]
                if self.control.show_resources:
                    row.append(name.english.resources)
                rows.append(row)
        return rows

    def rows_es(self):
        """
        Assemble and return the rows for the report of glossary term
        concepts by Spanish definition status.
        """
        rowspan = None
        row_count = 0
        for name in self.names:
            spanish_count = len(name.spanish)
            if not spanish_count and self.control.language == "all":
                spanish_count = 1
            row_count += spanish_count
            if not row_count:
                row_count = 1
        if row_count > 1:
            rowspan = row_count
        row = [cdrcgi.Report.Cell(self.doc_id, rowspan=rowspan)]
        if self.control.language == "all":
            if self.names and self.names[0].english:
                name = self.names[0].english
            else:
                name = Error("NO NAME FOUND", rowspan)
            if len(self.names[0].spanish) > 1:
                name.set_rowspan(len(self.names[0].spanish))
            row.append(name)
        if self.names and self.names[0].spanish:
            name = self.names[0].spanish[0]
        else:
            name = Error("NO NAME FOUND")
        row.append(name)
        if self.control.language == "all":
            if self.en_def:
                definition = self.en_def
            else:
                error = "NO %s DEFINITION FOUND" % control.audience.upper()
                definition = Error(error)
            definition.set_rowspan(rowspan)
            row.append(definition)
        self.sp_def.set_rowspan(rowspan)
        row.append(self.sp_def)
        if self.sp_def.comments:
            last_comment = self.sp_def.comments[0]
        else:
            last_comment = u""
        row.append(cdrcgi.Report.Cell(last_comment, rowspan=rowspan))
        if self.control.show_resources:
            def_resources = self.sp_def.resources
            row.append(cdrcgi.Report.Cell(def_resources, rowspan=rowspan))
        if self.control.notes:
            row.append(cdrcgi.Report.Cell("", rowspan=rowspan, width="100px"))
        rows = [row]
        if self.names:
            for name in self.names[0].spanish[1:]:
                rows.append([name])
        if self.control.language == "all":
            for n in self.names[1:]:
                e = n.english or Error("NO ENGLISH NAME")
                if len(n.spanish) > 1:
                    e.set_rowspan(len(n.spanish))
                s = n.spanish and n.spanish[0] or Error("NO SPANISH NAME")
                rows.append([e, s])
                for s in n.spanish[1:]:
                    rows.append([s])
        else:
            for n in self.names[1:]:
                for s in n.spanish:
                    rows.append([s])
        return rows

if __name__ == "__main__":
    "Allow the module to be imported without side effects"
    Control().run()
