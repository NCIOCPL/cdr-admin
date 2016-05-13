#----------------------------------------------------------------------
#
# $Id: BoardMeetingDates.py 9572 2010-04-02 17:25:19Z volker $
#
# Report listing the PCIB Statistics of updated/added documents for 
# the specified time frame.  
# This report runs on a monthly schedule but can also be submitted from
# the CDR Admin reports menu.
#
# OCECDR-3867: PCIB Statistics Report
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import datetime
import os

class Control(cdrcgi.Control):

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
        email = cdr.getEmail(self.session)
        self.start = self.fields.getvalue("start", str(start))
        self.end = self.fields.getvalue("end", str(today))
        self.emailTo = self.fields.getvalue("email", email)
        msg = cdrcgi.TAMPERING
        cdrcgi.valParmDate(self.start, msg=msg)
        cdrcgi.valParmDate(self.end, msg=msg)
        cdrcgi.valParmEmail(self.emailTo, msg=msg, empty_ok=True)

    def populate_form(self, form):
        "Fill in the fields for requesting the report."
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Run PCIB Statistics Report for a specific time frame"))
        ### Need to find out how to write 1st properly using the control
        ### class (using <sup>...</sup>
        instructions = ("This Report runs on every 1st of the month "
                        "for the previous month. "
                        "Specify the start date and end date to run the "
                        "report for a different time frame.",
                        "Click the submit button only once!  The report "
                        "will take a few seconds to complete.")
        for para in instructions:
            form.add(form.B.P(para))
        form.add_date_field("start", "Start Date", value=self.start)
        form.add_date_field("end", "End Date", value=self.end)
        form.add_text_field("email", "Email", value=self.emailTo)
        footer = ("Leave the Email field empty to send the report to the "
                  "default distribution list.")
        form.add(form.B.P(footer))
        form.add("</fieldset>")

    def show_report(self):
        """
        Hand off the work of creating the report to another script.
        Tell the user when we're done.
        """
        if not self.emailTo:
            cdrcgi.bail("Email address is required.")
        script = os.path.join(cdr.BASEDIR, "publishing", "PCIBStatsReport.py")
        # The report was written with the --email option to turn sending 
        # it by email on/off.
        opts = ("--livemode", "--include",
                "--email", "--sendto=%s" % self.emailTo, 
                "--startdate=%s" % self.start, "--enddate=%s" % self.end)
        cmd = "%s %s" % (script, " ".join(opts))
        result = cdr.runCommand(cmd, joinErr2Out=False)
        if result.error:
            logger = cdr.Log("PCIBStats.log")
            message = "Error submitting report\n%s" % result.error
            logger.write(message, stdout=True)
            cdrcgi.bail(message)
        page = cdrcgi.Page("CDR Administration",
                           subtitle="PCIB Statistics Report submitted",
                           buttons=("Reports Menu", cdrcgi.MAINMENU, "Log Out"),
                           action=self.script, session=self.session)
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Run PCIB Statistics Report for specific time frame"))
        page.add(page.B.P("The report has been sent to you by email."))
        page.add("</fieldset>")
        page.send()

# Top-level entry point for script.
if __name__ == "__main__":
    Control().run()
