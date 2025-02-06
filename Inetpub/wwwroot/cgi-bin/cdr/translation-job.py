#!/usr/bin/env python

"""Edit a summary translation job.

JIRA::OCECDR-4193 - create translation job editor
JIRA::OCECDR-4248 - allow the user to attach a file
JIRA::OCECDR-4504 - make the status date field read-only
JIRA::OCECDR-4664 - automatically update status date
"""

from functools import cached_property
from datetime import date
from operator import itemgetter
from lxml import etree
from cdr import EmailMessage, EmailAttachment, isProdHost, getEmailList
from cdrcgi import Controller
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
    SUBTITLE = "Summary Translation Job"
    ACTION = "MANAGE TRANSLATION QUEUE"
    INSERT = "INSERT INTO {} ({}) VALUES ({})"
    UPDATE = "UPDATE {} SET {} WHERE {} = ?"
    DROP = "attachments-to-drop"
    QC_REPORT_INSTRUCTIONS = (
        "The following file(s) will be attached to all email notifications"
        " for this translation job. To delete a file from the set to be"
        " attached, check the box next to the file name. More files can"
        " be added in the field set below."
    )
    DELETE_INSTRUCTIONS = "Use Checkbox to Delete an Attachment"

    def delete_job(self):
        """
        Drop the table row for the job."""

        query = f"DELETE FROM {Job.TABLE} WHERE english_id = ?"
        self.cursor.execute(query, self.english_id)
        query = f"DELETE FROM {Job.ATTACHMENT} WHERE english_id = ?"
        self.cursor.execute(query, self.english_id)
        self.conn.commit()
        self.logger.info("removed translation job for CDR%d", self.english_id)
        message = (
            f"Translation job for CDR{self.english_id} successfully removed."
        )
        params = dict(message=message)
        if self.testing:
            params["testing"] = True
        self.redirect("translation-jobs.py", **params)

    def populate_form(self, page):
        """
        Separate out logic for editing jobs versus picking a summary doc.

        Pass:
            page - object used to collect the form fields
        """

        if self.testing:
            page.form.append(page.hidden_field("testing", "True"))
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
        identification = page.B.DIV(id="doc-identification")
        for line in self.job.identification:
            if len(line) > 120:
                line = f"{line[:120]} ...)"
            identification.append(page.B.DIV(line))
        page.main.find(".//h1").addnext(identification)
        action = "Create" if self.job.new else "Edit"
        fieldset = page.fieldset(f"{action} Translation Job")
        opts = dict(options=types, default=change_type)
        fieldset.append(page.select("change_type", **opts))
        opts = dict(options=users, default=user)
        fieldset.append(page.select("assigned_to", **opts))
        opts = dict(options=states, default=state_id)
        fieldset.append(page.select("status", **opts))
        fieldset.append(page.textarea("comments", value=comments))
        page.form.append(page.hidden_field("english_id", self.english_id))
        page.form.append(fieldset)
        fieldset = page.fieldset("QC Report Attachments")
        if self.attachments:
            fieldset.append(page.B.P(self.QC_REPORT_INSTRUCTIONS))
            fieldset.append(page.B.P(page.B.STRONG(self.DELETE_INSTRUCTIONS)))
            for id in sorted(self.attachments):
                opts = dict(label=self.attachments[id], value=id)
                fieldset.append(page.checkbox(self.DROP, **opts))
        field = page.B.DIV(
            page.B.LABEL(
                "Add QC Report Attachments",
                page.B.CLASS("usa-label"),
                page.B.FOR("files")
            ),
            page.B.INPUT(
                page.B.CLASS("usa-file-input"),
                type="file",
                id="files",
                name="files",
                multiple="multiple"
            )
        )
        field.find("input").set("aria-describedby", "files-hint")
        fieldset.append(field)
        page.form.append(fieldset)
        page.add_css(
            "#doc-identification { margin-bottom: 1.5rem; }\n"
            "#doc-identification div { font-weight: bold; }\n"
        )
        page.head.append(page.B.SCRIPT(src="/js/translation-job.js"))

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

    def run(self):
        """
        Override the base class method to handle additional buttons.
        """

        if not self.session or not self.session.can_do(self.ACTION):
            self.bail("not authorized")
        if self.request == self.JOBS:
            params = dict(testing=True) if self.testing else {}
            self.redirect("translation-jobs.py", **params)
        elif self.request == self.DELETE:
            self.delete_job()
        elif self.request == self.GLOSSARY:
            self.redirect("glossary-translation-jobs.py")
        elif self.request == self.MEDIA:
            self.redirect("media-translation-jobs.py")
        Controller.run(self)

    def show_report(self):
        """
        Override the base class because we're storing data, not
        creating a report. Modified to also populate the history
        table.
        """

        if self.have_required_values:
            self.process_attachments()
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
                    cols = [f"{name} = ?" for name in Job.FIELDS]
                    strings = (Job.TABLE, ", ".join(cols), Job.KEY)
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
                message = "Translation job state stored successfully."
                params = dict(message=message)
            else:
                message = "No changes found to store."
                params = dict(warning=message)
            if self.testing:
                params["testing"] = True
            self.redirect("translation-jobs.py", **params)
        else:
            self.show_form()

    @cached_property
    def assigned_to(self):
        """Translator to whom this translation task is currently assigned."""
        return self.get_id("assigned_to", self.users)

    @cached_property
    def attachments(self):
        """Dictionary of QC reports already attached to job.

        Key is attachment ID, value is display label.
        """

        attachments = {}
        query = db.Query(Job.ATTACHMENT, "attachment_id", "file_name")
        query.where(query.Condition("english_id", self.english_id))
        for row in query.execute(self.cursor).fetchall():
            attachments[row.attachment_id] = row.file_name
        return attachments

    @cached_property
    def banner(self):
        """Customize the display banner if we have a job."""
        return self.job.banner if self.job else self.title

    @cached_property
    def buttons(self):
        """Customize the action buttons."""

        if not self.job or self.job.new:
            return self.SUBMIT, self.JOBS, self.GLOSSARY, self.MEDIA
        return self.SUBMIT, self.JOBS, self.DELETE, self.GLOSSARY, self.MEDIA

    @cached_property
    def change_type(self):
        """Primary key for the change type for the English summary."""
        return self.get_id("change_type", self.change_types.map)

    @cached_property
    def change_types(self):
        """Valid values for types of summary changes."""
        return self.load_values("summary_change_type")

    @cached_property
    def comments(self):
        """Notes on the translation job."""
        comments = self.fields.getvalue("comments", "").strip()
        return comments if comments else None

    @cached_property
    def drop(self):
        """Attachments which should be removed from the job."""
        return self.fields.getlist(self.DROP)

    @cached_property
    def english_id(self):
        """CDR ID of English PDQ Summary being translated."""
        return self.get_id("english_id", self.english_summaries)

    @cached_property
    def english_summaries(self):
        """Dictionary of titles of English PDQ summaries."""
        return self.get_summaries("English")

    @cached_property
    def files(self):
        """Attachments to be appended to email notification."""

        files = []
        if self.english_id:
            query = db.Query(Job.ATTACHMENT, "file_bytes", "file_name")
            query.order("registered")
            query.where(query.Condition("english_id", self.english_id))
            for row in query.execute(self.cursor).fetchall():
                attachment = EmailAttachment(row.file_bytes, row.file_name)
                files.append(attachment)
        return files

    @cached_property
    def have_required_values(self):
        """
        Determine whether we have values for all of the required job fields.
        """

        for name in (Job.KEY,) + Job.FIELDS:
            if name != "comments" and not getattr(self, name):
                return False
        return True

    @cached_property
    def job(self):
        """Translation job being displayed/edited."""
        return Job(self) if self.english_id else None

    @cached_property
    def lead_translators(self):
        """Lead users for the PDQ Summary translation team."""
        return self.load_group("Spanish Translators Leads")

    @cached_property
    def posted_files(self):
        """Attachments to be added to the job."""

        if "files" not in self.fields:
            return []
        files = self.fields["files"]
        if not isinstance(files, (list, tuple)):
            files = [files]
        return [file for file in files if file.filename]

    @cached_property
    def same_window(self):
        """Ease up on the opening of new browser tabs."""
        return self.buttons

    @cached_property
    def spanish_summaries(self):
        """Dictionary of titles of Spanish PDQ summaries."""
        return self.get_summaries("Spanish")

    @cached_property
    def state_id(self):
        """Primary key for the job's current translation state."""
        return self.get_id("status", self.states.map)

    @cached_property
    def state_date(self):
        """If we save or update a job, set its state to today."""

        if self.job and self.state_id == self.job.state_id:
            return self.job.state_date
        return date.today()

    @cached_property
    def states(self):
        """Valid values for summary translation states."""
        return self.load_values("summary_translation_state")

    @cached_property
    def testing(self):
        """Used by automated tests to avoid spamming the users."""
        return self.fields.getvalue("testing")

    @cached_property
    def translators(self):
        """Users who are authorized to translate PDQ summaries."""
        return self.load_group("Spanish Translators")

    @cached_property
    def user(self):
        """Instance of `UserInfo` class."""
        return self.UserInfo(self)

    @cached_property
    def users(self):
        """Dictionary of all active users.

        We need this for validating the assigned_to parameter. The set
        of currently active translators won't work for that purpose,
        because a job may have been assigned to a user who is no longer
        active, or who has been subsequently removed from the translators
        group.
        """

        query = db.Query("usr", "id", "fullname")
        query.where("fullname IS NOT NULL")
        rows = query.execute(self.cursor).fetchall()
        return dict([(row[0], row[1]) for row in rows])

    def alert(self, job):
        """
        Send an email alert to the user to whom the translation job
        is currently assigned.

        Note that the `testing` property is set by the automated
        test suite, in which the account to which the job is
        assigned is a test account, so it's OK to use the recipient
        address instead of the Test Translation Queue Recips group
        addresses.
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
            if not self.testing:
                recips = getEmailList("Test Translation Queue Recips")
                body.append(
                    "[*** THIS IS A TEST MESSAGE ON THE "
                    f"{self.session.tier} TIER. "
                    f"ON PRODUCTION IT WOULD HAVE GONE TO {recip}. ***]\n"
                )
                log_message = f"test alert for {recip} sent to {recips}"
            else:
                self.logger.info("sending mail to the regression tester email")
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
        state_date = str(job.state_date)[:10]
        body.append(f"Date of status transition: {state_date}")
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
        except Exception:
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
            query.outer("query_term s", "s.doc_id = d.id",
                        "s.path = '/Summary/@SVPC'")
            query.where("(c.id IS NOT NULL OR m.value = 'Yes' "
                        "OR s.value = 'Yes')")
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

    def process_attachments(self):
        """Update the attachment table from the current form information."""

        conn = db.connect()
        cursor = conn.cursor()
        if self.drop:
            sql = f"DELETE FROM {Job.ATTACHMENT} WHERE attachment_id = ?"
            for attachment_id in self.drop:
                if int(attachment_id) not in self.attachments:
                    self.bail()
                cursor.execute(sql, (attachment_id,))
            conn.commit()
        columns = "english_id, file_bytes, file_name, registered"
        values = "?, ?, ?, GETDATE()"
        insert = self.INSERT.format(Job.ATTACHMENT, columns, values)
        for f in self.posted_files:
            self.logger.info("filename is %s", f.filename)
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
                values = self.english_id, file_bytes, f.filename
                cursor.execute(insert, values)
                conn.commit()
            else:
                self.logger.warning("%s empty", f.filename)

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
    ATTACHMENT = "summary_translation_job_attachment"
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

    @cached_property
    def assigned_to(self):
        """ID of user to whom the translation job has been assigned."""
        return self.row.assigned_to if self.row else None

    @cached_property
    def change_type(self):
        """Primary key for the type of change for the English summary.

        If this is a new job, we try to determine the change type from
        parsing the summary.
        """

        if self.row:
            return self.row.change_type
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
                        return id
        except Exception:
            self.__control.logger.exception("Parsing change types")
        return None

    @cached_property
    def changed(self):
        """
        Determine whether any of the fields on the editing form have
        been changed. We do this to optimize away unnecessary writes
        to the database.
        """

        changed = False
        self.__control.logger.info("checking to see if the job has changed")
        for name in self.FIELDS:
            job, form = getattr(self, name), getattr(self.__control, name)
            if job != form:
                args = name, job, form
                self.__control.logger.info("%s: %s <> %s", *args)
                changed = True
        count = len(self.__control.posted_files)
        if count:
            self.__control.logger.info("%d new files posted", count)
            changed = True
        count = len(self.__control.drop)
        if count:
            self.__control.logger.info("dropping %d attachments", count)
            changed = True
        return changed

    @cached_property
    def comments(self):
        """Notes on the translation job."""
        return self.row.comments if self.row else None

    @cached_property
    def english_id(self):
        """CDR ID for the English PDQ Summary being translated."""
        return self.__control.english_id

    @cached_property
    def english_title(self):
        """Title for the original English summary document."""
        return self.full_english_title.split(";")[0].strip()

    @cached_property
    def english_audience(self):
        """Audience for the original English summary document."""
        return self.full_english_title.split(";")[-1].strip()

    @cached_property
    def full_english_title(self):
        """Title column for the original English summary document."""
        return self.__control.english_summaries[self.english_id]

    @cached_property
    def full_spanish_title(self):
        """Title column for the translated summary (if it exists)."""

        if self.spanish_id is None:
            return None
        title = self.__control.spanish_summaries.get(self.spanish_id)
        if not title:
            message = f"CDR{self.spanish_id} is not a Spanish summary"
            self.__control.bail(message)
        return title

    @cached_property
    def identification(self):
        """Lines displayed at the top of the form to identify the docs."""

        cdr_id, title = f"CDR{self.english_id}", self.english_title
        lines = [f"English summary: {cdr_id} ({title})"]
        if self.spanish_title:
            cdr_id, title = f"CDR{self.spanish_id}", self.spanish_title
            lines.append(f"Spanish summary: {cdr_id} ({title})")
        return lines

    @cached_property
    def new(self):
        """True if we don't already have a job for this summary."""
        return False if self.row else True

    @cached_property
    def row(self):
        """Current values for an existing job, if applicable."""

        query = db.Query(self.TABLE, *self.FIELDS)
        query.where(query.Condition(self.KEY, self.english_id))
        return query.execute(self.__control.cursor).fetchone()

    @cached_property
    def spanish_id(self):
        """CDR ID for the translated summary document (if it exists)."""

        query = db.Query("query_term", "doc_id")
        query.where("path = '/Summary/TranslationOf/@cdr:ref'")
        query.where(query.Condition("int_val", self.english_id))
        row = query.execute(self.__control.cursor).fetchone()
        return row.doc_id if row else None

    @cached_property
    def spanish_audience(self):
        """Audience for the translated summary document (if it exists)."""

        if self.full_spanish_title is None:
            return None
        return self.full_spanish_title.split(";")[-1].strip()

    @cached_property
    def spanish_title(self):
        """Title for translated summary document (if it exists)."""

        if self.full_spanish_title is None:
            return None
        return self.full_spanish_title.split(";")[0].strip()

    @cached_property
    def state_date(self):
        """Date the job state last changed or set."""
        return self.row.state_date if self.row else None

    @cached_property
    def state_id(self):
        """Primary key for the job's state."""
        return self.row.state_id if self.row else None


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
