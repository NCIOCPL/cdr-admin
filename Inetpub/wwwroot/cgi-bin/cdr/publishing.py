#!/usr/bin/env python

"""Create publishing jobs.
"""

from cdrcgi import Controller, navigateTo
from cdr import PDQDTDPATH, PUBTYPES
from cdrapi.docs import Doc
from cdrapi.publishing import Job
from os import stat
import re


class Control(Controller):
    """Access to the database, the current session, and form-building tools."""

    SUBTITLE = "Publishing"
    LOGNAME = "publishing"
    PUBLISH = "Publish"
    MANAGE_STATUSES = "Manage Publishing Statuses"
    READONLY_PARMS = {"PubType", "SubSetName", "GroupEmailAddrs"}
    CSS = (
        ".labeled-field label { width: 200px; }",
        "fieldset { width: 575px; }",
    )

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
                help = "Separate IDs with whitespace; 'CDR' prefix is optional"
                opts = dict(label="Enter CDR IDs", tooltip=help, rows=3)
                fieldset.append(page.textarea("docs", **opts))
                page.form.append(fieldset)
            fieldset = page.fieldset("Job Options")
            yes_no = "Yes", "No"
            for p in self.subset.parameters:
                if p.name == "PubType":
                    if p.default not in PUBTYPES:
                        self.bail(f"Pub type {p.default!r} not supported")
                help = p.info.help if p.info else ""
                opts = dict(label=p.name, tooltip=help)
                if p.default in yes_no:
                    opts["options"] = yes_no
                    opts["default"] = p.default
                    fieldset.append(page.select(p.name, **opts))
                else:
                    opts["readonly"] = p.name in Control.READONLY_PARMS
                    opts["disabled"] = p.name in Control.READONLY_PARMS
                    opts["value"] = p.default or ""
                    fieldset.append(page.text_field(p.name, **opts))
            user = self.session.User(self.session, id=self.session.user_id)
            email = user.email
            if " " in email or "@" not in email:
                email = ""
            notify = email and "Yes" or "No"
            help = self.system.param_info["notify"].help
            opts = dict(options=yes_no, default=notify, tooltip=help)
            fieldset.append(page.select("notify", **opts))
            label = "Address(es)"
            help = self.system.param_info["email"].help
            opts = dict(tooltip=help, value=email, label="Address(es)")
            fieldset.append(page.text_field("email", **opts))
            label = "No Output"
            help = self.system.param_info["no-output"].help
            no = "No"
            opts = dict(tooltip=help, label=label, options=yes_no, default=no)
            fieldset.append(page.select("no-output", **opts))
            page.form.append(fieldset)
            page.add_css("\n".join(self.CSS))

        elif self.system:

            # Ask the user to pick a specific job type.
            page.form.append(page.hidden_field("system", self.system.id))
            legend = f"Select {self.system.name} Publication System Subset"
            fieldset = page.fieldset(legend)
            checked=True
            for subset in self.system.subsets:
                if subset.name != "Republish-Export":
                    description = subset.description.replace("\r", "")
                    tooltip = re.sub(r"\n\n+", "@@NL@@", description)
                    tooltip = re.sub(r"\s+", " ", tooltip)
                    tooltip = tooltip.replace("@@NL@@", "\n\n")
                    opts = dict(
                        label=subset.name,
                        tooltip=tooltip,
                        value=subset.name,
                        checked=checked,
                    )
                    fieldset.append(page.radio_button("subset", **opts))
                    checked = False
            page.form.append(fieldset)
            page.add_css("fieldset { width: 600px; }")

        else:

            # Ask the user to pick a publishing system.
            fieldset = page.fieldset("Select a Publishing System")
            checked=True
            for system in sorted(self.systems.values()):
                opts = dict(
                    label=f"{system.name} [Version {system.doc.version:d}]",
                    tooltip=system.description,
                    value=system.id,
                    checked=checked,
                )
                fieldset.append(page.radio_button("system", **opts))
                checked = False
            page.form.append(fieldset)

    def publish(self):
        """Create the publishing job and link to its status."""

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
        try:
            job_id = Job(self.session, **opts).create()
            self.logger.info("Job %d created", job_id)
            legend = f"Job {job_id} started"
            url = f"PubStatus.py?id={job_id}"
            label = "Check the status of the publishing job."
            details = self.HTMLPage.B.P(self.HTMLPage.B.A(label, href=url))
        except Exception as e:
            self.logger.exception("Job creation failure")
            legend = "Publishing Request Failed"
            details = self.HTMLPage.B.P(str(e), self.HTMLPage.B.CLASS("error"))
        buttons = (
            self.HTMLPage.button(self.DEVMENU),
            self.HTMLPage.button(self.ADMINMENU),
            self.HTMLPage.button(self.LOG_OUT),
        )
        opts = dict(
            buttons=buttons,
            subtitle=self.subset.name,
        )
        page = self.HTMLPage(self.TITLE, **opts)
        fieldset = page.fieldset(legend)
        fieldset.append(details)
        page.body.append(fieldset)
        page.send()

    def run(self):
        """Overload to check permissions and to handle the publish command."""

        if not self.session.can_do("USE PUBLISHING SYSTEM"):
            self.bail("You are not authorized to use the publishing system")
        elif self.request == self.MANAGE_STATUSES:
            params = dict(type="Manage", id=1)
            navigateTo("PubStatus.py", self.session.name, **params)
        elif self.request == self.PUBLISH:
            self.publish()
        elif self.request == self.SUBMIT:
            self.show_form()
        else:
            Controller.run(self)

    @property
    def buttons(self):
        """Custom button list, as this isn't a standard report."""

        if not hasattr(self, "_buttons"):
            self._buttons = [self.DEVMENU, self.ADMINMENU, self.LOG_OUT]
            if self.subset:
                self._buttons.insert(0, self.PUBLISH)
            else:
                if not self.system:
                    self._buttons.insert(0, self.MANAGE_STATUSES)
                self._buttons.insert(0, self.SUBMIT)
        return self._buttons

    @property
    def docs(self):
        """Sorted sequence of documents if explicitly provided."""

        if not hasattr(self, "_docs"):
            self._docs = []
            value = self.fields.getvalue("docs", "")
            ids = re.findall(r"\d+", value)
            for doc_id in sorted([int(id) for id in ids], reverse=True):
                problem = None
                if self.__is_meeting_recording(doc_id):
                    problem = "meeting recording"
                elif self.__is_module_only(doc_id):
                    problem = "summary module"
                if problem:
                    self.bail(f"Attempt to publish {problem} CDR{doc_id}")
                self._docs.append(Doc(self.session, id=doc_id))
        return self._docs

    @property
    def email(self):
        """Address where notifications about the job should be sent."""
        return self.fields.getvalue("email") or "Do not notify"

    @property
    def force(self):
        """True if inclusion of documents marked Inactive is allowed."""
        return True if self.subset.name == "Hotfix-Remove" else False

    @property
    def no_output(self):
        """True: writing documents to the file system should be suppressed."""
        return self.fields.getvalue("no-output") == "Yes"

    @property
    def parameters(self):
        """Dictionary of options to be passed to the job creation request."""

        if not hasattr(self, "_parameters"):
            self._parameters = {}
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
                        self.bail(str(e))
                    self._parameters[p.name] = value
        return self._parameters

    @property
    def subset(self):
        """Publishing subset selected by the user."""

        if not hasattr(self, "_subset"):
            self._subset = None
            if self.system:
                name = self.fields.getvalue("subset")
                if name:
                    for subset in self.system.subsets:
                        if subset.name == name:
                            self._subset = subset
                            break
                    if not self._subset:
                        self.bail("subset missing")
        return self._subset

    @property
    def subtitle(self):
        """String displayed immediately under the main banner."""
        return self.subset.name if self.subset else self.SUBTITLE

    @property
    def system(self):
        """Publishing system selected by the user."""

        if not hasattr(self, "_system"):
            self._system = None
            system_id = self.fields.getvalue("system")
            if system_id:
                try:
                    self._system = self.systems[int(system_id)]
                except Exception:
                    self.logger.exception("Bad system ID")
                    self.bail("Bad system ID")
        return self._system

    @property
    def systems(self):
        """Dictionary of objects for the known CDR (non-mailer) pub systems."""

        if not hasattr(self, "_systems"):
            self._systems = {}
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
                self._systems[system.id] = system
        return self._systems

    def __is_meeting_recording(self, doc_id):
        """Is this a Media document for the recording of a board meeting?

        We don't allow publication of meeting recordings, which are
        for internal use only. The publishing queries in the control
        documents exclude those documents, but we have to make sure
        they aren't included in user-specified document lists.

        Pass:
            doc_id - integer for the ID of a document to be published

        Return:
            True if this is an internal meeting recording, otherwise False
        """

        query = self.Query("query_term_pub", "doc_id")
        query.where(query.Condition("doc_id", doc_id))
        query.where("value = 'Internal'")
        query.where("path = '/Media/@Usage'")
        return True if query.execute(self.cursor).fetchall() else False

    def __is_module_only(self, doc_id):
        """Is this a summary which can only be used as a module?

        We don't allow publication of summary modules, which are
        for internal use only. The publishing queries in the control
        documents exclude those documents, but we have to make sure
        they aren't included in user-specified document lists.

        Pass:
            doc_id - integer for the ID of a document to be published

        Return:
            True if this is summary module, otherwise False
        """

        query = self.Query("query_term_pub", "doc_id")
        query.where(query.Condition("doc_id", doc_id))
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

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Support sorting by system name.

        Pass:
            other - reference to `PublishingSystem` we're comparing with
        """

        return self.name.lower() < other.name.lower()

    @property
    def id(self):
        """CDR ID for the publishing system's control document."""
        return self.__row.id

    @property
    def name(self):
        """String for the publishing system's name."""
        return self.__row.title

    @property
    def control(self):
        """Access to the database and the current CDR login session."""
        return self.__control

    @property
    def description(self):
        """String containing the description of this system's usage."""

        if not hasattr(self, "_description"):
            node = self.doc.root.find("SystemDescription")
            self._description = Doc.get_text(node, "").strip()
        return self._description

    @property
    def doc(self):
        """The control document for the publishing system."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id, version="lastp")
        return self._doc

    @property
    def param_info(self):
        """Dictionary of metadata about parameters, indexed by parm name."""

        if not hasattr(self, "_param_info"):
            self._param_info = {}
            for node in self.doc.root.findall("ParmInfoSet/ParmInfo"):
                info = self.ParamInfo(node)
                self._param_info[info.name] = info
        return self._param_info

    @property
    def subsets(self):
        """Sequence of subtypes for this publishing system."""

        if not hasattr(self, "_subsets"):
            self._subsets = []
            for node in self.doc.root.findall("SystemSubset"):
                self._subsets.append(self.Subset(self, node))
        return self._subsets


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

            self.__system = system
            self.__node = node

        @property
        def control(self):
            """Access to the current CDR login session."""
            return self.system.control

        @property
        def description(self):
            """String explaining how this subset is to be used."""

            if not hasattr(self, "_description"):
                node = self.__node.find("SubsetDescription")
                self._description = Doc.get_text(node, "")
            return self._description

        @property
        def name(self):
            """String for the name of the subset."""

            if not hasattr(self, "_name"):
                self._name = Doc.get_text(self.__node.find("SubsetName"))
            return self._name

        @property
        def parameters(self):
            """Sequence of `Parameter` objects."""

            if not hasattr(self, "_parameters"):
                self._parameters = []
                for node in self.__node.findall(self.PARAMETER):
                    self._parameters.append(self.Parameter(self, node))
            return self._parameters

        @property
        def system(self):
            """Publishing control system to which this subset belongs."""
            return self.__system

        @property
        def user_can_select_docs(self):
            """True if any specs allow the users to specify documents by id."""

            if not hasattr(self, "_user_can_select_docs"):
                self._user_can_select_docs = False
                path = f"{self.SPECIFICATION}/SubsetSelection/UserSelect"
                if self.__node.findall(path):
                    self._user_can_select_docs = True
            return self._user_can_select_docs


        class Parameter:
            """Option which can be specified for jobs of this type."""

            def __init__(self, subset, node):
                """Save the caller's values.

                Pass:
                    subset - publishing type using this parameter value
                    node - parsed XML node containing the parameter info
                """

                self.__subset = subset
                self.__node = node

            @property
            def default(self):
                """Default value for the parameter."""

                if not hasattr(self, "_default"):
                    self._default = Doc.get_text(self.__node.find("ParmValue"))
                    if not self._default:
                        if self.name == "GKServer":
                            self._default = self.hosts.get("GK")
                        elif self.name == "DrupalServer":
                            self._default = self.hosts.get("DRUPAL")
                return self._default

            @property
            def hosts(self):
                """Dictionary of host name defaults for this tier."""

                if not hasattr(self, "_hosts"):
                    self._hosts = self.__subset.control.session.tier.hosts
                return self._hosts

            @property
            def info(self):
                """Help and validation information for this parameter."""

                return self.__subset.system.param_info.get(self.name)

            @property
            def name(self):
                """String for the parameter value's name."""

                if not hasattr(self, "_name"):
                    self._name = Doc.get_text(self.__node.find("ParmName"))
                return self._name


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

            self.__node = node

        @property
        def help(self):
            """String for the explanation of the parameter."""

            if not hasattr(self, "_help"):
                help = Doc.get_text(self.__node.find("ParmInfoHelp"))
                self._help = help.replace("\r", "")
            return self._help

        @property
        def method(self):
            """Name of the method used to validate these values."""

            if not hasattr(self, "_method"):
                node = self.__node.find("ParmInfoMethod")
                self._method = Doc.get_text(node)
            return self._method

        @property
        def name(self):
            """String for the parameter's name."""

            if not hasattr(self, "_name"):
                self._name = Doc.get_text(self.__node.find("ParmInfoName"))
            return self._name

        @property
        def pattern(self):
            """String for the regular expression used for validation."""

            if not hasattr(self, "_pattern"):
                node = self.__node.find("ParmInfoPattern")
                self._pattern = Doc.get_text(node)
            return self._pattern

        @property
        def values(self):
            """Strings for the parameter's valid values."""

            if not hasattr(self, "_values"):
                self._values = []
                path = "ParmInfoValidValues/ParmInfoValidValue"
                for node in self.__node.findall(path):
                    value = Doc.get_text(node, "").strip()
                    if value:
                        self._values.append(value)
            return self._values

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
            return value in cdr.PUBTYPES

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
    "Don't execute the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.bail(str(e))
