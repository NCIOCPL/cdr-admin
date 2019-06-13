#----------------------------------------------------------------------
# Finding ProtocolRef elements in Summary documents and testing its
# final location (Cancer.gov or ClinicalTrials.gov).  Some of the 
# links may have been removed my vendor filters if the linked document
# has been blocked.  Those links will be listed as 'None'.
#
#----------------------------------------------------------------------
from lxml import etree
from cdrapi import db as cdrdb
import cdr
import cdrcgi
import cgi
import requests
import sys
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
class SummaryDoc:
    """ Class to extract the ProtocolRef elements and URL for the link
        It creates the list of rows for each ProtocolRef link found

        This didn't have to be a class.  Should be rewritten.
    """

    def __init__(self, docId):
        self.docId = docId
        self.rows = []

        # Retrieve the XML of the summary
        # ----------------------------------------------------
        qry = "SELECT xml FROM document WHERE id = %d" % docId
        query = cdrdb.Query("document", "xml")
        query.where("id = {}".format(docId))
        cursor = query.execute()
        row = cursor.fetchall()
        cursor.close()

        #cursor = conn.cursor()
        #cursor.execute(qry)
        #row = cursor.fetchall()
        #cursor.close()

        docXml = row[0][0]
        tree = etree.XML(docXml.encode('utf-8'))

        # Finding the summary title
        # --------------------------
        for titleNode in tree.findall('.//SummaryTitle'):
            title = "CDR%d - %s" % (docId, titleNode.text)
            sumRow = (self.docId, titleNode.text)

        # Finding the summary URL
        # -------------------------
        for urlNode in tree.findall('.//SummaryURL'):
            summaryUrl = urlNode.attrib['{cips.nci.nih.gov/cdr}xref']

        # Searching for all ProtocolRef elements within the document
        # and testing the URL final location
        # Cancer.gov will re-direct the link depending if the 
        # protocol is part of the CTRO.
        # ----------------------------------------------------------
        for node in tree.findall('.//ProtocolRef'):
            attribs = node.attrib
            if 'nct_id' in attribs:
                nctId = attribs['nct_id']

                url = 'https://www.cancer.gov/clinicaltrials/%s' % nctId
                endUrl = requests.head(url, timeout=100.0, headers={'Accept-Encoding':'identity'}).headers.get('location', url)
                row = [self.docId, titleNode.text, node.text, endUrl]
            else:
                row = [self.docId, titleNode.text, node.text, "None"]

            self.rows.append(row)


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
    title = "ProtocolRef links in Summaries"
    now = datetime.date.today()
    subtitle = "Report Date: {}".format(now)

    table = cdrcgi.Report.Table(columns, rows)
    report = cdrcgi.Report(title, [table], banner=title, subtitle=subtitle)
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

    # Connecting to the DB and executing the query
    # ----------------------------------------------------
    #try:
    #    conn = cdrdb.connect()
    #    cursor = conn.cursor()
    #    cursor.execute(qry)
    #    rows = cursor.fetchall()
    #    cursor.close()
    #except:
    #    cdrcgi.bail(qry)
    #    sys.exit('*** clinical_trials.py: Error connecting to DB ***')

    #for docId in [62753, 62779]:
    docIds = [row[0] for row in rows ]
    rows = []

    for docId in docIds[0:10]:
        try:
            doc = SummaryDoc(docId)
            rows.extend(doc.rows)
        except Exception as e:
            cdrcgi.bail("CDR%d: %s" % (docId, e))

    show_report(rows)
