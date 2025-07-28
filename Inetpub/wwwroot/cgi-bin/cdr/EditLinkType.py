#!/usr/bin/env python

"""Create a new CDR link type or edit an existing one.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doctype, LinkType
from lxml import html


class Control(Controller):
    """Access to the current session and form-building tools."""

    LOGNAME = "link-control"
    SAVE = "Save"
    TYPES = "Link Types"
    EDIT_LINKS = "EditLinkControl.py"
    CANCEL = "Cancel"
    DELETE = "Delete"
    SKIP = "Filter", "schema", "PublishingSystem", "TermSet", "xxtest"
    VERSIONS = (
        ("P", "Published version"),
        ("V", "Any version"),
        ("C", "Current working document")
    )
    JS = "/js/EditLinkType.js"

    def delete(self):
        """Delete the link type and go the menu page for link types."""

        self.linktype.delete()
        self.return_to_link_menu(self.name)

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
        fieldset.set("class", "r-block numbered-block usa-fieldset")
        legend = fieldset.find("legend")
        button = self.HTMLPage.B.SPAN(
            self.HTMLPage.B.IMG(
                self.HTMLPage.B.CLASS("clickable"),
                src="/images/add.gif",
                onclick=f"add_block({counter}, 'r')",
                alt="add rule block",
                title="Add another custom rule block"
            ),
            self.HTMLPage.B.CLASS("image-button")
        )
        legend.append(button)
        button = self.HTMLPage.B.SPAN(
            self.HTMLPage.B.IMG(
                self.HTMLPage.B.CLASS("clickable"),
                src="/images/del.gif",
                onclick=f"del_block({counter}, 'r')",
                alt="drop rule block",
                title="Remove this custom rule block"
            ),
            self.HTMLPage.B.CLASS("image-button")
        )
        legend.append(button)
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
        opts = dict(tooltip=help_text, value=value, label="Rule Text")
        opts["widget_id"] = name
        return self.HTMLPage.textarea(name, **opts)

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
        options = [("", "Select Rule Type")] + sorted(self.ruletypes)
        opts = dict(label="Rule Type", default=ruletype, options=options)
        return self.HTMLPage.select(name, **opts)

    def make_source_block(self, counter, doctype="", element=""):
        """Create a fieldset with fields for a source doctype/element combo.

        Pass:
            counter - integer identifying this block/fields uniquely
            doctype - string for the name of this document type
            element - string for the name of the linking element
        """

        fieldset = self.HTMLPage.fieldset("Allowed Link Source")
        fieldset.set("id", f"block-{counter}")
        fieldset.set("class", "e-block numbered-block usa-fieldset")
        legend = fieldset.find("legend")
        button = self.HTMLPage.B.SPAN(
            self.HTMLPage.B.IMG(
                self.HTMLPage.B.CLASS("clickable"),
                src="/images/add.gif",
                onclick=f"add_block({counter}, 'e')",
                alt="add element block",
                title="Add another target element block"
            ),
            self.HTMLPage.B.CLASS("image-button")
        )
        legend.append(button)
        button = self.HTMLPage.B.SPAN(
            self.HTMLPage.B.IMG(
                self.HTMLPage.B.CLASS("clickable"),
                src="/images/del.gif",
                onclick=f"del_block({counter}, 'e')",
                alt="drop element block",
                title="Remove this target element block"
            ),
            self.HTMLPage.B.CLASS("image-button")
        )
        legend.append(button)
        doctypes = list(self.doctypes)
        if doctype and doctype not in doctypes:
            doctypes.append(doctype)
        doctypes = [("", "Select Document Type")] + sorted(doctypes)
        opts = dict(label="Doc Type", default=doctype, options=doctypes)
        fieldset.append(self.HTMLPage.select(f"doctype-{counter}", **opts))
        opts = dict(label="Element", value=element)
        fieldset.append(self.HTMLPage.text_field(f"element-{counter}", **opts))
        return fieldset

    def make_target_block(self, targets):
        """Create a fieldset with checkboxes for allowed target doctypes.

        Pass:
            targets - sequence of names of allowed document types
        """

        Page = self.HTMLPage
        fieldset = Page.fieldset("Allowed Link Targets")
        fieldset.set("id", "target-block")
        doctypes = list(self.doctypes)
        for target in targets:
            if target not in doctypes:
                doctypes.append(target)
        ul = Page.B.UL()
        for doctype in sorted(doctypes, key=str.lower):
            opts = dict(value=doctype, label=doctype)
            if doctype in targets:
                opts["checked"] = True
            ul.append(Page.B.LI(Page.checkbox("target", **opts)))
        fieldset.append(ul)
        return fieldset

    def populate_form(self, page):
        """Add the fields to the editing form.

        Pass:
            page - HTMLPage object on which the fields are placed
        """

        id = self.linktype.id if self.linktype else ""
        page.form.append(page.hidden_field("id", id))
        if self.errors:
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
        page.add_css("""\
