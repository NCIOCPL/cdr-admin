#!/usr/bin/env python

"""Interface for managing the mappings to string from external sources.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc
from datetime import datetime
import json


class Control(Controller):
    """Encapsulate the logic for this report."""

    SUBTITLE = "External Map Editor"
    ONLY_UNMAPPED = "Only include unmapped values"
    WITH_UNMAPPABLE = "Also include unmappable values"
    FILTER = "Get Values"
    SAVE = "Save Changes"
    LOGNAME = "EditExternalMap"
    FIELDS = "doc_id=?, bogus=?, mappable=?, usr=?, last_mod=GETDATE()"
    UPDATE = f"UPDATE external_map SET {FIELDS} WHERE id = ?"
    FILTER_OPTS = "filter-opts"
    DELETION_BLOCKED = "Deletion request blocked because the value is mapped"
    DELETE = "DELETE FROM external_map WHERE id = ?"
    TYPE_NOT_MAPPABLE = "{} mappings can't link to {} document CDR{:d}"
    CSS = """\
.mapped-to { width: 5rem; margin-top: 0; }
#tabular-form { width: 80%; margin: 5rem auto 1rem; }
#tabular-form caption { text-align: center; font-size: 1.2rem; }
#tabular-form th { text-align: center; font-weight: bold; }
#tabular-form.usa-form .usa-button { margin-top: 0; }
#tabular-form .usa-checkbox__label { margin-top: 0; }
tfoot td { color: green; font-size: .9em; font-style: italic; }
.usa-table tfoot td { text-align: center; border-bottom: none; }
.usa-form td a:visited { color: white; }
"""

    def build_tables(self):
        """Show the selected mappings (if any) under the filter form."""

        page = self.form_page
        filter_opts = json.dumps(self.filter_opts)
        self.populate_form(page)
        page.form.append(page.button(self.FILTER))
        page.form.set("target", "")
        opts = dict(action=self.script, method="POST", id="tabular-form")
        form = page.B.FORM(page.B.CLASS("usa-form"), **opts)
        if self.table is not None:
            form.append(self.table)
            page.add_css(self.CSS)
            form.append(page.button(self.SAVE))
        else:
            message = "No mappings found matching the filtering criteria."
            page.add_alert(message, type="warning")
        form.append(page.hidden_field(self.FILTER_OPTS, filter_opts))
        form.append(page.hidden_field(self.SESSION, self.session))
        page.main.append(form)
        page.send()

    def populate_form(self, page):
        """Add the fields for refining the selection of mappings.

        Required positional argument:
          page - instance of the cdrcgi.HTMLPage class
        """

        fieldset = page.fieldset("Select Mappings")
        options = [(0, "All")] + self.usages
        opts = dict(options=options, default=self.usage)
        fieldset.append(page.select("usage", **opts))
        opts = dict(value=self.pattern, tooltip="Use SQL wildcards")
        fieldset.append(page.text_field("value_pattern", **opts))
        opts = dict(value=self.doc_id, label="CDR ID")
        fieldset.append(page.text_field("doc_id", **opts))
        fieldset.append(page.text_field("max", value=self.max))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        opts = dict(value=self.ONLY_UNMAPPED, checked=self.only_unmapped)
        fieldset.append(page.checkbox("options", **opts))
        opts = dict(
            value=self.WITH_UNMAPPABLE,
            checked=self.include_unmappable,
        )
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)

    def run(self):
        """Provide routing for our custom actions."""

        try:
            if self.request == self.SAVE:
                self.save()
            elif self.request == self.FILTER:
                self.show_report()
        except Exception as e:
            self.logger.exception("failure")
            self.bail(str(e))
        Controller.run(self)

    def save(self):
        """Make the requested changes and display the page again."""

        # Collect the values from the tabular form at the bottom of the page.
        mappings = {}
        for mapping in self.original_mappings:
            mappings[mapping.id] = mapping
        doc_ids = {}
        for name in self.fields:
            if name.startswith("cdrid-"):
                doc_id = self.fields[name].value
                if doc_id:
                    doc_id = Doc.extract_id(self.fields[name].value)
                mapping_id = Doc.extract_id(name)
                doc_ids[mapping_id] = doc_id
        bogus = {int(b) for b in self.fields.getlist("bogus")}
        delete_requests = {int(d) for d in self.fields.getlist("delete")}
        mappable = {int(m) for m in self.fields.getlist("mappable")}
        page = self.form_page

        # Handle the requests to delete some of the mappings.
        changes = {}
        errors = {}
        actions = {}
        for mapping_id in delete_requests:
            if doc_ids.get(mapping_id):
                errors[mapping_id] = [self.DELETION_BLOCKED]
                continue
            mapping = mappings[mapping_id]
            if mapping.action not in actions:
                actions[mapping.action] = self.session.can_do(mapping.action)
            if not actions[mapping.action]:
                errors[mapping_id] = [f"{mapping.action} not permitted"]
                continue
            try:
                self.cursor.execute(self.DELETE, mapping_id)
                self.conn.commit()
                changes[mapping_id] = ["Mapping deleted"]
                args = mapping_id, mappings[mapping_id].value
                self.logger.info("Deleted mapping %d for %s", *args)
            except Exception as e:
                self.logger.exception("Deleting mapping %d", mapping_id)
                errors[mapping_id] = [f"Deletion failure: {e}"]

        # Walk through all of the mapping the user was looking at.
        for mapping in sorted(self.original_mappings):

            # If the user asked that the mapping be deleted, skip it here.
            if mapping.id in delete_requests:
                continue

            # Collect 'diffs' and 'problems' for each mapping, rolled into
            # 'changes' and 'errors' for the complete request.
            diffs = []
            problems = []

            # Find out if there are changes to be saved, or problems to show.
            old_id, new_id = mapping.doc_id, doc_ids.get(mapping.id)
            if old_id != new_id:
                if new_id:
                    try:
                        doctype = Doc(self.session, id=new_id).doctype
                    except Exception:
                        doctype = None
                    if not doctype:
                        problems.append(f"CDR document {new_id} not found")
                    elif doctype.id not in mapping.allowed_doctypes:
                        args = mapping.usage, doctype, new_id
                        problems.append(self.TYPE_NOT_MAPPABLE.format(*args))
                    elif not old_id:
                        diffs.append(f"Mapping to CDR{new_id} added")
                    else:
                        diff = f"Mapping changed from {old_id} to {new_id}"
                        diffs.append(diff)
                elif old_id:
                    diffs.append(f"Mapping to CDR{old_id} removed")
            if mapping.id in bogus:
                if new_id:
                    problems.append("Mapped value cannot be flagged 'bogus'")
                if mapping.id in mappable:
                    problem = "Mapping cannot be both bogus and unmappable"
                    problems.append(problem)
                elif not new_id and not mapping.bogus:
                    diffs.append("Bogus flag set")
            elif mapping.bogus:
                diffs.append("Bogus flag cleared")
            if mapping.id not in mappable:
                if new_id:
                    problems.append("Mapped value must be flagged 'mappable'")
                elif mapping.mappable:
                    diffs.append("Mappable flag cleared")
            elif not mapping.mappable:
                diffs.append("Mappable flag set")

            # If we found any problems, we won't save any changes.
            if problems:
                errors[mapping.id] = problems

            # Update the mapping row, remembering any failures.
            elif diffs:
                action = mapping.action
                if action not in actions:
                    actions[action] = self.session.can_do(action)
                if not actions[action]:
                    errors[mapping_id] = [f"{action} not permitted"]
                    continue
                values = [
                    new_id or None,
                    "Y" if mapping.id in bogus else "N",
                    "Y" if mapping.id in mappable else "N",
                    self.session.user_id,
                    mapping.id,
                ]
                try:
                    args = mapping.id, values
                    self.logger.info("Updating mapping %d with %s", *args)
                    self.cursor.execute(self.UPDATE, values)
                    self.conn.commit()
                    changes[mapping.id] = diffs
                except Exception as e:
                    self.logger.exception("Updating mapping %d", mapping.id)
                    errors[mapping.id] = [f"Update failure: {e}"]

        # Show the page, including a report of successful updates and failures.
        self.show_results(page, mappings, errors, True)
        self.show_results(page, mappings, changes)
        if not changes and not errors:
            page.add_alert("No changes found to be saved.", type="warning")
        self.show_report()

    def show_results(self, page, mappings, results, errors=False):
        """Display messages describing what happened with the Save request."""

        alert_type = "error" if errors else "success"
        what = "Error(s) in" if errors else "Change(s) to"
        for mapping_id, items in results.items():
            mapping = f"{what} {mappings[mapping_id]}"
            if len(items) == 1:
                message = f"{mapping}: {items[0]}."
                page.add_alert(message, type=alert_type)
            else:
                items = [page.B.LI(item) for item in items]
                opts = dict(type=alert_type, extra=page.B.UL(*items))
                page.add_alert(f"{mapping}:", **opts)

    @cached_property
    def buttons(self):
        """Override the available commands for the filtering form."""
        return [self.FILTER]

    @property
    def doc_id(self):
        """Used to show mappings only to a single CDR document."""
        return self.filter_opts.get("doc_id")

    @cached_property
    def filter_opts(self):
        """Current setting of the filtering form fields."""

        opts = self.fields.getvalue(self.FILTER_OPTS)
        if opts:
            return json.loads(opts)
        try:
            usage = int(self.fields.getvalue("usage"))
        except Exception:
            usage = None
        return dict(
            max=self.fields.getvalue("max", "100"),
            usage=usage,
            doc_id=self.fields.getvalue("doc_id"),
            pattern=self.fields.getvalue("value_pattern"),
            include_unmappable=self.WITH_UNMAPPABLE in self.options,
            only_unmapped=self.ONLY_UNMAPPED in self.options,
        )

    @property
    def include_unmappable(self):
        """Has the user said we should include unmappable values?"""
        return True if self.filter_opts.get("include_unmappable") else False

    @cached_property
    def mappings(self):
        """Sorted sequence of mapping matching the filtering parameters."""
        return Mapping.get_mappings(self, **self.filter_opts)

    @property
    def max(self):
        """Throttle for the number of mappings to display."""
        return self.filter_opts.get("max", "100")

    @property
    def only_unmapped(self):
        """Has the user asked that we only show unmapped values?"""
        return True if self.filter_opts.get("only_unmapped") else False

    @cached_property
    def original_mappings(self):
        """Mappings before changes are applied."""
        return Mapping.get_mappings(self, **self.filter_opts)

        opts = self.original_filter_opts
        if opts is None:
            self.bail()
        return Mapping.get_mappings(self, **opts)

    @property
    def options(self):
        """Flags the user can set for filtering which mappings to show."""
        return self.fields.getlist("options")

    @property
    def pattern(self):
        """Optional string for filtering by mapped values.

        Usually includes wildcards.
        """
        return self.filter_opts.get("pattern")

    @property
    def same_window(self):
        """Avoid opening new browser tabs."""
        return self.buttons

    @cached_property
    def table(self):
        """Table showing the mapping matching the user's selections."""

        if not self.mappings:
            return None
        B = self.HTMLPage.B
        rows = []
        url = f"QcReport.py?Session={self.session}&DocVersion=-1"
        headers = [
            B.TH("Variant String"),
            B.TH("Mapped To", colspan="2"),
            B.TH("Flags", colspan="3"),
        ]
        if not self.usage:
            headers.insert(0, B.TH("Usage"))
        for mapping in self.mappings:
            mid = str(mapping.id)
            doc_id = str(mapping.doc_id or "")
            id_field_id = f"cdrid-{mapping.id}"
            id_field = B.INPUT(name=id_field_id, id=id_field_id, value=doc_id)
            id_field.set("class", "usa-input mapped-to")
            if doc_id:
                opts = dict(href=f"{url}&DocId={doc_id}", target="_blank")
                view_button = B.A("View", B.CLASS("usa-button"), **opts)
            else:
                view_button = ""
            opts = dict(label="Delete?", value=mid)
            delete = self.HTMLPage.checkbox("delete", **opts)
            bogus = self.HTMLPage.checkbox("bogus", label="Bogus?", value=mid)
            opts = dict(label="Mappable?", value=mid)
            mappable = self.HTMLPage.checkbox("mappable", **opts)
            if mapping.bogus:
                bogus.find("input").set("checked")
            if mapping.mappable:
                mappable.find("input").set("checked")
            cols = [
                B.TD(mapping.value),
                B.TD(id_field),
                B.TD(view_button),
                B.TD(delete),
                B.TD(bogus),
                B.TD(mappable)
            ]
            if not self.usage:
                cols.insert(0, B.TD(mapping.usage))
            rows.append(B.TR(*cols))
        elapsed = datetime.now() - self.started
        footnote = f"Fetched {len(rows):d} mapping(s) in {elapsed}"
        return B.TABLE(
            B.CAPTION("Mappings"),
            B.THEAD(B.TR(*headers)),
            B.TBODY(*rows),
            B.TFOOT(B.TR(B.TD(footnote, colspan=str(len(cols))))),
            B.CLASS("usa-table usa-table--borderless")
        )

    @cached_property
    def usage(self):
        """Which mapping type has the users selected (if any)?"""
        return self.filter_opts.get("usage")

    @cached_property
    def usages(self):
        """All mapping types in the system (for the filtering picklist)."""

        fields = "id", "name"
        query = self.Query("external_map_usage", *fields).order(2)
        return [tuple(row) for row in query.execute(self.cursor)]


