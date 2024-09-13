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

        fields = "id", "pub_subset", "started", "completed", "status"
        query = self.Query("pub_proc", *fields)
        query.where(query.Condition("started", self.start, ">="))
        end = f"{self.end} 23:59:59.999"
        query.where(query.Condition("started", end, "<="))
        query.order("1 DESC")
        rows = query.execute().fetchall()

        # For-loop to create a new list containing a cell object as the
        # first element and adding the SQL output for the remaining list
        # elements
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

    def show_report(self):
        """Special formatting of report output

           Overriding this method allows us to add CSS rules to the
           report output, like styling the column header row or choosing
           a background color for the report, for instance.  By using this
           method we can use the page method add_css(<CSS rule>)

           Removing this method will ensure usage of the standard report
           formatting rules.
        """

        elapsed = self.report.page.html.get_element_by_id("elapsed", None)
        if elapsed is not None:
            elapsed.text = str(self.elapsed)
        self.report.page.add_css("th { background-color: yellow; }")
        self.report.send(self.format)

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page - `HTMLPage` object on which the form is drawn
        """

        fieldset = page.fieldset("Specify Date Range For Report")
        fieldset.append(page.date_field("start", value=self.start))
        fieldset.append(page.date_field("end", value=self.end))
        page.form.append(fieldset)

    @cached_property
    def end(self):
        """Ending date for the date range on which we are to report."""

        end = self.parse_date(self.fields.getvalue("end"))
        return end if end else date.today()

    @cached_property
    def start(self):
        """Start date for the date range on which we are to report."""

        start = self.parse_date(self.fields.getvalue("start"))
        return start if start else self.end - timedelta(7)


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
