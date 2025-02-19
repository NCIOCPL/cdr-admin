#!/usr/bin/env python

"""Display counts of selected elements in summaries.

   The elements currently included are:
     - Comment
     - EmbeddedVideo
     - MediaLink
     - MiscellaneousDocLink
     - StandardWording
     - SummaryModuleLink
     - Table

   This report can help answering questions like: "Which summaries
   include a video?" or "I need a drug summary with a table."
"""

from functools import cached_property
from cdrcgi import Controller, BasicWebPage
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Elements Included In PDQ Summaries"
    ELEMENTS = dict(
        Table="table",
        SummaryModuleLink="module-link",
        MiscellaneousDocLink="misc-doc-link",
        MediaLink="media-link",
        EmbeddedVideo="embedded-video",
        StandardWording="standard-wording",
        Comment="comment",
    )
    CSS = (
        ".summary          { color: blue; font-weight: normal; }",
        ".module-link      { color: red; }",
        ".misc-doc-link    { color: brown; }",
        ".media-link       { color: green; }",
        ".table            { color: purple; }",
        ".embedded-video   { color: deeppink; }",
        ".standard-wording { color: lime; }",
        ".comment          { color: fuchsia; }",
        ".error            { color: red; font-weight: bold; }",
        ".element-list     { margin-bottom: 2rem; }",
        ".element-list li  { margin-bottom: 0; line-height: 1.5 }",
        ".element-list, dl { font-size: 1.06rem; }",
        "dl *              { line-height: 1.3 }",
    )
    DOCTYPES = [
        ("cis", "Cancer Information Summaries", True),
        ("dis", "Drug Information Summaries", False),
    ]
    DOCTYPE_NAMES = dict(
        cis="Summary",
        dis="DrugInformationSummary",
    )

    def populate_form(self, page):
        """Choose document type for report.

        Required positional argument:
          page - HTMLPage object
        """

        fieldset = page.fieldset("Choose summary type")
        for value, label, checked in self.DOCTYPES:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("doctype", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Override the base class version, as this isn't a tabular report."""

        B = self.HTMLPage.B
        dl = B.DL()
        for summary in self.summaries:
            dl.append(summary.dt)
            for dd in summary.dds:
                dl.append(dd)
        elements = B.UL(B.CLASS("usa-list element-list"))
        for tag in sorted(self.ELEMENTS):
            element = B.LI(tag, B.CLASS(self.ELEMENTS[tag]))
            elements.append(element)
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        report.wrapper.append(B.H2("Report Elements"))
        report.wrapper.append(elements)
        report.wrapper.append(B.H2("Summaries"))
        report.wrapper.append(dl)
        report.wrapper.append(self.footer)
        report.head.append(report.B.STYLE("\n".join(self.CSS)))
        report.send()

    @cached_property
    def doctype(self):
        """Key to document type selection from form."""
        return self.fields.getvalue("doctype") or "cis"

    @property
    def no_results(self):
        """Suppress the message we'd normally get with no report tables."""
        return None

    @cached_property
    def subtitle(self):
        """Override page title for DIS report."""

        if self.doctype == "dis":
            return "Elements Included in PDQ Drug Information Summaries"
        return self.SUBTITLE

    @cached_property
    def summaries(self):
        """PDQ Summaries included in the report."""

        doctype = self.DOCTYPE_NAMES[self.doctype]
        query = self.Query("document d", "d.id").order("d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", doctype))
        query.where("d.title NOT LIKE '%BLOCKED%'")
        rows = query.execute(self.cursor).fetchall()
        return [Summary(self, row.id) for row in rows]


class Summary:
    """PDQ cancer information summary represented on the report."""

    MODULE_LINK = "SummaryModuleLink"
    MODULE_CLASS = Control.ELEMENTS[MODULE_LINK]
    CDR_REF = f"{{{Doc.NS}}}ref"

    def __init__(self, control, id):
        """Capture the caller's values.

        Pass:
            control - access to page-building tools
        """

        self.__control = control
        self.__id = id

    @property
    def counts(self):
        """Count of all of the elements except summary module links."""

        if not hasattr(self, "_counts"):
            self._counts = {}
            for tag in Control.ELEMENTS:
                if tag != self.MODULE_LINK:
                    try:
                        for node in self.doc.root.iter(tag):
                            self._counts[tag] = self._counts.get(tag, 0) + 1
                    except Exception:
                        print(self.doc.id)
                        raise
        return self._counts

    @property
    def dds(self):
        """Information about the summary's elements, wrapped in dd elements."""

        dds = []
        if self.doc.root is not None:
            for tag in sorted(self.counts):
                count = self.counts[tag]
                display = f"{count:d} {tag}"
                if count > 1:
                    display = f"{display}s"
                dd = self.__control.HTMLPage.B.DD(display)
                dd.set("class", Control.ELEMENTS[tag])
                dds.append(dd)
            for link in self.module_links:
                display = f"{self.MODULE_LINK} {link}"
                dd = self.__control.HTMLPage.B.DD(display)
                dd.set("class", self.MODULE_CLASS)
                dds.append(dd)
        return dds

    @property
    def doc(self):
        """`Doc` object for the summary."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.__id)
        return self._doc

    @property
    def dt(self):
        """Identification of the summary wrapped in an HTML dt element."""

        dt = self.__control.HTMLPage.B.DT(f"{self.doc.title} ({self.doc.id})")
        dt.set("class", "summary")
        return dt

    @property
    def module_links(self):
        """Sequence of links to summary modles."""

        if not hasattr(self, "_module_links"):
            self._module_links = []
            if self.doc.root is not None:
                for node in self.doc.root.iter(self.MODULE_LINK):
                    self._module_links.append(node.get(self.CDR_REF))
        return self._module_links


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
