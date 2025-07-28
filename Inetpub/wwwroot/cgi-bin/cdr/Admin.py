#!/usr/bin/env python

"""Landing page for the CDR Administrative system.
"""

import datetime
import functools
import cdrcgi


class Page(cdrcgi.HTMLPage):

    @functools.cached_property
    def logged_in_count(self):
        """How many users are currently logged in on this CDR tier?"""

        query = self.control.Query("session", "COUNT(DISTINCT usr)")
        query.where("ended IS NULL")
        query.where("name <> 'guest'")
        return query.execute(self.control.cursor).fetchone()[0]

    @functools.cached_property
    def saved_today(self):
        """Count of unique documents saved today."""

        today = str(datetime.date.today())
        query = self.control.Query("audit_trail", "COUNT(DISTINCT document)")
        query.where(f"dt >= '{today}'")
        return f"{query.execute(self.control.cursor).fetchone()[0]:,}"

    @functools.cached_property
    def saved_this_week(self):
        """Count of unique documents saved in the past week."""

        last_week = str(datetime.date.today() - datetime.timedelta(7))
        query = self.control.Query("audit_trail", "COUNT(DISTINCT document)")
        query.where(f"dt >= '{last_week}'")
        return f"{query.execute(self.control.cursor).fetchone()[0]:,}"

    @functools.cached_property
    def locked_count(self):
        """How many documents are currently checked out?"""

        query = self.control.Query("checkout", "COUNT(DISTINCT id)")
        query.where("dt_in IS NULL")
        return f"{query.execute(self.control.cursor).fetchone()[0]:,}"

    @functools.cached_property
    def active_count(self):
        """How many non-blocked documents are in the system?"""

        query = self.control.Query("active_doc", "COUNT(*)")
        return f"{query.execute(self.control.cursor).fetchone()[0]:,}"

    @functools.cached_property
    def last_pub_date(self):
        """When was the last successful weekly publishing job run?"""

        query = self.control.Query("pub_proc", "MAX(started)")
        query.where("pub_subset = 'Push_Documents_To_Cancer.Gov_Export'")
        query.where("status = 'Success'")
        date = query.execute(self.control.cursor).fetchone()[0]
        return date.strftime("%Y-%m-%d")

    @functools.cached_property
    def summary_count(self):
        """How many Summary documents are published?"""
        return self.doctype_count("Summary")

    @functools.cached_property
    def drug_summary_count(self):
        """How many Summary documents are published?"""
        return self.doctype_count("DrugInformationSummary")

    @functools.cached_property
    def glossary_term_count(self):
        """How many Summary documents are published?"""
        return self.doctype_count("GlossaryTermName")

    @functools.cached_property
    def media_count(self):
        """How many Summary documents are published?"""
        return self.doctype_count("Media")

    def doctype_count(self, name):
        """How many documents of a given document type are published?
        """

        query = self.control.Query("document d", "COUNT(*)")
        query.join("pub_proc_cg c", "c.id = d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", name))
        return f"{query.execute(self.control.cursor).fetchone()[0]:,}"

    @functools.cached_property
    def main(self):
        """Dispense with the sidebar menu."""

        card_classes = "usa-card desktop:grid-col-6 usa-card-header-first"
        checked_out_label = "Documents checked out for editing"
        drug_summary_count = self.drug_summary_count
        activity_counts = (
            self.B.LI(f"Logged-in users: {self.logged_in_count}"),
            self.B.LI(f"Documents saved today: {self.saved_today}"),
            self.B.LI(f"Documents saved this week: {self.saved_this_week}"),
            self.B.LI(f"{checked_out_label}: {self.locked_count}"),
            self.B.LI(f"Active CDR documents: {self.active_count}"),
        )
        publishing_counts = (
            self.B.LI(f"Last full publishing job: {self.last_pub_date}"),
            self.B.LI(f"Cancer Information Summaries: {self.summary_count}"),
            self.B.LI(f"Drug Information Summaries: {drug_summary_count}"),
            self.B.LI(f"Glossary Terms: {self.glossary_term_count}"),
            self.B.LI(f"Media: {self.media_count}"),
        )
        return self.B.E(
            "main",
            self.B.DIV(
                self.B.UL(
                    self.B.LI(
                        self.B.DIV(
                            self.B.DIV(
                                self.B.H2(
                                    "Current Activity",
                                    self.B.CLASS("usa-card__heading")
                                ),
                                self.B.CLASS("usa-card__header")
                            ),
                            self.B.DIV(
                                self.B.DIV(
                                    self.B.IMG(
                                        src="/images/office-cropped.jpg",
                                        alt="office"
                                    ),
                                    self.B.CLASS("usa-card__img")
                                ),
                                self.B.CLASS("usa-card__media")
                            ),
                            self.B.DIV(
                                self.B.UL(*activity_counts),
                                self.B.CLASS("usa-card__body")
                            ),
                            self.B.CLASS("usa-card__container")
                        ),
                        self.B.CLASS(card_classes)
                    ),
                    self.B.LI(
                        self.B.DIV(
                            self.B.DIV(
                                self.B.H2(
                                    "Publishing",
                                    self.B.CLASS("usa-card__heading")
                                ),
                                self.B.CLASS("usa-card__header")
                            ),
                            self.B.DIV(
                                self.B.DIV(
                                    self.B.IMG(
                                        src="/images/printing-cropped.jpg",
                                        alt="printing"
                                    ),
                                    self.B.CLASS("usa-card__img")
                                ),
                                self.B.CLASS("usa-card__media")
                            ),
                            self.B.DIV(
                                self.B.UL(*publishing_counts),
                                self.B.CLASS("usa-card__body")
                            ),
                            self.B.CLASS("usa-card__container")
                        ),
                        self.B.CLASS(card_classes)
                    ),
                    self.B.CLASS("usa-card-group")
                ),
                self.B.CLASS("grid-container")
            ),
            self.B.CLASS("usa-section")
        )


class Control(cdrcgi.Controller):
    """Logic for dynamic construction of the top-level CDR admin menu."""

    SUBTITLE = "Main Menu"
    BOARD_MANAGERS = "Board Manager Menu Users"
    CIAT_OCCM = "CIAT/OCCM Staff Menu Users"
    DEV_SA = "Developer/SysAdmin Menu Users"
    MENUS = (
        (BOARD_MANAGERS, "BoardManagers.py", "OCC Board Managers"),
        (CIAT_OCCM, "CiatCipsStaff.py", "CIAT/OCC Staff"),
        (DEV_SA, "DevSA.py", "Developers/System Administrators"),
    )

    def populate_form(self, page):
        """Add the menu links available for this user.

        If the user only has one menu option, go there directly.
        """

        if len(page.user_menus) < 2:
            labels = [menu["label"] for menu in page.menus]
            menu = page.user_menus[0]
            label = menu["label"]
            positions = [labels.index(label)] if label in labels else []
            script = page.find_menu_link(menu, positions)
            opts = dict(show_news=True)
            if self.logged_out:
                opts["logged_out"] = True
            self.navigate_to(script, self.session, **opts)

    @functools.cached_property
    def form_page(self):
        """Custom layout for the landing page."""
        return Page(self.title, control=self, session=self.session, buttons=[])

    @property
    def buttons(self):
        """This page needs no buttons."""
        return []

    @functools.cached_property
    def show_news(self):
        """Show news items when the user hits the home page."""
        return True

    @property
    def user(self):
        """Access to which groups the current user belongs to."""

        if not hasattr(self, "_user"):
            opts = dict(name=self.session.user_name)
            self._user = self.session.User(self.session, **opts)
        return self._user


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
