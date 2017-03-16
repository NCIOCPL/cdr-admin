#----------------------------------------------------------------------
#
# Show version history of document.
#
# BZIssue::216  - explain unavailable removal dates
# BZIssue::3539 - show publishing event that removed the document
# Rewritten summary 2015 as part of security sweep.
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb
import datetime

class Control(cdrcgi.Control):
    """
    Show form for selecting document (and possibly intermediate form
    for choosing from multiple matches to title field), then collect
    information about the selected document's versions and display it.
    """

    TITLE = "Document Version History Report"

    def __init__(self):
        "Scrub the request parameters"
        cdrcgi.Control.__init__(self, Control.TITLE)
        cdrcgi.valParmVal(self.request, val_list=self.buttons, empty_ok=True,
                          msg=cdrcgi.TAMPERING)
        self.document = self.get_doc()
        if self.document:
            self.request = self.SUBMIT

    def populate_form(self, form):
        "Let the user specify a document ID or a document title"
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Specify Document ID or Title"))
        form.add_text_field(cdrcgi.DOCID, "Doc ID")
        form.add_text_field("DocTitle", "Doc Title")
        form.add("</fieldset>")

    def get_doc(self):
        "Find the requested document; if there are choices, show them"
        doc_id = self.fields.getvalue(cdrcgi.DOCID)
        if doc_id:
            try:
                doc_id = cdr.exNormalize(doc_id)[1]
                return Document(self, doc_id)
            except Exception:
                cdrcgi.bail("Not a valid document ID")
        title = unicode(self.fields.getvalue("DocTitle", ""), "utf-8")
        if not title:
            return None
        query = cdrdb.Query("document d", "d.id", "d.title", "t.name").order(2)
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("title", title + "%", "LIKE"))
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            cdrcgi.bail("No matching documents found")
        if len(rows) > 1:
            self.offer_choices(rows)
        return Document(self, rows[0][0])

    def offer_choices(self, rows):
        "Show the user the documents matching the title pattern"
        legend = "Choose Document"
        if len(rows) > 500:
            legend = "Choose Document (First 500 Shown)"
            rows = rows[:500]
        opts = {
            "buttons": self.buttons,
            "action": self.script,
            "session": self.session,
            "subtitle": "Multiple documents found"
        }
        page = cdrcgi.Page(self.TITLE, **opts)
        page.add("<fieldset>")
        page.add(page.B.LEGEND(legend))
        checked=True
        for doc_id, doc_title, doc_type in rows:
            tooltip = u"CDR%d (%s) %s" % (doc_id, doc_type, doc_title)
            if len(doc_title) > 90:
                doc_title = doc_title[:90] + " ..."
            page.add_radio(cdrcgi.DOCID, doc_title, str(doc_id),
                           checked=checked, tooltip=tooltip)
            checked=False
        page.add("</fieldset>")
        page.add_css("fieldset { width: 800px; }")
        page.send()

    def build_tables(self):
        "Override base class method for generating the report"
        if not self.document:
            cdrcgi.bail("Document ID or title must be specified")
        return [self.document.build_table()]

    def set_report_options(self, opts):
        "Override base class method for customizing the report display"
        opts["subtitle"] = str(datetime.date.today())
        opts["page_opts"] = {}
        return opts

