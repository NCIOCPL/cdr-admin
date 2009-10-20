#----------------------------------------------------------------------
#
# $Id$
#
# "We have a request from Oregeon Health Sciences University Cancer Center
# for a report in Excel format that lists OHSUCC trials that we have in PDQ.
# I think this would be a useful report to provide to other requestors also,
# hence, I would suggest that we create this report by allowing the user to
# specify the Organization, similar to the Organization Protocol Review Report.
#
# We need three worksheets (we could also allow users to select whether
# they want the full report, the lead org report or the site and lead org
# report.
#
# 1. Worksheet for Active, Approved Not Yet Active trials where the
#    organization is the Lead Organization.
#
# 2. Worksheet for Active, Approve Not Yet Active trials where the
#    organization is  a site (ProtocolSite or ExternalSite)
#
# 3. Worksheet for Closed, Temp Closed, and Completed trials where the
#    organization is a lead.
#
# Columns in the Spreadsheet would include
#
# PDQ Unique Identifier PDQ Primary Protocol ID(link to NCI Web site if
# Published)  Alternate IDs  ClinicalTrials.govID, Original Trial Title,
# Condition (use CTGOV Export Menu mapping - string together multiples
# with semicolon), Lead Org Personnel (not Update Person) (for Lead Org
# Worksheet) and PI at the site (for Site Worksheet)"
#
# [Amended by Lakshmi 2007-04-09:
#
# "For now, let us not include the conditions. 
#
# Would it be possible to get both the worksheets if we drop the conditions
# element?
#
# Could we add a column to indicate whether a trial is published on
# Cancer.gov yet?"]
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2009/07/02 15:07:05  venglisc
# Added additional columns with status information to worksheets. (Bug 4604)
#
# Revision 1.2  2007/04/23 12:42:02  bkline
# Changed filename for output at Lakshmi's request.
#
# Revision 1.1  2007/04/23 12:39:38  bkline
# Organization Protocols Spreadsheet report.
#
#----------------------------------------------------------------------

import cgi, cdrdb, cdrcgi, sys, cdr, ExcelWriter, time

debugging = False

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

def extractPersonName(docTitle):
    docTitle = docTitle.strip()
    if docTitle.lower().startswith('inactive;'):
        docTitle = docTitle[len('inactive;'):]
    semicolon = docTitle.find(';')
    if semicolon >= 0:
        docTitle = docTitle[:semicolon].strip()
    return docTitle

