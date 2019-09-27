#----------------------------------------------------------------------
#
# Report to list updated document count by document type.
#
# Added an option to the script (VOL=Y) to allow to pull out the
# media documents and create a list suitable for Visuals Online to be
# updated.
#
# BZIssue::2111
# BZIssue::3716
# BZIssue::4757
# BZIssue::5062 - Modify Media Change Report
# BZIssue::5173 - ICRDB Stats Report
# JIRA::OCECDR-3800 - Address security vulnerabilities
# JIRA::OCECDR-4165 - work around SQL Server limitation
#
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
import datetime
from cdrapi import db

LOG_QUERIES = False

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
conn      = db.connect()
cursor    = conn.cursor()
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
doc_type  = fields.getlist("doc_type")
date_from = fields.getvalue("date_from")
date_to   = fields.getvalue("date_to")
vol       = fields.getvalue("VOL")
audience  = fields.getvalue("audience") or "Both"
title     = "CDR Administration"
instr     = "Publishing Job Statistics by Date"
script    = "PubStatsByDate.py"
SUBMENU   = "Report Menu"
buttons   = ("Submit", SUBMENU, cdrcgi.MAINMENU)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Validate parameters
#----------------------------------------------------------------------
doc_type_choices = cdr.getDoctypes(session) + ["All"]
if request:   cdrcgi.valParmVal(request, valList=buttons)
if doc_type:  cdrcgi.valParmVal(doc_type, valList=doc_type_choices)
if date_from: cdrcgi.valParmDate(date_from)
if date_to:   cdrcgi.valParmDate(date_to)
if vol:       cdrcgi.valParmVal(vol, valList='Y')
if audience:
    vlist = "Both", "Patients", "Health_professionals"
    cdrcgi.valParmVal(audience, valList=vlist)

#----------------------------------------------------------------------
# Adjustments to form variables.
#----------------------------------------------------------------------
if not date_to:
    date_to = datetime.date.today()
if not date_from:
    date_from = date_to - datetime.timedelta(7)
if vol:
    instr = "Media Doc Publishing Report"

#----------------------------------------------------------------------
# Find the published document types.
# It doesn't make sense, but adding a second column to the results
# set speeds up the query by orders of magnitude.
#----------------------------------------------------------------------
def get_pub_doc_types():
    query = db.Query("doc_type t", "t.name", "d.doc_type").unique().order(1)
    query.join("document d", "d.doc_type = t.id")
    query.join("pub_proc_cg c", "c.id = d.id")
    if LOG_QUERIES:
        query.log(label="PUB DOC TYPES QUERY")
    return [row[0] for row in query.execute(cursor).fetchall()]

#----------------------------------------------------------------------
# Function to get the Media information to be displayed in the table
# from the CDR
# We're selecting the information for the latest version of the doc.
# OCECDR-4165: SQL Server can't handle the original query; do some
# of its work for it.
#----------------------------------------------------------------------
def get_media_info(ids):
    if not ids:
        return []
    last_ver = db.Query("doc_version", "MAX(num)").where("id = v.id")
    query = db.Query("query_term t", "t.doc_id", "t.value", "d.first_pub",
                        "v.dt", "v.updated_dt", "b.value", "v.num",
                        "v.publishable").unique().order("t.value")
    query.join("doc_version v", "t.doc_id = v.id")
    query.join("document d", "v.id = d.id")
    query.join("query_term c", "t.doc_id = c.doc_id")
    query.outer("query_term b",
                "t.doc_id = b.doc_id AND b.path = '/Media/@BlockedFromVOL'")
    query.where("t.path = '/Media/MediaTitle'")
    query.where("c.path = '/Media/MediaContent/Categories/Category'")
    query.where("c.value NOT IN ('pronunciation', 'meeting recording')")
    #query.where(query.Condition("d.id", ids, "IN"))
    query.where(query.Condition("v.num", last_ver))
    if LOG_QUERIES:
        query.log(label="MEDIA INFO QUERY")
    info = []
    for row in query.execute(cursor).fetchall():
        if row[0] in ids:
            info.append(row)
    return info

