#!/usr/bin/env python

"""
Fetch XML for CDR filter

Used for comparing filters across tiers
"""

import cgi
import cdr
import cdrdb

logger = cdr.Logging.get_logger("filters")
fields = cgi.FieldStorage()
title = fields.getvalue("title")
if not title:
    print("Status: 400 Missing title\n")
    exit(0)
logger.info("Fetch %r", title)
try:
    query = cdrdb.Query("document d", "d.xml", "t.name")
    query.join("doc_type t", "t.id = d.doc_type")
    query.where(query.Condition("d.title", title))
    rows = query.execute().fetchall()
except:
    print("Status: 500 CDR database unavailable\n")
    exit(0)
if not len(rows):
    print("Status: 400 filter not found\n")
elif len(rows) > 1:
    print("Status: 400 ambiguous title\n")
else:
    xml, doctype = rows[0]
    if doctype.lower() != "filter":
        print("Status: 400 not a filter document\n")
    else:
        print(("Content-type: text/xml\n\n" + xml.encode("utf-8")))