class Protocol:
    protocols = {}
    def __init__(self, docId, status):
        self.docId  = docId
        self.status = status
        self.active = status.lower() in ['active', 'approved-not yet active']

        cursor.execute("""\
            SELECT t.value
              FROM query_term t
              JOIN query_term o
                ON o.doc_id = t.doc_id
               AND LEFT(o.node_loc, 4) = LEFT(t.node_loc, 4)
             WHERE t.doc_id = ?
               AND t.path = '/InScopeProtocol/ProtocolTitle'
               AND o.path = '/InScopeProtocol/ProtocolTitle/@Type'
               AND o.value = 'Original'""", docId)
        rows = cursor.fetchall()
        self.title = rows and rows[0][0] or u"[NO ORIGINAL TITLE]"

        cursor.execute("""\
            SELECT t.value
              FROM query_term t
              JOIN query_term o
                ON o.doc_id = t.doc_id
               AND LEFT(o.node_loc, 4) = LEFT(t.node_loc, 4)
             WHERE t.doc_id = ?
               AND t.path = '/InScopeProtocol/ProtocolTitle'
               AND o.path = '/InScopeProtocol/ProtocolTitle/@Type'
               AND o.value = 'Professional'""", docId)
        rows = cursor.fetchall()
        self.ptitle = rows and rows[0][0] or u"[NO PROFESSIONAL TITLE]"

        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
               AND doc_id = ?""", docId)
        rows = cursor.fetchall()
        self.primaryId = rows and rows[0][0] or u"[NO PRIMARY PROTOCOL ID]"

        cursor.execute("""\
            SELECT i.value, t.value
              FROM query_term i
              JOIN query_term t
                ON i.doc_id = t.doc_id
               AND LEFT(i.node_loc, 8) = LEFT(t.node_loc, 8)
             WHERE i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND i.doc_id = ?""", docId, timeout = 300)
        rows = cursor.fetchall()
        self.altIds = []
        self.ctGovId = None
        for idValue, idType in rows:
            if idType == u"ClinicalTrials.gov ID":
                self.ctGovId = idValue
            else:
                self.altIds.append(idValue)

        cursor.execute("SELECT id FROM pub_proc_cg WHERE id = ?", docId)
        self.published = cursor.fetchall() and True or False

        cursor.execute("""\
            SELECT d.value, dt.value
              FROM query_term d
              JOIN query_term dt
                ON d.doc_id = dt.doc_id
               AND dt.path  = '/InScopeProtocol/ProtocolAdminInfo' +
                              '/CompletionDate/@DateType'
             WHERE d.path   = '/InScopeProtocol/ProtocolAdminInfo' +
                              '/CompletionDate'
               AND d.doc_id = ?""", docId, timeout = 300)
        row = cursor.fetchone()
        self.completionDate = row and row[0] or ''
        self.dateType       = row and row[1] or ''

        cursor.execute("""\
            SELECT c.doc_id, c.value, d.value
              FROM query_term c
              JOIN query_term d
                ON c.doc_id = d.doc_id
               AND d.path = '/InScopeProtocol/ProtocolAdminInfo'       +
                            '/ProtocolLeadOrg/LeadOrgProtocolStatuses' +
                            '/CurrentOrgStatus/StatusDate'
             WHERE c.path = '/InScopeProtocol/ProtocolAdminInfo'       +
                            '/ProtocolLeadOrg/LeadOrgProtocolStatuses' +
                            '/CurrentOrgStatus/StatusName'
               AND c.value in ('Closed', 'Completed')
               AND c.doc_id = ?""", docId, timeout = 300)
        row = cursor.fetchone()
        self.closedDate = row and row[2] or ''


class ProtocolOrg:
    def __init__(self, docId, status):
        if docId not in Protocol.protocols:
            Protocol.protocols[docId] = Protocol(docId, status)
        self.protocol = Protocol.protocols[docId]
        self.personnel = []


class LeadOrgProtocol(ProtocolOrg):
    def __init__(self, docId, status, nodeLoc):
        ProtocolOrg.__init__(self, docId, status)
        cursor.execute("""\
            SELECT d.title
              FROM document d
              JOIN query_term p
                ON p.int_val = d.id
              JOIN query_term r
                ON p.doc_id = r.doc_id
               AND LEFT(p.node_loc, 12) = LEFT(r.node_loc, 12)
             WHERE p.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/LeadOrgPersonnel'
                          + '/Person/@cdr:ref'
               AND r.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/LeadOrgPersonnel/PersonRole'
               AND r.value <> 'Update person'
               AND LEFT(p.node_loc, 8) = ?
               AND p.doc_id = ?""", (nodeLoc[:8], docId), timeout = 300)
        for row in cursor.fetchall():
            self.personnel.append(extractPersonName(row[0]))

if debugging:
    sitePIs = 0
class SiteOrgProtocol(ProtocolOrg):
    def __init__(self, docId, status, nodeLoc, external = False):
        ProtocolOrg.__init__(self, docId, status)
        if external:
            cursor.execute("""\
                SELECT d.title
                  FROM document d
                  JOIN query_term p
                    ON p.int_val = d.id
                 WHERE p.path = '/InScopeProtocol/ProtocolAdminInfo'
                              + '/ExternalSites/ExternalSite/ExternalSitePI'
                              + '/ExternalSitePIID/@cdr:ref'
                   AND LEFT(p.node_loc, 12) = ?
                   AND p.doc_id = ?""", (nodeLoc[:12], docId), timeout = 300)
        else:
            cursor.execute("""\
                SELECT d.title
                  FROM document d
                  JOIN query_term p
                    ON p.int_val = d.id
                  JOIN query_term r
                    ON r.doc_id = p.doc_id
                   AND LEFT(r.node_loc, 20) = LEFT(p.node_loc, 20)
                 WHERE p.path = '/InScopeProtocol/ProtocolAdminInfo'
                              + '/ProtocolLeadOrg/ProtocolSites/OrgSite'
                              + '/OrgSiteContact/SpecificPerson'
                              + '/Person/@cdr:ref'
                   AND r.path = '/InScopeProtocol/ProtocolAdminInfo'
                              + '/ProtocolLeadOrg/ProtocolSites/OrgSite'
                              + '/OrgSiteContact/SpecificPerson/Role'
                   AND p.doc_id = ?
                   AND r.value = 'Principal investigator'
                   AND LEFT(p.node_loc, 16) = ?""", (docId, nodeLoc[:16]),
                           timeout = 300)
        for row in cursor.fetchall():
            if debugging:
                global sitePIs
                sitePIs += 1
            self.personnel.append(extractPersonName(row[0]))

fields   = cgi.FieldStorage()
session  = fields and fields.getvalue("Session") or None
request  = cdrcgi.getRequest(fields)
orgId    = fields.getvalue('orgId')

#----------------------------------------------------------------------
# Handle requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Ask the user for the report parameters.
#----------------------------------------------------------------------
if not orgId:
    title    = "CDR Administration"
    instr    = "Organization Protocol Report"
    buttons  = ["Submit Request", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
    script   = "Request3109.py"
    header   = cdrcgi.header(title, title, instr, script, buttons)
    form     = """\
   <input type='hidden' name='%s' value='%s'>
   <table border='0'>
    <tr>
     <td align='right'><b>Document ID for Organization:&nbsp;</b></td>
     <td><input name='orgId' />
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)
    
