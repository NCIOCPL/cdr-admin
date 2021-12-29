#!/usr/bin/env python

"""Display CDR glossary translation job queue.

https://tracker.nci.nih.gov/browse/OCECDR-4489
"""

from cdrcgi import Controller, navigateTo


class Control(Controller):
    """
    Logic for collecting and displaying the active CDR glossary
    translation jobs, including links to the editing page for
    modifying individual jobs, as well as a button for creating
    a new job, a button for clearing out jobs which have run
    the complete processing course, and a button for reassigning
    jobs in bulk.
    """

    SUBTITLE = "Glossary Translation Job Queue"
    ADD = "Add"
    ASSIGN = "Assign"
    PURGE = "Purge"
    SUMMARY = "Summary"
    MEDIA = "Media"
    REPORTS_MENU = SUBMENU = "Reports"
    ADMINMENU = "Admin"
    CSS = "th, td { background-color: #e8e8e8; border-color: #bbb; }"

    def populate_form(self, page):
        """Override to replace the standard form with a table of jobs.

        Instead of form fields, we're actually displaying a table
        containing one row for each job in the queue, sorted by
        job state, with a sub-sort on user name and date of last
        state transition.

        Change in requirements: the queue must now support re-assigning
        jobs in bulk.

        Pass:
            page - HTMLPage object on which we place the table
        """

        if self.message:
            para = page.B.P(self.message, page.B.CLASS("strong info center"))
            page.form.append(para)
        fieldset = page.fieldset("Assign To")
        for row in self.translators:
            opts = dict(value=row.id, label=row.fullname)
            fieldset.append(page.radio_button("assign_to", **opts))
        page.form.append(fieldset)
        fields = ("j.doc_id", "s.value_name", "u.fullname", "j.state_date",
                  "j.comments")
        query = self.Query("glossary_translation_job j", *fields)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.doc_id")
        query.join("glossary_translation_state s", "s.value_id = j.state_id")
        query.order("j.state_date", "s.value_pos", "u.fullname")
        rows = query.execute(self.cursor).fetchall()
        table = page.B.TABLE(
            page.B.THEAD(
                page.B.TR(
                    page.B.TH("SELECT JOB"),
                    page.B.TH("DOC ID"),
                    page.B.TH("DOC TYPE"),
                    page.B.TH("DOC TITLE"),
                    page.B.TH("STATUS"),
                    page.B.TH("STATUS DATE"),
                    page.B.TH("ASSIGNED TO"),
                    page.B.TH("COMMENT"),
                )
            ),
            page.B.TBODY(*[Job(self, row).row for row in rows]),
        )
        page.form.append(table)
        page.add_css(self.CSS)

    def run(self):
        """Override base class method, as we support extra buttons/tasks."""

        if not self.session.can_do("MANAGE TRANSLATION QUEUE"):
            self.bail("not authorized")
        if self.request == self.ADD:
            navigateTo("glossary-translation-job.py", self.session.name)
        elif self.request == self.SUMMARY:
            navigateTo("translation-jobs.py", self.session.name)
        elif self.request == self.MEDIA:
            navigateTo("media-translation-jobs.py", self.session.name)
        elif self.request == self.PURGE:
            if not self.session.can_do("PRUNE TRANSLATION QUEUE"):
                self.bail("not authorized")
            self.cursor.execute(
                "DELETE FROM glossary_translation_job"
                "      WHERE state_id = ("
                "     SELECT value_id"
                "       FROM glossary_translation_state"
                "      WHERE value_name = 'Translation Made Publishable')"
            )
            count = self.cursor.rowcount
            self.conn.commit()
            self.message = f"Purged jobs for {count:d} published translations."
        elif self.request == self.ASSIGN:
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
                query = self.Query("glossary_translation_job", *fields)
                query.where(query.Condition("doc_id", job))
                row = query.execute(self.cursor).fetchone()
                if not row:
                    self.bail()
                if row.assigned_to == self.assignee:
                    continue
                params = [getattr(row, name) for name in fields[:-1]]
                params.append(self.assignee)
                params.append(job)
                params.append(self.started)
                self.cursor.execute(insert, params)
                params = self.assignee, self.started, job
                self.cursor.execute(update, params)
                self.conn.commit()
                count += 1
            self.message = f"Re-assigned {count:d} jobs"
        Controller.run(self)

    @property
    def assignee(self):
        """New translator for a job."""

        if not hasattr(self, "_assignee"):
            assignee = self.fields.getvalue("assign_to")
            if not assignee:
                self.bail("No translator selected")
            try:
                self._assignee = int(assignee)
            except Exception:
                self.bail()
            if self._assignee not in [row.id for row in self.translators]:
                self.bail()
        return self._assignee

    @property
    def buttons(self):
        """Add our custom buttons for the extra tasks."""

        return (
            self.ADD,
            self.ASSIGN,
            self.PURGE,
            self.MEDIA,
            self.SUMMARY,
            self.REPORTS_MENU,
            self.ADMINMENU,
            self.LOG_OUT,
        )

    @property
    def message(self):
        """Optional string, displayed prominently above the jobs table."""

        if hasattr(self, "_message"):
            return self._message

    @message.setter
    def message(self, value):
        """This is how the purge action reports its activity."""
        self._message = value

    @property
    def translators(self):
        """Get the list of users who can translate Glossary documents."""

        if not hasattr(self, "_translators"):
            query = self.Query("usr u", "u.id", "u.fullname")
            query.join("grp_usr x", "x.usr = u.id")
            query.join("grp g", "g.id = x.grp")
            query.where("u.expired IS NULL")
            query.where("g.name = 'Spanish Glossary Translators'")
            query.order("u.fullname")
            self._translators = query.execute(self.cursor).fetchall()
        return self._translators


