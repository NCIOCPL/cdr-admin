#----------------------------------------------------------------------
#
# $Id: DcpProtocolWithNctid.py,v 1.1 2008-05-08 20:40:18 venglisc Exp $
#
# Report of DCP InScopeProtocols with NCT protocol ID
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, sys, time, ExcelWriter, ExcelReader

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()

# -------------------------------------------------------------
# Read the DCP protocol file (stored in CSV format)
# -------------------------------------------------------------
def readProtocols(filename = 'd:/cdr/tmp/DCP_Protocols.xls'):
    book = ExcelReader.Workbook(filename)
    sheet = book[0]
    headerRow = 1
    rownum = 0
    dcpProtocols = {}
    for row in sheet.rows[1:]:
        dcpID    = row[0]
        dcpNct   = row[1]
        dcpTitle = row[2]
        dcpProtocols[dcpID.val] = {u'DCPTitle':dcpTitle.val, 
                                   u'CDR-NCTID':dcpNct and dcpNct.val or None} 
    return dcpProtocols


# -------------------------------------------------------------
# Clean the text string by removing spaces, dots, dashes, etc.
# -------------------------------------------------------------
def normalizeText(text):
    if type(text) == type(1.0): text = str(text)
    try:
        cleanText = text.strip().lower().\
replace(' ', '').\
replace('-', '').\
replace('.', '').\
replace(',', '').\
replace('/', '')
    except:
        print 'Type Error: %s - %s' % (text, type(text))
        return text
    return cleanText


# -------------------------------------------------------------
# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
t = time.strftime("%Y%m%d%H%M%S")
REPORTS_BASE = 'd:/cdr/tmp'
name = '/DcpProtocolWithNctid.xls'
dcpName = '/DCP_Protocols.xls'
fullname = REPORTS_BASE + name

# Read the spreadsheet providing the DCP IDs
# ------------------------------------------
dcpProtocols = readProtocols(filename = REPORTS_BASE + dcpName)


#----------------------------------------------------------------------
# Find InScopeProtocol that are marked as DCP protocols
#----------------------------------------------------------------------
# Query to find all DCP protocols based on the 'DCP ID' IDType
# ------------------------------------------------------------
query1 = """\
SELECT q1.doc_id, q1.value AS "Primary ID", 
       q2.value AS "ID Type", q3.value AS "Other ID", 
       q4.value AS "ID Type", q5.value AS "NCT ID",
       q6.value AS "Title",   q7.value AS "Title Type"
  FROM query_term q1
  JOIN query_term q2
    ON q1.doc_id = q2.doc_id
   AND q2.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND q2.value  in (%s)
  JOIN query_term q3
    ON q1.doc_id = q3.doc_id
   AND q3.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
   AND left(q2.node_loc, 8) = left(q3.node_loc, 8)
  JOIN query_term q4
    ON q1.doc_id = q4.doc_id
   AND q4.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND q4.value  = 'ClinicalTrials.gov ID'
  JOIN query_term q5
    ON q1.doc_id = q5.doc_id
   AND q5.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
   AND left(q4.node_loc, 8) = left(q5.node_loc, 8)
  JOIN query_term q6
    ON q1.doc_id = q6.doc_id
   AND q6.path   = '/InScopeProtocol/ProtocolTitle'
  JOIN query_term q7
    ON q1.doc_id = q7.doc_id
   AND q7.path   = '/InScopeProtocol/ProtocolTitle/@Type'
   AND left(q6.node_loc, 4) = left(q7.node_loc, 4)
   AND q7.value  = 'Original'
 WHERE q1.path   = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
"""

query2 = """\
SELECT distinct q1.doc_id, q1.value AS "Primary ID", 
     --  q2.value AS "ID Type", q3.value AS "Other ID", 
       q4.value AS "ID Type", q5.value AS "NCT ID",
       q6.value AS "Title",   q7.value AS "Title Type"
  FROM query_term q1
  JOIN query_term q2
    ON q1.doc_id = q2.doc_id
   AND q2.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND q2.value  in (%s)
  JOIN query_term q3
    ON q1.doc_id = q3.doc_id
   AND q3.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
   AND left(q2.node_loc, 8) = left(q3.node_loc, 8)
  JOIN query_term q4
    ON q1.doc_id = q4.doc_id
   AND q4.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND q4.value  = 'ClinicalTrials.gov ID'
  JOIN query_term q5
    ON q1.doc_id = q5.doc_id
   AND q5.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
   AND left(q4.node_loc, 8) = left(q5.node_loc, 8)
  JOIN query_term q6
    ON q1.doc_id = q6.doc_id
   AND q6.path   = '/InScopeProtocol/ProtocolTitle'
  JOIN query_term q7
    ON q1.doc_id = q7.doc_id
   AND q7.path   = '/InScopeProtocol/ProtocolTitle/@Type'
   AND left(q6.node_loc, 4) = left(q7.node_loc, 4)
   AND q7.value  = 'Original'
 WHERE q1.path   = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
"""

