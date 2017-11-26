#----------------------------------------------------------------------
#
# Publishing CGI script.
#
# BZIssue::2533
# BZIssue::4870
# BZIssue::5051 - [Media] Modify Publishing Software to Process Audio Files
# 2015-07-11 - Completely rewritten to address security vulnerabilities
# OCECDR-4034: Prevent Modules from Being Published Automatically
#
#----------------------------------------------------------------------
import cdr
import cdr2gk
import cdrdb
import cdrcgi
import cgi
import lxml.etree as etree
import os
import re
import urllib

class Control:
    """
    Object used to determine how to respond to the client's request.
    Collects parameters used to invoke the script and scrubs them.
    """

    readonly_parms = set(["PubType", "SubSetName", "GroupEmailAddrs"])
    "Parameters that can't be overridden by the user."

    def __init__(self):
        """
        Load the control information used to process the user's requests
        and generate the next page. Make sure the user's account is
        authorized to use the publishing system.
        """
        self.confirmed = self.need_user_choices = self.need_confirmation = False
        self.user_choices = {}
        self.cursor = cdrdb.connect("CdrPublishing").cursor()
        self.title = "CDR Administration"
        self.script = "publishing.py"
        self.systems = []
        self.system_names = {}
        self.system_ids = {}
        query = cdrdb.Query("active_doc d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", "PublishingSystem"))
        rows = query.order("d.title").execute(self.cursor).fetchall()
        for doc_id, doc_title in rows:
            title = doc_title.upper().strip()
            if title == "MAILERS":
                continue
            if cdr.isProdHost() and title == "QCFILTERSETS":
                continue
            system = PublishingSystem(self.cursor, doc_id)
            self.systems.append(system)
            self.system_names[system.name] = system
            self.system_ids[system.system_id] = system
        self.load_parameters()
        self.pageopts = {
            "subtitle": "Publishing",
            "action": self.script,
            "buttons": (cdrcgi.MAINMENU, "Log Out"),
            "session": self.session,
            "body_classes": "admin-menu"
        }

    def load_parameters(self):
        """
        Load the CGI parameters, including the session ID, the
        publishing system and subset (if selected). Abort if the
        user is not authorized to use this script. Invoked by the
        object's constructor. Redirect elsewhere if so requested.
        """
        self.fields = cgi.FieldStorage()
        self.session = cdrcgi.getSession(self.fields)
        self.request = cdrcgi.getRequest(self.fields)
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", self.session)
        elif self.request == "Log Out":
            cdrcgi.logout(session)
        if not cdr.canDo(self.session, "USE PUBLISHING SYSTEM"):
            message = "You are not authorized to use the publishing system."
            raise Exception(message)
        self.system = self.subset = None
        system_id = self.fields.getvalue("system")
        if system_id:
            try:
                system_id = int(system_id)
            except:
                raise Exception("invalid publishing system ID")
            self.system = self.system_ids.get(system_id)
            if not self.system:
                raise Exception("requested publishing system disappeared")
            subset_name = self.fields.getvalue("subset")
            if subset_name:
                self.subset = self.system.subset_names.get(subset_name)
                if not self.subset:
                    raise Exception("requested publishing subset not found")
                if self.request == "Publish":
                    self.confirmed = True
                else:
                    if self.subset.parameters:
                        self.need_user_choices = True
                    elif control.subset.user_can_select_docs:
                        self.need_user_choices = True
                    else:
                        self.need_confirmation = True
                    if self.need_user_choices:
                        self.user_choices = self.collect_user_choices()
                        if self.user_choices:
                            self.need_user_choices = False
                            self.need_confirmation = True

    def collect_user_choices(self):
        """
        Pack up the user choices (including an optional list of IDs for
        documents to be published) so they can be passed along in a
        hidden variable on the confirmation page. Make sure the values
        haven't been tampered with. Reverse sort the document ID list
        so newer documents get published first. Invoked by load_parameters().
        """
        choices = {}
        doc_ids = re.findall(r"\d+", self.fields.getvalue("doc_ids", ""))
        if doc_ids:
            choices["doc_ids"] = sorted([int(d) for d in doc_ids], reverse=True)
        for p in self.subset.parameters:
            value = self.get_scrubbed_value(p.name)
            if value:
                choices[p.name] = value
        return choices

    def get_scrubbed_value(self, name):
        """
        Get a CGI value by name and make sure it hasn't been tampered with.
        Invoked by collect_user_choices().
        """
        value = self.fields.getvalue(name) or u""
        if not value:
            return value
        info = self.system.param_info.get(name)
        if not info:
            raise Exception("Unsupported parameter %s" % repr(name))
        info.scrub(value)
        return value

    def run(self):
        """
        Processing sequence (separate invocations for each step):
          1. user selects one of the publishing systems
          2. user selects a publishing subset from the selected system
          3. user chooses settable options (if appropriate)
          4. user confirms job request
          5. publishing job is created status link is given to the user
        """
        if self.confirmed:
            self.create_publishing_job()
        elif self.need_confirmation:
            self.request_confirmation()
        elif self.need_user_choices:
            self.offer_choices()
        elif self.system:
            self.show_subsets()
        else:
            self.show_publishing_systems()

    def show_publishing_systems(self):
        """
        Put up the page from which the user will select one of the
        publishing systems. We also include (at the top) a link to
        the page for managing the status of an existing publishing
        job (most frequently this is used to release the job to
        push the results of an export job to Cancer.gov's GateKeeper).
        The bogus parameter for a job ID on this link is needed
        because of a bug in the PubStatus.py script. Invoked by
        the run() method.
        """
        page = cdrcgi.Page(self.title, **self.pageopts)
        page.add(page.B.H3("Publication Types"))
        page.add("<ol>")
        page.add_menu_link("PubStatus.py", "Manage Publishing Job Status",
                           self.session, type="Manage", id=1)
        args = { cdrcgi.SESSION: self.session }
        for system in self.systems:
            label = "%s [Version %d]" % (system.name, system.system_version)
            args["system"] = system.system_id
            url = "%s?%s" % (self.script, urllib.urlencode(args))
            link = page.B.A(label, href=url)
            br = page.B.BR()
            br.tail = system.description
            link.append(br)
            page.add(page.B.LI(link))
        page.add("</ol>")
        page.send()

    def show_subsets(self):
        """
        Display the page from which the user will select one of the
        publishing job sub-types for which to request a new job.
        Suppress the Republish-Export sub type (invoked elsewhere?).
        Invoked by the run() method.
        """
        page = cdrcgi.Page(self.title, **self.pageopts)
        page.add_css(".description { font-size: 10pt; margin: 1em 0 0 -1em; }")
        page.add(page.B.H3("%s Publication System Subsets" % self.system.name))
        page.add("<ol>")
        description_class = page.B.CLASS("description")
        args = {
            cdrcgi.SESSION: self.session,
            "system": self.system.system_id
        }
        for subset in self.system.subsets:
            if subset.name == "Republish-Export":
                continue
            args["subset"] = subset.name
            url = "%s?%s" % (self.script, urllib.urlencode(args))
            link = page.B.A(subset.name, href=url)
            description = subset.description.replace("\n", cdrcgi.NEWLINE)
            description = page.B.PRE(description, description_class)
            page.add(page.B.LI(link, description))
        page.add("</ol>")
        page.send()

    def offer_choices(self):
        """
        Display the page on which the user will choose specific documents
        to be published, or set options for the publishing job, or both.
        The options (oddly called "SubsetParameters" in the control document)
        are optional according to the schema, but in practice there has
        never been a publishing sub type which didn't have some user-
        settable options. Invoked by the run() method.
        """
        buttons = ("Submit",) + self.pageopts["buttons"]
        subtitle = "Publishing Options For %s Job" % self.subset.name
        self.pageopts["buttons"] = buttons
        self.pageopts["subtitle"] = subtitle
        page = cdrcgi.Page(self.title, **self.pageopts)
        page.add_hidden_field("system", self.system.system_id)
        page.add_hidden_field("subset", self.subset.name)
        if self.subset.user_can_select_docs:
            help = "Separate IDs with whitespace; 'CDR' prefix is optional"
            selector = ".ids .labeled-field textarea"
            page.add_css(" %s { height: 100px; width: 360px; }" % selector)
            page.add_css(" .ids .labeled-field label { width: 115px; }")
            page.add("<fieldset class='ids'>")
            page.add(page.B.LEGEND("Documents to Publish"))
            page.add_textarea_field("doc_ids", "Enter CDR IDs", tooltip=help)
            page.add("</fieldset>")
        if self.subset.parameters:
            page.add_css(".opts .labeled-field label { width: 180px; }")
            page.add("<fieldset class='opts'>")
            page.add(page.B.LEGEND("Job Options"))
            for p in self.subset.parameters:
                if p.name == "PubType":
                    if p.default not in cdr.PUBTYPES:
                        raise Exception("PubType %s not supported" %
                                        repr(p.default))
                info = p.get_info()
                help = info and info.get_help() or ""
                if p.default in ("Yes", "No"):
                    page.add_select(p.name, p.name, ("Yes", "No"), p.default,
                                    tooltip=help)
                else:
                    readonly = p.name in Control.readonly_parms
                    page.add_text_field(p.name, p.name, value=p.default or "",
                                        disabled=readonly, tooltip=help)
            page.add("</fieldset>")
        page.send()

    def request_confirmation(self):
        """
        Ask the user to confirm the publishing job request. We also
        ask the user for some last-minute decisions about the job.
        It's not clear why those decisions are not included with
        the options displayed on the previous screen, but this is
        the way it's always been done. :-)
        Invoked by the run() method.
        """
        buttons = ("Publish",) + self.pageopts["buttons"]
        subtitle = "Confirming Submission For %s Job" % self.subset.name
        email = cdr.getEmail(self.session) or ""
        if " " in email or "@" not in email:
            email = ""
        notify = email and "Yes" or "No"
        self.pageopts["buttons"] = buttons
        self.pageopts["subtitle"] = subtitle
        page = cdrcgi.Page(self.title, **self.pageopts)
        page.add_hidden_field("system", self.system.system_id)
        page.add_hidden_field("subset", self.subset.name)
        page.add_hidden_field("user-opts", repr(self.user_choices))
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Confirmation Settings"))
        page.add_select("notify", "Notify", ("Yes", "No"), notify,
                        tooltip=self.system.param_info["notify"].get_help())
        page.add_text_field("email", "Address(es)", value=email,
                            tooltip=self.system.param_info["email"].get_help())
        page.add_select("no-output", "No Output", ("Yes", "No"), "No",
                        tooltip=self.system.param_info["no-output"].get_help())
        page.add("</fieldset>")
        page.send()

    def create_publishing_job(self):
        """
        Invoke the cdr.publish command and tell the user if we succeeded.
        If so, provide a link to the page showing the job's status.
        Otherwise, explain what went wrong. Invoked by the run() method.
        """
        try:
            user_opts = eval(self.fields.getvalue("user-opts", "{}"))
        except Exception:
            raise Exception("tampering with CGI parameters detected")
        parameters = self.collect_parameters(user_opts)
        doc_ids = self.collect_doc_ids(user_opts.get("doc_ids", []))
        inactive_ok = self.subset.name == "Hotfix-Remove" and "Y" or "N"
        no_output = self.fields.getvalue("no-output") == "Yes" and "Y" or "N"
        if self.fields.getvalue("notify") == "Yes":
            email = self.fields.getvalue("email")
        else:
            email = "Do not notify"
        args = self.session, self.system.name, self.subset.name
        opts = dict(
            parms=parameters,
            docList=doc_ids,
            email=email,
            noOutput=no_output,
            allowInActive=inactive_ok
        )
        response = cdr.publish(*args, **opts)
        job_id, errors = response
        self.pageopts["subtitle"] = self.subset.name
        page = cdrcgi.Page(self.title, **self.pageopts)
        if job_id:
            page.add(page.B.H3("Job %s Started" % job_id))
            label = "Check the status of the publishing job"
            url = "PubStatus.py?id=%s" % job_id
            page.add(page.B.A(label, href=url))
        else:
            page.add(page.B.H3("Publishing Request Failed"))
            page.add(page.B.P(errors))
        page.send()

    def collect_parameters(self, user_opts):
        """
        Repackage the sequence of job settings to be passed to the
        CdrPublish command. Check for invalid values (possibly caused
        by malicious tampering). Invoked by create_publishing_job().
        """
        parameters = []
        for name in user_opts:
            if name != "doc_ids":
                info = self.system.param_info.get(name)
                if not info:
                    raise Exception("Unexpected parameter %s" % repr(name))
                value = user_opts[name]
                info.scrub(value)
                parameters.append((name, value))
        return parameters

    def collect_doc_ids(self, doc_ids):
        """
        Repackage the list of document IDs to be passed to the
        CdrPublish command. Abort if we detect an attempt to
        publish a meeting recording document or tampering with
        the CGI parameter. Invoked by create_publishing_job().
        """
        id_list = []
        for doc_id in doc_ids:
            if not isinstance(doc_id, int):
                raise Exception("Detected tampering with document ID list")
            if self.is_meeting_recording(doc_id):
                raise Exception("Attempt to publish meeting recording "
                                "CDR%s" % doc_id)
            if self.is_module_only(doc_id):
                raise Exception("Attempt to publish a summary module "
                                "CDR%s" % doc_id)
            id_list.append("CDR%s" % doc_id)
        return id_list

    def is_meeting_recording(self, doc_id):
        """
        We don't allow publication of meeting recordings, which are
        for internal use only. The publishing queries in the control
        documents exclude those documents, but we have to make sure
        they aren't included in user-specified document lists.
        Invoked by collect_doc_ids().
        """
        query = cdrdb.Query("query_term_pub", "doc_id")
        query.where(query.Condition("doc_id", doc_id))
        query.where(query.Condition("value", "Internal"))
        query.where(query.Condition("path", "/Media/@Usage"))
        return query.execute(self.cursor).fetchall() and True or False


    def is_module_only(self, doc_id):
        """
        We don't allow summary modules, which are
        for internal use only. The publishing queries in the control
        documents exclude those documents, but we have to make sure
        they aren't included in user-specified document lists.
        Invoked by collect_doc_ids().
        """
        query = cdrdb.Query("query_term_pub", "doc_id")
        query.where(query.Condition("doc_id", doc_id))
        query.where(query.Condition("value", "Yes"))
        query.where(query.Condition("path", "/Summary/@ModuleOnly"))
        return query.execute(self.cursor).fetchall() and True or False
