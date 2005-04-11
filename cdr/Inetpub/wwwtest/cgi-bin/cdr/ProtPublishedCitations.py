#----------------------------------------------------------------------
#
# $Id: ProtPublishedCitations.py,v 1.2 2005-04-11 21:12:57 venglisc Exp $
#
# Report identifying previously published protocols that should be 
# included in a hotfix.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/04/11 21:05:44  venglisc
# Initial version of Protocol Published Citation Report.
# The report displayes all citations linked to InScopeProtocols along with
# the citations formatted output.
# Due to the fact that the formatted output has to be displayed each
# individual citation will have to be filtered -- a very time consuming
# process.
# The command is run from the command line
#    $ python ProtPublishedCitations.py > filename.xls
# (Bug 1612)
#
#
#----------------------------------------------------------------------
import cdr, cdrdb, pyXLWriter, sys, time, cdrcgi

def addWorksheet(workbook, title, headers, widths, headerFormat, rows):
    worksheet = workbook.add_worksheet(title)
    worksheet.set_landscape()
    worksheet.set_margin_top(0.50)
    worksheet.set_margins_LR(0.25)
    worksheet.set_margin_bottom(0.25)
    worksheet.set_header('&RPage &P of &N', 0.25)
    worksheet.repeat_rows(3)
    worksheet.center_horizontally
    worksheet.write([1, 3], 'Protocol Published Citation Report',
                    workbook.add_format(bold=1))
    for col in range(len(headers)):
        worksheet.set_column(col, widths[col])
        worksheet.write([3, col], headers[col], headerFormat)

    r = 4
    for row in rows:
        c = 0
        for col in row:
            if type(col) == type(9):
                col = `col`
            elif type(col) == type(u""):
                col = col.encode('latin-1', 'replace')
            if 0 and c == 2:
                worksheet.write([r, c], col, datefmt)
            elif c == 5:
                if row[5] != None:
                    url = ("http://www.ncbi.nlm.nih.gov/entrez/query.fcgi"
                           "?cmd=Retrieve&amp;db=pubmed&amp;dopt=Abstract" 
                           "&amp;list_uids=%s" % (row[5]))
                    worksheet.write_url([r, c], url, col,
                                    workbook.add_format(align='top',
                                                        size=8, 
                                                        color='blue',
                                                        underline=1))
                else:
                    worksheet.write([r, c], col,
                                    workbook.add_format(align='top',
                                                        size=8))
            else:
                worksheet.write([r, c], col, 
                                workbook.add_format(align='top', 
                                                    text_wrap=1,
                                                    size=8))
            c += 1
        #worksheet.write([r, c], url)
        r += 1
    #sys.stderr.write("Created worksheet %s\n" % title)

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()

# Creating table of all InScopeProtocol documents
# that have been published (and pushed to Cancer.gov)
# We start looking from the last successfull pushing job of the 
# full data set since there may be documents that were dropped
# because of that and did not have a removal record in the 
# pub_proc_doc table
# ------------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #t0
             (id INTEGER     NOT NULL,
             job INTEGER     NOT NULL,
        doc_type VARCHAR(32) NOT NULL,
   active_status CHAR        NOT NULL)
""")

cursor.execute("""\
    INSERT INTO #t0
         SELECT a.id, MAX(p.id), t.name, a.active_status
           FROM all_docs a
           JOIN doc_type t
             ON a.doc_type = t.id
           JOIN pub_proc_doc d
             ON d.doc_id = a.id
           JOIN pub_proc p
             ON p.id = d.pub_proc
          WHERE t.name = 'InScopeProtocol'
            AND (d.failure IS NULL OR d.failure <> 'Y')
            AND p.status = 'Success'
            AND p.pub_subset LIKE 'Push_Documents_To_Cancer.Gov%'
            AND P.id >= (SELECT max(id)
                           FROM pub_proc
                          WHERE pub_subset = 'Push_Documents_to_Cancer.Gov_Full-Load'
                            AND status = 'Success'
                        )
       GROUP BY a.id, t.name, a.active_status
""", timeout = 300)

# Create a temp table listing all documents created under #t0 along
# with it's title, primary ID, and citation link
# -----------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #t1
             (id INTEGER       NOT NULL,
             cit INTEGER       NOT NULL,
          protid NVARCHAR(32)  NOT NULL,
           title NVARCHAR(510) NOT NULL,
          otitle NVARCHAR(510) NOT NULL,
          ptitle NVARCHAR(510) NOT NULL,
             job INTEGER       NOT NULL,
        doc_type VARCHAR(32)   NOT NULL,
   active_status CHAR          NOT NULL,
         removed CHAR          NOT NULL)
""")

