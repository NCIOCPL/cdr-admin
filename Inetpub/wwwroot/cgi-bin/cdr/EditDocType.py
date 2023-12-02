#!/usr/bin/env python

"""Create a new CDR document type or modify an existing one.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi import db
from cdrapi.docs import Doc, Doctype


class Control(Controller):
    """Top-level logic for editing interface."""

    EDIT_DOCTYPES = "EditDocTypes.py"
    DOCTYPE_MENU = "Document Type Menu"
    SAVE_CHANGES = "Save Changes"
    SAVE_NEW = "Save New Document Type"
    DELETE = "Delete Document Type"
    ELEMENT = "{http://www.w3.org/2001/XMLSchema}element"
    LOGNAME = "EditDocType"

    def delete(self):
        """Delete the current document type and return to the parent menu."""

        try:
            self.doctype.delete()
            self.return_to_doctypes_menu(self.doctype.name)
        except Exception as e:
            self.alerts.append(dict(message=str(e), type="error"))
            self.show_form()

    def populate_form(self, page):
        """Add the field sets and custom style rules to the page.

        Pass:
            page - HTMLPage object to be filled out
        """

        # Add the text and picklist fields, disabling the date fields).
        fieldset = page.fieldset("Document Type Settings")
        if self.doctype.name:
            opts = dict(value=self.doctype.name)
            fieldset.append(page.hidden_field("doctype", **opts))
            opts = dict(value=self.doctype.name, disabled=True, label="Name")
            fieldset.append(page.text_field("name", **opts))
            opts = dict(value=str(self.doctype.created)[:10], disabled=True)
            fieldset.append(page.text_field("created", **opts))
            opts["value"] = (str(self.doctype.schema_mod or ""))[:10]
            fieldset.append(page.text_field("modified", **opts))
        else:
            fieldset.append(page.text_field("doctype", label="Name"))
        opts = dict(options=self.formats, default=self.doctype.format)
        fieldset.append(page.select("format", **opts))
        opts = dict(options=self.schemas, default=self.doctype.schema)
        fieldset.append(page.select("schema", **opts))
        opts = dict(
            options=self.title_filters,
            default=self.doctype.title_filter,
        )
        fieldset.append(page.select("title_filter", **opts))
        opts = dict(value=self.doctype.comment, rows=5)
        fieldset.append(page.textarea("comment", **opts))
        page.form.append(fieldset)

        # Add a second field set for the checkbox options.
        fieldset = page.fieldset("Options")
        label = "Documents of this type can be versioned"
        opts = dict(value="versioning", label=label)
        if self.doctype.versioning == "Y":
            opts["checked"] = True
        fieldset.append(page.checkbox("options", **opts))
        label = "Documents of this type can be versioned"
        opts = dict(value="active", label="Document type is active")
        if self.doctype.active == "Y":
            opts["checked"] = True
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)

        # The last "fieldset" is read-only information about valid values.
        if self.doctype.id:
            try:
                if self.doctype.vv_lists:
                    fieldset = page.fieldset("Valid Values")
                    dl = page.B.DL()
                    for name in sorted(self.doctype.vv_lists, key=str.lower):
                        dl.append(page.B.DT(name))
                        # pylint: disable-next=unsubscriptable-object
                        for value in self.doctype.vv_lists[name]:
                            dl.append(page.B.DD(value))
                    fieldset.append(dl)
                    page.form.append(fieldset)
                    page.add_css("dt { font-weight: bold; }")
                    page.add_css("dd { font-style: italic; }")
            except Exception as e:
                self.logger.exception("Failure parsing vv lists")
                message = f"Valid value information is not parseable: {e}."
                self.alerts.append(dict(message=message, type="warning"))

    def return_to_doctypes_menu(self, deleted=None):
        """Go back to the menu listing all the CDR document types."""

        opts = dict(deleted=deleted) if deleted else dict(returned="true")
        self.navigate_to(self.EDIT_DOCTYPES, self.session.name, **opts)

    def run(self):
        """Override base class so we can handle the extra buttons."""

        try:
            if self.request == self.DELETE:
                return self.delete()
            elif self.request in (self.SAVE_CHANGES, self.SAVE_NEW):
                return self.save()
            elif self.request == self.DOCTYPE_MENU:
                return self.return_to_doctypes_menu()
        except Exception as e:
            self.bail(f"Failure: {e}")
        Controller.run(self)

    def save(self):
        """Save the new or modified document type object."""

        if not self.name:
            self.bail("Required name is missing")
        opts = dict(
            active=self.active,
            comment=self.comment,
            format=self.format,
            name=self.name,
            schema=self.schema,
            title_filter=self.title_filter,
            versioning=self.versioning,
        )
        if self.doctype.id:
            opts["id"] = self.doctype.id
            alert = f"Document type {self.name!r} successfully updated."
        else:
            alert = f"New document type {self.name!r} successfully added."
        self.alerts.append(dict(message=alert, type="success"))
        self.doctype = Doctype(self.session, **opts)
        self.doctype.save()
        self.show_form()

    @cached_property
    def active(self):
        """Boolean representing whether the doctype is active (Y or N)."""
        return "Y" if "active" in self.fields.getlist("options") else "N"

    @cached_property
    def buttons(self):
        """Add our custom navigation buttons."""

        if self.doctype.id:
            return [self.SAVE_CHANGES, self.DELETE, self.DOCTYPE_MENU]
        return [self.SAVE_NEW, self.DOCTYPE_MENU]

    @cached_property
    def comment(self):
        """Get the comment value from the form field."""
        return self.fields.getvalue("comment")

    @property
    def doctype(self):
        """Object for the CDR document type being edited/created."""

        if not hasattr(self, "_doctype"):
            self._doctype = Doctype(self.session, name=self.name)
        return self._doctype

    @doctype.setter
    def doctype(self, value):
        """Allow replacement after a save."""
        self._doctype = value

    @cached_property
    def format(self):
        """Value from the form's format field."""
        return self.fields.getvalue("format")

    @cached_property
    def formats(self):
        """CDR document formats (e.g., xml)."""
        return Doctype.list_formats(self.session)

    @cached_property
    def name(self):
        """Current value of the form's name field."""
        return self.fields.getvalue("doctype")

    @cached_property
    def same_window(self):
        """Don't open any new browser tabs."""
        return self.buttons

    @cached_property
    def schema(self):
        """Selected value from the schema picklist."""
        return self.fields.getvalue("schema")

    @cached_property
    def schemas(self):
        """Top-level CDR schemas."""

        query = db.Query("document d", "d.id").order("d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'schema'")
        schemas = []
        for row in query.execute(self.cursor).fetchall():
            doc = Doc(self.session, id=row.id)
            if doc.root.find(self.ELEMENT) is not None:
                schemas.append(doc.title)
        return schemas

    @cached_property
    def subtitle(self):
        """Dynamic string for display under the main banner."""

        if self.doctype.name:
            return f"Edit {self.doctype.name} Document Type"
        return "Adding New Document Type"

    @cached_property
    def title_filter(self):
        """Value from the title filter picklist."""
        return self.fields.getvalue("title_filter")

    @cached_property
    def title_filters(self):
        """Filters used to generate titles for documents of given types."""
        return Doctype.list_title_filters(self.session)

    @cached_property
    def versioning(self):
        """Boolean representing whether versioning is supported (Y or N)."""
        return "Y" if "versioning" in self.fields.getlist("options") else "N"


if __name__ == "__main__":
    """Don't execute the script if we've been loaded as a module."""
    Control().run()
