#----------------------------------------------------------------------
# Media (Images) Processing Status Report.
#----------------------------------------------------------------------
import datetime
import re
import cdr
import cdrcgi
import cdrdb

class Control(cdrcgi.Control):
    """
    Logic for gathering request parameters from the user, and then
    generating the requested report.
    """

    def __init__(self):
        """
        Collect and validate the user's request parameters.
        """

        cdrcgi.Control.__init__(self, "Media (Images) Processing Status Report")
        self.begin = datetime.datetime.now()
        self.statuses = self.get_statuses()
        self.diagnoses = self.get_diagnoses()
        self.status = self.get_status()
        self.diagnosis = self.get_diagnosis()
        self.start = self.get_date("start")
        self.end = self.get_date("end")
    def get_status(self):
        status = self.fields.getvalue("status")
        if status and status not in self.statuses:
            cdrcgi.bail("bad status")
            cdrcgi.bail()
        return status
    def get_diagnosis(self):
        diagnosis = self.fields.getlist("diagnosis") or []
        try:
            diagnosis = [int(doc_id) for doc_id in diagnosis]
        except:
            cdrcgi.bail()
        if set(diagnosis) - set([d[0] for d in self.diagnoses]):
            cdrcgi.bail()
        return diagnosis
    def get_diagnoses(self):
        diagnosis_path = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
        query = cdrdb.Query("query_term t", "t.doc_id", "t.value")
        query.unique().order(2)
        query.join("query_term m", "m.int_val = t.doc_id")
        query.where("t.path = '/Term/PreferredName'")
        query.where("m.path = '%s'" % diagnosis_path)
        return query.execute(self.cursor).fetchall()
        return [["any", "Any Diagnosis"]] + query.execute(cursor).fetchall()
    def get_statuses(self):
        dt = cdr.getDoctype(self.session, "Media")
        statuses = dict(dt.vvLists).get("ProcessingStatusValue")
        if not statuses:
            cdrcgi.bail("unable to load valid processing status values")
        return [status for status in statuses if not status.startswith("Audio")]
    def get_date(self, name):
        value = self.fields.getvalue(name)
        cdrcgi.valParmDate(value, empty_ok=True, msg=cdrcgi.TAMPERING)
        return value
    def populate_form(self, form):
        """
        Put the fields we need on the form. See documentation of the
        cdrcgi.Page class for examples and other details. Read the
        comment at the bottom of this script to see when and how this
        callback method is invoked.
        """
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Request Parameters (only Status is required)"))
        form.add_select("status", "Status", self.statuses)
        form.add_date_field("start", "Start Date")
        form.add_date_field("end", "End Date")
        form.add_select("diagnosis", "Diagnosis", self.diagnoses,
                        multiple=True)
        form.add("</fieldset>")
        form.add_output_options("html")

    def build_tables(self):
        """
        Callback to give the base class an array of Table objects
        (only one in our case). See documentation of that class in
        the cdrcgi module. Read the comment at the bottom of this
        script to learn now and when this method is called.
        """
        if not self.status:
            cdrcgi.bail("missing required status value")
        query = cdrdb.Query("query_term i", "i.doc_id")
        query.where("i.path = '/Media/PhysicalMedia/ImageData/ImageType'")
        if self.diagnosis:
            query.join("query_term d", "d.doc_id = i.doc_id")
            query.where(query.Condition("d.int_val", self.diagnosis, "IN"))
        ids = [row[0] for row in query.execute(self.cursor).fetchall()]
        docs = [Doc(id, self) for id in ids]
        rows = [doc.row() for doc in sorted(docs) if doc.in_scope()]
        columns = (
            cdrcgi.Report.Column("CDR ID"),
            cdrcgi.Report.Column("Media Title", width="250px"),
            cdrcgi.Report.Column("Diagnosis", width="150px"),
            cdrcgi.Report.Column("Processing Status", width="150px"),
            cdrcgi.Report.Column("Processing Status Date", width="100px"),
            cdrcgi.Report.Column("Proposed Summaries", width="300px"),
            cdrcgi.Report.Column("Proposed Glossary Terms", width="300px"),
            cdrcgi.Report.Column("Comments", width="300px"),
            cdrcgi.Report.Column("Last Version Publishable", width="125px"),
            cdrcgi.Report.Column("Published", width="100px"),
        )
        caption = [self.title]
        if self.start:
            if self.end:
                caption.append("From %s - %s" % (self.start, self.end))
            else:
                caption.append("On or after %s" % self.start)
        elif self.end:
            caption.append("On or before %s" % self.end)
        caption.append(self.status)
        return [cdrcgi.Report.Table(columns, rows, caption=caption)]
    def set_report_options(self, opts):
        opts["elapsed"] = datetime.datetime.now() - self.begin
        opts["banner"] = self.PAGE_TITLE
        opts["subtitle"] = "Media Reports"
        self.PAGE_TITLE = "Media Processing Status Report"
        return opts
