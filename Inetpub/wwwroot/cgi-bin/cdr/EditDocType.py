#!/usr/bin/env python

"""Create a new CDR document type or modify an existing one.
"""

from cdrcgi import Controller, navigateTo, bail
from cdrapi import db
from cdrapi.docs import Doc, Doctype


class Control(Controller):
    """Top-level logic for editing interface."""

    EDIT_DOCTYPES = "EditDocTypes.py"
    SUBMENU = "Document Type Menu"
    SAVE_CHANGES = "Save Changes"
    SAVE_NEW = "Save New Document Type"
    DELETE = "Delete Document Type"
    ELEMENT = "{http://www.w3.org/2001/XMLSchema}element"
    LOGNAME = "EditDocType"

    def delete(self):
        """Delete the current document type and return to the parent menu."""
        self.doctype.delete()
        self.return_to_doctypes_menu(self.doctype.name)

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
        if self.doctype.name:
            try:
                if self.doctype.vv_lists:
                    fieldset = page.fieldset("Valid Values")
                    dl = page.B.DL()
                    for name in sorted(self.doctype.vv_lists, key=str.lower):
                        dl.append(page.B.DT(name))
                        for value in self.doctype.vv_lists[name]:
                            dl.append(page.B.DD(value))
                    fieldset.append(dl)
                    page.form.append(fieldset)
            except Exception:
                self.logger.exception("Failure parsing vv lists")
                fieldset = page.fieldset("Valid Values")
                message = page.B.P("Valid value information is not parseable.")
                message.set("class", "error")
                fieldset.append(message)
                page.form.append(fieldset)

    def return_to_doctypes_menu(self, deleted=None):
        """Go back to the menu listing all the CDR document types."""

        opts = dict(deleted=deleted) if deleted else {}
        navigateTo(self.EDIT_DOCTYPES, self.session.name, **opts)

    def run(self):
        """Override base class so we can handle the extra buttons."""

        try:
            if self.request == self.DELETE:
                return self.delete()
            elif self.request in (self.SAVE_CHANGES, self.SAVE_NEW):
                return self.save()
            elif self.request == self.SUBMENU:
                return self.return_to_doctypes_menu()
        except Exception as e:
            bail(f"Failure: {e}")
        Controller.run(self)

    def save(self):
        """Save the new or modified document type object."""

        if not self.name:
            bail("Required name is missing")
        if self.doctype.name:
            self.subtitle = f"Changes to {self.name} saved successfully"
        else:
            self.subtitle = f"New doctype {self.name} saved successfully"
        opts = dict(
            active=self.active,
            comment=self.comment,
            format=self.format,
            name=self.name,
            schema=self.schema,
            title_filter=self.title_filter,
            versioning=self.versioning,
        )
        self.doctype = Doctype(self.session, **opts)
        self.doctype.save()
        self.show_form()

    @property
    def active(self):
        """Boolean representing whether the doctype is active (Y or N)."""
        if not hasattr(self, "_active"):
            self._active = "N"
            if "active" in self.fields.getlist("options"):
                self._active = "Y"
        return self._active

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

    @property
    def buttons(self):
        """Add our custom navigation buttons."""

        if not hasattr(self, "_buttons"):
            self._buttons = [self.SUBMENU, self.ADMINMENU, self.LOG_OUT]
            if self.doctype.id:
                self._buttons.insert(0, self.DELETE)
                self._buttons.insert(0, self.SAVE_CHANGES)
            else:
                self._buttons.insert(0, self.SAVE_NEW)
        return self._buttons

    @property
    def comment(self):
        """Get the comment value from the form field."""
        return self.fields.getvalue("comment")

    @property
    def format(self):
        """Value from the form's format field."""
        return self.fields.getvalue("format")

    @property
    def formats(self):
        """CDR document formats (e.g., xml)."""

        if not hasattr(self, "_formats"):
            self._formats = Doctype.list_formats(self.session)
        return self._formats

    @property
    def name(self):
        """Current value of the form's name field."""
        return self.fields.getvalue("doctype")

    @property
    def schema(self):
        """Selected value from the schema picklist."""
        return self.fields.getvalue("schema")

    @property
    def schemas(self):
        """Top-level CDR schemas."""

        if not hasattr(self, "_schemas"):
            query = db.Query("document d", "d.id").order("d.title")
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'schema'")
            self._schemas = []
            for row in query.execute(self.cursor).fetchall():
                doc = Doc(self.session, id=row.id)
                if doc.root.find(self.ELEMENT) is not None:
                    self._schemas.append(doc.title)
        return self._schemas

    @property
    def subtitle(self):
        """Dynamic string for display under the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.doctype.name:
                self._subtitle = f"Editing {self.doctype.name} Document Type"
            else:
                self._subtitle = "Adding New Document Type"
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Provide status information after a save."""
        self._subtitle = value

    @property
    def title_filter(self):
        """Value from the title filter picklist."""
        return self.fields.getvalue("title_filter")

    @property
    def title_filters(self):
        """Filters used to generate titles for documents of given types."""

        if not hasattr(self, "_title_filters"):
            self._title_filters = Doctype.list_title_filters(self.session)
        return self._title_filters

    @property
    def versioning(self):
        """Boolean representing whether versioning is supported (Y or N)."""
        if not hasattr(self, "_versioning"):
            self._versioning = "N"
            if "versioning" in self.fields.getlist("options"):
                self._versioning = "Y"
        return self._versioning


if __name__ == "__main__":
    """Don't execute the script if we've been loaded as a module."""
    Control().run()
