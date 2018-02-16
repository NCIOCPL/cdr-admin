#----------------------------------------------------------------------
# Prototype for CDR reporting/formatting web wrapper.
# BZIssue::255 - change report title at Margaret's request
#----------------------------------------------------------------------
from lxml import etree
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    "Collect and verify the user options for the report"

    TITLE = "Checked Out Documents With No Activity"

    def __init__(self):
        "Make sure the values make sense and haven't been hacked"

        cdrcgi.Control.__init__(self, self.TITLE)
        self.days = self.fields.getvalue("days")
        if self.days:
            try:
                self.days = int(self.days)
            except:
                cdrcgi.bail("Days value must be an integer")

    def populate_form(self, form):
        "Show form with doctype selection picklist"

        form.add("<fieldset>")
        form.add(form.B.LEGEND("Inactivity Threshold"))
        form.add_text_field("days", "Days", value="10")
        form.add("</fieldset>")

    def show_report(self):
        """
        Use reporting and filtering modules to generate the output
        """
        name = "Inactive Checked Out Documents"
        parms = dict(InactivityLength="0000-00-{:02d}".format(self.days))
        report = cdr.report(self.session, name, parms=parms)
        report = etree.tostring(report, encoding="utf-8")
        filters = ['name:Inactivity Report Filter']
        html = cdr.filterDoc(self.session, filters, doc=report)[0]
        html = html.replace("@@DAYS@@", str(self.days)).decode("utf-8")
        cdrcgi.sendPage(html)

if __name__ == "__main__":
    Control().run()
