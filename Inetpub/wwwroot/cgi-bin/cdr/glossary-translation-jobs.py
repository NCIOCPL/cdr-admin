#!/usr/bin/env python

"""Display CDR glossary translation job queue.

https://tracker.nci.nih.gov/browse/OCECDR-4489
"""

from functools import cached_property
from cdrcgi import Controller


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
    COLUMNS = (
        "\u2713",
        "Doc ID",
        "Doc Type",
        "Doc Title",
        "Status",
        "Status Date",
        "Assigned To",
        "Comment",
    )

    def show_form(self):
        """Overridden because the form needs a very wide table."""

        class Page(self.HTMLPage):
            """Derived class so we can override the layout of main."""

            @cached_property
            def main(self):
                """Move the form outside the grid container so it's wider."""

                return self.B.E(
                    "main",
                    self.B.DIV(
                        self.B.H1("Glossary Translation Job Queue"),
                        self.B.CLASS("grid-container")
                    ),
                    self.form,
                    self.B.CLASS("usa-section")
                )

        opts = dict(
            control=self,
            action=self.script,
            session=self.session,
            method=self.method,
        )
        page = Page(self.title, **opts)
        container = page.B.DIV(page.B.CLASS("grid-container"))
        fieldset = page.fieldset("Assign To")
        for row in self.translators:
            opts = dict(value=row.id, label=row.fullname)
            fieldset.append(page.radio_button("assign_to", **opts))
        container.append(fieldset)
        for label in self.buttons:
            container.append(page.button(label, onclick=self.SAME_WINDOW))
        for alert in self.alerts:
            message = alert["message"]
            del alert["message"]
            page.add_alert(message, **alert)
        page.form.append(container)
        page.form.append(self.table.node)
        page.add_css("""\
form { width: 90%; margin: 0 auto; }
.usa-table { margin-top: 3rem; }
.usa-table caption { font-size: 1.3rem; text-align: center; }
.usa-table th:first-child { text-align: center; }
.clickable.usa-checkbox__label {  margin-top: -.25rem; margin-left: .75rem; }
""")
        page.send()

    def run(self):
        """Override base class method, as we support extra buttons/tasks."""

        if not self.session.can_do("MANAGE TRANSLATION QUEUE"):
            self.bail("not authorized")
        if self.request == self.ADD:
            self.redirect("glossary-translation-job.py")
        elif self.request == self.SUMMARY:
            self.redirect("translation-jobs.py")
        elif self.request == self.MEDIA:
            self.redirect("media-translation-jobs.py")
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
            message = f"Purged jobs for {count:d} published translations."
            self.alerts.append(dict(message=message, type="success"))
            return self.show_form()
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
            message = f"Re-assigned {count:d} jobs."
            self.alerts.append(dict(message=message, type="success"))
            return self.show_form()
        Controller.run(self)

    @cached_property
    def alerts(self):
        """Messages to be displayed at the top of the page."""

        alerts = []
        if self.message:
            alerts.append(dict(message=self.message, type="success"))
        if self.warning:
            alerts.append(dict(message=self.warning, type="warning"))
        return alerts

    @cached_property
    def assignee(self):
        """New translator for a job."""

        assignee = self.fields.getvalue("assign_to")
        if not assignee:
            self.bail("No translator selected")
        try:
            assignee = int(assignee)
        except Exception:
            self.bail()
        if assignee not in [row.id for row in self.translators]:
            self.bail()
        return assignee

    @cached_property
    def buttons(self):
        """This form uses custom buttons."""
        return self.ASSIGN, self.ADD, self.PURGE, self.MEDIA, self.SUMMARY

    @cached_property
    def message(self):
        """Information about successfully performed action just taken."""
        return self.fields.getvalue("message")

    @cached_property
    def rows(self):
        """Rows for the table of queued jobs."""

        fields = (
            "j.doc_id",
            "s.value_name",
            "u.fullname",
            "j.state_date",
            "j.comments",
        )
        query = self.Query("glossary_translation_job j", *fields)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.doc_id")
        query.join("glossary_translation_state s", "s.value_id = j.state_id")
        query.order("j.state_date", "s.value_pos", "u.fullname")
        rows = query.execute(self.cursor).fetchall()
        return [Job(self, row).row for row in rows]

    @cached_property
    def same_window(self):
        """Don't open any more new browser tabs."""
        return self.buttons

    @cached_property
    def table(self):
        """Table of queued glossary translation jobs."""

        opts = dict(cols=self.COLUMNS, caption="Jobs")
        return self.Reporter.Table(self.rows, **opts)

    @cached_property
    def translators(self):
        """Get the list of users who can translate Glossary documents."""

        query = self.Query("usr u", "u.id", "u.fullname")
        query.join("grp_usr x", "x.usr = u.id")
        query.join("grp g", "g.id = x.grp")
        query.where("u.expired IS NULL")
        query.where("g.name = 'Spanish Glossary Translators'")
        query.order("u.fullname")
        return query.execute(self.cursor).fetchall()

    @cached_property
    def warning(self):
        """Warning message passed on from the form page."""
        return self.fields.getvalue("warning")


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

    @cached_property
    def comments(self):
        """Notes on the translation job."""

        comments = self.__row.comments or ""
        return comments[:40] + "..." if len(comments) > 40 else comments

    @cached_property
    def date(self):
        """Date when the current job state was assigned."""
        return str(self.__row.state_date)[:10]

    @property
    def doc_id(self):
        """CDR ID of the glossary document being translated."""
        return self.__row.doc_id

    @cached_property
    def doc_type(self):
        """Use the abbreviations GTN and GTC for name and concept documents."""

        query = self.__control.Query("doc_type t", "t.name")
        query.join("document d", "d.doc_type = t.id")
        query.where(query.Condition("d.id", self.doc_id))
        row = query.execute(self.__control.cursor).fetchone()
        if not row or not row.name.startswith("GlossaryTerm"):
            self.__control.bail(f"CDR{self.doc_id} is not a glossary doc")
        return "GTN" if "Name" in row.name else "GTC"

    @cached_property
    def row(self):
        """
        Create a row for the job queue table, showing information about
        this individual translation job.
        """

        Page = self.__control.HTMLPage
        Cell = self.__control.Reporter.Cell
        doc_id = str(self.doc_id)
        url = self.URL.format(self.__control.session, doc_id)
        opts = dict(widget_id=doc_id, value=doc_id, label="\u00a0")
        checkbox = Page.checkbox("assignments", **opts)
        return (
            Cell(checkbox, center=True),
            Cell(f"CDR{doc_id}", href=url, title="edit job"),
            self.doc_type,
            self.title,
            self.state,
            Cell(self.date, classes="nowrap"),
            self.user,
            self.comments,
        )

    @property
    def state(self):
        """Which state is the translation job in?"""
        return self.__row.value_name

    @cached_property
    def title(self):
        """Come up with a reasonable doc title (tricky for concept docs)."""

        if self.doc_type == "GTN":
            query = self.__control.Query("document", "title")
            query.where(query.Condition("id", self.doc_id))
            row = query.execute(self.__control.cursor).fetchone()
            return row.title if row else None
        path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
        query = self.__control.Query("document d", "d.title")
        query.join("query_term q", "q.doc_id = d.id")
        query.where(query.Condition("q.path", path))
        query.where(query.Condition("q.int_val", self.doc_id))
        query.order("d.title")
        rows = query.execute(self.__control.cursor).fetchall() or []
        titles = [row.title.split(";")[0].strip() for row in rows]
        pattern = "GTC for {}"
        return pattern.format("; ".join(titles))

    @property
    def user(self):
        """Full name of the translator assigned to this job."""
        return self.__row.fullname


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
