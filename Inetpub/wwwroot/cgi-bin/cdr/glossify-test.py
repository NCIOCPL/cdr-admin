#!/usr/bin/env python

"""Check the health of the glossifier service.
"""

from argparse import ArgumentParser
from cdrcgi import Controller
from zeep import Client


class Control(Controller):
    """Access to the CDR runtime environment and HTML page generation."""

    SUBTITLE = "PDQ Glossifier Test"
    LOGNAME = "glossify-test"
    LANGUAGES = ("en", "English"), ("es", "Spanish")
    DICTIONARIES = "any", "Cancer.gov"
    FRAGMENT = "<p>Gerota\u2019s capsule breast cancer and mama</p>"
    DEBUG_LEVEL = "X_DEBUG_LEVEL"

    def populate_form(self, page):
        """Show the form and the glossification output on the same page.

        Pass:
            page - HTMLPage object where the form and results are shown
        """

        # Let the user override the defaults.
        fieldset = page.fieldset("Language(s)")
        for value, label in self.LANGUAGES:
            checked = value in self.language
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("language", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Dictionary")
        for dictionary in self.DICTIONARIES:
            checked = dictionary == self.dictionary
            opts = dict(value=dictionary, checked=checked)
            fieldset.append(page.radio_button("dictionary", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Additional Options")
        fieldset.append(page.text_field("host", value=self.host))
        opts = dict(value=self.level, label="Log Level")
        fieldset.append(page.text_field("level", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Test HTML Fragment")
        textarea = page.textarea("fragment", value=self.fragment, rows=5)
        fieldset.append(textarea)
        page.form.append(fieldset)

        # Show the results of the glossification at the bottom of the form.
        fieldset = page.fieldset("Result")
        fieldset.append(page.B.PRE(str(self.result)))
        page.form.append(fieldset)
        page.form.append(self.footer)

    def show_report(self):
        """Cycle back to the form."""
        self.show_form()

    @property
    def dictionary(self):
        """Dictionary selected by the user."""
        return self.fields.getvalue("dictionary") or "any"

    @property
    def fragment(self):
        """String for the HTML fragment to be glossified."""
        return self.fields.getvalue("fragment") or self.FRAGMENT

    @property
    def host(self):
        """Glossification server DNS name."""

        if not hasattr(self, "_host"):
            self._host = self.fields.getvalue("host")
            if not self._host:
                self._host = self.session.tier.hosts["GLOSSIFIERC"]
        return self._host

    @property
    def language(self):
        """Language(s) selected by the user."""
        return self.fields.getlist("language")

    @property
    def level(self):
        """Optional debugging level (default is 1)."""
        return self.fields.getvalue("level") or "1"

    @property
    def result(self):
        """Return value from the glossifier."""

        try:
            client = Client(self.url)
            factory = client.type_factory("ns0")
            dictionaries = []
            if self.dictionary and self.dictionary != "any":
                dictionaries = [self.dictionary]
            dictionaries = factory.ArrayOfString(dictionaries)
            languages = factory.ArrayOfString(self.language)
            headers = { self.DEBUG_LEVEL: self.level }
            args = self.fragment, dictionaries, languages
            with client.settings(extra_http_headers=headers):
                result = client.service.glossify(*args)
            if self.standalone:
                print(result)
                print(f"elapsed: {self.elapsed}")
                exit(0)
            return result
        except Exception as e:
            self.logger.exception("Glossification failure")
            return self.HTMLPage.B.P(str(e), self.HTMLPage.B.CLASS("error"))

    @property
    def standalone(self):
        """Are we running from the command line?"""

        if not hasattr(self, "_standalone"):
            parser = ArgumentParser()
            parser.add_argument("--standalone", action="store_true")
            opts = parser.parse_args()
            self._standalone = opts.standalone
        return self._standalone

    @property
    def url(self):
        """Address of the glossification service."""
        return f"http://{self.host}/cgi-bin/glossify"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