class Document:
    "CDR document which will be the subject of the requested report"

    # Convenience variable for the HTML builder class
    B = cdrcgi.Page.B

    def __init__(self, control, doc_id):
        "Collect the information to be shown on the report"
        self.control = control
        self.doc_id = doc_id
        fields = ("doc_title", "doc_type", "doc_status", "created_by",
                  "created_date", "mod_by", "mod_date")
        query = cdrdb.Query("doc_info", *fields)
        query.where(query.Condition("doc_id", doc_id))
        row = query.execute(control.cursor).fetchone()
        if not row:
            cdrcgi.bail("CDR%d not found" % doc_id)
        self.doc_title = row[0]
        self.doc_type = row[1]
        self.doc_status = row[2]
        self.created_by = row[3]
        self.created_date = row[4]
        self.modified_by = row[5]
        self.mod_date = row[6]
        self.last_pub_job = self.last_pub_version = self.remove_date = None
        self.blocked = self.doc_status == "I"
        self.versions = self.load_versions()
        self.version_numbers = sorted(self.versions, reverse=True)

    def build_table(self):
        """
        Build the report body using a table with one row for each version.
        Put the most recent versions at the top, because those are the ones
        we're most likely to be interested in.
        """
        columns = (
            cdrcgi.Report.Column("Version"),
            cdrcgi.Report.Column("Comment"),
            cdrcgi.Report.Column("Date"),
            cdrcgi.Report.Column("User"),
            cdrcgi.Report.Column("Validity"),
            cdrcgi.Report.Column("Publishable?"),
            cdrcgi.Report.Column("Publication Date(s)")
        )
        rows = [self.versions[v].assemble_row() for v in self.version_numbers]
        return cdrcgi.Report.Table(columns, rows, user_data=self,
                                   html_callback_pre=self.callback)

    def published(self):
        "Find out if the document is currently on the web site"
        query = cdrdb.Query("pub_proc_cg", "id")
        query.where(query.Condition("id", self.doc_id))
        rows = query.execute(self.control.cursor).fetchall()
        return rows and True or False

    def first_full_load_after_last_pub_job(self):
        """
        We're looking for an explanation for why the document isn't
        on the web site. One possibility is that a full load took
        place after the last time this document was published.
        Rare but possible.
        """
        if not self.last_pub_job:
            return None
        query = cdrdb.Query("pub_proc", "MIN(started)")
        query.where("status = 'Success'")
        query.where("pub_subset = 'Full-Load'")
        query.where(query.Condition("id", self.last_pub_job, ">"))
        rows = query.execute(self.control.cursor).fetchall()
        return rows and rows[0][0] and rows[0][0][:10] or None

    def load_versions(self):
        "Collect information on all of the versions created for this doc"
        fields = ("v.num", "v.comment", "u.fullname", "v.dt",
                  "v.val_status", "v.publishable")
        query = cdrdb.Query("doc_version v", *fields)
        query.join("open_usr u", "u.id = v.usr")
        query.where(query.Condition("v.id", self.doc_id))
        versions = {}
        rows = query.execute(self.control.cursor).fetchall()
        for num, comment, user, date, status, publishable in rows:
            versions[num] = self.Version(num, comment, user, date,
                                         status, publishable)

        # Fold in the publication events.
        fields = ("doc_version", "started", "pub_proc", "removed", "output_dir")
        query = cdrdb.Query("primary_pub_doc", *fields)
        query.where(query.Condition("doc_id", self.doc_id))
        query.order("started")
        for row in query.execute(self.control.cursor).fetchall():
            num, started, pub_job, removed, output_dir = row
            job_type = output_dir and "V" or "C"
            pub_date = started[:10]
            versions[num].add_pub_event(pub_date, job_type, pub_job, removed)
            if removed == "Y" and self.blocked:
                self.remove_date = pub_date
            if not self.last_pub_job or pub_job > self.last_pub_job:
                    self.last_pub_job = pub_job
            if not self.last_pub_version or num > self.last_pub_version:
                self.last_pub_version = num
        return versions

    @staticmethod
    def callback(table, page):
        """
        Hook for displaying information about the document which is
        not version specific.
        """
        doc = table.user_data()
        doc.show_doc_info(page)

    def show_doc_info(self, page):
        """
        Display a table of information about the document which is
        not specific to any given version.
        """
        cdr_id = cdr.normalize(self.doc_id)
        created = self.created_date and self.created_date[:10] or cdr.URDATE
        created_by = self.created_by or u"[Conversion]"
        modified = self.mod_date and self.mod_date[:10] or None
        modified_by = self.modified_by or "N/A"
        removal = self.get_removal_info()
        page.add('<table class="doc-info">')
        page.add("<tr>")
        page.add(page.B.TH("Document"))
        page.add(page.B.TD("%s (%s)" % (cdr_id, self.doc_type)))
        page.add("</tr>")
        page.add("<tr>")
        page.add(page.B.TH("Title"))
        page.add(page.B.TD(self.doc_title))
        page.add("</tr>")
        if removal:
            status = "BLOCKED FOR PUBLICATION (%s)" % removal
            page.add("<tr>")
            page.add(page.B.TH("Status"))
            page.add(page.B.TD(status, page.B.CLASS("blocked")))
            page.add("</tr>")
        page.add("<tr>")
        page.add(page.B.TH("Created"))
        page.add(page.B.TD("%s by %s" % (created, created_by)))
        page.add("</tr>")
        page.add("<tr>")
        if modified:
            page.add(page.B.TH("Updated"))
            page.add(page.B.TD("%s by %s" % (modified, modified_by)))
            page.add("</tr>")
        page.add("</table>")
        page.add_css("""\
.removed, .blocked { color: red; }
.doc-info th { text-align: right; }""")

    def get_removal_info(self):
        """
        If a document has been blocked for publication (doc_status is 'I' --
        for "Inactive") we display an extra row showing the status and the
        date the document was pulled from Cancer.gov (assuming it has been
        pulled).
        """
        if not self.blocked:
            return None

        # Make sure we have a removal date.  Normally we will, if the
        # document has ever been published, because when the document is
        # blocked the next publication event sends an instruction to
        # Cancer.gov to withdraw the document, in which case we will have
        # picked up the removal date when we collected the information
        # on publication events.
        if self.remove_date:
            return "removed %s" % self.remove_date

        # No removal date.  Is the document still on Cancer.gov?
        if self.published():

            # Yes, which means the document was blocked since last
            # published and will be removed as part of the next
            # publication job.  However, only a versioned document
            # can be removed, so we check to see if a version has
            # been created since the last version which got published.
            if self.versions:
                if self.version_numbers[0] > self.last_pub_version:
                    return "not yet removed"
            return "needs versioning to be removed"

        # The document isn't on Cancer.gov.  Was it removed by
        # a full load (meaning the sequence of events was
        # publication of the document when it was active,
        # followed by a change of status to inactive, after
        # which the next publication event was a full load)?
        remove_date = self.first_full_load_after_last_pub_job()
        if remove_date:
            return "removed %s" % remove_date

        # If that didn't happen, then presumably the document
        # was never published.
        if not self.last_pub_job:
            return "never published"

        # Otherwise, we have a data corruption problem.
        return "CAN'T DETERMINE REMOVAL DATE"

    class Version:
        "Object to hold info for a single version of the document"
        def __init__(self, num, comment, user, date, status, publishable):
            self.num = num
            self.comment = comment
            self.user = user
            self.date = date[:16]
            self.status = status
            self.publishable = publishable
            self.pub_events = []

        def add_pub_event(self, job_date, job_type, job_id, removed):
            "Record a publication of the document from this version"
            event = self.PubEvent(job_date, job_type, job_id, removed)
            self.pub_events.append(event)

        @staticmethod
        def show_pub_events(cell, output_type):
            "Callback method to generate the cell in the table's last column"
            events = cell._value
            td = Document.B.TD()
            if events:
                event = events.pop(0)
                td.append(event.to_span())
                while events:
                    event = events.pop(0)
                    td.append(Document.B.BR())
                    td.append(event.to_span())
            return td

        def assemble_row(self):
            "Create the line in the report for this version"
            return [
                cdrcgi.Report.Cell(self.num, classes="center"),
                self.comment or "",
                self.date,
                self.user,
                cdrcgi.Report.Cell(self.status, classes="center"),
                cdrcgi.Report.Cell(self.publishable == "Y" and "Y" or "N",
                                   classes="center"),
                cdrcgi.Report.Cell(self.pub_events,
                                   callback=self.show_pub_events)
            ]

        class PubEvent:
            "Information about a publication of this document"
            def __init__(self, job_date, job_type, job_id, removed):
                self.job_date = job_date
                self.job_type = job_type
                self.job_id = job_id
                self.removed = removed == "Y"

            def to_span(self):
                "Convert this event to its HTML display object"
                event = "%s(%s-%d)" % (self.job_date, self.job_type,
                                       self.job_id)
                if self.removed:
                    event += "R"
                    return Document.B.SPAN(event, Document.B.CLASS("removed"))
                else:
                    return Document.B.SPAN(event)

if __name__ == "__main__":
    "Allow documentation or lint tools to load script without side effects"
    Control().run()
