#!/usr/bin/env python

"""Edit a summary translation job.

JIRA::OCECDR-4193 - create translation job editor
JIRA::OCECDR-4248 - allow the user to attach a file
JIRA::OCECDR-4504 - make the status date field read-only
JIRA::OCECDR-4664 - automatically update status date
"""

from datetime import date
from operator import itemgetter
from lxml import etree
from cdr import EmailMessage, EmailAttachment, isProdHost, getEmailList
from cdrcgi import Controller, navigateTo
from cdrapi import db


class Control(Controller):
    """
    Logic for displaying an editing form for creating new translation
    jobs as well as modifying existing jobs. Sends an alert to the individual
    to whom the job is currently assigned (unless it's the same user
    who is editing or creating the job).
    """

    JOBS = "Jobs"
    DELETE = "Delete"
    LOGNAME = "translation-workflow"
    MEDIA = "Media"
    GLOSSARY = "Glossary"
    REPORTS_MENU = SUBMENU = "Reports"
    ADMINMENU = "Admin"
    SUBTITLE = "Translation Job"
    ACTION = "MANAGE TRANSLATION QUEUE"
    INSERT = "INSERT INTO {} ({}) VALUES ({})"
    UPDATE = "UPDATE {} SET {} WHERE {} = ?"

    def run(self):
        """
        Override the base class method to handle additional buttons.
        """

        if not self.session or not self.session.can_do(self.ACTION):
            self.bail("not authorized")
        if self.request == self.JOBS:
            navigateTo("translation-jobs.py", self.session.name)
        elif self.request == self.DELETE:
            self.delete_job()
        elif self.request == self.GLOSSARY:
            navigateTo("glossary-translation-jobs.py", self.session.name)
        elif self.request == self.MEDIA:
            navigateTo("media-translation-jobs.py", self.session.name)
        Controller.run(self)

    def show_report(self):
        """
        Override the base class because we're storing data, not
        creating a report. Modified to also populate the history
        table.
        """

        if self.have_required_values:
            if self.job.changed:
                conn = db.connect()
                cursor = conn.cursor()
                params = [getattr(self, name) for name in Job.FIELDS]
                params.append(getattr(self, Job.KEY))
                self.logger.info("storing translation job state %s", params)
                placeholders = ", ".join(["?"] * len(params))
                cols = ", ".join(Job.FIELDS + (Job.KEY,))
                strings = Job.HISTORY, cols, placeholders
                cursor.execute(self.INSERT.format(*strings), params)
                if self.job.new:
                    strings = (Job.TABLE, cols, placeholders)
                    query = self.INSERT.format(*strings)
                else:
                    cols = ", ".join([("%s = ?" % name) for name in Job.FIELDS])
                    strings = (Job.TABLE, cols, Job.KEY)
                    query = self.UPDATE.format(*strings)
                try:
                    cursor.execute(query, params)
                    conn.commit()
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        self.logger.error("duplicate translation job ID")
                        self.bail("attempt to create duplicate job")
                    else:
                        self.logger.error("database failure: %s", e)
                        self.bail(f"database failure: {e}")
                self.logger.info("translation job state stored successfully")
                job = Job(self)
                if self.alert_needed(job):
                    self.alert(job)
            navigateTo("translation-jobs.py", self.session.name)
        else:
            self.show_form()

    def populate_form(self, page):
        """
        Separate out logic for editing jobs versus picking a summary doc.

        Pass:
            page - object used to collect the form fields
        """

        if self.english_id:
            self.populate_editing_form(page)
        else:
            self.populate_summary_selection_form(page)

    def populate_editing_form(self, page):
        """
        We have an English summary; show the form for editing/creating its job.

        Pass:
            page - object used to collect the form fields
        """

        page.form.set("enctype", "multipart/form-data")
        if not self.job.new:
            page.add_script(f"""\
jQuery("input[value='{self.DELETE}']").click(function(e) {{
    if (confirm("Are you sure?"))
        return true;
    e.preventDefault();
}});""")
        else:
            page.add_script(f"""\
var submitted = false;
jQuery("input[value='{self.SUBMIT}']").click(function(e) {{
    if (!submitted) {{
        submitted = true;
        return true;
    }}
    e.preventDefault();
}});""")
        user = self.job.assigned_to
        users = self.translators
        if user:
            if user not in users:
                users[user] = self.users[user]
        elif self.lead_translators:
            user = self.sort_dict(self.lead_translators)[0][0]
        users = self.sort_dict(users)
        types = self.change_types.values
        states = self.states.values
        change_type = self.job.change_type or types[0][0]
        state_id = self.job.state_id or states[0][0]
        comments = (self.job.comments or "").replace("\r", "")
        action = "Create" if self.job.new else "Edit"
        legend = f"{action} Translation Job for CDR{self.english_id:d}"
        fieldset = page.fieldset(legend)
        opts = dict(options=types, default=change_type)
        fieldset.append(page.select("change_type", **opts))
        opts = dict(options=users, default=user)
        fieldset.append(page.select("assigned_to", **opts))
        opts = dict(options=states, default=state_id)
        fieldset.append(page.select("status", **opts))
        fieldset.append(page.textarea("comments", value=comments))
        opts = dict(label="QC Report(s)", multiple=True)
        fieldset.append(page.file_field("file", **opts))
        page.form.append(page.hidden_field("english_id", self.english_id))
        page.form.append(fieldset)

    def populate_summary_selection_form(self, page):
        """
        We don't have a summary to translate yet; let the user pick one.

        Pass:
            page - object used to collect the form fields
        """

        temp = self.sort_dict(self.english_summaries)
        query = db.Query(Job.TABLE, Job.KEY)
        rows = query.execute(self.cursor).fetchall()
        jobs = set([row[0] for row in rows])
        summaries = []
        for summary_id, summary_title in temp:
            if summary_id not in jobs:
                summaries.append((summary_id, summary_title))
        fieldset = page.fieldset("Select English Summary")
        opts = dict(label="Summary", options=summaries)
        fieldset.append(page.select("english_id", **opts))
        page.form.append(fieldset)

    def delete_job(self):
        """
        Drop the table row for a job (we already have confirmation from
        the user).
        """

        query = f"DELETE FROM {Job.TABLE} WHERE english_id = ?"
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(query, self.english_id)
        conn.commit()
        self.logger.info("removed translation job for CDR%d", self.english_id)
        navigateTo("translation-jobs.py", self.session.name)

    @property
    def assigned_to(self):
        """Translator to whom this translation task is currently assigned."""

        if not hasattr(self, "_assigned_to"):
            self._assigned_to = self.get_id("assigned_to", self.users)
        return self._assigned_to

    @property
    def banner(self):
        """Customize the display banner if we have a job."""
        return self.job.banner if self.job else self.title

    @property
    def buttons(self):
        """Customize the action buttons."""

        if not hasattr(self, "_buttons"):
            self._buttons = [self.SUBMIT, self.JOBS]
            if self.job and not self.job.new:
                self._buttons.append(self.DELETE)
            self._buttons.append(self.MEDIA)
            self._buttons.append(self.GLOSSARY)
            self._buttons.append(self.SUBMENU)
            self._buttons.append(self.ADMINMENU)
            self._buttons.append(self.LOG_OUT)
        return self._buttons

    @property
    def change_type(self):
        """Primary key for the change type for the English summary."""

        if not hasattr(self, "_change_type"):
            _type = self.get_id("change_type", self.change_types.map)
            self._change_type = _type
        return self._change_type

    @property
    def change_types(self):
        """Valid values for types of summary changes."""

        if not hasattr(self, "_change_types"):
            self._change_types = self.load_values("summary_change_type")
        return self._change_types

    @property
    def comments(self):
        """Notes on the translation job."""

        if not hasattr(self, "_comments"):
            comments = self.fields.getvalue("comments", "").strip()
            self._comments = comments if comments else None
        return self._comments

    @property
    def english_id(self):
        """CDR ID of English PDQ Summary being translated."""

        if not hasattr(self, "_english_id"):
            _id = self.get_id("english_id", self.english_summaries)
            self._english_id = _id
        return self._english_id

    @property
    def english_summaries(self):
        """Dictionary of titles of English PDQ summaries."""

        if not hasattr(self, "_english_summaries"):
            self._english_summaries = self.get_summaries("English")
        return self._english_summaries

    @property
    def files(self):
        """Attachments to be appended to email notification."""

        if not hasattr(self, "_files"):
            self._files = []
            if "file" in self.fields.keys():
                files = self.fields["file"]
                if not isinstance(files, list):
                    files = [files]
                for f in files:
                    if f.file:
                        file_bytes = []
                        while True:
                            more_bytes = f.file.read()
                            if not more_bytes:
                                break
                            file_bytes.append(more_bytes)
                        file_bytes = b"".join(file_bytes)
                    else:
                        file_bytes = f.value
                    if file_bytes:
                        self.logger.info("filename=%s", f.filename)
                        attachment = EmailAttachment(file_bytes, f.filename)
                        self._files.append(attachment)
                    else:
                        self.logger.warning("%s empty", f.filename)
        return self._files

    @property
    def have_required_values(self):
        """
        Determine whether we have values for all of the required job fields.
        """

        if not hasattr(self, "_have_required_values"):
            self._have_required_values = True
            for name in (Job.KEY,) + Job.FIELDS:
                if name != "comments" and not getattr(self, name):
                    self._have_required_values = False
                    return False
        return self._have_required_values

    @property
    def job(self):
        """Translation job being displayed/edited."""

        if not hasattr(self, "_job"):
            self._job = Job(self) if self.english_id else None
        return self._job

    @property
    def lead_translators(self):
        """Lead users for the PDQ Summary translation team."""

        if not hasattr(self, "_lead_translators"):
            group_name = "Spanish Translators Leads"
            self._lead_translators = self.load_group(group_name)
        return self._lead_translators

    @property
    def spanish_summaries(self):
        """Dictionary of titles of Spanish PDQ summaries."""

        if not hasattr(self, "_spanish_summaries"):
            self._spanish_summaries = self.get_summaries("Spanish")
        return self._spanish_summaries

    @property
    def state_id(self):
        """Primary key for the job's current translation state."""

        if not hasattr(self, "_state_id"):
            self._state_id = self.get_id("status", self.states.map)
        return self._state_id

    @property
    def state_date(self):
        """If we save or update a job, set its state to today."""

        if not hasattr(self, "_state_date"):
            if self.job and self.state_id == self.job.state_id:
                self._state_date = self.job.state_date
            else:
                self._state_date = date.today()
        return self._state_date

    @property
    def states(self):
        """Valid values for summary translation states."""

        if not hasattr(self, "_states"):
            self._states = self.load_values("summary_translation_state")
        return self._states

    @property
    def subtitle(self):
        """Customize the string below the main banner."""
        return self.job.banner if self.job else self.SUBTITLE

    @property
    def translators(self):
        """Users who are authorized to translate PDQ summaries."""

        if not hasattr(self, "_translators"):
            self._translators = self.load_group("Spanish Translators")
        return self._translators

    @property
    def user(self):
        """Instance of `UserInfo` class."""

        if not hasattr(self, "_user"):
            self._user = self.UserInfo(self)
        return self._user

    @property
    def users(self):
        """Dictionary of all active users.

        We need this for validating the assigned_to parameter. The set
        of currently active translators won't work for that purpose,
        because a job may have been assigned to a user who is no longer
        active, or who has been subsequently removed from the translators
        group.
        """

        if not hasattr(self, "_users"):
            query = db.Query("usr", "id", "fullname")
            query.where("fullname IS NOT NULL")
            rows = query.execute(self.cursor).fetchall()
            self._users = dict([(row[0], row[1]) for row in rows])
        return self._users

    def load_values(self, table_name):
        """
        Factor out logic for collecting a valid values set.

        This works because our tables for valid values both
        have the same structure.

        Returns a populated Values object.
        """

        query = db.Query(table_name, "value_id", "value_name")
        rows = query.order("value_pos").execute(self.cursor).fetchall()
        class Values:
            def __init__(self, rows):
                self.map = {}
                self.values = []
                for value_id, value_name in rows:
                    self.map[value_id] = value_name
                    self.values.append((value_id, value_name))
        return Values(rows)

    def get_id(self, name, valid_values):
        """
        Fetch and validate a parameter for a primary key in one
        of the valid values tables.

        Pass:
            name - name of the CGI parameter
            valid_values - dictionary of valid values indexed by primary keys

        Return:
            integer for a valid value primary key if parameter is present
            otherwise None

        Script exits with an error message if the parameters have been
        tampered with by a hacker.
        """

        value = self.fields.getvalue(name)
        if not value:
            return None
        try:
            int_id = int(value)
        except:
            self.bail(f"invalid {name} ({value!r})")
        if int_id not in valid_values:
            self.bail(f"invalid {name} ({value!r})")
        return int_id

    def get_summaries(self, language):
        """
        Fetch the IDs and titles for published CDR summary documents.

        OCECDR-4240: all modules to be queued for translation jobs.

        Pass:
            language - string representing language of summaries to
            be returned

        Return:
            dictionary of titles of summaries in the specified language
            indexed by the summary document IDs
        """

        query = db.Query("active_doc d", "d.id", "d.title")
        query.join("query_term l", "l.doc_id = d.id")
        query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("l.value", language))
        if language == "English":
            query.outer("pub_proc_cg c", "c.id = d.id")
            query.outer("query_term m", "m.doc_id = d.id",
                        "m.path = '/Summary/@ModuleOnly'")
            query.where("(c.id IS NOT NULL OR m.value = 'Yes')")
        query.unique()
        self.logger.debug("query: %s", query)
        return dict(query.execute(self.cursor).fetchall())

    def load_group(self, group):
        """
        Fetch the user ID and name for all members of a specified group.

        Pass:
            group - name of group to fetch

        Return:
            dictionary of user names indexed by user ID
        """

        query = db.Query("usr u", "u.id", "u.fullname")
        query.join("grp_usr gu", "gu.usr = u.id")
        query.join("grp g", "g.id = gu.grp")
        query.where("u.expired IS NULL")
        query.where(query.Condition("g.name", group))
        rows = query.execute(self.cursor).fetchall()
        return dict([(row[0], row[1]) for row in rows])

    def alert_needed(self, job):
        """
        Determine whether an email alert to the job's assignee is
        required. We only send such an alert if the assignee is
        different from the current user, and either the job's state
        or it's assignee has changed.

        Pass:
            job - Job object created after changes were saved (to
                  compared to the Job object created before that
                  point)

        Return:
            boolean reflecting the tests described above
        """

        if job.assigned_to == self.user.id:
            return False
        if self.job.state_id != job.state_id:
            return True
        if self.job.assigned_to != job.assigned_to:
            return True
        return False

    def alert(self, job):
        """
        Send an email alert to the user to whom the translation job
        is currently assigned.
        """

        recip = self.UserInfo(self, job.assigned_to)
        if not recip.email:
            error = f"no email address found for user {recip.name}"
            self.logger.error(error)
            self.bail(error)
        recips = [recip.email]
        sender = "cdr@cancer.gov"
        body = []
        subject = f"[{self.session.tier}] Translation Queue Notification"
        log_message = f"mailed translation job state alert to {recip}"
        if not isProdHost():
            recips = getEmailList("Test Translation Queue Recips")
            body.append(
                f"[*** THIS IS A TEST MESSAGE ON THE {self.session.tier} TIER."
                f" ON PRODUCTION IT WOULD HAVE GONE TO {recip}. ***]\n"
            )
            log_message = f"test alert for {recip} sent to {recips}"
        if self.job.new:
            body.append("A new translation job has been assigned to you.")
        else:
            body.append("A translation job assigned to you has a new status.")
        body.append(f"Assigned by: {self.user}")
        body.append(f"English summary document ID: CDR{job.english_id:d}")
        body.append(f"English summary title: {job.english_title}")
        if job.spanish_title:
            body.append(f"Spanish summary document ID: CDR{job.spanish_id:d}")
            body.append(f"Spanish summary title: {job.spanish_title}")
        body.append(f"Summary audience: {job.english_audience}")
        body.append(f"Job status: {self.states.map.get(job.state_id)}")
        body.append(f"Date of status transition: {job.state_date}")
        body.append(f"Comments: {job.comments}")
        opts = dict(subject=subject, body="\n".join(body))
        if self.files:
            opts["attachments"] = self.files
        try:
            message = EmailMessage(sender, recips, **opts)
            message.send()
        except Exception as e:
            self.logger.error("sending mail: %s", e)
            self.bail(f"sending mail: {e}")
        self.logger.info(log_message)

    @staticmethod
    def sort_dict(d):
        """
        Generate a sequence from a dictionary, with the elements in the
        sequence ordered by the dictionary element's value. The sequence
        contain tuples of (key, value) pairs pulled from the dictionary.
        """

        return sorted(d.items(), key=itemgetter(1))

    class UserInfo:
        """
        Stores user ID, name, and email address.

        Pass:
            control - reference to script's control object
            user_id - primary key for the usr table (optional)

        If no user_id is supplied, use the one for the session.
        """

        def __init__(self, control, user_id=None):
            """
            Look up the information for the specified user in the database.

            If no user ID is passed, use that of the user running this script.
            """

            if not user_id:
                query = db.Query("session", "usr")
                query.where(query.Condition("name", control.session.name))
                user_id = query.execute(control.cursor).fetchone()[0]
            self.id = user_id
            query = db.Query("open_usr", "email", "fullname")
            query.where(query.Condition("id", user_id))
            self.email, self.name = query.execute(control.cursor).fetchone()

        def __str__(self):
            """
            Create a display version of the user's information.
            """

            return f"{self.name} <{self.email}>"


