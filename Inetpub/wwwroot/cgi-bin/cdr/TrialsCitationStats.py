#----------------------------------------------------------------------
#
# $Id$
#
# "We want to create a new report to be added to the Protocols Menu
# in the CDR, to respond to requests for Clinical Trial Statistics."
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2005/06/09 18:37:41  bkline
# Cosmetic mods requested by Lakshmi.
#
# Revision 1.1  2005/06/06 20:49:32  bkline
# New report for clinical trials statistics.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, time

def showTotal(label, total):
    totalString = str(total)
    dots = (70 - len(totalString) - len(label) - 2) * u'.'
    return label + u' ' + dots + u' ' + totalString

htmlStrings = [u"""\
<html>
 <head>
  <title>Clinical Trials Citation Statistics Report</title>
 </head>
 <body>
  <h3>Clinical Trials Citation Statistics Report</h3>
  <h4>%s</h4>
  <pre>""" % time.strftime("%Y-%m-%d")]
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #protcit (id INTEGER)")
conn.commit()

# Create a table listing all InScopeProtocol that are on Cancer.gov
# and contain a published citation entry
# -----------------------------------------------------------------
cursor.execute("""\
    INSERT INTO #protcit
SELECT DISTINCT s.doc_id
           FROM query_term s
           JOIN pub_proc_cg p
             ON p.id = s.doc_id
           JOIN query_term cit
             ON cit.doc_id = p.id
          WHERE s.path   = '/InScopeProtocol/ProtocolAdminInfo'
                         + '/CurrentProtocolStatus'
            AND s.value IN ('Active', 'Approved-not yet active', 
                            'Closed', 'Completed', 'Temporarily closed')
            AND cit.path = '/InScopeProtocol/PublishedResults'
                         + '/Citation/@cdr:ref'""",
               timeout = 300)
conn.commit()
cursor.execute("SELECT COUNT(*) FROM #protcit")
#print "total protocols:", cursor.fetchall()[0][0]
htmlStrings.append(u"PUBLISHED RESULTS")
htmlStrings.append(showTotal(u"   InScopeProtocol Trials with Citations",
                             cursor.fetchall()[0][0] ))

# Create a table listing all InScopeProtocol that are on Cancer.gov
# and contain a published citation entry
# -----------------------------------------------------------------
cursor.execute("CREATE TABLE #ctprotcit (id INTEGER)")
conn.commit()
cursor.execute("""\
    INSERT INTO #ctprotcit
SELECT DISTINCT s.doc_id
           FROM query_term s
           JOIN pub_proc_cg p
             ON p.id = s.doc_id
           JOIN query_term cit
             ON cit.doc_id = p.id
          WHERE s.path   = '/CTGovProtocol/CTStatus'
            AND s.value IN ('Active', 'Approved-not yet active', 
                            'Closed', 'Completed', 'Temporarily closed')
            AND cit.path = '/CTGovProtocol/PublishedResults'
                         + '/Citation/@cdr:ref'""",
               timeout = 300)
conn.commit()
cursor.execute("SELECT COUNT(*) FROM #ctprotcit")

htmlStrings.append(showTotal(u"   CTGovProtocol Trials with Citations",
                             cursor.fetchall()[0][0]))
htmlStrings.append(u"""\
  </pre>
 </body>
</html>""")
cdrcgi.sendPage(u"\n".join(htmlStrings) + "\n")
