"""
Create a new CDR link type or edit an existing one

Rewritten for OCECDR-4319 - Fix link type management interface
"""

import lxml.html
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    """
    Top-level processing logic for form
    """

    LOGNAME = "link-control"
    SAVE = "Save"
    CANCEL = "Cancel"
    DELETE = "Delete"
    SKIP = "Filter", "schema", "PublishingSystem", "TermSet", "xxtest"
    BUTTONS = SAVE, CANCEL, cdrcgi.Control.ADMINMENU, cdrcgi.Control.LOG_OUT
    VERSIONS = (
        ("P", "Published version"),
        ("V", "Any version"),
        ("C", "Current working document")
    )

    def __init__(self):
        """
        Assemble the lookup table and initialize control variables
        """

        cdrcgi.Control.__init__(self, "Link Control")
        self.doctypes = cdr.getDoctypes(self.session)
        self.ruletypes = [p.name for p in cdr.getLinkProps(self.session)]
        self.name = self.fields.getvalue("name", "")
        self.message = None
        self.linktype = None
        self.errors = []

    def run(self):
        """
        Override the top-level entry point, as this isn't a report
        """

        try:
            if self.request == self.SAVE:
                self.save()
            elif self.request == self.CANCEL:
                cdrcgi.navigateTo("EditLinkControl.py", self.session)
            elif self.request == self.DELETE:
                cdr.delLinkType(self.session, self.name)
                cdrcgi.navigateTo("EditLinkControl.py", self.session)
            else:
                cdrcgi.Control.run(self)
        except Exception as e:
            self.logger.exception("link type editing failure")
            cdrcgi.bail(str(e))

    def get_linktype(self):
        """
        Assemble the values for this link type

        The first step is to collect the form values. Then, if the
        form values are empty and we are editing an existing link
        type, we load that type's information from the database.
        If the form values are not empty, instantiate an object
        holding those values.

        Return:
            reference to a `cdr.LinkType` object
        """

        # Fetch the straightforward field values
        new_name = self.fields.getvalue("newname", "")
        target_version = self.fields.getvalue("version", "")
        comment = self.fields.getvalue("desc")
        targets = self.fields.getlist("target")

        # Collect all the multiply-occurring blocks' field values
        value_sets = {}
        for key in self.fields.keys():
            if "-" in key:
                name, number = key.split("-", 1)
                if number.isdigit():
                    if number not in value_sets:
                        value_sets[number] = {}
                    value_sets[number][name] = self.fields.getvalue(key)

        # Populate the list of link sources and custom rules from those fields
        sources = []
        rules = []
        for key in value_sets:
            values = value_sets[key]
            if "element" in values or "doctype" in values:
                element = values.get("element", "")
                doctype = values.get("doctype", "")
                if element or doctype:
                    if not element:
                        self.errors.append("Missing element")
                    if not doctype:
                        self.errors.append("Linking doctype not selected")
                    sources.append((doctype, element))
            else:
                ruletype = values.get("ruletype", "")
                ruletext = values.get("ruletext", "")
                rulecomment = values.get("rulecomment")
                if ruletype or ruletext:
                    if not ruletype:
                        self.errors.append("Rule type not selected")
                    if not ruletext:
                        self.errors.append("Missing rule text")
                    rules.append((ruletype, ruletext, rulecomment))

        # Handle the case where no editing has been performed
        if not (new_name or target_version or comment or targets or
                sources or rules):
            if self.name:
                return cdr.getLinkType(self.session, self.name)
            else:
                return cdr.LinkType("")

        # Create an object reflecting edited values
        opts = dict(
            linkSources=sources,
            linkTargets=targets,
            linkProps=rules,
            comment=comment,
            linkChkType=target_version
        )
        return cdr.LinkType(new_name, **opts)

    def save(self):
        """
        Check the type's values for errors and save them if no errors

        Chain into displaying the editing form again.
        """

        self.linktype = self.get_linktype()
        if not self.linktype.name:
            self.errors.append("Missing rule type name")
        if self.linktype.linkChkType not in "PVC":
            cdrcgi.bail(cdrcgi.TAMPERING)
        if not self.linktype.linkTargets:
            self.errors.append("No target document type(s) selected")
        if not self.linktype.linkSources:
            self.errors.append("No link sources specified")
        if not self.errors:
            action = "modlink" if self.name else "addlink"
            name = self.linktype.name
            cdr.putLinkType(self.session, self.name, self.linktype, action)
            self.linktype = cdr.getLinkType(self.session, name)
            if self.name:
                self.message = "Saved changes to link type {}".format(name)
            else:
                self.message = "Added new link type {}".format(name)
            self.name = name
        self.show_form()

    def set_form_options(self, opts):
        """
        Adjust the form's buttons and subtitle

        Pass:
           opts - dictionary of options for the form

        Return:
           reference to the modified dictionary
        """

        subtitle = "{} link type".format("Edit" if self.name else "Add")
        buttons = list(self.BUTTONS)
        if self.name:
            buttons.insert(2, self.DELETE)
        opts["buttons"] = buttons
        opts["subtitle"] = subtitle
        return opts

    def populate_form(self, form):
        """
        Add the fields to the editing form

        More complicated than the standard form, because some of the
        field sets can have more than one instance. Therefore we
        build some fields directly from the lxml Builder instead of
        using the cdrcgi wrappers.

        Pass:
           form - reference to the `cdrcgi.Page` object
        """

        classes = "center warning strong"
        if self.message:
            form.add(form.B.P(self.message, form.B.CLASS(classes)))
        self.show_errors(form)
        if self.linktype is None:
            self.linktype = self.get_linktype()
        name = self.name or ""
        form.add_hidden_field("name", name)
        name = self.linktype.name or name
        desc = self.fix(self.linktype.comment or "")
        ver = self.linktype.linkChkType or "P"
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Link Type Properties"))
        form.add_text_field("newname", "Name", value=name)
        form.add_textarea_field("desc", "Description", value=desc)
        form.add_select("version", "Version", self.VERSIONS, default=ver)
        form.add("</fieldset>")
        counter = 1
        for source in sorted(self.linktype.linkSources):
            form.add(self.make_linking_element(form, counter, *source))
            counter += 1
        if not self.linktype.linkSources:
            form.add(self.make_linking_element(form, counter))
            counter += 1
        form.add(self.make_target_block(form))
        for rule in sorted(self.linktype.linkProps):
            form.add(self.make_rule_block(form, counter, *rule))
            counter += 1
        if not self.linktype.linkProps:
            form.add(self.make_rule_block(form, counter))
            counter += 1
        element_template = self.make_linking_element(form, "@@COUNTER@@")
        rule_template = self.make_rule_block(form, "@@COUNTER@@")
        form.add_script("""\
var next_counter = %s;
var templates = {'e': `%s`, 'r': `%s`};
var descs = {'e': 'linking element', 'r': 'custom rule'};
function add_block(n, t) {
    block = templates[t].replace(/@@COUNTER@@/g, next_counter);
    jQuery(block).insertAfter('#block-' + n);
    ++next_counter;
}
function del_block(n, t) {
    if (confirm("Do you really want to delete this " + descs[t] + " block?")) {
        if (jQuery('.' + t + '-block').length < 2)
            add_block(n, t);
        jQuery('#block-' + n).remove();
    }
}
jQuery("h1 input[value='Cancel']").attr("title",
                                        "Return to menu of link types");
""" % (counter, element_template, rule_template))
        if self.name:
            form.add_script("""\
jQuery("h1 input[value='Delete']").click(function(e) {
    if (confirm("Are you sure?"))
        return true;
    e.preventDefault();
});""")
        form.add_css("""
.labeled-field img { padding-left: 15px; }
#target-block label { width: 220px; display: inline-block; padding-left: 5px; }
fieldset.errors { border-color: red; }
fieldset.errors legend { color: red; font-weight: bold; }
fieldset.errors li { color: red; font-weight: bold; }
""")

    def make_target_block(self, form):
        """
        Create the fieldset for allowable link targets

        Pass:
           form - reference to the `cdrcgi.Page` object

        Return:
           serialized HTML fieldset element
        """

        wrapper = form.B.DIV(id="target-block")
        doctypes = list(self.doctypes)
        for t in self.SKIP:
            doctypes.remove(t)
        for t in self.linktype.linkTargets:
            if t not in doctypes:
                doctypes.append(t)
        doctypes = sorted(doctypes)
        ndoctypes = len(doctypes)
        rows = ndoctypes / 2
        if ndoctypes % 2:
            rows += 1
        j = rows
        for i in range(rows):
            self.add_target(form, wrapper, doctypes[i])
            if j < ndoctypes:
                self.add_target(form, wrapper, doctypes[j])
                j += 1
        fieldset = form.B.FIELDSET(
            form.B.LEGEND("Allowed Link Targets"),
            wrapper
        )
        return lxml.html.tostring(fieldset)

    def add_target(self, form, wrapper, doctype):
        """
        Add a checkbox and its label for an allowed target document type

        Pass:
           form - reference to the `cdrcgi.Page` object
           wrapper - reference to object for HTML div wrapper
           doctype - string naming a CDR document type
        """

        elem_id = "target-{}".format(doctype.lower())
        opts = {
            "type": "checkbox",
            "name": "target",
            "value": doctype,
            "id": elem_id
        }
        if doctype in self.linktype.linkTargets:
            opts["checked"] = "checked"
        wrapper.append(form.B.INPUT(**opts))
        wrapper.append(form.B.LABEL(form.B.FOR(elem_id), doctype))

    def make_rule_block(self, form, counter, ruletype="", text="", comment=""):
        """
        Create the fieldset block for a link type custom rule

        Pass:
           form - reference to the `cdrcgi.Page` object
           counter - suffix identifying which block we are creating
           ruletype - string identifying the type of this custom rule
           text - string containing the rule's constraints
           comment - optional string describing this custom rule

        Return:
           serialized HTML fieldset element
        """

        fieldset = form.B.FIELDSET(
            form.B.LEGEND("Custom Rule"),
            self.make_ruletype_field(form, counter, ruletype),
            self.make_ruletext_field(form, counter, text),
            self.make_rulecomment_field(form, counter, comment),
            form.B.CLASS("r-block"),
            id="block-{}".format(counter)
        )
        return lxml.html.tostring(fieldset)

    def make_linking_element(self, form, counter, doctype="", element=""):
        """
        Create the fieldset block for an allowable link source element

        Pass:
           form - reference to the `cdrcgi.Page` object
           counter - suffix identifying which block we are creating
           doctype - string identifying the selected document type, if any
           element - string naming one of the elements from which links
                     are allowed from this document type

        Return:
           serialized HTML fieldset element
        """

        fieldset = form.B.FIELDSET(
            form.B.LEGEND("Allowed Link Source"),
            self.make_doctype_field(form, counter, doctype),
            self.make_element_field(form, counter, element),
            form.B.CLASS("e-block"),
            id="block-{}".format(counter)
        )
        return lxml.html.tostring(fieldset)

    def make_doctype_field(self, form, counter, doctype=""):
        """
        Create the picklist for an allowed link source's document type

        Pass:
           form - reference to the `cdrcgi.Page` object
           counter - suffix identifying block in which the field occurs
           doctype - string identifying the selected document type, if any

        Return:
           reference to object representing an HTML div wrapper containing
           the field elements
        """

        name = "doctype-{}".format(counter)
        select = form.B.SELECT(name=name, id=name)
        option = form.B.OPTION("Select Document Type", value="")
        if not doctype:
            option.set("selected", "selected")
        select.append(option)
        if doctype and doctype not in self.doctypes:
            option = form.B.OPTION(doctype, value=doctype, selected="selected")
            select.append(option)
        for t in sorted(self.doctypes):
            if not t:
                t = ""
            option = form.B.OPTION(t, value=t)
            if t == doctype:
                option.set("selected", "selected")
            select.append(option)
        return form.B.DIV(
            form.B.LABEL(form.B.FOR(name), "Doc Type"),
            select,
            form.B.IMG(
                src="/images/add.gif",
                onclick="add_block({}, 'e')".format(counter),
                alt="add element block",
                title="Add another target element block"
            ),
            form.B.IMG(
                src="/images/del.gif",
                onclick="del_block({}, 'e')".format(counter),
                alt="drop element block",
                title="Remove this target element block"
            ),
            form.B.CLASS("labeled-field")
        )

    def make_element_field(self, form, counter, value=""):
        """
        Create the text field for an element allowed as a link source

        Pass:
           form - reference to the `cdrcgi.Page` object
           counter - suffix identifying block in which the field occurs
           value - name of the element from which links are allowed

        Return:
           reference to object representing an HTML div wrapper containing
           the field elements
        """

        if not value:
            value = ""
        name = "element-{}".format(counter)
        return form.B.DIV(
            form.B.LABEL(
                form.B.FOR(name),
                "Element",
                form.B.CLASS("clickable")
            ),
            form.B.INPUT(id=name, name=name, value=value),
            form.B.CLASS("labeled-field")
        )

    def make_ruletype_field(self, form, counter, ruletype=""):
        """
        Create the picklist for the custom rule type

        There is currently only one supported custom rule type, named
        LinkTargetContains.

        Pass:
           form - reference to the `cdrcgi.Page` object
           counter - suffix identifying block in which the field occurs
           ruletype - optional string for currently selected rule type

        Return:
           reference to object representing an HTML div wrapper containing
           the field elements
        """

        name = "ruletype-{}".format(counter)
        select = form.B.SELECT(name=name, id=name)
        option = form.B.OPTION("Select Rule Type", value="")
        if not ruletype:
            option.set("selected", "selected")
        select.append(option)
        for t in sorted(self.ruletypes):
            option = form.B.OPTION(t, value=t)
            if t == ruletype:
                option.set("selected", "selected")
            select.append(option)
        return form.B.DIV(
            form.B.LABEL(form.B.FOR(name), "Rule Type"),
            select,
            form.B.IMG(
                src="/images/add.gif",
                onclick="add_block({}, 'r')".format(counter),
                alt="add rule block",
                title="Add another custom rule block"
            ),
            form.B.IMG(
                src="/images/del.gif",
                onclick="del_block({}, 'r')".format(counter),
                alt="drop rule block",
                title="Remove this custom rule block"
            ),
            form.B.CLASS("labeled-field")
        )

    def make_ruletext_field(self, form, counter, value=""):
        """
        Create the textarea field for this rule's constraints

        For the syntax of the only custom rule type currently
        supported, refer to the class documentation for the
        LinkTargetContains class in cdrapi/docs.py.

        Pass:
           form - reference to the `cdrcgi.Page` object
           counter - suffix identifying block in which the field occurs
           value - optional string for the field's current value

        Return:
           reference to object representing an HTML div wrapper containing
           the field elements
        """

        if not value:
            value = ""
        else:
            value = self.fix(value)
        name = "ruletext-{}".format(counter)
        help_text = 'E.g. /Term/TermType/TermTypeName == "Index term"'
        return form.B.DIV(
            form.B.LABEL(
                form.B.FOR(name),
                "Rule Text",
                form.B.CLASS("clickable")
            ),
            form.B.TEXTAREA(value, id=name, name=name, title=help_text),
            form.B.CLASS("labeled-field")
        )

    def make_rulecomment_field(self, form, counter, value=""):
        """
        Create the textarea field for this rule's optional description

        Pass:
           form - reference to the `cdrcgi.Page` object
           counter - suffix identifying block in which the field occurs
           value - optional string for the field's current value

        Return:
           reference to object representing an HTML div wrapper containing
           the field elements
        """

        if not value:
            value = ""
        name = "rulecomment-{}".format(counter)
        return form.B.DIV(
            form.B.LABEL(
                form.B.FOR(name),
                "Comment",
                form.B.CLASS("clickable")
            ),
            form.B.TEXTAREA(self.fix(value), id=name, name=name),
            form.B.CLASS("labeled-field")
        )

    def show_errors(self, form):
        """
        Add a box at the top to display error messages if there are any

        Pass:
           form - reference to the `cdrcgi.Page` object
        """

        if not self.errors:
            return
        errors = form.B.UL()
        for error in self.errors:
            errors.append(form.B.LI(error))
        fieldset = form.B.FIELDSET(
            form.B.LEGEND("Errors"),
            errors,
            form.B.CLASS("errors")
        )
        form.add(fieldset)

    @staticmethod
    def fix(string):
        """
        Protect textarea value from garbling by cdrcgi's indenting code

        Pass:
           string - field value to be protected

        Return:
           value with newlines replaced by placeholders
        """

        return string.replace("\r", "").replace("\n", cdrcgi.NEWLINE)

Control().run()
