#!/usr/bin/env

"""Simple demonstration of how to use the cdrcgi.Controller class.
"""

import datetime
import cdrcgi
from cdrapi import db

class Control(cdrcgi.Controller):
    """Report-specific behavior implemented in this derived class.
    """

    def __init__(self):
        """Let the base class get things started."""
        cdrcgi.Controller.__init__(self, "Simple Report on Publishing Jobs")

    @property
    def end(self):
        """Ending date for the date range on which we are to report."""
        if not hasattr(self, "_end"):
            self._end = self.fields.getvalue("end_date")
            if self._end:
                cdrcgi.valParmDate(self._end, msg=cdrcgi.TAMPERING)
        return self._end

    @property
    def start(self):
        """Start date for the date range on which we are to report."""
        if not hasattr(self, "_start"):
            self._start = self.fields.getvalue("start_date")
            if self._start:
                cdrcgi.valParmDate(self._start, msg=cdrcgi.TAMPERING)
        return self._start

    def populate_form(self, page):
        """Put the fields on the form."""
        start, end = self.start, self.end
        if not start and not end:
            end = datetime.date.today()
            start = end - datetime.timedelta(7)
        fieldset = page.fieldset("Specify Date Range For Report")
        fieldset.append(page.date_field("start_date", value=start))
        fieldset.append(page.date_field("end_date", value=end))
        page.form.append(fieldset)

    def build_tables(self):
        """Create the table for the report."""
        fields = ("id", "pub_subset", "started", "completed", "status")
        query = db.Query("pub_proc", *fields)
        if self.start:
            query.where(query.Condition("started", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59.999"
            query.where(query.Condition("started", end, "<="))
        query.order("1 DESC")
        rows = query.execute().fetchall()
        columns = (
            cdrcgi.Reporter.Column("Job ID"),
            cdrcgi.Reporter.Column("Job Type"),
            cdrcgi.Reporter.Column("Started"),
            cdrcgi.Reporter.Column("Completed"),
            cdrcgi.Reporter.Column("Status")
        )
        return cdrcgi.Reporter.Table(columns, rows)


#----------------------------------------------------------------------
# Instantiate an instance of our class and invoke the inherited run()
# method. This method acts as a switch statement, in effect, and checks
# to see whether any of the action buttons have been clicked. If so,
# and the button is not the "Submit" button, the user is taken to
# whichever page is appropriate to that button (e.g., logging out,
# the reports menu, or the top-level administrative menu page).
# If the clicked button is the "Submit" button, the show_report()
# method is invoked. The show_report() method in turn invokes the
# build_tables() method, which we have overridden above. It also
# invokes set_report_options() which we could override if we wanted
# to modify how the report's page is displayed (for example, to
# change which buttons are displayed); we're not overriding that
# method in this simple example. Finally show_report() invokes
# report.send() to display the report.
#
# If no button is clicked, the run() method invokes the show_form()
# method, which in turn calls the set_form_options() method (which
# we're not overriding here) as well as the populate_form() method
# (see above) before calling form.send() to display the form.
#----------------------------------------------------------------------
if __name__ == "__main__":
    Control().run()
