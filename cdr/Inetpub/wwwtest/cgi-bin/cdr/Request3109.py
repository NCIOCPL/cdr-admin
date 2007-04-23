#----------------------------------------------------------------------
#
# $Id: Request3109.py,v 1.1 2007-04-23 12:39:38 bkline Exp $
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
cursor.execute("""\
    SELECT s.doc_id, s.value, o.node_loc
      FROM query_term s
      JOIN query_term o
        ON s.doc_id = o.doc_id
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND o.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrganizationID/@cdr:ref'
       AND o.int_val = ?""", orgId, timeout = 300)
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
cursor.execute("""\
    SELECT s.doc_id, s.value, o.node_loc
      FROM query_term s
      JOIN query_term o
        ON s.doc_id = o.doc_id
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND o.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref'
       AND o.int_val = ?
       AND s.value IN ('Active', 'Approved-not yet active')""", orgId,
               timeout = 300)
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

cursor.execute("""\
    SELECT s.doc_id, s.value, o.node_loc
      FROM query_term s
      JOIN query_term o
        ON s.doc_id = o.doc_id
     WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND o.path = '/InScopeProtocol/ProtocolAdminInfo/ExternalSites'
                  + '/ExternalSite/ExternalSiteOrg'
                  + '/ExternalSiteOrgID/@cdr:ref'
       AND o.int_val = ?
       AND s.value IN ('Active', 'Approved-not yet active')""", orgId,
               timeout = 300)
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
if debugging:
    sys.stderr.write("\n%d site PIs found\n" % sitePIs)

def addSheet(wb, styles, protocolOrgs, title, sites = False):
    ws = wb.addWorksheet(title)
    col = 1
    for width in (40, 125, 125, 100, 400, 100, 65):
        ws.addCol(col, width)
        col += 1
    row = ws.addRow(1, styles.header)
    col = 1
    for name in ('PDQ UI', 'Primary Protocol ID', 'Alternate IDs',
                 'ClinicalTrials.gov ID', 'Original Trial Title',
                 sites and 'PI' or 'Lead Org Personnel', 'Published?'):
        row.addCell(col, name, style = styles.header)
        col += 1
    rowNum = 2
    for protocolOrg in protocolOrgs:
        row = ws.addRow(rowNum)
        row.addCell(1, protocolOrg.protocol.docId, style = styles.right)
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
        row.addCell(4, protocolOrg.protocol.ctGovId, style = styles.left)
        row.addCell(5, protocolOrg.protocol.title, style = styles.left)
        row.addCell(6, personnel, style = styles.left)
        row.addCell(7, published, style = styles.center)
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
         "Lead Org (Active)")
addSheet(wb, styles, siteOrgProtocols, "Site (Active)", True)
addSheet(wb, styles, [p for p in leadOrgProtocols if not p.protocol.active],
         "Lead Org (Not Active)")
now = time.strftime("%Y%m%d%H%M%S")
filename = "Request3109-%s.xls" % now
if not debugging:
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=%s" % filename
    print
wb.write(sys.stdout, True)
