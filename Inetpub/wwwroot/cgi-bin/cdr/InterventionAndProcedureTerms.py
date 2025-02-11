#!/usr/bin/env python

"""Generate hierarchical report of terminology for interventions/procedures.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "CDR Intervention or Procedure Index Terms"
    LOGNAME = "TerminologyReports"
    FIELD_NAME = "IncludeAlternateNames"
    INCLUDE = "Include display of alternate term names"
    EXCLUDE = "Exclude display of alternate term names"
    OPTIONS = ((INCLUDE, "True", True), (EXCLUDE, "False", False))
    CREATE_IP = "CREATE TABLE #ip (sid INT, pid INT)"
    CREATE_TERMS = "CREATE TABLE #terms (sid INT, tid INT, name NVARCHAR(MAX))"
    PARENT_PATH = "/Term/TermRelationship/ParentTerm/TermId/@cdr:ref"
    CSS = (
        "ul.t { padding-left: 0; }",
        "li { list-style: none; }",
        "li.u { color: green; font-weight: bold; }",
        "ul li { font-weight: normal; }",
        "li.u { font-variant: small-caps; }",
        "li.i { font-variant: small-caps; }",
        "li.l { color: blue; font-variant: normal; }",
        "li.a { color: #ff2222; font-style: italic; }",
        "li.a { font-variant: normal; }",
    )

    def populate_form(self, page):
        """Let the user choose which version of the report to show.

        Required positional argument:
          page - instance of the HTMLPage class
        """

        if self.flavor:
            self.show_report()
        fieldset = page.fieldset("Display Options")
        for label, value, checked in self.OPTIONS:
            opts = dict(label=label, value=value, checked=checked)
            fieldset.append(page.radio_button(self.FIELD_NAME, **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Override base class method, because we're not using Report class."""

        opts = dict(
            session=self.session,
            action=self.script,
            subtitle=self.subtitle,
        )
        page = self.HTMLPage(self.title, **opts)
        fieldset = page.fieldset("Tree Hierarchy")
        tree = page.B.UL(self.patriarch.node, page.B.CLASS("usa-list t"))
        fieldset.append(tree)
        fieldset.append(self.footer)
        page.form.append(fieldset)
        page.body.set("class", "report")
        page.add_css("\n".join(self.CSS))
        page.send()

    @cached_property
    def flavor(self):
        """If "short" don't collect or show aliases."""

        value = self.fields.getvalue(self.FIELD_NAME)
        if value:
            return "long" if value == "True" else "short"
        return self.fields.getvalue("flavor")

    @property
    def patriarch(self):
        """Highest ancestor in the tree (no parents).

        The value for `self._patriarch` is modified by
        `self.__collect_terms()`.
        """

        if not hasattr(self, "_patriarch"):
            self._patriarch = None
            self.__create_tables()
            self.__populate_tables()
            self.__collect_terms()
        return self._patriarch

    @cached_property
    def subtitle(self):
        """String to be displayed directly under the main banner."""

        if self.flavor == "short":
            return f"{self.SUBTITLE} (without Alternate Names)"
        return self.SUBTITLE

    @cached_property
    def terms(self):
        """Dictionary of `Term` objects."""
        return {}

    def __create_tables(self):
        """Create the two temporary tables needed to build the tree."""

        self.cursor.execute(self.CREATE_IP)
        self.cursor.execute(self.CREATE_TERMS)
        self.conn.commit()

    def __populate_tables(self):
        """Add the terms to the temporary tables."""

        query = self.Query("query_term", "doc_id", "0").unique()
        query.where("path = '/Term/PreferredName'")
        query.where("value = 'Intervention or procedure'")
        self.cursor.execute(f"INSERT INTO #ip (sid, pid) {query}")
        query = self.Query("query_term p", "p.doc_id", "p.int_val")
        query.join("active_doc d", "d.id = p.doc_id")
        query.join("#ip i", "i.sid = p.int_val")
        query.where("p.doc_id NOT IN (SELECT sid from #ip)")
        query.where(f"p.path = '{self.PARENT_PATH}'")
        while self.cursor.rowcount:
            self.conn.commit()
            self.cursor.execute(f"INSERT INTO #ip (sid, pid) {query}")

    def __collect_terms(self):
        """Create the `Term` objects and return the top of the tree."""

        # Start by collecting the terms which are semantic types.
        query = self.Query("#ip i", "i.sid", "i.pid", "n.value").order("i.pid")
        query.join("query_term n", "n.doc_id = i.sid")
        query.where("n.path = '/Term/PreferredName'")
        for row in query.execute(self.cursor).fetchall():
            if row.pid:
                if self._patriarch and self._patriarch.id == row.pid:
                    term = Term(self, row.sid, row.value, True)
                else:
                    term = Term(self, row.sid, row.value)
                term.parents.add(row.pid)
            else:
                self._patriarch = term = Term(self, row.sid, row.value)
            self.terms[term.id] = term

        # Populate parent->child links for what we have so far.
        for term in self.terms.values():
            for pid in term.parents:
                self.terms[pid].children.add(term.id)

        # Pull in the terms whose semantic types we have collected.
        query = self.Query("#ip i", "i.sid", "t.doc_id", "n.value")
        query.join("query_term t", "t.int_val = i.sid")
        query.join("query_term n", "n.doc_id = t.doc_id")
        query.join("active_doc d", "d.id = t.doc_id")
        query.where("t.path = '/Term/SemanticType/@cdr:ref'")
        query.where("n.path = '/Term/PreferredName'")
        self.cursor.execute(f"INSERT INTO #terms (sid, tid, name) {query}")
        self.conn.commit()
        query = self.Query("#terms", "tid", "name")
        for row in query.execute(self.cursor).fetchall():
            if row.tid not in self.terms:
                self.terms[row.tid] = Term(self, row.tid, row.name)

        # Finish connecting the parents and children.
        query = self.Query("#terms t", "t.tid", "p.int_val AS pid")
        query.join("query_term p", "p.doc_id = t.tid")
        query.join("active_doc d", "d.id = p.int_val")
        query.where(f"p.path = '{self.PARENT_PATH}'")
        for row in query.execute(self.cursor).fetchall():
            if row.pid in self.terms:
                self.terms[row.pid].children.add(row.tid)
                self.terms[row.tid].parents.add(row.pid)

        # Finally, collect the term name aliases.
        if self.flavor == "long":
            query = self.Query("query_term o", "o.doc_id", "o.value AS name")
            query.join("#terms t", "t.tid = o.doc_id")
            query.where("o.path = '/Term/OtherName/OtherTermName'")
            for row in query.execute(self.cursor).fetchall():
                self.terms[row.doc_id].aliases.add(row.name)


class Term:
    """Node in the report's tree."""

    def __init__(self, control, id, name, top=False):
        """Save the caller's value and prepare some empty sets.

        Pass:
            control - access to report-building tools
            id - CDR ID for the Term document
            name - preferred name string
            top - True if term is connected directly to the tree's top node
        """

        self.control = control
        self.id = id
        self.name = name
        self.parents = set()
        self.children = set()
        self.aliases = set()
        self.top = top

    def __lt__(self, other):
        """Support sorting by name, without regard to case."""
        return self.name.lower() < other.name.lower()

    @property
    def level(self):
        """Class name (u or l) to denote whether we're upper or lower."""
        return "u" if self.top else "l"

    @property
    def node(self):
        """HTML list item node with name and possibly recursive child lists."""

        B = self.control.HTMLPage.B
        node = B.LI(self.name, B.CLASS(self.level))
        if self.children or self.aliases:
            ul = B.UL()
            for alias in sorted(self.aliases, key=str.lower):
                ul.append(B.LI(f"x {alias}", B.CLASS("a")))
            children = [self.control.terms[id] for id in self.children]
            for child in sorted(children):
                ul.append(child.node)
            node.append(ul)
        return node


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