# ***** First Pass *****
#----------------------------------------------------------------------
# If we don't have a request, put up the form.
# For the Media Doc report, however, we only need the Start/End date
# fields to put up.
#----------------------------------------------------------------------
if not doc_type or not cdrcgi.is_date(date_from) or not cdrcgi.is_date(date_to):
    page = cdrcgi.Page(title, subtitle=instr, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Date Range"))
    page.add_date_field("date_from", "Start Date", value=date_from)
    page.add_date_field("date_to", "End Date", value=date_to)
    page.add("</fieldset>")
    if vol:
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Audience"))
        page.add_radio("audience", "Both", "Both", checked=True)
        page.add_radio("audience", "Patient", "Patients")
        page.add_radio("audience", "Health Professional",
                       "Health_professionals")
        page.add("</fieldset>")
        page.add(page.B.INPUT(name="doc_type", value="Media", type="hidden"))
        page.add(page.B.INPUT(name="VOL", value="Y", type="hidden"))
    else:
        doc_types = get_pub_doc_types()
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Choose Document Type(s)"))
        page.add_checkbox("doc_type", "All", "All", checked=True,
                          onclick="clear_others();")
        for t in doc_types:
            page.add_checkbox("doc_type", t, t, onclick="clear_all();",
                              widget_classes="dt-cb")
        page.add("</fieldset>")
        page.add_script("""\
function clear_all() { jQuery("#doc_type-all").prop("checked", false); }
function clear_others() { jQuery(".dt-cb").prop("checked", false); }""")
    page.send()

# ***** Second Pass *****
#----------------------------------------------------------------------
# Creating temporary tables
# The SQL queries for both reports Media Doc and Job Statistics are
# slightly different, in the first we're selecting document IDs in the
# other one we're selecting counts.
#----------------------------------------------------------------------

# Create #removed table
# ---------------------
query = db.Query("pub_proc_doc d", "d.doc_id", "MAX(p.started) AS started")
query.join("pub_proc p", "p.id = d.pub_proc")
query.where(query.Condition("p.started", "%s 23:59:59" % date_to, "<="))
query.where("p.pub_subset LIKE 'Push_%'")
query.where("p.status = 'Success'")
query.where("d.removed = 'Y'")
query.group("d.doc_id")
query.into("##removed")
if LOG_QUERIES:
    query.log(label="##REMOVED QUERY")
query.execute(cursor)
conn.commit()

# Create #prevpub table
# ----------------------
query = db.Query("pub_proc_doc d", "d.doc_id").unique()
query.join("pub_proc p", "p.id = d.pub_proc")
query.where(query.Condition("p.started", date_from, "<"))
query.where("p.pub_subset LIKE 'Push_%'")
query.where("p.status = 'Success'")
query.into("##prevpub")
if LOG_QUERIES:
    query.log(label="##PREVPUB QUERY")
query.execute(cursor)
conn.commit()

# Create #brandnew table
# ----------------------
subquery = db.Query("##prevpub", "doc_id")
query = db.Query("pub_proc_doc d", "d.doc_id", "MIN(p.started) AS started")
query.join("pub_proc p", "p.id = d.pub_proc")
query.where(query.Condition("p.started", date_from, ">="))
query.where(query.Condition("p.started", "%s 23:59:59" % date_to, "<="))
query.where("p.pub_subset LIKE 'Push_%'")
query.where("p.status = 'Success'")
query.where(query.Condition("d.doc_id", subquery, "NOT IN"))
query.group("d.doc_id")
query.into("##brandnew")
if LOG_QUERIES:
    query.log(label="##BRANDNEW QUERY")
query.execute(cursor)
conn.commit()

# Create #phoenix table
# ---------------------
query = db.Query("pub_proc_doc d", "d.doc_id", "MIN(p.started) AS started")
query.join("pub_proc p", "p.id = d.pub_proc")
query.join("##removed r", "r.doc_id = d.doc_id")
query.where("p.started > r.started")
query.where("p.pub_subset LIKE 'Push_%'")
query.where("p.status = 'Success'")
query.where("d.removed = 'N'")
query.group("d.doc_id")
query.into("##phoenix")
if LOG_QUERIES:
    query.log(label="##PHOENIX QUERY")
query.execute(cursor)
conn.commit()

def get_docs_or_counts(cursor, temp_table, date_from, date_to, vol):
    if vol:
        query = db.Query("%s p" % temp_table, "p.doc_id")
        query.where("t.name = 'Media'")
    else:
        query = db.Query("%s p" % temp_table, "t.name", "COUNT(*)")
        query.group("t.name")
    query.join("document d", "d.id = p.doc_id")
    query.join("doc_type t", "d.doc_type = t.id")
    query.where(query.Condition("p.started", date_from, ">="))
    query.where(query.Condition("p.started", "%s 23:59:59" % date_to, "<="))
    if LOG_QUERIES:
        query.log(label="#DOCS OR COUNTS QUERY (%s)" % temp_table)
    return query.execute(cursor).fetchall()

# Select information from removed table (count or doc-ID)
# -------------------------------------------------------
removes = get_docs_or_counts(cursor, "##removed", date_from, date_to, vol)

# Select information of brandnew table (count or doc_ID)
# ------------------------------------------------------
brandnews = get_docs_or_counts(cursor, "##brandnew", date_from, date_to, vol)

# Select information of re-published new table (count or doc-id)
# --------------------------------------------------------------
renews = get_docs_or_counts(cursor, "##phoenix", date_from, date_to, vol)

# Select information of updated table (count or doc-id)
# Note: This might count documents multiple times.
#       If a document has been added *and* updated
#       during the given time period it's counted once
#       in each category.
# -----------------------------------------------------
if vol:
    query = db.Query("pub_proc_doc pd", "d.id").unique()
    query.where("t.name = 'Media'")
else:
    query = db.Query("pub_proc_doc pd", "t.name", "COUNT(DISTINCT d.id)")
    query.group("t.name")
query.join("pub_proc p", "p.id = pd.pub_proc")
query.join("document d", "d.id = pd.doc_id")
query.join("doc_type t", "t.id = d.doc_type")
query.where("p.started >= '%s'" % date_from)
query.where("p.started <= '%s 23:59:59'" % date_to)
query.where("p.pub_subset LIKE 'Push_%'")
query.where("p.status = 'Success'")
query.where("pd.removed = 'N'")
if LOG_QUERIES:
    query.log(label="UPDATES2 QUERY")
updates2 = query.execute(cursor).fetchall()

# Select information of updated table (count or doc-id)
# Note: This counts every document exactly one time.
#       If a document has been added *and* updated
#       during the given time period it's only been
#       counted as an added document.
# -----------------------------------------------------
subquery1 = db.Query("##phoenix", "doc_id")
subquery1.where("started >= '%s'" % date_from)
subquery1.where("started <= '%s 23:59:59'" % date_to)
subquery2 = db.Query("##brandnew", "doc_id")
subquery2.where("started >= '%s'" % date_from)
subquery2.where("started <= '%s 23:59:59'" % date_to)
query.where(query.Condition("d.id", subquery1, "NOT IN"))
query.where(query.Condition("d.id", subquery2, "NOT IN"))
if LOG_QUERIES:
    query.log(label="UPDATES QUERY")
updates = query.execute(cursor).fetchall()


# Create a dictionary out of the update list
# (It's easier to select the results later on)
# --------------------------------------------
countUpdate   = {}
countUpdate2  = {}
countRemove   = {}
countRenew    = {}
countBrandnew = {}

#----------------------------------------------------------------------
# Bolted on the side for enhancement request #4757: support restriction
# of the report on published media documents by audience.
#----------------------------------------------------------------------
if vol and audience != 'Both':
    paths = (
        "/Media/MediaContent/Captions/MediaCaption/@audience",
        "/Media/MediaContent/ContentDescriptions/ContentDescription/@audience",
    )
    query = db.Query("query_term_pub", "doc_id").unique()
    query.where(query.Condition("value", audience))
    query.where(query.Condition("path", paths, "IN"))
    if LOG_QUERIES:
        query.log(label="AUDIENCES QUERY")
    audiences = set([row[0] for row in query.execute(cursor, 300).fetchall()])

# Collect all doc-ids in one list and get the information for the
# report for each of the documents from the database
# ---------------------------------------------------------------
if vol:
    mediaIds = []
    for docSet in (updates, updates2, removes, brandnews, renews):
        for doc in docSet:
            if audience == 'Both' or doc[0] in audiences:
                mediaIds.append(doc[0])

    mediaRecords = get_media_info(mediaIds)

# Store the row counts in a dictionary to be accessed later
# ---------------------------------------------------------
else:
    for update in updates:
        countUpdate[update[0]] = update[1]

    for update2 in updates2:
        countUpdate2[update2[0]] = update2[1]

    for remove in removes:
        countRemove[remove[0]] = remove[1]

    for brandnew in brandnews:
        countBrandnew[brandnew[0]] = brandnew[1]

    for renew in renews:
        countRenew[renew[0]] = renew[1]

#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = datetime.date.today().strftime("%B %d, %Y")

#----------------------------------------------------------------------
# Create the results page.
#----------------------------------------------------------------------
instr     = 'Published%s Documents on Cancer.gov -- %s.' % (
                                      vol and ' Media' or '', dateString)
header    = cdrcgi.header(title, title, instr, script, buttons[1:],
                          stylesheet = """
   <STYLE type="text/css">
    H3            { font-weight: bold;
                    font-family: Arial;
                    font-size: 16pt;
                    margin: 8pt; }
    TABLE.output  { margin-left: auto;
                    margin-right: auto; }
    TABLE.output  TD
                  { padding: 3px; }
    TD.header     { font-weight: bold;
                    text-align: center; }
    TR.odd        { background-color: #E7E7E7; }
    TR.even       { background-color: #FFFFFF; }
    TR.head       { background-color: #D2D2D2; }
    .link         { color: blue;
                    text-decoration: underline; }
    .doc          { text-align: left;
                    vertical-align: top; }
    .star         { background-color: #D2D2D2; }
    p             { font-weight: bold;
                    font-family: Arial;
                    font-size: 10pt; }
    #wrapper      { text-align: center;
                    margin: 0 auto;
                    width: 500px;
                    border: 1px solid #ccc;
                    padding: 5px; }
    #myvar        { border: 1px solid #ccc;
                    background: #f2f2f2;
                    padding: 10px }
   </STYLE>

   <script language='JavaScript' type='text/javascript'>
       function showDoc(obj) {
           var el = document.getElementById(obj);
           if ( el.style.display == "none") {
                el.style.display = '';
           }
           else {
                el.style.display = 'none';
           }
       }
   </script>
""")

# -------------------------
# Display the Report Title
# -------------------------
report    = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
""" % (cdrcgi.SESSION, session)

# ------------------------------------------------------------------------
# Display Summary Title including CDR ID
# ------------------------------------------------------------------------
audienceHeader = ""
if vol and audience != 'Both':
    audienceHeader = "%s<br />" % {
        "Health_professionals": "Health Professional",
        "Patients": "Patient" }.get(audience, "Unrecognized audience")
report += """\
  <center>
    <H3>Published %s Documents</H3>
     Report includes publishing jobs started between<br/>
     <b>%s</b> and <b>%s</b><br/>%s
""" % (vol and 'Media' or '', date_from, date_to, audienceHeader)

if not vol:
    report += """\
     <div id="wrapper">
      <p>For an explanation of the numbers please click
         <span class="link">
          <a onclick="showDoc('myvar');" title="Explain the Numbers">here</a>
         </span>
      </p>
      <div id="myvar" style="display: none">
       <table>
        <tr>
         <td class="doc"><strong>Added-Old</strong></td>
         <td class="doc">This number includes documents that existed
                         on Cancer.gov, had been removed and added again.</td>
        </tr>
        <tr>
         <td class="doc"><strong>Added-New</strong></td>
         <td class="doc">This number includes documents that are new and
                         never existed on Cancer.gov before.</td>
        </tr>
        <tr>
         <td class="doc"><strong>Updated</strong></td>
         <td class="doc">This number includes documents that have been
                         updated on Cancer.gov. If a document has been
                         added <strong>and</strong> updated during the
                         specified time period it is
                         only counted as a new document.</td>
        </tr>
        <tr>
         <td class="doc"><strong>Updated*</strong></td>
         <td class="doc">This number includes documents that have been
                         updated on Cancer.gov. If a document has been
                         added <strong>and</strong> updated during the
                         specified time period it is
                         counted twice, once as a new document
                         and once as an updated document.</td>
        </tr>
        <tr>
         <td class="doc"><strong>Removed</strong></td>
         <td class="doc">This number includes documents that have been
                         removed from Cancer.gov.</td>
        </tr>
        <tr>
         <td class="doc"><strong>Total</strong></td>
         <td class="doc">This number sums up all columns (except for
                         the column Updated* to only count a document
                         once per time frame specified.</td>
        </tr>
       </table>
      </div>
     </div>
  </center>
  <p></p>
"""

# ***** Main part for Media Doc Published report *****
# ----------------------------------------------------
if vol:
    report += """
  <br>
  <table class="output" border="1">
   <tr class="head">
    <td class="header">CDR-ID</td>
    <td class="header">Media Title</td>
    <td class="header">First Pub Date</td>
    <td class="header">Version Date</td>
    <td class="header">Last Version<br/>Publishable</td>
    <td class="header">Blocked from<br/>VOL</td>
   </tr>
"""
    count = 0
    for id, title, first, verDt, audDt, volFlag, ver, \
        publishable in mediaRecords:
        count += 1
        if count % 2 == 0:
            report += '   <tr class="even">'
        else:
            report += '   <tr class="odd">'

        report += """
    <td class="link">
     <a href="/cgi-bin/cdr/GetCdrImage.py?id=CDR%s.jpg">%s</a>
    </td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td align="center">%s</td>
    <td align="center">%s</td>
   </tr>
""" % (id, id, title, first and str(first)[:10] or "",
       verDt and str(verDt)[:16] or "", publishable,
       volFlag and volFlag[:1] or "")


    footer = """\
  </table>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(header + report + footer)


# ***** Main section for Job Statistics report display *****
# ----------------------------------------------------------
# Display the header row
# ----------------------
report += """
   <table class="output" width="50%%" border="0">
    <tr class="head">
     <td class="header" width="22%%">Doc Type</td>
     <td class="header" width="13%%">Added-Old</td>
     <td class="header" width="13%%">Added-New</td>
     <td class="header" width="13%%">Updated</td>
     <td class="header star" width="13%%">Updated*</td>
     <td class="header" width="13%%">Removed</td>
     <td class="header" width="13%%">Total</td>
    </tr>"""

# Selecting the document types to be displayed
# User can select to display all document types or select individual
# document types by selecting a check box.
# ------------------------------------------------------------------
if "All" in doc_type:
    doc_types = get_pub_doc_types()
else:
    doc_types = doc_type

# Display the columns of the display table
# (Creating a column should probably be handled in a function)
# ------------------------------------------------------------
count = 0
for doc_type in doc_types:
    total = 0
    count += 1

    # Display first column (list of document types selected)
    # ------------------------------------------------------
    if count % 2 == 0:
        report += """
    <tr class="even">"""
    else:
        report += """
    <tr class="odd">"""

    report += """
     <td><b>%s</b></td>""" % doc_type

    # Display second column (documents added again after being deleted)
    # -----------------------------------------------------------------
    if doc_type in countRenew:
        total += countRenew[doc_type]
        report += """
     <td align="right">
      <b>%s</b>
     </td>""" % countRenew[doc_type]
    else:
        report += """
     <td align="right">0</td>"""

    # Display third column (documents being added for the first time)
    # ---------------------------------------------------------------
    if doc_type in countBrandnew:
        total += countBrandnew[doc_type]
        report += """
     <td align="right">
      <b>%s<b/>
     </td>""" % countBrandnew[doc_type]
    else:
        report += """
     <td align="right">0</td>"""

    # Display fourth column (updated documents - unique count)
    # --------------------------------------------------------
    if doc_type in countUpdate:
        total += countUpdate[doc_type]
        report += """
     <td align="right">
      <b>%s</b>
     </td>""" % countUpdate[doc_type]
    else:
        report += """
     <td align="right">0</td>"""

    # Display fifth column (updated documents - not unique count)
    # We are not counting these to the total
    # -----------------------------------------------------------
    if doc_type in countUpdate:
        # total += countUpdate2[doc_type]
        report += """
     <td class="star" align="right">
      <b>%s</b>
     </td>""" % countUpdate2[doc_type]
    else:
        report += """
     <td align="right">0</td>"""

    # Display sixth column (documents being deleted)
    # ----------------------------------------------
    if doc_type in countRemove:
        total += countRemove[doc_type]
        report += """
     <td align="right">
      <b>%s</b>
     </td>""" % countRemove[doc_type]
    else:
        report += """
     <td align="right">0</td>"""

    # Display total column (a total of all previous columns
    # except for the second update column)
    # ------------------------------------------------------
    if total:
        report += """
     <td align="right">
      <b>%s</b>
     </td>""" % total
    else:
        report += """
     <td align="right">
      <b>0</b>
     </td>"""

    report += """
    </tr>"""

report += """
   </table>"""

footer = """\
 </BODY>
</HTML>
"""

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + report + footer)
