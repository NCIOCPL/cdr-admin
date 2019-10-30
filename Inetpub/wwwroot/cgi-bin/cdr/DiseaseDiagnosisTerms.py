#!/usr/bin/env python

"""Generate hierarchical report of terminology under Disease/Diagnosis.
"""

from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "CDR Cancer Diagnosis Hierarchy Report"
    LOGNAME = "DiseaseDiagnosisTerms"
    CSS = (
        "ul.t { width: 600px; margin: 15px auto; }",
        "li { list-style: none; font-size: 14px; }",
        "li.u { color: green; font-weight: bold; font-family: serif; }",
        "li.i { font-variant: small-caps; }",
        "li.l { color: blue; font-variant: normal; }",
        "li.a { color: #FF2222; font-size: 12px; font-style: italic; }",
        "li.a { font-variant: normal; }",
    )


    def show_form(self):
        """Bypass the form, which isn't needed for this report."""
        self.show_report()

    def show_report(self):
        """Override base class method, because we're not using Report class."""

        buttons = (
            self.HTMLPage.button(self.SUBMENU),
            self.HTMLPage.button(self.ADMINMENU),
            self.HTMLPage.button(self.LOG_OUT),
        )
        opts = dict(
            buttons=buttons,
            session=self.session,
            action=self.script,
            banner=self.title,
            footer=self.footer,
            subtitle=self.subtitle,
        )
        top = self.tree.top
        top = self.tree.terms[top].node
        report = self.HTMLPage(self.title, **opts)
        wrapper = report.B.UL(top, self.footer, report.B.CLASS("t"))
        report.body.append(wrapper)
        report.body.set("class", "report")
        report.add_css("\n".join(self.CSS))
        report.send()

    @property
    def flavor(self):
        """Boolean - if "short" don't collect or show aliases."""
        return self.fields.getvalue("flavor")

    @property
    def tree(self):
        """Dictionary of terms for the report."""

        if not hasattr(self, "_tree"):
            try:
                self._tree = Tree(self)
            except Exception as e:
                self.logger.exception("Failure building tree")
        return self._tree


class Tree:
    """CDR Term document hierarchy for the report"""

    SEED = "malignant neoplasm"
    CREATE = "CREATE TABLE #terms(id INTEGER, parent INTEGER)"
    PARENT = "/Term/TermRelationship/ParentTerm/TermId/@cdr:ref"
    TERM_TYPE = "/Term/TermType/TermTypeName"

    def __init__(self, control):
        """Save the control object for future processing.

        Pass:
            control - access the HTML build and the database
        """

        self.__control = control

    @property
    def control(self):
        """Access to HTML builder and the database."""
        return self.__control

    @property
    def terms(self):
        """Dictionary of all the terms in the tree."""
        return self._terms

    @property
    def top(self):
        """Top node ID in the Hierarchical dictionary of terms in the tree."""

        if not hasattr(self, "_top"):
            self._top = None
            self.__create_table()
            self.__seed_table()
            self.__load_table()
            self.__query_table()
            self.__collect_terms()
        return self._top

    def __collect_terms(self):
        """Walk through the rows in the new temporary table."""

        # Load the terms into the tree.
        self._terms = {}
        for id, name, parent in self.control.cursor.fetchall():
            term = self._terms.get(id)
            if not term:
                term = self._terms[id] = self.Term(self, name)
            if not parent:
                self._top = id
            elif parent not in term.parents:
                term.parents.append(parent)

        # Gather in the children.
        for term in self._terms.values():
            for parent in term.parents:
                try:
                    alreadyHaveIt = 0
                    for child in self._terms[parent].children:
                        if child.name == term.name:
                            alreadyHaveIt = 1
                            break
                    if not alreadyHaveIt:
                        self._terms[parent].children.append(term)
                except:
                    cdrcgi.bail("No object for parent %s" % str(parent))

        # Optionally collect aliases.
        if self.control.flavor != "short":
            self.control.cursor.execute(
                "SELECT DISTINCT q.doc_id, q.value"
                "           FROM query_term q"
                "           JOIN #terms t"
                "             ON t.id = q.doc_id"
                "          WHERE q.path = '/Term/OtherName/OtherTermName'")
            for id, name in self.control.cursor.fetchall():
                if name not in self._terms[id].aliases:
                    self._terms[id].aliases.append(name)

    def __create_table(self):
        """Create a temporary table for the tree."""

        self.control.cursor.execute(self.CREATE)
        self.control.conn.commit()

    def __seed_table(self):
        """Initialize the temporary table with the tree's top node."""

        self.control.cursor.execute(
            "INSERT INTO #terms"
            "     SELECT doc_id, NULL"
            "       FROM query_term"
            "      WHERE path = '/Term/PreferredName'"
            "        AND value = ?", self.SEED)
        self.control.conn.commit()

    def __load_table(self):
        """Recursively insert the lower branches of the tree."""

        args = self.PARENT, self.TERM_TYPE
        while self.control.cursor.rowcount:
            self.control.cursor.execute(
                "INSERT INTO #terms"
                "     SELECT p.doc_id, p.int_val"
                "       FROM query_term p"
                "       JOIN #terms t"
                "         ON t.id = p.int_val"
                "      WHERE p.path = ?"
                "        AND NOT EXISTS ("
                "            SELECT *"
                "              FROM #terms"
                "              WHERE id = p.doc_id"
                "                AND parent = p.int_val)"
                "        AND p.doc_id NOT IN ("
                "            SELECT doc_id"
                "              FROM query_term"
                "             WHERE path = ?"
                "               AND value = 'Obsolete term')", *args)
        self.control.conn.commit()

    def __query_table(self):
        """Select all of the rows from our new temporary table."""

        self.control.cursor.execute(
            "SELECT d.id, n.value, d.parent"
            "  FROM #terms d"
            "  JOIN query_term n"
            "    ON n.doc_id = d.id"
            " WHERE n.path = '/Term/PreferredName'")


    class Term:
        def __init__(self, tree, name):
            """Capture the caller's values and prepare empty lists.

            Pass:
                tree - access to the controller and the top node
                name - string for the name of this term
            """

            self.tree = tree
            self.name = name
            self.aliases = []
            self.children = []
            self.parents = []

        def __lt__(self, other):
            """Support sorting by name, case insensitive."""
            return self.name.lower() < other.name.lower()

        @property
        def level(self):
            """Will be 'u' for upper terms and 'l' for lower terms."""
            if not hasattr(self, "_level"):
                self._level = "l"
                if not self.parents or self.tree.top in self.parents:
                    self._level = "u"
                #else:
                #    for parent in self.parents:
                #        if parent.name == Tree.TOP:
                #            self._level = "u"
                #            break
            return self._level

        @property
        def node(self):
            """Create the HTML node for the report."""

            B = self.tree.control.HTMLPage.B
            node = B.LI(self.name, B.CLASS(self.level))
            if self.children or self.aliases:
                ul = B.UL()
                for alias in sorted(self.aliases, key=str.lower):
                    ul.append(B.LI(f"x {alias}", B.CLASS("a")))
                for child in sorted(self.children):
                    ul.append(child.node)
                node.append(ul)
            return node


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
