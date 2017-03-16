#----------------------------------------------------------------------
# Report on recently imported CT.gov protocols.
# JIRA::OCECDR-3877
#----------------------------------------------------------------------
import cdrcgi
import cdrdb
import cgi
import datetime

#----------------------------------------------------------------------
# Collect the request's parameters.
#----------------------------------------------------------------------
fields = cgi.FieldStorage()
start_date = fields.getvalue("startdate")
end_date = fields.getvalue("enddate")
fmt = fields.getvalue("format")
title = "Recent CT.gov Protocols"
script = "RecentCTGovProtocols.py"
SUBMENU = "Report Menu"
buttons = ("Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out")
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)

#----------------------------------------------------------------------
# If we don't have the required parameters, ask for them.
#----------------------------------------------------------------------
if not cdrcgi.is_date(start_date) or not cdrcgi.is_date(end_date):
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(30)
    subtitle = "Clinical Trial Documents at NLM"
    page = cdrcgi.Page(title, subtitle=subtitle, action=script, buttons=buttons,
                       session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Report Parameters"))
    page.add_date_field("startdate", "Start Date", value=start_date)
    page.add_date_field("enddate", "End Date", value=end_date)
    page.add("</fieldset>")
    page.add_output_options("excel")
    page.send()

#----------------------------------------------------------------------
# Create the report.
#----------------------------------------------------------------------
cursor = cdrdb.connect("CdrGuest").cursor()
query = cdrdb.Query("ctgov_trial", "nct_id", "first_received", "trial_title",
                    "trial_phase")
query.where(query.Condition("first_received", start_date, ">="))
query.where(query.Condition("first_received", "%s 23:59:59" % end_date, "<="))
query.order(1)
fp = open("d:/tmp/rcp.sql", "w")
fp.write("%s\n" % query)
fp.write("%s\n" % start_date)
fp.write("%s\n" % end_date)
fp.close()
results = query.execute(cursor).fetchall()
columns = (
    cdrcgi.Report.Column("NCT ID", width="100px"),
    cdrcgi.Report.Column("Received", width="100px"),
    cdrcgi.Report.Column("Trial Title", width="500px"),
    cdrcgi.Report.Column("Phase", width="100px"),
    cdrcgi.Report.Column("Other IDs", width="200px"),
    cdrcgi.Report.Column("Sponsors", width="1000px")
)
rows = []
for nct_id, received, title, phase in results:
    query = cdrdb.Query("ctgov_trial_other_id", "other_id").order("position")
    query.where(query.Condition("nct_id", nct_id))
    ids = u"; ".join([row[0] for row in query.execute(cursor).fetchall()])
    query = cdrdb.Query("ctgov_trial_sponsor", "sponsor").order("position")
    query.where(query.Condition("nct_id", nct_id))
    sponsors = u"; ".join([row[0] for row in query.execute(cursor).fetchall()])
    href = "https://clinicaltrials.gov/ct2/show/%s" % nct_id
    row = (cdrcgi.Report.Cell(nct_id, href=href, target="_blank"),
           str(received)[:10], title, phase or u"", ids, sponsors)
    rows.append(row)
caption = "CT.gov Protocols Received between %s and %s" % (start_date, end_date)
table = cdrcgi.Report.Table(columns, rows, caption=caption)
report = cdrcgi.Report("Recent CT.gov Protocols", [table])
report.send(fmt)
