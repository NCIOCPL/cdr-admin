#!/usr/bin/env python

"""Display CDR summary translation job queue.

Logic for collecting and displaying the active CDR summary translation
jobs, including links to the editing page for modifying individual
jobs, as well as a button for creating a new job, and a button for
clearing out jobs which have run the complete processing course.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report generation tools."""

    SUBTITLE = "Translation Job Queue"
    ADD = "Add"
    PURGE = "Purge"
    GLOSSARY = "Glossary"
    MEDIA = "Media"
    COLUMNS = (
        "CDR ID",
        "Title",
        "Audience",
        "Status",
        "Assigned To",
        "Date",
        "Type of Change",
        "Comments",
    )
    FIELDS = (
        "d.id",
        "d.title",
        "s.value_name AS state",
        "c.value_name AS change",
        'u.fullname AS "user"',
        "j.state_date",
        "j.comments",
        "q.value AS svpc",
    )

    def run(self):
        """Override base class method, as we support extra buttons/tasks."""

        if not self.session.can_do("MANAGE TRANSLATION QUEUE"):
            self.bail("not authorized")
        if self.request == self.ADD:
            params = dict(testing=True) if self.testing else {}
            self.redirect("translation-job.py", **params)
        elif self.request == self.GLOSSARY:
            self.redirect("glossary-translation-jobs.py")
        elif self.request == self.MEDIA:
            self.redirect("media-translation-jobs.py")
        if self.request == self.PURGE:
            if not self.session.can_do("PRUNE TRANSLATION QUEUE"):
                self.bail("not authorized")
            self.cursor.execute(
                "DELETE FROM summary_translation_job"
                "      WHERE state_id = ("
                "     SELECT value_id"
                "       FROM summary_translation_state"
                "      WHERE value_name = 'Translation Made Publishable')"
            )
            count = self.cursor.rowcount
            self.conn.commit()
            message = f"Purged jobs for {count:d} published translations."
            self.alerts.append(dict(message=message, type="success"))
            return self.show_form()
        Controller.run(self)

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
                        self.B.H1("Summary Translation Job Queue"),
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
        for label in self.buttons:
            container.append(page.button(label, onclick=self.SAME_WINDOW))
        for alert in self.alerts:
            message = alert["message"]
            del alert["message"]
            page.add_alert(message, **alert)
        page.form.append(container)
        page.form.append(self.table.node)
        if self.testing:
            page.form.append(page.hidden_field("testing", "True"))
        page.add_css("""\
form { width: 90%; margin: 0 auto; }
.usa-table { margin-top: 3rem; }
.usa-table caption { font-size: 1.3rem; text-align: center; }
.usa-table th:first-child { text-align: center; }
.clickable.usa-checkbox__label {  margin-top: -.25rem; margin-left: .75rem; }
td.svpc, td.svpc a, td.svpc a:visited { color: green; }
""")
        page.send()

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
    def buttons(self):
        """Add our custom buttons for the extra tasks."""
        return self.ADD, self.PURGE, self.GLOSSARY, self.MEDIA

    @cached_property
    def message(self):
        """Information about successfully performed action just taken."""
        return self.fields.getvalue("message")

    @cached_property
    def rows(self):
        """Rows for the table of queued jobs."""

        query = self.Query("summary_translation_job j", *self.FIELDS)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.english_id")
        query.join("summary_translation_state s", "s.value_id = j.state_id")
        query.join("summary_change_type c", "c.value_id = j.change_type")
        query.outer("query_term q",
                    "q.doc_id = d.id AND q.path = '/Summary/@SVPC'")
        query.order("q.value DESC", "s.value_pos", "u.fullname",
                    "j.state_date")
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
    def testing(self):
        """Used by automated tests to avoid spamming the users."""
        return self.fields.getvalue("testing")

    @cached_property
    def warning(self):
        """Warning message passed on from the form page."""
        return self.fields.getvalue("warning")


class Job:
    """Information for a single CDR summary translation job."""

    SCRIPT = "translation-job.py"
    URL = "translation-job.py?Session={}&english_id={}"

    def __init__(self, control, row):
        """Store the caller's values.

        Pass:
            control - access to page-building tools and the current session
            row - results set row from the database query
        """

        self.__control = control
        self.__row = row

    @cached_property
    def audience(self):
        """Audience for the summary document."""
        return self.__row.title.split(";")[-1]

    @cached_property
    def comments(self):
        """Possibly truncated comments for the last column in the row."""

        comments = (self.__row.comments or "")[:40]
        if self.__row.comments and len(self.__row.comments) > 40:
            comments = f"{comments} ..."
        return comments

    @cached_property
    def date(self):
        """State date for the job."""
        return str(self.__row.state_date)[:10]

    @cached_property
    def link(self):
        """Link to the job from its ID column."""

        url = self.__control.make_url(self.SCRIPT, english_id=self.__row.id)
        opts = dict(href=url, title="edit job")
        return self.__control.HTMLPage.B.A(f"CDR{self.__row.id:d}", **opts)

    @cached_property
    def row(self):
        """Values for the job table."""

        Cell = self.__control.Reporter.Cell
        doc_id = str(self.__row.id)
        url = self.URL.format(self.__control.session, doc_id)
        if self.__control.testing:
            url += "&testing=True"
        classes = "svpc" if self.__row.svpc else "pdq"
        return (
            Cell(f"CDR{doc_id}", href=url, title="edit job", classes=classes),
            Cell(self.title, classes=classes),
            Cell(self.audience, classes=classes),
            Cell(self.__row.state, classes=classes),
            Cell(self.__row.user, classes=classes),
            Cell(self.date, classes=f"{classes} nowrap"),
            Cell(self.__row.change, classes=classes),
            Cell(self.comments, classes=classes),
        )

    @cached_property
    def title(self):
        """Title of the summary document."""
        return self.__row.title.split(";")[0]


if __name__ == "__main__":
    """Make it possible to load this script as a module."""
    Control().run()