cursor.execute("""\
    INSERT INTO #t1
         SELECT t.id, c.int_val, pid.value, d.title, tot.value, tpt.value, 
                t.job, t.doc_type, t.active_status, p.removed
           FROM pub_proc_doc p
           JOIN #t0 t
             ON p.doc_id = t.id
            AND p.pub_proc = t.job
           JOIN document d
             ON d.id = t.id
           JOIN query_term pid
             ON t.id = pid.doc_id
            AND pid.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
           JOIN query_term tot
             ON t.id = tot.doc_id
            AND tot.path = '/InScopeProtocol/ProtocolTitle'
           JOIN query_term ot
             ON t.id = ot.doc_id
            AND tot.node_loc = ot.node_loc
            AND ot.value in ('Original')
            AND ot.path = '/InScopeProtocol/ProtocolTitle/@Type'
           JOIN query_term tpt
             ON t.id = tpt.doc_id
            AND tpt.path = '/InScopeProtocol/ProtocolTitle'
           JOIN query_term pt
             ON t.id = pt.doc_id
            AND tpt.node_loc = pt.node_loc
            AND pt.value in ('Professional')
            AND pt.path = '/InScopeProtocol/ProtocolTitle/@Type'
           JOIN query_term c
             ON t.id = c.doc_id
            AND c.path = '/InScopeProtocol/PublishedResults/Citation/@cdr:ref'
            """, timeout = 300)

# Create a temp table with all the existing latest valid versions
# ----------------------------------------------------------------------
cursor.execute("""\
         CREATE TABLE #t2 (cit  INTEGER  NOT NULL, 
                           pmid INTEGER  NOT NULL)
""")

cursor.execute("""\
    INSERT INTO #t2
         SELECT DISTINCT doc_id, int_val
           FROM query_term q
          WHERE exists (SELECT 'x'
                          FROM #t1 t
                         WHERE t.cit = q.doc_id
                       )
            AND q.path = '/Citation/PubmedArticle/MedlineCitation/PMID'
""", timeout = 300)

# Create a temp table listing all OtherID protocol names
# ------------------------------------------------------
cursor.execute("""\
         CREATE TABLE #t3 (id  INTEGER     NOT NULL, 
                      otherid  VARCHAR(50) NOT NULL)
""")

cursor.execute("""\
    INSERT INTO #t3
         SELECT q.doc_id, q.value
           FROM query_term q
           JOIN #t0 t0
             ON q.doc_id = t0.id
          WHERE path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
          ORDER BY q.doc_id, q.value
""", timeout = 300)

# Create the list of InScopeProtocols for which we find a publishable
# version whose version number is greater than the version number that
# has been published.
# ---------------------------------------------------------------------
cursor.execute("""\
         SELECT t1.id, t1.protid, t1.ptitle, t1.otitle, t1.cit, t2.pmid
           FROM #t1 t1
LEFT OUTER JOIN #t2 t2
             ON t1.cit = t2.cit
          ORDER BY t1.protid
""", timeout = 300)

rows = cursor.fetchall()

# Filter the Citation document to extract the formatted citation
# for each document
# --------------------------------------------------------------
for row in rows:
    response = []
    response = cdr.filterDoc('guest', ['set:Format Citation'], row[4])
    row.append(response[0])

# Select the protocol OtherIDs and concatenate them to the primary
# protocol ID
# --------------------------------------------------------------------
for row in rows:
    query = """\
         SELECT otherid
           FROM #t3
          WHERE id = %s
""" % row[0]
    cursor.execute(query)
    names = cursor.fetchall()

    otherNames = ''
    for name in names:
        otherNames += '; ' + name[0]
    row[1] += otherNames

t = time.strftime("%Y%m%d%H%M%S")
#print "Content-type: application/vnd.ms-excel"
#print "Content-Disposition: attachment; filename=PublishedCitationReport-%s.xls" % t
#print 

workbook = pyXLWriter.Writer(sys.stdout)

format = workbook.add_format()
format.set_bold();
format.set_color('white')
format.set_bg_color('blue')
format.set_align('top')

# Create worksheet listing all updated InScopeProtocols
# -----------------------------------------------------
titles  = ('InScopeProtocol Citations', 'Summary Titles')
colheaders = ['DocID',    'Protocol IDs',
           'HP Title', 'Original Title', 
           'CID', 'PMID', 
           'Formatted Citation', 'Kp/Rm', 'Comment']
widths  = (5, 15, 25, 25, 7, 8, 25, 5, 15)
addWorksheet(workbook, titles[0], colheaders, widths, format, rows)

workbook.close()
