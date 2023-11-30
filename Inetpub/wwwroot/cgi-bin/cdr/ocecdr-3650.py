#!/usr/bin/env python

"""Reports on internal links within a summary.

The report is used to support keeping standard treatment options in
sync during the HP reformat process.
"""

from functools import cached_property
from re import sub as re_sub
from sys import maxsize
from cdrcgi import Controller, Reporter
from cdrapi.docs import Doc


class Control(Controller):
    """Report logic."""

    SUBTITLE = ("Report on Links From One Section of a Summary "
                "to Another Section")
    COLUMNS = (
        Reporter.Column("FragID", width="75px"),
        Reporter.Column("Target Section/Subsection", width="500px"),
        Reporter.Column("Linking Section/Subsection", width="500px"),
        Reporter.Column("Text in Linking Node", width="500px"),
        Reporter.Column("In Table?", width="75px"),
        Reporter.Column("In List?", width="75px"),
    )

    def populate_form(self, page):
        """Ask the user for a document ID.

        Pass:
            page - HTMLPage object to which the ID field is attached
        """
        if self.ready:
            return self.show_report()
        if self.problems:
            fieldset = page.fieldset("Problems Were Found")
            for problem in self.problems:
                fieldset.append(page.B.DIV(problem, page.B.CLASS("error")))
            page.form.append(fieldset)
        fieldset = page.fieldset("Specify a Summary Document")
        fieldset.append(page.text_field("id", label="Summary ID"))
        page.form.append(fieldset)

    def build_tables(self):
        """Return the single table for this report."""
        return self.table if self.ready else self.show_form()

    @cached_property
    def doc(self):
        """The `Doc` object for the report's Summary document."""
        return Doc(self.session, id=self.id) if self.id else None

    @cached_property
    def format(self):
        """Generate this report as an Excel workbook."""
        return "excel"

    @cached_property
    def id(self):
        """CDR ID of the summary for this report."""
        return self.fields.getvalue("id", "").strip()

    @cached_property
    def problems(self):
        """Errors to show the user at the top of the form."""
        return []

    @cached_property
    def ready(self):
        """True if we have everything we need for the report."""

        if not self.request:
            return False
        if not self.id:
            self.problems.append("A Summary ID is required.")
            return False
        try:
            if self.doc.doctype.name != "Summary":
                message = f"CDR{self.doc.id} is a {self.doc.doctype} document."
                self.problems.append(message)
                return False
        except Exception:
            message = f"Document {self.id} not found."
            self.logger.exception(message)
            self.problems.append(message)
            return False
        id = f"CDR{self.doc.id}"
        try:
            if not self.rows:
                self.problems.append(f"{id} has no internal links.")
                return False
        except Exception as e:
            message = f"Unexpected failure creating report for {id}: {e}"
            self.problems.append(message)
            return False
        return True

    @cached_property
    def rows(self):
        """Rows for the report table."""

        rows = []
        for target in sorted(self.targets.values()):
            args = target.id, len(target.links)
            self.logger.debug("target %s has %d links", *args)
            opts = {}
            rowspan = len(target.links)
            if rowspan > 1:
                opts = dict(rowspan=rowspan)
            link = target.links[0]
            row = [
                self.Reporter.Cell(target.id, right=True, **opts),
                self.Reporter.Cell(target.section, **opts),
                link.section,
                link.text,
                self.Reporter.Cell(link.in_table, center=True),
                self.Reporter.Cell(link.in_list, center=True),
            ]
            rows.append(row)
            for link in target.links[1:]:
                row = [
                    link.section,
                    link.text,
                    self.Reporter.Cell(link.in_table, center=True),
                    self.Reporter.Cell(link.in_list, center=True),
                ]
                rows.append(row)
        args = len(rows), self.doc.cdr_id
        self.logger.info("%d internal links found in %s", *args)
        return rows

    @cached_property
    def table(self):
        """Create the table for the document's internal links."""

        if self.rows:
            caption = f"Links for CDR{self.doc.id} ({self.doc.title})"
            opts = dict(columns=self.COLUMNS, caption=caption)
            return Reporter.Table(self.rows, **opts)
        return None

    @cached_property
    def targets(self):
        """Collect the targets by following the links."""

        targets = {}
        dead_links = set()
        root = self.doc.root
        opts = dict(namespaces=Doc.NSMAP)
        linking_nodes = root.xpath(self.xpath, **opts)
        for linking_node in linking_nodes:
            link = Link(linking_node)
            if link.id and link.id not in dead_links:
                if link.id not in targets:
                    xpath = f"//*[@cdr:id = '{link.id}']"
                    nodes = root.xpath(xpath, **opts)
                    if len(nodes) > 1:
                        args = len(nodes), self.id
                        self.logger.warning("%d nodes have id %s", *args)
                    if nodes:
                        args = link.id, nodes[0]
                        targets[link.id] = Target(*args)
                    else:
                        self.logger.warning("cdr:id %s not found", link.id)
                        dead_links.add(link.id)
                if link.id in targets:
                    targets[link.id].add(link)
        return targets

    @cached_property
    def xpath(self):
        """String for finding the linking nodes."""
        return f"//*[starts-with(@cdr:href, '{self.doc.cdr_id}#')]"


