#!/usr/bin/env python

"""Show Media QC report with Spanish version side-by-side
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
from cdrapi.users import Session
from functools import cached_property
from lxml import html
from lxml.html import builder
import sys


class Control(Controller):
    SUBTITLE = "Media QC Report - EN/ES"
    TRANSLATION_OF = '/Media/TranslationOf/@cdr:ref'
    METHOD = "get"

    def populate_form(self, page):
        """Ask for more information if we don't have everything we need."""

        if self.media:
            self.show_report()
            sys.exit(0)

    def show_report(self):
        """Provide custom routing for the multiple forms."""

        self.media.show_report()

    @cached_property
    def media(self):
        """Subject of the report."""
        return Media(self) if self.idpair else None

    @cached_property
    def idpair(self):
        """CDR Media document ID pair - returning a list [EN, ES]."""

        # Find Spanish document when given the English version.
        value = self.fields.getvalue("DocId")
        if not value:
            self.bail("Missing document ID.")
        doc_id = Doc.extract_id(value)

        query = self.Query("query_term", "doc_id", "int_val")
        query.where(query.Condition("path", self.TRANSLATION_OF))
        query.where(query.Condition("int_val", doc_id))
        rows = query.execute(self.cursor).fetchall()
        if rows:
            return [rows[0][1], rows[0][0]]

        # Find English document when given the Spanish version.
        query = self.Query("query_term", "doc_id", "int_val")
        query.where(query.Condition("path", self.TRANSLATION_OF))
        query.where(query.Condition("doc_id", doc_id))
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            message = "No Spanish translation found for image document"
            self.bail(message)
        return [rows[0][1], rows[0][0]] or None


