#!/usr/bin/env python

"""
Fetch XML for CDR filter

Used for comparing filters across tiers
"""

from sys import stdout
import cdr
from cdrapi import db
from cdrcgi import FieldStorage()

logger = cdr.Logging.get_logger("filters")
fields = FieldStorage()
title = fields.getvalue("title")
if not title:
    print("Status: 400 Missing title\n")
    exit(0)
logger.info("Fetch %r", title)
try:
    query = db.Query("document d", "d.xml", "t.name")
    query.join("doc_type t", "t.id = d.doc_type")
    query.where(query.Condition("d.title", title))
    rows = query.execute().fetchall()
except Exception:
    print("Status: 500 CDR database unavailable\n")
    exit(0)
if not len(rows):
    print("Status: 404 filter not found\n")
elif len(rows) > 1:
    print("Status: 400 ambiguous title\n")
else:
    xml, doctype = rows[0]
    if doctype.lower() != "filter":
        print("Status: 400 not a filter document\n")
    else:
        stdout.buffer.write(f"Content-type: text/xml\n\n{xml}".encode("utf-8"))
