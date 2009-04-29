#----------------------------------------------------------------------
#
# $Id: Request4551.py,v 1.1 2009-04-29 00:12:46 venglisc Exp $
#
# Update Non-Compliance Report from CTGov.
#
# $Log: not supported by cvs2svn $
#
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, time, cdrdocobject #, cdrcgi, 
import xml.dom.minidom, ExcelWriter, ExcelReader

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
#conn.setAutoCommit()
cursor = conn.cursor()

# -------------------------------------------------------------------
# Protocol class to identify the elements requested
# -------------------------------------------------------------------
class Protocol:
    def __init__(self, nctInfo, cursor):
        self.cdrId     = nctInfo[u'CDRID']
        self.closed    = nctInfo[u'Compl before?']
        self.complDate = nctInfo[u'Compl Date']
        self.completed = None
        self.respp     = None
        self.fdaReg    = u'No'
        self.safety    = u'No'
        self.arms      = u'No'
        self.usSites   = None
        self.phase     = []
        self.status    = None
        self.source    = []
        self.primaryId = None

        # Extract the XML document and create the DOM tree
        # ------------------------------------------------
        cursor.execute("""\
            SELECT xml
              FROM pub_proc_cg
             WHERE id = ? """, (self.cdrId))
        try:
            docXml = cursor.fetchall()[0][0]
        except:
            print 'No document in CG table for CDR%s' % self.cdrId
            docXml = None
            return
            

        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))

        # Setting initial variables
        # -------------------------
        multiArms = 0
        singleArm = None
        safety = allSafety = None
        ynFda  = None
        respp = []

        # Walking through the tree to find the elements available in the 
        # licensee output
        # --------------------------------------------------------------
        for node in dom.documentElement.childNodes:
            # Find the value of the Protocol ID
            # ---------------------------------
            if node.nodeName == 'ProtocolIDs':
                for child in node.childNodes:
                    if child.nodeName == 'PrimaryID':
                        self.primaryId = getElementText(child, 'IDString')
            # Identify if the FDARegulated element exists and is not empty
            # ------------------------------------------------------------
            elif node.nodeName == 'RegulatoryInformation':
                ynFda = getElementText(node, 'FDARegulated')

                # Identify if Responsible Party exists with children
                # --------------------------------------------------
                for child in node.childNodes:
                    if child.nodeName == 'ResponsibleParty':
                        for nextChild in child.childNodes:
                            if nextChild.nodeName in ('ResponsiblePerson',
                                                    'ResponsibleOrganization'):
                                for next2Child in nextChild.childNodes:
                                    respp.append(cdr.getTextContent(next2Child))
            elif node.nodeName == 'ProtocolAbstract':
                for child in node.childNodes:
                    if child.nodeName == 'Professional':
                        for nextChild in child.childNodes:
                            # Identify if an empty ArmsOrGroups element exists
                            # with the SingleArm attribute or none-empty
                            # ArmOrGroup elements exist.
                            # ------------------------------------------------
                            if nextChild.nodeName == 'ArmsOrGroups':
                                singleArm = nextChild.getAttribute(
                                              'SingleArmOrGroupStudy')
                                for next2Child in nextChild.childNodes:
                                    if next2Child.nodeName == 'ArmOrGroup':
                                        multiArms += 1
                            # Identify that all Outcome elements exist with 
                            # the Saftey attribute
                            # ---------------------------------------------
                            elif nextChild.nodeName == 'Outcome':
                                safety = nextChild.getAttribute(
                                            'Safety') or None
                                if not safety and not allSafety:
                                    allSafety = u'No'

            # Extract the ProtocolPhase elements
            # ----------------------------------
            elif node.nodeName == 'ProtocolPhase':
                self.phase.append(cdr.getTextContent(node))
            # Extract the protocol status
            # ---------------------------
            elif node.nodeName == 'ProtocolAdminInfo':
                self.status = getElementText(node, 'CurrentProtocolStatus')
                country = []
                for child in node.childNodes:
                    if child.nodeName == 'ProtocolSites':
                        country = dom.documentElement.getElementsByTagName(
                                                               'CountryName')

        isUsTrial = None
        for node in country:
            # print node.nodeName, cdr.getTextContent(node)
            if cdr.getTextContent(node) == 'U.S.A.':
                isUsTrial = 'Yes'
                break



        # Setting the ResponsibleParty Y/N flag
        # -------------------------------------
        self.completed = None
        if len(respp):
           self.respp     = u'Yes'
        else:
           self.respp     = u'No'
        nctInfo[u'respp'] = self.respp
        
        # Setting the FDA Regulated Y/N flag
        # ----------------------------------
        if ynFda:
            self.fdaReg = u'Yes'
        nctInfo[u'fdaReg'] = self.fdaReg

        # Setting the Outcome with Saftey Y/N flag
        # ----------------------------------------
        if allSafety:
            self.safety = u'No'
        else:
            self.safety = u'Yes'
        nctInfo[u'safety'] = self.safety

        # Setting the ArmsOrGroups Y/N flag
        # ---------------------------------
        if singleArm or multiArms > 0:
            self.arms  = u'Yes'
        nctInfo[u'arms'] = self.arms

        if isUsTrial:
            nctInfo[u'us'] = u'Yes'

        # Setting the phase and status
        # ----------------------------
        nctInfo[u'phase'] = self.phase
        nctInfo[u'status'] = self.status

        # Extracting the source name from the database since this information
        # is not part of the vendor output
        # -------------------------------------------------------------------
        cursor.execute("""\
            SELECT value 
              FROM query_term_pub
             WHERE PATH = '/InScopeProtocol/ProtocolSources' +
                          '/ProtocolSource/SourceName'
               AND doc_id = ? """, (self.cdrId))
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                self.source.append(row[0])
        nctInfo[u'source'] = self.source

        # Setting the protocol ID
        # -----------------------
        nctInfo[u'pid'] = self.primaryId



