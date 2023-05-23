#!/usr/bin/env python

# ----------------------------------------------------------------------
# Sends back Excel workbook report to client.
# ----------------------------------------------------------------------
import cdrcgi
import sys

fields = cdrcgi.FieldStorage()
name = fields and fields.getvalue('name') or cdrcgi.bail('Missing name')
try:
    with open('d:/cdr/Reports/%s' % name, 'rb') as fp:
        book = fp.read()
except Exception:
    cdrcgi.bail('Report %s not found' % name)

sys.stdout.buffer.write(f"""\
Content-type: application/vnd.ms-excel
Content-disposition: attachment;filename={name}

""".encode("utf-8"))
sys.stdout.buffer.write(book)
