"""
Edit a summary translation job.
JIRA::OCECDR-4193
JIRA::OCECDR-4248 - allow the user to attach a file
JIRA::OCECDR-4504 - make the status date field read-only
"""

import datetime
import operator
import lxml.etree as etree
import cdr
import cdrcgi
from cdrapi import db
from cdrapi.settings import Tier

class Control(cdrcgi.Control):
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

    def __init__(self):
        """
        Collect and validate the request parameters.
        """

        self.tier = Tier()
        cdrcgi.Control.__init__(self, "Translation Job")
        if not self.session:
            cdrcgi.bail("not authorized")
        if not cdr.canDo(self.session, "MANAGE TRANSLATION QUEUE"):
            cdrcgi.bail("not authorized")
        self.user = self.UserInfo(self)
        self.today = datetime.date.today()
        self.states = self.load_values("summary_translation_state")
        self.change_types = self.load_values("summary_change_type")
        self.english_summaries = self.get_summaries("English")
        self.spanish_summaries = self.get_summaries("Spanish")
        self.users = self.load_users()
        self.translators = self.load_group("Spanish Translators")
        self.lead_translators = self.load_group("Spanish Translation Leads")
        self.assigned_to = self.get_id("assigned_to", self.users)
        self.english_id = self.get_id("english_id", self.english_summaries)
        self.state_id = self.get_id("state", self.states.map)
        self.change_type = self.get_id("change_type", self.change_types.map)
        self.state_date = self.fields.getvalue("state_date")
        self.comments = self.fields.getvalue("comments") or None
        self.job = self.english_id and Job(self) or None
        cdrcgi.valParmDate(self.state_date, empty_ok=True, msg=cdrcgi.TAMPERING)

    def run(self):
        """
        Override the base class method to handle additional buttons.
        """

        if self.request == self.JOBS:
            cdrcgi.navigateTo("translation-jobs.py", self.session)
        elif self.request == self.DELETE:
            self.delete_job()
        elif self.request == self.GLOSSARY:
            cdrcgi.navigateTo("glossary-translation-jobs.py", self.session)
        elif self.request == self.MEDIA:
            cdrcgi.navigateTo("media-translation-jobs.py", self.session)
        cdrcgi.Control.run(self)

    def show_report(self):
        """
        Override the base class because we're storing data, not
        creating a report. Modified to also populate the history
        table.
        """

        if self.have_required_values():
            if self.job.changed():
                conn = db.connect()
                cursor = conn.cursor()
                params = [getattr(self, name) for name in Job.FIELDS]
                params.append(getattr(self, Job.KEY))
                self.logger.info("storing translation job state %s", params)
                placeholders = ", ".join(["?"] * len(params))
                cols = "%s, %s" % (", ".join(Job.FIELDS), Job.KEY)
                strings = (Job.HISTORY, cols, placeholders)
                query = "INSERT INTO %s (%s) VALUES (%s)" % strings
                cursor.execute(query, params)
                if self.job.new:
                    strings = (Job.TABLE, cols, placeholders)
                    query = "INSERT INTO %s (%s) VALUES (%s)" % strings
                else:
                    cols = ", ".join([("%s = ?" % name) for name in Job.FIELDS])
                    strings = (Job.TABLE, cols, Job.KEY)
                    query = "UPDATE %s SET %s WHERE %s = ?" % strings
                try:
                    cursor.execute(query, params)
                    conn.commit()
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        self.logger.error("duplicate translation job ID")
                        cdrcgi.bail("attempt to create duplicate job")
                    else:
                        self.logger.error("database failure: %s", e)
                        cdrcgi.bail("database failure: %s" % e)
                self.logger.info("translation job state stored successfully")
                job = Job(self)
                if self.alert_needed(job):
                    self.alert(job)
            cdrcgi.navigateTo("translation-jobs.py", self.session)
        else:
            self.show_form()

    def set_form_options(self, opts):
        """
        Add some extra buttons and optionally replace the banner's subtitle.

        OCECDR-4248: allow the user to post a file.
        """

        if self.english_id:
            opts["enctype"] = "multipart/form-data"
        opts["buttons"].insert(-3, self.JOBS)
        if self.job:
            if not self.job.new:
                opts["buttons"].insert(-3, self.DELETE)
            opts["banner"] = self.job.banner
            if self.job.subtitle:
                opts["subtitle"] = self.job.subtitle
        opts["buttons"].insert(-3, self.MEDIA)
        opts["buttons"].insert(-3, self.GLOSSARY)
        return opts

    def populate_form(self, form):
        """
        Separate out logic for editing jobs versus picking a summary doc.
        """

        if self.english_id:
            self.populate_editing_form(form)
        else:
            self.populate_summary_selection_form(form)

    def populate_editing_form(self, form):
        """
        We have an English summary; show the form for editing/creating its job.
        """

        if not self.job.new:
            form.add_script("""\
jQuery("input[value='%s']").click(function(e) {
    if (confirm("Are you sure?"))
        return true;
    e.preventDefault();
});""" % self.DELETE)
        else:
            form.add_script("""\
var submitted = false;
jQuery("input[value='%s']").click(function(e) {
    if (!submitted) {
        submitted = true;
        return true;
    }
    e.preventDefault();
});""" % self.SUBMIT)
        action = self.job.new and "Create" or "Edit"
        legend = "%s Translation Job for CDR%d" % (action, self.english_id)
        form.add("<fieldset>")
        form.add(form.B.LEGEND(legend))
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
        state_date = self.job.state_date or str(self.today)
        comments = self.job.comments or ""
        comments = comments.replace("\r", "").replace("\n", cdrcgi.NEWLINE)
        form.add_select("change_type", "Change Type", types, change_type)
        form.add_select("assigned_to", "Assigned To", users, user)
        form.add_select("state", "Status", states, state_id)
        form.add_hidden_field("state_date", state_date)
        form.add_textarea_field("comments", "Comments", value=comments)
        form.add_text_field("file", "QC Report", upload=True)
        form.add("</fieldset>")
        form.add_hidden_field("english_id", self.english_id)

    def populate_summary_selection_form(self, form):
        """
        We don't have a summary to translate yet; let the user pick one.
        """

        temp = self.sort_dict(self.english_summaries)
        query = db.Query(Job.TABLE, Job.KEY)
        rows = query.execute(self.cursor).fetchall()
        jobs = set([row[0] for row in rows])
        summaries = []
        for summary_id, summary_title in temp:
            if summary_id not in jobs:
                summaries.append((summary_id, summary_title))
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Select English Summary"))
        form.add_select("english_id", "Summary", summaries)
        form.add("</fieldset>")

    def delete_job(self):
        """
        Drop the table row for a job (we already have confirmation from
        the user).
        """

        query = "DELETE FROM %s WHERE english_id = ?" % Job.TABLE
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(query, self.english_id)
        conn.commit()
        self.logger.info("removed translation job for CDR%d", self.english_id)
        cdrcgi.navigateTo("translation-jobs.py", self.session)

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
            cdrcgi.bail("invalid %s (%s)" % (name, repr(value)))
        if int_id not in valid_values:
            cdrcgi.bail("invalid %s (%s)" % (name, repr(value)))
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

    def have_required_values(self):
        """
        Determine whether we have values for all of the required job fields.
        """

        for name in (Job.KEY,) + Job.FIELDS:
            if name != "comments" and not getattr(self, name):
                return False
        return True

    def load_users(self):
        """
        Fetch a dictionary of all active users.

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
            cdrcgi.bail(error)
        recips = [recip.email]
        sender = "cdr@cancer.gov"
        body = []
        subject = f"[{self.tier.name}] Translation Queue Notification"
        log_message = f"mailed translation job state alert to {recip}"
        if not cdr.isProdHost():
            recips = cdr.getEmailList("Test Translation Queue Recips")
            body.append("[*** THIS IS A TEST MESSAGE ON THE %s TIER. "
                        "ON PRODUCTION IT WOULD HAVE GONE TO %s. ***]\n" %
                        (self.tier.name, recip))
            log_message = "test alert for %s sent to %s" % (recip, recips)
        if self.job.new:
            body.append("A new translation job has been assigned to you.")
        else:
            body.append("A translation job assigned to you has a new status.")
        body.append("Assigned by: %s" % self.user)
        body.append("English summary document ID: CDR%d" % job.english_id)
        body.append("English summary title: %s" % job.english_title)
        if job.spanish_title:
            body.append("Spanish summary document ID: CDR%d" % job.spanish_id)
            body.append("Spanish summary title: %s" % job.spanish_title)
        body.append("Summary audience: %s" % job.english_audience)
        body.append("Job status: %s" % self.states.map.get(job.state_id))
        body.append("Date of status transition: %s" % job.state_date)
        body.append("Comments: %s" % job.comments)
        opts = dict(subject=subject, body="\n".join(body))
        attachment = self.fetch_file()
        if attachment:
            opts["attachments"] = [attachment]
        try:
            message = cdr.EmailMessage(sender, recips, **opts)
            message.send()
        except Exception as e:
            self.logger.error("sending mail: %s", e)
            cdrcgi.bail("sending mail: %s" % e)
        self.logger.info(log_message)

    def fetch_file(self):
        """
        If the user has posted a file, wrap it in a `cdr.EmailAttachment`
        object and return the object. Otherwise, return None
        """

        if "file" not in self.fields.keys():
            return None
        f = self.fields["file"]
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
        if not file_bytes:
            return None
        return cdr.EmailAttachment(file_bytes, f.filename)

    @staticmethod
    def sort_dict(d):
        """
        Generate a sequence from a dictionary, with the elements in the
        sequence ordered by the dictionary element's value. The sequence
        contain tuples of (key, value) pairs pulled from the dictionary.
        """

        return sorted(d.items(), key=operator.itemgetter(1))

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
                query.where(query.Condition("name", control.session))
                user_id = query.execute(control.cursor).fetchone()[0]
            self.id = user_id
            query = db.Query("open_usr", "email", "fullname")
            query.where(query.Condition("id", user_id))
            self.email, self.name = query.execute(control.cursor).fetchone()

        def __str__(self):
            """
            Create a display version of the user's information.
            """

            return "%s <%s>" % (self.name, self.email)


class Job:
    """
    Represents a translation job for the currently selected English
    CDR summary document.
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
        """
        Collect the information about the English CDR summary document
        being translated, as well as about the corresponding translated
        Spanish document (if it exists). Also collect information about
        the ongoing translation job if there exists a record for such
        a job for this document. Otherwise populate the job attributes
        with suitable defaults to be displayed in the editing form for
        the job.
        """

        self.control = control
        self.new = True
        self.english_id = control.english_id
        self.spanish_id = self.spanish_title = self.spanish_audience = None
        self.subtitle = None
        for name in self.FIELDS:
            setattr(self, name, None)
        query = db.Query(self.TABLE, *self.FIELDS)
        query.where(query.Condition(self.KEY, self.english_id))
        row = query.execute(control.cursor).fetchone()
        if row:
            self.new = False
            self.state_id = row[0]
            self.state_date = row[1]
            self.assigned_to = row[2]
            self.change_type = row[3]
            self.comments = row[4]
            if self.state_date:
                self.state_date = str(self.state_date)[:10]
        else:
            query = db.Query("document", "xml")
            query.where(query.Condition("id", self.english_id))
            try:
                xml = query.execute(control.cursor).fetchone()[0]
                root = etree.fromstring(xml.encode("utf-8"))
                class Change:
                    def __init__(self, node):
                        self.value = self.date = None
                        child = node.find("TypeOfSummaryChangeValue")
                        if child is not None and child.text is not None:
                            self.value = child.text.lower()
                        child = node.find("Date")
                        if child is not None and child.text is not None:
                            self.date = child.text
                    def __lt__(self, other):
                        return self.date < other.date
                name = "TypeOfSummaryChange"
                change_types = [Change(node) for node in root.findall(name)]
                if change_types:
                    change_type = sorted(change_types)[-1].value
                    for id, value in control.change_types.values:
                        if change_type.startswith(value.lower()):
                            self.change_type = id
                            break
            except:
                pass
        query = db.Query("query_term", "doc_id")
        query.where("path = '/Summary/TranslationOf/@cdr:ref'")
        query.where(query.Condition("int_val", self.english_id))
        row = query.execute(control.cursor).fetchone()
        if row:
            self.spanish_id = row[0]
            title = control.spanish_summaries.get(self.spanish_id)
            if not title:
                cdrcgi.bail("CDR%d is not a Spanish summary document" % row[0])
            title_parts = title.split(";")
            self.spanish_title = title = title_parts[0]
            self.spanish_audience = title_parts[-1]
            self.subtitle = "Spanish summary: CDR%d (%s)" % (row[0], title)
        title_parts = control.english_summaries[self.english_id].split(";")
        self.english_title = title_parts[0]
        self.english_audience = title_parts[-1]
        self.banner = self.english_title
        if len(self.banner) > 40:
            self.banner = self.banner[:40] + " ..."

    def changed(self):
        """
        Determine whether any of the fields on the editing form have
        been changed. We do this to optimize away unnecessary writes
        to the database.
        """

        for name in self.FIELDS:
            if getattr(self, name) != getattr(self.control, name):
                return True
        return False

if __name__ == "__main__":
    """
    Make it possible to load this script as a module.
    """

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure")
        cdrcgi.bail("failure: %s" % e)