def getElementText(parent, name):
    nodes = parent.getElementsByTagName(name)
    return nodes and cdr.getTextContent(nodes[0]) or None


# -------------------------------------------------------------
# Read the DCP protocol file (stored in CSV format)
# -------------------------------------------------------------
def readProtocols(filename = 'd:/cdr/tmp/CTGov_Protocols.xls'):
    book = ExcelReader.Workbook(filename)
    sheet = book[0]
    headerRow = 1
    rownum = 0
    ctGovProtocols = {}
    for row in sheet.rows:
        nctId      = row[0]
        cdrId      = row[1]
        earlyCompl = row[2]
        complDate  = row[3]
        ctGovProtocols[nctId.val] = {u'CDRID':str(cdrId),
                                     u'Compl before?':earlyCompl.val,
                                     u'Compl Date':str(complDate)}
    return ctGovProtocols


# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
quickTitle = "CTGov None-Compliance Report"
t = time.strftime("%Y%m%d%H%M%S")
REPORTS_BASE = 'd:/cdr/tmp'
REPORTS_BASE = 'm:/cdr/tmp'
name = '/CTGovNoneCompliance.xml'
ctGovName = '/test_X.xls'
ctGovName = '/test_R4551.xls'
fullname = REPORTS_BASE + name

# ----------------------------------------------------------------------
# First Step:
# We need to read the content of the Spreadsheet provided
# ----------------------------------------------------------------------
ctGovProtocols = readProtocols(filename = REPORTS_BASE + ctGovName)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

for docs in ctGovProtocols.keys():
    if ctGovProtocols[docs][u'CDRID'] not in ('CDR ID', 'None'):
        Protocol(ctGovProtocols[docs], cursor)

