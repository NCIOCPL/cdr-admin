#!/usr/bin/env python

"""Interface for creating/editing a glossary translation job.

JIRA::OCECDR-4489
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """
    Logic for displaying an editing form for creating new translation
    jobs as well as modifying existing jobs.
    """

    JOBS = "Jobs"
    DELETE = "Delete"
    LOGNAME = "glossary-translation-workflow"
    SUMMARY = "Summary"
    MEDIA = "Media"
    REPORTS_MENU = SUBMENU = "Reports"
    ADMINMENU = "Admin"
    SUBTITLE = "Glossary Translation Job"
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
            self.redirect("glossary-translation-jobs.py")
        elif self.request == self.DELETE:
            self.delete_job()
        elif self.request == self.MEDIA:
            self.redirect("media-translation-jobs.py")
        elif self.request == self.SUMMARY:
            self.redirect("translation-jobs.py")
        Controller.run(self)

    def show_report(self):
        """
        Override the base class because we're storing data, not
        creating a report. Modified to also populate the history
        table.
        """

        if self.have_required_values:
            if self.job.changed:
                params = [getattr(self, name) for name in Job.FIELDS]
                params.append(self.started)
                params.append(getattr(self, Job.KEY))
                self.logger.info("storing translation job state %s", params)
                placeholders = ", ".join(["?"] * len(params))
                cols = ", ".join(Job.FIELDS + ("state_date", Job.KEY))
                strings = Job.HISTORY, cols, placeholders
                self.cursor.execute(self.INSERT.format(*strings), params)
                if self.job.new:
                    strings = Job.TABLE, cols, placeholders
                    query = self.INSERT.format(*strings)
                else:
                    cols = [f"{name} = ?" for name in Job.FIELDS]
                    cols.append("state_date = ?")
                    strings = Job.TABLE, ", ".join(cols), Job.KEY
                    query = self.UPDATE.format(*strings)
                try:
                    self.cursor.execute(query, params)
                    self.conn.commit()
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        self.logger.error("duplicate translation job ID")
                        self.bail("attempt to create duplicate job")
                    else:
                        self.logger.error("database failure: %s", e)
                        self.bail(f"database failure: {e}")
                self.logger.info("translation job state stored successfully")
            self.redirect("glossary-translation-jobs.py")
        else:
            self.show_form()

    def populate_form(self, page):
        """
        Show the form for editing/creating a transation job.

        Pass:
            page - object used to collect the form fields
        """

        if self.job and not self.job.new:
            page.add_script(f"""\
jQuery(function() {{
  jQuery("input[value='{self.DELETE}']").click(function(e) {{
    if (confirm("Are you sure?"))
      return true;
    e.preventDefault();
  }});
}});""")
        else:
            page.add_script(f"""\
