import cgi, cdr, cdrcgi, cdrdb, sys

def getDocId(fields, args):
    docId = fields and fields.getvalue("id") or len(args) > 1 and args[1]
    if not docId:
        cdrcgi.sendPage(u"<Failure>Missing required 'id' parameter"
                        u"</Failure>", 'xml')
    return docId.strip()

def getDocType(cursor, docId):
    cursor.execute("""\
        SELECT t.name
          FROM doc_type t
          JOIN document d
            ON d.doc_type = t.id
         WHERE d.id = %s""" % docId)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.sendPage(u"<Failure>Invalid doc id '%s'</Failure", 'xml')
    docType = rows[0][0]
    if docType != 'InScopeProtocol':
        cdrcgi.sendPage(u"<Failure>Wrong document type (%s)</Failure>" %
                        docType, 'xml')
    return rows[0][0]

fields  = cgi.FieldStorage() or None
docId   = getDocId(fields, sys.argv)
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()
docType = getDocType(cursor, docId)
filters = ['set:Vendor InScopeProtocol Set']
docId   = "CDR%s" % docId
result  = cdr.filterDoc('guest', filters, docId)
if type(result) in (str, unicode):
    cdrcgi.sendPage(u"<Failure>Unable to filter trial document</Failure>",
                    'xml')
cdrcgi.sendPage(unicode(result[0], 'utf-8'), 'xml')