#print ' ========================'
#print "*** After ***"
#print ctGovProtocols[u'NCT00020436']
#print ''
#print ctGovProtocols[u'NCT00003325']
#print ''
#print ctGovProtocols[u'NCT00066365']
print 'Records processed: %s' % len(ctGovProtocols)

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
wb      = ExcelWriter.Workbook()
b       = ExcelWriter.Border()
borders = ExcelWriter.Borders(b, b, b, b)
font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style1  = wb.addStyle(alignment = align, font = font)
# style1  = wb.addStyle(alignment = align, font = font, borders = borders)
urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
style4  = wb.addStyle(alignment = align, font = urlFont)
ws      = wb.addWorksheet(quickTitle, style1, 45, 1)
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', size = 12)
styleH  = wb.addStyle(alignment = alignH, font = headFont)
    
# Set the colum width
# -------------------
ws.addCol( 1,  90)
ws.addCol( 2,  55)
ws.addCol( 3,  90)
ws.addCol( 4,  80)
ws.addCol( 5,  80)
ws.addCol( 6,  60)
ws.addCol( 7,  60)
ws.addCol( 8,  60)
ws.addCol( 9,  60)
ws.addCol(10,  60)
ws.addCol(11,  60)
ws.addCol(12,  65)
ws.addCol(13,  75)
ws.addCol(14, 150)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, styleH)
exRow.addCell(1, 'NCT-ID')
exRow.addCell(2, 'CDR-ID')
exRow.addCell(3, 'Closed Before 2007-09-27?')
exRow.addCell(4, 'Completion Date')
exRow.addCell(5, 'Completion Date [Y/N]')
exRow.addCell(6, 'RP [Y/N]')
exRow.addCell(7, 'FDA Reg [Y/N]')
exRow.addCell(8, 'Outcomes w/ Safety [Y/N]')
exRow.addCell(9, 'Arms [Y/N]')
exRow.addCell(10, 'US Sites [Y/N]')
exRow.addCell(11, 'Phase')
exRow.addCell(12, 'Protocol Status')
exRow.addCell(13, 'Source')
exRow.addCell(14, 'Primary ID')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in ctGovProtocols.keys():
    if ctGovProtocols[row][u'CDRID'] != 'CDR ID':
        rowNum += 1
        exRow = ws.addRow(rowNum, style1, 40)
        exRow.addCell(1, row)
        exRow.addCell(2, ctGovProtocols[row][u'CDRID'])
        exRow.addCell(3, ctGovProtocols[row][u'Compl before?'])
        exRow.addCell(4, ctGovProtocols[row][u'Compl Date'])
        exRow.addCell(5, None)

        if ctGovProtocols[row].has_key(u'respp'):
            exRow.addCell(6, ctGovProtocols[row][u'respp'])

        if ctGovProtocols[row].has_key(u'fdaReg'):
            exRow.addCell(7, ctGovProtocols[row][u'fdaReg'])

        if ctGovProtocols[row].has_key(u'safety'):
            exRow.addCell(8, ctGovProtocols[row][u'safety'])

        if ctGovProtocols[row].has_key(u'arms'):
            exRow.addCell(9, ctGovProtocols[row][u'arms'])

        if ctGovProtocols[row].has_key(u'us'):
            exRow.addCell(10, ctGovProtocols[row][u'us'])

        if ctGovProtocols[row].has_key(u'phase'):
            cellPhase = ctGovProtocols[row][u'phase']
            cellPhase.sort()
            cellPhase.reverse()
            exRow.addCell(11, cellPhase[0])

        if ctGovProtocols[row].has_key(u'status'):
            exRow.addCell(12, ctGovProtocols[row][u'status'])
            exRow.addCell(13, " ,".join(
                                 [x for x in ctGovProtocols[row][u'source']]))

        if ctGovProtocols[row].has_key(u'pid'):
            exRow.addCell(14, ctGovProtocols[row][u'pid'])

t = time.strftime("%Y%m%d%H%M%S")                                               

# # Web report
# # ----------
# print "Content-type: application/vnd.ms-excel"
# print "Content-Disposition: attachment; filename=ContentInventory-%s.xls" % t
# print  
# 
# wb.write(sys.stdout, True)

# Save the Report
# ---------------
fobj = file(fullname, "w")
wb.write(fobj)
print ""
print "  Report written to %s" % fullname
fobj.close()

