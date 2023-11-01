#!/usr/bin/env python

"""Show the users the available XMetaL icons.
"""

from pathlib import Path
from cdrcgi import Controller
from lxml.html import tostring


class Control(Controller):
    SUBTITLE = "XMetaL CDR Icons"
    NAMES = dict(
        Annotations="Annotations (Custom)",
        Databases="Databases (Custom)",
        Design="Design (Custom)",
        General="General (Custom)",
        Integration="Integration (Custom)",
        Misc1="Misc 1 (Custom)",
        Misc2="Misc 2 (Custom)",
        Revisions="Revisions (Custom)",
        Shapes="Shapes (Custom)",
        Structure="Structure (Custom)",
    )
    CSS = "img { border: 1px black solid } * { font-family: Arial; }"
    PATH = Path("d:/Inetpub/wwwroot/images/xmetal")
    INSTRUCTIONS = (
        "Press Submit to bring up a page showing the button icons "
        "which are available for use on the CDR toolbars in XMetaL. "
        "The icons are grouped in blocks. Each block has a name "
        "displayed at the top of the block and numbering for the "
        "rows and columns in which each separate icon is stored. "
        "When requesting a new toolbar button, select the desired "
        "icon to be displayed for the button, and provide the name "
        "of its block, as well the row and column in which it is "
        "stored, in the JIRA ticket requesting the new toolbar macro."
    )

    def populate_form(self, page):
        """Explain the report.

        Required positional argument:
          page - instance of the HTMLPage class
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)

    def show_report(self):
        """Override to display custom report."""

        B = self.HTMLPage.B
        content = B.CENTER(B.H1("XMetaL CDR Icons"))
        for path in sorted(self.PATH.glob("*.jpg")):
            name = path.name[:-4]
            if "xmetal_cdr" not in name and "Standard" not in name:
                content.append(B.H2(self.NAMES.get(name, name)))
                content.append(B.IMG(src=f"/images/xmetal/{name}.jpg"))
        page = B.HTML(
            B.HEAD(
                B.TITLE("XMetaL CDR Icons"),
                B.STYLE(self.CSS)
            ),
            B.BODY(content)
        )
        html = tostring(page, encoding="unicode")
        print(f"Content-type: text/html\n\n{html}")
        exit(0)


if __name__ == "__main__":
    """Avoid execution when loaded as a module."""
    Control().run()
