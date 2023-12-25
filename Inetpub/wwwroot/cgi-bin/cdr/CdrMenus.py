#!/usr/bin/env python

"""Show CDR Admin menu hierarchy.
"""

from functools import cached_property
from json import loads
from pathlib import Path
from lxml.html import tostring
from cdrcgi import Controller


class Control(Controller):
    """Program logic."""

    SUBTITLE = "CDR Admin Menu Hierarchy"
    LOGNAME = "CdrMenus"
    FONTS = "Source Sans Pro Web,Helvetica Neue,Helvetica,Arial,sans-serif"
    CSS = (
        f"body {{ font-family: {FONTS}; }}",
        "h1 { font-size: 1.4em; }",
        "h2 { font-size: 1.2em; }",
        "h1, h2 { text-align: center; color: maroon; }",
        "strong { color: green; }",
    )

    def show_form(self):
        """Override to generate custom report."""

        try:
            path = Path(self.session.tier.etc) / "menus.json"
            with path.open(encoding="utf-8") as fp:
                json = fp.read()
        except Exception:
            self.logger.exception(f"Failed loading {path}")
            self.bail("Failed loading %s", path)
        if self.fields.getvalue("raw"):
            self.send_page(json, "json")
        B = self.HTMLPage.B
        menus = B.OL()
        for menu in loads(json):
            menus.append(self.show_menu(menu))
        count = self.tracker.count
        unique = len(self.tracker.unique)
        page = B.HTML(
            B.HEAD(
                B.META(charset="utf-8"),
                B.TITLE("CDR Administrative Menus"),
                B.STYLE("\n".join(self.CSS))
            ),
            B.BODY(
                B.H1("CDR Administrative Menus"),
                B.H2(f"{count} Menu items ({unique} unique)"),
                menus
            )
        )
        opts = dict(
            pretty_print=True,
            doctype="<!DOCTYPE html>",
            encoding="unicode",
        )
        self.send_page(tostring(page, **opts))

    def show_menu(self, menu):
        """Recursively convert menu items to DOM objects.

        Required positional argument:
          menu - dictionary of values for a given menu

        Return:
          DOM object for an HTML list item
        """

        B = self.HTMLPage.B
        label = menu["label"]
        script = menu.get("script")
        if script:
            self.tracker.count += 1
            self.tracker.unique.add(script.lower())
            return B.LI(f"{label} - {script}")
        submenu = B.OL()
        for child in menu["children"]:
            submenu.append(self.show_menu(child))
        return B.LI(B.STRONG(label), submenu)

    @cached_property
    def tracker(self):
        """Keep track of how many menu items we have."""

        class Tracker:
            def __init__(self):
                self.count = 0
                self.unique = set()
        return Tracker()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
