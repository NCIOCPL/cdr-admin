#!/usr/bin/env python

"""Republish CDR documents to Cancer.gov.
"""

from cdrcgi import Controller
from RepublishDocs import CdrRepublisher
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and form-building tools."""

    SUBTITLE = "Re-Publish CDR Documents to Cancer.gov"
    INSTRUCTIONS = (
        "This page can be used to request re-publishing of CDR documents "
        "which have already been sent to Cancer.gov, in a way which "
        "bypasses the optimization which normally prevents sending of "
        "an unchanged document to the Cancer.gov GateKeeper program.",
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
        "exported jobs to the GateKeeper at Cancer.gov.",
        "You may optionally add an Email Address to which "
        "status notifications for the progress of the new publishing "
        "jobs will be sent, with links to pages with additional "
        "information about the status for the jobs.",
        "Specify the fully qualified domain name or IP address for "
        "the GateKeeper host to which the republishing job is to be "
        "directed if it is not the default host for the CDR server "
        "from which the request originates.",
    )

    def populate_form(self, page):
        """Ask the user for the request parameters.

        Pass:
            page - HTMLPage object on which to draw the form
        """

        fieldset = page.fieldset("Instructions")
        for paragraph in self.INSTRUCTIONS:
            fieldset.append(page.B.P(paragraph))
        page.form.append(fieldset)
        fieldset = page.fieldset("Request Parameters")
        fieldset.append(page.text_field("docs", label="Doc IDs"))
        fieldset.append(page.text_field("jobs", label="Job IDs"))
        opts = dict(label="Doc Type", options=[""]+self.doctypes)
        fieldset.append(page.text_field("doctype", **opts))
        opts = dict(label="Email", value=self.email)
        fieldset.append(page.text_field("email", **opts))
        fieldset.append(page.text_field("host", label="GK Host"))
        opts = dict(label="GK Target", value="Live")
        fieldset.append(page.text_field("target", **opts))
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
        """Re-draw the form, with a description of the request outcome."""
        self.show_form()

    @property
    def buttons(self):
        """Customize button list to add the developer menu."""
        return self.SUBMIT, self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @property
    def docs(self):
        """Sequence of document ID for the docs to be republished."""

        if not hasattr(self, "_docs"):
            try:
                docs = self.fields.getvalue("docs", "").split()
                self._docs = [Doc.extract_id(doc) for doc in docs]
            except Exception:
                self.logger.exception("failure parsing IDs")
                self.bail("invalid document IDs")
        return self._docs

    @property
    def doctype(self):
        """Document type name selected from the form, if any."""

        if not hasattr(self, "_doctype"):
            self._doctype = self.fields.getvalue("doctype") or None
            if self._doctype and self._doctype not in self.doctypes:
                self.bail()
        return self._doctype

    @property
    def doctypes(self):
        """Document type names for the form picklist.

        It doesn't make sense, but adding a second column to the results
        set speeds up the query by orders of magnitude.
        """

        if not hasattr(self, "_doctypes"):
            query = self.Query("doc_type t", "t.name", "d.doc_type").unique()
            query.order("t.name")
            query.join("document d", "d.doc_type = t.id")
            query.join("pub_proc_cg c", "c.id = d.id")
            rows = query.execute(self.cursor).fetchall()
            self._doctypes = [row.name for row in rows if row.name != "Person"]
        return self._doctypes

    @property
    def email(self):
        """Email address to which we send notification of request outcome."""

        if not hasattr(self, "_email"):
            self._email = self.fields.getvalue("email")
            if not self._email:
                user = self.session.User(self.session, id=self.session.user_id)
                self._email = user.email
        return self._email

    @property
    def gatekeeper_host(self):
        """Optional GateKeeper host name entered on the form."""
        return self.fields.getvalue("host")

    @property
    def gatekeeper_target(self):
        """Optional GateKeeper target name entered on the form."""
        return self.fields.getvalue("target")

    @property
    def include_all_documents_for_type(self):
        """Boolean indicating whether to do a full doctype republish."""
        return True if "all" in self.options else False

    @property
    def include_linked_documents(self):
        """True: add documents which are linked from the original set."""
        return True if "linked" in self.options else False

    @property
    def include_only_failed_documents(self):
        """True means ignore successful docs and just republish failures."""
        return True if "failed" in self.options else False

    @property
    def jobs(self):
        """Sequence of job IDs for the jobs to be republished."""

        if not hasattr(self, "_jobs"):
            try:
                jobs = self.fields.getvalue("jobs", "").split()
                self._jobs = [int(job) for job in jobs]
            except:
                self.bail("invalid job IDs")
        return self._jobs

    @property
    def options(self):
        """Sequence of checked checkbox options."""

        if not hasattr(self, "_options"):
            self._options = self.fields.getlist("options")
        return self._options

    @property
    def subtitle(self):
        """String to be displayed under the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.request != self.SUBMIT:
                self._subtitle = self.SUBTITLE
            elif not (self.docs or self.jobs or self.doctype):
                self._subtitle = self.SUBTITLE
            else:
                try:
                    republisher = CdrRepublisher(self.session.name)
                    args = (
                        self.include_linked_documents,
                        self.docs,
                        self.jobs,
                        self.doctype,
                        self.include_all_documents_for_type,
                        self.include_only_failed_documents,
                        self.email,
                        self.gatekeeper_host,
                        self.gatekeeper_target,
                    )
                    job_id = republisher.republish(*args)
                    subtitle = f"Export job {job_id:d} created successfully"
                except Exception as e:
                    self.logger.exception("Republish failure: %s", e)
                    subtitle = f"Republish request failed: {e}"
                self._subtitle = subtitle
        return self._subtitle


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
