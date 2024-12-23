#!/usr/bin/env python

"""Republish CDR documents to Cancer.gov.
"""

from functools import cached_property
from cdrcgi import Controller
from RepublishDocs import CdrRepublisher
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and form-building tools."""

    SUBTITLE = "Re-Publish CDR Documents to Cancer.gov"
    INSTRUCTIONS = (
        "This page can be used to request re-publishing of CDR documents "
        "which have already been sent to Cancer.gov, in a way which "
        "bypasses the optimization which normally prevents pushing of "
        "an unchanged document to the Cancer.gov web site.",
        "You may enter one or more CDR Document IDs, and/or one or "
        "more publishing Job IDs.  Separate multiple ID values with "
        "spaces.  You may also select a Document Type. "
        "If you select a document type you may indicate that all "
        "publishable documents of that type are to be included; "
        "otherwise, only those documents which are already in the "
        "pub_proc_cg table will be published.  If a document type "
        "is not selected this flag is ignored.  You may also indicate "
        "that in addition to those documents selected for the document "
        "IDs, job IDs, and document type provided, the new publishing "
        "document should also identify and include documents which are "
        "the target of links from the base set of documents to be published, "
        "and are not already on Cancer.gov.  Finally, when you specify "
        "one or more job IDs you can indicate that only documents from "
        "those jobs marked as 'Failed' are to be included. "
        "If no job IDs are entered, this flag is ignored.",
        "An export job will be created for generating the "
        "output suitable for publishing. This job, if successful, "
        "will in turn create a second job for pushing the "
        "exported jobs to Cancer.gov.",
        "You may optionally add an Email Address to which "
        "status notifications for the progress of the new publishing "
        "jobs will be sent, with links to pages with additional "
        "information about the status for the jobs.",
    )

    def populate_form(self, page):
        """Ask the user for the request parameters.

        Pass:
            page - HTMLPage object on which to draw the form
        """

        if not self.session.can_do("USE PUBLISHING SYSTEM"):
            self.bail("You are not authorized to use the publishing system")
        fieldset = page.fieldset("Instructions")
        for paragraph in self.INSTRUCTIONS:
            fieldset.append(page.B.P(paragraph))
        page.form.append(fieldset)
        fieldset = page.fieldset("Request Parameters")
        fieldset.append(page.text_field("docs", label="Doc IDs"))
        fieldset.append(page.text_field("jobs", label="Job IDs"))
        opts = dict(label="Doc Type", options=[""]+self.doctypes)
        fieldset.append(page.select("doctype", **opts))
        opts = dict(label="Email", value=self.email)
        fieldset.append(page.text_field("email", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        opts = dict(value="all", label="Include all documents for type")
        fieldset.append(page.checkbox("options", **opts))
        label = "Include linked documents not on Cancer.gov"
        opts = dict(value="linked", label=label)
        fieldset.append(page.checkbox("options", **opts))
        label = "Only include failed documents from specified publishing jobs"
        opts = dict(value="failed", label=label)
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Submit the job and re-draw the form."""

        # Make sure we have what we need.
        if not self.session.can_do("USE PUBLISHING SYSTEM"):
            self.bail("You are not authorized to use the publishing system")
        if not (self.docs or self.jobs or self.doctype):
            self.alerts.append(dict(
                message="Document(s), job(s), or document type required.",
                type="error",
            ))
        else:
            try:

                # Submit the job.
                republisher = CdrRepublisher(self.session.name)
                args = (
                    self.include_linked_documents,
                    self.docs,
                    self.jobs,
                    self.doctype,
                    self.include_all_documents_for_type,
                    self.include_only_failed_documents,
                    self.email,
                )
                job_id = str(republisher.republish(*args))

                # Tell the user that the job has been queued.
                page = self.form_page
                link = page.menu_link("PubStatus.py", job_id, id=job_id)
                link.set("target", "_blank")
                self.alerts.append(dict(
                    message=("Export job ", link, " created successfully."),
                    type="success",
                ))
            except Exception as e:
                self.logger.exception("Republish failure: %s", e)
                self.alerts.append(dict(
                    message=f"Republish request failed: {e}",
                    type="error",
                ))

        # Re-draw the form.
        self.show_form()

    @cached_property
    def docs(self):
        """Sequence of document ID for the docs to be republished."""

        try:
            docs = self.fields.getvalue("docs", "").split()
            return [Doc.extract_id(doc) for doc in docs]
        except Exception:
            self.logger.exception("failure parsing IDs")
            self.bail("invalid document IDs")

    @cached_property
    def doctype(self):
        """Document type name selected from the form, if any."""

        doctype = self.fields.getvalue("doctype") or None
        if doctype and doctype not in self.doctypes:
            self.bail()
        return doctype

    @cached_property
    def doctypes(self):
        """Document type names for the form picklist.

        It doesn't make sense, but adding a second column to the results
        set speeds up the query by orders of magnitude.
        """

        query = self.Query("doc_type t", "t.name", "d.doc_type").unique()
        query.order("t.name")
        query.join("document d", "d.doc_type = t.id")
        query.join("pub_proc_cg c", "c.id = d.id")
        rows = query.execute(self.cursor).fetchall()
        return [row.name for row in rows if row.name != "Person"]

    @cached_property
    def email(self):
        """Email address to which we send notification of request outcome."""

        email = self.fields.getvalue("email")
        if email:
            return email
        return self.session.User(self.session, id=self.session.user_id).email

    @cached_property
    def include_all_documents_for_type(self):
        """Boolean indicating whether to do a full doctype republish."""
        return True if "all" in self.options else False

    @cached_property
    def include_linked_documents(self):
        """True: add documents which are linked from the original set."""
        return True if "linked" in self.options else False

    @cached_property
    def include_only_failed_documents(self):
        """True means ignore successful docs and just republish failures."""
        return True if "failed" in self.options else False

    @cached_property
    def jobs(self):
        """Sequence of job IDs for the jobs to be republished."""

        try:
            jobs = self.fields.getvalue("jobs", "").split()
            return [int(job) for job in jobs]
        except Exception:
            self.bail("invalid job IDs")

    @cached_property
    def options(self):
        """Sequence of checked checkbox options."""
        return self.fields.getlist("options")

    @cached_property
    def same_window(self):
        """Only open a new browser tab once."""
        return [self.SUBMIT] if self.request else []


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
