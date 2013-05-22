#----------------------------------------------------------------------
#
# $Id: $
#
# CTGov Transfer report by Organization and Status.
# This report already exists as a batch version but the users wanted to
# run the same report (which is running a long time) to run for 
# individual organizations and statuses.
#
# BZIssue::4659
# BZIssue::4680 - Identify and fix CDR Reports affected by changes 
#                 to CTGov schema changes
#
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, cdrdb, sys, time, cdrdocobject
import xml.dom.minidom, ExcelWriter, ExcelReader

fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
orgId      = fields and fields.getvalue("orgid")          or None
orgName    = fields and fields.getvalue("orgname")        or None
protStatus = fields and fields.getvalue("protstatus")      or []
title      = u"CDR Administration"
instr      = u"Protocol Ownership Transfer Report"
script     = u"ProtOwnershipTransferOrg.py"
SUBMENU    = u"Report Menu"
buttons    = (SUBMENU, cdrcgi.MAINMENU)

header     = cdrcgi.header(title, title, instr, 
                          script, (u"Submit",
                                   SUBMENU,
                                   cdrcgi.MAINMENU),
                          numBreaks = 1,
                          stylesheet = u"""
       <STYLE type="text/css">
        .ilabel    { font-weight: bold; }
        label:hover { color: Navy;
                      text-decoration: none;
                      background: #FFFFCC; }
       </STYLE>
""")

if orgId:
    orgId = cdr.exNormalize(orgId)[1]
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

# If we have a single status we put it in a list
# ----------------------------------------------
if type(protStatus) == type(""):
    protStatus = [protStatus]

# Create the status condition for the SQL queries
if protStatus:
    status_query = "AND s.value in ('%s')" % \
                                   "', '".join([x for x in protStatus])
else:
    status_query = ""

# -------------------------------------------
# Getting the Protocol Grant information
# -------------------------------------------
def getGrantNo(id, docType, cursor):
    if docType == 'CTGovProtocol':
        protString = 'CTGovProtocol/PDQAdminInfo'
        nodeLoc    = 12

    else:
        protString = 'InScopeProtocol'
        nodeLoc    = 8

    query = """
        SELECT t.value, g.value
          FROM query_term g
          JOIN query_term t
            on t.doc_id = g.doc_id
           AND t.path = '/%s/FundingInfo' +
                         '/NIHGrantContract/NIHGrantContractType'
           AND left(g.node_loc, %d) = left(t.node_loc, %d)
         WHERE g.doc_id = %s
           AND g.path = '/%s/FundingInfo' +
                         '/NIHGrantContract/GrantContractNo'
               """ % (protString, nodeLoc, nodeLoc, id, protString)

    cursor.execute(query)

    rows = cursor.fetchall()
    grantNo = []
    for row in rows:
        grantNo.append(u'%s-%s' % (row[0], row[1]))

    grantNo.sort()

    return ", ".join(["%s" % g for g in grantNo])


