#----------------------------------------------------------------------
#
# Reports on documents which link to a specified document.
#
# BZIssue::161
# BZIssue::1532
# BZIssue::3716
# BZIssue::4672 - Changes to LinkedDoc Report
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi
import datetime
import urllib
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
cursor       = db.connect(user="CdrGuest").cursor()
fields       = cgi.FieldStorage()
doc_id       = fields.getvalue("doc_id") or fields.getvalue("DocId")
frag_id      = fields.getvalue("frag_id") or fields.getvalue("FragId") or u""
doc_title    = unicode(fields.getvalue("doc_title", ""), "utf-8")
linked_type  = fields.getvalue("linked_type")
linking_type = fields.getvalue("linking_type") or u""
with_blocked = fields.getvalue("with_blocked") or u"N"
session      = cdrcgi.getSession(fields)
request      = cdrcgi.getRequest(fields)
title        = "Linked Documents Report"
instr        = "Report on documents which link to a specified document"
script       = "LinkedDocs.py"
SUBMENU      = "Report Menu"
buttons      = ("Submit", SUBMENU, cdrcgi.MAINMENU)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Show a list of the matching documents so the user can pick one.
#----------------------------------------------------------------------
def put_up_selection(rows):
    page = cdrcgi.Page(title, subtitle=instr, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add_css("fieldset { width: 1000px; }")
    page.add(page.B.LEGEND("Select Linked Document For Report"))
    for doc_id, name in rows:
        id_string = cdr.normalize(doc_id)
        label = u"%s: %s" % (id_string, name)
        page.add_radio("doc_id", label, id_string)
    page.add("</fieldset>")
    page.add(page.B.INPUT(name="frag_id", value=frag_id, type="hidden"))
    page.add(page.B.INPUT(name="linking_type", value=linking_type,
                          type="hidden"))
    page.add(page.B.INPUT(name="with_blocked", value=with_blocked,
                          type="hidden"))
    page.send()

#----------------------------------------------------------------------
# Search for linked document by title, if so requested.
#----------------------------------------------------------------------
if doc_title and not doc_id:
    query = db.Query("document d", "d.id", "d.title")
    if linked_type:
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", linked_type))
    query.where(query.Condition("d.title", doc_title + "%", "LIKE"))
    rows = query.order("d.title").execute(cursor).fetchall()
    if not rows:
        cdrcgi.bail("No documents match %s" % repr(doc_title))
    if len(rows) > 1:
        put_up_selection(rows)
    doc_id = rows[0][0]

#----------------------------------------------------------------------
# Describe the linked document.
#----------------------------------------------------------------------
def show_target_info(table, page):
    target_info = table.user_data()
    doc_id = target_info["doc_id"]
    doc_title = target_info["doc_title"]
    doc_type = target_info["doc_type"]
    page.add_css("""\
.target-info th { width: 130px; text-align: right; }
.target-info td { width: 860px; }""")
    page.add('<table class="report target-info">')
    page.add(page.B.CAPTION("Target Document"))
    page.add('<tr class="odd">')
    page.add(page.B.TH("Document Type"))
    page.add(page.B.TD(doc_type))
    page.add("</tr>")
    page.add('<tr class="odd">')
    page.add(page.B.TH("Document Title"))
    page.add(page.B.TD(doc_title))
    page.add("</tr>")
    page.add('<tr class="odd">')
    page.add(page.B.TH("Document ID"))
    page.add(page.B.TD(str(doc_id)))
    page.add("</tr>")
    page.add("</table>")

#----------------------------------------------------------------------
# Callback to show current date and user for whom report was run.
#----------------------------------------------------------------------
def show_footer(table, page):
    try:
        query = db.Query("usr u", "u.fullname")
        query.join("session s", "u.id = s.usr")
        query.where(query.Condition("s.name", session))
        user = query.execute().fetchall()[0][0]
    except:
        user = "anonymous user"
    today = datetime.date.today().strftime("%b %d, %Y")
    page.add(page.B.P("Report generated %s for %s" % (today, user),
                      page.B.CLASS("emphasis center")))

#----------------------------------------------------------------------
# Assemble and display the report.
#----------------------------------------------------------------------
def show_report(doc_id, frag_id):
    id_pieces = cdr.exNormalize(doc_id)
    doc_id = id_pieces[1]
    if not frag_id:
        frag_id = id_pieces[2]

    # Get the target doc info.
    query = db.Query("document d", "d.title", "t.name")
    query.join("doc_type t", "t.id = d.doc_type")
    query.where(query.Condition("d.id", doc_id))
    rows = query.execute(cursor).fetchall()
    target_info = {
        "doc_id": doc_id,
        "doc_title": rows[0][0],
        "doc_type": rows[0][1]
    }

    # Find the links.
    columns = ("d.id", "d.title", "t.name", "n.source_elem", "n.target_frag")
    query = db.Query("document d", *columns)
    query.join("doc_type t", "t.id = d.doc_type")
    query.join("link_net n", "d.id = n.source_doc")
    query.where(query.Condition("n.target_doc", doc_id))
    if linking_type:
        query.where(query.Condition("t.name", linking_type))
    if frag_id:
        query.where(query.Condition("n.target_frag", frag_id))
    if with_blocked == "N":
        query.where("d.active_status = 'A'")
    results = query.order(3, 2, 4, 5).execute().fetchall()

    # Build the report and show it.
    args = {
        "html_callback_pre": show_target_info,
        "user_data": target_info
    }
    tables = []
    if not results:
        args["html_callback_post"] = show_footer
        nada = "No link to this document found."
        col = cdrcgi.Report.Column(nada, width="500px")
        table = cdrcgi.Report.Table((col,), [], **args)
        tables.append(table)
    last_doc_type = ""
    rows = []
    columns = (
        cdrcgi.Report.Column("Doc ID", width="80px"),
        cdrcgi.Report.Column("Doc Title", width="550px"),
        cdrcgi.Report.Column("Linking Element", width="200px"),
        cdrcgi.Report.Column("Fragment ID", width="150px"),
    )
    for doc_id, doc_title, doc_type, source_elem, target_frag in results:
        if doc_type != last_doc_type:
            if rows:
                args["caption"] = u"Links From %s Documents" % last_doc_type
                tables.append(cdrcgi.Report.Table(columns, rows, **args))
                rows = []
                args = {}
            last_doc_type = doc_type
        doc_id_string = "CDR%d" % doc_id
        params = { "DocId": doc_id_string, "Session": session or "guest" }
        url = "QcReport.py?%s" % urllib.urlencode(params)
        row = (
            cdrcgi.Report.Cell(doc_id_string, href=url),
            doc_title or "",
            source_elem or "",
            target_frag or "",
        )
        rows.append(row)
    if last_doc_type:
        args["caption"] = u"Links From %s Documents" % last_doc_type
        args["html_callback_post"] = show_footer
        tables.append(cdrcgi.Report.Table(columns, rows, **args))
    report = cdrcgi.Report(title, tables, banner=title, subtitle=instr)
    report.send()

#----------------------------------------------------------------------
# If we have a document ID, produce a report.
#----------------------------------------------------------------------
if doc_id:
    try:
        show_report(doc_id, frag_id)
    except Exception as e:
        cdrcgi.bail("%s" % e)

#----------------------------------------------------------------------
# Retrieve the list of document type names.
#----------------------------------------------------------------------
def get_doc_types():
    try:
        cursor.execute("""\
SELECT DISTINCT name
           FROM doc_type
          WHERE name IS NOT NULL and name <> '' AND active = 'Y'
       ORDER BY name
""")
        return cursor.fetchall()
    except Exception as e:
        cdrcgi.bail('Database query failure: %s' % e)

#----------------------------------------------------------------------
# Put up the main request form.
#----------------------------------------------------------------------
doc_types = [(row[0], row[0]) for row in get_doc_types()]
page = cdrcgi.Page(title, subtitle=instr, action=script, session=session,
                   buttons=buttons)
instructions = (
    "Enter the criteria for the report. "
    "You can either enter the CDR ID for the linked document "
    "or you can provide the title of that document (and optionally "
    "a document type). "
    "If you enter a title string which matches the start of more than "
    "one document title (for that document type, if you have selected "
    "a type), you will be asked to select the document from a list of "
    "those which match. "
    "You can also specify a fragment ID to further restrict the links "
    "which are reported to those which link to one specific element of "
    "the target document. "
    "You can restrict the report to links from only a specified document "
    "type, or you can include links from any document type. "
    "Finally, you can exclude or include links from documents which "
    "have been blocked."
)
page.add(page.B.FIELDSET(page.B.P(instructions)))
page.add("<fieldset>")
page.add(page.B.LEGEND("Linked Document"))
page.add_text_field("doc_id", "Document ID")
page.add_text_field("frag_id", "Fragment ID")
page.add_text_field("doc_title", "Doc Title")
page.add_select("linked_type", "Doc Type", [("", "")] + doc_types)
page.add("</fieldset>")
page.add("<fieldset>")
page.add(page.B.LEGEND("Linking Documents"))
page.add_select("linking_type", "Doc Type", [("", "Any")] + doc_types)
page.add("<fieldset>")
page.add(page.B.LEGEND("Links From Blocked Documents"))
page.add_radio("with_blocked", "Include", "Y")
page.add_radio("with_blocked", "Exclude", "N", checked=True)
page.add("</fieldset>")
page.add("</fieldset>")
page.send()
