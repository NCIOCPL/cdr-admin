#!/usr/bin/env python

"""Show terminalogy hierarchy.
"""

from cdrcgi import Controller


class Control(Controller):
    """Access to the database and HTML page generation tools."""

    SUBTITLE = "Term Hierarchy Tree"
    LOGNAME = "TermHierarchyTree"
    STYLESHEET = "../../stylesheets/TermHierarchyTree.css"
    SCRIPT = "../../js/TermHierarchyTree.js"
    PARENT_PATH = "/Term/TermRelationship/ParentTerm/TermId/@cdr:ref"

    def show_form(self):
        """Re-route straight to the report, as we need no input options."""
        self.show_report()

    def show_report(self):
        """Override the base class version, as this is not a tabular report."""

        buttons = (
            self.HTMLPage.button(self.SUBMENU),
            self.HTMLPage.button(self.ADMINMENU),
            self.HTMLPage.button(self.LOG_OUT),
        )
        opts = dict(
            buttons=buttons,
            subtitle=self.SUBTITLE,
            method="get",
            session=self.session,
        )
        page = self.HTMLPage(self.TITLE, **opts)
        page.head.append(page.B.LINK(href=self.STYLESHEET, rel="stylesheet"))
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))
        page.body.append(self.tree)
        page.body.append(self.clipboard)
        page.body.append(self.footer)
        page.send()

    @property
    def children(self):
        """Dictionary indexing child term IDs by their parent term IDs."""

        if not hasattr(self, "_children"):
            self._children = {}
            for child, parent in self.parent_links:
                if parent not in self._children:
                    self._children[parent] = [child]
                else:
                    self._children[parent].append(child)
        return self._children

    @property
    def clipboard(self):
        """Fallback in case the browser doesn't support the real clipboard."""

        if not hasattr(self, "_clipboard"):
            self._clipboard = self.HTMLPage.fieldset("Copied CDR IDs")
            self._clipboard.set("class", "hidden")
            self._clipboard.set("id", "clipboard")
            self._clipboard.append(self.HTMLPage.B.TEXTAREA())
        return self._clipboard

    @property
    def id(self):
        """Unique ID generator for term nodes."""

        if not hasattr(self, "_id"):
            self._id = 0
        self._id += 1
        return self._id

    @property
    def obsolete(self):
        """Terms to be skipped."""

        if not hasattr(self, "_obsolete"):
            query = self.Query("query_term", "doc_id")
            query.where("path = '/Term/TermType/TermTypeName'")
            query.where("value = 'Obsolete term'")
            rows = query.execute(self.cursor)
            self._obsolete = {row.doc_id for row in rows}
        return self._obsolete

    @property
    def parent_links(self):
        """Sequence of parent ID, child ID tuples."""

        if not hasattr(self, "_parent_links"):
            query = self.Query("query_term", "doc_id", "int_val").unique()
            query.where(query.Condition("path", self.PARENT_PATH))
            rows = query.execute(self.cursor)
            self._parent_links = [tuple(row) for row in rows]
        return self._parent_links

    @property
    def parents(self):
        """Dictionary indexing parent term IDs by their child term IDs."""

        if not hasattr(self, "_parents"):
            self._parents = {}
            for child, parent in self.parent_links:
                if child not in self.obsolete and parent not in self.obsolete:
                    if child not in self._parents:
                        self._parents[child] = [parent]
                    else:
                        self._parents[child].append(parent)
        return self._parents

    @property
    def semantic_types(self):
        """Unique IDs for terms whose term type is 'Semantic type'."""

        if not hasattr(self, "_semantic_types"):
            query = self.Query("query_term", "doc_id").unique()
            query.where("path = '/Term/TermType/TermTypeName'")
            query.where("value = 'Semantic type'")
            rows = query.execute(self.cursor)
            self._semantic_types = {row.doc_id for row in rows}
        return self._semantic_types

    @property
    def terms(self):
        """Collect the terms for the report.

        The logging of parents and children cannot be eliminated,
        as it is needed for populating the children and parents
        properties of the `Term` objects.
        """

        if not hasattr(self, "_terms"):
            self._terms = {}
            query = self.Query("query_term n", "n.doc_id", "n.value")
            query.where("n.path = '/Term/PreferredName'")
            query.join("active_doc a", "a.id = n.doc_id")
            for row in query.execute(self.cursor).fetchall():
                if row.doc_id not in self.obsolete:
                    if row.doc_id in self._terms:
                        self.bail(f"too many names for CDR{row.doc_id}")
                    self._terms[row.doc_id] = Term(self, row)
            query = self.Query("query_term", "int_val")
            query.where("path = '/Term/SemanticType/@cdr:ref'")
            query.where("doc_id = ?")
            query = str(query)
            for id in self._terms:
                term = self._terms[id]
                if not term.parents and not term.is_semantic_type:
                    for row in self.cursor.execute(query, id).fetchall():
                        parent = self._terms.get(row.int_val)
                        if parent:
                            term.parents.append(parent)
                            parent.children.append(term)
        return self._terms

    @property
    def top(self):
        """Top-level (orphan) semantic types."""

        if not hasattr(self, "_top"):
            self._top = []
            for id in self.terms:
                if id in self.semantic_types:
                    term = self.terms[id]
                    if not term.parents:
                        self._top.append(term)
        return self._top

    @property
    def tree(self):
        """This is what the folks came to see."""

        if not hasattr(self, "_tree"):
            self._tree = self.HTMLPage.B.UL()
            self._tree.set("class", "treeview")
            for term in sorted(self.top):
                self._tree.append(term.node)
        return self._tree