class Job:
    """Holds the information for a single CDR glossary translation job."""

    URL = "glossary-translation-job.py?Session={}&doc_id={}"

    def __init__(self, control, row):
        """Remeber the caller's values.

        Pass:
            control - access to page-building tools and the current session
            row - results set row from the database query
        """

        self.__control = control
        self.__row = row

    @property
    def comments(self):
        """Notes on the translation job."""

        if not hasattr(self, "_comments"):
            self._comments = self.__row.comments or ""
            if len(self._comments) > 40:
                self._comments = self._comments[:40] + "..."
        return self._comments

    @property
    def date(self):
        """Date when the current job state was assigned."""
        return str(self.__row.state_date)[:10]

    @property
    def doc_id(self):
        """CDR ID of the glossary document being translated."""
        return self.__row.doc_id

    @property
    def doc_type(self):
        """Use the abbreviations GTN and GTC for name and concept documents."""

        if not hasattr(self, "_doc_type"):
            query = self.__control.Query("doc_type t", "t.name")
            query.join("document d", "d.doc_type = t.id")
            query.where(query.Condition("d.id", self.doc_id))
            row = query.execute(self.__control.cursor).fetchone()
            if not row or not row.name.startswith("GlossaryTerm"):
                self.__control.bail(f"CDR{self.doc_id} is not a glossary doc")
            self._doc_type = "GTN" if "Name" in row.name else "GTC"
        return self._doc_type

    @property
    def row(self):
        """
        Create a row for the job queue table, showing information about
        this individual translation job.
        """

        B = self.__control.HTMLPage.B
        url = self.URL.format(self.__control.session, self.doc_id)
        link = B.A(f"CDR{self.doc_id:d}", href=url, title="edit job")
        checkbox = B.INPUT(
            id=str(self.doc_id),
            type="checkbox",
            name="assignments",
            value=str(self.doc_id)
        )
        return B.TR(
            B.TD(checkbox, B.CLASS("center")),
            B.TD(link),
            B.TD(self.doc_type),
            B.TD(self.title),
            B.TD(self.state),
            B.TD(self.date, B.CLASS("nowrap")),
            B.TD(self.user),
            B.TD(self.comments)
        )

    @property
    def state(self):
        """Which state is the translation job in?"""
        return self.__row.value_name

    @property
    def title(self):
        """Come up with a reasonable doc title (tricky for concept docs)."""

        if not hasattr(self, "_title"):
            if self.doc_type == "GTN":
                query = self.__control.Query("document", "title")
                query.where(query.Condition("id", self.doc_id))
                row = query.execute(self.__control.cursor).fetchone()
                self._title = row.title if row else None
            else:
                path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
                query = self.__control.Query("document d", "d.title")
                query.join("query_term q", "q.doc_id = d.id")
                query.join("glossary_translation_job j", "j.doc_id = d.id")
                query.where(query.Condition("q.path", path))
                query.where(query.Condition("q.int_val", self.doc_id))
                query.order("d.title")
                rows = query.execute(self.__control.cursor).fetchall() or []
                titles = [row.title.split(";")[0].strip() for row in rows]
                pattern = "GTC for {}"
                self._title = pattern.format("; ".join(titles))
        return self._title

    @property
    def user(self):
        """Full name of the translator assigned to this job."""
        return self.__row.fullname


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
