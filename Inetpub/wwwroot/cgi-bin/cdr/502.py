#!/usr/bin/env python
"""Provide custom handling for 502 errors.

Note that IIS mistakenly returns 502 for file-not-found errors
when the file is a script, even though that condition should
result in a 404 error.
"""

from functools import cached_property
from os import environ
from pathlib import Path
from urllib.parse import urlparse
from cdrcgi import Controller


class Control(Controller):

    LOGNAME = "error-502"
    FAILURE = (
        "A problem occurred during the processing of your request. If the "
        "problem persists, please create a JIRA ticket in the OCECDR project."
    )
    MISSING = (
        "The script you requested cannot be located. If the URL contains an "
        "obvious misspelling, please correct it and try the request again. "
        "Otherwise, please report the problem to the CDR development team."
    )
    ERROR_404 = "404 - Not Found"
    ERROR_502 = "502 - Server Error"

    def populate_form(self, page):
        """Tell the user what happened."""

        legend = "Script Not Found" if self.missing else "Server Failure"
        message = self.MISSING if self.missing else self.FAILURE
        fieldset = page.fieldset(legend)
        fieldset.append(page.B.P(message))
        page.body.append(fieldset)

    @cached_property
    def buttons(self):
        """Don't need any buttons on this page."""
        return []

    @cached_property
    def missing(self):
        """Should this really be a 404 page?"""

        query_string = environ.get("QUERY_STRING")
        try:
            url = query_string.split(";", 1)[1]
            script = urlparse(url).path
            root = Path(__file__).parent.parent.parent
            path = root / script.strip("/")
            self.logger.info("path=%s", path)
        except Exception:
            args = query_string, Path(__file__)
            self.logger.exception("QUERY_STRING=%r __file__=%r", *args)
            return False
        return False if path.exists() else True

    @cached_property
    def subtitle(self):
        """What gets displayed under the main banner."""
        return self.ERROR_404 if self.missing else self.ERROR_502


Control().run()