class Mapping:
    """Information about a single external mapping of string to CDR document.
    """

    FIELDS = (
        "m.id",
        "m.value",
        "u.name AS usage",
        "m.doc_id",
        "m.bogus",
        "m.mappable",
        "a.name AS action",
    )
    ALLOWED_DOCTYPES = {}

    def __init__(self, control, row):
        """Capture the caller's information, letting proerties do the work."""

        self.__control = control
        self.__row = row

    def __str__(self):
        """Make the mappings identify themselves usefully."""
        return f"{self.usage} mapping of {self.value}"

    def __lt__(self, other):
        """Make the mappings sortable."""
        return (self.usage, self.value) < (other.usage, other.value)

    @cached_property
    def allowed_doctypes(self):
        """Which document types are allowed for this mapping's usage?"""

        if self.usage not in Mapping.ALLOWED_DOCTYPES:
            query = self.control.Query("external_map_type t", "t.doc_type")
            query.join("external_map_usage u", "u.id = t.usage")
            query.where(query.Condition("u.name", self.usage))
            rows = query.execute(self.control.cursor).fetchall()
            allowed = set([row.doc_type for row in rows])
            Mapping.ALLOWED_DOCTYPES[self.usage] = allowed
            return allowed
        return Mapping.ALLOWED_DOCTYPES[self.usage]

    @property
    def action(self):
        """String naming permission needed for saving mapping information."""
        return self.__row.action

    @property
    def bogus(self):
        """Boolean indicating whether the proposed mapping is legitimate.

        No longer of much use, now that we are no longer managing
        clinical trials. When we did, strings from fields in the
        imported trial documents were automatically inserted into
        the external map table to be mapped to CDR documents representing
        the entities referenced by those strings. It often happened that
        the sources from which the trial documents were imported were
        not edited very carefully, and we would frequently find values
        which obviously didn't belong in the fields in which they were
        entered (for example, a comment in a state element).

        There's some semantic overlap with the `mappable` flag, which
        also lost its usefulness with the retirement from the clinical
        trials business. Perhaps if we decide after a reasonable amount
        of time has gone by without a good use case for these flags,
        we can remove them from the mapping table.
        """

        return self.__row.bogus == "Y"

    @property
    def control(self):
        """Access to database queries and logging."""
        return self.__control

    @property
    def doc_id(self):
        """The ID of the CDR document being mapped (if any)."""
        return self.__row.doc_id or None

    @property
    def id(self):
        """The unique integer ID for the mapping."""
        return self.__row.id

    @property
    def mappable(self):
        """Boolean indicating whether this string is mappable.

        In theory, the value should be one to which we can find
        (or create) a CDR document, but after considerable research
        we have given up trying to find out enough information
        about the entity the string represents, and we don't want
        to spend any more time on searching further. This flag
        isn't as useful as it was when we were curating information
        about clinical trials, and we had to maintain information
        about persons, places, organizations, etc., connected with
        the documents for the clinical trials.
        """

        return self.__row.mappable == "Y"

    @property
    def usage(self):
        """The string identifying the mapping's type."""
        return self.__row.usage

    @property
    def value(self):
        """The string being mapped."""
        return self.__row.value

    @classmethod
    def get_mappings(cls, control, **opts):
        """Use the current filtering options to select mappable strings.

        Required positional argument:

            control
                Control object, providing access to the database and logging

        Optional keyword arguments:

            doc_id
                integer limiting the results to mapping to a single document

            usage
                integer restricting results to a single mapping type

            limit
                integer restricting the results to a maximum number

            pattern
                string with optional wildcard limiting to matched values

            only_unmapped
                if True, only include `Mapping` objects with no doc_id

            include_unmappable
                if True, include values which have been flagged as not
                worth any more research to find or create a suitable
                CDR document to which the value can be mapped (by
                default those are excluded)

        Return:

            sequence of `Mapping` objects ordered by value string
        """
        query = control.Query("external_map m", *cls.FIELDS)
        query.join("external_map_usage u", "u.id = m.usage")
        query.join("action a", "a.id = u.auth_action")
        query.order("m.value", "u.name")
        doc_id = opts.get("doc_id")
        if doc_id:
            query.where(query.Condition("m.doc_id", doc_id))
        else:
            usage = int(opts.get("usage") or "0")
            if usage:
                query.where(query.Condition("u.id", usage))
            limit = int(opts.get("max") or "0")
            if limit:
                query.limit(limit)
            pattern = opts.get("pattern")
            if pattern:
                query.where(query.Condition("m.value", pattern, "LIKE"))
            if opts.get("only_unmapped"):
                query.where("m.doc_id IS NULL")
            if not opts.get("include_unmappable"):
                query.where("m.mappable = 'Y'")
        query.log(label="EditExternalMap.get_mappings() query")
        rows = query.execute(control.cursor).fetchall()
        return [cls(control, row) for row in rows]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
