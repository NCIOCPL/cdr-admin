#----------------------------------------------------------------------
#
# $Id: Help.py,v 1.4 2009-05-06 18:18:22 venglisc Exp $
#
# Display the table of contents for the CDR help system.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/10/18 13:54:49  bkline
# Added option for system documentation TOC.
#
# Revision 1.2  2002/08/15 19:26:26  bkline
# Removed hard-coded CDR login credentials.
#
# Revision 1.1  2002/06/04 20:18:52  bkline
# New interface to Eileen's Help pages.
#
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, cdrdb

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
flavor    = fields and fields.getvalue('flavor') or 'CDR Help'

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
                   WHERE doc_type.name = 'DocumentationToC'
                     AND document.title LIKE '%s%%'""" % flavor)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Cannot find %s table of contents")
except cdrdb.Error, info:
    cdrcgi.bail('Failure locating table of contents document: %s' % info[1][0])

#----------------------------------------------------------------------
# Filter the document to create the HTML page.
#----------------------------------------------------------------------
response = cdr.filterDoc('guest', ['name:Help Table of Contents'], rows[0][0])
if type(response) in (type(''), type(u'')):
    cdrcgi.bail(response)

#----------------------------------------------------------------------
# Send the page back to the browser after converting to Unicode.
#----------------------------------------------------------------------
page = response[0].decode('utf-8')
cdrcgi.sendPage(page)