# ---------------------------------------------------------------------
# This Protocol Owner Transfer report takes a long time because 
# several elements have to be displayed for which we need to identify
# the node location.  When a function has to be used within the query
# the indeces are not being used.
# ---------------------------------------------------------------------
class ProtocolOwnershipTransfer:
    def __init__(self, orgId, query, host = 'localhost'):
        #--------------------------------------------------------------
        # Set up a database connection and cursor.
        #--------------------------------------------------------------
        self.cdrId    = orgId
        self.q_status = query
        self.conn     = cdrdb.connect('CdrGuest')
        self.cursor   = self.conn.cursor()

    # -------------------------------------------------------------------
    # Transferred Protocols class to identify the elements requested
    # The information for blocked and CTGov blocked protocols is being
    # populated by calling a function for each protocol found.
    # -------------------------------------------------------------------
    class TransferredProtocols:
        def __init__(self, orgId, q_status, cursor):
            self.protocols = {}

            # This query selects those protocols that used to be 
            # InScopeProtocols and a new CTGovProtocol with a new CDR-ID was
            # created.
            # The current process replaces an InScopeProtocol by saving the
            # CTGovProtocol type on top of the InScope under the same CDR-ID
            # --------------------------------------------------------------
            #cursor.execute("""\
            #   SELECT t.doc_id, pid.value AS "Primary ID", n.value AS "NCT-ID",
            #          t.value AS "Owner Org", p.value AS "PRS User", 
            #          d.value AS "Tr Date", s.value AS "Status",
            #          oo.value AS "OrgName", o.int_val AS "Org-ID"
            #     INTO #tprotocols
            #     FROM query_term t
            #     JOIN query_term pid
            #       ON t.doc_id  = pid.doc_id
            #      AND pid.path  = '/InScopeProtocol/ProtocolIDs/PrimaryID' +
            #                      '/IDString'
            #     JOIN query_term n
            #       ON t.doc_id  = n.doc_id
            #      AND n.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
            #  -- JOIN query_term nct
            #  --   ON t.doc_id  = nct.doc_id
            #  --  AND nct.path  = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
            #  --  AND nct.value = 'ClinicalTrials.gov ID'
            #  --  AND left(n.node_loc, 8) = left(nct.node_loc, 8)
            #     JOIN query_term p
            #       ON t.doc_id  = p.doc_id
            #      AND p.path = '/InScopeProtocol/CTGovOwnershipTransferInfo' +
            #                   '/PRSUserName'
            #     JOIN query_term d
            #       ON t.doc_id  = d.doc_id
            #      AND d.path = '/InScopeProtocol/CTGovOwnershipTransferInfo' +
            #                   '/CTGovOwnershipTransferDate'
            #     JOIN query_term s
            #       ON t.doc_id  = s.doc_id
            #      AND s.path = '/InScopeProtocol/ProtocolAdminInfo'          +
            #                   '/CurrentProtocolStatus'
            #     JOIN query_term o
            #       ON t.doc_id = o.doc_id
            #      AND o.path = '/InScopeProtocol/ProtocolAdminInfo'          +
            #                   '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
            #      AND o.int_val = %s
            #     JOIN query_term oo
            #       ON oo.doc_id = o.int_val
            #      AND oo.path = '/Organization/OrganizationnameInformation'  +
            #                    '/OfficialName/Name'
            #    WHERE t.path = '/InScopeProtocol/CTGovOwnershipTransferInfo' +
            #                   '/CTGovOwnerOrganization'
            #    %s
            #    ORDER BY s.value""" % (orgId, q_status), timeout = 300)

            cursor.execute("""\
               SELECT t.doc_id, pid.value AS "Primary ID", n.value AS "NCT-ID",
                      t.value AS "Owner Org", p.value AS "PRS User", 
                      d.value AS "Tr Date", s.value AS "Status",
                      oo.value AS "OrgName", 
                      o.int_val AS "Org-ID", dt.name AS "DocType"
                 INTO #tprotocols
                 FROM query_term t
                 JOIN document doc
                   ON doc.id = t.doc_id
                 JOIN doc_type dt
                   ON doc.doc_type = dt.id
                 JOIN query_term pid
                   ON t.doc_id  = pid.doc_id
                  AND pid.path  = '/CTGovProtocol/PDQAdminInfo' +
                                  '/PDQProtocolIDs/PrimaryID/IDString'
                 JOIN query_term n
                   ON t.doc_id  = n.doc_id
                  AND n.path = '/CTGovProtocol/IDInfo/NCTID'
                 JOIN query_term p
                   ON t.doc_id  = p.doc_id
                  AND p.path    = '/CTGovProtocol/PDQAdminInfo' +
                                  '/CTGovOwnershipTransferInfo' +
                                  '/PRSUserName'
                 JOIN query_term d
                   ON t.doc_id  = d.doc_id
                  AND d.path    = '/CTGovProtocol/PDQAdminInfo' +
                                  '/CTGovOwnershipTransferInfo' +
                                  '/CTGovOwnershipTransferDate'
                 JOIN query_term s
                   ON t.doc_id  = s.doc_id
                  AND s.path    = '/CTGovProtocol/OverallStatus'
                 JOIN query_term o
                   ON t.doc_id  = o.doc_id
                  AND o.path    = '/CTGovProtocol/Location/Facility' +
                                  '/Name/@cdr:ref'
                  AND o.int_val = %s
                 JOIN query_term oo
                   ON oo.doc_id = o.int_val
                  AND oo.path   = '/Organization/OrganizationnameInformation' +
                                  '/OfficialName/Name'
                WHERE t.path    = '/CTGovProtocol/PDQAdminInfo' +
                                  '/CTGovOwnershipTransferInfo' +
                                  '/CTGovOwnerOrganization'
                  AND dt.name in ('CTGovProtocol', 'InScopeProtocol')
                --AND n.value like 'NCT%%'
                %s
                ORDER BY s.value, n.value""" % (orgId, q_status), timeout = 300)

            # This query is not necessary if we're only looking at 
            # CTGovProtocols but we need it if InScopeProtocols need to be
            # considered.  
            # I'm still waiting if we'll need to look at both doc types.
            # -------------------------------------------------------------
            cursor.execute("""\
                SELECT *
                  FROM #tprotocols
                 WHERE "NCT-ID" like 'NCT%'
                 ORDER BY doc_id""")

            rows = cursor.fetchall()

            # Assign all the elements to the protocols dictionary
            # ---------------------------------------------------
            for row in rows:
                cdrId = row[0]
                self.protocols[row[0]] = {u'pId' : row[1],
                                          u'nctId'  : row[2],
                                          u'trOrg'  : row[3],
                                          u'trUser'  : row[4],
                                          u'trDate'  : row[5],
                                          u'status'  : row[6],
                                          u'orgName' : row[7],
                                          u'orgId'   : row[8],
                                          u'docType' : row[9]}
                                          ### u'grantNo' : row[9]}

                self.protocols[row[0]][u'blocked']  = \
                                          self.checkBlocked(cdrId, cursor)
                self.protocols[row[0]][u'ctgovBlk'] = \
                                          self.checkCtgovBlocked(cdrId, 
                                                                 row[9], 
                                                                 cursor)
                self.protocols[row[0]][u'grantNo'] = \
                                          getGrantNo(cdrId, row[9], cursor)

        # --------------------------------------
        # Check if a protocol is blocked or not
        # --------------------------------------
        def checkBlocked(self, id, cursor):
            cursor.execute("""\
               SELECT *
                 FROM document
                WHERE id = %s
                  AND active_status = 'A' """ % id)
            row = cursor.fetchone()

            if row:  return 'No'
            return 'Yes'

        # -------------------------------------------------
        # Check if a protocol is blocked from CTGov or not
        # -------------------------------------------------
        def checkCtgovBlocked(self, id, docType, cursor):
            if docType == 'CTGovProtocol':
                return 'N/A'

            cursor.execute("""\
               SELECT *
                 FROM query_term
                WHERE doc_id = %s
                  AND path = '/InScopeProtocol/BlockedFromCTGov' """ % id)
            row = cursor.fetchone()

            if row: return 'Yes'
            return 'No'


    # -------------------------------------------------------------------
    # Not Transferred Protocols class to identify the elements requested
    # Only PUP information needs to get populated.  We're doing this by
    # sending the vendor filter output through a new filter extracting 
    # this information.
    # -------------------------------------------------------------------
    class NotTransferredProtocols:

        # ---------------------------------------------------------------
        # PUP class to identify the protocol update person information
        # If the personRole is specified as 'Protocol chair' the chair's
        # information is selected instead.
        # ---------------------------------------------------------------
        class PUP:
            def __init__(self, id, cursor, persRole = 'Update person'):
                self.cdrId       = id
                self.persId      = None
                self.persFname   = None
                self.persLname   = None
                self.persPhone   = None
                self.persEmail   = None
                self.persContact = None
                self.persRole    = persRole

                # Get the person name
                # -------------------
                cursor.execute("""\
                  SELECT q.doc_id, u.int_val, 
                         g.value as "FName", l.value as "LName", 
                         c.value as Contact  
                    FROM query_term_pub q
                    JOIN query_term_pub u
                      ON q.doc_id = u.doc_id
                     AND u.path   = '/InScopeProtocol/ProtocolAdminInfo' +
                                    '/ProtocolLeadOrg/LeadOrgPersonnel'  +
                                    '/Person/@cdr:ref'
                     AND left(q.node_loc, 12) = left(u.node_loc, 12)
                    JOIN query_term g
                      ON u.int_val = g.doc_id
                     AND g.path   = '/Person/PersonNameInformation/GivenName'
                    JOIN query_term l
                      ON g.doc_id = l.doc_id
                     AND l.path   = '/Person/PersonNameInformation/SurName'
                    JOIN query_term c
                      ON g.doc_id = c.doc_id
                     AND c.path   = '/Person/PersonLocations/CIPSContact'
                   WHERE q.doc_id = %s
                     AND q.value  = '%s'
                """ % (self.cdrId, self.persRole))

                rows = cursor.fetchall()

                for row in rows:
                    self.cdrId       = row[0]
                    self.persId      = row[1]
                    self.persFname   = row[2]
                    self.persLname   = row[3]
                    self.persContact = row[4]

                # Get the person's email and phone if a PUP was found
                # ---------------------------------------------------
                if self.persId:
                    cursor.execute("""\
                  SELECT q.doc_id, c.value, p.value, e.value
                    FROM query_term q
                    JOIN query_term c
                      ON c.doc_id = q.doc_id
                     AND c.path = '/Person/PersonLocations' +
                                  '/OtherPracticeLocation/@cdr:id'
         LEFT OUTER JOIN query_term p
                      ON c.doc_id = p.doc_id
                     AND p.path = '/Person/PersonLocations' +
                                  '/OtherPracticeLocation/SpecificPhone'
                     AND LEFT(c.node_loc, 8) = LEFT(p.node_loc, 8)
         LEFT OUTER JOIN query_term e
                      ON c.doc_id = e.doc_id
                     AND e.path = '/Person/PersonLocations' +
                                  '/OtherPracticeLocation/SpecificEmail'
                     AND LEFT(c.node_loc, 8) = LEFT(e.node_loc, 8)
                   WHERE q.path = '/Person/PersonLocations/CIPSContact'
                     AND q.value = c.value
                     AND q.doc_id = %s
                    """ % self.persId)

                    rows = cursor.fetchall()

                    for row in rows:
                        self.persPhone   = row[2]
                        self.persEmail   = row[3]


        # -----------------------------------------------------
        # Create the dictionary holding all protocols with the 
        # information to display on the spreadsheet.
        # -----------------------------------------------------
        def __init__(self, orgId, q_status, cursor):
            self.protocols = {}

            cursor.execute("""\
                SELECT s.doc_id, pid.value AS "Primary ID", n.value AS "NCT-ID",
                       r.value as "TResponse", d.value as "TR date", 
                       t.value as "Log date",
                       s.value AS "Status",  sd.value AS "Status Date",
                       oo.value AS "OrgName", o.int_val AS "OrgId", 
                       dt.name AS "DocType"
                  INTO #ntprotocols
                  FROM query_term_pub s
                  JOIN document doc
                    ON doc.id = s.doc_id
                  JOIN doc_type dt
                    ON doc.doc_type = dt.id
                  JOIN query_term_pub pid
                    ON s.doc_id  = pid.doc_id
                   AND pid.path  = '/InScopeProtocol/ProtocolIDs/PrimaryID' +
                                   '/IDString'
                  JOIN query_term_pub n
                    ON s.doc_id  = n.doc_id
                   AND n.path    = '/InScopeProtocol/ProtocolIDs/OtherID'   +
                                   '/IDString'
               -- JOIN query_term nct
               --   ON s.doc_id  = nct.doc_id
               --  AND nct.path  = '/InScopeProtocol/ProtocolIDs/OtherID'   +
               --                  '/IDType'
               --  AND nct.value = 'ClinicalTrials.gov ID'
               --  AND left(n.node_loc, 8) = left(nct.node_loc, 8)
                  JOIN query_term_pub sd
                    ON s.doc_id  = sd.doc_id
                   AND sd.path   = '/InScopeProtocol/ProtocolAdminInfo'     +
                                   '/ProtocolLeadOrg/LeadOrgProtocolStatuses' +
                                   '/CurrentOrgStatus/StatusDate'
                  JOIN query_term sp
                    ON s.doc_id  = sp.doc_id
                   AND sp.path   = '/InScopeProtocol/ProtocolAdminInfo'      +
                                   '/ProtocolLeadOrg/LeadOrgRole'
                   AND sp.value  = 'Primary'
                   AND left(sp.node_loc, 8) = left(sd.node_loc, 8)
                  JOIN query_term o
                    ON s.doc_id = o.doc_id
                   AND o.path = '/InScopeProtocol/ProtocolAdminInfo'          +
                                '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
                   AND o.int_val = %s
                  JOIN query_term oo
                    ON oo.doc_id = o.int_val
                   AND oo.path = '/Organization/OrganizationnameInformation'  +
                                 '/OfficialName/Name'
       LEFT OUTER JOIN query_term d
                    ON s.doc_id  = d.doc_id
                   AND d.path    = '/InScopeProtocol'                        +
                                   '/CTGovOwnershipTransferInfo'             +
                                   '/CTGovOwnershipTransferDate'
       LEFT OUTER JOIN query_term r
                    ON s.doc_id  = r.doc_id
                   AND r.path    = '/InScopeProtocol'                        + 
                                   '/CTGovOwnershipTransferContactLog'       + 
                                   '/CTGovOwnershipTransferContactResponse'
       LEFT OUTER JOIN query_term t
                    ON s.doc_id  = t.doc_id
                   AND t.path    = '/InScopeProtocol'                        +
                                   '/CTGovOwnershipTransferContactLog'       + 
                                   '/Date'
                 WHERE s.path    = '/InScopeProtocol/ProtocolAdminInfo'      +
                                   '/CurrentProtocolStatus'
                   AND d.value is null
                   %s
                 ORDER BY s.value
            """ % (orgId, q_status), timeout = 300)

            cursor.execute("""\
                SELECT *
                  FROM #ntprotocols
                 WHERE "NCT-ID" like 'NCT%'
                 ORDER BY 'Status'""")

            rows = cursor.fetchall()

            for row in rows:
                cdrId = row[0]
                self.protocols[cdrId] = {u'pId'      : row[1],
                                         u'nctId'    : row[2],
                                         u'tResponse': row[3],
                                         u'trDate'   : row[4],
                                         u'logDate'  : row[5],
                                         u'status'   : row[6],
                                         u'statDate' : row[7]} #
                                         #u'grantNo'  : row[10]} #,
                                         #u'orgName'  : row[8],
                                         #u'orgId'    : row[9]}

                # Populate the Orgname
                # --------------------
                self.protocols[cdrId][u'orgName'] = \
                                      self.getOrgName(cdrId, cursor)

                # Populate the PUP information
                pup = self.PUP(cdrId, cursor)
                if pup.persId:
                    self.protocols[cdrId][u'pup'] = pup 
                else:
                    pup = self.PUP(cdrId, cursor, 'Protocol chair')
                    self.protocols[cdrId][u'pup'] = pup
                    
                # Populate the Source information
                # -------------------------------
                self.protocols[cdrId][u'protSource'] = \
                                      self.getSource(cdrId, cursor)

                # Populate the GrantNo information
                # --------------------------------
                self.protocols[cdrId][u'grantNo'] = \
                                      getGrantNo(cdrId, row[8], cursor)

        # ---------------------------------------
        # Getting the official organization name
        # ---------------------------------------
        def getOrgName(self, id, cursor):
            cursor.execute("""\
                SELECT ln.value
                  FROM query_term lo
                  JOIN query_term ln
                    ON lo.int_val = ln.doc_id
                   AND ln.path = '/Organization/OrganizationNameInformation' +
                                 '/OfficialName/Name'
                  JOIN query_term sp
                    ON lo.doc_id = sp.doc_id
                   AND sp.path = '/InScopeProtocol/ProtocolAdminInfo' +
                                 '/ProtocolLeadOrg/LeadOrgRole'
                   AND sp.value = 'Primary'
                   AND left(sp.node_loc, 8) = left(lo.node_loc, 8)
                 WHERE lo.doc_id = %s
                   AND lo.path = '/InScopeProtocol/ProtocolAdminInfo' +
                                 '/ProtocolLeadOrg/LeadOrganizationId/@cdr:ref'
            """ % id)
            row = cursor.fetchone()

            return row[0]


        # -------------------------------------------
        # Getting the Protocol SourceName information
        # -------------------------------------------
        def getSource(self, id, cursor):
            cursor.execute("""\
                SELECT value 
                  FROM query_term 
                 WHERE doc_id = %s
                   AND path = '/InScopeProtocol/ProtocolSources' +
                              '/ProtocolSource/SourceName'
            """ % id)
            rows = cursor.fetchall()
            sourceNames = []
            for row in rows:
                sourceNames.append(row[0])

            sourceNames.sort()

            return ", ".join(["%s" % s for s in sourceNames])


    # We need to display the rows in a specific order based on
    # the protocol status.  Identify the order in which the 
    # protocol ids need to be listed.
    # --------------------------------------------------------
    def sortIdByStatus(self, Prot):
        statusList = {}
        for row in Prot.protocols:
            statusList[row] = Prot.protocols[row][u'status'] 

        statusSort = []
        for a, b in sorted(statusList.iteritems(), key=lambda (k,v):(v,k)):
            statusSort.append(a)
        return statusSort


    # ----------------------------------------------------------------
    # Creating a spreadsheet for displaying the protocols transferred
    # and not yet transferred to CT.gov
    # ----------------------------------------------------------------
    def createTransferSpreadsheet(self, orgName):

        now = time.localtime()
        startDate = list(now)
        endDate   = list(now)

        # Transferred Protocols
        tps  = self.TransferredProtocols(self.cdrId, self.q_status, 
                                                     self.cursor)

        # Not Transferred Protocols
        ntps = self.NotTransferredProtocols(self.cdrId, self.q_status, 
                                                        self.cursor)

        # Create the spreadsheet and define default style, etc.
        # -----------------------------------------------------
        wsTitle = {u'tr':u'Transferred',
                   u'ntr':u'Not Transferred'}
        wb      = ExcelWriter.Workbook()
        b       = ExcelWriter.Border()
        borders = ExcelWriter.Borders(b, b, b, b)
        font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
        align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
        alignS  = ExcelWriter.Alignment('Left', 'Top', wrap = False)
        style1  = wb.addStyle(alignment = align, font = font)
        urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
        style4  = wb.addStyle(alignment = align, font = urlFont)
        style2  = wb.addStyle(alignment = align, font = font, 
                                 numFormat = 'YYYY-mm-dd')
        alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
        alignT  = ExcelWriter.Alignment('Left', 'Bottom', wrap = False)
        headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                    size = 12)
        titleFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                    size = 14)
        boldFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', 
                                                                    size = 11)
        styleH  = wb.addStyle(alignment = alignH, font = headFont)
        styleT  = wb.addStyle(alignment = alignT, font = titleFont)
        style1b = wb.addStyle(alignment = align,  font = boldFont)
        styleS  = wb.addStyle(alignment = alignS, font = boldFont)
            
        for key in wsTitle.keys():
            ws      = wb.addWorksheet(wsTitle[key], style1, 45, 1)
            
            # CIAT wants a title row
            # ----------------------------------------------------------
            titleTime = time.strftime("%Y-%m-%d %H:%M:%S")
            rowNum = 1
            exRow = ws.addRow(rowNum, styleT)
            exRow.addCell(1,  'Org Name: %s' % orgName)

            rowNum = 2
            exRow = ws.addRow(rowNum, styleS)
            exRow.addCell(1,  'Report created: %s' % titleTime)

            # Set the column width
            # --------------------
            if key == 'ntr':
                ws.addCol( 1,  60)
                ws.addCol( 2,  90)
                ws.addCol( 3,  80)
                ws.addCol( 4, 100)
                ws.addCol( 5,  60)
                ws.addCol( 6,  60)
                ws.addCol( 7,  60)
                ws.addCol( 8,  60)
                ws.addCol( 9, 120)
                ws.addCol(10,  90)
                ws.addCol(11,  90)
                ws.addCol(12, 140)
                ws.addCol(13,  60)
            else:
                ws.addCol( 1,  60)
                ws.addCol( 2,  90)
                ws.addCol( 3,  80)
                ws.addCol( 4,  90)
                ws.addCol( 5,  70)
                ws.addCol( 6,  70)
                ws.addCol( 7,  60)
                ws.addCol( 8,  60)
                ws.addCol( 9,  90)
                ws.addCol(10,  90)
                ws.addCol(11,  60)
                ws.addCol(13,  60)

            # Create the Header row
            # ---------------------
            rowNum = 3
            if key == 'ntr':
                exRow = ws.addRow(rowNum, styleH)
                exRow.addCell(1,  'CDR-ID')
                exRow.addCell(2,  'Primary ID')
                exRow.addCell(3,  'NCT-ID')
                exRow.addCell(4,  'Source')
                exRow.addCell(5,  'Transfer Response')
                exRow.addCell(6,  'Date')
                exRow.addCell(7,  'Protocol Status')
                exRow.addCell(8,  'Status Date')
                exRow.addCell(9,  'Primary Lead Org Name')
                exRow.addCell(10, 'PUP')
                exRow.addCell(11, 'Phone')
                exRow.addCell(12, 'Email')
                exRow.addCell(13, 'GrantNo')
            else:
                exRow = ws.addRow(rowNum, styleH)
                exRow.addCell( 1, 'CDR-ID')
                exRow.addCell( 2, 'Primary ID')
                exRow.addCell( 3, 'NCT-ID')
                exRow.addCell( 4, 'CTGov Owner Organization')
                exRow.addCell( 5, 'PRS User Name')
                exRow.addCell( 6, 'CTGov Ownership Transfer Date')
                exRow.addCell( 7, 'Blocked From Publication')
                exRow.addCell( 8, 'Blocked From CTGov')
                exRow.addCell( 9, 'Current Protocol Status')
                exRow.addCell(10, 'Organization Name')
                exRow.addCell(11, 'Org CDR-ID')
                exRow.addCell(12, 'GrantNo')


            # Add the protocol data one record at a time beginning after 
            # the header row
            # ----------------------------------------------------------
            if key == 'ntr':
                Prot = ntps
            else:
                Prot = tps

            statCount = statTotal = 0
            if key == 'ntr':
                statusSort = self.sortIdByStatus(Prot)

                lastStatus = ''
                for row in statusSort:
                    if lastStatus != Prot.protocols[row][u'status']:
                        if lastStatus != '':
                            rowNum += 1
                            exRow = ws.addRow(rowNum, style1b)
                            exRow.addCell(1, 'Count: %d' % statCount)
                            rowNum += 1
                            statCount = 0
                        lastStatus = Prot.protocols[row][u'status']

                    rowNum += 1
                    exRow = ws.addRow(rowNum, style1, 40)
                    exRow.addCell(1, row)
                    exRow.addCell(2, Prot.protocols[row][u'pId'])
                    exRow.addCell(3, Prot.protocols[row][u'nctId'])

                    if Prot.protocols[row].has_key('protSource'):
                        exRow.addCell(4, Prot.protocols[row][u'protSource'])

                    if Prot.protocols[row].has_key('tResponse'):
                        exRow.addCell(5, Prot.protocols[row][u'tResponse'])

                    if Prot.protocols[row].has_key('logDate'):
                        exRow.addCell(6, Prot.protocols[row][u'logDate'])


                    # We are supposed to count the rows by status
                    # -------------------------------------------
                    statCount += 1
                    statTotal += 1
                    exRow.addCell(7, Prot.protocols[row][u'status'])

                    if Prot.protocols[row].has_key('statDate'):
                        exRow.addCell(8, Prot.protocols[row][u'statDate'])

                        exRow.addCell(9, Prot.protocols[row][u'orgName'])
                    if Prot.protocols[row].has_key('pup'):
                        if Prot.protocols[row][u'pup'].persFname and \
                           Prot.protocols[row][u'pup'].persLname:
                            exRow.addCell(10, 
                                 Prot.protocols[row][u'pup'].persFname + \
                                  " " + Prot.protocols[row][u'pup'].persLname)

                        exRow.addCell(11, Prot.protocols[row][u'pup'].persPhone)
                        exRow.addCell(12, Prot.protocols[row][u'pup'].persEmail)
                    if Prot.protocols[row].has_key('grantNo'):
                        exRow.addCell(13, Prot.protocols[row][u'grantNo'])
                rowNum += 1
                exRow = ws.addRow(rowNum, style1b)
                exRow.addCell(1, 'Count: %d' % statCount)
                rowNum += 1
                exRow = ws.addRow(rowNum, style1b)
                exRow.addCell(1, 'Total: %d' % statTotal)
            else:
                statusSort = self.sortIdByStatus(Prot)

                lastStatus = ''
                for row in statusSort:
                    if lastStatus != Prot.protocols[row][u'status']:
                        if lastStatus != '':
                            rowNum += 1
                            exRow = ws.addRow(rowNum, style1b)
                            exRow.addCell(1, 'Count: %d' % statCount)
                            rowNum += 1
                            statCount = 0
                        lastStatus = Prot.protocols[row][u'status']

                    rowNum += 1
                    exRow = ws.addRow(rowNum, style1, 40)
                    exRow.addCell(1, row)
                    exRow.addCell(2, Prot.protocols[row][u'pId'])
                    exRow.addCell(3, Prot.protocols[row][u'nctId'])

                    if Prot.protocols[row].has_key('trOrg'):
                        exRow.addCell(4, Prot.protocols[row][u'trOrg'])
                        
                    if Prot.protocols[row].has_key('trUser'):
                        exRow.addCell(5, Prot.protocols[row][u'trUser'])

                    if Prot.protocols[row].has_key('trDate'):
                        exRow.addCell(6, Prot.protocols[row][u'trDate'])

                    if Prot.protocols[row].has_key('blocked'):
                        exRow.addCell(7, Prot.protocols[row][u'blocked'])

                    if Prot.protocols[row].has_key('ctgovBlk'):
                        exRow.addCell(8, Prot.protocols[row][u'ctgovBlk'])

                    # We are supposed to count the rows by status
                    # -------------------------------------------
                    statCount += 1
                    statTotal += 1
                    exRow.addCell(9, Prot.protocols[row][u'status'])

                    if exRow.addCell(10, Prot.protocols[row][u'orgName']):
                        exRow.addCell(10, Prot.protocols[row][u'orgName'])

                    if exRow.addCell(11, Prot.protocols[row][u'orgId']):
                        exRow.addCell(11, Prot.protocols[row][u'orgId'])

                    if exRow.addCell(12, Prot.protocols[row][u'grantNo']):
                        exRow.addCell(12, Prot.protocols[row][u'grantNo'])

                rowNum += 1
                exRow = ws.addRow(rowNum, style1b)
                exRow.addCell(1, 'Count: %d' % statCount)
                rowNum += 1
                exRow = ws.addRow(rowNum, style1b)
                exRow.addCell(1, 'Total: %d' % statTotal)

        t = time.strftime("%Y%m%d%H%M%S")                                               
        # Save the report.
        # ----------------
        name = "/ProtocolOwnershipTransferReport-%s.xls" % t
        f = open(REPORTS_BASE + name, 'wb')
        wb.write(f, True)
        f.close()

        print "Content-type: application/vnd.ms-excel"
        print "Content-Disposition: attachment; filename=%s" % name
        print
        wb.write(sys.stdout, True)


 