class PublishingSystem:
    """
    Object containing instructions for each of the types of publishing
    jobs available for a given publishing system.
    """

    def __init__(self, cursor, system_id, system_version=None):
        """
        Load the publishing control document for the specified
        CDR document ID and extract the information about the
        publishing system defined therein, including the system
        name and description, as well as the publishing job
        sub-types (commonly referred to as "subsets"). We also
        load the information for validating and explaining each
        of the choices (called "parameters" here) which the user
        make for publishing jobs.
        """
        self.system_id = system_id
        self.system_version = system_version
        self.name = self.description = None
        self.subsets = []
        self.subset_names = {}
        self.param_info = {}
        if not self.system_version:
            query = cdrdb.Query("doc_version", "MAX(num)")
            query.where(query.Condition("publishable", "Y"))
            query.where(query.Condition("id", self.system_id))
            rows = query.execute(cursor).fetchall()
            if not rows:
                raise Exception("No publishable version of CDR%d found" %
                                self.system_id)
            self.system_version = rows[0][0]
        query = cdrdb.Query("doc_version", "xml")
        query.where(query.Condition("id", self.system_id))
        query.where(query.Condition("num", self.system_version))
        rows = query.execute(cursor).fetchall()
        if not rows:
            raise Exception("Version %s of document %s not found" %
                            (repr(self.system_id), repr(self.system_version)))
        root = etree.XML(rows[0][0].encode("utf-8"))
        self.name = root.find("SystemName").text.strip()
        for node in root.findall("SystemDescription"):
            self.description = node.text.strip()
        for node in root.findall("SystemSubset"):
            subset = PublishingSystem.Subset(self, node)
            self.subsets.append(subset)
            self.subset_names[subset.name] = subset
        for node in root.findall("ParmInfoSet/ParmInfo"):
            info = PublishingSystem.ParamInfo(node)
            self.param_info[info.name] = info

    class Subset:
        """
        A type of publishing job which can be created by the
        publishing system represented by the control document
        being parsed.
        """

        def __init__(self, system, node):
            """
            Extract the publishing job type's information from
            the control document's SystemSubset block.
            """
            self.system = system
            self.name = self.description = None
            self.user_can_select_docs = False
            self.parameters = []
            self.specifications = []
            for child in node.findall("SubsetName"):
                self.name = child.text
            for child in node.findall("SubsetDescription"):
                self.description = child.text
            for child in node.findall("SubsetParameters/SubsetParameter"):
                parameter = PublishingSystem.Subset.Parameter(self, child)
                self.parameters.append(parameter)
            path = "SubsetSpecifications/SubsetSpecification/SubsetSelection"
            if node.findall("%s/UserSelect" % path):
                self.user_can_select_docs = True

        class Parameter:
            """
            Holds the name and default value for an option
            available for publishing jobs of this type.
            """

            def __init__(self, subset, node):
                """
                Extract the information for a job option which can
                be used by this job type from the SubsetParameter
                block.
                """
                self.subset = subset
                self.name = self.default = None
                for child in node.findall("ParmName"):
                    self.name = child.text
                for child in node.findall("ParmValue"):
                    self.default = child.text
                if self.name == "GKServer" and not self.default:
                    self.default = cdr2gk.host

            def get_info(self):
                """
                Find and return the help and validation information
                for this parameter.
                """
                return self.subset.system.param_info.get(self.name)

    class ParamInfo:
        """
        Metadata about publishing job parameters. Used for displaying help
        and for scrubbing the data to prevent malicious tampering.
        """

        def __init__(self, node):
            "Parse the name, help, and validation info from the DOM node."
            self.name = self.help = self.pattern = self.method = None
            self.values = None
            for child in node:
                if child.tag == "ParmInfoName":
                    self.name = child.text.strip()
                elif child.tag == "ParmInfoHelp":
                    self.help = child.text.strip()
                elif child.tag == "ParmInfoPattern":
                    self.pattern = child.text
                elif child.tag == "ParmInfoMethod":
                    self.method = child.text
                elif child.tag == "ParmInfoValidValues":
                    self.values = [v.text for v in child]

        def get_help(self):
            """
            Return a version of the help string that will survive
            the indenting performed by the cdrcgi.Page object.
            """
            if self.help:
                help = self.help.replace("\r", "")
                return help.replace("\n", cdrcgi.NEWLINE)
            return ""

        def scrub(self, value):
            """
            Make sure the parameter's value hasn't been tampered with.
            Abort if it has.
            """
            failed = False
            if self.pattern and not re.match(self.pattern, value):
                failed = True
            if self.values and value not in self.values:
                failed = True
            if self.method and not getattr(self, self.method)(value):
                failed = True
            if failed:
                why = "invalid %s value %s" % (repr(self.name), repr(value))
                raise Exception(why)

        def yes_no_int(self, value):
            "Make sure the value is 'Yes', 'No', or an integer."
            if value in ("Yes", "No"):
                return True
            return value.isdigit()

        def dtd(self, value):
            """
            Verify that the file named can be found in the CDR
            Licensee directory in the file system.
            """
            try:
                path = r"%s\%s" % (cdr.PDQDTDPATH, value)
                return os.stat(path) and True or False
            except Exception, e:
                return False

        def job_date(self, value):
            """
            Ensure that the value contains one of the following:
              * the string 'JobStartDateTime'
              * an ISO date
              * an ISO date and time (with or without seconds)
            """
            if value == "JobStartDateTime":
                return True
            pattern = r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}(:\d{2})?)?$"
            return re.match(pattern, value) and True or False

        def integer(self, value):
            "Verify that the value is an integer string"
            return value.isdigit()

        def pubtype(self, value):
            "Make sure the value is one of the known publishing types"
            return value in cdr.PUBTYPES

        def server_name(self, value):
            """
            If the value is not empty, make sure it doesn't contain
            any unexpected characters.
            """
            if not value:
                return True
            return re.match(r"^[A-Za-z0-9._-]+$", value) and True or False

def main():
    "Wrap up the top-level driver so we can use the classes separately."
    try:
        control = Control()
        control.run()
    except Exception, e:
        cdrcgi.bail(str(e))

if __name__ == "__main__":
    main()
