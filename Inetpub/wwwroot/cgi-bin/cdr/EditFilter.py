#!/usr/bin/env python

"""View filter code or compare with another tier.
"""

from cdrapi.docs import Doc
from cdrcgi import Controller
from difflib import Differ
from lxml import etree
from requests import post


class Control(Controller):
    """Access to the database and form-building tools."""

    LOGNAME = "filters"
    TIERS = "PROD", "STAGE", "QA", "DEV"
    VIEW = "View"
    COMPARE = "Compare"
    FILTERS = "Filters"
    NORMALIZE_TOOLTIP = (
        "Not usually recommended, unless the formatting",
        "of one of the documents has been seriously mangled.",
    )
    CSS = (
        ".del { background-color: #fafad2; } /* light goldenrod yellow */",
        ".add { background-color: #f0e68c; } /* khaki */",
        ".pnt { background-color: #87cefa; } /* light sky blue */",
        "@media print {",
        "    h1, fieldset { display: none; }",
        "    h2 { font-size: 2em; }",
        "    pre { border: none; }",
    )
    CLASSES = {"-": "del", "+": "add", "?": "pnt"}

    def run(self):
        """Override the base class version, as this isn't a standard report."""

        if not self.doc or self.request == self.FILTERS:
            self.navigate_to("EditFilters.py", self.session.name)
        elif not self.request or self.request in (self.VIEW, self.COMPARE):
            self.show_form()
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Show the form and the filter (possibly compared with another tier).

        Pass:
            page - HTMLPage object on which the form and filter are placed
        """

        page.form.append(page.hidden_field(self.DOCID, self.doc.id))
        fieldset = page.fieldset("Select Stage For Filter Comparison")
        for tier in self.TIERS:
            if tier != self.session.tier.name:
                checked = tier == self.default_tier
                opts = dict(value=tier, label=tier, checked=checked)
                fieldset.append(page.radio_button("tier", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Comparison Options")
        opts = dict(label="Show all lines?", value="full", checked=self.full)
        opts["tooltip"] = "Leave unchecked to see just the changes."
        fieldset.append(page.checkbox("options", **opts))
        label = "Parse documents to normalize them?"
        opts = dict(label=label, value="normalize", checked=self.normalize)
        opts["tooltip"] = "\n".join(self.NORMALIZE_TOOLTIP)
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)
        if self.diff is not None:
            fieldset = page.fieldset("Filter Comparison")
            fieldset.append(self.diff)
        else:
            fieldset = page.fieldset("Filter Document")
            fieldset.append(page.B.PRE(self.doc.xml.strip()))
        page.form.append(fieldset)
        page.add_css("\n".join(self.CSS))

    @property
    def same_window(self):
        """We're already in a separate tab; don't open any more."""
        return self.COMPARE, self.FILTERS, self.VIEW

    @property
    def buttons(self):
        """Customize the command buttons."""

        if self.request and self.request != self.VIEW:
            return self.VIEW, self.COMPARE, self.FILTERS
        return self.COMPARE, self.FILTERS

    @property
    def default_tier(self):
        """Natural tier against which to compare our filter."""
        return "DEV" if self.session.tier.name == "PROD" else "PROD"

    @property
    def diff(self):
        """String for differences between two tiers, if requested."""

        if self.request != self.COMPARE:
            return None
        if not hasattr(self, "_diff"):
            host = "cdr.cancer.gov"
            if self.tier != "PROD":
                host = f"cdr-{self.tier.lower()}.cancer.gov"
            url = f"https://{host}/cgi-bin/cdr/get-filter.py"
            self.logger.info("url=%s", url)
            parms = dict(title=self.doc.title)
            response = post(url, data=parms, timeout=5)
            if not response.ok:
                self.bail(f"{self.doc.title} not found on {host}")
            if self.normalize:
                root = etree.fromstring(response.content)
                other = etree.tostring(root, encoding="unicode")
                mine = etree.tostring(self.doc.root, encoding="unicode")
            else:
                other = response.text
                mine = self.doc.xml
            filters = [other, mine]
            tiers = [self.tier, self.session.tier.name]
            if self.higher:
                filters.reverse()
                tiers.reverse()
            for i in range(len(filters)):
                filters[i] = filters[i].strip().replace("\r", "").splitlines()
            differ = Differ()
            B = self.HTMLPage.B
            title = self.doc.title
            pre = B.PRE(
                B.SPAN(f"- {title} on {tiers[0]}\n", B.CLASS("del")),
                B.SPAN(f"+ {title} on {tiers[1]}\n", B.CLASS("add")),
                "\n"
            )
            self.logger.info("comparing %s with %s", *tiers)
            for line in differ.compare(*filters):
                if line[0] != "?":
                    line += "\n"
                if line[0] in self.CLASSES:
                    pre.append(B.SPAN(line, B.CLASS(self.CLASSES[line[0]])))
                elif self.full:
                    pre.append(B.SPAN(line))
            self._diff = pre
        return self._diff

    @property
    def doc(self):
        """`Doc` object for filter to display or compare."""

        if not hasattr(self, "_doc"):
            id = self.fields.getvalue(self.DOCID)
            if not id:
                self.bail()
            self._doc = Doc(self.session, id=id)
        return self._doc

    @property
    def full(self):
        """True if we should show all the lines in the diff output."""
        return True if "full" in self.options else False

    @property
    def higher(self):
        """True if this tier is higher than the one we're comparing with."""

        tier = self.session.tier.name
        return self.TIERS.index(tier) < self.TIERS.index(self.tier)

    @property
    def method(self):
        """Override HTTP method."""
        return "get"

    @property
    def normalize(self):
        """True if we should parse the documents before comparing them."""
        return True if "normalize" in self.options else False

    @property
    def options(self):
        """Comparison options for the diff report."""

        if not hasattr(self, "_options"):
            self._options = self.fields.getlist("options")
        return self._options

    @property
    def subtitle(self):
        """String to be displayed directly under the main banner."""
        return f"{self.doc.title} ({self.doc.cdr_id})"

    @property
    def tier(self):
        """Tier with which we compare the filter."""
        return self.fields.getvalue("tier") or self.default_tier


if __name__ == "__main__":
    "Allow documentation and lint to import this without side effects"
    Control().run()