# This query is only used if we're looking for protocols without
# an NCT-ID
query3 = """\
SELECT q1.doc_id, q1.value AS "Primary ID", 
       q2.value AS "ID Type", q3.value AS "DCP ID", 
       q4.value AS "ID Type", q5.value AS "NCT ID",
       q6.value AS "Title",   q7.value AS "Title Type"
  FROM query_term q1
  JOIN query_term q2
    ON q1.doc_id = q2.doc_id
   AND q2.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND q2.value  in (%s) 
  JOIN query_term q3
    ON q1.doc_id = q3.doc_id
   AND q3.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
   AND left(q2.node_loc, 8) = left(q3.node_loc, 8)
 left outer JOIN query_term q4
    ON q1.doc_id = q4.doc_id
   AND q4.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND q4.value  = 'ClinicalTrials.gov ID'
 left outer JOIN query_term q5
    ON q1.doc_id = q5.doc_id
   AND q5.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
   AND left(q4.node_loc, 8) = left(q5.node_loc, 8)
  JOIN query_term q6
    ON q1.doc_id = q6.doc_id
   AND q6.path   = '/InScopeProtocol/ProtocolTitle'
  JOIN query_term q7
    ON q1.doc_id = q7.doc_id
   AND q7.path   = '/InScopeProtocol/ProtocolTitle/@Type'
   AND left(q6.node_loc, 4) = left(q7.node_loc, 4)
   AND q7.value  = 'Original'
 WHERE q1.path   = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
and q4.value is NULL
"""

query4 = """\
SELECT q1.doc_id, q1.value, q2.value
  FROM query_term q1
  JOIN query_term q2
    ON q1.doc_id = q2.doc_id
   AND q2.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
   AND left(q1.node_loc, 8) = left(q2.node_loc, 8)
 WHERE q1.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND q1.value in ('Alternate', 'NCI alternate', 'CTEP ID',
                    'Institutional/Original', 'Secondary')
   AND q1.doc_id = %s
"""


cursor.execute(query1 % "'DCP ID'", timeout = 300)
rows = cursor.fetchall()

# Now we have all DCP protocols from the CDR.  Compare the protocol IDs
# with the once retrieved from the spreadsheet.  We'll expand the 
# dictionary of DCP protocols with the CDR protocol ID, the CDR DCP ID 
# (as we know it), and a 'MATCH' string indicating how we matched the 
# documents:  Match-CDRID, Match-Title, Match-...
# ---------------------------------------------------------------------
allDcpIds = dcpProtocols.keys()
allDcpIds.sort()

numProt = numMatch = numMatchTotal = 0
for dcpId in allDcpIds:
    numProt += 1
    # First matching their ID against our protocol ID
    for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
                                        origTitle, didi) in rows:
        if normalizeText(cdrDcpId) == normalizeText(dcpId):
            #print "Match on ProtID: %s - %s" % (protId, dcpId)
            numMatch += 1
            dcpProtocols[dcpId].update({'Match':'1-DCPId', 
                                        'CDR-ID':cdrId,
                                        'CDR-ProtID':protId,
                                        'CDR-DCPID':cdrDcpId,
                                        'OtherID':None,
                                        'CDR-NCTID':cdrNctId,
                                        'CDR-Title':origTitle})

    # Second matching their ID against our DCP ID
    for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
                                        origTitle, didi) in rows:
        if dcpProtocols[dcpId].has_key('Match'):
            continue
        elif normalizeText(protId) == normalizeText(dcpId):
            #print "Match on DCP ID: %s - %s" % (cdrDcpId, dcpId)
            numMatch += 1
            dcpProtocols[dcpId].update({'Match':'2-ProtocolId', 
                                        'CDR-ID':cdrId,
                                        'CDR-ProtID':protId,
                                        'CDR-DCPID':cdrDcpId,
                                        'OtherID':None,
                                        'CDR-NCTID':cdrNctId,
                                        'CDR-Title':origTitle})

    # Third matching their protocol title against our title 
    for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
                                        origTitle, didi) in rows:
        dcpProtString  = normalizeText(dcpProtocols[dcpId][u'DCPTitle'])
        origProtString = normalizeText(origTitle)

        if dcpProtocols[dcpId].has_key('Match'):
            continue
        elif (dcpProtString == origProtString):
            numMatch += 1
            dcpProtocols[dcpId].update({'Match':'3-Title', 
                                        'CDR-ID':cdrId,
                                        'CDR-ProtID':protId,
                                        'CDR-DCPID':cdrDcpId,
                                        'OtherID':None,
                                        'CDR-NCTID':cdrNctId,
                                        'CDR-Title':origTitle})