var submitted = false;
jQuery(function() {{
  jQuery("input[value='{self.SUBMIT}']").click(function(e) {{
    if (!submitted) {{
      submitted = true;
      return true;
    }}
    e.preventDefault();
  }});
}});""")
        action = "Edit" if self.job and not self.job.new else "Create"
        legend = f"{action} Translation Job"
        fieldset = page.fieldset(legend)
        if self.doc_id:
            page.form.append(page.hidden_field("doc_id", self.doc_id))
        else:
            fieldset.append(page.text_field("doc_id", label="Doc ID"))
        user = self.job.assigned_to if self.job else self.lead_translator
        if not user:
            user = self.lead_translator
        opts = dict(options=self.translators, default=user)
        fieldset.append(page.select("assigned_to", **opts))
        states = self.states.values
        state_id = self.job.state_id if self.job else None
        if not state_id:
            state_id = states[0][0]
        opts = dict(options=states, default=state_id, label="Status")
        fieldset.append(page.select("state", **opts))
        comments = self.job.comments if self.job else None
        comments = (comments or "").replace("\r", "")
        fieldset.append(page.textarea("comments", value=comments))
        page.form.append(fieldset)

    def delete_job(self):
        """
        Drop the table row for a job (we already have confirmation from
        the user).
        """

        query = f"DELETE FROM {Job.TABLE} WHERE doc_id = ?"
        self.cursor.execute(query, self.doc_id)
        self.conn.commit()
        self.logger.info("removed translation job for CDR%d", self.doc_id)
        self.redirect("glossary-translation-jobs.py")

    @property
    def assigned_to(self):
        """Integer for the account ID of the user who is assigned this task."""

        if not hasattr(self, "_assigned_to"):
            self._assigned_to = self.fields.getvalue("assigned_to")
            if self._assigned_to:
                if not self._assigned_to.isdigit():
                    self.bail()
                self._assigned_to = int(self._assigned_to)
                if self._assigned_to not in self.users:
                    self.bail()
        return self._assigned_to

    @property
    def buttons(self):
        """Customize the action buttons."""

        if not hasattr(self, "_buttons"):
            self._buttons = [self.SUBMIT, self.JOBS]
            if self.job and not self.job.new:
                self._buttons.append(self.DELETE)
            self._buttons.append(self.SUMMARY)
            self._buttons.append(self.MEDIA)
            self._buttons.append(self.SUBMENU)
            self._buttons.append(self.ADMINMENU)
            self._buttons.append(self.LOG_OUT)
        return self._buttons

    @property
    def comments(self):
        """Notes on the translation job."""

        if not hasattr(self, "_comments"):
            self._comments = None
            comments = self.fields.getvalue("comments", "").strip()
            if comments:
                self._comments = comments.replace("\r", "")
        return self._comments

    @property
    def doc(self):
        """`Doc` object for the glossary document being translated."""

        if not hasattr(self, "_doc"):
            self._doc = None
            id = self.fields.getvalue("doc_id")
            if id:
                try:
                    doc = self._doc = Doc(self.session, id=id)
                except Exception:
                    self.logger.exception("id %r", id)
                    self.bail("Invalid document ID")
                if not doc.doctype.name.lower().startswith("glossary"):
                    self.bail(f"CDR{doc.id} is a {doc.doctype} document")
        return self._doc

    @property
    def doc_id(self):
        """Integer for the CDR ID of the glossary document being translated."""
        return self.doc.id if self.doc else None

    @property
    def doc_type(self):
        """String for the name of the glossary document's CDR doctype."""
        return self.doc.doctype.name if self.doc else None

    @property
    def doc_title(self):
        if not hasattr(self, "_doc_title"):
            if not self.doc_type:
                self._doc_title = None
            else:
                if self.doc_type.lower() == "glossarytermname":
                    self._doc_title = self.doc.title.split(";")[0].strip()
                else:
                    path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
                    query = self.Query("document d", "d.title").limit(1)
                    query.join("query_term q", "q.doc_id = d.id")
                    query.where(query.Condition("q.path", path))
                    query.where(query.Condition("q.int_val", self.doc_id))
                    query.where("d.active_status = 'A'")
                    query.order("d.title")
                    row = query.execute(self.cursor).fetchone()
                    if row:
                        title = row.title.split(";")[0].strip()
                        self._doc_title = f"Concept document for {title}"
                    else:
                        pattern = "Concept document CDR{:d}"
                        self._doc_title = pattern.format(self.doc_id)
        return self._doc_title

    @property
    def have_required_values(self):
        """
        Determine whether we have values for all of the required job fields.
        """

        for name in Job.REQUIRED:
            if not getattr(self, name):
                return False
        return True

    @property
    def job(self):
        """Translation job being displayed/edited."""

        if not hasattr(self, "_job"):
            self._job = Job(self) if self.doc_id else None
        return self._job

    @property
    def lead_translator(self):
        """Default assignee for a new translation job."""

        if not hasattr(self, "_lead_translator"):
            group_name = "Spanish Translation Leads"
            leads = self.load_group(group_name).items
            self._lead_translator = leads[0][0] if leads else None
        return self._lead_translator

    @property
    def state_id(self):
        """Primary key for the selected translation state."""

        if not hasattr(self, "_state_id"):
            self._state_id = self.fields.getvalue("state")
            if self._state_id:
                if not self._state_id.isdigit():
                    self.bail()
                self._state_id = int(self._state_id)
                if self._state_id not in self.states.map:
                    self.bail()
        return self._state_id

    @property
    def states(self):
        """Valid values for the translation job states."""

        if not hasattr(self, "_states"):
            self._states = self.load_valid_values("glossary_translation_state")
        return self._states

    @property
    def subtitle(self):
        """What we display under the main banner."""
        return self.job.subtitle if self.job else self.SUBTITLE

    @property
    def translators(self):
        """Users who are authorized to translate glossary documents.

        Expand the list to include the translator of the current job,
        in case he/she is no long in the translation group.
        """

        if not hasattr(self, "_translators"):
            translators = self.load_group("Spanish Glossary Translators")
            if self.assigned_to and self.assigned_to not in translators.map:
                translators = translators.map
                translators[self.assigned_to] = self.users[self.assigned_to]
                def key(pair): return pair[1].lower()
                self._translators = sorted(translators.items(), key=key)
            else:
                self._translators = translators.items
        return self._translators

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
            query = self.Query("usr", "id", "fullname")
            query.where("fullname IS NOT NULL")
            rows = query.execute(self.cursor).fetchall()
            self._users = dict([tuple(row) for row in rows])
        return self._users


class Job:
    """Translation job for a CDR glossary document.

    Collect the information about the CDR glossary document being
    translated into Spanish. Also collect information about the
    ongoing translation job if there exists a record for such a job
    for this document. Otherwise populate the job attributes with
    suitable defaults to be displayed in the editing form for the job.
    """

    TABLE = "glossary_translation_job"
    HISTORY = "glossary_translation_job_history"
    KEY = "doc_id"
    FIELDS = "state_id", "assigned_to", "comments"
    REQUIRED = "doc_id", "state_id", "assigned_to"

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
    def changed(self):
        """Determine whether any fields on the editing form have been changed.

        We do this to optimize away unnecessary writes to the database.
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
    def doc_id(self):
        """CDR ID for the CDR glossary document being translated."""
        return self.__control.doc_id

    @property
    def doc_title(self):
        """String for the title of the glossary document."""
        return self.__control.doc_title

    @property
    def doc_type(self):
        """String for the name of the glossary document's CDR doctype."""
        return self.__control.doc_type

    @property
    def new(self):
        """True if we don't already have a job for this summary."""
        return False if self.row else True

    @property
    def row(self):
        """Current values for an existing job, if applicable."""

        if not hasattr(self, "_row"):
            query = self.__control.Query(self.TABLE, *self.FIELDS)
            query.where(query.Condition(self.KEY, self.doc_id))
            self._row = query.execute(self.__control.cursor).fetchone()
        return self._row

    @property
    def state_id(self):
        """Primary key for the job's state."""
        return self.row.state_id if self.row else None

    @property
    def subtitle(self):
        """Override for string below banner."""

        if not hasattr(self, "_subtitle"):
            title = self.doc_title.split(";")[0].strip()
            cdr_id = self.__control.doc.cdr_id
            if len(title) > 40:
                title = f"{title[:40]} ..."
            self._subtitle = f"Translation job for {cdr_id} ({title})"
        return self._subtitle


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure")
        control.bail(f"failure: {e}")
