"""
Display CDR glossary translation job queue.

https://tracker.nci.nih.gov/browse/OCECDR-4489
"""

import cdr
import cdrcgi
from cdrapi import db

class Control(cdrcgi.Control):
    """
    Logic for collecting and displaying the active CDR glossary
    translation jobs, including links to the editing page for
    modifying individual jobs, as well as a button for creating
    a new job, a button for clearing out jobs which have run
    the complete processing course, and a button for reassigning
    jobs in bulk.
    """

    ADD = "Add Job"
    ASSIGN = "Assign"
    PURGE = "Purge Completed Jobs"

    def __init__(self):
        """
        Make sure the user is authorized to manage the translation queue.
        """

        cdrcgi.Control.__init__(self, "Translation Job Queue")
        self.conn = db.connect()
        self.cursor = self.conn.cursor()
        if not self.session:
            cdrcgi.bail("not authorized")
        if not cdr.canDo(self.session, "MANAGE TRANSLATION QUEUE"):
            cdrcgi.bail("not authorized")
        self.message = None
        self.translators = self.fetch_translators()

    def run(self):
        """
        Override the base class method, as we support extra buttons/tasks.
        """

        if self.request == self.ADD:
            cdrcgi.navigateTo("glossary-translation-job.py", self.session)
        elif self.request == self.PURGE:
            if not cdr.canDo(self.session, "PRUNE TRANSLATION QUEUE"):
                cdrcgi.bail("not authorized")
            self.cursor.execute("""\
DELETE FROM glossary_translation_job
      WHERE state_id = (SELECT value_id
                          FROM glossary_translation_state
                         WHERE value_name = 'Translation Made Publishable')
""")
            count = self.cursor.rowcount
            self.conn.commit()
            message = "Purged jobs for {:d} published translations."
            self.message = message.format(count)
        elif self.request == self.ASSIGN:
            assign_to = self.fields.getvalue("assign_to")
            if not assign_to:
                cdrcgi.bail("No translator selected")
            try:
                assign_to = int(assign_to)
            except:
                cdrcgi.bail(cdrcgi.TAMPERING)
            if assign_to not in [row.id for row in self.translators]:
                cdrcgi.bail(cdrcgi.TAMPERING)
            count = 0
            fields = "state_id", "comments", "assigned_to"
            history_fields = fields + ("doc_id", "state_date")
            placeholders = ", ".join(["?"] * len(history_fields))
            table = "glossary_translation_job_history"
            args = table, ", ".join(history_fields), placeholders
            insert = "INSERT INTO {} ({}) VALUES ({})".format(*args)
            table = "glossary_translation_job"
            args = table, "assigned_to = ?, state_date = ?", "doc_id"
            update = "UPDATE {} SET {} WHERE {} = ?".format(*args)
            for job in self.fields.getlist("assignments"):
                query = db.Query("glossary_translation_job", *fields)
                query.where(query.Condition("doc_id", job))
                row = query.execute(self.cursor).fetchone()
                if not row:
                    cdrcgi.bail(cdrcgi.TAMPERING)
                if row.assigned_to == assign_to:
                    continue
                params = [getattr(row, name) for name in fields[:-1]]
                params.append(assign_to)
                params.append(job)
                params.append(self.started)
                self.cursor.execute(insert, params)
                params = assign_to, self.started, job
                self.cursor.execute(update, params)
                self.conn.commit()
                count += 1
            self.message = "Re-assigned {:d} jobs".format(count)
        cdrcgi.Control.run(self)

    def set_form_options(self, opts):
        """
        Add our custom buttons for the extra tasks.
        """

        opts["buttons"][0] = self.PURGE
        opts["buttons"].insert(0, self.ASSIGN)
        opts["buttons"].insert(0, self.ADD)
        return opts

    def fetch_translators(self):
        """
        Get the list of users who can translate Glossary documents
        """

        query = db.Query("usr u", "u.id", "u.fullname")
        query.join("grp_usr x", "x.usr = u.id")
        query.join("grp g", "g.id = x.grp")
        query.where("u.expired IS NULL")
        query.where("g.name = 'Spanish Glossary Translators'")
        query.order("u.fullname")
        return query.execute(self.cursor).fetchall()

    def populate_form(self, form):
        """
        Instead of form fields, we're actually displaying a table
        containing one row for each job in the queue, sorted by
        job state, with a sub-sort on user name and date of last
        state transition.

        Change in requirements: the queue must support re-assigning
        jobs in bulk.
        """

        if self.message:
            form.add(form.B.P(self.message,
                              style="color: green; font-weight: bold"))
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Assign To"))
        for row in self.translators:
            form.add_radio("assign_to", row.fullname, str(row.id))
        form.add("</fieldset>")
        fields = ("j.doc_id", "s.value_name", "u.fullname", "j.state_date",
                  "j.comments")
        query = db.Query("glossary_translation_job j", *fields)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.doc_id")
        query.join("glossary_translation_state s", "s.value_id = j.state_id")
        query.order("j.state_date", "s.value_pos", "u.fullname")
        rows = query.execute(self.cursor).fetchall()
        jobs = [Job(self, row) for row in rows]
        body = form.B.TBODY()
        for job in jobs:
            body.append(job.tr())
        table = form.B.TABLE(
            form.B.CLASS("report"),
            form.B.THEAD(
                form.B.TR(
                    form.B.TH("SELECT JOB"),
                    form.B.TH("DOC ID"),
                    form.B.TH("DOC TYPE"),
                    form.B.TH("DOC TITLE"),
                    form.B.TH("STATUS"),
                    form.B.TH("STATUS DATE"),
                    form.B.TH("ASSIGNED TO"),
                    form.B.TH("COMMENT")
                )
            ),
            body,
        )
        form.add(table, False)