numMatchTotal = numMatch
print "Match %d of %d protocols - Total: %s" % (numMatch, numProt,
                                                numMatchTotal)

# Second Round, we are checking which of the protocols don't have
# an NCT ID
# Note: Lakshmi is not interested in any protocols that don't have
#       a NCT ID so we can remove this third round of testing
#       However, if we do match these protocols we can shave off
#       about 20 seconds for each protocol identified here in the 
#       next loop.
# ----------------------------------------------------------------
cursor.execute(query3 % "'DCP ID', 'CTEP ID','NCI alternate','Alternate'",
                       timeout = 300)
#cursor.execute(query3, timeout = 300)
rows = cursor.fetchall()

numMatch = 0
for dcpId in allDcpIds:
    # First matching their ID against our protocol ID
    for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
                                        origTitle, didi) in rows:
        if dcpProtocols[dcpId].has_key('Match'):
            continue
        elif normalizeText(protId) == normalizeText(dcpId):
            numMatch += 1
            dcpProtocols[dcpId].update({'Match':'4-NoNCTID', 
                                        'CDR-ID':cdrId,
                                        'CDR-ProtID':protId,
                                        'CDR-DCPID':cdrDcpId,
                                        'OtherID':None,
                                        'CDR-NCTID':'NA',
                                        'CDR-Title':origTitle})

    # Second matching their ID against our DCP ID
    #for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
    #                                    origTitle, didi) in rows:
    #    if dcpProtocols[dcpId].has_key('Match'):
    #        continue
    #    elif cdrDcpId == dcpId:
    #        #print "Match on DCP ID: %s - %s" % (cdrDcpId, dcpId)
    #        numMatch += 1
    #        dcpProtocols[dcpId].update({'Match':'8-DCPId-NoNCT', 
    #                                    'CDR-ID':cdrId,
    #                                    'CDR-ProtID':protId,
    #                                    'CDR-DCPID':cdrDcpId,
    #                                    'CDR-NCTID':'NA',
    #                                    'CDR-Title':origTitle})
#
    ## Trying to match against a substring of the protocol IDs
    ## Note: This is iffy. Per Lakshmi we don't want to use this match
    #for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
    #                                    origTitle, didi) in rows:
    #    subProtId = protId.partition('-')
    #    subDcpId  = cdrDcpId.partition('-')
    #    if dcpProtocols[dcpId].has_key('Match'):
    #        continue
    #    elif subProtId[2] == dcpId or subDcpId[2] == dcpId:
    #        #print "Match on ProtID: %s - %s" % (protId, dcpId)
    #        numMatch += 1
    #        dcpProtocols[dcpId].update({'Match':'SubProtId-NoNCT', 
    #                                    'CDR-ID':cdrId,
    #                                    'CDR-ProtID':protId,
    #                                    'CDR-DCPID':cdrDcpId,
    #                                    'CDR-NCTID':cdrNctId,
    #                                    'CDR-Title':origTitle})

    # Third matching their protocol title against our title (limit to
    # the first 200 chars
    for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
                                        origTitle, didi) in rows:
        dcpProtString  = normalizeText(dcpProtocols[dcpId][u'DCPTitle'])
        origProtString = normalizeText(origTitle)

        if dcpProtocols[dcpId].has_key('Match'):
            continue
        elif dcpProtString == origProtString:
            #print "Match on Title : %s - %s" % (cdrDcpId, dcpId)
            numMatch += 1
            dcpProtocols[dcpId].update({'Match':'5-NoNCTTitle', 
                                        'CDR-ID':cdrId,
                                        'CDR-ProtID':protId,
                                        'CDR-DCPID':None,
                                        'OtherID':None,
                                        'CDR-NCTID':'NA',
                                        'CDR-Title':origTitle})