orgId  = cdr.exNormalize(orgId)[1]
conn   = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

# Selecting all published, non-blocked protocols listing the given
# organization as a lead org
# ----------------------------------------------------------------
cursor.execute("""\
    SELECT s.doc_id, s.value, o.node_loc -- , l.value
      FROM query_term_pub s
      JOIN query_term_pub o
        ON s.doc_id = o.doc_id
      JOIN document d
        ON s.doc_id = d.id
      JOIN query_term_pub l
        ON s.doc_id = l.doc_id
       AND l.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrgRole'
       AND left(l.node_loc, 8) = left(o.node_loc, 8)
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND o.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrganizationID/@cdr:ref'
       AND o.int_val = ?
       AND l.value = 'Primary'
       AND d.active_status = 'A'""", orgId, timeout = 300)
leadOrgProtocols = []
rows = cursor.fetchall()
if debugging:
    i = 0
for docId, status, nodeLoc in rows:
    leadOrgProtocol = LeadOrgProtocol(docId, status, nodeLoc)
    leadOrgProtocols.append(leadOrgProtocol)
    if debugging:
        i += 1
        sys.stderr.write("\rcollected %d of %d lead org prots" % (i,
                                                                  len(rows)))
# Selecting all published, non-blocked protocols listing the given
# organization as a protocol site
# ----------------------------------------------------------------
cursor.execute("""\
    SELECT s.doc_id, s.value, o.node_loc
      FROM query_term_pub s
      JOIN query_term_pub o
        ON s.doc_id = o.doc_id
      JOIN document d
        ON s.doc_id = d.id
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND o.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref'
       AND o.int_val = ?
       AND s.value IN ('Active', 'Approved-not yet active')
       AND d.active_status = 'A'""", orgId, timeout = 300)
if debugging:
    i = 0
    sys.stderr.write("\n")
siteOrgProtocols = []
rows = cursor.fetchall()
for docId, status, nodeLoc in rows:
    siteOrgProtocol = SiteOrgProtocol(docId, status, nodeLoc)
    siteOrgProtocols.append(siteOrgProtocol)
    if debugging:
        i += 1
        sys.stderr.write("\rcollected %d of %d site prots" % (i, len(rows)))

