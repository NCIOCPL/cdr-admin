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
import requests
import datetime

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

        Using grequests didn't safe much time, so I'm reverting the
        calls back to requests but I'm now removing duplicates
        protocols within summaries.
    """

    cursor = cdrdb.connect().cursor()
    logger = cdr.Logging.get_logger("SummaryProtocolRefLinks")

    def __init__(self, docId):
        self.logger.info("Parsing CDR%d", docId)
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
        docXml = query.execute(SummaryDoc.cursor).fetchone().xml
        root = etree.XML(docXml.encode('utf-8'))

        # Finding the summary title
        # --------------------------
        titleNode = root.find('SummaryTitle')
        title = "CDR%d - %s" % (docId, titleNode.text)
        sumRow = (self.docId, titleNode.text)

        # Finding the summary URL (currently not used)
        # --------------------------------------------
        for urlNode in root.findall('SummaryMetaData/SummaryURL'):
            summaryUrl = urlNode.get('{cips.nci.nih.gov/cdr}xref')

        # Searching for all ProtocolRef elements within the document
        # and testing the URL final location
        # Cancer.gov will re-direct the link depending if the
        # protocol is part of the CTRO or not.
        # We're creating the rows with the original URL first and
        # are replacing the final URL after the "requests" call.
        # ----------------------------------------------------------
        for node in root.iter('ProtocolRef'):
            nct_id = node.get("nct_id")
            if nct_id:
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
        # the requests call
        # --------------------------------------------------------------
        uniqueLst = list(uniqueRows)

        # Creating the rows to be displayed and updating the URL with the
        # result from the requests call
        # ---------------------------------------------------------------
        self.rows = [list(row) for row in uniqueLst]
        for row in self.rows:
            try:
                request = requests.head(row[3], allow_redirects=True)
                row[3] = request.url
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


# -------------------------------------------------------------------
# Starting Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Connecting to DB and selecting all published summaries
    # with ProtocolRefs
    # --------------------------------------------------------
    start = datetime.datetime.now()
    qry = """
        SELECT DISTINCT p.doc_id
          FROM query_term_pub p
          JOIN pub_proc_cg c
            ON c.id = p.doc_id
         WHERE path like '/Summary/%ProtocolRef%'
         ORDER BY p.doc_id
    """
    query = cdrdb.Query("query_term_pub p", "p.doc_id").unique().order(1)
    query.join("pub_proc_cg c", "c.id = p.doc_id")
    query.where("path LIKE '/Summary/%ProtocolRef%'")
    rows = query.execute().fetchall()
    SummaryDoc.logger.info("Found %d summaries with ProtocolRef links",
                           len(rows))

    docIds = [row.doc_id for row in rows]
    rows = []

    #start_time = time.time()

    for docId in docIds:
        try:
            doc = SummaryDoc(docId)
            rows.extend(doc.rows)
        except Exception as e:
            SummaryDoc.logger.exception("Failure parsing SummaryDoc")
            cdrcgi.bail("CDR%d: %s" % (docId, e))
    elapsed = datetime.datetime.now() - start
    SummaryDoc.logger.info("Finished parsing summaries")
    SummaryDoc.logger.info("Elapsed: %s", elapsed)
    #print("--- {} seconds ---".format(time.time() - start_time))
    show_report(rows)