numMatchTotal += numMatch
print "Match %d of %d protocols - Total: %s" % (numMatch, numProt,
                                                numMatchTotal)

# Third Round, we are opening the search criteria in the database
# to everything besides DCP ID
# ----------------------------------------------------------------
cursor.execute(query2 % "'CTEP ID','NCI alternate','Alternate'", timeout = 300)
rows = cursor.fetchall()

numMatch = 0
for dcpId in allDcpIds:
    print '**** ', dcpId
    # First matching their ID against our protocol ID
    #for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
    for (cdrId, protId, dudu, cdrNctId, 
                                        origTitle, didi) in rows:
        if dcpProtocols[dcpId].has_key('Match'):
            continue
        elif normalizeText(protId) == normalizeText(dcpId):
            #print "Match on ProtID: %s - %s" % (protId, dcpId)
            numMatch += 1
            cursor.execute(query4 % cdrId, timeout = 300)
            otherIDs = cursor.fetchall()
            allIDs = ''
            for (oID, oType, oProt) in otherIDs:
                allIDs += "%s (%s), " % (oProt, oType)
            dcpProtocols[dcpId].update({'Match':'6-OtherProtId', 
                                        'CDR-ID':cdrId,
                                        'CDR-ProtID':protId,
                                        'CDR-DCPID':None,
                                        'OtherID':allIDs,
                                        'CDR-NCTID':cdrNctId,
                                        'CDR-Title':origTitle})

    # Second matching their protocol title against our title 
    # Fetch the other IDs to be displayed if we found a match
    #for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
    for (cdrId, protId, dada, cdrNctId, 
                                        origTitle, didi) in rows:
        dcpProtString  = normalizeText(dcpProtocols[dcpId][u'DCPTitle'])
        origProtString = normalizeText(origTitle)

        if dcpProtocols[dcpId].has_key('Match'):
            continue
        elif dcpProtString == origProtString:
            #print "Match on Title : %s - %s" % (cdrDcpId, dcpId)
            numMatch += 1
            cursor.execute(query4 % cdrId, timeout = 300)
            otherIDs = cursor.fetchall()
            allIDs = ''
            for (oID, oType, oProt) in otherIDs:
                allIDs += "%s (%s), " % (oProt, oType)
            dcpProtocols[dcpId].update({'Match':'7-OtherTitle', 
                                        'CDR-ID':cdrId,
                                        'CDR-ProtID':protId,
                                        'CDR-DCPID':None,
                                        'OtherID':allIDs,
                                        'CDR-NCTID':cdrNctId,
                                        'CDR-Title':origTitle})

    # Third matching their ID against our Other IDs
    # This step takes a while since we have to loop through every
    # protocol from the database for every DCP protocol and run
    # the query to find the Other IDs.
    for (cdrId, protId, dudu, cdrNctId, 
                                        origTitle, didi) in rows:
        if dcpProtocols[dcpId].has_key('Match'):
            continue
        else:
            cursor.execute(query4 % cdrId, timeout = 300)
            otherIDs = cursor.fetchall()
            allIDs = ''
            matchFound = False
            for (oID, oType, oProt) in otherIDs:
                allIDs += "%s (%s)," % (oProt, oType)
                if normalizeText(oProt) == normalizeText(dcpId): 
                    matchFound = True
                    print oProt, dcpId
        #elif cdrDcpId == dcpId:
            #print "Match on DCP ID: %s - %s" % (cdrDcpId, dcpId)
            if matchFound:
                print allIDs
                numMatch += 1
                dcpProtocols[dcpId].update({'Match':'8-OtherId', 
                                            'CDR-ID':cdrId,
                                            'CDR-ProtID':protId,
                                            'CDR-DCPID':None,
                                            'OtherID':allIDs,
                                            'CDR-NCTID':cdrNctId,
                                            'CDR-Title':origTitle})
                break

    ## Trying to match against a substring of the protocol IDs
    ## Note: This is iffy. Per Lakshmi we don't want to use this match
    #for (cdrId, protId, dada, cdrDcpId, dudu, cdrNctId, 
    #                                    origTitle, didi) in rows:
    #    subProtId = protId.partition('-')
    #    subDcpId  = cdrDcpId.partition('-')
    #    if dcpProtocols[dcpId].has_key('Match'):
    #        continue
    #    elif subProtId[2] == dcpId or subDcpId[2] == dcpId:
    #        #print "Match on ProtID: %s - %s" % (protId, dcpId)
    #        numMatch += 1
    #        dcpProtocols[dcpId].update({'Match':'SubProtId', 
    #                                    'CDR-ID':cdrId,
    #                                    'CDR-ProtID':protId,
    #                                    'CDR-DCPID':cdrDcpId,
    #                                    'CDR-NCTID':cdrNctId,
    #                                    'CDR-Title':origTitle})

