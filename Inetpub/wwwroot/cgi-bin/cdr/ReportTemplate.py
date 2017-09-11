#----------------------------------------------------------------------
# Simple demonstration of how to use the cdrcgi.Control class.
#----------------------------------------------------------------------
import cdrcgi
import cdrdb
import datetime

class Control(cdrcgi.Control):
    """
    Report-specific behavior implemented in this derived class.
    """

    def __init__(self):
        """
        Let the base class get things started, then determine the default
        and actual values for the parameters, and validate them.
        Setting the msg argument to the validation routines causes
        processing to stop when validation fails, displaying the error
        message. In cases (like this one) in which the parameter values
        can only fail vaildation when a hacker has tampered with the
        request, it's often best to reveal as little as possible about
        why the value was rejected.
        """
        cdrcgi.Control.__init__(self, "Simple Report on Publishing Jobs")
        today = datetime.date.today()
        start = today - datetime.timedelta(7)
        self.start = self.fields.getvalue("start", str(start))
        self.end = self.fields.getvalue("end", str(today))
        cdrcgi.valParmDate(self.start, msg=cdrcgi.TAMPERING)
        cdrcgi.valParmDate(self.end, msg=cdrcgi.TAMPERING)

    def populate_form(self, form):
        """
        Put the fields we need on the form. See documentation of the
        cdrcgi.Page class for examples and other details. Read the
        comment at the bottom of this script to see when and how this
        callback method is invoked.
        """
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Specify Date Range For Report"))
        form.add_date_field("start", "Start Date", value=self.start)
        form.add_date_field("end", "End Date", value=self.end)
        form.add("</fieldset>")

    def build_tables(self):
        """
        Callback to give the base class an array of Table objects
        (only one in our case). See documentation of that class in
        the cdrcgi module. Read the comment at the bottom of this
        script to learn now and when this method is called.
        """
        fields = ("id", "pub_subset", "started", "completed", "status")
        query = cdrdb.Query("pub_proc", *fields)
        query.where(query.Condition("started", self.start, ">="))
        query.where(query.Condition("started", self.end + " 23:59:59", "<="))
        query.order("1 DESC")
        rows = query.execute().fetchall()
        columns = (
            cdrcgi.Report.Column("Job ID"),
            cdrcgi.Report.Column("Job Type"),
            cdrcgi.Report.Column("Started"),
            cdrcgi.Report.Column("Completed"),
            cdrcgi.Report.Column("Status")
        )
        return [cdrcgi.Report.Table(columns, rows)]

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
