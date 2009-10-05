#----------------------------------------------------------------------
#
# $Id: CTGov_Compliance_PUP.py,v 1.2 2009-09-25 16:18:56 venglisc Exp $
#
# Update Non-Compliance Report from CTGov to add PUP information.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2009/05/04 21:13:42  venglisc
# Initial copy of program to read a spreadsheet with protocol information
# and populate the PUP information of the primary LeadOrg for the listed
# protocols. (Bug 4566)
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, time, cdrdocobject #, cdrcgi, 
import xml.dom.minidom, ExcelWriter, ExcelReader

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

#conn = cdrdb.connect('CdrGuest')
#conn.setAutoCommit()
#cursor = conn.cursor()

# -------------------------------------------------------------------
# Protocol class to identify the elements requested
# Only PUP information needs to get populated.  We're doing this by
# sending the vendor filter output through a new filter extracting 
# this information.
# -------------------------------------------------------------------
class Protocol:
    def __init__(self, nctInfo, cursor):
        self.cdrId     = nctInfo[u'CDRID']
        self.pID       = nctInfo[u'pid']
        self.source    = nctInfo[u'source']
        self.status    = nctInfo[u'status']
        self.closeDate = nctInfo[u'closeDate']
        self.complDate = nctInfo[u'complDate']
        self.respParty = nctInfo[u'respParty']
        self.fda       = nctInfo[u'fda']
        self.phase     = nctInfo[u'phase']
        self.pupName   = []
        self.pupPhone  = []
        self.pupEmail  = []
        self.vMailerResp = []
        self.vMailerChange = []

        #----------------------------------------------------------------------
        # Filter the document.
        # Run the cdr.filterDoc() to extract just the PUP information for the 
        # primary LeadOrg.
        #----------------------------------------------------------------------
        filterWarning = ""
        filterSet     = ['set:Mailer InScopeProtocol Set',
                         'name:Protocol Report Post Process']
        doc = cdr.filterDoc('guest', filterSet, docId = self.cdrId, 
                            docVer = 'lastp')
        if type(doc) == type(()):
            if doc[1]: filterWarning += doc[1]
            doc = doc[0]

        try:
            docXml = doc
        except:
            print 'No document in CG table for CDR%s' % self.cdrId
            docXml = None
            return
            
        dom = xml.dom.minidom.parseString(docXml)

        # Setting initial variables
        # -------------------------
        name = phone = email = None

        # Walking through the tree to find the elements available in the 
        # modified licensee output
        # --------------------------------------------------------------
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'Person':
                for child in node.childNodes:
                    if child.nodeName   == 'Name':
                        name = cdr.getTextContent(child)
                    elif child.nodeName == 'Phone':
                        phone = cdr.getTextContent(child)
                    elif child.nodeName == 'Email':
                        email = cdr.getTextContent(child)

            # In case we have multiple names (if we also need the information
            # for the secondary lead orgs) collect the info in a list
            # ---------------------------------------------------------------
            self.pupName.append(name)
            self.pupPhone.append(phone)
            self.pupEmail.append(email)

        nctInfo[u'pupName'] = self.pupName
        nctInfo[u'pupPhone'] = self.pupPhone
        nctInfo[u'pupEmail'] = self.pupEmail

        # Extract the Verification Mailer information from the database
        # -------------------------------------------------------------
        cursor.execute("""\
            SELECT value 
              FROM query_term 
             WHERE doc_id = (
                   SELECT MAX(i.doc_id)
                     FROM query_term i
                     JOIN query_term v  -- only extract Verification Mailer
                       ON v.doc_id = i.doc_id
                      AND v.path   = '/Mailer/Type'
                      AND v.value  = 'Verification mailer'
                    WHERE i.int_val = %s
                      AND i.path = '/Mailer/Document/@cdr:ref'
                   )
               AND path = '/Mailer/Response/ChangesCategory'""" % self.cdrId)

        rows = cursor.fetchall()

        responseCat = []
        if rows:
            for row in rows:
                responseCat.append(row[0])

            nctInfo[u'vMailerResp'] = u'Yes'
            nctInfo[u'vMailerChange'] = responseCat
        else:
            nctInfo[u'vMailerResp'] = u'No'


# -------------------------------------------------------------
#
# -------------------------------------------------------------
def getElementText(parent, name):
    nodes = parent.getElementsByTagName(name)
    return nodes and cdr.getTextContent(nodes[0]) or None


# -------------------------------------------------------------
# Read the protocol file 
# -------------------------------------------------------------
def readProtocols(filename = 'd:/cdr/tmp/CTGov_Protocols.xls'):
    book = ExcelReader.Workbook(filename)
    sheet = book[0]
    headerRow = 1
    rownum = 0
    ctGovProtocols = {}
    for row in sheet.rows:
        rownum += 1
        if rownum > headerRow:
            nctId     = row[0]
            cdrId     = row[1]
            pID       = row[2]
            source    = row[3]
            status    = row[4]
            closeDate = row[5]
            complDate = row[6]
            respParty = row[7]
            fda       = row[8]
            phase     = row[9]
            ctGovProtocols[nctId.val] = {u'CDRID':str(cdrId),
                                         u'pid':str(pID),
                                         u'source':str(source),
                                         u'status':str(status),
                                         u'closeDate':closeDate.val,
                                         u'complDate':complDate.val,
                                         u'respParty':respParty.val,
                                         u'fda':fda.val,
                                         u'phase':phase.val}
    return ctGovProtocols


# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
wsTitle = "CTGov with PUP Report"
t = time.strftime("%Y%m%d%H%M%S")
REPORTS_BASE = 'd:/cdr/tmp'
REPORTS_BASE = 'm:/cdr/tmp'

# Input file name
# ---------------
ctGovName = u'/Trials Missing Info_PUP Contact Info.xls'

# Output file name
# ----------------
name = u'/CTGov_with_PUP-%s.xml' % t
fullname = REPORTS_BASE + name

# ----------------------------------------------------------------------
# First Step:
# We need to read the content of the Spreadsheet provided
# ----------------------------------------------------------------------
ctGovProtocols = readProtocols(filename = REPORTS_BASE + ctGovName)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

i = 0
for docs in ctGovProtocols.keys():
    i += 1
    print '%d: Doc = %s' % (i, docs)
    Protocol(ctGovProtocols[docs], cursor)
    #print ctGovProtocols[docs]
    #print '*****'

print 'Records processed: %s' % len(ctGovProtocols)
#sys.exit(1)
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
ws      = wb.addWorksheet(wsTitle, style1, 45, 1)
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', size = 12)
styleH  = wb.addStyle(alignment = alignH, font = headFont)
    
# Set the colum width
# -------------------
ws.addCol( 1,  80)
ws.addCol( 2,  55)
ws.addCol( 3,  120)
ws.addCol( 4,  100)
ws.addCol( 5,  60)
ws.addCol( 6,  60)
ws.addCol( 7,  60)
ws.addCol( 8,  40)
ws.addCol( 9,  40)
ws.addCol(10,  60)
ws.addCol(11,  120)
ws.addCol(12,  80)
ws.addCol(13,  150)
ws.addCol(14,  55)
ws.addCol(15,  150)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, styleH)
exRow.addCell(1, 'NCT-ID')
exRow.addCell(2, 'CDR-ID')
exRow.addCell(3, 'Primary ID')
exRow.addCell(4, 'Source')
exRow.addCell(5, 'Protocol Status')
exRow.addCell(6, 'Closed Before 2007-09-27?')
exRow.addCell(7, 'Completion Date')
exRow.addCell(8, 'RP [Y/N]')
exRow.addCell(9, 'FDA Reg [Y/N]')
exRow.addCell(10, 'Phase')
exRow.addCell(11, 'PUP Name')
exRow.addCell(12, 'PUP Phone')
exRow.addCell(13, 'PUP Email')
exRow.addCell(14, 'Ver Mailer Response')
exRow.addCell(15, 'Response Category')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in ctGovProtocols.keys():
    # print rowNum
    if ctGovProtocols[row][u'CDRID'] != 'CDR ID':
        rowNum += 1
        exRow = ws.addRow(rowNum, style1, 40)
        exRow.addCell(1, row)
        exRow.addCell(2, ctGovProtocols[row][u'CDRID'])
        exRow.addCell(3, ctGovProtocols[row][u'pid'])
        exRow.addCell(4, ctGovProtocols[row][u'source'])
        exRow.addCell(5, ctGovProtocols[row][u'status'])
        exRow.addCell(6, ctGovProtocols[row][u'closeDate'])
        exRow.addCell(7, ctGovProtocols[row][u'complDate'])
        exRow.addCell(8, ctGovProtocols[row][u'respParty'])
        exRow.addCell(9, ctGovProtocols[row][u'fda'])
        exRow.addCell(10, ctGovProtocols[row][u'phase'])

        if ctGovProtocols[row].has_key(u'pupName') and \
           ctGovProtocols[row][u'pupName']:
            exRow.addCell(11, ctGovProtocols[row][u'pupName'][0])

        if ctGovProtocols[row].has_key(u'pupPhone') and \
           ctGovProtocols[row][u'pupPhone']:
            exRow.addCell(12, ctGovProtocols[row][u'pupPhone'][0])

        if ctGovProtocols[row].has_key(u'pupEmail') and \
           ctGovProtocols[row][u'pupEmail']:
            exRow.addCell(13, ctGovProtocols[row][u'pupEmail'][0])

        if ctGovProtocols[row].has_key(u'vMailerResp') and \
           ctGovProtocols[row][u'vMailerResp']:
            exRow.addCell(14, ctGovProtocols[row][u'vMailerResp'][0])

        if ctGovProtocols[row].has_key(u'vMailerChange') and \
           ctGovProtocols[row][u'vMailerChange']:
            exRow.addCell(15, ", ".join([x for x in ctGovProtocols[row][u'vMailerChange']]))

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