numMatchTotal += numMatch
print "Match %d of %d protocols - Total: %s" % (numMatch, numProt,
                                                numMatchTotal)


# Set all remaining values to None
# --------------------------------
for dcpId in allDcpIds:
    if dcpProtocols[dcpId].has_key('Match'):
        continue
    else:
        dcpProtocols[dcpId].update({'Match':None, 
                                    'CDR-ID':None,
                                    'CDR-ProtID':None,
                                    'CDR-DCPID':None,
                                    'OtherID':None,
                                    'CDR-NCTID':None,
                                    'CDR-Title':None})

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
wb      = ExcelWriter.Workbook()
b       = ExcelWriter.Border()
borders = ExcelWriter.Borders(b, b, b, b)
#font    = ExcelWriter.Font(name = 'Times New Roman', size = 10)
font    = ExcelWriter.Font(name = 'Arial', size = 10)
fontHdr = ExcelWriter.Font(name = 'Arial', size = 10, bold = True)
align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style1  = wb.addStyle(alignment = align, font = font)
# style1  = wb.addStyle(alignment = align, font = font, borders = borders)
urlFont = ExcelWriter.Font('blue', None, 'Arial', size = 10)
style4  = wb.addStyle(alignment = align, font = urlFont)
ws      = wb.addWorksheet("DCP Protocols", style1, 45, 1)
style2  = wb.addStyle(alignment = align, font = fontHdr, 
                         numFormat = 'YYYY-mm-dd')
    
# Set the colum width
# -------------------
ws.addCol( 1, 50)
ws.addCol( 2, 100)
ws.addCol( 3, 120)
ws.addCol( 4, 100)
ws.addCol( 5, 100)
ws.addCol( 6, 80)
ws.addCol( 7, 80)
ws.addCol( 8, 300)
ws.addCol( 9, 300)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, style2)
exRow.addCell(1, 'PDQ Identifier')
exRow.addCell(2, 'PDQ Primary Protocol ID')
exRow.addCell(3, 'DCP ID')
exRow.addCell(4, 'PDQ DCP ID')
exRow.addCell(5, 'Other ID')
exRow.addCell(6, 'Match by')
exRow.addCell(7, 'ClinicalTrials ID')
exRow.addCell(8, 'PDQ Original Title')
exRow.addCell(9, 'DCP Title')


# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for dcpId in allDcpIds:
    #print dcpProtocols[dcpId]
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    url = ("http://www.cancer.gov/clinicaltrials/"
           "view_clinicaltrials.aspx?version=healthprofessional&"
           "cdrid=%s" % dcpProtocols[dcpId]['CDR-ID'])

    exRow.addCell(1, dcpProtocols[dcpId]['CDR-ID'])
    if dcpProtocols[dcpId]['CDR-ProtID']:
        exRow.addCell(2, dcpProtocols[dcpId]['CDR-ProtID'],
                         href = url, style = style4)
    exRow.addCell(3, dcpId)
    exRow.addCell(4, dcpProtocols[dcpId]['CDR-DCPID'])
    exRow.addCell(5, dcpProtocols[dcpId]['OtherID'])
    exRow.addCell(6, dcpProtocols[dcpId]['Match'])
    exRow.addCell(7, dcpProtocols[dcpId]['CDR-NCTID'])
    exRow.addCell(8, dcpProtocols[dcpId]['CDR-Title'])
    exRow.addCell(9, dcpProtocols[dcpId]['DCPTitle'])

# Save the Report
# ---------------
fobj = file(fullname, "w")
wb.write(fobj)
print ""
print "  Report written to %s" % fullname
fobj.close()