# ---------------------------------------------------------------------
# Module to select all protocol status values to provide a drop-down
# list on the input form.
# ---------------------------------------------------------------------
def getProtStatusValues():
    statusValues = []
    try:
        conn = cdrdb.connect('CdrGuest')
        cursor = conn.cursor()
        cursor.execute("""\
            SELECT DISTINCT value 
              FROM query_term_pub 
             WHERE path = '/InScopeProtocol/ProtocolAdminInfo/' +
                          'CurrentProtocolStatus' 
             ORDER BY value
""")
        rows = cursor.fetchall()
    except Exception, info:
        cdrcgi.bail(u"Database failure getting protocol statuses: %s" %
                    str(info))
    for row in rows:
        statusValues.append(row)

    return statusValues


#----------------------------------------------------------------------
# More than one matching title; let the user choose one.
#----------------------------------------------------------------------
def showTitleChoices(choices):
    form = u"""\
   <H3>More than one matching document found; please choose one.</H3>
"""
    for choice in choices:
        form += u"""\
   <INPUT TYPE='radio' NAME='orgid' id='%s' VALUE='CDR%010d'>
   <label for='%s'>[CDR%08d] %s</label><br>
""" % (choice[0], choice[0], choice[0], choice[0], cgi.escape(choice[1]))

    footer = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + footer)


