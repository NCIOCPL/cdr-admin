#!/usr/bin/env python

"""Interface for creating/editing a glossary translation job.
"""

from functools import cached_property
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
    SUBTITLE = "Glossary Translation Job"
    ACTION = "MANAGE TRANSLATION QUEUE"
    INSERT = "INSERT INTO {} ({}) VALUES ({})"
    UPDATE = "UPDATE {} SET {} WHERE {} = ?"

    def delete_job(self):
        """Drop the table row for the job."""

        query = f"DELETE FROM {Job.TABLE} WHERE doc_id = ?"
        self.cursor.execute(query, self.doc_id)
        self.conn.commit()
        self.logger.info("removed translation job for CDR%d", self.doc_id)
        message = f"Translation job for CDR{self.doc_id} successfully removed."
        parms = dict(message=message)
        self.redirect("glossary-translation-jobs.py", **parms)

    def populate_form(self, page):
        """Show the form for editing/creating a transation job.

        Pass:
            page - object used to collect the form fields
        """

        fieldset = page.fieldset(self.doc_title or "Create Translation Job")
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
        page.head.append(page.B.SCRIPT(src="/js/translation-job.js"))

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

        if self.missing_values:
            for field in self.missing_values:
                error = f"Required {field} value not provided."
                self.alerts.append(dict(message=error, type="error"))
            self.show_form()
        else:
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
                message = f"Translation job for CDR{self.doc_id} saved."
                parms = dict(message=message)
                self.logger.info("translation job state stored successfully")
            else:
                warning = f"No changes found in job for CDR{self.doc_id}."
                parms = dict(warning=warning)
            self.redirect("glossary-translation-jobs.py", **parms)

    @cached_property
    def assigned_to(self):
        """Integer for the account ID of the user who is assigned this task."""

        assigned_to = self.fields.getvalue("assigned_to")
        if not assigned_to:
            return None
        if not assigned_to.isdigit():
            self.bail()
        assigned_to = int(assigned_to)
        if assigned_to not in self.users:
            self.bail()
        return assigned_to

    @cached_property
    def buttons(self):
        """Customize the action buttons."""

        if not self.job or self.job.new:
            return self.SUBMIT, self.JOBS, self.MEDIA, self.SUMMARY
        return self.SUBMIT, self.JOBS, self.DELETE, self.MEDIA, self.SUMMARY

    @cached_property
    def comments(self):
        """Notes on the translation job."""

        comments = self.fields.getvalue("comments", "").strip()
        return comments.replace("\r", "") if comments else None

    @cached_property
    def doc(self):
        """`Doc` object for the glossary document being translated."""

        id = self.fields.getvalue("doc_id")
        if not id:
            return None
        try:
            doc = Doc(self.session, id=id)
            doctype = doc.doctype.name
        except Exception:
            self.logger.exception("id %r", id)
            self.bail("Invalid document ID")
        if not doctype.lower().startswith("glossary"):
            self.bail(f"CDR{doc.id} is a {doctype} document")
        return doc

    @cached_property
    def doc_id(self):
        """Integer for the CDR ID of the glossary document being translated."""
        return self.doc.id if self.doc else None

    @cached_property
    def doc_type(self):
        """String for the name of the glossary document's CDR doctype."""
        return self.doc.doctype.name if self.doc else None

    @cached_property
    def doc_title(self):
        """Use a GlossaryTermName title for both GTN and GTC documents."""

        if not self.doc_type:
            return None
        if self.doc_type.lower() == "glossarytermname":
            return self.doc.title.split(";")[0].strip()
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
            return f"Concept document for {title}"
        return f"Concept document CDR{self.doc_id:d}"

    @cached_property
    def missing_values(self):
        """List of required values which were not found."""

        missing = []
        for name in Job.REQUIRED:
            if not getattr(self, name):
                missing.append(Job.REQUIRED[name])
        return missing

    @cached_property
    def job(self):
        """Translation job being displayed/edited."""
        return Job(self) if self.doc_id else None

    @cached_property
    def lead_translator(self):
        """Default assignee for a new translation job."""

        group_name = "Spanish Translation Leads"
        leads = self.load_group(group_name).items
        return leads[0][0] if leads else None

    @property
    def same_window(self):
        """Don't open any more new browser tabs."""
        return self.buttons

    @cached_property
    def state_id(self):
        """Primary key for the selected translation state."""

        state_id = self.fields.getvalue("state")
        if not state_id:
            return None
        if not state_id.isdigit():
            self.bail()
        state_id = int(state_id)
        if state_id not in self.states.map:
            self.bail()
        return state_id

    @cached_property
    def states(self):
        """Valid values for the translation job states."""
        return self.load_valid_values("glossary_translation_state")

    @cached_property
    def subtitle(self):
        """What we display at the top of the page."""
        return self.job.subtitle if self.job else self.SUBTITLE

    @cached_property
    def translators(self):
        """Users who are authorized to translate glossary documents.

        Expand the list to include the translator of the current job,
        in case he/she is no long in the translation group.
        """

        translators = self.load_group("Spanish Glossary Translators")
        if self.assigned_to and self.assigned_to not in translators.map:
            translators = translators.map
            translators[self.assigned_to] = self.users[self.assigned_to]
            def key(pair): return pair[1].lower()
            return sorted(translators.items(), key=key)
        else:
            return translators.items

    @cached_property
    def users(self):
        """Dictionary of all active users.

        We need this for validating the assigned_to parameter. The set
        of currently active translators won't work for that purpose,
        because a job may have been assigned to a user who is no longer
        active, or who has been subsequently removed from the translators
        group.
        """

        query = self.Query("usr", "id", "fullname")
        query.where("fullname IS NOT NULL")
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])


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
    REQUIRED = dict(
        doc_id="Doc ID",
        state_id="Status",
        assigned_to="Assigned To",
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
    def changed(self):
        """Determine whether any fields on the editing form have been changed.

        We do this to optimize away unnecessary writes to the database.
        """

        for name in self.FIELDS:
            if getattr(self, name) != getattr(self.__control, name):
                return True
        return False

    @cached_property
    def comments(self):
        """Notes on the translation job."""
        return self.row.comments if self.row else None

    @cached_property
    def doc_id(self):
        """CDR ID for the CDR glossary document being translated."""
        return self.__control.doc_id

    @cached_property
    def doc_title(self):
        """String for the title of the glossary document."""
        return self.__control.doc_title

    @cached_property
    def doc_type(self):
        """String for the name of the glossary document's CDR doctype."""
        return self.__control.doc_type

    @cached_property
    def new(self):
        """True if we don't already have a job for this summary."""
        return False if self.row else True

    @cached_property
    def row(self):
        """Current values for an existing job, if applicable."""

        query = self.__control.Query(self.TABLE, *self.FIELDS)
        query.where(query.Condition(self.KEY, self.doc_id))
        return query.execute(self.__control.cursor).fetchone()

    @cached_property
    def state_id(self):
        """Primary key for the job's state."""
        return self.row.state_id if self.row else None

    @cached_property
    def subtitle(self):
        """Override for string displayed at the top of the page."""
        return f"Translation job for CDR{self.doc_id}"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure")
        control.bail(f"failure: {e}")