class Link:
    """A link from one node in the report's document to another."""

    CDR_HREF = f"{{{Doc.NS}}}href"

    def __init__(self, node):
        """Remember the caller's node and start with false flags.

        Pass:
            node - the element containing an internal link
        """

        self.__node = node
        self.__in_table = False
        self.__in_list = False

    @cached_property
    def id(self):
        """The fragment ID for the linking attribute."""
        return self.node.get(self.CDR_HREF, "#").split("#")[1]

    @cached_property
    def in_list(self):
        """'X' if the link is inside a list, otherwise an empty string."""
        return "X" if self.__in_list else ""

    @cached_property
    def in_table(self):
        """'X' if the link is inside a table, otherwise an empty string."""
        return "X" if self.__in_table else ""

    @cached_property
    def node(self):
        """Node containing the cdr:href internal link."""
        return self.__node

    @cached_property
    def section(self):
        """The string for the title of the immediately enclosing section.

        As a side effect, we detect whether we are in a list or a table.
        """

        node = self.node
        while node is not None:
            if node.tag == "SummarySection":
                return Doc.get_text(node.find("Title"))
            if node.tag == "Table":
                self.__in_table = True
            elif node.tag == "ListItem":
                self.__in_list = True
            node = node.getparent()
        return None

    @cached_property
    def text(self):
        """The text content of the linking element."""
        return Doc.get_text(self.node)


class Target:
    """The target node of one of more internal links."""

    def __init__(self, id, node):
        """Save the caller's values and add tracking for linkers.

        Pass:
            id - cdr:id attribute value for this node
            node - element to which one or more internal links exit.
        """

        self.__id = id
        self.__node = node
        self.__links = []

    def __lt__(self, other):
        """Sort numerically, with a fallback for human-created IDs."""
        return self.sortkey < other.sortkey

    def add(self, link):
        """Remember another linker to this target node."""
        self.__links.append(link)

    @cached_property
    def id(self):
        """ID of the target node."""
        return self.__id

    @cached_property
    def links(self):
        """The nodes which link to this one."""
        return self.__links

    @cached_property
    def node(self):
        """Node to which one or more internal links exist."""
        return self.__node

    @cached_property
    def section(self):
        """Title of the nnermost enclosing section for the link target."""

        node = self.node
        while node is not None:
            if node.tag == "SummarySection":
                return Doc.get_text(node.find("Title"))
            node = node.getparent()
        return None

    @cached_property
    def sortkey(self):
        """Sort the targets numerically, if possible, with a fallback."""

        digits = re_sub("[^0-9]+", "", self.id)
        number = int(digits) if digits else maxsize
        return (number, self.id)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