class Job:
    """
    Holds the information for a single CDR glossary translation job.
    """

    URL = "glossary-translation-job.py?Session={}&doc_id={}"

    def __init__(self, control, row):
        """
        Store the information pulled from the database tables.

        Pass:
          reference to control object
          row object from database query result set
        """

        self.control = control
        self.doc_id = row.doc_id
        self.state = row.value_name
        self.user = row.fullname
        self.date = row.state_date
        self.comments = row.comments

    @property
    def doc_type(self):
        if not hasattr(self, "_doc_type"):
            query = db.Query("doc_type t", "t.name")
            query.join("document d", "d.doc_type = t.id")
            query.where(query.Condition("d.id", self.doc_id))
            row = query.execute(self.control.cursor).fetchone()
            self._doc_type = row.name if row else None
        return self._doc_type

    @property
    def title(self):
        if not hasattr(self, "_title"):
            if not self.doc_type:
                self._title = None
            elif self.doc_type.lower() == "glossarytermname":
                query = db.Query("document", "title")
                query.where(query.Condition("id", self.doc_id))
                row = query.execute(self.control.cursor).fetchone()
                self._title = row.title if row else None
            else:
                path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
                query = db.Query("document d", "d.title")#.limit(1)
                query.join("query_term q", "q.doc_id = d.id")
                query.where(query.Condition("q.path", path))
                query.where(query.Condition("q.int_val", self.doc_id))
                query.order("d.title")
                rows = query.execute(self.control.cursor).fetchall()
                if rows:
                    titles = [row.title.split(";")[0] for row in rows]
                    #title = row.title.split(";")[0]
                    pattern = u"GTC for {}"
                    #self._title = pattern.format(title)
                    self._title = pattern.format(u"; ".join(titles))
                else:
                    pattern = u"GTC CDR{:d}"
                    self._title = pattern.format(self.doc_id)
        return self._title

    def tr(self):
        """
        Create a row for the job queue table, showing information about
        this individual translation job.
        """

        B = cdrcgi.Page.B
        url = self.URL.format(self.control.session, self.doc_id)
        label = "CDR{:d}".format(self.doc_id)
        link = B.A(label, href=url, title="edit job")
        comments = self.comments or ""
        if len(comments) > 40:
            comments = comments[:40] + "..."
        checkbox = B.INPUT(
            id=str(self.doc_id),
            type="checkbox",
            name="assignments",
            value=str(self.doc_id)
        )
        dt = "GTN" if self.doc_type.lower() == "glossarytermname" else "GTC"
        return B.TR(
            B.TD(checkbox, B.CLASS("center")),
            B.TD(link),
            B.TD(dt),
            B.TD(self.title),
            B.TD(self.state),
            B.TD(str(self.date)[:10], B.CLASS("nowrap")),
            B.TD(self.user),
            B.TD(comments)
        )

if __name__ == "__main__":
    """
    Make it possible to load this script as a module.
    """

    Control().run()