class Job:
    """Translation job for an English PDQ Cancer Information Summary.

    Collects information about the English CDR summary document being
    translated, as well as about the corresponding translated Spanish
    document (if it exists). Also collects information about the
    ongoing translation job if there exists a record for such a job
    for this document. Otherwise populates the job attributes with
    suitable defaults to be displayed in the editing form for the job.
    """

    TABLE = "summary_translation_job"
    HISTORY = "summary_translation_job_history"
    KEY = "english_id"
    FIELDS = (
        "state_id",
        "state_date",
        "assigned_to",
        "change_type",
        "comments"
    )

    def __init__(self, control):
        """Save a reference to the `Control` object.

        Pass:
          control - access to the form and to the database
        """

        self.__control = control

    @property
    def assigned_to(self):
        """ID of user to whom the translation job has been assigned."""
        return self.row.assigned_to if self.row else None

    @property
    def banner(self):
        """Use English summary title for the main banner (possible shortened).
        """

        if not hasattr(self, "_banner"):
            self._banner = self.english_title
            if len(self._banner) > 40:
                self._banner = self._banner[:40] + " ..."
        return self._banner

    @property
    def change_type(self):
        """Primary key for the type of change for the English summary.

        If this is a new job, we try to determine the change type from
        parsing the summary.
        """

        if not hasattr(self, "_change_type"):
            if self.row:
                self._change_type = self.row.change_type
            else:
                self._change_type = None
                query = db.Query("document", "xml")
                query.where(query.Condition("id", self.english_id))
                try:
                    xml = query.execute(self.__control.cursor).fetchone().xml
                    root = etree.fromstring(xml.encode("utf-8"))
                    class Change:
                        def __init__(self, node):
                            self.value = self.date = ""
                            child = node.find("TypeOfSummaryChangeValue")
                            if child is not None and child.text is not None:
                                self.value = child.text.lower()
                            child = node.find("Date")
                            if child is not None and child.text is not None:
                                self.date = child.text
                        def __lt__(self, other):
                            return self.date < other.date
                    name = "TypeOfSummaryChange"
                    change_types = [Change(n) for n in root.findall(name)]
                    if change_types:
                        change_type = sorted(change_types)[-1].value
                        for id, value in self.__control.change_types.values:
                            if change_type.startswith(value.lower()):
                                self._change_type = id
                                break
                except Exception:
                    self.__control.logger.exception("Parsing change types")
        return self._change_type

    @property
    def changed(self):
        """
        Determine whether any of the fields on the editing form have
        been changed. We do this to optimize away unnecessary writes
        to the database.
        """

        for name in self.FIELDS:
            if getattr(self, name) != getattr(self.__control, name):
                return True
        return False

    @property
    def comments(self):
        """Notes on the translation job."""
        return self.row.comments if self.row else None

    @property
    def english_id(self):
        """CDR ID for the English PDQ Summary being translated."""
        return self.__control.english_id

    @property
    def english_title(self):
        """Title for the original English summary document."""

        if not hasattr(self, "_english_title"):
            parts = self.full_english_title.split(";")
            self._english_title = parts[0].strip()
        return self._english_title

    @property
    def english_audience(self):
        """Audience for the original English summary document."""

        if not hasattr(self, "_english_audience"):
            parts = self.full_english_title.split(";")
            self._audience = parts[-1].strip()
        return self._audience

    @property
    def full_english_title(self):
        """Title column for the original English summary document."""

        if not hasattr(self, "_full_english_title"):
            title = self.__control.english_summaries[self.english_id]
            self._full_english_title = title
        return self._full_english_title

    @property
    def full_spanish_title(self):
        """Title column for the translated summary (if it exists)."""

        if not hasattr(self, "_full_spanish_title"):
            if self.spanish_id is None:
                self._full_spanish_title = None
            else:
                title = self.__control.spanish_summaries.get(self.spanish_id)
                if not title:
                    message = f"CDR{self.spanish_id} is not a Spanish summary"
                    self.__control.bail(message)
                self._full_spanish_title = title
        return self._full_spanish_title

    @property
    def new(self):
        """True if we don't already have a job for this summary."""
        return False if self.row else True

    @property
    def row(self):
        """Current values for an existing job, if applicable."""

        if not hasattr(self, "_row"):
            query = db.Query(self.TABLE, *self.FIELDS)
            query.where(query.Condition(self.KEY, self.english_id))
            self._row = query.execute(self.__control.cursor).fetchone()
        return self._row

    @property
    def spanish_id(self):
        """CDR ID for the translated summary document (if it exists)."""

        if not hasattr(self, "_spanish_id"):
            query = db.Query("query_term", "doc_id")
            query.where("path = '/Summary/TranslationOf/@cdr:ref'")
            query.where(query.Condition("int_val", self.english_id))
            row = query.execute(self.__control.cursor).fetchone()
            self._spanish_id = row.doc_id if row else None
        return self._spanish_id

    @property
    def spanish_audience(self):
        """Audience for the translated summary document (if it exists)."""

        if not hasattr(self, "_spanish_audience"):
            if self.full_spanish_title is None:
                self._spanish_audience = None
            else:
                parts = self.full_spanish_title.split(";")
                self._spanish_audience = parts[-1].strip()
        return self._spanish_audience

    @property
    def spanish_title(self):
        """Title for translated summary document (if it exists)."""

        if not hasattr(self, "_spanish_title"):
            if self.full_spanish_title is None:
                self._spanish_title = None
            else:
                parts = self.full_spanish_title.split(";")
                self._spanish_title = parts[0].strip()
        return self._spanish_title

    @property
    def state_date(self):
        """Date the job state last changed or set."""
        return self.row.state_date if self.row else None

    @property
    def state_id(self):
        """Primary key for the job's state."""
        return self.row.state_id if self.row else None

    @property
    def subtitle(self):
        """Override for string below banner if we have a Spanish summary."""

        if not hasattr(self, "_subtitle"):
            if self.full_spanish_title is None:
                self._subtitle = None
            else:
                args = self.spanish_id, self.full_spanish_title
                self._subtitle = "Spanish summary: CDR{} ({})".format(*args)
        return self._subtitle


if __name__ == "__main__":
    """
    Make it possible to load this script as a module.
    """

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure")
        control.bail(f"failure: {e}")
