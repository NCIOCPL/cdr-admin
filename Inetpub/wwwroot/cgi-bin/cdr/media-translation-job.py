"""
Interface for creating/editing a media translation job

JIRA::OCECDR-4489
"""

import operator
import cdr
import cdrcgi
from cdrapi import db


class Control(cdrcgi.Control):
    """
    Logic for displaying an editing form for creating new translation
    jobs as well as modifying existing jobs.
    """

    JOBS = "Jobs"
    DELETE = "Delete"
    LOGNAME = "media-translation-workflow"
    SUMMARY = "Summary"
    GLOSSARY = "Glossary"
    REPORTS_MENU = SUBMENU = "Reports"
    ADMINMENU = "Admin"

    def __init__(self):
        """
        Collect and validate the request parameters
        """

        cdrcgi.Control.__init__(self, "Translation Job")
        self.conn = db.connect()
        self.cursor = self.conn.cursor()
        if not self.session:
            cdrcgi.bail("not authorized")
        if not cdr.canDo(self.session, "MANAGE TRANSLATION QUEUE"):
            cdrcgi.bail("not authorized")
        self.states = self.load_values("media_translation_state")
        self.users = self.load_users()
        self.translators = self.load_group("Spanish Media Translators")
        self.lead_translators = self.load_group("Spanish Translation Leads")
        self.english_id = self.get_id("english_id")
        self.state_id = self.get_id("state", self.states.map)
        self.assigned_to = self.get_id("assigned_to", self.users)
        self.comments = self.fields.getvalue("comments") or None
        self.job = Job(self) if self.english_id else None

    def run(self):
        """
        Override the base class method to handle additional buttons.
        """

        if self.request == self.JOBS:
            cdrcgi.navigateTo("media-translation-jobs.py", self.session)
        elif self.request == self.DELETE:
            self.delete_job()
        elif self.request == self.GLOSSARY:
            cdrcgi.navigateTo("glossary-translation-jobs.py", self.session)
        elif self.request == self.SUMMARY:
            cdrcgi.navigateTo("translation-jobs.py", self.session)
        cdrcgi.Control.run(self)

    def show_report(self):
        """
        Override the base class because we're storing data, not
        creating a report. Modified to also populate the history
        table.
        """

        if self.have_required_values():
            if self.job.changed():
                params = [getattr(self, name) for name in Job.FIELDS]
                params.append(self.started)
                params.append(getattr(self, Job.KEY))
                self.logger.info("storing translation job state %s", params)
                placeholders = ", ".join(["?"] * len(params))
                cols = ", ".join(Job.FIELDS + ("state_date", Job.KEY))
                args = (Job.HISTORY, cols, placeholders)
                query = "INSERT INTO {} ({}) VALUES ({})".format(*args)
                self.cursor.execute(query, params)
                if self.job.new:
                    strings = Job.TABLE, cols, placeholders
                    query = "INSERT INTO {} ({}) VALUES ({})".format(*strings)
                else:
                    cols = [("{} = ?".format(name)) for name in Job.FIELDS]
                    cols.append("state_date = ?")
                    strings = (Job.TABLE, ", ".join(cols), Job.KEY)
                    query = "UPDATE {} SET {} WHERE {} = ?".format(*strings)
                try:
                    self.cursor.execute(query, params)
                    self.conn.commit()
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        self.logger.error("duplicate translation job ID")
                        cdrcgi.bail("attempt to create duplicate job")
                    else:
                        self.logger.error("database failure: %s", e.message)
                        cdrcgi.bail("database failure: {}".format(e.message))
                self.logger.info("translation job state stored successfully")
            cdrcgi.navigateTo("media-translation-jobs.py", self.session)
        else:
            self.show_form()

    def set_form_options(self, opts):
        """
        Add some extra buttons and optionally replace the banner's subtitle.
        """

        opts["buttons"].insert(-3, self.JOBS)
        if self.job:
            if not self.job.new:
                opts["buttons"].insert(-3, self.DELETE)
            opts["banner"] = self.job.banner
            if self.job.subtitle:
                opts["subtitle"] = self.job.subtitle
        opts["buttons"].insert(-3, self.SUMMARY)
        opts["buttons"].insert(-3, self.GLOSSARY)
        return opts

    def populate_form(self, form):
        """
        Add the fields to the job form
        """

        if self.job and not self.job.new:
            form.add_script("""\
jQuery("input[value='{}']").click(function(e) {{
    if (confirm("Are you sure?"))
        return true;
    e.preventDefault();
}});""".format(self.DELETE))
        else:
            form.add_script("""\
var submitted = false;
jQuery("input[value='{}']").click(function(e) {{
    if (!submitted) {{
        submitted = true;
        return true;
    }}
    e.preventDefault();
}});""".format(self.SUBMIT))
        action = "Edit" if self.job and not self.job.new else "Create"
        legend = "{} Translation Job".format(action)
        if self.english_id:
            legend = "{} for CDR{}".format(legend, self.english_id)
            form.add_hidden_field("english_id", self.english_id)
        form.add("<fieldset>")
        form.add(form.B.LEGEND(legend))
        user = self.job.assigned_to if self.job else None
        users = self.translators
        if user:
            if user not in users:
                users[user] = self.users[user]
        elif self.lead_translators:
            user = self.sort_dict(self.lead_translators)[0][0]
        users = self.sort_dict(users)
        states = self.states.values
        state_id = self.job.state_id if self.job else None
        if not state_id:
            state_id = states[0][0]
        comments = self.job.comments if self.job else None
        comments = comments or ""
        comments = comments.replace("\r", "").replace("\n", cdrcgi.NEWLINE)
        if not self.english_id:
            form.add_text_field("english_id", "English ID")
        form.add_select("assigned_to", "Assigned To", users, user)
        form.add_select("state", "Status", states, state_id)
        form.add_textarea_field("comments", "Comments", value=comments)
        form.add("</fieldset>")

    def delete_job(self):
        """
        Drop the table row for a job (we already have confirmation from
        the user).
        """

        query = "DELETE FROM {} WHERE english_id = ?".format(Job.TABLE)
        self.cursor.execute(query, self.english_id)
        self.conn.commit()
        self.logger.info("removed translation job for CDR%d", self.english_id)
        cdrcgi.navigateTo("media-translation-jobs.py", self.session)

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

    def get_id(self, name, valid_values=None):
        """
        Fetch and validate a parameter for a primary key in one
        of the valid values tables.

        Pass:
            name - name of the CGI parameter
            valid_values - dictionary of valid values indexed by primary keys
                           if None, verify that the value (if present)
                           is the CDR ID for a Media document

        Return:
            integer for a valid value primary key if parameter is present
            otherwise None

        Script exits with an error message if the parameters have been
        tampered with by a hacker.
        """

        value = self.fields.getvalue(name)
        if not value:
            return None
        if valid_values:
            try:
                int_id = int(value)
            except:
                cdrcgi.bail("invalid {} ({!r})".format(name, value))
            if int_id not in valid_values:
                cdrcgi.bail("invalid {} ({!r})".format(name, value))
        else:
            try:
                int_id = cdr.exNormalize(value)[1]
            except:
                cdrcgi.bail("invalid {} ({!r})".format(name, value))
            query = db.Query("doc_type t", "name")
            query.join("document d", "d.doc_type = t.id")
            query.where(query.Condition("d.id", int_id))
            row = query.execute(self.cursor).fetchone()
            if not row:
                cdrcgi.bail("CDR{:d} not found".format(int_id))
            elif row.name.lower() != "media":
                cdrcgi.bail("CDR{:d} is not a Media document".format(int_id))
        return int_id

    def have_required_values(self):
        """
        Determine whether we have values for all of the required job fields.
        """

        for name in Job.REQUIRED:
            if not getattr(self, name):
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

    @staticmethod
    def sort_dict(d):
        """
        Generate a sequence from a dictionary, with the elements in the
        sequence ordered by the dictionary element's value. The sequence
        contain tuples of (key, value) pairs pulled from the dictionary.
        """

        return sorted(d.items(), key=operator.itemgetter(1))


