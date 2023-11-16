#!/usr/bin/env python

"""Show count of updated documents by document type.
"""

from functools import cached_property
from cdrcgi import Controller, Reporter
from datetime import date, timedelta


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Publishing Job Statistics by Date"
    COLUMNS = (
        Reporter.Column("Doc Type", classes="text-left"),
        Reporter.Column("Re-Added", classes="text-right"),
        Reporter.Column("New", classes="text-right"),
        Reporter.Column("Updated", classes="text-right"),
        Reporter.Column("Updated*", classes="text-right"),
        Reporter.Column("Removed", classes="text-right"),
        Reporter.Column("Total", classes="text-right"),
    )

    def build_tables(self):
        """Assemble the counts table."""

        start = str(self.start)[:10]
        end = str(self.end)[:10]
        caption = f"Documents Published Between {start} and {end}"
        opts = dict(caption=caption, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask the user for the report's parameters.

        Pass:
            page - HTMLPage object where we put the form
        """

        end = date.today()
        start = end - timedelta(7)
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)
        fieldset = page.fieldset("Document Type(s)")
        opts = dict(value="all", checked=True)
        fieldset.append(page.checkbox("doctype", **opts))
        for doctype in self.doctypes:
            opts = dict(value=doctype, label=doctype, classes="dt")
            fieldset.append(page.checkbox("doctype", **opts))
        page.add_script("\n".join([
            "function check_doctype(name) {",
            "  if (name == 'all') {",
            "    jQuery('.dt').prop('checked', false);",
            "    jQuery('#doctype-all').prop('checked', true);",
            "  }",
            "  else",
            "    jQuery('#doctype-all').prop('checked', false);",
            "}",
        ]))
        page.form.append(fieldset)

    def show_report(self):
        """Override the base class version to add a key to the columns."""

        fieldset = self.report.page.fieldset("Key")
        fieldset.append(self.key)
        self.report.page.form.append(fieldset)
        self.report.page.add_css("dt { font-weight: bold; }")
        self.report.send()

    @cached_property
    def doctype(self):
        """Document type(s) selected for the report from the form."""

        doctypes = self.fields.getlist("doctype")
        return [] if "all" in doctypes else doctypes

    @cached_property
    def doctypes(self):
        """Document type strings for the form's checkboxes.

        It doesn't make sense, but adding a second column to the results
        set speeds up the query by orders of magnitude.
        """

        query = self.Query("doc_type t", "t.name", "d.doc_type").unique()
        query.order("t.name")
        query.join("document d", "d.doc_type = t.id")
        query.join("pub_proc_cg c", "c.id = d.id")
        rows = query.execute(self.cursor).fetchall()
        return [row.name for row in rows]

    @cached_property
    def end(self):
        """End of the date range for the report."""

        end = self.parse_date(self.fields.getvalue("end")) or date.today()
        return f"{end} 23:59:59"

    @cached_property
    def key(self):
        """Guide explaining what the numbers in each column mean."""

        return self.HTMLPage.B.DL(
            self.HTMLPage.B.DT("Re-Added"),
            self.HTMLPage.B.DD(
                "This count includes documents that existed on Cancer.gov, "
                "had been removed and added again."
            ),
            self.HTMLPage.B.DT("New"),
            self.HTMLPage.B.DD(
                "This count includes documents that are new and never "
                "existed on Cancer.gov before."
            ),
            self.HTMLPage.B.DT("Updated"),
            self.HTMLPage.B.DD(
                "This count includes documents that have been updated on "
                "Cancer.gov. If a document has been added ",
                self.HTMLPage.B.STRONG("and"),
                " updated during the specified time period it is only "
                "counted as a new document."
            ),
            self.HTMLPage.B.DT("Updated*"),
            self.HTMLPage.B.DD(
                "This count also includes documents that have been updated "
                "on Cancer.gov. If a document has been added ",
                self.HTMLPage.B.STRONG("and"),
                " updated during the specified time period it is counted "
                "twice, once as a new document and once as an updated "
                "document."
            ),
            self.HTMLPage.B.DT("Removed"),
            self.HTMLPage.B.DD(
                "This number includes documents that have been removed "
                "from Cancer.gov."
            ),
            self.HTMLPage.B.DT("Total"),
            self.HTMLPage.B.DD(
                "This number sums up all columns (except for the column "
                "Updated*) to only count a document once per time frame "
                "specified."
            )
        )

    @cached_property
    def new(self):
        """Counts of new documents by doctype."""

        query = self.Query("doc_type t", "t.name", "COUNT(*)")
        query.join("all_docs d", "d.doc_type = t.id")
        query.join("##ganzneu n", "n.doc_id = d.id")
        if self.doctype:
            query.where(query.Condition("t.name", self.doctype, "IN"))
        query.group("t.name")
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def removed(self):
        """Counts by doctype of removed documents."""

        query = self.Query("doc_type t", "t.name", "COUNT(*)")
        query.join("all_docs d", "d.doc_type = t.id")
        query.join("##removed r", "r.doc_id = d.id")
        query.where(query.Condition("r.started", self.start, ">="))
        if self.doctype:
            query.where(query.Condition("t.name", self.doctype, "IN"))
        query.group("t.name")
        self.logger.info("removed: %s", query)
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def resurrected(self):
        """Counts of re-added (after removal) documents by doctype."""

        query = self.Query("doc_type t", "t.name", "COUNT(*)")
        query.join("all_docs d", "d.doc_type = t.id")
        query.join("##phoenix p", "p.doc_id = d.id")
        query.where(query.Condition("p.started", self.start, ">="))
        query.where(query.Condition("p.started", self.end, "<="))
        if self.doctype:
            query.where(query.Condition("t.name", self.doctype, "IN"))
        query.group("t.name")
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def rows(self):
        """Values for the report table."""

        self.__create_temporary_removed_table()
        self.__create_temporary_prevpub_table()
        self.__create_temporary_ganzneu_table()
        self.__create_temporary_phoenix_table()
        doctypes = sorted(self.doctype) if self.doctype else self.doctypes
        rows = []
        for doctype in doctypes:
            renewed = self.resurrected.get(doctype, 0)
            new = self.new.get(doctype, 0)
            updated = self.updated.get(doctype, [0, 0])
            removed = self.removed.get(doctype, 0)
            total = renewed + new + updated[0] + removed
            rows.append([
                doctype,
                self.Reporter.Cell(renewed, right=True),
                self.Reporter.Cell(new, right=True),
                self.Reporter.Cell(updated[0], right=True),
                self.Reporter.Cell(updated[1], right=True),
                self.Reporter.Cell(removed, right=True),
                self.Reporter.Cell(total, right=True),
            ])
        return rows

    @cached_property
    def start(self):
        """Beginning of the date range for the report."""
        return self.parse_date(self.fields.getvalue("start", "2001-01-01"))

    @property
    def updated(self):
        """Dictionary of two counts of updated docs for each doctype.

        The first count is for all docs published to cancer.gov during
        the report's date range. The second count excludes new documents
        and documents which were newly added after having been removed.
        """

        if not hasattr(self, "_updated"):
            fields = "t.name", "COUNT(DISTINCT d.doc_id) n"
            query = self.Query("doc_type t", *fields)
            query.join("all_docs a", "a.doc_type = t.id")
            query.join("pub_proc_doc d", "d.doc_id = a.id")
            query.join("pub_proc p", "p.id = d.pub_proc")
            query.where(query.Condition("p.started", self.start, ">="))
            query.where(query.Condition("p.started", self.end, "<="))
            query.where("p.pub_subset LIKE 'Push_%'")
            query.where("p.status = 'Success'")
            query.where("d.removed = 'N'")
            query.group("t.name")
            if self.doctype:
                query.where(query.Condition("t.name", self.doctype, "IN"))
            self._updated = {}
            for row in query.execute(self.cursor).fetchall():
                self._updated[row.name] = [0, row.n]
            new = self.Query("##ganzneu", "doc_id")
            new.where(new.Condition("started", self.start, ">="))
            new.where(new.Condition("started", self.end, "<="))
            renewed = self.Query("##phoenix", "doc_id")
            renewed.where(renewed.Condition("started", self.start, ">="))
            renewed.where(renewed.Condition("started", self.end, "<="))
            query.where(query.Condition("a.id", new, "NOT IN"))
            query.where(query.Condition("a.id", renewed, "NOT IN"))
            for row in query.execute(self.cursor).fetchall():
                if row.name in self._updated:
                    self._updated[row.name][0] = row.n
                else:
                    self._updated[row.name] = [row.n, 0]
        return self._updated

    def __create_temporary_removed_table(self):
        """Find documents removed no later than the end of the date range."""

        fields = "d.doc_id", "MAX(p.started) as started"
        query = self.Query("pub_proc_doc d", *fields)
        query.join("pub_proc p", "p.id = d.pub_proc")
        query.where(query.Condition("p.started", self.end, "<="))
        query.where("p.pub_subset LIKE 'Push_%'")
        query.where("p.status = 'Success'")
        query.where("d.removed = 'Y'")
        query.group("d.doc_id")
        query.into("##removed")
        query.execute(self.cursor)
        self.logger.info("##removed: %s", query)
        self.conn.commit()

    def __create_temporary_prevpub_table(self):
        """Find documents which were published at least once before range."""

        query = self.Query("pub_proc_doc d", "d.doc_id").unique()
        query.join("pub_proc p", "p.id = d.pub_proc")
        query.where(query.Condition("p.started", self.start, "<"))
        query.where("p.pub_subset LIKE 'Push_%'")
        query.where("p.status = 'Success'")
        query.into("##prevpub")
        query.execute(self.cursor)
        self.conn.commit()

    def __create_temporary_ganzneu_table(self):
        """Find documents first published during our date range."""

        subquery = self.Query("##prevpub", "doc_id")
        fields = "d.doc_id", "MIN(p.started) AS started"
        query = self.Query("pub_proc_doc d", *fields)
        query.join("pub_proc p", "p.id = d.pub_proc")
        query.where(query.Condition("p.started", self.start, ">="))
        query.where(query.Condition("p.started", self.end, "<="))
        query.where("p.pub_subset LIKE 'Push_%'")
        query.where("p.status = 'Success'")
        query.where(query.Condition("d.doc_id", subquery, "NOT IN"))
        query.group("d.doc_id")
        query.into("##ganzneu")
        query.execute(self.cursor)
        self.conn.commit()

    def __create_temporary_phoenix_table(self):
        """Find docs which had been remove and then published again."""

        fields = "d.doc_id", "MIN(p.started) AS started"
        query = self.Query("pub_proc_doc d", *fields)
        query.join("pub_proc p", "p.id = d.pub_proc")
        query.join("##removed r", "r.doc_id = d.doc_id")
        query.where("p.started > r.started")
        query.where("p.pub_subset LIKE 'Push_%'")
        query.where("p.status = 'Success'")
        query.where("d.removed = 'N'")
        query.group("d.doc_id")
        query.into("##phoenix")
        query.execute(self.cursor)
        self.conn.commit()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
