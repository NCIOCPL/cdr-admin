#!/usr/bin/env python

"""Create publishing jobs.
"""

from functools import cached_property
from os import stat
import re
from cdrcgi import Controller
from cdr import PDQDTDPATH, PUBTYPES
from cdrapi import db
from cdrapi.docs import Doc
from cdrapi.publishing import Job


class Control(Controller):
    """Access to the database, the current session, and form-building tools."""

    SUBTITLE = "Publishing"
    LOGNAME = "publishing"
    PUBLISH = "Publish"
    MANAGE_STATUSES = "Manage Publishing Statuses"
    READONLY_PARMS = {"PubType", "SubSetName", "GroupEmailAddrs"}
    HELP = "/images/help.gif"

    def populate_form(self, page):
        """Show links or fields, depending on how far we've gotten.

        Pass:
            page - HTMLPage object on which we place the links or fields
        """

        if self.subset:

            # Ask for the individual settings for this job.
            page.form.append(page.hidden_field("system", self.system.id))
            page.form.append(page.hidden_field("subset", self.subset.name))
            if self.subset.user_can_select_docs:
                fieldset = page.fieldset("Documents to Publish")
                opts = dict(label="Enter CDR IDs", rows=3)
                field = page.textarea("docs", **opts)
                help = "Separate IDs with whitespace; 'CDR' prefix is optional"
                self.__add_help_icon(page, field, help)
                fieldset.append(field)
                page.form.append(fieldset)
            fieldset = page.fieldset("Job Options")
            yes_no = "Yes", "No"
            for p in self.subset.parameters:
                if p.name == "PubType":
                    if p.default not in PUBTYPES:
                        self.bail(f"Pub type {p.default!r} not supported")
                help = p.info.help if p.info else ""
                opts = dict(label=p.name)
                if p.default in yes_no:
                    opts["options"] = yes_no
                    opts["default"] = p.default
                    field = page.select(p.name, **opts)
                else:
                    opts["readonly"] = p.name in Control.READONLY_PARMS
                    opts["value"] = p.default or ""
                    field = page.text_field(p.name, **opts)
                self.__add_help_icon(page, field, help)
                fieldset.append(field)
            user = self.session.User(self.session, id=self.session.user_id)
            email = user.email
            if " " in email or "@" not in email:
                email = ""
            notify = "Yes" if email else "No"
            help = self.system.param_info["notify"].help
            opts = dict(options=yes_no, default=notify)
            field = page.select("notify", **opts)
            self.__add_help_icon(page, field, help)
            fieldset.append(field)
            label = "Address(es)"
            help = self.system.param_info["email"].help
            opts = dict(value=email, label="Address(es)")
            field = page.text_field("email", **opts)
            self.__add_help_icon(page, field, help)
            fieldset.append(field)
            label = "No Output"
            help = self.system.param_info["no-output"].help
            no = "No"
            opts = dict(label=label, options=yes_no, default=no)
            field = page.select("no-output", **opts)
            self.__add_help_icon(page, field, help)
            fieldset.append(field)
            page.form.append(fieldset)

        elif self.system:

            # Ask the user to pick a specific job type.
            page.form.append(page.hidden_field("system", self.system.id))
            legend = f"Select {self.system.name} Publication System Subset"
            fieldset = page.fieldset(legend)
            checked = True
            for subset in self.system.subsets:
                if subset.name != "Republish-Export":
                    description = subset.description.replace("\r", "")
                    tooltip = re.sub(r"\n\n+", "@@NL@@", description)
                    tooltip = re.sub(r"\s+", " ", tooltip)
                    tooltip = tooltip.replace("@@NL@@", "\n\n")
                    opts = dict(
                        label=subset.name,
                        value=subset.name,
                        checked=checked,
                    )
                    button = page.radio_button("subset", **opts)
                    self.__add_help_icon(page, button, tooltip)
                    fieldset.append(button)
                    checked = False
            page.form.append(fieldset)
            page.add_css("fieldset { width: 600px; }")

        else:

            # Ask the user to pick a publishing system.
            fieldset = page.fieldset("Select a Publishing System")
            checked = True
            for system in sorted(self.systems.values()):
                opts = dict(
                    label=f"{system.name} [Version {system.doc.version:d}]",
                    value=system.id,
                    checked=checked,
                )
                button = page.radio_button("system", **opts)
                self.__add_help_icon(page, button, system.description)
                checked = False
                fieldset.append(button)
            page.form.append(fieldset)
        # We're removing the dependency on jQuery, and in theory the USWDS
        # framework has comparable tooltip support, but right now it's broken
        # when used on the label for a radio button, so for now at least, we
        # are going back to inserting a "help" icon on the side of the fields
        # and radio buttons. See https://github.com/uswds/uswds/issues/6372.
        # page.add_script("jQuery(document).tooltip({show:'fold'});")

    def publish(self):
        """Create the publishing job and link to its status.

        If any problems were encountered when assembling the job's options,
        send the user back to the form.
        """

        opts = dict(
            system=self.system.name,
            subsystem=self.subset.name,
            parms=self.parameters,
            docs=self.docs,
            email=self.email,
            no_output=self.no_output,
            permissive=False,
            force=self.force,
        )
        if self.alerts:
            self.show_form()
        try:
            job_id = Job(self.session, **opts).create()
            self.logger.info("Job %d created", job_id)
            opts = dict(id=job_id, alert=f"Job {job_id} started.")
            self.redirect("PubStatus.py", **opts)
            legend = f"Job {job_id} started"
            url = f"PubStatus.py?id={job_id}"
            label = "Check the status of the publishing job."
            details = self.HTMLPage.B.P(self.HTMLPage.B.A(label, href=url))
        except Exception as e:
            self.logger.exception("Job creation failure")
            self.alerts.append(dict(
                message=f"Publishing Request Failed: {e}",
                type="error",
            ))
            self.show_form()
            details = self.HTMLPage.B.P(str(e), self.HTMLPage.B.CLASS("error"))
        page = self.HTMLPage(self.TITLE, subtitle=self.subset.name)
        fieldset = page.fieldset(legend)
        fieldset.append(details)
        page.body.append(fieldset)
        page.send()

    def run(self):
        """Overload to check permissions and to handle the publish command."""

        if not self.session.can_do("USE PUBLISHING SYSTEM"):
            self.bail("You are not authorized to use the publishing system")
        elif self.request == self.MANAGE_STATUSES:
            self.navigate_to("ManagePubStatus.py", self.session.name)
        elif self.request == self.PUBLISH:
            self.publish()
        elif self.request == self.SUBMIT:
            self.show_form()
        else:
            Controller.run(self)

    @cached_property
    def buttons(self):
        """Custom button list, as this isn't a standard report."""

        if self.subset:
            return [self.PUBLISH]
        if self.system:
            return [self.SUBMIT]
        return [self.SUBMIT, self.MANAGE_STATUSES]

    @cached_property
    def docs(self):
        """Sorted sequence of documents if explicitly provided."""

        docs = []
        value = self.fields.getvalue("docs", "")
        ids = re.findall(r"\d+", value)
        for id in sorted([int(id) for id in ids], reverse=True):
            doc = self.Candidate(self.session, id=id)
            problem = None
            if doc.is_meeting_recording:
                problem = "meeting recording"
            elif doc.is_module_only:
                problem = "summary module"
            if problem:
                self.alerts.append(dict(
                    message=f"Attempt to publish {problem} CDR{doc.id}.",
                    type="error",
                ))
            else:
                docs.append(doc)
        return docs

    @cached_property
    def email(self):
        """Address where notifications about the job should be sent."""
        return self.fields.getvalue("email") or "Do not notify"

    @cached_property
    def force(self):
        """True if inclusion of documents marked Inactive is allowed."""
        return True if self.subset.name == "Hotfix-Remove" else False

    @cached_property
    def method(self):
        """Override for the form method."""
        return "post" if self.subset else "get"

    @cached_property
    def no_output(self):
        """True: writing documents to the file system should be suppressed."""
        return self.fields.getvalue("no-output") == "Yes"

    @cached_property
    def parameters(self):
        """Dictionary of options to be passed to the job creation request."""

        parameters = {}
        for p in self.subset.parameters:
            value = self.fields.getvalue(p.name)
            if value:
                self.logger.debug("scrubbing %s value %s", p.name, value)
                info = self.system.param_info.get(p.name)
                if not info:
                    self.bail(f"Unsupported parameter {p.name!r}")
                try:
                    info.scrub(value)
                except Exception as e:
                    self.logger.exception("parameters")
                    self.bail(str(e))
                parameters[p.name] = value
        return parameters

    @cached_property
    def subset(self):
        """Publishing subset selected by the user."""

        if self.system:
            name = self.fields.getvalue("subset")
            if name:
                for subset in self.system.subsets:
                    if subset.name == name:
                        return subset
                self.bail("subset missing")
        return None

    @cached_property
    def subtitle(self):
        """String displayed immediately under the main banner."""
        return self.subset.name if self.subset else self.SUBTITLE

    @cached_property
    def same_window(self):
        """Stay on the same browser tab until job is queued."""
        return [self.SUBMIT]

    @cached_property
    def system(self):
        """Publishing system selected by the user."""

        system_id = self.fields.getvalue("system")
        if system_id:
            try:
                return self.systems[int(system_id)]
            except Exception:
                self.logger.exception("Bad system ID")
                self.bail("Bad system ID")
        return None

    @cached_property
    def systems(self):
        """Dictionary of objects for the known CDR (non-mailer) pub systems."""

        systems = {}
        query = self.Query("active_doc d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'PublishingSystem'")
        query.where("d.title <> 'Mailers'")
        rows = query.execute(self.cursor).fetchall()
        for row in rows:
            if self.session.tier.name == "PROD":
                if row.title.lower() == "qcfiltersets":
                    continue
            system = PublishingSystem(self, row)
            systems[system.id] = system
        return systems

    @staticmethod
    def __add_help_icon(page, field, description):
        """Add an icon that will bring up a tooltip with documentation.

        Pass:
            page - access to DOM-node creation tools
            field - wrapper for field's label and value elements
            description - string to be displayed in the tooltip
        """

        if description:
            opts = {
                "src": "/images/help.gif",
                "alt": "Help icon",
                "title": description.strip(),
            }
            label = field.find("label")
            icon = page.B.IMG(**opts)
            icon.set("class", "usa-tooltip margin-left-1")
            icon.set("data-position", "right")
            label.append(icon)

    class Candidate(Doc):
        """Derived class which problems in publishing candidate docs."""

        @cached_property
        def is_meeting_recording(self):
            """Is this a Media document for the recording of a board meeting?

            We don't allow publication of meeting recordings, which are
            for internal use only. The publishing queries in the control
            documents exclude those documents, but we have to make sure
            they aren't included in user-specified document lists.
            """

            query = db.Query("query_term_pub", "doc_id")
            query.where(query.Condition("doc_id", self.id))
            query.where("value = 'Internal'")
            query.where("path = '/Media/@Usage'")
            return True if query.execute(self.cursor).fetchall() else False

        @cached_property
        def is_module_only(self):
            """Is this a summary which can only be used as a module?

            We don't allow publication of summary modules, which are
            for internal use only. The publishing queries in the control
            documents exclude those documents, but we have to make sure
            they aren't included in user-specified document lists.
            """

            query = db.Query("query_term_pub", "doc_id")
            query.where(query.Condition("doc_id", self.id))
            query.where("value = 'Yes'")
            query.where("path = '/Summary/@ModuleOnly'")
            return True if query.execute(self.cursor).fetchall() else False


