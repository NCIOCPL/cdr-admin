#!/usr/bin/env python

"""Show changes to DEV after DB refresh from PROD.
"""

from argparse import ArgumentParser
from difflib import Differ
from glob import glob
from cdrcgi import Controller
from cdr_dev_data import Data


class Control(Controller):

    SUBTITLE = "DEV CDR Refresh Report"
    CHECK = "\u2713"
    COLORS = {"-": "LightGoldenrodYellow", "+": "Khakhi", "?": "LightSkyBlue"}
    RULES = {
        "*": "font-family: Arial, sans-serif;",
        "h1": "color: maroon; font-size: 22pt;",
        "h2": "font-size: 20pt; color: green; margin-top: 25px;",
        "h3": "background-color: green; color: white; padding: 5px;",
        "p.ok": "font-size: 16pt; padding-left: 30px; color: green;",
        "pre.fixed, pre.fixed span": "font-family: monospace; font-size: 9pt;",
        "input.path": "width: 500px;",
        "header h2": "color: black; margin-top: 0;",
        "pre": "font-family: monospace;",
    }
    RULES = "\n".join([f"{s} {{ {r} }}" for (s, r) in RULES.items()])
    LOST = "DOCUMENT TYPE LOST"

    def show_report(self):
        """Override the base class version as this isn't a tabular report."""

        buttons = self.report.page.form.find("header/h1/span")
        buttons.insert(0, self.report.page.button(self.DEVMENU))
        self.compare_tables(self.report.page)
        self.compare_docs(self.report.page)
        self.report.page.add_css(self.RULES)
        self.report.send()

    def compare_tables(self, page):
        """Describe the differences between the old and new table versions.

        Pass:
            page - shortcut reference to the report's HTMLPage object
        """

        page.form.append(page.B.H2("Table Comparisons"))
        for name in sorted(self.old.tables):
            page.form.append(page.B.H3(name))
            if name in self.new.tables:
                self.compare_table(page, name)
            else:
                page.form.append(page.B.UL(page.B.LI(page.B.B("TABLE LOST"))))

    def compare_docs(self, page):
        """Describe the differences between the old and the new documents.

        Pass:
            page - shortcut reference to the report's HTMLPage object
        """

        page.form.append(page.B.H2("Document Comparisons"))
        for name in sorted(self.old.docs):
            page.form.append(page.B.H3(f"{name} Docs"))
            new_docs = self.new.docs[name]
            if not new_docs.docs:
                page.form.append(page.B.UL(page.B.LI(page.B.B(self.LOST))))
            else:
                old_docs = self.old.docs[name]
                items = []
                for key in old_docs.docs:
                    old_id, old_title, old_xml = old_docs.docs[key]
                    if key not in new_docs.docs:
                        items.append(page.B.LI(page.B.I(old_title)))
                    else:
                        diffs = self.diff_xml(old_xml, new_docs.docs[key][2])
                        if diffs is not None:
                            title = page.B.B(old_title)
                            items.append(page.B.LI(title, diffs))
                if not items:
                    page.form.append(page.B.P(self.CHECK, page.B.CLASS("ok")))
                else:
                    page.form.append(page.B.UL(*items))

    def diff_xml(self, old, new):
        """Find the differences between the old and new versions of a doc.

        Pass:
            old - the serialized XML for the old version of the document
            new - the serialized XML for the new version of the document

        Return:
            an HTML `pre` element containing the deltas between old and new,
            or None if there are no differences after normalization
        """

        differ = Differ()
        before = old.replace("\r", "").splitlines()
        after = new.replace("\r", "").splitlines()
        diffs = differ.compare(before, after)
        lines = []
        changes = False
        for line in diffs:
            line = line.rstrip("\n")
            color = self.COLORS.get(line[0], "white")
            if line and line[0] in self.COLORS:
                changes = True
                bgcolor = f"background-color: {color}"
                span = self.HTMLPage.B.SPAN(f"{line}\n", style=bgcolor)
                lines.append(span)
            elif self.verbose:
                lines.append(self.HTMLPage.B.SPAN(line))
        if changes:
            pre = self.HTMLPage.B.PRE(*lines)
            pre.set("class", "fixed")
            return pre
        return None

    def compare_table(self, page, name):
        """Show the deltas between the old and new versions of a table.

        Pass:
            page - shortcut reference to the report's HTMLPage object
            name - string for the name of the table to be checked
        """

        items = []
        ot = self.old.tables[name]
        nt = self.new.tables[name]
        if set(ot.cols) != set(nt.cols):
            ul = page.B.UL()
            item = page.B.LI("TABLE STRUCTURE MISMATCH", ul)
            ul.append(page.B.LI(f"old: {ot.cols:!r}"))
            ul.append(page.B.LI(f"new: {nt.cols:!r}"))
            items.append(item)
        if ot.names:
            for key in sorted(ot.names):
                if key not in nt.names:
                    items.append(page.B.LI("row for ", page.B.B(key), " lost"))
                    continue
                old_row = ot.names[key].copy()
                new_row = nt.names[key].copy()
                if "id" in old_row:
                    old_row.pop("id")
                    new_row.pop("id")
                if old_row != new_row:
                    cols = page.B.UL()
                    args = "row for ", page.B.B(key), " changed", cols
                    item = page.B.LI(*args)
                    items.append(item)
                    for col in old_row:
                        ov = old_row[col]
                        nv = new_row[col]
                        if ov != nv:
                            if name == "query" and col == "value":
                                ov = page.B.PRE(ov.replace("\r", ""))
                                nv = page.B.PRE(nv.replace("\r", ""))
                            else:
                                ov = repr(ov)
                                nv = repr(nv)
                            changes = page.B.LI(f"{col!r} column changed")
                            cols.append(changes)
                            if col not in ("hashedpw", "password"):
                                changes.append(page.B.UL(
                                    page.B.LI("old: ", ov),
                                    page.B.LI("new: ", nv)
                                ))
        elif name in ("grp_action", "grp_usr"):
            old_rows = [getattr(self.old, name)(row) for row in ot.rows]
            new_rows = [getattr(self.new, name)(row) for row in nt.rows]
            for row in sorted(set(old_rows) - set(new_rows)):
                items.append(page.B.LI(f"row for {row} lost"))
        else:
            if name in dir(self.old):
                old_rows = set([getattr(self.old, name)(r) for r in ot.rows])
                new_rows = set([getattr(self.new, name)(r) for r in nt.rows])
            else:
                old_rows = set(ot.rows)
                new_rows = set(nt.rows)
            old_only = [(row, "lost") for row in (old_rows - new_rows)]
            new_only = [(row, "added") for row in (new_rows - old_rows)]
            deltas = old_only + new_only
            try:
                for row, which_set in sorted(deltas, key=lambda v: str(v)):
                    items.append(page.B.LI(f"{which_set}: {row}"))
            except Exception:
                print(deltas)
                raise
        if items:
            page.form.append(page.B.UL(*items))
        else:
            page.form.append(page.B.P(self.CHECK, page.B.CLASS("ok")))

    def populate_form(self, page):
        """Ask the user for the baseline against which we should compare.

        Pass:
            HTMLPage object where we put our form field
        """

        if self.new:
            self.show_report()
        fieldset = page.fieldset("Saved Development Server Data")
        fieldset.append(page.text_field("path", value=self.default_path))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        label = "Verbose (include full diffs)"
        fieldset.append(page.checkbox("verbose", label=label))
        page.form.append(fieldset)

    @property
    def default_path(self):
        """String for seeding the form's path field."""

        dev_data_path = f"{self.session.tier.basedir}/DevData"
        files = glob(f"{dev_data_path}/DevData-20*")
        default = sorted(files)[-1] if files else f"{dev_data_path}/"
        return default.replace("\\", "/")

    @property
    def new(self):
        """Source for the new data to be compared with the old."""

        if not hasattr(self, "_new"):
            self._new = None
            if self.opts.new and self.old:
                self._new = Data(self.opts.new, self.old)
        return self._new

    @property
    def old(self):
        """Source for the old data to be compared with the new."""

        if not hasattr(self, "_old"):
            self._old = Data(self.opts.old) if self.opts.old else None
        return self._old

    @property
    def opts(self):
        """Options pulled from a CGI request or the command line."""

        if not hasattr(self, "_opts"):
            parser = ArgumentParser()
            parser.add_argument("--old", default=self.fields.getvalue("path"))
            parser.add_argument("--new", default=self.cursor)
            parser.add_argument("--verbose", action="store_true")
            self._opts = parser.parse_args()
        return self._opts

    @property
    def verbose(self):
        """If True, show full documents in the diff output."""

        if not hasattr(self, "_verbose"):
            self._verbose = self.opts.verbose
            if not self._verbose:
                self._verbose = self.fields.getvalue("verbose")
        return self._verbose


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
