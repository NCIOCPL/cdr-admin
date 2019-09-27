#----------------------------------------------------------------------
#
# Tool for checking the health of the glossifier service.  The most common
# cause of failure is someone at cancer.gov trying to connect using a
# temporary URL (on Verdi) I set up for Bryan for a one-time test.
# The correct URL for the production service is:
#
#     http://glossifier.cancer.gov/cgi-bin/glossify
#
#----------------------------------------------------------------------
import datetime
from zeep import Client
import cdrcgi
from cdrapi.settings import Tier

class Control(cdrcgi.Control):
    TIER = Tier()
    HOST = TIER.hosts["GLOSSIFIERC"]
    URL = f"http://{HOST}/cgi-bin/glossify"
    FRAGMENT = "<p>Gerota\u2019s capsule breast cancer and mama</p>"
    DEBUG_LEVEL = "X_DEBUG_LEVEL"
    PAGE_TITLE = "PDQ Glossifier Test"

    def __init__(self):
        cdrcgi.Control.__init__(self, self.PAGE_TITLE)
        self.level = self.fields.getvalue("level") or ""
        self.frag = self.fields.getvalue("frag") or self.FRAGMENT
        self.lang = self.fields.getvalue("lang")
        self.standalone = self.fields.getvalue("standalone") and True or False
    def glossify(self):
        client = Client(self.URL)
        factory = client.type_factory('ns0')
        dictionaries = factory.ArrayOfString(["Cancer.gov"])
        languages = factory.ArrayOfString([self.lang] if self.lang else [])
        headers = self.level and { self.DEBUG_LEVEL: self.level } or {}
        with client.settings(extra_http_headers=headers):
            return client.service.glossify(self.frag, dictionaries, languages)
    def populate_form(self, form):
        try:
            result = self.glossify()
        except Exception as e:
            self.logger.exception("aargh!")
            print(dir(e))
            print(e.detail)
            print(e)
            exit(0)
        elapsed = (datetime.datetime.now() - self.started).total_seconds()
        if self.standalone:
            print(result)
            print(("elapsed: %f" % elapsed))
            exit(0)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Test Options"))
        languages = (("", "Any"), ("en", "English"), ("es", "Spanish"))
        form.add_select("lang", "Language(s)", languages, self.lang)
        form.add_textarea_field("frag", "Fragment", value=self.frag)
        form.add_text_field("level", "Debug Level", value=self.level)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Result (elapsed %f seconds)" % elapsed))
        form.add(form.B.PRE(str(result)))
        form.add("</fieldset>")
    def show_report(self):
        self.show_form()

if __name__ == "__main__":
    Control().run()
