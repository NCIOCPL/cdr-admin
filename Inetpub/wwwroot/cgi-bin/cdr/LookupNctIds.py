#----------------------------------------------------------------------
#
# $Id$
#
# Find NCT IDs matching CDR IDs.
#
#----------------------------------------------------------------------
import cgi, cdrdb

fields = cgi.FieldStorage()
cdrIds = fields.getvalue('cdr-ids').split('|')
cursor = cdrdb.connect('CdrGuest').cursor()
result = []
for cdrId in cdrIds:
    cursor.execute("""\
        SELECT i.value
          FROM query_term i
          JOIN query_term t
            ON t.doc_id = i.doc_id
           AND LEFT(t.node_loc, 8) = LEFT(i.node_loc, 8)
         WHERE t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
           AND i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
           AND t.value = 'ClinicalTrials.gov ID'
           AND i.doc_id = ?""", cdrId)
    rows = cursor.fetchall()
    if rows:
        result.append(u"%s=%s" % (cdrId, rows[0][0]))
print (u"""\
Content-type: text/plain; charset=utf-8

%s""" % "\n".join(result))