class Doc:
    HOST = cdrcgi.WEBSERVER
    BASE = cdrcgi.BASE
    linked_titles = {}
    def __init__(self, doc_id, control):
        self.doc_id = doc_id
        self.control = control
        self.title = self.status = self.last_publishable_date = None
        self.last_version_publishable = False
        try:
            self.root = self.control.get_parsed_doc_xml(doc_id)
        except Exception as e:
            cdrcgi.bail(e)
        self.title = (self.root.find("MediaTitle").text or "").strip()
        self.status = None
        for node in self.root.findall("ProcessingStatuses/ProcessingStatus"):
            self.status = self.Status(node)
            break
    def row(self):
        diagnoses = []
        summaries = []
        glossary_terms = []
        diagnosis_map = dict(self.control.diagnoses)
        for node in self.root.findall("MediaContent/Diagnoses/Diagnosis"):
            cdr_id = self.control.get_cdr_ref_int(node)
            diagnosis = diagnosis_map.get(cdr_id)
            if diagnosis:
                diagnoses.append(diagnosis)
        for node in self.root.findall("ProposedUse/*"):
            title = self.get_linked_title(node)
            if title:
                if node.tag == "Summary":
                    summaries.append(title.split(";")[0])
                elif node.tag == "Glossary":
                    glossary_terms.append(title.split(";")[0])
        self.check_last_versions()
        publishable = self.last_version_publishable and "Yes" or "No"
        values = (self.HOST, self.BASE, self.control.session, self.doc_id)
        url = "https://%s%s/QcReport.py?Session=%s&DocId=%d" % values
        return [cdrcgi.Report.Cell(self.doc_id, href=url, target="_blank"),
                self.title, u"; ".join(diagnoses),
                self.status.value, self.make_date_cell(self.status.date),
                u"; ".join(summaries), u"; ".join(glossary_terms),
                u"; ".join(self.status.comments),
                cdrcgi.Report.Cell(publishable, center=True),
                self.make_date_cell(self.last_publishable_date)]
    def make_date_cell(self, date):
        if not date:
            return ""
        return cdrcgi.Report.Cell(str(date)[:10], classes="nowrap center")
    def check_last_versions(self):
        versions = cdr.lastVersions(self.control.session, self.doc_id)
        #cdrcgi.bail("versions: %s" % versions)
        if versions[1] > 0:
            self.last_version_publishable = versions[0] == versions[1]
            query = cdrdb.Query("doc_version", "dt")
            query.where(query.Condition("id", self.doc_id))
            query.where(query.Condition("num", versions[1]))
            row = query.execute(self.control.cursor).fetchone()
            if row:
                self.last_publishable_date = row[0]
    def get_linked_title(self, node):
        cdr_id = self.control.get_cdr_ref_int(node)
        if not cdr_id:
            return None
        if cdr_id not in Doc.linked_titles:
            Doc.linked_titles[cdr_id] = self.control.get_doc_title(cdr_id)
        return Doc.linked_titles[cdr_id]
    def in_scope(self):
        if not self.status:
            return False
        if self.status.value != self.control.status:
            return False
        if self.control.start:
            if not self.status.date or self.status.date < self.control.start:
                return False
        if self.control.end:
            if not self.status.date or self.status.date > self.control.end:
                return False
        return True
    def __cmp__(self, other):
        return cmp((self.title or "").lower(), (other.title or "").lower())
    class Status:
        def __init__(self, node):
            self.value = self.date = None
            self.comments = []
            for child in node:
                if child.text is not None:
                    if child.tag == "ProcessingStatusValue":
                        self.value = child.text
                    elif child.tag == "ProcessingStatusDate":
                        self.date = child.text
                    elif child.tag == "Comment":
                        self.comments.append(child.text)

#----------------------------------------------------------------------
# Instantiate an instance of our class and invoke the inherited run()
# method. This method acts as a switch statement, in effect, and checks
# to see whether any of the action buttons have been clicked. If so,
# and the button is not the "Submit" button, the user is taken to
# whichever page is appropriate to that button (e.g., logging out,
# the reports menu, or the top-level administrative menu page).
# If the clicked button is the "Submit" button, the show_report()
# method is invoked. The show_report() method in turn invokes the
# build_tables() method, which we have overridden above. It also
# invokes set_report_options() which we could override if we wanted
# to modify how the report's page is displayed (for example, to
# change which buttons are displayed); we're not overriding that
# method in this simple example. Finally show_report() invokes
# report.send() to display the report.
#
# If no button is clicked, the run() method invokes the show_form()
# method, which in turn calls the set_form_options() method (which
# we're not overriding here) as well as the populate_form() method
# (see above) before calling form.send() to display the form.
#----------------------------------------------------------------------
if __name__ == "__main__":
    Control().run()
