#!/usr/bin/env python

"""Simple demonstration of how to use the cdrcgi.Controller class.
"""

from datetime import date, timedelta
from cdrcgi import Controller


class Control(Controller):
    """Report-specific behavior implemented in this derived class."""

    SUBTITLE = "Simple report on Publishing Jobs"

    def build_tables(self):
        """Create the table for the report."""

        fields = "id", "pub_subset", "started", "completed", "status"
        query = self.Query("pub_proc", *fields)
        query.where(query.Condition("started", self.start, ">="))
        end = f"{self.end} 23:59:59.999"
        query.where(query.Condition("started", end, "<="))
        query.order("1 DESC")
        rows = query.execute().fetchall()
        columns = "Job ID", "Job Type", "Started", "Completed", "Status"
        opts = dict(columns=columns, caption="Jobs")
        return self.Reporter.Table(rows, **opts)

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page - `HTMLPage` object on which the form is drawn
        """

        fieldset = page.fieldset("Specify Date Range For Report")
        fieldset.append(page.date_field("start", value=self.start))
        fieldset.append(page.date_field("end", value=self.end))
        page.form.append(fieldset)

    @property
    def end(self):
        """Ending date for the date range on which we are to report."""

        if not hasattr(self, "_end"):
            end = self.parse_date(self.fields.getvalue("end"))
            self._end = end if end else date.today()
        return self._end

    @property
    def start(self):
        """Start date for the date range on which we are to report."""

        if not hasattr(self, "_start"):
            start = self.parse_date(self.fields.getvalue("start"))
            self._start = start if start else self.end - timedelta(7)
        return self._start


if __name__ == "__main__":
    """Don't execute the script if loaded as a module.

    Instantiate an instance of our class and invoke the inherited run()
    method. This method acts as a switch statement, in effect, and checks
    to see whether any of the action buttons have been clicked. If so,
    and the button is not the "Submit" button, the user is taken to
    whichever page is appropriate to that button (e.g., logging out,
    the reports menu, or the top-level administrative menu page).
    If the clicked button is the "Submit" button, the show_report()
    method is invoked. The show_report() method in turn invokes the
    build_tables() method, which we have overridden above. Finally,
    show_report() invokes this.report.send() to display the report.

    If no button is clicked, the run() method invokes the show_form()
    method, which in turn calls the populate_form() method so we can
    add the fields we need for this report (as well as make any other
    tweaks to the form's page) before displaying the form.
    """

    Control().run()
