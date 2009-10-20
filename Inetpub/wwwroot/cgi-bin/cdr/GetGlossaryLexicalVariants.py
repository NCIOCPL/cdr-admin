#----------------------------------------------------------------------
#
# $Id$
#
# Service requested by Chen (request #1895).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import cdrdb, cdrcgi, cgi, sys, cdr, xml.sax.saxutils

def fix(me):
    return xml.sax.saxutils.escape(me)

def bail(why):
    sys.stdout.write("Content-type: text/xml; charset=utf-8\n\n")
    what = u"<Failure>%s</Failure>" % why
    sys.stdout.write(what.encode('utf-8'))
    sys.stdout.close()
    sys.exit(0)
    
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
fields = cgi.FieldStorage()
cdrId = fields and fields.getvalue('CdrId') or bail("Missing required CdrId")
try:
    cdrId = cdr.exNormalize(cdrId)[1]
    
    cursor.execute("""\
    SELECT m.value
      FROM external_map m
      JOIN external_map_usage u
        ON u.id = m.usage
     WHERE u.name = 'GlossaryTerm Phrases'
       AND m.doc_id = ?
  ORDER BY m.id""", cdrId)
    rows = cursor.fetchall()
except Exception, e:
    bail(unicode(e))
if rows:
    lines = [u"<CdrGlossaryLexicalVariants DocId='CDR%010d'>" % cdrId]
    for row in rows:
        lines.append(u" <LexicalVariant>%s</LexicalVariant>" % row[0].strip())
    lines.append(u"</CdrGlossaryLexicalVariants>")
    response = u"\n".join(lines) + u"\n"
else:
    response = u"<CdrGlossaryLexicalVariants DocId='CDR%010d'/>" % cdrId
sys.stdout.write("Content-type: text/xml; charset=utf-8\n\n")
sys.stdout.write(response.encode('utf-8'))
sys.stdout.close()
