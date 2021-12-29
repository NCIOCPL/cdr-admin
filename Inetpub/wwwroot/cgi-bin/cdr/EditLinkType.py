#!/usr/bin/env python

"""Create a new CDR link type or edit an existing one.
"""

from cdrcgi import Controller, navigateTo
from cdrapi.docs import Doctype, LinkType
from lxml import html


class Control(Controller):
    """Access to the current session and form-building tools."""

    SUBTITLE = "Link Control"
    LOGNAME = "link-control"
    SAVE = "Save"
    TYPES = "Link Types"
    CANCEL = "Cancel"
    DELETE = "Delete"
    SKIP = "Filter", "schema", "PublishingSystem", "TermSet", "xxtest"
    VERSIONS = (
        ("P", "Published version"),
        ("V", "Any version"),
        ("C", "Current working document")
    )
    CSS = "/stylesheets/EditLinkType.css"
    JS = "/js/EditLinkType.js"

    def run(self):
        """Override the top-level entry point, as this isn't a report."""

        try:
            if self.request == self.SAVE:
                self.save()
            elif self.request == self.CANCEL:
                navigateTo("EditLinkControl.py", self.session.name)
            elif self.request == self.DELETE:
                self.delete()
            else:
                Controller.run(self)
        except Exception as e:
            self.logger.exception("link type editing failure")
            self.bail(str(e))

    def delete(self):
        """Delete the link type and go the menu page for link types."""

        self.linktype.delete()
        navigateTo("EditLinkControl.py", self.session.name)

    def save(self):
        """Save a new or modified link type, then display the form again."""

        opts = dict(
            name=self.name,
            sources=self.sources,
            targets=self.targets,
            properties=self.rules,
            chk_type=self.version,
            comment=self.comment,
        )
        if not opts["name"]:
            self.errors.append("Missing required name")
        else:
            id = self.linktypes.get(opts["name"].lower())
            if id:
                if not self.linktype or self.linktype.id != id:
                    self.errors.append(f"Name {self.name} already in use")
        if not self.sources:
            self.errors.append("Missing required source(s)")
        if not self.targets:
            self.errors.append("Missing required target(s)")
        if self.version not in "PVC":
            self.errors.append("Invalid version type")
        if self.errors:
            self.show_form()
        if self.linktype:
            opts["id"] = self.linktype.id
            message = f"Saved changes to link type {self.name}"
        else:
            message = f"added new link type {self.name}"
        linktype = LinkType(self.session, **opts)
        try:
            linktype.save()
            self.messages.append(message)
        except Exception as e:
            self.logger.exception("Failure saving link type %s", self.name)
            self.errors.append(f"Failure saving link type {self.name}: {e}")

        # Force re-load of the link type values.
        del self._linktype
        self.show_form()

    def populate_form(self, page):
        """Add the fields to the editing form.

        Pass:
            page - HTMLPage object on which the fields are placed
        """

        id = self.linktype.id if self.linktype else None
        page.form.append(page.hidden_field("id", id))
        classes = "center warning strong"
        for message in self.messages:
            page.form.append(page.B.P(message, page.B.CLASS(classes)))
        if self.errors:
            page.form.append(self.make_error_block())
            source_list = self.sources
            rule_list = self.rules
            targets = self.targets
        else:
            source_list = self.linktype.sources if self.linktype else []
            rule_list = self.linktype.properties if self.linktype else []
            targets = self.linktype.targets if self.linktype else {}
        sources = []
        rules = []
        targets = [t.name for t in targets.values()]
        for s in sorted(source_list):
            sources.append((s.doctype.name, s.element))
        for r in rule_list:
            rules.append((r.name, r.value, r.comment))
        if not sources:
            sources = [("", "")]
        if not rules:
            rules = [("", "", "")]
        page.form.append(self.make_identification_block())
        counter = 1
        for source in sources:
            page.form.append(self.make_source_block(counter, *source))
            counter += 1
        page.form.append(self.make_target_block(targets))
        for rule in rules:
            page.form.append(self.make_rule_block(counter, *rule))
            counter += 1
        opts = dict(pretty_print=True, encoding="unicode")
        fieldset = self.make_source_block("@@COUNTER@@")
        e_template = html.tostring(fieldset, **opts)
        fieldset = self.make_rule_block("@@COUNTER@@")
        r_template = html.tostring(fieldset, **opts)
        js = f"var templates = {{'e': `{e_template}`, 'r': `{r_template}`}};"
        page.add_script(js)
        page.head.append(page.B.SCRIPT(src=self.JS))
        page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))

    def make_error_block(self):
        """Create a box showing the errors preventing the save request."""

        B = self.HTMLPage.B
        fieldset = self.HTMLPage.fieldset("Errors")
        fieldset.set("class", "errors")
        ul = B.UL()
        for error in self.errors:
            ul.append(B.LI(error, B.CLASS("errors")))
        fieldset.append(ul)
        return fieldset

    def make_identification_block(self):
        """Create the simple fields for the link type."""

        if self.errors:
            name = self.name
            comment = self.comment
            version = self.version
        else:
            name = self.linktype.name if self.linktype else ""
            comment = self.linktype.comment if self.linktype else ""
            version = self.linktype.chk_type if self.linktype else "P"
        fieldset = self.HTMLPage.fieldset("Link Type Properties")
        fieldset.append(self.HTMLPage.text_field("name", value=name))
        fieldset.append(self.HTMLPage.textarea("comment", value=comment))
        opts = dict(options=self.VERSIONS, default=version)
        fieldset.append(self.HTMLPage.select("version", **opts))
        return fieldset

    def make_rule_block(self, counter, ruletype="", text="", comment=""):
        """Create the fieldset block for a link type custom rule.

        Pass:
           counter - suffix identifying which block we are creating
           ruletype - string identifying the type of this custom rule
           text - string containing the rule's constraints
           comment - optional string describing this custom rule

        Return:
           fieldset element object
        """

        fieldset = self.HTMLPage.fieldset("Custom Rule")
        fieldset.set("id", f"block-{counter}")
        fieldset.set("class", "r-block numbered-block")
        fieldset.append(self.make_ruletype_field(counter, ruletype))
        fieldset.append(self.make_ruletext_field(counter, text))
        fieldset.append(self.make_rulecomment_field(counter, comment))
        return fieldset

    def make_rulecomment_field(self, counter, value=""):
        """Create the textarea field for this rule's optional description.

        Pass:
           counter - suffix identifying block in which the field occurs
           value - optional string for the field's current value

        Return:
           reference to object representing an HTML div wrapper containing
           the field elements
       """

        opts = dict(label="Comment", value=value or "")
        return self.HTMLPage.textarea(f"rulecomment-{counter}", **opts)

    def make_ruletext_field(self, counter, value=""):
        """Create the textarea field for this rule's constraints.

        For the syntax of the only custom rule type currently
        supported, refer to the class documentation for the
        LinkTargetContains class in cdrapi/docs.py.

        Pass:
           counter - suffix identifying block in which the field occurs
           value - optional string for the field's current value

        Return:
           reference to object representing an HTML div wrapper containing
           the field elements
        """

        name = f"ruletext-{counter}"
        help_text = 'E.g. /Term/TermType/TermTypeName == "Index term"'
        opts = dict(id=name, name=name, title=help_text)
        return self.HTMLPage.B.DIV(
            self.HTMLPage.B.LABEL(
                self.HTMLPage.B.FOR(name),
                "Rule Text",
                self.HTMLPage.B.CLASS("clickable")
            ),
            self.HTMLPage.B.TEXTAREA(value or "", **opts),
            self.HTMLPage.B.CLASS("labeled-field")
        )

    def make_ruletype_field(self, counter, ruletype=""):
        """Create the picklist for the custom rule type.

        There is currently only one supported custom rule type, named
        LinkTargetContains.

        Pass:
           counter - suffix identifying block in which the field occurs
           ruletype - optional string for currently selected rule type

        Return:
           reference to object representing an HTML div wrapper containing
           the field elements
        """

        name = f"ruletype-{counter}"
        select = self.HTMLPage.B.SELECT(name=name, id=name)
        option = self.HTMLPage.B.OPTION("Select Rule Type", value="")
        if not ruletype:
            option.set("selected")
        select.append(option)
        for t in sorted(self.ruletypes):
            option = self.HTMLPage.B.OPTION(t, value=t)
            if t == ruletype:
                option.set("selected")
            select.append(option)
        return self.HTMLPage.B.DIV(
            self.HTMLPage.B.LABEL(self.HTMLPage.B.FOR(name), "Rule Type"),
            select,
            self.HTMLPage.B.IMG(
                src="/images/add.gif",
                onclick=f"add_block({counter}, 'r')",
                alt="add rule block",
                title="Add another custom rule block"
            ),
            self.HTMLPage.B.IMG(
                src="/images/del.gif",
                onclick=f"del_block({counter}, 'r')",
                alt="drop rule block",
                title="Remove this custom rule block"
            ),
            self.HTMLPage.B.CLASS("labeled-field")
        )

    def make_source_block(self, counter, doctype="", element=""):
        """Create a fieldset with fields for a source doctype/element combo.

        Pass:
            counter - integer identifying this block/fields uniquely
            doctype - string for the name of this document type
            element - string for the name of the linking element
        """

        fieldset = self.HTMLPage.fieldset("Allowed Link Source")
        fieldset.set("id", f"block-{counter}")
        fieldset.set("class", "e-block numbered-block")
        doctypes = list(self.doctypes)
        if doctype and doctype not in doctypes:
            doctypes.append(doctype)
        doctypes = [("", "Select Document Type")] + sorted(doctypes)
        opts = dict(label="Doc Type", default=doctype, options=doctypes)
        field = self.HTMLPage.select(f"doctype-{counter}", **opts)
        image = self.HTMLPage.B.IMG(
            src="/images/add.gif",
            onclick=f"add_block({counter}, 'e')",
            alt="add element block",
            title="Add another target element block"
        )
        field.append(image)
        image = self.HTMLPage.B.IMG(
            src="/images/del.gif",
            onclick="del_block({}, 'e')".format(counter),
            alt="drop element block",
            title="Remove this target element block"
        )
        field.append(image)
        fieldset.append(field)
        opts = dict(label="Element", value=element)
        fieldset.append(self.HTMLPage.text_field(f"element-{counter}", **opts))
        return fieldset

    def make_target_block(self, targets):
        """Create a fieldset with checkboxes for allowed target doctypes.

        Pass:
            targets - sequence of names of allowed document types
        """

        fieldset = self.HTMLPage.fieldset("Allowed Link Targets")
        fieldset.set("id", "target-block")
        doctypes = list(self.doctypes)
        for target in targets:
            if target not in doctypes:
                doctypes.append(target)
        ndoctypes = len(doctypes)
        rows = ndoctypes // 2
        if ndoctypes % 2:
            rows += 1
        j = rows
        for i in range(rows):
            doctype = doctypes[i]
            checked = doctype in targets
            opts = dict(value=doctype, label=doctype, checked=checked)
            fieldset.append(self.HTMLPage.checkbox("target", **opts))
            if j < ndoctypes:
                doctype = doctypes[j]
                checked = doctype in targets
                opts = dict(value=doctype, label=doctype, checked=checked)
                fieldset.append(self.HTMLPage.checkbox("target", **opts))
                j += 1
        return fieldset

    @property
    def buttons(self):
        """Customize the action buttons at the top of the form."""

        buttons = [
            self.SAVE,
            self.CANCEL,
            self.DEVMENU,
            self.ADMINMENU,
            self.LOG_OUT,
        ]
        if self.linktype or self.request == self.SAVE and not self.errors:
            buttons.insert(2, self.DELETE)
        return buttons

    @property
    def comment(self):
        """String for the description of the link type."""
        return self.fields.getvalue("comment")

    @property
    def doctypes(self):
        """Document type names."""

        if not hasattr(self, "_doctypes"):
            self._doctypes = []
            for doctype in Doctype.list_doc_types(self.session):
                if doctype not in self.SKIP:
                    self._doctypes.append(doctype)
        return self._doctypes

    @property
    def errors(self):
        """Sequence of error messages to be displayed above the form."""

        if not hasattr(self, "_errors"):
            self._errors = []
        return self._errors

    @property
    def linktype(self):
        """Link type object select from the form."""

        if not hasattr(self, "_linktype"):
            self._linktype = None
            id = self.fields.getvalue("id")
            if id:
                self._linktype = LinkType(self.session, id=id)
        return self._linktype

    @property
    def linktypes(self):
        """Dictionary of link type IDs, indexed by lowercase name.

        Used to make sure we don't try to reuse a link type name.
        """

        if not hasattr(self, "_linktypes"):
            query = self.Query("link_type", "id", "name")
            rows = query.execute(self.cursor)
            self._linktypes = {}
            for row in rows:
                self._linktypes[row.name.lower()] = row.id
        return self._linktypes

    @property
    def messages(self):
        """Sequence of extra strings to be displayed above the form."""

        if not hasattr(self, "_messages"):
            self._messages = []
        return self._messages

    @property
    def name(self):
        """String entered on the form for the link type's name."""
        return self.fields.getvalue("name", "").strip()

    @property
    def rules(self):
        """Custom selection logic for links."""

        if not hasattr(self, "_rules"):
            self._rules = []
            for values in self.value_sets:
                name = values.get("ruletype")
                value = values.get("ruletext")
                if name or value:
                    if not name:
                        self.errors.append("Rule type not selected")
                    if not value:
                        self.errors.append("Missing rule text")
                    comment = values.get("rulecomment")
                    try:
                        args = self.session, name, value, comment
                        self._rules.append(getattr(LinkType, name)(*args))
                    except Exception as e:
                        message = f"Failure adding rule {name}: {e}"
                        self.logger.exception(message)
                        self.errors.append(message)
        return self._rules

    @property
    def ruletypes(self):
        """Available property types."""

        if not hasattr(self, "_ruletypes"):
            property_types = LinkType.get_property_types(self.session)
            self._ruletypes = [p.name for p in property_types]
        return self._ruletypes

    @property
    def sources(self):
        """Doctype/element combinations which can use this link type."""

        if not hasattr(self, "_sources"):
            sources = []
            missing_doctype = "Link source document type not selected"
            missing_element = "Missing required linking element name"
            for values in self.value_sets:
                name = values.get("doctype")
                element = values.get("element")
                if name or element:
                    if not name:
                        self.errors.append(missing_doctype)
                    if not element:
                        self.errors.append(missing_element)
                    try:
                        doctype = Doctype(self, name=name)
                        sources.append(LinkType.LinkSource(doctype, element))
                    except Exception:
                        error = f"Failure adding source {name}/{element}"
                        self.logger.exception(error)
                        self.errors.append(error)
            self._sources = sources
        return self._sources

    @property
    def subtitle(self):
        """Customize the string displayed below the main banner."""

        if self.linktype:
            return "Edit Link Type"
        return "Add Link Type"

    @property
    def targets(self):
        """Doctypes to which links of this type can point."""

        if not hasattr(self, "_targets"):
            self._targets = {}
            for name in self.fields.getlist("target"):
                doctype = Doctype(self.session, name=name)
                self._targets[doctype.id] = doctype
        return self._targets

    @property
    def value_sets(self):
        """Dictionary of values for complex multiply-occurring fields."""

        if not hasattr(self, "_value_sets"):
            sets = {}
            for key in self.fields:
                if "-" in key:
                    name, number = key.split("-", 1)
                    if number.isdigit():
                        if number not in sets:
                            sets[number] = {}
                        value = self.fields.getvalue(key)
                        sets[number][name] = value
            self._value_sets = sets.values()
        return self._value_sets

    @property
    def version(self):
        """Type of version link must use (see `LinkType.CHECK_TYPES`)."""
        return self.fields.getvalue("version")


if __name__ == "__main__":
    "Allow documentation and lint to import this without side effects"
    Control().run()
