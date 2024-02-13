#!/usr/bin/env python

"""Fetch an English summary ready for translation.
"""

from functools import cached_property
from html import escape as html_escape
from re import findall, split, sub
from sys import stdout
from lxml import etree, html
from requests import get
from cdr import getDoc, IdAndName, lastVersions, listVersions
from cdrapi.docs import Doc
from cdrapi.settings import Tier
from cdrcgi import Controller, HTMLPage


class Control(Controller):
    """Access to the database, form creation."""

    SUBTITLE = "Fetch English Summary For Translation"
    LOGNAME = "get-english-summary"
    CHANGES = "SummarySection[SectMetaData/SectionType='Changes to summary']"
    INSTRUCTIONS = (
        "Document ID is required, and must be an integer.  Version is "
        "optional, and can be a positive or negative integer (negative "
        "number counts back from the most recent version, so -1 means "
        "last version, -2 is the one before that, etc.).  If the "
        "version is omitted, the current working copy of the document "
        "is retrieved.  You can also give 'last' for the most recent "
        "version, or 'pub' for the latest publishable version.  The "
        "default output is the display of the document in the browser; "
        "select the 'raw' output option to get the XML document itself, "
        "which you can save to your local file system and pass on to "
        "Trados for translation."
    )
    STRIP = (
        "BoardMember",
        "Comment",
        "ComprehensiveReview",
        "DateLastModified",
        "DatedAction",
        "PatientVersionOf",
        "PMID",
        "PdqKey",
        "RelatedDocuments",
        "ReplacementFor",
        "ResponseToComment",
        "TypeOfSummaryChange",
        "WillReplace",
    )
    RAW = (
        "ContentType: text/xml;charset=utf-8\n"
        "Content-disposition: attachment; filename={}\n\n{}"
    )
    CSS = (
        ".tag { color: blue; font-weight: bold }",
        ".name { color: brown }",
        ".value { color: red }",
        "body { background: white; }",
        "pre { font-size: 13px; }",
    )
    URL = "https://www.cancer.gov/espanol/tipos"
    TIERS = (
        ("PROD", "Production"),
        ("STAGE", "Stage"),
        ("QA", "QA"),
        ("DEV", "Development"),
    )

    def populate_form(self, page):
        """Show the fields and the instruction.

        Pass:
            page - canvas on which we draw
        """

        if self.ready:
            return self.show_report()
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Document Selection")
        fieldset.append(page.text_field("id", label="Document ID"))
        fieldset.append(page.text_field("version"))
        fieldset.append(page.select("tier", options=self.TIERS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Output")
        label = "Display (for viewing)"
        opts = dict(value="display", label=label, checked=True)
        fieldset.append(page.radio_button("fmt", **opts))
        opts = dict(value="raw", label="Raw (for import into Trados)")
        fieldset.append(page.radio_button("fmt", **opts))
        page.form.append(fieldset)
        page.add_script("jQuery(function(){jQuery('id').focus();}")

    def show_report(self):
        """Not a standard report, so we override the base class version."""

        if not self.ready:
            return self.show_form()
        args = self.id, self.version, self.fmt
        self.logger.info("doc id=%r version=%r format=%r", *args)
        cdr_id = f"CDR{self.id:010d}"
        if self.raw:
            ver = f"V{self.version:d}" if self.version else ""
            name = f"{cdr_id}{ver}.xml"
            raw = self.RAW.format(name, self.xml)
            stdout.buffer.write(raw.encode("utf-8"))
        else:
            subtitle = f"CDR Document {cdr_id}"
            if self.version:
                subtitle += f" (version {self.version})"
            buttons = (
                HTMLPage.button(self.SUBMENU),
                HTMLPage.button(self.ADMINMENU),
                HTMLPage.button(self.LOG_OUT),
            )
            opts = dict(
                subtitle=subtitle,
                session=self.session,
                action=self.script,
                buttons=buttons,
            )

            class Page(HTMLPage):
                """Customized for raw HTML block."""
                def __init__(self, pre, title, **opts):
                    self.__pre = pre
                    HTMLPage.__init__(self, title, **opts)

                def tostring(self):
                    opts = dict(self.STRING_OPTS, encoding="unicode")
                    string = html.tostring(self.html, **opts)
                    return string.replace("@@PRE@@", self.__pre)
            page = Page(self.display, self.TITLE, **opts)
            page.form.append(page.B.PRE("@@PRE@@"))
            page.add_css("\n".join(self.CSS))
            page.send()

    @staticmethod
    def markup_tag(match):
        """Replace XML tags with placeholders.

        This is a callback used by `display()` below, so what we can apply
        color formatting to make the XML tags easier to find and read in
        the display (i.e., not raw) version of the document.

        Pass:
          match - regex SRE_Match object

        Return:
          replacement Unicode string with placeholders for tags
        """

        s = match.group(1)
        if s.startswith("/"):
            return "</@@TAG-START@@{}@@END-SPAN@@>".format(s[1:])
        trailingSlash = ""
        if s.endswith("/"):
            s = s[:-1]
            trailingSlash = "/"
        pieces = split("\\s", s, 1)
        if len(pieces) == 1:
            return "<@@TAG-START@@{}@@END-SPAN@@{}>".format(s, trailingSlash)
        tag, attrs = pieces
        pieces = ["<@@TAG-START@@{}@@END-SPAN@@".format(tag)]
        for attr, delim in findall("(\\S+=(['\"]).*?\\2)", attrs):
            name, value = attr.split("=", 1)
            pieces.append(" @@NAME-START@@{}=@@END-SPAN@@"
                          "@@VALUE-START@@{}@@END-SPAN@@".format(name, value))
        pieces.append(trailingSlash)
        pieces.append(">")
        return "".join(pieces)

    @cached_property
    def display(self):
        """Colorized markup to show the document prior to download."""

        xml = sub("<([^>]+)>", Control.markup_tag, self.xml)
        doc = html_escape(xml)
        doc = doc.replace("@@TAG-START@@", '<span class="tag">')
        doc = doc.replace("@@NAME-START@@", '<span class="name">')
        doc = doc.replace("@@VALUE-START@@", '<span class="value">')
        return doc.replace("@@END-SPAN@@", "</span>")

    @cached_property
    def fmt(self):
        """One of 'raw' or 'display' (validated)."""

        fmt = self.fields.getvalue("fmt")
        if fmt not in ("raw", "display"):
            self.bail()
        return fmt

    @cached_property
    def id(self):
        """Integer for the CDR document ID."""
        return self.fields.getvalue("id", "").strip()

    @property
    def raw(self):
        """True if we send raw bytes. Else send display version."""
        return self.fmt == "raw"

    @cached_property
    def ready(self):
        """True if we have what we need from the form."""

        if not self.id:
            if self.request:
                message = "Document ID is required."
                return self.bail(message)
            return False
        try:
            int_id = int(self.id)
            self.id = int_id
        except Exception:
            self.logger.exception("id=%s", self.id)
            message = f"Invalid document id {self.id!r}."
            return self.bail(message)
        try:
            last_version, last_pub_version, _ = self.versions
        except Exception:
            message = f"CDR{self.id} not found on {self.tier}."
            return self.bail(message)
        if self.version == "pub":
            if last_pub_version < 1:
                message = (
                    f"CDR{self.id} has no publishable version on {self.tier}."
                )
                return self.bail(message)
            self.version = last_pub_version
        elif self.version == "last":
            if last_version < 1:
                message = f"CDR{self.id} has no versions on {self.tier}."
                return self.bail(message)
            self.version = last_version
        elif self.version:
            try:
                version = int(self.version)
            except Exception:
                message = f"Invalid version {self.version!r}."
                return self.bail(message)
            if version == 0:
                self.version = None
            elif version < 0:
                opts = dict(limit=abs(version), tier=self.tier)
                versions = listVersions("guest", self.id, **opts)
                if len(versions) < abs(version):
                    message = (
                        f"CDR{self.id} only has {len(versions)} "
                        f"versions on {self.tier}."
                    )
                    return self.bail(message)
                self.version = versions[-1][0]
            else:
                self.version = version
        return self.xml is not None

    @cached_property
    def tier(self):
        """Tier from which the document's XML should come."""
        return self.fields.getvalue("tier") or "PROD"

    @cached_property
    def version(self):
        """Which version to get."""
        return self.fields.getvalue("version", "").strip()

    @cached_property
    def versions(self):
        """Version information about the selected document."""
        return lastVersions("guest", self.id, tier=self.tier)

    @cached_property
    def xml(self):
        """Filtered and stripped serialized document."""

        try:
            opts = dict(tier=self.tier, getObject=True)
            if self.version:
                opts["version"] = self.version
            doc = getDoc("guest", self.id, **opts)
            title = doc.ctrl.get("DocTitle", "[no title]")
            cdr_id = doc.id
        except Exception as e:
            self.logger.exception("fetching CDR%s", self.id)
            message = f"Failure fetching CDR{self.id}: {e}"
            return self.bail(message)
        if doc.type != "Summary":
            message = f"CDR{self.id} is a {doc.type} document."
            return self.bail(message)
        try:
            doc = Doc(self.session, xml=doc.xml)
            xml = etree.tostring(doc.resolved, encoding="utf-8")
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.fromstring(xml, parser)
        except Exception as e:
            self.logger.exception("resolving CDR%s", self.id)
            message = f"Failure parsing CDR{self.id}: {e}"
            return self.bail(message)
        hp = None
        node = root.find("PatientVersionOf")
        if node is not None:
            english_hp = node.get(f"{{{Doc.NS}}}ref")
            if english_hp:
                try:
                    hp = self.__get_hp_doc(english_hp)
                except Exception as e:
                    message = f"Failure finding {english_hp}: {e}"
                    self.logger.exception(message)
                    return self.bail(message)
        first = True
        for node in root.findall("SummaryMetaData/MainTopics"):
            if first:
                first = False
            else:
                parent = node.getparent()
                parent.remove(node)
        for node in root.xpath(self.CHANGES):
            first = True
            for child in node.findall("*"):
                if child.tag == "Para" and first:
                    first = False
                    continue
                elif child.tag in ("Title", "SectMetaData"):
                    continue
                node.remove(child)
        node = root.find("SummaryMetaData/SummaryLanguage")
        if node is not None:
            node.text = "Spanish"
        node = root.find("SummaryMetaData/SummaryURL")
        if node is not None:
            node.set(f"{{{Doc.NS}}}xref", self.URL)
        etree.strip_elements(root, with_tail=False, *self.STRIP)
        etree.strip_tags(root, "StandardWording")
        etree.strip_attributes(root, "PdqKey")
        node = etree.SubElement(root, "TranslationOf")
        node.text = title
        node.set(f"{{{Doc.NS}}}ref", cdr_id)
        if hp is not None:
            node = etree.SubElement(root, "PatientVersionOf")
            node.text = hp.name
            node.set(f"{{{Doc.NS}}}ref", f"CDR{int(hp.id):010d}")
        opts = dict(pretty_print=True, encoding="unicode")
        return etree.tostring(root, **opts)

    def __get_hp_doc(self, cdr_id):
        """Find the Spanish HP document for this patient summary.

        Required positional argument:
          cdr_id - normalized CDR ID for the English HP summary

        Return:
          object containing the normalized ID and title of the
          Spanish HP equivalent of this patient summary
        """

        sql = (
            "SELECT d.id, d.title FROM document d "
            "JOIN query_term t ON t.doc_id = d.id "
            "WHERE t.path = '/Summary/TranslationOf/@cdr:ref' "
            f"AND t.value = '{cdr_id}'"
        )
        tier = Tier(self.tier)
        host = tier.hosts["APPC"]
        base = f"https://{host}/cgi-bin/cdr/CdrQueries.py"
        parms = f"sql={sql}&Request=JSON"
        url = f"{base}?{parms}"
        response = get(url)
        rows = response.json()["rows"]
        return IdAndName(rows[0][0], rows[0][1]) if rows else None


if __name__ == "__main__":
    Control().run()
