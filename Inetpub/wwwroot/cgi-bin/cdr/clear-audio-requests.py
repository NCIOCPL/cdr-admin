import cdrdb
import cgi

fields = cgi.FieldStorage()
book_name = fields.getvalue("book_name")
print "Content-type: text/plain\n"
if book_name:
    conn = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""\
DELETE FROM glossary_term_audio_request
      WHERE spreadsheet = ?""", book_name)
    conn.commit()
    print cursor.rowcount,
else:
    print 0,
print "rows deleted"