class Job:
    """
    Represents a translation job for the currently selected English
    CDR Media document.
    """

    TABLE = "media_translation_job"
    HISTORY = "media_translation_job_history"
    KEY = "english_id"
    FIELDS = "state_id", "assigned_to", "comments"
    REQUIRED = "english_id", "state_id", "assigned_to"

    def __init__(self, control):
        """
        Collect the information about the English CDR Media document
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
        self.subtitle = self.spanish_id = self.spanish_title = None
        for name in self.FIELDS:
            setattr(self, name, None)
        query = db.Query(self.TABLE, *self.FIELDS)
        query.where(query.Condition(self.KEY, self.english_id))
        row = query.execute(control.cursor).fetchone()
        if row:
            self.new = False
            for name in self.FIELDS:
                setattr(self, name, getattr(row, name))
        query = db.Query("document", "title")
        query.where(query.Condition("id", self.english_id))
        row = query.execute(control.cursor).fetchone()
        title_not_found = "Title for CDR{:d} not found"
        if not row:
            cdrcgi.bail(title_not_found.format(self.english_id))
        title_parts = row.title.split(";")
        self.banner = self.english_title = title_parts[0]
        if len(self.banner) > 40:
            self.banner = self.banner[:40] + " ..."
        query = db.Query("document d", "d.id", "d.title")
        query.join("query_term q", "q.doc_id = d.id")
        query.where("q.path = '/Media/TranslationOf/@cdr:ref'")
        query.where(query.Condition("q.int_val", self.english_id))
        row = query.execute(control.cursor).fetchone()
        if row:
            self.spanish_id = row.id
            self.spanish_title = row.title.split(";")[0]
            args = self.spanish_id, self.spanish_title
            self.subtitle = "Spanish Media doc: CDR{:d} ({})".format(*args)

    def changed(self):
        """
        Determine which fields on the editing form have been changed

        We do this to optimize away unnecessary writes to the database.
        """

        fields = []
        for name in self.FIELDS:
            if getattr(self, name) != getattr(self.control, name):
                fields.append(name)
        return fields

if __name__ == "__main__":
    """
    Make it possible to load this script as a module
    """

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure")
        cdrcgi.bail("failure: {}".format(e.message))
