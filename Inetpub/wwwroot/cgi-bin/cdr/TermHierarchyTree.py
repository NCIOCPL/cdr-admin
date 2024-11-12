#!/usr/bin/env python

"""Show terminalogy hierarchy.
"""

from collections import defaultdict
from functools import cached_property
from cdrcgi import Controller, BasicWebPage


class Control(Controller):
    """Access to the database and HTML page generation tools."""

    SUBTITLE = "Term Hierarchy Tree"
    LOGNAME = "TermHierarchyTree"
    CSS = "../../stylesheets/TermHierarchyTree.css"
    SCRIPT = "../../js/TermHierarchyTree.js"
    PARENT_PATH = "/Term/TermRelationship/ParentTerm/TermId/@cdr:ref"
    INSTRUCTIONS = (
        "This report provides an interactive interface for navigating "
        "through the CDR terminology hierarcchy, collapsing and expanding "
        "nodes dynamically, with the ability to copy the document IDs "
        "for a given subset of the tree into the clipboard. The leaf nodes "
        "of the tree are displayed in a teal color. Nodes which have children "
        "have a navy font color."
    )

    def populate_form(self, page):
        """Explain the report.

        Required positional argument:
          page - instance of HTMLPage
        """

        if not self.fields.getvalue("prompt"):
            self.show_report()
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)

    def show_report(self):
        """Override the base class version, as this is not a tabular report."""

        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        report.head.append(report.B.SCRIPT(src=self.HTMLPage.JQUERY))
        report.head.append(report.B.SCRIPT(src=self.SCRIPT))
        report.head.append(report.B.LINK(href=self.CSS, rel="stylesheet"))
        report.body.append(self.tree)
        report.body.append(self.clipboard)
        report.body.append(self.footer)
        report.send()

    @cached_property
    def children(self):
        """Dictionary indexing child term IDs by their parent term IDs."""

        children = {}
        for child, parent in self.parent_links:
            if parent not in children:
                children[parent] = [child]
            else:
                children[parent].append(child)
        return children

    @cached_property
    def clipboard(self):
        """Fallback in case the browser doesn't support the real clipboard."""

        clipboard = self.HTMLPage.fieldset("Copied CDR IDs")
        clipboard.set("class", "hidden")
        clipboard.set("id", "clipboard")
        clipboard.append(self.HTMLPage.B.TEXTAREA())
        return clipboard

    @property
    def id(self):
        """Unique ID generator for term nodes (don't use @cached_property)."""

        if not hasattr(self, "_id"):
            self._id = 0
        self._id += 1
        return self._id

    @cached_property
    def obsolete(self):
        """Terms to be skipped."""

        query = self.Query("query_term", "doc_id")
        query.where("path = '/Term/TermType/TermTypeName'")
        query.where("value = 'Obsolete term'")
        rows = query.execute(self.cursor)
        return {row.doc_id for row in rows}

    @cached_property
    def parent_links(self):
        """Sequence of parent ID, child ID tuples."""

        query = self.Query("query_term", "doc_id", "int_val").unique()
        query.where(query.Condition("path", self.PARENT_PATH))
        rows = query.execute(self.cursor)
        return [tuple(row) for row in rows]

    @cached_property
    def parents(self):
        """Dictionary indexing parent term IDs by their child term IDs."""

        parents = {}
        for child, parent in self.parent_links:
            if child not in self.obsolete and parent not in self.obsolete:
                if child not in parents:
                    parents[child] = [parent]
                else:
                    parents[child].append(parent)
        return parents

    @cached_property
    def semantic_types(self):
        """Unique IDs for terms whose term type is 'Semantic type'."""

        query = self.Query("query_term", "doc_id").unique()
        query.where("path = '/Term/TermType/TermTypeName'")
        query.where("value = 'Semantic type'")
        rows = query.execute(self.cursor)
        return {row.doc_id for row in rows}

    @property
    def terms(self):
        """Collect the terms for the report.

        The logging of parents and children cannot be eliminated,
        as it is needed for populating the children and parents
        properties of the `Term` objects.

        Caching has to be done by hand, because of the dependency on
        the `parents` property of the `Term` object, which needs to
        see this property while it's still in the process of being
        created.
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

    @cached_property
    def top(self):
        """Top-level (orphan) semantic types."""

        top = []
        for id in self.terms:
            if id in self.semantic_types:
                term = self.terms[id]
                if not term.parents:
                    top.append(term)
        return top

    @cached_property
    def tree(self):
        """This is what the folks came to see."""

        tree = self.HTMLPage.B.UL()
        tree.set("class", "treeview")
        for term in sorted(self.top):
            tree.append(term.node)
        return tree

    def find_terms_in_multiple_top_level_trees(self):
        """Not used by this script. Invoke for debugging."""

        subtrees = [self.load_subtree(root) for root in self.top]
        terms = defaultdict(list)
        for subtree in subtrees:
            for id in subtree.descendants:
                terms[id].append(subtree)
        report = dict(found=[], checked=sum(s.checked for s in subtrees))
        for id in sorted(terms):
            if len(terms[id]) > 1:
                values = dict(
                    id=id,
                    name=self.terms[id].name,
                    subtrees=[subtree.root.name for subtree in terms[id]],
                )
                report["found"].append(values)
        report["elapsed"] = str(self.elapsed)
        return report

    @staticmethod
    def load_subtree(term, subtree=None):
        """Called recursively by debugging routine.

        Pass:
          subtree - None for top of subtree
        """

        if subtree is None:
            class Subtree:
                def __init__(self, term):
                    self.root = term
                    self.descendants = {}
                    self.checked = 0
            subtree = Subtree(term)
        for child in term.children:
            subtree.checked += 1
            subtree.descendants[child.id] = child
            Control.load_subtree(child, subtree)
        return subtree


class Term:
    """Term document from the CDR repository."""

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to logging and the other terms
            row - database row for this term
        """

        self.control = control
        self.row = row

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
    def children(self):
        """Terms of which this node is a parent.

        Make this property available to the control object during population.
        """

        if not hasattr(self, "_children"):
            self._children = []
            children = self.control.children.get(self.id)
            if children:
                for id in children:
                    term = self.control.terms.get(id)
                    if term and term.is_semantic_type == self.is_semantic_type:
                        self._children.append(term)
        return self._children

    @cached_property
    def id(self):
        """Integer ID for this term's CDR document."""
        return self.row.doc_id

    @cached_property
    def is_semantic_type(self):
        """True if one of this term's types is 'Semantic type'."""
        return self.id in self.control.semantic_types

    @cached_property
    def key(self):
        """Support case-insensitive sorting."""
        return self.name.lower()

    @cached_property
    def leaves(self):
        """Unique IDs of descendant leaf nodes under this term."""

        leaves = set()
        for child in self.children:
            if not child.children:
                leaves.add(child.id)
            else:
                leaves |= child.leaves
        return leaves

    @cached_property
    def name(self):
        """The preferred name for this term."""
        return self.row.value

    @property
    def node(self):
        """HTML li element node for this term.

        This can't be cached, because the same term may show up in
        more than one part of the tree, and each occurrence needs its
        own instance.
        """

        B = self.control.HTMLPage.B
        if self.children:
            args = self.name, self.children
            self.control.logger.debug("%s children: %s", *args)
            if self.name == "AIDS-related malignancies":
                self.control.logger.info("%s children: %s", *args)
            id = f"li-{self.control.id}"
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
        """Terms of which this is a child.

        Caching has to be done by hand, because of the dependency on
        the `terms` property of the `control` object, which needs to
        see this property while it's still in the process of being
        created.
        """

        if not hasattr(self, "_parents"):
            self._parents = []
            parents = self.control.parents.get(self.id)
            if parents:
                for id in parents:
                    term = self.control.terms.get(id)
                    if term and term.is_semantic_type == self.is_semantic_type:
                        self._parents.append(term)
                    if not self._parents and not self.is_semantic_type:
                        for id in parents:
                            term = self.control.terms.get(id)
                            if term:
                                term.children.append(self)
                                self._parents.append(term)
        return self._parents


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
