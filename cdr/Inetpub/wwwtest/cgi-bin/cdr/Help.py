#----------------------------------------------------------------------
#
# $Id: Help.py,v 1.2 2002-08-15 19:26:26 bkline Exp $
#
# Display the table of contents for the CDR help system.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/06/04 20:18:52  bkline
# New interface to Eileen's Help pages.
#
#----------------------------------------------------------------------
import cdr, cdrcgi, cdrdb

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
except cdrdb.Error, info:
    cdrcgi.bail('Failure connecting to CDR: %s' % info[1][0])

#----------------------------------------------------------------------
# Find the table of contents document.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute("""\
            SELECT TOP 1 document.id
                    FROM document
                    JOIN doc_type
                      ON doc_type.id = document.doc_type
                   WHERE doc_type.name = 'DocumentationToC'""")
    rows = cursor.fetchall()
    if len(rows) != 1:
        cdrcgi.bail("Should be exactly one table of contents for CDR Help")
except cdrdb.Error, info:
    cdrcgi.bail('Failure locating table of contents document: %s' % info[1][0])

#----------------------------------------------------------------------
# Filter the document to create the HTML page.
#----------------------------------------------------------------------
response = cdr.filterDoc('guest', ['name:Help Table of Contents'], rows[0][0])
if type(response) in (type(''), type(u'')):
    cdrcgi.bail(response)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(response[0])
