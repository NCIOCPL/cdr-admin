#----------------------------------------------------------------------
#
# $Id: LookupNctId.py,v 1.1 2005-03-14 16:32:19 bkline Exp $
#
# Implement mechanism whereby they can query to get an NCTID for a CTEP ID.
# They will receive a response with content-type of text/plain, 
# containing the corresponding NCT ID if we find it, and the string
# ID NOT FOUND if we don't.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cgi, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields = cgi.FieldStorage()
ctepId = fields and fields.getvalue('ctep-id') or None
if not ctepId:
    sys.stdout.write("""\
Content-type: text/plain

MISSING ctep-id PARAMETER""")
    sys.exit(0)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
   SELECT nct_id.value
     FROM query_term nct_id
     JOIN query_term nct_id_type
       ON nct_id_type.doc_id = nct_id.doc_id
      AND LEFT(nct_id.node_loc, 8) = LEFT(nct_id_type.node_loc, 8)
     JOIN query_term ctep_id
       ON ctep_id.doc_id = nct_id.doc_id
     JOIN query_term ctep_id_type
       ON ctep_id_type.doc_id = ctep_id.doc_id
      AND LEFT(ctep_id.node_loc, 8) = LEFT(ctep_id_type.node_loc, 8)
    WHERE nct_id_type.path   = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
      AND nct_id.path        = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
      AND ctep_id_type.path  = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
      AND ctep_id.path       = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
      AND nct_id_type.value  = 'ClinicalTrials.gov ID'
      AND ctep_id_type.value = 'CTEP ID'
      AND ctep_id.value      = ?""", ctepId)
rows = cursor.fetchall()
nctId = rows and rows[0][0] or "ID NOT FOUND"
sys.stdout.write("""\
Content-type: text/plain

%s""" % nctId)
