#----------------------------------------------------------------------
# CGI program for displaying the status of batch jobs.
#
# Administrator may use this to see past or current batch job
# status information.
#
# Program may be invoked with posted variables to display status
# to a user.  If no variables are posted, the program displays
# a form to get user parameters for the status request, then
# processes them.
#
# May post:
#   jobId     = ID of job in batch_jobs table.
#   jobName   = Name of job.
#   jobAge    = Number of days to look backwards for jobs.
#   jobStatus = One of the status strings in cdrbatch.py.
#
# As with many other CDR CGI programs, the same program functions
# both to display a form and to read its contents.
#
# Rewritten July 2015 to eliminate security vulnerabilities.
#----------------------------------------------------------------------
import cdrbatch
import cdrcgi
import cgi

class Control:
    """
    Collects information about the report request and generates the report.
    """
    statuses = [getattr(cdrbatch, n) for n in dir(cdrbatch)
                if n.startswith("ST_")]
    def __init__(self):
        self.script = "getBatchStatus.py"
        fields = cgi.FieldStorage()
        self.session = cdrcgi.getSession(fields)
        self.request = cdrcgi.getRequest(fields)
        self.id = fields.getvalue("jobId")
        self.name = fields.getvalue("jobName")
        self.age = fields.getvalue("jobAge")
        self.status = fields.getvalue("status")
        self.sanitize()
        if self.request == "Cancel":
            cdrcgi.navigateTo("Admin.py", self.session)

    def sanitize(self):
        """
        Make sure the parameters haven't been tampered with.
        We don't need to worry about the job name parameter,
        because we're escaping it when we fold it into our
        form, and the cdrbatch module is doing the right thing
        with SQL placeholders to guard against an injection
        attach. That's a good thing, because it would be a
        challenge to come up with a regular expression which
        accepted all possible job names but rejected dangerous
        strings. The cdrbatch module allows for partial matches
        of the job name strings and wildcards; otherwise we
        could have checked against all unique strings in the
        database. Invoked by the Control constructor.
        """
        if not self.session:
            raise Exception("Missing or expired session")
        if self.id and not self.id.isdigit():
            raise Exception("Job ID must be an integer")
        if self.age and not self.age.isdigit():
            raise Exception("Job age must be an integer")
        if self.status and self.status not in Control.statuses:
            raise Exception("Parameter tampering detected")

    def run(self):
        """
        Shows the request form or the report as appropriate.
        """
        if self.request == "New Request":
            self.show_form()
        if self.id or self.name or self.age or self.status:
            self.show_report()
        self.show_form()

    def show_form(self):
        """
        Displays the search form for the report request.
        """
        self.pageopts = {
            "action": self.script,
            "session": self.session,
            "subtitle": "View batch jobs",
            "buttons": ("Submit", "Cancel")
        }
        page = cdrcgi.Page("CDR Batch Job Status Request", **self.pageopts)
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Enter Job ID or Other Options"))
        page.add_text_field("jobId", "Job ID")
        page.add_text_field("jobName", "Job Name")
        page.add_text_field("jobAge", "Job Age",
                            tooltip="Number of days to look back.")
        page.add_select("jobStatus", "Job Status", [""] + Control.statuses)
        page.add("</fieldset>")
        page.send()

    def show_report(self):
        """
        Show the information about the requested jobs. Use a custom
        Cell object (see below) for the last column.
        """
        columns = (
            cdrcgi.Report.Column("ID", width="40px"),
            cdrcgi.Report.Column("Job Name", width="200px"),
            cdrcgi.Report.Column("Started", width="150px"),
            cdrcgi.Report.Column("Status", width="100px"),
            cdrcgi.Report.Column("Last Info", width="150px"),
            cdrcgi.Report.Column("Last Message")#, width="300px")
        )
        rows = cdrbatch.getJobStatus(self.id, self.name, self.age, self.status)
        for row in rows:
            row[0] = cdrcgi.Report.Cell(row[0], classes="center")
            row[-1] = Cell(row[-1])
        caption = "Batch Jobs"
        table = cdrcgi.Report.Table(columns, rows, caption=caption)
        report = Report(self, table)
        report.send()

class Cell(cdrcgi.Report.Cell):
    """
    The batch job software violates the rule of applying display markup
    to information as far downstream as possible. As a result we have to
    override the Cell method which assembles the td element so we can
    parse the markup in the database column.
    """
    def to_td(self):
        markup = "<td>%s</td>" % (self._value or "").strip()
        td = cdrcgi.lxml.html.fragment_fromstring(markup)
        td.set("style", "xwidth: 300px; word-wrap: break-word;")
        return td

class Report(cdrcgi.Report):
    """
    Overrides the default cdrcgi.Report class so we can display our
    report inside a CGI form with buttons and hidden form fields.
    """
    def __init__(self, control, table):
        cdrcgi.Report.__init__(self, "CDR Batch Job Status Review", [table])
        self.control = control
    def _create_html_page(self, **opts):
        opts["session"] = self.control.session
        opts["action"] = self.control.script
        opts["buttons"] = ("Refresh", "New Request", "Cancel")
        opts["subtitle"] = "Batch status search results"
        opts["banner"] = self._title
        page = cdrcgi.Page(self._title, **opts)
        page.add_hidden_field("jobId", self.control.id or "")
        page.add_hidden_field("jobName", self.control.name or "")
        page.add_hidden_field("jobAge", self.control.age or "")
        page.add_hidden_field("jobStatus", self.control.status or "")
        page.add_css("table.report { width: 90%; table-layout: fixed; }")
        page.add_css(".right padding-right: 4px;")
        return page

def main():
    """
    Protect the top-level code so we can be imported by autodoc
    tools and code checkers.
    """
    Control().run()
if __name__ == "__main__":
    main()