class Term:
    """Term document from the CDR repository."""

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to logging and the other terms
            row - database row for this term
        """

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Allow the terms to be sorted."""
        return self.key < other.key

    def __str__(self):
        """For debugging display."""
        return f"<Term> {self.name}"

    def __repr__(self):
        """For logging."""
        return f"<Term> {self.name}"

    @property
    def key(self):
        """Support case-insensitive sorting."""
        if not hasattr(self, "_key"):
            self._key = self.name.lower()
        return self._key

    @property
    def name(self):
        """The preferred name for this term."""
        return self.__row.value

    @property
    def id(self):
        """Integer ID for this term's CDR document."""
        return self.__row.doc_id

    @property
    def is_semantic_type(self):
        """True if one of this term's types is 'Semantic type'."""
        return self.id in self.__control.semantic_types

    @property
    def children(self):
        """Terms of which this node is a parent."""

        if not hasattr(self, "_children"):
            self._children = []
            children = self.__control.children.get(self.id)
            if children:
                for id in children:
                    term = self.__control.terms.get(id)
                    if term and term.is_semantic_type == self.is_semantic_type:
                        self._children.append(term)
        return self._children

    @children.setter
    def children(self, value):
        """Allow adoption of orphans which are not semantic types."""
        self._children = value

    @property
    def leaves(self):
        """Unique IDs of descendant leaf nodes under this term."""

        if not hasattr(self, "_leaves"):
            self._leaves = set()
            for child in self.children:
                if not child.children:
                    self._leaves.add(child.id)
                else:
                    self._leaves |= child.leaves
        return self._leaves

    @property
    def node(self):
        """HTML li element node for this term.

        This can't be cached, because the same term may show up in
        more than one part of the tree, and each occurrence needs its
        own instance.
        """

        B = self.__control.HTMLPage.B
        if self.children:
            args = self.name, self.children
            self.__control.logger.debug("%s children: %s", *args)
            if self.name == "AIDS-related malignancies":
                self.__control.logger.info("%s children: %s", *args)
            id = f"li-{self.__control.id}"
            onclick = f"toggle_node(event, '#{id}')"
            sign = B.SPAN("+", B.CLASS("sign"))
            name = B.SPAN(self.name)
            span = B.SPAN(sign, name, onclick=onclick)
            kids = B.UL(*[child.node for child in sorted(self.children)])
            clip = " ".join([str(id) for id in sorted(self.leaves)])
            clip = f"{self.id:d}:{clip}"
            clip = f"send_to_clipboard('{clip}', {len(self.leaves)})"
            copy = "(copy)"
            copy = B.A(copy, onclick=clip, href="#")
            node = B.LI(span, copy, kids, id=id)
            node.set("class", "parent hide")
            return node
        else:
            return B.LI(self.name, B.CLASS("leaf"))

    @property
    def parents(self):
        """Terms of which this is a child."""

        if not hasattr(self, "_parents"):
            self._parents = []
            parents = self.__control.parents.get(self.id)
            if parents:
                for id in parents:
                    term = self.__control.terms.get(id)
                    if term and term.is_semantic_type == self.is_semantic_type:
                        self._parents.append(term)
                if not self._parents and not self.is_semantic_type:
                    for id in parents:
                        term = self.__control.terms.get(id)
                        if term:
                            term.children.append(self)
                            self._parents.append(term)
        return self._parents

    @parents.setter
    def parents(self, value):
        """Allow adoption of orphans which are not semantic types."""
        self._parents = value


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