# ----------------------------------------------------------------------
# Handle navigation requests
# ----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])


statusList = getProtStatusValues()
    
#----------------------------------------------------------------------
# Put up the main request form.
#----------------------------------------------------------------------
if not orgId and not orgName:
    form     = u"""\
       <input type='hidden' name='%s' value='%s'>

       <fieldset>
        <legend>&nbsp;Select Protocol Organization / Status&nbsp;</legend>
        <table>
         <tr>
          <td>
           <label class='ilabel' for='orgId'>CDR-ID</label>
          </td>
          <td>
           <input name='orgid' id='orgId'>
          </td>
         </tr>
         <tr>
          <td>
           <label class='ilabel' for='orgName'>Organization</label>
          </td>
          <td>
           <input name='orgname' id='orgName'>
          </td>
         </tr>
         <tr>
          <td>
           <label class='ilabel' for='stat'>Prot Status</label>
          </td>
          <td>
           <select name='protstatus' id='stat' size='5' MULTIPLE>
            <option value="" SELECTED>All</option>
    """ % (cdrcgi.SESSION, session and session or u'')

    for statusValue in statusList:
        form += """\
            <option>%s</option>
    """ % statusValue[0]

    form     += u"""\
           </select>
          </td>
         </tr>
        </table>
       </fieldset>
      </form>
     </body>
    </html>
    """
    cdrcgi.sendPage(header + form)




