#!/usr/bin/env python

#----------------------------------------------------------------------
# CDR document XML viewer
#----------------------------------------------------------------------
import cdr
import cdrcgi
from cdrapi import db

class Control(cdrcgi.Control):
    """
    Override base class to generate specific report.
    """

    LOGNAME = "cdr-document-viewer"

    def __init__(self):
        """
        Gather form parameters, applying defaults as needed.

        Validation is done later.
        """
        cdrcgi.Control.__init__(self, "CDR Document Viewer")
        self.method = self.fields.getvalue("method") or "id"
        self.doc_id = self.fields.getvalue("doc-id") or ""
        self.fragment = self.fields.getvalue("title") or ""
        self.doctypes = self.fields.getlist("doctype")
        self.vtype = self.fields.getvalue("vtype") or "cwd"
        self.version = self.fields.getvalue("version") or ""

    def run(self):
        """
        Override of the base class method to support immediately
        display without the CGI form.
        """

        if self.doc_id:
            self.show_report()
        cdrcgi.Control.run(self)

    def show_report(self):
        """
        Display the version of the CDR document requested by the user.

        If match_title() is called and finds more than one match,
        it puts up a chained form for selecting one of the matched
        documents, never returning to this method.
        """

        doc_id = self.method == "title" and self.match_title() or self.doc_id
        if not doc_id:
            cdrcgi.bail("Missing document ID")
        try:
            doc_id = cdr.exNormalize(doc_id)[1]
        except Exception:
            cdrcgi.bail("Invalid document ID")
        if self.vtype == "exported":
            query = db.Query("pub_proc_cg", "xml")
            what = "exported XML"
        else:
            version = self.get_version(doc_id)
            if version:
                query = db.Query("doc_version", "xml")
                query.where(query.Condition("num", version))
                what = "version %s" % version
            else:
                what = "current working document"
                query = db.Query("document", "xml")
        query.where(query.Condition("id", doc_id))
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            cdrcgi.bail("document not currently exported")
        self.logger.info("showing %s for CDR%d", what, doc_id)
        cdrcgi.sendPage(rows[0][0], "xml")

    def populate_form(self, form, title=None):
        """
        Let the user pick a document by ID or by title.
        """

        doctypes = self.get_doctypes()
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Selection Method"))
        form.add_radio("method", "By document ID", "id", checked=True)
        form.add_radio("method", "By document title", "title")
        form.add("</fieldset>")
        form.add('<fieldset id="by-id-block">')
        form.add(form.B.LEGEND("Document ID"))
        form.add_text_field("doc-id", "CDR ID")
        form.add("</fieldset>")
        form.add('<fieldset id="by-title-block" class="xxhidden">')
        form.add(form.B.LEGEND("Title Or Title Pattern"))
        form.add(self.TITLE_HELP)
        form.add_text_field("title", "Title")
        form.add_select("doctype", "Doc Type", doctypes, multiple=True)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Document Version"))
        checked = True
        for vtype in self.VERSION_TYPES:
            label = self.VERSION_TYPE_LABELS[vtype]
            if vtype == "num":
                form.add_radio("vtype", label, vtype, wrapper_id="num-div")
            else:
                form.add_radio("vtype", label, vtype, checked=checked)
            checked=False
        form.add("</fieldset>")
        form.add('<fieldset id="version-number-block" class="xxhidden">')
        form.add(form.B.LEGEND("Version Number"))
        form.add_text_field("version", "Version", tooltip=self.VHELP)
        form.add("</fieldset>")
        form.add_script(self.SCRIPT)

    def get_version(self, doc_id):
        """
        Return the integer version number for the user's request.

        Most often the user will request a version generically
        (latest version created, latest publishable version, etc.)
        but it is possible to enter a specific version number
        directly when picking a document by ID (doesn't work as
        well when entering a title fragment to be matched, because
        if the user doesn't already know the document ID, she's
        unlikely to know the numbers of the versions).
        """

        if self.vtype == "cwd":
            query = db.Query("document", "id")
            query.where(query.Condition("id", doc_id))
            rows = query.execute(self.cursor).fetchall()
            if not rows:
                cdrcgi.bail("CDR%d not found" % doc_id)
            return None
        if self.vtype == "latest":
            query = db.Query("doc_version", "MAX(num)")
            query.where(query.Condition("id", doc_id))
            rows = query.execute(self.cursor).fetchall()
            if not rows:
                cdrcgi.bail("no versions found for CDR%d" % doc_id)
            return rows[0][0]
        if self.vtype == "lastpub":
            query = db.Query("publishable_version", "MAX(num)")
            query.where(query.Condition("id", doc_id))
            rows = query.execute(self.cursor).fetchall()
            if not rows:
                cdrcgi.bail("no publishable versions found for CDR%d" % doc_id)
            return rows[0][0]
        if self.version.startswith("-"): # -1 is latest, -2 next-to-last, etc.
            version = self.version[1:]
            if not version.isdigit():
                cdrcgi.bail("invalid version")
            back = int(version)
            query = db.Query("doc_version", "num").limit(back)
            query.where(query.Condition("id", doc_id))
            rows = query.order("num DESC").execute(self.cursor).fetchall()
            if not rows:
                cdrcgi.bail("no versions found for CDR%d" % doc_id)
            elif len(rows) < back:
                cdrcgi.bail("only %d versions found for CDR%d" %
                            (len(rows), doc_id))
            return rows[-1][0]
        if not self.version.isdigit():
            cdrcgi.bail("invalid version")
        query = db.Query("doc_version", "num")
        query.where(query.Condition("id", doc_id))
        query.where(query.Condition("num", self.version))
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            cdrcgi.bail("version %s not found for CDR%d" % (self.version,
                                                            doc_id))
        return rows[0][0]

    def match_title(self):
        """
        Find documents matching the specified title fragment.

        If exactly one document is found, return its ID.
        If more than one match is found, put up a picker form.
        If no documents match, display an error message.
        """

        fragment = self.fragment.strip()
        if not fragment:
            cdrcgi.bail("Missing title")
        query = db.Query("document d", "d.id", "d.title", "t.name")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("d.title", fragment, "LIKE"))
        if self.doctypes:
            query.where(query.Condition("t.name", self.doctypes, "IN"))
            types = ", ".join(sorted(self.doctypes))
            self.logger.info("matching %r in %s", fragment, types)
        else:
            self.logger.info("matching title fragment %r", fragment)
        rows = query.order("d.id").execute(self.cursor).fetchall()
        if not rows:
            cdrcgi.bail("No matching documents found")
        if len(rows) == 1:
            return rows[0][0]
        opts = {
            "buttons": self.buttons,
            "action": self.script,
            "subtitle": self.title,
            "session": self.session
        }
        self.logger.info("putting up picker form for %d matches", len(rows))
        form = cdrcgi.Page(self.PAGE_TITLE, **opts)
        form.add_hidden_field("method", "by-id")
        form.add_hidden_field("version", self.version)
        form.add_hidden_field("vtype", self.vtype)
        form.add('<fieldset style="width: 1024px">')
        form.add(form.B.LEGEND("Choose Document"))
        for doc_id, title, doctype in rows:
            tooltip = None
            display = "CDR%d [%s] %s" % (doc_id, doctype, title)
            if len(display) > 125:
                display, tooltip = display[:125] + "...", display
            form.add_radio("doc-id", display, doc_id, tooltip=tooltip)
        form.add("</fieldset>")
        self.new_tab_on_submit(form)
        form.send()

    def get_doctypes(self):
        """
        Get the names of the active document types for the form picklist.
        """

        query = db.Query("doc_type", "name")
        query.where("active = 'Y'")
        query.where("xml_schema IS NOT NULL")
        rows = query.order("name").execute(self.cursor).fetchall()
        return [row[0] for row in rows]

    VHELP = (
        "Integer (negative for recent versions: -1 is last version saved; "
        "-2 is next-to-last version, etc.)"
    )
    VERSION_TYPE_LABELS = {
        "cwd": "Current working document",
        "latest": "Most recently created version",
        "lastpub": "Most recently created publishable version",
        "exported": "Filtered XML most recently sent to cancer.gov",
        "num": "Version by number"
    }
    VERSION_TYPES = "cwd", "latest", "lastpub", "exported", "num"
    TITLE_HELP = (
        '<p style="color: green; font-style: italic; font; font-size: 11pt">'
        "Use the wildcards (e.g., liver cancer%) unless you only want "
        "documents whose document title is an exact match (ignoring case) "
        "with the Title field. "
        "You can also optionally select one or more document "
        "types to narrow the selection.</p>"
    )
    SCRIPT = """\
function check_method(method) {
    switch (method) {
        case "id":
            jQuery("#by-id-block").show();
            jQuery("#by-title-block").hide();
            jQuery("#num-div").show();
            break;
        case "title":
            jQuery("#by-id-block").hide();
            jQuery("#by-title-block").show();
            jQuery("#num-div").hide();
            jQuery("#version-number-block").hide();
            if (jQuery("#vtype-num").prop("checked")) {
                jQuery("#vtype-num").prop("checked", false);
                jQuery("#vtype-cwd").prop("checked", true);
            }
            break;
    }
}
function check_vtype(vtype) {
    if (vtype == "num")
        jQuery("#version-number-block").show();
    else
        jQuery("#version-number-block").hide();
}
jQuery(function() {
    check_vtype(jQuery("input[name='vtype']:checked").val());
    check_method(jQuery("input[name='method']:checked").val());
});"""

Control().run()