.image-button { margin-left: .5rem; }
#target-block ul { column-width: 13rem; list-style-type: none; }
#target-block ul li:first-child div { margin-top: -.75rem; }
""")

    def return_to_link_menu(self, deleted=None):
        """Go back to the menu listing all the link types."""

        opts = dict(deleted=deleted) if deleted else dict(returned="true")
        self.navigate_to(self.EDIT_LINKS, self.session.name, **opts)

    def run(self):
        """Override the top-level entry point, as this isn't a report."""

        try:
            if self.request == self.SAVE:
                self.save()
            elif self.request == self.CANCEL:
                self.return_to_link_menu()
            elif self.request == self.DELETE:
                self.delete()
            else:
                Controller.run(self)
        except Exception as e:
            self.logger.exception("link type editing failure")
            self.bail(str(e))

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
                if not self.linktype or int(self.linktype.id) != id:
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
            message = f"Saved changes to link type {self.name}."
        else:
            message = f"Added new link type {self.name}."
        linktype = LinkType(self.session, **opts)
        try:
            linktype.save()
            self.messages.append(message)
        except Exception as e:
            self.logger.exception("Failure saving link type %s", self.name)
            self.errors.append(f"Failure saving link type {self.name}: {e}")

        # Force re-load of the link type values.
        self.linktype = LinkType(self.session, name=self.name)
        self.show_form()

    @cached_property
    def alerts(self):
        """Assemble the alerts from the errors and messages lists."""

        alerts = []
        for error in self.errors:
            alerts.append(dict(message=error, type="error"))
        for message in self.messages:
            alerts.append(dict(message=message, type="success"))
        return alerts

    @cached_property
    def buttons(self):
        """Customize the action buttons at the top of the form."""

        if self.linktype:
            return self.SAVE, self.DELETE, self.CANCEL
        return self.SAVE, self.CANCEL

    @cached_property
    def comment(self):
        """String for the description of the link type."""
        return self.fields.getvalue("comment")

    @cached_property
    def doctypes(self):
        """Pruned list of document type names."""

        doctypes = Doctype.list_doc_types(self.session)
        return [t for t in doctypes if t not in self.SKIP]

    @cached_property
    def errors(self):
        """Populated as we encounter problems."""
        return []

    @cached_property
    def linktype(self):
        """Object for the Link type selected from the linking menu."""

        id = self.fields.getvalue("id")
        if id:
            return LinkType(self.session, id=id)
        return None

    @cached_property
    def linktypes(self):
        """Dictionary of link type IDs, indexed by lowercase name.

        Used to make sure we don't try to reuse a link type name.
        """

        query = self.Query("link_type", "id", "name")
        linktypes = {}
        for row in query.execute(self.cursor):
            linktypes[row.name.lower()] = row.id
        return linktypes

    @cached_property
    def messages(self):
        """Populated as we process saves."""
        return []

    @cached_property
    def name(self):
        """String entered on the form for the link type's name."""
        return self.fields.getvalue("name", "").strip()

    @cached_property
    def rules(self):
        """Custom selection logic for links."""

        rules = []
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
                    rules.append(getattr(LinkType, name)(*args))
                except Exception as e:
                    message = f"Failure adding rule {name}: {e}"
                    self.logger.exception(message)
                    self.errors.append(message)
        return rules

    @property
    def ruletypes(self):
        """Available property types."""

        if not hasattr(self, "_ruletypes"):
            property_types = LinkType.get_property_types(self.session)
            self._ruletypes = [p.name for p in property_types]
        return self._ruletypes

    @cached_property
    def same_window(self):
        """Don't open any more browser tabs."""
        return self.buttons

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
