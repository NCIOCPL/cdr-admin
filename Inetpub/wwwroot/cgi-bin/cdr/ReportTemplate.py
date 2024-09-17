#!/usr/bin/env python

"""Simple demonstration of how to use the cdrcgi.Controller class.
"""

from datetime import date, timedelta
from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Report-specific behavior implemented in this derived class."""

    SUBTITLE = "Simple report on Publishing Jobs"

    def build_tables(self):
        """Create the table for the report.

           In the simple case we receive a list of lists containing
           the values from a SQL query and pass it to the Reporter.Table()
           class.  Each value will be placed in a single cell.

           In cases where a cell needs to be formatted or - like in this
           case - we're adding a link to a cell, we will create a Cell
           object.  The list passed to the table class may contain
           regular values from the SQL query or Cell objects!
        """

        # If we don't have everything we need, show the form/alerts.
        if not self.ready:
            return self.show_form()

        # Fetch the values for the report from the database.
        # Bothering with specifying the fractions of a second at the
        # end of the day doesn't address leap seconds, but this is
        # close enough. ;-)
        fields = "id", "pub_subset", "started", "completed", "status"
        query = self.Query("pub_proc", *fields)
        query.where(query.Condition("started", self.start, ">="))
        end = f"{self.end} 23:59:59.999"
        query.where(query.Condition("started", end, "<="))
        query.order("1 DESC")
        rows = query.execute().fetchall()

        # For-loop to create a new list containing a cell object as the
        # first element and adding the SQL output for the remaining list
        # elements.
        # If no special formatting (for example, creating the link to the
        # PubStatus.py report) is needed you may pass the rows list to
        # the Reporter.Table class instead of the table_rows list.
        # --------------------------------------------------------------
        table_rows = []
        for row in rows:
            cells = [
                self.Reporter.Cell(row[0], href=f"PubStatus.py?id={row[0]}")
            ]
            cells += row[1:]
            table_rows.append(cells)

        columns = "Job ID", "Job Type", "Started", "Completed", "Status"
        opts = {"columns": columns, "caption": "Jobs"}
        return self.Reporter.Table(table_rows, **opts)

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page - `HTMLPage` object on which the form is drawn
        """

        # If the URL contained all the information we need, nothing to do here.
        if self.ready:
            return self.show_report()

        # Come up with default dates if appropriate.
        end = self.end or date.today()
        start = self.start or end - timedelta(7)

        fieldset = page.fieldset("Specify Date Range For Report")
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)

    @cached_property
    def end(self):
        """Ending date for the date range on which we are to report."""
        return self.fields.getvalue("end")

    @cached_property
    def ready(self):
        """True if we have everything needed for the report.

        For this example, we'll allow a request to include the
        required start and end dates in the URL's parameters.
        So we can be ready even if the user hasn't clicked the
        Submit button.

        The price we pay for this flexibility is that we have to
        check the dates for validity. The form will prevent the
        user from submitting an invalid date, but the web server
        can't do the same thing for parameters in the URL.

        Note how we update the start and end properties. We can
        do that because Python's cached properties are writable.
        """

        # If we have a start date, make sure it's value.
        if self.start:
            try:
                self.start = self.parse_date(self.start)
                if self.start > date.today():
                    message = "Start date cannot be in the future."
                    self.alerts.append(dict(message=message, type="error"))
            except Exception:
                self.logger.exception(self.start)
                message = f"Invalid start date {self.start!r}."
                self.alerts.append(dict(message=message, type="error"))
                self.start = None

        # Do the same for the end date.
        if self.end:
            try:
                self.end = self.parse_date(self.end)
            except Exception:
                self.logger.exception(self.end)
                message = f"Invalid end date {self.end!r}."
                self.alerts.append(dict(message=message, type="error"))
                self.end = None

        if self.start and self.end:
            if self.end < self.start:
                message = "Start date cannot be after end date."
                self.alerts.append(dict(message=message, type="error"))
            else:
                return True if not self.alerts else False
        elif self.request:
            message = "Both start date and end date are required."
            self.alerts.append(dict(message=message, type="error"))
        return False

    @cached_property
    def start(self):
        """Start date for the date range on which we are to report."""
        return self.fields.getvalue("start")


def main():
    """Create an instance of our class and invoke the inherited run() method.

    That method acts as a switch statement, in effect, and checks to see
    whether any of the action buttons have been clicked. If so, and the
    button is not the "Submit" button, the user is taken to whichever page
    is appropriate to that button (e.g., logging out, the reports menu, or
    the top-level administrative menu page). If the clicked button is the
    "Submit" button, the show_report() method is invoked. The show_report()
    method in turn invokes the build_tables() method, which we have overridden
    above. Finally, show_report() invokes this.report.send() to display the
    report.

    If no button is clicked, the run() method invokes the show_form() method,
    which in turn calls the populate_form() method so we can add the fields we
    need for this report (as well as make any other tweaks to the form's page)
    before displaying the form.
    """
    Control().run()

if __name__ == "__main__":
    main()