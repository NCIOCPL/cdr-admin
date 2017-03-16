#----------------------------------------------------------------------
# Display CDR summary translation job queue.
# JIRA::OCECDR-4193
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb

class Control(cdrcgi.Control):
    """
    Logic for collecting and displaying the active CDR summary
    translation jobs, including links to the editing page for
    modifying individual jobs, as well as a button for creating
    a new job, and a button for clearing out jobs which have run
    the complete processing course.
    """

    ADD = "Add Job"
    PURGE = "Purge Completed Jobs"

    def __init__(self):
        """
        Make sure the user is authorized to manage the translation queue.
        """

        cdrcgi.Control.__init__(self, "Translation Job Queue")
        if not self.session:
            cdrcgi.bail("not authorized")
        if not cdr.canDo(self.session, "MANAGE TRANSLATION QUEUE"):
            cdrcgi.bail("not authorized")
        self.message = None

    def run(self):
        """
        Override the base class method, as we support extra buttons/tasks.
        """

        if self.request == self.ADD:
            cdrcgi.navigateTo("translation-job.py", self.session)
        if self.request == self.PURGE:
            if not cdr.canDo(self.session, "PRUNE TRANSLATION QUEUE"):
                cdrcgi.bail("not authorized")
            conn = cdrdb.connect()
            cursor = conn.cursor()
            cursor.execute("""\
DELETE FROM summary_translation_job
      WHERE state_id = (SELECT value_id
                          FROM summary_translation_state
                         WHERE value_name = 'Translation Made Publishable')""")
            count = cursor.rowcount
            conn.commit()
            self.message = "Purged jobs for %d published translations." % count
        cdrcgi.Control.run(self)

    def set_form_options(self, opts):
        """
        Add our custom buttons for the extra tasks.
        """

        opts["buttons"][0] = self.PURGE
        opts["buttons"].insert(0, self.ADD)
        return opts

    def populate_form(self, form):
        """
        Instead of form fields, we're actually displaying a table
        containing one row for each job in the queue, sorted by
        job state, with a sub-sort on user name and date of last
        state transition.
        """

        if self.message:
            form.add(form.B.P(self.message,
                              style="color: green; font-weight: bold"))
        fields = ("d.id", "d.title", "s.value_name", "c.value_name",
                  "u.fullname", "j.state_date", "j.comments")
        query = cdrdb.Query("summary_translation_job j", *fields)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.english_id")
        query.join("summary_translation_state s", "s.value_id = j.state_id")
        query.join("summary_change_type c", "c.value_id = j.change_type")
        query.order("s.value_pos", "u.fullname", "j.state_date")
        rows = query.execute(self.cursor).fetchall()
        jobs = sorted([Job(self, *row) for row in rows])
        body = form.B.TBODY()
        for job in jobs:
            body.append(job.tr())
        table = form.B.TABLE(
            form.B.CLASS("report"),
            form.B.THEAD(
                form.B.TR(
                    form.B.TH("CDR ID"),
                    form.B.TH("Title"),
                    form.B.TH("Audience"),
                    form.B.TH("Status"),
                    form.B.TH("Assigned To"),
                    form.B.TH("Date"),
                    form.B.TH("Type of Change"),
                    form.B.TH("Comments")
                )
            ),
            body,
        )
        form.add(table, False)

class Job:
    """
    Holds the information for a single CDR summary translation job.
    """

    URL = "translation-job.py?Session=%s&english_id=%s"

    def __init__(self, control, doc_id, title, state, change, user, date, cmt):
        """
        Store the information pulled from the database tables.
        """

        self.control = control
        self.doc_id = doc_id
        self.title = title.split(";")[0]
        self.audience = title.split(";")[-1]
        self.state = state
        self.change = change
        self.user = user
        self.date = date
        self.comments = cmt

    def tr(self):
        """
        Create a row for the job queue table, showing information about
        this individual translation job.
        """

        B = cdrcgi.Page.B
        url = self.URL % (self.control.session, self.doc_id)
        link = B.A("CDR%d" % self.doc_id, href=url, title="edit job")
        comments = self.comments or ""
        if len(comments) > 40:
            comments = comments[:40] + "..."
        return B.TR(
            B.TD(link),
            B.TD(self.title),
            B.TD(self.audience),
            B.TD(self.state),
            B.TD(self.user),
            B.TD(str(self.date)[:10], B.CLASS("nowrap")),
            B.TD(self.change),
            B.TD(comments)
        )

if __name__ == "__main__":
    """
    Make it possible to load this script as a module.
    """

    Control().run()
