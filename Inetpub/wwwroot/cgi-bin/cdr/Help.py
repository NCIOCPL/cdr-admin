#----------------------------------------------------------------------
# Display the table of contents for the CDR help system.
# JIRA::OCECDR-3800
#----------------------------------------------------------------------
import cdr
import cgi
import cdrcgi
from cdrapi import db

#----------------------------------------------------------------------
# Fallback when id parameter is not supplied.
#----------------------------------------------------------------------
def default_help():
    try:
        cursor = db.connect(user='CdrGuest').cursor()
        cursor.execute("""\
SELECT doc_id
  FROM query_term
 WHERE path = '/DocumentationToC/ToCTitle'
   AND value = 'CDR Help'""")
        rows = cursor.fetchall()
        if rows:
            return rows[0][0]
        cursor.execute("""\
SELECT MIN(doc_id)
  FROM query_term
 WHERE path = '/DocumentationToC/ToCTitle'""")
        rows = cursor.fetchall()
        if rows:
            return rows[0][0]
    except:
        cdrcgi.bail("Unable to connect to the CDR database")
    cdrcgi.bail("Help system cannot be found")

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields = cgi.FieldStorage()
doc_id = fields.getvalue("id") or default_help()

#----------------------------------------------------------------------
# Filter the document to create the HTML page.
#----------------------------------------------------------------------
try:
    response = cdr.filterDoc('guest', ['name:Help Table of Contents'], doc_id)
    error = cdr.checkErr(response)
    if error:
        cdrcgi.bail(error)
except Exception as e:
    cdrcgi.bail(str(e))

#----------------------------------------------------------------------
# Send the page back to the browser after converting to Unicode.
#----------------------------------------------------------------------
cdrcgi.sendPage(response[0])
