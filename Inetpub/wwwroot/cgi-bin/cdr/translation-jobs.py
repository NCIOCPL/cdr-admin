#!/usr/bin/env python

"""Display CDR summary translation job queue.

Logic for collecting and displaying the active CDR summary translation
jobs, including links to the editing page for modifying individual
jobs, as well as a button for creating a new job, and a button for
clearing out jobs which have run the complete processing course.
"""

from cdrcgi import Controller, navigateTo


class Control(Controller):
    """Access to the database and report generation tools."""

    SUBTITLE = "Translation Job Queue"
    ADD = "Add"
    PURGE = "Purge"
    GLOSSARY = "Glossary"
    MEDIA = "Media"
    REPORTS_MENU = SUBMENU = "Reports"
    ADMINMENU = "Admin"
    FIELDS = (
        "d.id",
        "d.title",
        "s.value_name AS state",
        "c.value_name AS change",
        'u.fullname AS "user"',
        "j.state_date",
        "j.comments"
    )

    def run(self):
        """Override base class method, as we support extra buttons/tasks."""

        if self.request == self.ADD:
            navigateTo("translation-job.py", self.session.name)
        elif self.request == self.GLOSSARY:
            navigateTo("glossary-translation-jobs.py", self.session.name)
        elif self.request == self.MEDIA:
            navigateTo("media-translation-jobs.py", self.session.name)
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
            self.message = f"Purged jobs for {count:d} published translations."
        Controller.run(self)

    def populate_form(self, page):
        """Override to replace the standard form with a table of jobs.

        Instead of form fields, we're actually displaying a table
        containing one row for each job in the queue, sorted by
        job state, with a sub-sort on user name and date of last
        state transition.

        Pass:
            page - HTMLPage object on which we place the table
        """

        if not self.session.can_do("MANAGE TRANSLATION QUEUE"):
            self.bail("not authorized")
        if self.message:
            para = page.B.P(self.message, page.B.CLASS("strong info center"))
            page.body.append(para)
        query = self.Query("summary_translation_job j", *self.FIELDS)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.english_id")
        query.join("summary_translation_state s", "s.value_id = j.state_id")
        query.join("summary_change_type c", "c.value_id = j.change_type")
        query.order("s.value_pos", "u.fullname", "j.state_date")
        rows = query.execute(self.cursor).fetchall()
        table = page.B.TABLE(
            page.B.CLASS("report"),
            page.B.THEAD(
                page.B.TR(
                    page.B.TH("CDR ID"),
                    page.B.TH("Title"),
                    page.B.TH("Audience"),
                    page.B.TH("Status"),
                    page.B.TH("Assigned To"),
                    page.B.TH("Date"),
                    page.B.TH("Type of Change"),
                    page.B.TH("Comments")
                )
            ),
            page.B.TBODY(*[Job(self, row).row for row in rows]),
        )
        page.body.append(table)
        page.add_css(
            "th, td {"
            "    background-color: #e8e8e8; border-color: #bbb;"
            "}")

    @property
    def buttons(self):
        """Add our custom buttons for the extra tasks."""

        return (
            self.ADD,
            self.PURGE,
            self.GLOSSARY,
            self.MEDIA,
            self.REPORTS_MENU,
            self.ADMINMENU,
            self.LOG_OUT,
        )

    @property
    def message(self):
        """Optional string to be displayed prominently above the jobs table."""

        if hasattr(self, "_message"):
            return self._message

    @message.setter
    def message(self, value):
        """This is how the purge action reports its activity."""
        self._message = value


class Job:
    """Information for a single CDR summary translation job."""

    SCRIPT = "translation-job.py"

    def __init__(self, control, row):
        """Store the caller's values.

        Pass:
            control - access to page-building tools and the current session
            row - results set row from the database query
        """

        self.__control = control
        self.__row = row

    @property
    def audience(self):
        """Audience for the summary document."""
        return self.__row.title.split(";")[-1]

    @property
    def comments(self):
        """Possibly truncated comments for the last column in the row."""

        comments = (self.__row.comments or "")[:40]
        if self.__row.comments and len(self.__row.comments) > 40:
            comments = f"{comments} ..."
        return comments

    @property
    def date(self):
        """State date for the job."""
        return str(self.__row.state_date)[:10]

    @property
    def link(self):
        """Link to the job from its ID column."""

        url = self.__control.make_url(self.SCRIPT, english_id=self.__row.id)
        opts = dict(href=url, title="edit job")
        return self.__control.HTMLPage.B.A(f"CDR{self.__row.id:d}", **opts)

    @property
    def row(self):
        """Values for the job table."""

        B = self.__control.HTMLPage.B
        return B.TR(
            B.TD(self.link),
            B.TD(self.title),
            B.TD(self.audience),
            B.TD(self.__row.state),
            B.TD(self.__row.user),
            B.TD(self.date, B.CLASS("nowrap")),
            B.TD(self.__row.change),
            B.TD(self.comments)
        )

    @property
    def title(self):
        """Title of the summary document."""
        return self.__row.title.split(";")[0]


if __name__ == "__main__":
    """Make it possible to load this script as a module."""
    Control().run()
