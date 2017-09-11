#----------------------------------------------------------------------
#
# Report listing the PCIB Statistics of updated/added documents for 
# the specified time frame.  
# This report runs on a monthly schedule but can also be submitted from
# the CDR Admin reports menu.
#
# OCECDR-3867: PCIB Statistics Report
# OCECDR-4096: Incorporate into new scheduler
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import datetime
import cdr_stats

class Control(cdrcgi.Control):

    LEGEND = "Run PCIB Statistics Report for a specific time frame"
    SECTION_LABELS = {
        "summary": "Summaries",
        "genetics": "Genetics Professionals",
        "drug": "NCI Drug Terms",
        "dis": "Drug Information Summaries",
        "boardmembers": "PDQ Board Members",
        "boardmeetings": "PDQ Board Meetings",
        "image": "Images",
        "glossary": "Glossary (including audio pronunciations)"
    }

    def __init__(self):
        """
        Gather and validate the parameters (using defaults as appropriate).
        Defer requiring value for email field until later, to handle the
        case where the logged-in user has no email address registered,
        and will instead enter an address manually.
        """

        cdrcgi.Control.__init__(self, "PCIB Statistics Report")
        today = datetime.date.today()
        start = datetime.date(today.year, 1, 1)
        recips = self.fields.getvalue("recips", "")
        self.recips = recips.replace(",", " ").replace(";", " ").split()
        self.email = cdr.getEmail(self.session)
        self.start = self.fields.getvalue("start", str(start))
        self.end = self.fields.getvalue("end", str(today))
        self.sections = self.fields.getlist("sections")
        self.list_docs = self.fields.getvalue("list-docs")
        self.max_docs = self.fields.getvalue("max-docs")
        self.show_ids = self.fields.getvalue("show-ids")
        msg = cdrcgi.TAMPERING
        cdrcgi.valParmDate(self.start, msg=msg)
        cdrcgi.valParmDate(self.end, msg=msg)
        for recip in self.recips:
            cdrcgi.valParmEmail(recip, msg=msg, empty_ok=True)
        cdrcgi.valParmVal(self.max_docs, regex=cdrcgi.VP_UNSIGNED_INT,
                          empty_ok=True, msg=msg)
        if set(self.sections) - set(cdr_stats.Control.SECTIONS):
            cdrcgi.bail("oops!: %s" % self.sections)

    def populate_form(self, form):
        "Fill in the fields for requesting the report."
        form.add("<fieldset>")
        form.add(form.B.LEGEND(self.LEGEND))
        instructions = (u"This Report runs on every 1\u02E2\u1d57 of the "
                        u"month for the previous month. "
                        u"Specify the start date and end date to run the "
                        u"report for a different time frame.",
                        u"Click the submit button only once!  The report "
                        u"will take a few seconds to complete.")
        for para in instructions:
            form.add(form.B.P(para))
        form.add_date_field("start", "Start Date", value=self.start)
        form.add_date_field("end", "End Date", value=self.end)
        form.add_text_field("recips", "Email", value=self.email)
        form.add_text_field("max-docs", "Max Docs")
        footer = ("Leave the Email field empty to send the report to the "
                  "default distribution list.")
        form.add(form.B.P(footer))
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Sections"))
        for section in cdr_stats.Control.SECTIONS:
            if section != "audio":
                label = self.SECTION_LABELS.get(section, section.capitalize())
                form.add_checkbox("sections", label, section, checked=True)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Flags"))
        form.add_checkbox("list-docs", "Include individual documents", "Yes",
                          checked=True)
        form.add_checkbox("show-ids", "Include column for CDR IDs", "Yes",
                          checked=True)

    def show_report(self):
        """
        Hand off the work of creating the report to another script.
        Tell the user when we're done.
        """

        sections = [s.lower() for s in self.sections]
        opts = {
            "mode": "live",
            "recips": self.recips,
            "start": self.start,
            "end": self.end,
            "sections": sections,
            "ids": self.show_ids == "Yes",
            "docs": self.list_docs == "Yes",
            "max-docs": self.max_docs
        }
        try:
            cdr_stats.Control(opts).run()
        except Exception, e:
            cdrcgi.bail("failure: %s" % e)
        page = cdrcgi.Page("CDR Administration",
                           subtitle="PCIB Statistics Report submitted",
                           buttons=("Reports Menu", cdrcgi.MAINMENU, "Log Out"),
                           action=self.script, session=self.session)
        page.add("<fieldset>")
        page.add(page.B.LEGEND(self.LEGEND))
        page.add(page.B.P("The report has been sent to you by email.",
                          style="text-align: center; padding-right: 20px;"))
        page.add("</fieldset>")
        page.send()

# Top-level entry point for script.
if __name__ == "__main__":
    Control().run()