#----------------------------------------------------------------------
# If we have an org name but not a document ID, find the ID.
#----------------------------------------------------------------------
if not orgId and orgName:
    lookingFor = 'org title'
    try:
        cursor.execute("""\
            SELECT d.id, d.title
              FROM document d
              JOIN doc_type dt
                ON dt.id = d.doc_type
               AND name = 'ORGANIZATION'
             WHERE title LIKE ?""", orgName + '%')
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to find document with %s '%s'" % (lookingFor,
                                                                  orgName))
        if len(rows) > 1:
            showTitleChoices(rows)
        orgId = rows[0][0]
        docId = "CDR%010d" % orgId
    except cdrdb.Error, info:
        cdrcgi.bail('Failure looking up document %s: %s' % (lookingFor,
                                                            info[1][0]))
#----------------------------------------------------------------------
# We have a document ID.  Check added at William's request.
#----------------------------------------------------------------------
elif orgId:
    cursor.execute(u"""\
        SELECT t.name
          FROM doc_type t
          JOIN document d
            ON d.doc_type = t.id
         WHERE d.id = ?""", orgId)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("CDR%d not found" % orgId)
    elif rows[0][0].upper() != 'ORGANIZATION':
        cdrcgi.bail("CDR%d has document type %s" % (orgId, rows[0][0]))
else:
    cdrcgi.bail('Unable to complete request without OrgName or CDR-ID')



t = time.strftime('%Y%m%d%H%M%S')
REPORTS_BASE = u'd:/cdr/reports'

# Output file name
# ----------------
name = u'/ProtTransferOfOwnershipByOrg-%s.xml' % t
fullname = REPORTS_BASE + name

# ----------------------------------------------------------------------
# Run the report and create the spreadsheet
# ----------------------------------------------------------------------
report      = ProtocolOwnershipTransfer(orgId, status_query)

# Select the organization name to be displayed as a title on the output
# ---------------------------------------------------------------------
cursor.execute(u"""\
    SELECT value 
      FROM query_term
     WHERE doc_id = ?
       AND path = '/Organization/OrganizationNameInformation' +
                  '/OfficialName/Name'""", orgId)
row = cursor.fetchall()
report.createTransferSpreadsheet(row[0][0])

# Save the Report
# ---------------
# fobj = file(fullname, "w")
# wb.write(fobj)
# print ""
# print "  Report written to %s" % fullname
# fobj.close()
