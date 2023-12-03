#!/usr/bin/env python

from functools import cached_property
from os import environ
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from cdrapi.users import Session
from cdrcgi import Controller

class Control(Controller):
    """Create a 502 (bad gateway) page.

    Note that we need to check to see if this really should have been
    a 404 error instead of a problem with the server, because for some
    reason IIS doesn't handle the failure to find the Python script
    specified in the URL correctly.
    """

    LOGNAME = "error-502"

    def run(self):
        """Take over control of the page."""

        opts = dict(subtitle=self.subtitle, session=self.session)
        page = self.HTMLPage("CDR Administration", **opts)
        page.form.append(
             page.B.P(
                "If the problem persists, please create a ",
                self.jira,
                " ticket in the OCECDR project. If the problem is "
                "obviously a network or other infrastructure failure, "
                "it may be appropriate to also file a ticket with ",
                self.service_now,
                "."
            )
        )
        if self.fields.getvalue("clean"):
            parent = page.header.find("div")
            if parent is not None:
                nav = parent.find("nav")
                if nav is not None:
                    parent.remove(nav)
            page.body.remove(page.footer)
        page.add_alert(self.alert, type="error")
        page.add_alert(
            "By the way, IIS is giving us a 502 error instead of a 404. "
            "We figured out the real problem without any help from IIS. 😎",
            title="502 Error",
            type="warning"
        )
        page.add_uswds_script()
        page.send()

    @cached_property
    def alert(self):
        """Notification of the problem."""

        if not self.missing:
            return "A problem occurred while processing your request."
        script = self.original_script
        return f"🔎 We really looked, but we can't find {script!r}. 👀"

    @cached_property
    def jira(self):
        """Link for creating a new CDR ticket in JIRA (if we have the URL)."""

        args = "trackers", "create-cdr-ticket"
        self.logger.info(dir(self.session.tier))
        url = self.session.tier.get_control_value(self.session, *args)
        if not url:
            return "JIRA"
        return self.HTMLPage.B.A("JIRA", href=url, target="_blank")

    @cached_property
    def missing(self):
        """Should this really be a 404 page?"""

        if not self.original_script:
            return False
        path = self.www_root / self.original_script.strip("/")
        if not path.exists():
            self.logger.warning("unable to find %s", path)
            return True
        return False

    @cached_property
    def original_script(self):
        """The script which was invoked when the problem was encountered."""
        return self.parsed_url.path if self.parsed_url else None

    @cached_property
    def original_url(self):
        """The URL for the original request which failed."""

        query_string = environ.get("QUERY_STRING")
        if not query_string:
            self.logger.warning("QUERY_STRING missing")
            return None
        self.logger.info("QUERY_STRING=%s", query_string)
        if ";" not in query_string:
            message = "unexpected syntax for QUERY_STRING: %s"
            self.logger.warning(message, query_string)
            return None
        return query_string.split(";", 1)[1]

    @cached_property
    def parsed_url(self):
        """The parsed URL for the request which failed."""

        if not self.original_url:
            return None
        try:
            parsed = urlparse(self.original_url)
            self.logger.info("parsed_url=%s", parsed)
            return parsed
        except Exception:
            self.logger.exception("failure parsing %s", self.original_url)
            message = "Failure parsing URL for original request."
            self.alerts.append(dict(message=message, type="error"))
            return None

    @cached_property
    def service_now(self):
        """Link for creating a Service Now ticket (if we have the URL)."""

        label = "NCI at Your Service"
        args = "trackers", "create-sn-ticket"
        self.logger.info(dir(self.session.tier))
        url = self.session.tier.get_control_value(self.session, *args)
        if not url:
            return label
        return self.HTMLPage.B.A(label, href=url, target="_blank")

    @cached_property
    def session(self):
        """Overridden so we can pull the session from the original URL."""

        if self.parsed_url:
            query_string = parse_qs(self.parsed_url.query)
            self.logger.info("query_string=%s", query_string)
            if self.SESSION in query_string:
                session = Session(query_string[self.SESSION][0])
                self.logger.info("Session=%s", session)
                return session
        return Session("guest")


    @cached_property
    def subtitle(self):
        """What we want shown at the top of the page."""
        return "Not Found" if self.missing else "Server Error"

    @cached_property
    def www_root(self):
        """Base directory for the web site's documents."""
        return Path(__file__).parent.parent.parent


if __name__ == "__main__":
    Control().run()