# Selecting all published, non-blocked protocols listing the given
# organization as an external site
# ----------------------------------------------------------------
cursor.execute("""\
    SELECT s.doc_id, s.value, o.node_loc
      FROM query_term_pub s
      JOIN query_term_pub o
        ON s.doc_id = o.doc_id
      JOIN document d
        ON s.doc_id = d.id
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND o.path = '/InScopeProtocol/ProtocolAdminInfo/ExternalSites'
                  + '/ExternalSite/ExternalSiteOrg'
                  + '/ExternalSiteOrgID/@cdr:ref'
       AND o.int_val = ?
       AND s.value IN ('Active', 'Approved-not yet active')
       AND d.active_status = 'A'""", orgId, timeout = 300)
if debugging:
    i = 0
    sys.stderr.write("\n%d site PIs found\n" % sitePIs)
    sitePIs = 0
rows = cursor.fetchall()
for docId, status, nodeLoc in rows:
    siteOrgProtocol = SiteOrgProtocol(docId, status, nodeLoc, True)
    siteOrgProtocols.append(siteOrgProtocol)
    if debugging:
        i += 1
        sys.stderr.write("\rcollected %d of %d external site org prots" % (i,
                                                                  len(rows)))
# Selecting all published, non-blocked protocols listing the given
# organization as a lead org
# Since we suppressed the secondary lead orgs earlier we're 
# adding those here.
# ----------------------------------------------------------------
cursor.execute("""\
    SELECT s.doc_id, s.value, o.node_loc -- , l.value
      FROM query_term_pub s
      JOIN query_term_pub o
        ON s.doc_id = o.doc_id
      JOIN document d
        ON s.doc_id = d.id
      JOIN query_term_pub l
        ON s.doc_id = l.doc_id
       AND l.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrgRole'
       AND left(l.node_loc, 8) = left(o.node_loc, 8)
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND o.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrganizationID/@cdr:ref'
       AND o.int_val = ?
       AND l.value <> 'Primary'
       AND d.active_status = 'A'""", orgId, timeout = 300)

if debugging:
    i = 0
    sys.stderr.write("\n")

rows = cursor.fetchall()

for docId, status, nodeLoc in rows:
    siteOrgProtocol = SiteOrgProtocol(docId, status, nodeLoc, True)
    siteOrgProtocols.append(siteOrgProtocol)

    if debugging:
        i += 1
        sys.stderr.write("\rcollected %d of %d secondary site org prots" % (i,
                                                                   len(rows)))

if debugging:
    sys.stderr.write("\n%d site PIs found\n" % sitePIs)

