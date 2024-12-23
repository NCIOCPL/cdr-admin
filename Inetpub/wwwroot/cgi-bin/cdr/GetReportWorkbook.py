#!/usr/bin/env python

# ----------------------------------------------------------------------
# Sends back Excel workbook report to client.
# ----------------------------------------------------------------------
from cdrcgi import Controller, FieldStorage
from sys import stdout

fields = FieldStorage()
name = fields and fields.getvalue('name') or Controller.bail('Missing name')
try:
    with open('d:/cdr/Reports/%s' % name, 'rb') as fp:
        book = fp.read()
except Exception:
    Controller.bail('Report %s not found' % name)

stdout.buffer.write(f"""\
Content-type: application/vnd.ms-excel
Content-disposition: attachment;filename={name}

""".encode("utf-8"))
stdout.buffer.write(book)