class Media:
    """Subject of the report."""

    TITLE = "Media QC Report (Title)"
    SUBTITLE = "Media QC Report"
    MEDIA_ELEMENTS = "ContentDescription", "MediaCaption"
    GUEST = Session("guest")
    LANGUAGES = dict(en="English", es="Spanish")
    AUDIENCES = "Patients",
    FILTER = "set:QC Media Set"
    EN_INGLES = " (en ingl\xe9s)"
    CSS = "../../stylesheets/MediaSideBySide.css"

    def __init__(self, control):
        """Save the control object, which has everything we need.

        Pass:
            control - access to the database and the report parameters
        """

        self.control = control

    def show_report(self):
        """Send the report back to the browser."""

        opts = dict(
            pretty_print=True,
            doctype="<!DOCTYPE html>",
            encoding="utf-8",
        )
        sys.stdout.buffer.write(b"Content-type: text/html;charset=utf-8\n\n")
        sys.stdout.buffer.write(html.tostring(self.report, **opts))
        sys.exit(0)

    @cached_property
    def doc(self):
        """CDR `Doc` objects for the Media document."""

        doc_en = Doc(self.control.session, id=self.control.idpair[0])
        doc_es = Doc(self.control.session, id=self.control.idpair[1])
        if doc_en.doctype.name != "Media":
            self.control.bail("Not a Media document")
        return [doc_en, doc_es]

    @cached_property
    def report(self):
        """`HTMLPage` object for the report."""

        B = builder
        meta = B.META(charset="utf-8")
        link = B.LINK(href=self.CSS, rel="stylesheet")
        icon = B.LINK(href="/favicon.ico", rel="icon")
        head = B.HEAD(meta, B.TITLE(self.TITLE), icon, link)
        time = B.SPAN(self.control.started.ctime())
        args = self.SUBTITLE, B.BR(), "Side-by-Side", B.BR(), time
        cdrId = self.control.fields.getvalue("DocId")
        orig_id = B.P(f"{cdrId}", id="media-id")
        wrapper = body = B.BODY(B.E("header", B.H1(*args)), orig_id)
        report = B.HTML(head, body)
        for cdrdoc in self.doc:
            media_id = B.P(f"CDR{self.doc[0].id}", id="media-id")
            wrapper = B.DIV(B.CLASS("lang-wrapper"))
            body.append(wrapper)

            # Display the language if uniquely identified
            lang = self.getLanguage(cdrdoc.id)
            if not lang:
                self.control.bail("Found none or multiple languages")

            # Display the CDR-ID
            media_id = B.P(f"{lang} - CDR{cdrdoc.id}", id="media-id")
            wrapper.append(media_id)

            # Display the image title
            media_title = self.getTitle(cdrdoc.id)
            media_id = B.P(media_title, B.CLASS("media-title"))
            wrapper.append(media_id)

            # Display the image
            if self.isImage(cdrdoc.id):
                image = ("/cgi-bin/cdr/GetCdrImage.py"
                         f"?id=CDR{cdrdoc.id}-400.jpg")
                wrapper.append(B.IMG(src=image))
            else:
                host_id = self.getHostID(cdrdoc.id)
                image = (f"https://img.youtube.com/vi/{host_id}"
                         "/hqdefault.jpg")
                wrapper.append(B.P(B.IMG(src=image)))

            # Display the image labels
            label_hdr = B.P("Label", B.CLASS("section-hdr"))

            labels = self.getLabel(cdrdoc.id)
            if labels:
                ul = B.UL()
                for label in labels:
                    ul.append(B.LI(label))
                wrapper.append(label_hdr)
                wrapper.append(ul)

            desc_hdr = B.P("Content Description", B.CLASS("section-hdr"))
            wrapper.append(desc_hdr)
            base_path = "/Media/MediaContent"
            description_path = "/ContentDescriptions/ContentDescription"
            caption_path = "/Captions/MediaCaption"

            descriptions = self.getInfo(cdrdoc.id,
                                        f"{base_path}{description_path}")

            if descriptions:
                for description in descriptions:
                    wrapper.append(B.P(B.B(f"{description[0]}:"),
                                       B.BR(),
                                       f" {description[1]}"))

            caption_hdr = B.P("Caption", B.CLASS("section-hdr"))
            wrapper.append(caption_hdr)
            captions = self.getInfo(cdrdoc.id,
                                    f"{base_path}{caption_path}")

            if captions:
                for caption in captions:
                    wrapper.append(B.P(B.B(f"{caption[0]}:"),
                                       B.BR(),
                                       f"  {caption[1]}"))

        return report

    # Select the language of the document.  Each document for which
    # this report is used should only include one language code (en/es)
    # For documents including both languages there won't exist a
    # translated Spanish document with the TranslationOf reference
    # to the current "English" version.  Those document will be
    # QC'ed using the original Media QC report.
    # ---------------------------------------------------------------
    def getLanguage(self, id):
        query = self.control.Query("query_term", "DISTINCT value")
        query.where("path like '/Media%@language'")
        query.where(query.Condition("doc_id", id))
        rows = query.execute(self.control.cursor).fetchall()

        if rows and len(rows) == 1:
            return 'English' if rows[0][0] == 'en' else 'Spanish'

        return None

    # Get the Media title
    # ------------------------------------------------------------
    def getTitle(self, id):
        query = self.control.Query("query_term", "value")
        query.where("path = '/Media/MediaTitle'")
        query.where(query.Condition("doc_id", id))
        rows = query.execute(self.control.cursor).fetchall()

        if rows:
            return rows[0][0]

        return None

    # Need to know if this is an image or video document
    # ------------------------------------------------------------
    def isImage(self, id):
        query = self.control.Query("query_term", "value")
        query.where("path = '/Media/PhysicalMedia/ImageData/ImageEncoding'")
        query.where(query.Condition("doc_id", id))
        rows = query.execute(self.control.cursor).fetchall()

        if rows:
            return True

        return False

    # Grab the YouTube hosting ID
    # ------------------------------------------------------------
    def getHostID(self, id):
        query = self.control.Query("query_term", "value")
        query.where("path = '/Media/PhysicalMedia/VideoData/HostingID'")
        query.where(query.Condition("doc_id", id))
        rows = query.execute(self.control.cursor).fetchall()

        if rows:
            return rows[0][0]

        return None

    # Create a list containing all of the labels for this image
    # ------------------------------------------------------------
    def getLabel(self, id):
        query = self.control.Query("query_term", "value")
        query.where("path = '/Media/PhysicalMedia/ImageData/LabelName'")
        query.where(query.Condition("doc_id", id))
        rows = query.execute(self.control.cursor).fetchall()

        if rows:
            return [x[0] for x in rows]

        return None

    # Create a list of the descriptions or captions (based on the path
    # parameter passed.  There could be two elements in the list
    # Patiens or Health_professionals
    # ------------------------------------------------------------------
    def getInfo(self, id, path):
        query = self.control.Query("query_term q", "a.value", "q.value")
        query.join("query_term a", "q.doc_id = a.doc_id")
        query.order("a.value DESC")
        query.where(f"q.path = '{path}'")
        query.where(f"a.path = '{path}/@audience'")
        query.where("LEFT(a.node_loc, 12) = LEFT(q.node_loc, 12)")
        query.where(query.Condition("q.doc_id", id))

        rows = query.execute(self.control.cursor).fetchall()

        if rows:
            return rows

        return None


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