class PublishingSystem:
    """Settings for one of the major CDR publishing systems."""

    def __init__(self, control, row):
        """Save the caller's values.

        Pass:
            control - access to the database and the current login session
            row - values from the database query
        """

        self.control = control
        self.row = row

    def __lt__(self, other):
        """Support sorting by system name.

        Pass:
            other - reference to `PublishingSystem` we're comparing with
        """

        return self.name.lower() < other.name.lower()

    @cached_property
    def id(self):
        """CDR ID for the publishing system's control document."""
        return self.row.id

    @cached_property
    def name(self):
        """String for the publishing system's name."""
        return self.row.title

    @cached_property
    def description(self):
        """String containing the description of this system's usage."""

        node = self.doc.root.find("SystemDescription")
        return Doc.get_text(node, "").strip()

    @cached_property
    def doc(self):
        """The control document for the publishing system."""
        return Doc(self.control.session, id=self.id, version="lastp")

    @cached_property
    def param_info(self):
        """Dictionary of metadata about parameters, indexed by parm name."""

        param_info = {}
        for node in self.doc.root.findall("ParmInfoSet/ParmInfo"):
            info = self.ParamInfo(node)
            param_info[info.name] = info
        return param_info

    @cached_property
    def subsets(self):
        """Sequence of subtypes for this publishing system."""

        subsets = []
        for node in self.doc.root.findall("SystemSubset"):
            subsets.append(self.Subset(self, node))
        return subsets

    class Subset:
        """Publishing job type available from this system."""

        SPECIFICATION = "SubsetSpecifications/SubsetSpecification"
        PARAMETER = "SubsetParameters/SubsetParameter"

        def __init__(self, system, node):
            """Remember the caller's values.

            Pass:
                system - publishing system to which this subset belongs
                node - parsed XML node with the subset's information
            """

            self.system = system
            self.node = node

        @cached_property
        def control(self):
            """Access to the current CDR login session."""
            return self.system.control

        @cached_property
        def description(self):
            """String explaining how this subset is to be used."""

            description = Doc.get_text(self.node.find("SubsetDescription"), "")
            return description.strip()

        @cached_property
        def name(self):
            """String for the name of the subset."""
            return Doc.get_text(self.node.find("SubsetName"))

        @cached_property
        def parameters(self):
            """Sequence of `Parameter` objects."""

            parameters = []
            for node in self.node.findall(self.PARAMETER):
                parameters.append(self.Parameter(self, node))
            return parameters

        @cached_property
        def user_can_select_docs(self):
            """True if any specs allow the users to specify documents by id."""

            path = f"{self.SPECIFICATION}/SubsetSelection/UserSelect"
            return True if self.node.findall(path) else False

        class Parameter:
            """Option which can be specified for jobs of this type."""

            def __init__(self, subset, node):
                """Save the caller's values.

                Pass:
                    subset - publishing type using this parameter value
                    node - parsed XML node containing the parameter info
                """

                self.subset = subset
                self.node = node

            @cached_property
            def default(self):
                """Default value for the parameter."""

                default = Doc.get_text(self.node.find("ParmValue"))
                if not default and self.name == "DrupalServer":
                    return self.hosts.get("DRUPAL")
                return default

            @cached_property
            def hosts(self):
                """Dictionary of host name defaults for this tier."""
                return self.subset.control.session.tier.hosts

            @cached_property
            def info(self):
                """Help and validation information for this parameter."""
                return self.subset.system.param_info.get(self.name)

            @cached_property
            def name(self):
                """String for the parameter value's name."""
                return Doc.get_text(self.node.find("ParmName"))

    class ParamInfo:
        """Metadata about publishing job parameters.

        Used for displaying help and for scrubbing the data to
        prevent malicious tampering.
        """

        def __init__(self, node):
            """Save the caller's value.

            Pass:
                node - parsed XML node with the parameter meta data
            """

            self.node = node

        @cached_property
        def help(self):
            """String for the explanation of the parameter."""

            help = Doc.get_text(self.node.find("ParmInfoHelp"))
            return help.replace("\r", "")

        @cached_property
        def method(self):
            """Name of the method used to validate these values."""
            return Doc.get_text(self.node.find("ParmInfoMethod"))

        @cached_property
        def name(self):
            """String for the parameter's name."""
            return Doc.get_text(self.node.find("ParmInfoName"))

        @cached_property
        def pattern(self):
            """String for the regular expression used for validation."""
            return Doc.get_text(self.node.find("ParmInfoPattern"))

        @cached_property
        def values(self):
            """Strings for the parameter's valid values."""

            values = []
            path = "ParmInfoValidValues/ParmInfoValidValue"
            for node in self.node.findall(path):
                value = Doc.get_text(node, "").strip()
                if value:
                    values.append(value)
            return values

        def scrub(self, value):
            """Make sure the parameter's value hasn't been tampered with.

            Abort if it has.
            """

            failed = False
            if self.pattern and not re.match(self.pattern, value):
                failed = True
            if self.values and value not in self.values:
                failed = True
            if self.method and not getattr(self, f"_{self.method}")(value):
                failed = True
            if failed:
                raise Exception(f"invalid {self.name!r} value {value!r}")

        def _dtd(self, value):
            """
            Verify that the file named can be found in the CDR
            Licensee directory in the file system.
            """

            try:
                return True if stat(f"{PDQDTDPATH}/{value}") else False
            except Exception:
                return False

        def _integer(self, value):
            """Verify that the value is an integer string."""
            return value.isdigit()

        def _job_date(self, value):
            """Check the validity of a job date value.

            Acceptable values will be one of the following:
              * the string 'JobStartDateTime'
              * an ISO date
              * an ISO date and time (with or without seconds)
            """

            if value == "JobStartDateTime":
                return True
            pattern = r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}(:\d{2})?)?$"
            return re.match(pattern, value) and True or False

        def _pubtype(self, value):
            """Make sure the value is one of the known publishing types."""
            return value in PUBTYPES

        def _server_name(self, value):
            """Ensure that the name contains only valid DNS characters."""

            if not value:
                return True
            return True if re.match(r"^[A-Za-z0-9._-]+$", value) else False

        def _yes_no_int(self, value):
            """Make sure the value is 'Yes', 'No', or an integer."""

            if value in ("Yes", "No"):
                return True
            return value.isdigit()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("publishing failed")
        control.bail(str(e))