def addSheet(wb, styles, protocolOrgs, title, sheet = 'ws2'):
    # Note: Columns with width "0.1" are hidden in the output
    colWidth = { 'ws1':[40, 125, 125, 100, 400,  60, 0.1, 0.1,  65, 100],
                 'ws2':[40, 125, 125, 100, 400, 0.1, 0.1, 0.1, 100,  65],
                 'ws3':[40, 125, 125, 100, 400,  60,  60,  60, 100,  65]}
    colName  = { 'ws1':['PDQ UI', 'Primary Protocol ID', 
                        'Alternate IDs', 'ClinicalTrials.gov ID', 
                        'Original Title / PDQ Title (bold)', 
                        'Completion Date (Projected/Actual)', 
                        '', '',
                        'Lead Org Personnel', 'Published?'],
                 'ws2':['PDQ UI', 'Primary Protocol ID',
                        'Alternate IDs', 'ClinicalTrials.gov ID', 
                        'Original Title / PDQ Title (bold)', 
                        '', 
                        '', '',
                        'PI', 'Published?'],
                 'ws3':['PDQ UI', 'Primary Protocol ID', 
                        'Alternate IDs', 'ClinicalTrials.gov ID', 
                        'Original Title / PDQ Title (bold)', 
                        'Completion Date (Projected/Actual)', 
                        'Current Prot. Status Date', 'Current Prot. Status',
                        'Lead Org Personnel', 'Published?']
                }
    ws = wb.addWorksheet(title)
    col = 1
    # The first 5 columns of the worksheets are identical
    # ---------------------------------------------------
    for width in colWidth[sheet]:
        ws.addCol(col, width)
        col += 1

    row = ws.addRow(1, styles.header)
    col = 1
    for name in colName[sheet]:
        row.addCell(col, name, style = styles.header)
        col += 1

    rowNum = 2
    for protocolOrg in protocolOrgs:
        row = ws.addRow(rowNum)
        row.addCell(1, protocolOrg.protocol.docId, style = styles.right)

        # Change per request (Bug 4606) 
        # Only published protocols are being displayed
        # ----------------------------------------------------------------
        if protocolOrg.protocol.published:
            published = "Yes"
            url = ("http://www.cancer.gov/clinicaltrials/"
                   "view_clinicaltrials.aspx?version=healthprofessional&"
                   "cdrid=%d" % protocolOrg.protocol.docId)
            row.addCell(2, protocolOrg.protocol.primaryId, style = styles.url,
                        href = url)
        else:
            published = "No"
            row.addCell(2, protocolOrg.protocol.primaryId, style = styles.left)

        altIds = u"\n".join(protocolOrg.protocol.altIds)
        personnel = u"\n".join(protocolOrg.personnel)
        row.addCell(3, altIds, style = styles.left)
        row.addCell(4, protocolOrg.protocol.ctGovId,    style = styles.left)

        if protocolOrg.protocol.title.upper() == 'NO ORIGINAL TITLE':
            row.addCell(5, protocolOrg.protocol.ptitle, style = styles.leftb)
        else:
            row.addCell(5, protocolOrg.protocol.title,  style = styles.left)

        if protocolOrg.protocol.completionDate:
            row.addCell(6, "%s (%s)" % (protocolOrg.protocol.completionDate,
                                        protocolOrg.protocol.dateType), 
                                                        style = styles.center)

        row.addCell(7, protocolOrg.protocol.closedDate, style = styles.center)
        row.addCell(8, protocolOrg.protocol.status,     style = styles.center)
        row.addCell(9, personnel, style = styles.left)
        row.addCell(10, published, style = styles.center)
        rowNum += 1

class Styles:
    def __init__(self, wb):

        # Create the style for the title of a sheet.
        font        = ExcelWriter.Font(name = 'Arial', size = 16, bold = True)
        align       = ExcelWriter.Alignment('Center', 'Center')
        self.title  = wb.addStyle(alignment = align, font = font)

        # Create the style for the column headers.
        font        = ExcelWriter.Font(name = 'Arial', size = 10, bold = True,
                                       color = 'green')
        align       = ExcelWriter.Alignment('Center', 'Center', True)
        self.header = wb.addStyle(alignment = align, font = font)

        # Create the style for the left-aligned, bold cells.
        font        = ExcelWriter.Font(name = 'Arial', size = 10, bold = True)
        align       = ExcelWriter.Alignment('Left', 'Top', True)
        self.leftb  = wb.addStyle(alignment = align, font = font)
        
        # Create the style for the linking cells.
        font        = ExcelWriter.Font('blue', None, 'Arial', size = 10)
        align       = ExcelWriter.Alignment('Left', 'Top', True)
        self.url    = wb.addStyle(alignment = align, font = font)

        # Create the style for the left-aligned cells.
        font        = ExcelWriter.Font(name = 'Arial', size = 10)
        self.left   = wb.addStyle(alignment = align, font = font)
        
        # Create the style for the centered cells.
        align       = ExcelWriter.Alignment('Center', 'Top', True)
        self.center = wb.addStyle(alignment = align, font = font)
        
        # Create the style for the right-aligned cells.
        align       = ExcelWriter.Alignment('Right', 'Top', True)
        self.right  = wb.addStyle(alignment = align, font = font)

wb      = ExcelWriter.Workbook()
styles  = Styles(wb)
addSheet(wb, styles, [p for p in leadOrgProtocols if p.protocol.active],
         "Lead Org (Active)", 'ws1')
addSheet(wb, styles, siteOrgProtocols, "Site (Active)")
addSheet(wb, styles, [p for p in leadOrgProtocols if not p.protocol.active],
         "Lead Org (Not Active)", 'ws3')
now = time.strftime("%Y%m%d%H%M%S")
filename = "OrganizationProtocolsSpreadsheet-%s.xls" % now
if not debugging:
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=%s" % filename
    print
wb.write(sys.stdout, True)
