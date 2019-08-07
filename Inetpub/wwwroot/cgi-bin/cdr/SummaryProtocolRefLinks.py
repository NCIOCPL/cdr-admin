#----------------------------------------------------------------------
# Finding ProtocolRef elements in Summary documents and testing its
# final location (Cancer.gov or ClinicalTrials.gov) by following
# redirects.  Some of the
# links may have been removed by vendor filters if the linked document
# has been blocked.  Those links will be listed as 'None'.
#
#----------------------------------------------------------------------
from lxml import etree
from cdrapi import db as cdrdb
import cdr
import cdrcgi
import cgi
import grequests
#import sys
import datetime
#import time

from cdrapi.settings import Tier
TIER = Tier()

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage() or None

if not fields:
    session    = 'guest'
    tier = TIER
else:
    session    = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
    tier       = fields.getvalue("Tier") or 'DEV'


#----------------------------------------------------------------------
# Document class holding all CDR-IDs, and rows to display on report
#----------------------------------------------------------------------
class SummaryDoc:
    """ Class to extract the ProtocolRef elements and URL for the link
        It creates the list of rows for each ProtocolRef link found

        This didn't have to be a class.  Should be rewritten.

        Modified to use grequests allowing to submit multiple URLs
        at the same time.
        Using grequests didn't safe much time, so I'm additionally
        removing duplicates within summaries.
    """

    def __init__(self, docId):
        self.docId = docId
        # Rows to be displayed on the report
        self.rows = []
        # Rows with original URLs
        protRefRows = []

        # Retrieve the XML of the summary
        # ----------------------------------------------------
        qry = "SELECT xml FROM document WHERE id = %d" % docId
        query = cdrdb.Query("document", "xml")
        query.where("id = {}".format(docId))
        cursor = query.execute()
        row = cursor.fetchall()
        cursor.close()

        docXml = row[0][0]
        tree = etree.XML(docXml.encode('utf-8'))

        # Finding the summary title
        # --------------------------
        for titleNode in tree.findall('.//SummaryTitle'):
            title = "CDR%d - %s" % (docId, titleNode.text)
            sumRow = (self.docId, titleNode.text)

        # Finding the summary URL (currently not used)
        # --------------------------------------------
        for urlNode in tree.findall('.//SummaryURL'):
            summaryUrl = urlNode.attrib['{cips.nci.nih.gov/cdr}xref']

        # Searching for all ProtocolRef elements within the document
        # and testing the URL final location
        # Cancer.gov will re-direct the link depending if the
        # protocol is part of the CTRO or not.
        # We're creating the rows with the original URL first and
        # are replacing the final URL after the "grequests" call.
        # ----------------------------------------------------------
        for node in tree.findall('.//ProtocolRef'):
            attribs = node.attrib
            if 'nct_id' in attribs:
                nctId = attribs['nct_id']

                url = 'https://www.cancer.gov/clinicaltrials/%s' % nctId
                row = [self.docId, titleNode.text, node.text, url]
            else:
                row = [self.docId, titleNode.text, node.text, 'None']

            protRefRows.append(row)

        # We have all ProtocolRef links for this summary.  Now we want
        # to dedup those. No need to follow the same link multiple times
        # --------------------------------------------------------------

        # Build a set out of the list of lists (rows)
        # -------------------------------------------
        rowsTuple = [tuple(lst) for lst in protRefRows]
        uniqueRows = set(rowsTuple)

        # Convert back to a list so we can iterate over it and update
        # the original URL with the redirected URL retrieved with
        # the grequests call
        # --------------------------------------------------------------
        uniqueLst = list(uniqueRows)

        # Building list of URLs from the rows to be tested all at once.
        # -------------------------------------------------------------
        urls = []
        for row in uniqueLst:
            try:
                urls.append(row[3])
            except:
                urls.append('Missing URL value')

        # Sending the requests
        # --------------------
        endUrls = (grequests.head(u, allow_redirects=True) for u in urls)
        sumUrls = grequests.map(endUrls)

        # Creating the rows to be displayed and updating the URL with the
        # result from the grequests call
        # ---------------------------------------------------------------
        self.rows = [list(row) for row in uniqueLst]
        for i, row in enumerate(self.rows):
            try:
                #print(sumUrls[i].url)
                row[3] = sumUrls[i].url
            except:
                if row[3] != 'None':
                    row[3] += ' *** URL timed out'


# -------------------------------------------------------------------
# Display the report
# -------------------------------------------------------------------
def show_report(rows):
    columns = (
                cdrcgi.Report.Column("CDR ID"),
                cdrcgi.Report.Column("Summary Title"),
                cdrcgi.Report.Column("Protocol ID"),
                cdrcgi.Report.Column("Protocol Link")
              )
    repTitle = "ProtocolRef links in Summaries"
    now = datetime.date.today()
    subtitle = "Report Date: {}".format(now)

    allLinks = { "CT": 0,
                 "CG": 0,
                 "None":0 }

    # Counting the protocol links by "type" to create summary table
    # -------------------------------------------------------------
    for cdrId, title, protId, link in rows:
        if link.find('clinicaltrials.gov') > -1:
            allLinks['CT'] += 1
        elif link.find('cancer.gov') > -1:
            allLinks['CG'] += 1
        else:
            allLinks['None'] += 1

    # Preparing the summary table
    # ---------------------------
    countCols = ( cdrcgi.Report.Column("Protocol Links including..."),
                  cdrcgi.Report.Column("Count") )
    countRows = ( ("clinicaltrials.gov", allLinks['CT']),
                  ("www.cancer.gov", allLinks['CG']),
                  ("None", allLinks['None']) )
    countHeader = "Total Count by Link Type"
    countTable = cdrcgi.Report.Table(countCols, countRows,
                                     caption = countHeader)

    # Preparing main protocol link table
    # ----------------------------------
    header = "Links to Clinical Trials"
    table = cdrcgi.Report.Table(columns, rows, caption = header)
    report = cdrcgi.Report(repTitle, [countTable, table], banner=repTitle,
                           subtitle=subtitle)
    report.send()


if __name__ == "__main__":
    # Connecting to DB and selecting all published summaries
    # with ProtocolRefs
    # --------------------------------------------------------
    qry = """
        SELECT DISTINCT p.doc_id
          FROM query_term_pub p
          JOIN pub_proc_cg c
            ON c.id = p.doc_id
         WHERE path like '/Summary/%ProtocolRef%'
         ORDER BY p.doc_id
    """
    query = cdrdb.Query("query_term_pub p",
                        "DISTINCT p.doc_id").order("p.doc_id")
    query.join("pub_proc_cg c", "c.id = p.doc_id")
    query.where("path like '/Summary/%ProtocolRef%'")
    cursor = query.execute()
    rows = cursor.fetchall()
    cursor.close()

    docIds = [row[0] for row in rows]
    rows = []

    #start_time = time.time()

    for docId in docIds:
        try:
            doc = SummaryDoc(docId)
            rows.extend(doc.rows)
        except Exception as e:
            cdrcgi.bail("CDR%d: %s" % (docId, e))

    #print("--- {} seconds ---".format(time.time() - start_time))

    show_report(rows)
