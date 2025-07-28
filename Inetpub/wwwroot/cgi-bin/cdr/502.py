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
        url = self.session.tier.get_control_value(self.session, *args)
        if not url:
            return "JIRA"
        return self.HTMLPage.B.A("JIRA", href=url, target="_blank")

    @cached_property
    def missing(self):
        """Should this really be a 404 page?"""

        if not self.path:
            return False
        if not self.path.exists():
            self.logger.warning("unable to find %s", self.path)
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
            self.alert = "Failure parsing URL for original request."
            return None

    @cached_property
    def path(self):
        """Path object for the location of the CGI script."""
        return self.www_root / self.original_script.strip("/")

    @cached_property
    def script_text(self):
        """The contents of the script file."""

        if self.missing:
            return None
        try:
            return self.path.read_text(encoding="utf-8")
        except Exception:
            self.logger.exception("reading %s", self.path)
            self.alert = (
                "The web server does not have permission "
                f"to read the script {self.original_script}."
            )
            return None

    @cached_property
    def script_valid(self):
        """True if the script can be successfully compiled.

        Doesn't detect problems with the included libraries.
        """

        if self.script_text is None:
            return False
        if not self.script_text.strip():
            self.alert = f"Script {self.original_script} is empty."
            return False
        try:
            compile(self.script_text + "\n", "<string>", "exec")
            return True
        except Exception:
            self.logger.exception("compiling %s", self.original_script)
            self.alert = f"Script {self.original_script} has syntax errors."
            return False

    @cached_property
    def service_now(self):
        """Link for creating a Service Now ticket (if we have the URL)."""

        label = "NCI at Your Service"
        args = "trackers", "create-sn-ticket"
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
                try:
                    session = Session(query_string[self.SESSION][0])
                    self.logger.info("Session=%s", session)
                    return session
                except Exception:
                    self.logger.exception(query_string[self.SESSION])
        return Session("guest")

    @cached_property
    def subtitle(self):
        """What we want shown at the top of the page."""

        if self.missing:
            return "Script Not Found"
        if self.script_text is None:
            return "Permissions Error"
        if not self.script_valid:
            return "Program Error"
        return "Server Error"

    @cached_property
    def www_root(self):
        """Base directory for the web site's documents."""
        return Path(__file__).parent.parent.parent


if __name__ == "__main__":
    control = Control()
    try:
        control.run()
    except Exception as e:
        control.bail(e)
